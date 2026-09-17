import os
import pytest
from backend.app.ingestion.cleaner import clean_text
from backend.app.ingestion.section_detector import detect_section_header
from backend.app.ingestion.chunker import chunk_document
from backend.app.ingestion.base import DocumentPage
from backend.app.ingestion.text_parser import TextParser
from backend.app.ingestion.markdown_parser import MarkdownParser
from backend.app.ingestion.pdf_parser import PDFParser
from backend.app.ingestion import get_parser_for_file

def test_clean_text():
    raw = "Here is some text with\x00 null bytes and \n\n\n excessive newlines. Page 1 of 10"
    cleaned = clean_text(raw)
    assert "\x00" not in cleaned
    assert "Page 1 of 10" not in cleaned
    assert "Here is some text with null bytes and" in cleaned

def test_section_detector():
    assert detect_section_header("1. Introduction") == "1 Introduction"
    assert detect_section_header("3.2 Multi-Head Attention") == "3.2 Multi-Head Attention"
    assert detect_section_header("## Methodology") == "Methodology"
    assert detect_section_header("This is regular sentence text that should not be a section.") is None

def test_chunker():
    pages = [
        DocumentPage(page_number=1, text="1. Introduction\n\n" + ("Transformer models are attention based architectures. " * 30)),
        DocumentPage(page_number=2, text="2. Background\n\n" + ("Recurrent neural networks process tokens sequentially. " * 30))
    ]
    chunks = chunk_document(
        document_id="doc_test",
        document_name="test.pdf",
        pages=pages,
        chunk_size_words=20,
        chunk_overlap_words=5
    )
    assert len(chunks) >= 2
    for c in chunks:
        assert c.document_id == "doc_test"
        assert c.document_name == "test.pdf"
        assert c.page_number in [1, 2]
        assert len(c.chunk_id) > 0
        assert c.section in ["1 Introduction", "2 Background"]

def test_text_and_markdown_parser(tmp_path):
    txt_file = tmp_path / "sample.txt"
    txt_file.write_text("This is a test plain text document.", encoding="utf-8")
    parser = TextParser()
    pages = parser.parse(str(txt_file))
    assert len(pages) == 1
    assert "test plain text" in pages[0].text

    md_file = tmp_path / "sample.md"
    md_file.write_text("# Title\n\nSome markdown paragraph.", encoding="utf-8")
    md_parser = MarkdownParser()
    md_pages = md_parser.parse(str(md_file))
    assert len(md_pages) == 1
    assert "# Title" in md_pages[0].text

def test_empty_file_handling(tmp_path):
    empty_file = tmp_path / "empty.txt"
    empty_file.write_text("", encoding="utf-8")
    parser = TextParser()
    with pytest.raises(ValueError, match="Empty text file"):
        parser.parse(str(empty_file))

def test_unsupported_file():
    with pytest.raises(ValueError, match="Unsupported file format"):
        get_parser_for_file("document.xlsx")

