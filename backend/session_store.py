"""
Very small in-memory session store.

Good enough for local development / a single-process demo. Sessions live
only as long as the server process runs. To make this persistent later,
swap this module for a SQLite-backed version (mentioned as a next step
in README.md) without changing the API other modules use.
"""

from typing import Dict, List, Optional
from threading import Lock

_lock = Lock()

# session_id -> {"profile": {...}, "history": [{"role": ..., "content": ...}, ...]}
_sessions: Dict[str, dict] = {}

DEFAULT_PROFILE = {
    "user_type": None,       # "student" | "well_wisher"
    "exam": None,             # "JEE" | "NEET" | "Other"
    "class_level": None,      # "9" | "10" | "11" | "12" | "Dropper"
    "language": None,         # "Hindi" | "English" | ...
    "hours_per_day": None,
    "weak_subjects": None,
    "strong_subjects": None,
    "exam_year": None,
}


def get_session(session_id: str) -> dict:
    with _lock:
        if session_id not in _sessions:
            _sessions[session_id] = {
                "profile": dict(DEFAULT_PROFILE),
                "history": [],
            }
        return _sessions[session_id]


def append_message(session_id: str, role: str, content: str) -> None:
    session = get_session(session_id)
    session["history"].append({"role": role, "content": content})
    # Keep history bounded so prompts don't grow unbounded in a long session.
    if len(session["history"]) > 40:
        session["history"] = session["history"][-40:]


def update_profile(session_id: str, updates: Dict[str, Optional[str]]) -> None:
    session = get_session(session_id)
    for key, value in updates.items():
        if key in session["profile"] and value:
            session["profile"][key] = value


def get_history(session_id: str) -> List[dict]:
    return get_session(session_id)["history"]


def get_profile(session_id: str) -> dict:
    return get_session(session_id)["profile"]


def reset_session(session_id: str) -> None:
    with _lock:
        _sessions[session_id] = {
            "profile": dict(DEFAULT_PROFILE),
            "history": [],
        }
