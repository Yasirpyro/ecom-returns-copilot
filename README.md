
# ecom-returns-copilot

An AI-powered returns & warranty assistant with a customer chat experience and a reviewer dashboard. Built with FastAPI, LangGraph, and a Vite + React frontend.

---

## Contents

- Overview
- Architecture
- Features
- Tech Stack
- Project Structure
- API Overview
- Setup (Windows)
- Environment Variables
- Cloudinary Photo Storage
- Running Locally
- Deployment Notes
- Troubleshooting
- Security Notes

---

## Overview

This project provides a complete workflow for returns and warranty claims:

- Customers chat with the assistant and submit requests.
- The system escalates cases to human review when needed.
- Reviewers approve/deny and finalize the customer response.
- Customers receive the final response automatically in chat.

---

## Architecture

- **Backend**: FastAPI + LangGraph for decision flows, SQLite for persistence, ChromaDB for policy retrieval.
- **Frontend**: Vite + React + TypeScript for customer chat and reviewer dashboard.
- **Storage**: Cloudinary for customer photo uploads (production-grade storage on Render).
- **Auth**: HTTP Basic Auth for reviewer endpoints only.

---

## Features

- Customer chat with order lookup and policy-aware responses.
- Human-in-the-loop (HITL) escalation to reviewer.
- Photo upload workflow for warranty evidence.
- Reviewer dashboard with AI recommendation + citations.
- Final response generation and automatic delivery to customer chat.
- Session-based case locking to prevent duplicate cases.

---

## Tech Stack

- **Backend**: FastAPI, LangGraph, LangChain, SQLite, ChromaDB
- **Frontend**: React 18, Vite, TypeScript, shadcn/ui
- **LLM**: OpenRouter (runtime), Ollama (local embeddings)
- **Storage**: Cloudinary (images)
- **Deployment**: Render (API), Netlify (frontend)

---

## Project Structure

```
backend/
	app/
		api/            # FastAPI routes
		cases/          # Case persistence
		chat/           # Chat sessions
		graph/          # LangGraph nodes
		policies/       # Policy docs
		rag/            # Retrieval logic
		tools/          # Utilities
frontend/
	code-companion-main/
		src/            # React app
		public/         # Icons + static assets
```

---

## API Overview

- `POST /chat/start` — start a chat session
- `POST /chat/{session_id}` — send a message
- `POST /cases/{case_id}/photos` — upload photos
- `POST /cases/{case_id}/decision` — reviewer decision (auth)
- `POST /cases/{case_id}/finalize` — finalize case (auth)

---

## Setup (Windows)

ChromaDB requires native wheels (not currently available for Python 3.14 on Windows). Use **Python 3.11–3.13**.

From the repo root:

```powershell
py -3.11 -m venv .venv
\.venv\Scripts\Activate.ps1
python -m pip install -U pip setuptools wheel
python -m pip install -r backend\requirements.txt
```

Quick sanity check:

```powershell
python -c "import chromadb; import chroma_hnswlib; import numpy; print('ok')"
```

---

## Environment Variables

Create a `backend/.env` file. Required variables:

```
OPENROUTER_API_KEY=your_key_here
```

Recommended:

```
OPENROUTER_BASE_URL=https://openrouter.ai/api/v1
OPENROUTER_MODEL=x-ai/grok-4.1-fast
OPENROUTER_APP_URL=http://localhost:8000
OPENROUTER_APP_NAME=ecom-returns-copilot
```

Reviewer auth (protects reviewer endpoints):

```
REVIEWER_BASIC_USER=reviewer
REVIEWER_BASIC_PASS=strong-password
```

Storage:

```
CHROMA_DIR=app/storage/chroma
POLICIES_DIR=app/policies
DB_PATH=app/storage/cases.db
```

---

## Cloudinary Photo Storage

Use Cloudinary for persistent photo storage (recommended for production):

1. Create a free account at https://cloudinary.com
2. Copy the **API environment variable** from the dashboard
3. Add to `backend/.env`:

```
CLOUDINARY_URL=cloudinary://api_key:api_secret@cloud_name
```

---

## Running Locally

Backend:

```powershell
cd backend
uvicorn app.main:app --reload --port 8000
```

Frontend:

```powershell
cd frontend\code-companion-main
npm install
npm run dev
```

---

## Deployment Notes

- **Backend**: Render
	- Set all environment variables in Render → Environment
- **Frontend**: Netlify
	- Base directory: `frontend/code-companion-main`
	- Build command: `npm run build`
	- Publish directory: `dist`

---

## Troubleshooting

**Photos not loading on Render**
- Ensure `CLOUDINARY_URL` is set on Render
- Upload a new photo after setting env vars

**Customer chat not receiving final response**
- Ensure backend is updated and polling is enabled
- Confirm the case status is `closed`

**CORS errors**
- Add your frontend URL to `CORS_ORIGINS` in `backend/.env`

---

## Security Notes

- Never commit API keys to Git.
- Rotate exposed secrets immediately.
- Use strong reviewer credentials in production.
