"""PDF -> raw text.

Uses PyMuPDF for the text layer, and falls back to OCR (Tesseract) for pages
that appear to be scanned images with no extractable text.
"""

from __future__ import annotations

from pathlib import Path

import pymupdf as fitz  # PyMuPDF (new import name)


def _in_table(block_rect: "fitz.Rect", table_rects: list) -> bool:
    """True if most of a text block falls inside a detected table region."""
    area = block_rect.get_area()
    if area <= 0:
        return False
    for tr in table_rects:
        if (block_rect & tr).get_area() > 0.5 * area:
            return True
    return False


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
            # Detect table regions geometrically so we can drop their cell text —
            # tables read as un-narratable fragments, and their cells don't share
            # any text marker we could otherwise filter on.
            # (find_tables emits a one-line "use pymupdf_layout" notice we can't
            # easily silence — harmless.)
            table_rects = []
            for strategy in ("lines_strict", "text"):
                try:
                    found = page.find_tables(strategy=strategy).tables
                    table_rects.extend(fitz.Rect(t.bbox) for t in found)
                except Exception:
                    pass

            # Layout blocks (paragraphs, captions) separated by blank lines.
            # Keeping them as distinct units lets text_clean drop a figure caption
            # without it bleeding into the surrounding sentence.
            blocks = page.get_text("blocks", sort=True)
            kept = []
            for b in blocks:
                if not b[4].strip() or b[6] != 0:
                    continue
                if _in_table(fitz.Rect(b[:4]), table_rects):
                    continue
                kept.append(b[4].strip())
            text = "\n\n".join(kept)
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
