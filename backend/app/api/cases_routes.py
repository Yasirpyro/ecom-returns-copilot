import os
from pathlib import Path
from typing import Optional
import cloudinary
import cloudinary.uploader

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from dotenv import load_dotenv

from app.cases.repo import (
    add_photo,
    get_case,
    list_cases,
    set_human_decision,
    update_status,
)
from app.security.basic_auth import require_reviewer_basic_auth

load_dotenv()

router = APIRouter(prefix="/cases", tags=["cases"])

# Configure Cloudinary (cloud storage for photos)
# Use CLOUDINARY_URL env var (simpler - contains all credentials in one variable)
cloudinary_url = os.getenv("CLOUDINARY_URL")

if not cloudinary_url:
    raise ValueError(
        "Missing CLOUDINARY_URL environment variable. "
        "Get it from Cloudinary dashboard → Settings → API Keys → 'API environment variable'"
    )

# Cloudinary SDK automatically parses CLOUDINARY_URL if it exists in env
# Format: cloudinary://api_key:api_secret@cloud_name


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

    # Upload to Cloudinary (cloud storage - persists across Render restarts)
    try:
        safe_name = Path(file.filename or "upload").stem
        content = await file.read()
        
        # Upload with folder organization: ecom-returns/{case_id}/{filename}
        result = cloudinary.uploader.upload(
            content,
            folder=f"ecom-returns/{case_id}",
            public_id=safe_name,
            resource_type="image"
        )
        
        photo_url = result["secure_url"]
        add_photo(case_id, photo_url)

        # After photo upload, move to human review if photos were required
        if case.get("photos_required"):
            update_status(case_id, "ready_for_human_review")

        return {"case_id": case_id, "photo_url": photo_url}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to upload photo: {str(e)}")


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