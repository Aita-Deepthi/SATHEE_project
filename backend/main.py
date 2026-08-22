import os
import uuid
from pathlib import Path

from dotenv import load_dotenv
load_dotenv(Path(__file__).parent / ".env")

import logging

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel

from agent import get_reply
from session_store import reset_session

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("sathee-agent")

app = FastAPI(title="SATHEE Guidance AI Agent")


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    # Log the full traceback to the terminal and return a readable message
    # to the browser instead of a bare "500 Internal Server Error".
    logger.exception("Unhandled error on %s", request.url.path)
    return JSONResponse(status_code=500, content={"detail": str(exc)})

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

FRONTEND_DIR = Path(__file__).parent.parent / "frontend"


class ChatRequest(BaseModel):
    session_id: str | None = None
    message: str


class ChatResponse(BaseModel):
    session_id: str
    reply: str


@app.post("/api/chat", response_model=ChatResponse)
def chat(req: ChatRequest):
    session_id = req.session_id or str(uuid.uuid4())
    reply = get_reply(session_id, req.message)
    return ChatResponse(session_id=session_id, reply=reply)


@app.post("/api/reset/{session_id}")
def reset(session_id: str):
    reset_session(session_id)
    return {"status": "ok"}


@app.get("/health")
def health():
    return {"status": "ok"}


# Serve the frontend at "/" so you can just open http://localhost:8000
@app.get("/")
def index():
    return FileResponse(FRONTEND_DIR / "index.html")


app.mount("/static", StaticFiles(directory=FRONTEND_DIR), name="static")
