import os
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, File, HTTPException, UploadFile
from fastapi.responses import FileResponse
from dotenv import load_dotenv

from app.cases.repo import (
    add_photo,
    get_case,
    list_cases,
    set_human_decision,
    set_final_reply,
    update_status,
)

load_dotenv()

router = APIRouter(prefix="/cases", tags=["cases"])

UPLOAD_DIR = Path(os.getenv("UPLOAD_DIR", "app/storage/uploads"))
PUBLIC_BASE_URL = os.getenv("PUBLIC_BASE_URL", "http://localhost:8000")


@router.get("")
def cases_list(status: Optional[str] = None):
    return {"data": list_cases(status=status)}


@router.get("/{case_id}")
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

    case_dir = UPLOAD_DIR / case_id
    case_dir.mkdir(parents=True, exist_ok=True)

    safe_name = Path(file.filename or "upload").name
    out_path = case_dir / safe_name

    content = await file.read()
    out_path.write_bytes(content)

    # public URL served by FastAPI static mount (added in main.py)
    photo_url = f"{PUBLIC_BASE_URL}/uploads/{case_id}/{safe_name}"
    add_photo(case_id, photo_url)

    # After photo upload, move to human review if photos were required
    # (you can require 1+ photos; for demo, 1 is enough)
    if case.get("photos_required"):
        update_status(case_id, "ready_for_human_review")

    return {"case_id": case_id, "photo_url": photo_url}


@router.post("/{case_id}/decision")
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