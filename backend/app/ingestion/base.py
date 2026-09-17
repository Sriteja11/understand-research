from abc import ABC, abstractmethod
from typing import List, Dict, Any
from pydantic import BaseModel, Field


class DocumentPage(BaseModel):
    page_number: int
    text: str
    metadata: Dict[str, Any] = Field(default_factory=dict)


class Chunk(BaseModel):
    document_id: str
    document_name: str
    page_number: int
    section: str
    chunk_id: str
    chunk_index: int
    text: str
    metadata: Dict[str, Any] = Field(default_factory=dict)


class DocumentParser(ABC):
    @abstractmethod
    def parse(self, file_path: str) -> List[DocumentPage]:
        """Parse file into document pages with extracted text and page numbers."""
        pass

