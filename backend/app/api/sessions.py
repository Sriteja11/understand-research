import uuid
from typing import List, Optional
from fastapi import APIRouter, HTTPException
from backend.app.db.database import get_db_connection
from backend.app.schemas.sessions import SessionResponse, MessageResponse

router = APIRouter(prefix="/sessions", tags=["sessions"])

@router.get("", response_model=List[SessionResponse])
async def list_sessions():
    with get_db_connection() as conn:
        # Retroactively set session titles to first user message if still default
        conn.execute("""
            UPDATE sessions
            SET title = (
                SELECT substr(replace(m.content, char(10), ' '), 1, 60)
                FROM messages m
                WHERE m.session_id = sessions.id AND m.role = 'user'
                ORDER BY m.created_at ASC
                LIMIT 1
            )
            WHERE (title = 'New Research Session' OR title IS NULL OR title = '')
              AND EXISTS (
                SELECT 1 FROM messages m
                WHERE m.session_id = sessions.id AND m.role = 'user'
              );
        """)

        rows = conn.execute("""
            SELECT id, title, created_at, updated_at 
            FROM sessions 
            ORDER BY updated_at DESC
        """).fetchall()

        return [
            SessionResponse(
                id=r["id"],
                title=r["title"] or "New Research Session",
                created_at=str(r["created_at"]),
                updated_at=str(r["updated_at"])
            )
            for r in rows
        ]

@router.post("", response_model=SessionResponse)
async def create_session(title: Optional[str] = "New Research Session"):
    sid = f"sess_{uuid.uuid4().hex[:8]}"
    with get_db_connection() as conn:
        conn.execute(
            "INSERT INTO sessions (id, title) VALUES (?, ?)",
            (sid, title)
        )
        row = conn.execute("SELECT * FROM sessions WHERE id = ?", (sid,)).fetchone()
        return SessionResponse(
            id=row["id"],
            title=row["title"],
            created_at=str(row["created_at"]),
            updated_at=str(row["updated_at"])
        )

@router.get("/{session_id}", response_model=SessionResponse)
async def get_session(session_id: str):
    with get_db_connection() as conn:
        s_row = conn.execute("SELECT * FROM sessions WHERE id = ?", (session_id,)).fetchone()
        if not s_row:
            raise HTTPException(status_code=404, detail="Session not found.")
        
        m_rows = conn.execute(
            "SELECT * FROM messages WHERE session_id = ? ORDER BY created_at ASC",
            (session_id,)
        ).fetchall()

        messages = [
            MessageResponse(
                id=m["id"],
                session_id=m["session_id"],
                role=m["role"],
                content=m["content"],
                metadata_json=m["metadata_json"],
                created_at=str(m["created_at"])
            )
            for m in m_rows
        ]

        return SessionResponse(
            id=s_row["id"],
            title=s_row["title"],
            created_at=str(s_row["created_at"]),
            updated_at=str(s_row["updated_at"]),
            messages=messages
        )

@router.delete("/{session_id}")
async def delete_session(session_id: str):
    with get_db_connection() as conn:
        conn.execute("DELETE FROM messages WHERE session_id = ?", (session_id,))
        conn.execute("DELETE FROM sessions WHERE id = ?", (session_id,))
    return {"message": f"Session {session_id} deleted."}

