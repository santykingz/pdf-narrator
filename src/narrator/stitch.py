"""Combine per-chunk WAVs into a single narrated audio file.

Concatenates chunk audio in order with a short silence between segments (a
longer pause at paragraph boundaries), then exports to mp3/m4a/m4b.
"""

from __future__ import annotations

from pathlib import Path


def _trim_silence(seg, silence_thresh_db: int = -45, keep_ms: int = 40):
    """Strip leading/trailing near-silence, keeping a small margin. Removes the
    dead air XTTS pads onto each chunk so our own pauses aren't doubled up."""
    from pydub.silence import detect_leading_silence

    lead = detect_leading_silence(seg, silence_threshold=silence_thresh_db)
    trail = detect_leading_silence(seg.reverse(), silence_threshold=silence_thresh_db)
    start = max(0, lead - keep_ms)
    end = len(seg) - max(0, trail - keep_ms)
    return seg[start:end] if end > start else seg


def stitch(
    chunk_wavs: list[Path],
    out_path: Path,
    paragraph_breaks: set[int] | None = None,
    pause_ms: int = 150,
    paragraph_pause_ms: int = 450,
    trim_silence: bool = True,
) -> Path:
    """Concatenate chunk audio into one file.

    ``paragraph_breaks`` holds indices of chunks that begin a new paragraph;
    a longer pause is inserted before those.
    """
    from pydub import AudioSegment

    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    paragraph_breaks = paragraph_breaks or set()

    short_gap = AudioSegment.silent(duration=pause_ms)
    long_gap = AudioSegment.silent(duration=paragraph_pause_ms)

    combined = AudioSegment.empty()
    for i, wav in enumerate(chunk_wavs):
        seg = AudioSegment.from_wav(str(wav))
        if trim_silence:
            seg = _trim_silence(seg)
        if i > 0:
            combined += long_gap if i in paragraph_breaks else short_gap
        combined += seg

    # pydub/ffmpeg format names: m4a/m4b are the "ipod" container.
    suffix = out_path.suffix.lower().lstrip(".")
    fmt = "ipod" if suffix in {"m4a", "m4b"} else suffix
    combined.export(str(out_path), format=fmt)
    return out_path
