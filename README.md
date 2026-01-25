
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
