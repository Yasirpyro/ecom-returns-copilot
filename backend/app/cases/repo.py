import json
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from app.cases.db import get_conn


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def create_case(payload: Dict[str, Any]) -> str:
    case_id = str(uuid.uuid4())
    with get_conn() as conn:
        conn.execute(
            """
            INSERT INTO cases (
              case_id, order_id, reason, customer_message, wants_store_credit,
              photos_required, status, created_at,
              ai_decision_json, ai_audit_json, policy_citations_json, order_facts_json,
              photo_urls_json
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                case_id,
                payload["order_id"],
                payload["reason"],
                payload.get("customer_message"),
                1 if payload.get("wants_store_credit") else 0,
                1 if payload.get("photos_required") else 0,
                payload["status"],
                _now_iso(),
                json.dumps(payload.get("ai_decision") or {}),
                json.dumps(payload.get("ai_audit") or {}),
                json.dumps(payload.get("policy_citations") or []),
                json.dumps(payload.get("order_facts") or {}),
                json.dumps(payload.get("photo_urls") or []),
            ),
        )
    return case_id


def get_case(case_id: str) -> Optional[Dict[str, Any]]:
    with get_conn() as conn:
        row = conn.execute("SELECT * FROM cases WHERE case_id = ?", (case_id,)).fetchone()
        if not row:
            return None
        d = dict(row)
        for k in [
            "ai_decision_json",
            "ai_audit_json",
            "policy_citations_json",
            "order_facts_json",
            "photo_urls_json",
            "next_actions_json",
        ]:
            d[k] = json.loads(d[k]) if d.get(k) else None
        return d


def list_cases(status: Optional[str] = None) -> List[Dict[str, Any]]:
    with get_conn() as conn:
        if status:
            rows = conn.execute(
                "SELECT case_id, order_id, reason, status, created_at, photos_required FROM cases WHERE status = ? ORDER BY created_at DESC",
                (status,),
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT case_id, order_id, reason, status, created_at, photos_required FROM cases ORDER BY created_at DESC"
            ).fetchall()
        return [dict(r) for r in rows]


def add_photo(case_id: str, photo_url: str) -> None:
    case = get_case(case_id)
    if not case:
        raise KeyError("case_not_found")
    photos = case.get("photo_urls_json") or []
    photos.append(photo_url)
    with get_conn() as conn:
        conn.execute("UPDATE cases SET photo_urls_json = ? WHERE case_id = ?", (json.dumps(photos), case_id))


def update_status(case_id: str, status: str) -> None:
    with get_conn() as conn:
        conn.execute("UPDATE cases SET status = ? WHERE case_id = ?", (status, case_id))


def set_human_decision(case_id: str, decision: str, notes: str | None) -> None:
    with get_conn() as conn:
        conn.execute(
            """
            UPDATE cases
            SET human_decision = ?, human_notes = ?, reviewed_at = ?, status = ?
            WHERE case_id = ?
            """,
            (decision, notes, _now_iso(), decision, case_id),
        )


def set_final_outcome(case_id: str, reply: str, next_actions: List[Dict[str, Any]]) -> None:
    with get_conn() as conn:
        conn.execute(
            """
            UPDATE cases
            SET final_customer_reply = ?, next_actions_json = ?, status = ?
            WHERE case_id = ?
            """,
            (reply, json.dumps(next_actions), "closed", case_id),
        )
def set_final_reply(case_id: str, reply: str) -> None:
    # Backward-compatible helper
    set_final_outcome(case_id, reply, next_actions=[])