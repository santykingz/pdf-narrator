"""Combine per-chunk WAVs into a single narrated audio file.

Milestone 5:
  - concatenate chunk WAVs in order with a short silence between paragraphs
  - loudness-normalize
  - export .mp3, or .m4b with chapter markers for long documents
"""

from __future__ import annotations

from pathlib import Path


def stitch(
    chunk_wavs: list[Path],
    out_path: Path,
    paragraph_breaks: set[int] | None = None,
    pause_ms: int = 400,
) -> Path:
    """Concatenate chunk audio into one file.

    TODO (milestone 5): use pydub.AudioSegment to concat, insert
    AudioSegment.silent(pause_ms) at indices in ``paragraph_breaks``, normalize,
    and export based on out_path suffix (.mp3 / .m4b).
    """
    raise NotImplementedError("stitch not implemented yet (milestone 5)")
