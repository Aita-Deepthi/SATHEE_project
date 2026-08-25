import uuid
from datetime import date

from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

import agent
import session_store
from study_plan import get_today_task
from rag_pipeline import search_knowledge

app = FastAPI(title="SATHEE Guidance Agent")


class ChatRequest(BaseModel):
    session_id: str
    message: str


class ResetRequest(BaseModel):
    session_id: str


@app.post("/api/chat")
async def chat(req: ChatRequest):
    reply = agent.chat(req.session_id, req.message)
    return {"reply": reply}


@app.post("/api/reset")
async def reset(req: ResetRequest):
    session_store.reset_session(req.session_id)
    return {"status": "ok"}


@app.get("/api/session/new")
async def new_session():
    return {"session_id": str(uuid.uuid4())}


@app.get("/api/study-plan/{session_id}")
async def get_study_plan(session_id: str):
    profile = session_store.get_profile(session_id)
    plan = profile.get("study_plan")
    if not plan:
        return {"plan": None}
    return {"plan": plan, "today": get_today_task(plan)}


@app.get("/api/study-plan/{session_id}/today")
async def get_today(session_id: str):
    profile = session_store.get_profile(session_id)
    plan = profile.get("study_plan")
    if not plan:
        return {"today": None, "message": "No plan generated yet."}
    today_task = get_today_task(plan)
    if not today_task:
        return {"today": None, "message": "Today is outside the plan's date range."}
    return {"today": today_task}


@app.get("/api/knowledge/search")
async def knowledge_search(q: str, limit: int = 4):
    """Inspect the passages the agent can retrieve for a question."""
    return {"results": search_knowledge(q, max(1, min(limit, 10)))}


app.mount("/static", StaticFiles(directory="static"), name="static")


@app.get("/")
async def root():
    return FileResponse("static/index.html")
