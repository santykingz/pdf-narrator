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
    voice: str = typer.Option(None, "--voice", help="Voice name built with prep-voice."),
):
    """Milestones 2/4/5: PDF -> spoken audio (optionally in a cloned voice)."""
    typer.echo("narrate is not implemented yet (milestones 2/4/5). See tts.py / stitch.py.")
    raise typer.Exit(code=1)


if __name__ == "__main__":
    app()
