"""Text -> speech backends.

A small interface so the rest of the pipeline never imports a specific engine.
XTTS-v2 (local, supports zero-shot voice cloning from a reference clip) is the
default; a cloud backend (e.g. ElevenLabs) could be added later without touching
callers.
"""

from __future__ import annotations

from pathlib import Path
from typing import Protocol


class TTSBackend(Protocol):
    def synthesize(self, text: str, out_wav: Path, ref_wav: Path | None = None) -> Path:
        """Render ``text`` to ``out_wav``. If ``ref_wav`` is given, clone that voice."""
        ...


class XTTSBackend:
    """Local XTTS-v2 via coqui-tts.

    TODO (milestone 2/4):
      - lazily load the model once: TTS("tts_models/multilingual/multi-dataset/xtts_v2")
      - pick device: mps if available else cpu (XTTS often needs cpu on M-series)
      - synthesize per chunk with speaker_wav=ref_wav, language=<cfg>
      - cache by hash(text + ref_wav) so re-runs skip finished chunks
    """

    def __init__(self, language: str = "en", device: str = "auto") -> None:
        self.language = language
        self.device = device
        self._model = None  # loaded on first use

    def synthesize(self, text: str, out_wav: Path, ref_wav: Path | None = None) -> Path:
        raise NotImplementedError(
            "XTTS backend not implemented yet (milestone 2/4). "
            "Install requirements-ml.txt, then wire coqui-tts here."
        )


def get_backend(name: str = "xtts", **kwargs) -> TTSBackend:
    if name == "xtts":
        return XTTSBackend(**kwargs)
    raise ValueError(f"unknown TTS backend: {name!r}")
