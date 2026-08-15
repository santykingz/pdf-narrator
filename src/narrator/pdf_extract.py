"""PDF -> raw text.

Uses PyMuPDF for the text layer, and falls back to OCR (Tesseract) for pages
that appear to be scanned images with no extractable text.
"""

from __future__ import annotations

from pathlib import Path

import pymupdf as fitz  # PyMuPDF (new import name)


def _ocr_page(page: "fitz.Page", dpi: int = 300) -> str:
    """Render a page to an image and OCR it. Imported lazily so milestone 1
    doesn't require pillow/pytesseract unless a scanned page is actually hit."""
    from io import BytesIO

    import pytesseract
    from PIL import Image

    pix = page.get_pixmap(dpi=dpi)
    img = Image.open(BytesIO(pix.tobytes("png")))
    return pytesseract.image_to_string(img)


def extract_pages(
    pdf_path: str | Path,
    ocr_fallback: bool = True,
    ocr_min_chars: int = 20,
) -> list[str]:
    """Return a list of page texts (one string per page).

    A page whose extracted text is shorter than ``ocr_min_chars`` is treated as
    scanned and, if ``ocr_fallback`` is set, re-read via OCR.
    """
    pdf_path = Path(pdf_path)
    if not pdf_path.exists():
        raise FileNotFoundError(pdf_path)

    pages: list[str] = []
    with fitz.open(pdf_path) as doc:
        for page in doc:
            text = page.get_text("text")
            if ocr_fallback and len(text.strip()) < ocr_min_chars:
                try:
                    text = _ocr_page(page)
                except Exception as exc:  # OCR is best-effort
                    text = text or f"[OCR failed on page {page.number + 1}: {exc}]"
            pages.append(text)
    return pages


def extract_text(pdf_path: str | Path, **kwargs) -> str:
    """Convenience: all pages joined with form-feeds so downstream cleaning can
    still see page boundaries (useful for stripping repeated headers/footers)."""
    return "\f".join(extract_pages(pdf_path, **kwargs))
