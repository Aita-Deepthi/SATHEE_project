import uuid
from datetime import date

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

import agent
import auth
import conversation_store
import session_store
from study_plan import get_today_task
from rag_pipeline import search_knowledge

app = FastAPI(title="SATHEE Guidance Agent")


class ChatRequest(BaseModel):
    session_id: str
    message: str
    conversation_id: str | None = None


class ResetRequest(BaseModel):
    session_id: str
    conversation_id: str | None = None


class AuthRequest(BaseModel):
    email: str
    password: str


def _authenticated_session(session_id: str) -> dict[str, str]:
    user = auth.get_session_user(session_id)
    if not user:
        raise HTTPException(
            status_code=401,
            detail="Please log in with your email address before using the chatbot.",
        )
    return user


def _conversation_id(user: dict[str, str], conversation_id: str | None) -> str:
    selected = conversation_id or user["session_id"]
    if not conversation_store.belongs_to_user(selected, user["email"]):
        raise HTTPException(status_code=404, detail="Conversation not found.")
    return selected


def _sync_legacy_history(conversation_id: str, email: str) -> None:
    if conversation_store.history(conversation_id, email):
        return
    for message in session_store.get_history(conversation_id):
        conversation_store.append(
            conversation_id,
            email,
            message["role"],
            message["content"],
        )


@app.post("/api/auth/register")
async def register(req: AuthRequest):
    try:
        result = auth.register(req.email, req.password)
        result["conversation_id"] = conversation_store.create(result["email"], result["session_id"])
        return result
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@app.post("/api/auth/login")
async def login(req: AuthRequest):
    try:
        result = auth.login(req.email, req.password)
        conversations = conversation_store.list_for_user(result["email"])
        result["conversation_id"] = conversations[0]["id"] if conversations else conversation_store.create(result["email"], result["session_id"])
        return result
    except ValueError as exc:
        raise HTTPException(status_code=401, detail=str(exc)) from exc


@app.get("/api/auth/session/{session_id}")
async def auth_session(session_id: str, conversation_id: str | None = None):
    user = _authenticated_session(session_id)
    conversations = conversation_store.list_for_user(user["email"])
    if not conversations:
        conversations = [{"id": conversation_store.create(user["email"], user["session_id"])}]
    selected = _conversation_id(user, conversation_id or conversations[0]["id"])
    _sync_legacy_history(selected, user["email"])
    return {
        **user,
        "conversation_id": selected,
        "profile": session_store.get_profile(selected),
    }


@app.get("/api/chat/history/{session_id}")
async def chat_history(session_id: str, conversation_id: str | None = None):
    user = _authenticated_session(session_id)
    selected = _conversation_id(user, conversation_id)
    history = conversation_store.history(selected, user["email"])
    session_store.hydrate_history(selected, history)
    return {"conversation_id": selected, "history": history}


@app.get("/api/chat/conversations/{session_id}")
async def conversations(session_id: str):
    user = _authenticated_session(session_id)
    return {"conversations": conversation_store.list_for_user(user["email"])}


@app.post("/api/chat/conversations/{session_id}")
async def new_conversation(session_id: str):
    user = _authenticated_session(session_id)
    return {"conversation_id": conversation_store.create(user["email"])}


@app.post("/api/chat")
async def chat(req: ChatRequest):
    user = _authenticated_session(req.session_id)
    selected = _conversation_id(user, req.conversation_id)
    conversation_history = conversation_store.history(selected, user["email"])
    session_store.hydrate_history(selected, conversation_history)
    conversation_store.append(selected, user["email"], "user", req.message)
    reply = agent.chat(selected, req.message)
    conversation_store.append(selected, user["email"], "assistant", reply)
    return {"reply": reply}


@app.post("/api/reset")
async def reset(req: ResetRequest):
    user = _authenticated_session(req.session_id)
    selected = _conversation_id(user, req.conversation_id)
    session_store.reset_session(selected)
    return {"status": "ok"}


@app.get("/api/session/new")
async def new_session():
    return {"session_id": str(uuid.uuid4())}


@app.get("/api/study-plan/{session_id}")
async def get_study_plan(session_id: str, conversation_id: str | None = None):
    user = _authenticated_session(session_id)
    selected = _conversation_id(user, conversation_id)
    profile = session_store.get_profile(selected)
    plan = profile.get("study_plan")
    if not plan:
        return {"plan": None}
    return {"plan": plan, "today": get_today_task(plan)}


@app.get("/api/study-plan/{session_id}/today")
async def get_today(session_id: str, conversation_id: str | None = None):
    user = _authenticated_session(session_id)
    selected = _conversation_id(user, conversation_id)
    profile = session_store.get_profile(selected)
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
