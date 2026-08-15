# pdf-narrator

Drop a PDF in, get a spoken-word audio file out — optionally narrated in a **cloned voice**.

Local, open-source pipeline: **PyMuPDF** for text, **XTTS-v2** (coqui-tts) for
text-to-speech, **pyannote** to pull a single speaker out of a multi-person
podcast for the voice reference, and **ffmpeg** for audio.

```
Voice prep (once per person):
  podcast audio → diarize → pick the speaker → reference.wav

Document run (every PDF):
  PDF → extract text → clean & chunk → XTTS(chunk, reference.wav) → stitch → output.mp3
```

## Status

1. ✅ **PDF → clean text** — `pdf_extract.py`, `text_clean.py`
2. ✅ **Text → audio (stock voice)** — `tts.py`
3. ✅ **Voice prep (diarize + manual speaker pick)** — `voice_prep.py`
4. ✅ **Clone from `reference.wav`** — `narrate --voice`
5. ◐ Pauses & stitching done; `.m4b` chapter markers TODO — `stitch.py`
6. ⬜ Automated speaker recognition (embeddings)
7. ⬜ Watch-folder / web UI

## Setup (macOS / Apple Silicon)

```bash
# system deps
brew install ffmpeg tesseract

# python 3.11 (the ML stack isn't reliable on 3.13 yet)
/opt/homebrew/bin/python3.11 -m venv .venv
source .venv/bin/activate

pip install -r requirements-core.txt   # PDF → text (light)
pip install -r requirements-ml.txt     # torch, XTTS, pyannote (multi-GB download)
pip install -e .                        # installs the `narrator` command
```

For voice cloning you also need a free **Hugging Face token** (pyannote's models
are gated):

1. Create a token at huggingface.co/settings/tokens (Read type is enough).
2. Accept the terms on `pyannote/speaker-diarization-community-1` (and
   `pyannote/segmentation-3.0`).
3. Put it in a `.env` file at the project root (gitignored, never committed):
   ```
   HF_TOKEN=hf_xxxxxxxxxxxxxxxxxxxx
   ```

## Generating an MP3

### 1. (Optional but recommended) sanity-check the text first
```bash
narrator extract "input/paper.pdf"      # → output/paper.txt — read it before synth
```
The cleaner drops figure/table captions, equations, references, and journal
front-matter. If the `.txt` looks good, the audio will too.

### 2a. Narrate with the built-in stock voice
```bash
narrator narrate "input/paper.pdf"       # → output/paper.mp3
```

### 2b. Narrate in a cloned voice
First build the voice once (see "Cloning a voice" below), then:
```bash
narrator narrate "input/paper.pdf" --voice barbaro     # → output/paper.mp3
```

### Useful flags
```bash
narrator narrate "input/paper.pdf" --voice barbaro \
    --out output/my_audiobook.mp3 \   # custom output path (.mp3 / .m4a / .m4b)
    --start 3 \                        # skip the first N chunks (e.g. a title page)
    --limit 20                         # only synthesize N chunks (great for quick tests)
```
Synthesized chunks are **cached** under `output/.cache/`, so re-running skips
finished audio. Changing the voice, chunk size, or speed invalidates the cache
for that document — delete the relevant `output/.cache/<name>/` folder to force
a re-synth.

## Cloning a voice

Source ~30+ min of the person speaking (a podcast episode works well). To pull a
YouTube episode as audio:
```bash
yt-dlp --no-playlist -x --audio-format mp3 -o "voices/barbaro/raw/%(id)s.%(ext)s" "<youtube-url>"
```

Then diarize and pick the speaker:
```bash
# 1. diarize — lists speakers and writes a listenable sample of each
narrator prep-voice barbaro "voices/barbaro/raw/EPISODE.mp3"
afplay voices/barbaro/samples/SPEAKER_07.wav     # listen, identify your target

# 2. build reference.wav from the chosen speaker
narrator prep-voice barbaro "voices/barbaro/raw/EPISODE.mp3" --speaker SPEAKER_07
```
Now `--voice barbaro` works. Diarization is cached, so step 2 is instant.

## Tuning (`config.yaml`)

- `chunk.max_chars` — keep ≤ 250 (XTTS's English limit) to avoid truncation.
- `chunk.pause_ms` / `paragraph_pause_ms` — silence between sentences / paragraphs.
- `tts.speed` — 1.0 is natural; below ~0.9 tends to sound worse.
- `voice_prep.target_reference_secs` — XTTS clones best from one clean ~20s clip.

## Notes on Apple Silicon

XTTS falls back to CPU on M-series (some ops lack MPS kernels). It works, but
synthesis runs ~2.3× real-time — a full chapter is best run in the background.

## A note on voice cloning

Only clone voices you have the right to use, and don't publish cloned audio of a
real person as if they actually said it. Also: zero-shot cloning transfers a
voice's **timbre**, not a person's **cadence or pauses** — expect "their voice,
reading in a neutral style," not an impression.
