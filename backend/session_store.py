"""Session store with an in-memory cache and optional Pinecone persistence."""

import threading
from typing import List, Dict, Any

import pinecone_store

MAX_HISTORY = 40

_lock = threading.Lock()
_sessions: Dict[str, Dict[str, Any]] = {}


def _ensure_session(session_id: str):
    if session_id not in _sessions:
        persisted = pinecone_store.load_session(session_id)
        if persisted:
            history, profile = persisted
        else:
            history = []
            profile = {"exam_type": None, "exam_date": None, "study_plan": None}
        _sessions[session_id] = {
            "history": history[-MAX_HISTORY:],
            "profile": profile,
            "history_offset": profile.pop("_history_sequence", 0),
        }


def get_history(session_id: str) -> List[Dict[str, str]]:
    with _lock:
        _ensure_session(session_id)
        return list(_sessions[session_id]["history"])


def hydrate_history(session_id: str, history: List[Dict[str, str]]) -> None:
    """Replace the agent context with the selected conversation's history."""
    with _lock:
        _ensure_session(session_id)
        _sessions[session_id]["history"] = history[-MAX_HISTORY:]


def append_message(session_id: str, role: str, content: str):
    with _lock:
        _ensure_session(session_id)
        history = _sessions[session_id]["history"]
        history.append({"role": role, "content": content})
        if len(history) > MAX_HISTORY:
            del history[: len(history) - MAX_HISTORY]
        sequence = len(history) + _sessions[session_id].get("history_offset", 0)
        _sessions[session_id]["history_offset"] = sequence
        profile = dict(_sessions[session_id]["profile"])
    pinecone_store.save_message(session_id, sequence, role, content)
    pinecone_store.save_profile(session_id, profile)


def get_profile(session_id: str) -> Dict[str, Any]:
    with _lock:
        _ensure_session(session_id)
        return _sessions[session_id]["profile"]


def update_profile(session_id: str, updates: Dict[str, Any]):
    with _lock:
        _ensure_session(session_id)
        if (updates.get("exam_type") and updates["exam_type"] != _sessions[session_id]["profile"].get("exam_type")) or (
            updates.get("exam_date") and updates["exam_date"] != _sessions[session_id]["profile"].get("exam_date")
        ):
            _sessions[session_id]["profile"]["study_plan"] = None
        _sessions[session_id]["profile"].update(
            {k: v for k, v in updates.items() if v is not None}
        )
        profile = dict(_sessions[session_id]["profile"])
    pinecone_store.save_profile(session_id, profile)


def reset_session(session_id: str):
    with _lock:
        _sessions[session_id] = {
            "history": [],
            "profile": {"exam_type": None, "exam_date": None, "study_plan": None},
        }
    pinecone_store.delete_session(session_id)
