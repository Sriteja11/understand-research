import os
from backend.app.ingestion.base import DocumentParser
from backend.app.ingestion.pdf_parser import PDFParser
from backend.app.ingestion.text_parser import TextParser
from backend.app.ingestion.markdown_parser import MarkdownParser

def get_parser_for_file(file_path: str) -> DocumentParser:
    ext = os.path.splitext(file_path)[1].lower()
    if ext == ".pdf":
        return PDFParser()
    elif ext == ".txt":
        return TextParser()
    elif ext == ".md":
        return MarkdownParser()
    else:
        raise ValueError(f"Unsupported file format '{ext}'. Supported formats: .pdf, .txt, .md")

