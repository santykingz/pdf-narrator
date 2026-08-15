# pdf-narrator

Drop a PDF in, get a spoken-word audio file out — narrated in a cloned voice.

Local, open-source pipeline built around **XTTS-v2** for text-to-speech and
**pyannote** for pulling a single speaker out of a multi-person podcast to use
as the voice reference.

```
Voice prep (once per person):
  podcast mp3s → diarize → pick the speaker → clean solo clips → reference.wav

Document run (every PDF):
  PDF → extract text → clean & chunk → XTTS(chunk, reference.wav) → stitch → output.m4b
```

## Status

Built in milestones (see `cli.py`):

1. ✅ **PDF → clean text** — `pdf_extract.py`, `text_clean.py`
2. ⬜ Text → audio with a stock XTTS voice — `tts.py`
3. ⬜ Voice prep (manual speaker pick) — `voice_prep.py`
4. ⬜ Clone from `reference.wav`
5. ⬜ Chunking, pauses, `.m4b` packaging — `stitch.py`
6. ⬜ Automated speaker recognition (embeddings)
7. ⬜ Watch-folder / web UI

## Setup (macOS / Apple Silicon)

```bash
# system deps
brew install ffmpeg tesseract           # tesseract already present for OCR

# python 3.11 (the ML stack isn't reliable on 3.13 yet)
/opt/homebrew/bin/python3.11 -m venv .venv
source .venv/bin/activate

# milestone 1 only — no heavy ML download needed
pip install -r requirements-core.txt

# later milestones (torch, XTTS, diarization — large download)
pip install -r requirements-ml.txt
```

## Usage

```bash
# milestone 1 — works today
narrator extract input/paper.pdf              # -> output/paper.txt (review this!)

# later milestones
narrator prep-voice barbaro voices/barbaro/raw/*.mp3
narrator narrate input/paper.pdf --voice barbaro
```

## Notes on Apple Silicon

XTTS often falls back to CPU on M-series (some ops lack MPS kernels). It works,
but expect roughly real-time synthesis, not faster. Generated chunks are cached
so re-runs skip finished audio.

## A note on voice cloning

Only clone voices you have the right to use. Don't publish cloned audio of a
real person in a way that implies they actually said it.
