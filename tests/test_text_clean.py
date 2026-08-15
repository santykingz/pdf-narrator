from narrator import text_clean


def test_dehyphenate_and_rewrap():
    raw = "This is an inter-\nnational study of soil\nmicrobes in the field."
    out = text_clean.clean(raw, skip_references=False)
    assert "international" in out
    assert "soil microbes" in out
    assert "\n" not in out  # single paragraph rewrapped


def test_paragraph_break_preserved():
    raw = "First paragraph here.\n\nSecond paragraph here."
    out = text_clean.clean(raw, skip_references=False)
    assert out.count("\n\n") == 1


def test_skip_references_section():
    raw = "Body text of the paper.\n\nReferences\n\nSmith et al. 2020. Some paper."
    out = text_clean.clean(raw, skip_references=True)
    assert "Body text" in out
    assert "Smith" not in out


def test_strip_page_numbers_and_headers():
    # 4 pages sharing a running header + bare page numbers
    pages = [f"Journal of Soil Science\nContent for page {i}.\n{i}" for i in range(1, 5)]
    raw = "\f".join(pages)
    out = text_clean.clean(raw, skip_references=False)
    assert "Journal of Soil Science" not in out
    assert "Content for page 1." in out


def test_chunk_respects_max_chars():
    text = "Sentence one is here. " * 40
    chunks = text_clean.chunk(text.strip(), max_chars=100)
    assert chunks
    assert all(len(c) <= 100 for c in chunks)
