"""Podcast audio -> a clean single-speaker reference.wav for voice cloning.

Milestone 3 (manual pick):
    1. Diarize each episode with pyannote -> speaker turns (who spoke when).
    2. Summarize speakers ("SPEAKER_00: 11.8 min across 42 turns") and export a
       short sample of each so the user can listen.
    3. User names which label is the target (e.g. Michael Barbaro).
    4. Gather that label's clean solo segments (>= min_segment_secs, no overlap)
       up to target_reference_secs, concatenate -> reference.wav.

Milestone 6 (automated): compute an ECAPA-TDNN embedding per speaker, enroll the
target once, then auto-match the closest cluster in future episodes by cosine
similarity — no manual pick needed.
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


def diarize(episode_path: Path, hf_token: str) -> list[SpeakerTurn]:
    """Run pyannote diarization on one audio file.

    TODO (milestone 3):
      from pyannote.audio import Pipeline
      pipe = Pipeline.from_pretrained("pyannote/speaker-diarization-3.1", use_auth_token=hf_token)
      annotation = pipe(str(episode_path))
      return [SpeakerTurn(spk, seg.start, seg.end) for seg, _, spk in annotation.itertracks(yield_label=True)]
    """
    raise NotImplementedError("diarization not implemented yet (milestone 3)")


def build_reference(
    episode_paths: list[Path],
    out_wav: Path,
    target_secs: float = 60.0,
    min_segment_secs: float = 3.0,
) -> Path:
    """Diarize, prompt for the target speaker, and assemble reference.wav.

    TODO (milestone 3): tie together diarize() + a small interactive picker +
    audio slicing (librosa/soundfile) + concatenation.
    """
    raise NotImplementedError("build_reference not implemented yet (milestone 3)")
