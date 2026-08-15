"""Text -> speech backends.

A small interface so the rest of the pipeline never imports a specific engine.
XTTS-v2 (local, supports zero-shot voice cloning from a reference clip) is the
default; a cloud backend (e.g. ElevenLabs) could be added later without touching
callers.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Protocol

# Agree to the Coqui model license non-interactively (otherwise the first model
# load blocks on a stdin prompt).
os.environ.setdefault("COQUI_TOS_AGREED", "1")


class TTSBackend(Protocol):
    def synthesize(self, text: str, out_wav: Path, ref_wav: Path | None = None) -> Path:
        """Render ``text`` to ``out_wav``. If ``ref_wav`` is given, clone that voice."""
        ...


def _pick_device(requested: str) -> str:
    """Resolve 'auto' to a concrete device. XTTS has spotty MPS-kernel coverage
    on Apple Silicon, so 'auto' prefers CUDA then CPU; pass device='mps'
    explicitly to try the GPU path."""
    import torch

    if requested and requested != "auto":
        return requested
    if torch.cuda.is_available():
        return "cuda"
    return "cpu"


class XTTSBackend:
    """Local XTTS-v2 via coqui-tts.

    Loads the model once on first use. Without a reference clip it narrates with
    a built-in speaker; with one it clones that voice zero-shot.
    """

    MODEL = "tts_models/multilingual/multi-dataset/xtts_v2"
    DEFAULT_SPEAKER = "Ana Florence"  # a clear built-in XTTS voice

    def __init__(self, language: str = "en", device: str = "auto") -> None:
        self.language = language
        self.device = device
        self._model = None
        self._speaker = None

    def _load(self):
        if self._model is not None:
            return self._model
        from TTS.api import TTS  # heavy import; defer until actually synthesizing

        device = _pick_device(self.device)
        model = TTS(self.MODEL).to(device)
        self._model = model
        # Resolve a default built-in speaker for the no-reference case.
        speakers = list(getattr(model, "speakers", None) or [])
        if speakers:
            self._speaker = self.DEFAULT_SPEAKER if self.DEFAULT_SPEAKER in speakers else speakers[0]
        return model

    def synthesize(self, text: str, out_wav: Path, ref_wav: Path | None = None) -> Path:
        model = self._load()
        out_wav = Path(out_wav)
        out_wav.parent.mkdir(parents=True, exist_ok=True)
        kwargs = dict(text=text, language=self.language, file_path=str(out_wav), split_sentences=False)
        if ref_wav is not None:
            kwargs["speaker_wav"] = str(ref_wav)
        else:
            kwargs["speaker"] = self._speaker
        model.tts_to_file(**kwargs)
        return out_wav


def get_backend(name: str = "xtts", **kwargs) -> TTSBackend:
    if name == "xtts":
        return XTTSBackend(**kwargs)
    raise ValueError(f"unknown TTS backend: {name!r}")
