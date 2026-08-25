"""
In-memory session store: conversation history (rolling window) and
per-session user profile. Swap for SQLite later without changing the
public functions below.
"""

import threading
from typing import List, Dict, Any

MAX_HISTORY = 40

_lock = threading.Lock()
_sessions: Dict[str, Dict[str, Any]] = {}


def _ensure_session(session_id: str):
    if session_id not in _sessions:
        _sessions[session_id] = {
            "history": [],  # list of {"role": "user"/"assistant", "content": str}
            "profile": {
                "exam_type": None,
                "exam_date": None,
                "study_plan": None,
            },
        }


def get_history(session_id: str) -> List[Dict[str, str]]:
    with _lock:
        _ensure_session(session_id)
        return list(_sessions[session_id]["history"])


def append_message(session_id: str, role: str, content: str):
    with _lock:
        _ensure_session(session_id)
        history = _sessions[session_id]["history"]
        history.append({"role": role, "content": content})
        if len(history) > MAX_HISTORY:
            del history[: len(history) - MAX_HISTORY]


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


def reset_session(session_id: str):
    with _lock:
        _sessions[session_id] = {
            "history": [],
            "profile": {"exam_type": None, "exam_date": None, "study_plan": None},
        }
