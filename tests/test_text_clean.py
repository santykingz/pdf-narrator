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
    # 4 pages sharing a running header + bare page numbers, varied body text
    bodies = [
        "Microbes drive carbon cycling in soils.",
        "Nitrogen fixation supports plant growth.",
        "Fungi decompose complex organic matter.",
        "Bacteria dominate the rhizosphere zone.",
    ]
    pages = [f"Journal of Soil Science\n{b}\n{i}" for i, b in enumerate(bodies, 1)]
    raw = "\f".join(pages)
    out = text_clean.clean(raw, skip_references=False, trim_frontmatter=False)
    assert "Journal of Soil Science" not in out
    assert "Microbes drive carbon cycling in soils." in out


def test_drops_figure_and_table_and_source_blocks():
    raw = (
        "Real narrative sentence about soil.\n\n"
        "FIGURE 2.1  Example soil profiles illustrating diversity.\n\n"
        "TABLE 2.1  Soil order descriptions and general features.\n\n"
        "Source: Photograph courtesy of J.A. Howe.\n\n"
        "Another real sentence follows here."
    )
    out = text_clean.clean(raw, skip_references=False)
    assert "Real narrative sentence about soil." in out
    assert "Another real sentence follows here." in out
    assert "FIGURE" not in out
    assert "TABLE" not in out
    assert "Source:" not in out


def test_keeps_inline_table_reference():
    raw = "The values are shown in Table 2.1 and remain valid."
    out = text_clean.clean(raw, skip_references=False)
    assert "Table 2.1" in out  # mid-sentence reference is not a caption


def test_drops_boilerplate_and_equations():
    raw = (
        "Body of the chapter here.\n\n"
        "Principles of Soil Microbiology. http://dx.doi.org/10.1016/x Copyright © 2021 Elsevier Inc.\n\n"
        "ρ ρ = − TotalPorosity b p\n\n"
        "(2.1)\n\n"
        "The chapter continues normally."
    )
    out = text_clean.clean(raw, skip_references=False)
    assert "Body of the chapter here." in out
    assert "The chapter continues normally." in out
    assert "doi.org" not in out
    assert "Copyright" not in out
    assert "TotalPorosity b p" not in out
    assert "(2.1)" not in out


def test_strips_invisible_chars():
    raw = "﻿Clean text with a byte order mark."
    out = text_clean.clean(raw, skip_references=False)
    assert out.startswith("Clean text")


def test_trims_frontmatter_to_abstract():
    raw = (
        "Journal of Soil Science\n\n"
        "Edited by: Some Editor\n\n"
        "Received: 04 December 2021 Accepted: 01 February 2022\n\n"
        "Abstract\n\n"
        + "This study examines microbial diversity in forest soils. " * 10
    )
    out = text_clean.clean(raw, skip_references=False, trim_frontmatter=True)
    assert "Edited by" not in out
    assert "Received" not in out
    assert "microbial diversity in forest soils" in out


def test_trim_does_not_fire_late_introduction():
    # "Introduction" only appears deep in the text -> must NOT trim.
    body = "Real opening content. " * 30
    raw = body + "\n\nIntroduction\n\nlate section"
    out = text_clean.clean(raw, skip_references=False, trim_frontmatter=True)
    assert "Real opening content." in out


def test_strips_citation_markers():
    raw = "recovered from soil libraries949-°1616472,73 and remained active*."
    out = text_clean.clean(raw, skip_references=False)
    assert "949" not in out
    assert "°" not in out
    assert "*" not in out
    assert "recovered from soil libraries" in out
    assert "remained active." in out


def test_citation_stripping_keeps_real_numbers():
    raw = "The soil had 8,000,000 microbes per gram at pH 6.5 in 2021."
    out = text_clean.clean(raw, skip_references=False)
    assert "8,000,000" in out
    assert "pH 6.5" in out
    assert "2021" in out


def test_fuzzy_footer_with_page_numbers():
    bodies = [
        "Soil microbes drive carbon cycling.",
        "Nitrogen fixation supports plant growth.",
        "Fungi decompose organic matter slowly.",
        "Bacteria dominate the rhizosphere zone.",
        "Archaea thrive in extreme soil habitats.",
    ]
    # Footer differs only by page number -> should collapse and be stripped.
    pages = [f"{b}\nNATURE REVIEWS | JUNE 2005 | {470 + i}" for i, b in enumerate(bodies, 1)]
    raw = "\f".join(pages)
    out = text_clean.clean(raw, skip_references=False, trim_frontmatter=False)
    assert "NATURE REVIEWS" not in out
    assert "Soil microbes drive carbon cycling." in out


def test_chunk_respects_max_chars():
    text = "Sentence one is here. " * 40
    chunks = text_clean.chunk(text.strip(), max_chars=100)
    assert chunks
    assert all(len(c) <= 100 for c in chunks)
