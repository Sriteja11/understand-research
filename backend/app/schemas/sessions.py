from typing import List, Optional
from pydantic import BaseModel

class MessageResponse(BaseModel):
    id: str
    session_id: str
    role: str
    content: str
    metadata_json: Optional[str] = None
    created_at: str


class SessionResponse(BaseModel):
    id: str
    title: Optional[str] = None
    created_at: str
    updated_at: str
    messages: Optional[List[MessageResponse]] = None

