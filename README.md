# DukonPro Backend

Core setup for the FastAPI backend.

## Run

```powershell
.\.venv\Scripts\activate
uvicorn app.main:app --reload
```

Health check:

```text
GET http://127.0.0.1:8000/api/v1/health
```
