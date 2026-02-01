import os
from pathlib import Path
from typing import Optional
from datetime import datetime

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from fastapi.responses import Response
from dotenv import load_dotenv

from app.cases.repo import (
    add_photo,
    get_case,
    list_cases,
    set_human_decision,
    update_status,
)
from app.cases.db import get_conn
from app.security.basic_auth import require_reviewer_basic_auth

load_dotenv()

router = APIRouter(prefix="/cases", tags=["cases"])

UPLOAD_DIR = Path(os.getenv("UPLOAD_DIR", "app/storage/uploads"))
PUBLIC_BASE_URL = os.getenv("PUBLIC_BASE_URL", "http://localhost:8000")


@router.get("", dependencies=[Depends(require_reviewer_basic_auth)])
def cases_list(status: Optional[str] = None):
    return {"data": list_cases(status=status)}


@router.get("/{case_id}", dependencies=[Depends(require_reviewer_basic_auth)])
def case_detail(case_id: str):
    case = get_case(case_id)
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")
    return case


@router.post("/{case_id}/photos")
async def upload_photo(case_id: str, file: UploadFile = File(...)):
    case = get_case(case_id)
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")

    # basic content type check
    if file.content_type not in {"image/jpeg", "image/png", "image/webp"}:
        raise HTTPException(status_code=400, detail="Only jpg/png/webp images are allowed")

    safe_name = Path(file.filename or "upload").name
    content = await file.read()
    
    # Store photo in database (Render has ephemeral storage)
    with get_conn() as conn:
        cursor = conn.execute(
            """
            INSERT INTO photos (case_id, filename, content_type, data, created_at)
            VALUES (?, ?, ?, ?, ?)
            """,
            (case_id, safe_name, file.content_type, content, datetime.utcnow().isoformat())
        )
        photo_id = cursor.lastrowid
    
    # Generate URL to serve photo from database
    photo_url = f"{PUBLIC_BASE_URL}/cases/{case_id}/photos/{photo_id}"
    add_photo(case_id, photo_url)

    # After photo upload, move to human review if photos were required
    if case.get("photos_required"):
        update_status(case_id, "ready_for_human_review")

    return {"case_id": case_id, "photo_url": photo_url}


@router.get("/{case_id}/photos/{photo_id}")
def get_photo(case_id: str, photo_id: int):
    """Serve photo from database (for Render's ephemeral storage)"""
    with get_conn() as conn:
        row = conn.execute(
            "SELECT filename, content_type, data FROM photos WHERE id = ? AND case_id = ?",
            (photo_id, case_id)
        ).fetchone()
        
        if not row:
            raise HTTPException(status_code=404, detail="Photo not found")
        
        return Response(
            content=row["data"],
            media_type=row["content_type"],
            headers={"Content-Disposition": f'inline; filename="{row["filename"]}"'}
        )


@router.post("/{case_id}/decision", dependencies=[Depends(require_reviewer_basic_auth)])
def human_decision(case_id: str, decision: str, notes: Optional[str] = None):
    """
    decision must be one of:
    - approved
    - denied
    - more_info_requested
    """
    case = get_case(case_id)
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")

    if decision not in {"approved", "denied", "more_info_requested"}:
        raise HTTPException(status_code=400, detail="Invalid decision")

    set_human_decision(case_id, decision, notes)

    return {"case_id": case_id, "status": decision}