import uuid
from datetime import datetime, timezone
from typing import Dict, List, Optional

from app.chat.db import get_conn


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def create_session() -> str:
    session_id = str(uuid.uuid4())
    with get_conn() as conn:
        conn.execute(
            "INSERT INTO chat_sessions (session_id, created_at) VALUES (?, ?)",
            (session_id, _now_iso()),
        )
    return session_id


def add_message(session_id: str, role: str, content: str, case_id: Optional[str] = None) -> None:
    with get_conn() as conn:
        conn.execute(
            "INSERT INTO chat_messages (session_id, role, content, created_at, case_id) VALUES (?, ?, ?, ?, ?)",
            (session_id, role, content, _now_iso(), case_id),
        )


def get_messages(session_id: str, limit: int = 12) -> List[Dict]:
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT role, content, created_at, case_id FROM chat_messages WHERE session_id = ? ORDER BY id DESC LIMIT ?",
            (session_id, limit),
        ).fetchall()
    # return oldest -> newest
    data = [dict(r) for r in rows]
    return list(reversed(data))