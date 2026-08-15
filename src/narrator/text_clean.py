"""Raw PDF text -> clean, narratable text -> chunks.

This is where most of the final audio quality is won or lost. PDF text arrives
with hyphenated line breaks, hard-wrapped paragraphs, repeated running
headers/footers, and bare page numbers — all of which sound wrong read aloud.
"""

from __future__ import annotations

import re
from collections import Counter

# A trailing reference/bibliography section reads terribly as audio.
_REF_HEADING = re.compile(
    r"^\s*(references|bibliography|works cited)\s*$",
    re.IGNORECASE | re.MULTILINE,
)


def _strip_running_headers(pages: list[str]) -> list[str]:
    """Drop lines that repeat on many pages (running headers/footers) and bare
    page numbers. A line appearing on >40% of pages is treated as boilerplate."""
    if len(pages) < 3:
        candidates: set[str] = set()
    else:
        first_last: Counter[str] = Counter()
        for p in pages:
            lines = [ln.strip() for ln in p.splitlines() if ln.strip()]
            # distinct lines from the top/bottom of the page — dedupe per page so
            # short pages (where the head and tail slices overlap) don't double-count.
            edges = set(lines[:2]) | set(lines[-2:])
            for ln in edges:
                first_last[ln] += 1
        threshold = max(2, int(len(pages) * 0.4))
        candidates = {ln for ln, n in first_last.items() if n >= threshold}

    cleaned = []
    for p in pages:
        kept = []
        for ln in p.splitlines():
            s = ln.strip()
            if s in candidates:
                continue
            if re.fullmatch(r"[\divxlcIVXLC\-–—.\s]{1,6}", s):  # bare page numbers
                continue
            kept.append(ln)
        cleaned.append("\n".join(kept))
    return cleaned


def _dehyphenate(text: str) -> str:
    """Join words split across line breaks: 'inter-\\nnational' -> 'international'."""
    return re.sub(r"(\w)-\n(\w)", r"\1\2", text)


def _rewrap_paragraphs(text: str) -> str:
    """Collapse hard-wrapped lines into paragraphs. Blank lines mark paragraph
    breaks; single newlines inside a block become spaces."""
    blocks = re.split(r"\n\s*\n", text)
    out = []
    for block in blocks:
        joined = re.sub(r"\s*\n\s*", " ", block).strip()
        if joined:
            out.append(joined)
    return "\n\n".join(out)


def clean(raw: str, skip_references: bool = True) -> str:
    """Full clean pass on form-feed-separated page text from pdf_extract."""
    pages = raw.split("\f")
    pages = _strip_running_headers(pages)
    text = "\n\n".join(pages)

    text = _dehyphenate(text)

    # Cut the references section while the heading is still on its own line —
    # rewrapping below would merge it into the following text.
    if skip_references:
        m = _REF_HEADING.search(text)
        if m:
            text = text[: m.start()].rstrip()

    text = _rewrap_paragraphs(text)

    # normalize whitespace and stray artifacts
    text = text.replace("­", "")            # soft hyphens
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


_SENT_SPLIT = re.compile(r"(?<=[.!?])\s+")


def chunk(text: str, max_chars: int = 240) -> list[str]:
    """Split into TTS-sized chunks on sentence boundaries, never exceeding
    ``max_chars`` where avoidable. Paragraphs are kept as boundaries so callers
    can insert pauses between them."""
    chunks: list[str] = []
    for para in text.split("\n\n"):
        para = para.strip()
        if not para:
            continue
        current = ""
        for sent in _SENT_SPLIT.split(para):
            sent = sent.strip()
            if not sent:
                continue
            if len(sent) > max_chars:  # very long sentence: hard-wrap on commas/space
                if current:
                    chunks.append(current)
                    current = ""
                chunks.extend(_hard_wrap(sent, max_chars))
                continue
            if len(current) + len(sent) + 1 <= max_chars:
                current = f"{current} {sent}".strip()
            else:
                chunks.append(current)
                current = sent
        if current:
            chunks.append(current)
    return chunks


def _hard_wrap(sent: str, max_chars: int) -> list[str]:
    parts, current = [], ""
    for word in sent.split():
        if len(current) + len(word) + 1 <= max_chars:
            current = f"{current} {word}".strip()
        else:
            parts.append(current)
            current = word
    if current:
        parts.append(current)
    return parts
