import re
from typing import List
from backend.app.ingestion.base import DocumentPage, Chunk
from backend.app.ingestion.cleaner import clean_text
from backend.app.ingestion.section_detector import detect_section_header
from backend.app.config import settings

def chunk_document(
    document_id: str,
    document_name: str,
    pages: List[DocumentPage],
    chunk_size_words: int = 400,
    chunk_overlap_words: int = 50
) -> List[Chunk]:
    """Segment document pages into section-aware overlapping chunks.
    
    Preserves document name, page numbers, section headers, and stable chunk identifiers.
    """
    chunks: List[Chunk] = []
    current_section = "Introduction"
    chunk_counter = 0

    for page in pages:
        cleaned_text = clean_text(page.text)
        if not cleaned_text:
            continue

        paragraphs = cleaned_text.split("\n\n")
        current_words: List[str] = []

        for p in paragraphs:
            lines = p.split("\n")
            first_line = lines[0].strip()
            detected = detect_section_header(first_line)
            if detected:
                # Flush accumulated words in previous section if any
                if current_words:
                    chunk_text = " ".join(current_words).strip()
                    if len(chunk_text) > 30:
                        chunk_id = f"{document_id}_p{page.page_number}_c{chunk_counter:03d}"
                        chunks.append(
                            Chunk(
                                document_id=document_id,
                                document_name=document_name,
                                page_number=page.page_number,
                                section=current_section,
                                chunk_id=chunk_id,
                                chunk_index=chunk_counter,
                                text=chunk_text,
                                metadata={
                                    "document_id": document_id,
                                    "document_name": document_name,
                                    "page_number": page.page_number,
                                    "section": current_section,
                                    "chunk_id": chunk_id,
                                    "chunk_index": chunk_counter
                                }
                            )
                        )
                        chunk_counter += 1
                        # Retain overlap words
                        current_words = current_words[-chunk_overlap_words:] if len(current_words) > chunk_overlap_words else []

                current_section = detected
                # The remainder of the paragraph is body text
                body = " ".join(lines[1:]).strip()
                words = body.split()
            else:
                words = p.split()

            current_words.extend(words)

            # Emit chunk when threshold reached
            while len(current_words) >= chunk_size_words:
                chunk_slice = current_words[:chunk_size_words]
                chunk_text = " ".join(chunk_slice).strip()
                if len(chunk_text) > 30:
                    chunk_id = f"{document_id}_p{page.page_number}_c{chunk_counter:03d}"
                    chunks.append(
                        Chunk(
                            document_id=document_id,
                            document_name=document_name,
                            page_number=page.page_number,
                            section=current_section,
                            chunk_id=chunk_id,
                            chunk_index=chunk_counter,
                            text=chunk_text,
                            metadata={
                                "document_id": document_id,
                                "document_name": document_name,
                                "page_number": page.page_number,
                                "section": current_section,
                                "chunk_id": chunk_id,
                                "chunk_index": chunk_counter
                            }
                        )
                    )
                    chunk_counter += 1
                # Slide window forward by overlap
                current_words = current_words[chunk_size_words - chunk_overlap_words:]

        # Emit leftover words on current page
        if current_words:
            chunk_text = " ".join(current_words).strip()
            if len(chunk_text) > 30:
                chunk_id = f"{document_id}_p{page.page_number}_c{chunk_counter:03d}"
                chunks.append(
                    Chunk(
                        document_id=document_id,
                        document_name=document_name,
                        page_number=page.page_number,
                        section=current_section,
                        chunk_id=chunk_id,
                        chunk_index=chunk_counter,
                        text=chunk_text,
                        metadata={
                            "document_id": document_id,
                            "document_name": document_name,
                            "page_number": page.page_number,
                            "section": current_section,
                            "chunk_id": chunk_id,
                            "chunk_index": chunk_counter
                        }
                    )
                )
                chunk_counter += 1

    return chunks

