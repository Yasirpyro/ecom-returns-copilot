
# ecom-returns-copilot

## Windows setup (recommended)

ChromaDB requires native wheels (not currently available for Python 3.14 on Windows).
Use **Python 3.11–3.13**.

From the repo root:

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -U pip setuptools wheel
python -m pip install -r backend\requirements.txt
```

Quick sanity check:

```powershell
python -c "import chromadb; import chroma_hnswlib; import numpy; print('ok')"
```

## OpenRouter configuration

Create an environment file from [backend/.env.example](backend/.env.example) and set your key:

```powershell
Copy-Item backend\.env.example backend\.env
# then edit backend\.env and set OPENROUTER_API_KEY
```

Required:
- `OPENROUTER_API_KEY`

Optional (recommended):
- `OPENROUTER_APP_URL` (default: http://localhost:8000)
- `OPENROUTER_APP_NAME` (default: ecom-returns-copilot)

## Run the API

```powershell
cd backend
uvicorn app.main:app --reload --port 8000
```

## Example request flow

1) Start a chat session:

```
POST /chat/start
```

2) Send a chat message:

```
POST /chat/{session_id}
```

3) Upload photos for a case (if required):

```
POST /cases/{case_id}/photos
```

4) Reviewer decision:

```
POST /cases/{case_id}/decision
```

5) Finalize (generates final customer reply + next actions):

```
POST /cases/{case_id}/finalize
```
