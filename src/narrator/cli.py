"""Command-line interface for pdf-narrator."""

from __future__ import annotations

from pathlib import Path

import typer

from . import config, pdf_extract, text_clean

app = typer.Typer(help="Drop a PDF in, get a cloned-voice audiobook out.", no_args_is_help=True)


@app.command()
def extract(
    pdf: Path = typer.Argument(..., help="Path to the input PDF."),
    out: Path = typer.Option(None, "--out", "-o", help="Output .txt (default: output/<name>.txt)."),
    no_ocr: bool = typer.Option(False, help="Disable OCR fallback for scanned pages."),
    raw: bool = typer.Option(False, help="Write raw extracted text without cleaning."),
):
    """Milestone 1: PDF -> clean, narratable text. Review the .txt before synth."""
    cfg = config.load()
    pages = pdf_extract.extract_pages(
        pdf,
        ocr_fallback=(not no_ocr) and cfg["extract"]["ocr_fallback"],
        ocr_min_chars=cfg["extract"]["ocr_min_chars"],
    )
    text = "\f".join(pages)
    if not raw:
        text = text_clean.clean(
            text,
            skip_references=cfg["extract"]["skip_references"],
            trim_frontmatter=cfg["extract"].get("trim_frontmatter", True),
        )

    if out is None:
        out_dir = config.project_root() / cfg["paths"]["output_dir"]
        out_dir.mkdir(parents=True, exist_ok=True)
        out = out_dir / f"{pdf.stem}.txt"

    out.write_text(text)
    chunks = text_clean.chunk(text, max_chars=cfg["chunk"]["max_chars"])
    typer.echo(f"✓ {len(pages)} pages -> {len(text)} chars -> {len(chunks)} chunks")
    typer.echo(f"  wrote {out}")


@app.command()
def prep_voice(
    name: str = typer.Argument(..., help="Voice name, e.g. 'barbaro'."),
    episodes: list[Path] = typer.Argument(..., help="Podcast audio files to source from."),
):
    """Milestone 3: build a clean reference.wav from podcast audio (manual speaker pick)."""
    typer.echo("prep-voice is not implemented yet (milestone 3). Scaffolding is in voice_prep.py.")
    raise typer.Exit(code=1)


@app.command()
def narrate(
    pdf: Path = typer.Argument(..., help="Path to the input PDF."),
    voice: str = typer.Option(None, "--voice", help="Voice name built with prep-voice (omit for a stock voice)."),
    out: Path = typer.Option(None, "--out", "-o", help="Output audio file (default: output/<name>.mp3)."),
    start: int = typer.Option(0, "--start", help="Skip the first N chunks (e.g. past a title page)."),
    limit: int = typer.Option(0, "--limit", help="Synthesize at most N chunks (for quick tests)."),
):
    """PDF -> spoken audio. With --voice, clone that voice; otherwise a stock voice."""
    from . import stitch, tts

    cfg = config.load()
    root = config.project_root()

    # 1. text
    pages = pdf_extract.extract_pages(
        pdf,
        ocr_fallback=cfg["extract"]["ocr_fallback"],
        ocr_min_chars=cfg["extract"]["ocr_min_chars"],
    )
    text = text_clean.clean(
        "\f".join(pages),
        skip_references=cfg["extract"]["skip_references"],
        trim_frontmatter=cfg["extract"].get("trim_frontmatter", True),
    )
    chunks, breaks = text_clean.chunk_with_breaks(text, max_chars=cfg["chunk"]["max_chars"])
    if not chunks:
        typer.echo("No narratable text found.")
        raise typer.Exit(code=1)

    # Keep original chunk indices as the cache key so slicing with --start/--limit
    # never collides with cache from a different slice of the same document.
    selected = list(enumerate(chunks))[start:]
    if limit > 0:
        selected = selected[:limit]
    # Remap paragraph-break indices to positions within the selected slice.
    local_breaks = {pos for pos, (orig_i, _) in enumerate(selected) if orig_i in breaks}

    # 2. resolve voice reference (None -> stock built-in speaker)
    ref_wav = None
    if voice:
        ref_wav = root / cfg["paths"]["voices_dir"] / voice / "reference.wav"
        if not ref_wav.exists():
            typer.echo(f"No reference.wav for voice '{voice}'. Build it with: narrator prep-voice {voice} <audio>")
            raise typer.Exit(code=1)

    # 3. synthesize per chunk, caching so re-runs skip finished audio
    backend = tts.get_backend(
        cfg["tts"]["backend"], language=cfg["tts"]["language"], device=cfg["tts"]["device"]
    )
    cache_dir = root / cfg["paths"]["output_dir"] / ".cache" / (pdf.stem + ("-" + voice if voice else ""))
    cache_dir.mkdir(parents=True, exist_ok=True)

    wavs = []
    with typer.progressbar(selected, label="Synthesizing") as items:
        for orig_i, chunk_text in items:
            wav = cache_dir / f"{orig_i:05d}.wav"
            if not wav.exists():
                backend.synthesize(chunk_text, wav, ref_wav=ref_wav)
            wavs.append(wav)

    # 4. stitch
    if out is None:
        out = root / cfg["paths"]["output_dir"] / f"{pdf.stem}.mp3"
    stitch.stitch(
        wavs,
        out,
        paragraph_breaks=local_breaks,
        paragraph_pause_ms=cfg["chunk"]["paragraph_pause_ms"],
    )
    typer.echo(f"✓ {len(wavs)} chunks -> {out}")


if __name__ == "__main__":
    app()
