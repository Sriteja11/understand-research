import os
from typing import List
from backend.app.ingestion.base import DocumentParser, DocumentPage

class MarkdownParser(DocumentParser):
    """Extract text from markdown files while preserving markdown headers."""

    def parse(self, file_path: str) -> List[DocumentPage]:
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"File not found: {file_path}")

        if os.path.getsize(file_path) == 0:
            raise ValueError(f"Empty markdown file: {os.path.basename(file_path)}")

        content = ""
        for encoding in ["utf-8", "latin-1"]:
            try:
                with open(file_path, "r", encoding=encoding) as f:
                    content = f.read()
                break
            except UnicodeDecodeError:
                continue

        if not content.strip():
            raise ValueError(f"Markdown file contains only whitespace: {os.path.basename(file_path)}")

        return [DocumentPage(page_number=1, text=content)]

