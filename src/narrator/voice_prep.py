"""Podcast audio -> a clean single-speaker reference.wav for voice cloning.

Milestone 3 (manual pick):
    1. Diarize the episode with pyannote -> speaker turns (who spoke when).
    2. Summarize speakers and export a short sample of each to listen to.
    3. The user names which label is the target speaker.
    4. Gather that label's clean solo segments (>= min_segment_secs) up to
       target_reference_secs, concatenate -> reference.wav.

Diarization is the slow step, so the CLI caches its result (see cli.prep_voice)
and this module stays pure: diarize once, then build samples / reference from
the cached turns.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass
class SpeakerTurn:
    label: str
    start: float  # seconds
    end: float

    @property
    def duration(self) -> float:
        return self.end - self.start


# Pipelines to try, best/most-self-contained first. pyannote 4.x's community-1
# bundles segmentation + embedding in one gated repo; the 3.1 pipeline (older)
# pulls from three separate gated repos.
_PIPELINES = ["pyannote/speaker-diarization-community-1", "pyannote/speaker-diarization-3.1"]


def _load_pipeline(hf_token: str):
    from pyannote.audio import Pipeline

    last_err = None
    for name in _PIPELINES:
        try:  # pyannote renamed the auth kwarg across versions
            try:
                return Pipeline.from_pretrained(name, token=hf_token)
            except TypeError:
                return Pipeline.from_pretrained(name, use_auth_token=hf_token)
        except Exception as e:  # gated/not-accepted -> try the next option
            last_err = e
    raise RuntimeError(
        "Could not load any diarization pipeline. Accept the model terms for one "
        f"of {_PIPELINES} on huggingface.co, then retry.\nLast error: {last_err}"
    )


def _as_clean_wav(path: Path) -> tuple[Path, "object"]:
    """pyannote's strict cropping trips on mp3s whose header sample-count doesn't
    match the decoder output. Decode to a temp 16 kHz mono WAV (exact sample
    counts) for diarization. Returns (wav_path, tempfile_or_None)."""
    if path.suffix.lower() == ".wav":
        return path, None
    import tempfile

    from pydub import AudioSegment

    tmp = tempfile.NamedTemporaryFile(suffix=".wav", delete=False)
    AudioSegment.from_file(str(path)).set_channels(1).set_frame_rate(16000).export(tmp.name, format="wav")
    return Path(tmp.name), tmp


def diarize(episode_path: Path, hf_token: str, device: str = "auto") -> list[SpeakerTurn]:
    """Run pyannote speaker diarization on one audio file. Timestamps are in
    seconds, so they map back to the original file for reference building."""
    import os

    import torch

    pipeline = _load_pipeline(hf_token)
    wav_path, tmp = _as_clean_wav(episode_path)

    dev = device
    if dev == "auto":
        dev = "mps" if torch.backends.mps.is_available() else "cpu"
    try:
        pipeline.to(torch.device(dev))
    except Exception:
        pipeline.to(torch.device("cpu"))  # fall back if the accelerator path fails

    try:
        result = pipeline(str(wav_path))
    finally:
        if tmp is not None:
            tmp.close()
            os.unlink(tmp.name)

    # pyannote 3.x returns an Annotation directly; 4.x returns a DiarizeOutput
    # with several views. Prefer the exclusive (non-overlapping) diarization —
    # it excludes crosstalk, which is exactly what we want for a clean reference.
    annotation = result
    if not hasattr(annotation, "itertracks"):
        annotation = (
            getattr(result, "exclusive_speaker_diarization", None)
            or getattr(result, "speaker_diarization", None)
        )
    if annotation is None or not hasattr(annotation, "itertracks"):
        raise RuntimeError(f"unexpected diarization output type: {type(result)}")

    return [
        SpeakerTurn(label=spk, start=float(turn.start), end=float(turn.end))
        for turn, _, spk in annotation.itertracks(yield_label=True)
    ]


def speaker_stats(turns: list[SpeakerTurn]) -> dict[str, dict]:
    """Per-speaker total speaking time and turn count, sorted by time desc."""
    stats: dict[str, dict] = {}
    for t in turns:
        s = stats.setdefault(t.label, {"seconds": 0.0, "turns": 0})
        s["seconds"] += t.duration
        s["turns"] += 1
    return dict(sorted(stats.items(), key=lambda kv: kv[1]["seconds"], reverse=True))


def _load_audio(path: Path):
    from pydub import AudioSegment

    seg = AudioSegment.from_file(str(path))
    return seg.set_channels(1)  # mono for a cleaner voice reference


def export_samples(
    episode_path: Path,
    turns: list[SpeakerTurn],
    out_dir: Path,
    seconds_each: float = 15.0,
    min_segment_secs: float = 3.0,
) -> dict[str, Path]:
    """Write one listenable sample per speaker (their longest solo segments
    concatenated up to ~seconds_each) so the user can identify the target."""
    audio = _load_audio(episode_path)
    out_dir.mkdir(parents=True, exist_ok=True)
    by_label: dict[str, list[SpeakerTurn]] = {}
    for t in turns:
        if t.duration >= min_segment_secs:
            by_label.setdefault(t.label, []).append(t)

    samples: dict[str, Path] = {}
    for label, segs in by_label.items():
        segs = sorted(segs, key=lambda s: s.duration, reverse=True)
        clip = audio[0:0]
        for s in segs:
            clip += audio[int(s.start * 1000) : int(s.end * 1000)]
            if clip.duration_seconds >= seconds_each:
                break
        out = out_dir / f"{label}.wav"
        clip[: int(seconds_each * 1000)].export(str(out), format="wav")
        samples[label] = out
    return samples


def build_reference(
    episode_path: Path,
    turns: list[SpeakerTurn],
    label: str,
    out_wav: Path,
    target_secs: float = 60.0,
    min_segment_secs: float = 3.0,
    sample_rate: int = 24000,
) -> float:
    """Concatenate the target speaker's clean solo segments into reference.wav.
    Returns the number of seconds of audio gathered."""
    audio = _load_audio(episode_path).set_frame_rate(sample_rate)
    segs = sorted(
        (t for t in turns if t.label == label and t.duration >= min_segment_secs),
        key=lambda s: s.duration,
        reverse=True,
    )
    if not segs:
        raise ValueError(f"no segments >= {min_segment_secs}s for speaker {label!r}")

    # Prefer a single continuous segment (best clone quality). Only concatenate
    # if the longest clean segment is too short to reach target on its own.
    if segs[0].duration >= min(target_secs, 12.0):
        s = segs[0]
        ref = audio[int(s.start * 1000) : int(s.end * 1000)]
    else:
        ref = audio[0:0]
        for s in segs:
            ref += audio[int(s.start * 1000) : int(s.end * 1000)]
            if ref.duration_seconds >= target_secs:
                break

    ref = ref[: int(target_secs * 1000)]
    out_wav.parent.mkdir(parents=True, exist_ok=True)
    ref.export(str(out_wav), format="wav")
    return ref.duration_seconds
