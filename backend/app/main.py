import os
from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pathlib import Path

from app.api.routes import router as core_router
from app.api.cases_routes import router as cases_router
from app.api.chat_routes import router as chat_router
from app.api.finalize_routes import router as finalize_router
from app.cases.db import init_db
from app.chat.db import init_chat_db

load_dotenv()

app = FastAPI(title="Ecommerce Returns & Refunds Copilot", version="0.1.0")

origins = os.getenv("CORS_ORIGINS", "")
allow_origins = [o.strip() for o in origins.split(",") if o.strip()] or ["*"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=allow_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Init SQLite tables
init_db()
init_chat_db()

# Serve uploaded files
upload_dir = Path(os.getenv("UPLOAD_DIR", "app/storage/uploads"))
upload_dir.mkdir(parents=True, exist_ok=True)
app.mount("/uploads", StaticFiles(directory=str(upload_dir)), name="uploads")

app.include_router(core_router)
app.include_router(cases_router)
app.include_router(chat_router)
app.include_router(finalize_router) 