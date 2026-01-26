import os
import secrets

from dotenv import load_dotenv
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBasic, HTTPBasicCredentials

load_dotenv()

security = HTTPBasic()

REVIEWER_BASIC_USER = os.getenv("REVIEWER_BASIC_USER", "")
REVIEWER_BASIC_PASS = os.getenv("REVIEWER_BASIC_PASS", "")


def require_reviewer_basic_auth(
    credentials: HTTPBasicCredentials = Depends(security),
) -> None:
    if not REVIEWER_BASIC_USER or not REVIEWER_BASIC_PASS:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Server missing REVIEWER_BASIC_USER/REVIEWER_BASIC_PASS configuration",
        )

    username_ok = secrets.compare_digest(credentials.username, REVIEWER_BASIC_USER)
    password_ok = secrets.compare_digest(credentials.password, REVIEWER_BASIC_PASS)

    if not (username_ok and password_ok):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Unauthorized",
            headers={"WWW-Authenticate": "Basic"},
        )
