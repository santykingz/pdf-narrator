"""Combine per-chunk WAVs into a single narrated audio file.

Concatenates chunk audio in order with a short silence between segments (a
longer pause at paragraph boundaries), then exports to mp3/m4a/m4b.
"""

from __future__ import annotations

from pathlib import Path


def stitch(
    chunk_wavs: list[Path],
    out_path: Path,
    paragraph_breaks: set[int] | None = None,
    pause_ms: int = 250,
    paragraph_pause_ms: int = 500,
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
        if i > 0:
            combined += long_gap if i in paragraph_breaks else short_gap
        combined += AudioSegment.from_wav(str(wav))

    # pydub/ffmpeg format names: m4a/m4b are the "ipod" container.
    suffix = out_path.suffix.lower().lstrip(".")
    fmt = "ipod" if suffix in {"m4a", "m4b"} else suffix
    combined.export(str(out_path), format=fmt)
    return out_path
