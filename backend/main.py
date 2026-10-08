"""
MyMind — FastAPI Backend
"""
from dotenv import load_dotenv
load_dotenv()

from fastapi import FastAPI, UploadFile, File, HTTPException, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse, RedirectResponse
from pydantic import BaseModel
from typing import Optional
import json, shutil, tempfile, os
from pathlib import Path
from pydantic import field_validator

from agent import MyMindAgent
from calendar_client import CalendarClient

app = FastAPI(title="MyMind Agent", version="2.0.0")
FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:5174")
ALLOWED_UPLOAD_SUFFIXES = {".pdf", ".txt", ".md"}
MAX_UPLOAD_BYTES = 20 * 1024 * 1024

app.add_middleware(
    CORSMiddleware,
    allow_origins=[FRONTEND_URL],
    allow_methods=["*"],
    allow_headers=["*"],
)

agent    = MyMindAgent()
calendar = agent.calendar  # shared instance


class ChatRequest(BaseModel):
    message: str
    ingest_source: Optional[str] = ""

    @field_validator("ingest_source")
    @classmethod
    def only_urls(cls, v):
        # Local file paths must never come from the client (arbitrary file read);
        # uploads go through /upload, which creates its own temp file.
        if v and not v.startswith(("http://", "https://")):
            raise ValueError("ingest_source must be an http(s) URL")
        return v or ""


# ─── Health ───────────────────────────────────────────────────────────────────
@app.get("/health")
def health():
    return {
        "status": "ok",
        "kbs": agent.list_kbs(),
        "integrations": agent.integration_status(),
    }


# ─── Chat ─────────────────────────────────────────────────────────────────────
@app.post("/chat")
def chat(req: ChatRequest):
    try:
        return agent.run(req.message, req.ingest_source)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/chat/stream")
def chat_stream(req: ChatRequest):
    """Streaming chat — SSE with per-node visibility.

    Sync generator on purpose: Starlette iterates it in a threadpool, so the
    blocking LLM calls don't stall the event loop.
    """
    def generate():
        try:
            for event in agent.stream(req.message, req.ingest_source):
                for node_name, state in event.items():
                    result = state.get("result", {})
                    payload = {
                        "node":       node_name,
                        "intent":     state.get("intent", ""),
                        "kb":         state.get("kb", ""),
                        "result":     result,
                        "error":      state.get("error", ""),
                        "notion_url": result.get("notion_url", ""),
                    }
                    msgs = state.get("messages", [])
                    if msgs and msgs[-1]["role"] == "assistant":
                        payload["answer"] = msgs[-1]["content"]
                    yield f"data: {json.dumps(payload, ensure_ascii=False)}\n\n"
        except Exception as e:
            yield f"data: {json.dumps({'error': str(e)})}\n\n"
        yield "data: [DONE]\n\n"

    return StreamingResponse(generate(), media_type="text/event-stream")


# ─── Upload ───────────────────────────────────────────────────────────────────
@app.post("/upload")
def upload_file(file: UploadFile = File(...)):
    filename = Path(file.filename or "upload").name
    suffix = Path(filename).suffix.lower()
    if suffix not in ALLOWED_UPLOAD_SUFFIXES:
        raise HTTPException(status_code=400, detail=f"Unsupported file type: {suffix or 'none'}")
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        shutil.copyfileobj(file.file, tmp)
        tmp_path = tmp.name
    try:
        if os.path.getsize(tmp_path) > MAX_UPLOAD_BYTES:
            raise HTTPException(status_code=413, detail="File too large (max 20 MB)")
        return agent.run(
            f"請將這份文件加入知識庫：{filename}",
            ingest_source=tmp_path,
            source_name=filename,
        )
    finally:
        os.unlink(tmp_path)


# ─── Knowledge bases ─────────────────────────────────────────────────────────
@app.get("/kbs")
def list_kbs():
    return {"kbs": agent.list_kbs()}


# ─── Google Calendar OAuth ────────────────────────────────────────────────────
@app.get("/auth/google")
async def auth_google():
    """Start the Google Calendar OAuth flow. Returns the authorization URL."""
    if not calendar.credentials_exist:
        raise HTTPException(
            status_code=400,
            detail=(
                "google_credentials.json not found. "
                "Download OAuth credentials from Google Cloud Console and place "
                "it in the backend directory."
            ),
        )
    try:
        auth_url = calendar.start_oauth_flow()
        return {"auth_url": auth_url}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/auth/google/callback")
def auth_google_callback(
    request: Request,
    state:   str = Query(...),
):
    """Handle Google OAuth2 callback, save token, redirect to frontend."""
    # Pass the full URL so oauthlib can extract code and validate state
    authorization_response = str(request.url).replace("https://", "http://")
    success, err = calendar.handle_oauth_callback(authorization_response, state)
    if success:
        return RedirectResponse(f"{FRONTEND_URL}?calendar_auth=success")
    raise HTTPException(status_code=400, detail=f"Google OAuth callback failed: {err}")


@app.get("/auth/google/status")
async def auth_google_status():
    """Return current Google Calendar authentication state."""
    return calendar.status()
