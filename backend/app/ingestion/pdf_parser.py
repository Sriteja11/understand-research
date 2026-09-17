import os
from typing import List
import pymupdf
from backend.app.ingestion.base import DocumentParser, DocumentPage

class PDFParser(DocumentParser):
    """Extract page-level text and metadata from PDF files."""

    def parse(self, file_path: str) -> List[DocumentPage]:
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"File not found: {file_path}")

        file_size = os.path.getsize(file_path)
        if file_size == 0:
            raise ValueError(f"Empty PDF file: {os.path.basename(file_path)}")

        pages: List[DocumentPage] = []
        try:
            doc = pymupdf.open(file_path)
            if doc.is_encrypted:
                raise ValueError(f"PDF is encrypted: {os.path.basename(file_path)}")

            if len(doc) == 0:
                raise ValueError(f"PDF contains no pages: {os.path.basename(file_path)}")

            has_extracted_text = False
            for page_idx in range(len(doc)):
                page = doc[page_idx]
                text = page.get_text("text")
                if text.strip():
                    has_extracted_text = True
                pages.append(
                    DocumentPage(
                        page_number=page_idx + 1,
                        text=text or "",
                        metadata={"total_pages": len(doc)}
                    )
                )
            doc.close()

            if not has_extracted_text:
                raise ValueError(f"PDF contains no extractable text: {os.path.basename(file_path)}")

            return pages
        except pymupdf.FileDataError as err:
            raise ValueError(f"Corrupt or invalid PDF file: {err}")
        except Exception as err:
            if isinstance(err, ValueError):
                raise
            raise ValueError(f"Failed to parse PDF {os.path.basename(file_path)}: {str(err)}")

