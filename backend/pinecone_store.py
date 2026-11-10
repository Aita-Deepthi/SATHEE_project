"""Pinecone persistence for SATHEE sessions.

Only the non-sensitive study profile and chat messages are stored. Authentication
credentials such as passwords, access tokens, and API keys must not be stored in
this vector index.
"""

from __future__ import annotations

import hashlib
import json
import logging
import os
import time
from typing import Any

from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)
NAMESPACE = os.getenv("PINECONE_NAMESPACE", "sathee")
DIMENSION = 256
_INDEX = None


def _response_value(response: Any, key: str, default: Any) -> Any:
    if isinstance(response, dict):
        return response.get(key, default)
    return getattr(response, key, default)


def enabled() -> bool:
    return bool(os.getenv("PINECONE_API_KEY") and os.getenv("PINECONE_INDEX_NAME"))


def _embedding(text: str) -> list[float]:
    values = [0.0] * DIMENSION
    tokens = text.lower().split()
    for token in tokens:
        digest = hashlib.sha256(token.encode("utf-8")).digest()
        index = int.from_bytes(digest[:2], "big") % DIMENSION
        values[index] += 1.0 if digest[2] % 2 else -1.0
    magnitude = sum(value * value for value in values) ** 0.5
    return [value / magnitude for value in values] if magnitude else values


def _index():
    global _INDEX
    if _INDEX is not None:
        return _INDEX
    if not enabled():
        return None

    try:
        from pinecone import Pinecone, ServerlessSpec

        client = Pinecone(api_key=os.environ["PINECONE_API_KEY"])
        index_name = os.environ["PINECONE_INDEX_NAME"]
        names = client.list_indexes().names()
        if index_name not in names:
            client.create_index(
                name=index_name,
                dimension=DIMENSION,
                metric="cosine",
                spec=ServerlessSpec(
                    cloud=os.getenv("PINECONE_CLOUD", "aws"),
                    region=os.getenv("PINECONE_REGION", "us-east-1"),
                ),
            )
        _INDEX = client.Index(index_name)
        return _INDEX
    except Exception as exc:
        logger.exception("Could not initialize Pinecone index")
        raise RuntimeError("Pinecone persistence is configured but unavailable.") from exc


def load_session(session_id: str) -> tuple[list[dict[str, str]], dict[str, Any]] | None:
    index = _index()
    if index is None:
        return None
    try:
        profile_response = index.fetch(ids=[f"profile:{session_id}"], namespace=NAMESPACE)
        vectors = _response_value(profile_response, "vectors", {})
        profile_record = vectors.get(f"profile:{session_id}")
        if not profile_record:
            return None

        metadata = profile_record.get("metadata", {})
        profile: dict[str, Any] = {
            "exam_type": metadata.get("exam_type"),
            "exam_date": metadata.get("exam_date"),
            "study_plan": json.loads(metadata["study_plan"]) if metadata.get("study_plan") else None,
            "practice_log": json.loads(metadata["practice_log"]) if metadata.get("practice_log") else [],
        }
        history_response = index.query(
            vector=_embedding(session_id),
            top_k=40,
            namespace=NAMESPACE,
            include_metadata=True,
            filter={"session_id": {"$eq": session_id}, "record_type": {"$eq": "message"}},
        )
        history = [
            {
                "role": match["metadata"]["role"],
                "content": match["metadata"]["content"],
            }
            for match in sorted(
                _response_value(history_response, "matches", []),
                key=lambda match: int(match.get("metadata", {}).get("sequence", 0)),
            )
        ]
        if history_response:
            profile["_history_sequence"] = max(
                (int(match.get("metadata", {}).get("sequence", 0))
                 for match in _response_value(history_response, "matches", [])),
                default=0,
            )
        return history, profile
    except Exception as exc:
        logger.exception("Could not load session %s from Pinecone", session_id)
        raise RuntimeError("Pinecone session loading failed.") from exc


def save_profile(session_id: str, profile: dict[str, Any]) -> None:
    index = _index()
    if index is None:
        return
    metadata: dict[str, Any] = {"record_type": "profile", "session_id": session_id}
    for key in ("exam_type", "exam_date"):
        if profile.get(key) is not None:
            metadata[key] = str(profile[key])
    if profile.get("study_plan") is not None:
        metadata["study_plan"] = json.dumps(profile["study_plan"])
    if profile.get("practice_log") is not None:
        metadata["practice_log"] = json.dumps(profile["practice_log"])
    try:
        index.upsert(
            vectors=[{
                "id": f"profile:{session_id}",
                "values": _embedding(session_id),
                "metadata": metadata,
            }],
            namespace=NAMESPACE,
        )
    except Exception as exc:
        logger.exception("Could not save profile %s to Pinecone", session_id)
        raise RuntimeError("Pinecone profile persistence failed.") from exc


def save_message(session_id: str, sequence: int, role: str, content: str) -> None:
    index = _index()
    if index is None:
        return
    try:
        index.upsert(
            vectors=[{
                "id": f"message:{session_id}:{sequence}",
                "values": _embedding(content),
                "metadata": {
                    "record_type": "message",
                    "session_id": session_id,
                    "sequence": sequence,
                    "role": role,
                    "content": content,
                    "created_at": time.time(),
                },
            }],
            namespace=NAMESPACE,
        )
    except Exception as exc:
        logger.exception("Could not save message for session %s to Pinecone", session_id)
        raise RuntimeError("Pinecone chat-history persistence failed.") from exc


def delete_session(session_id: str) -> None:
    index = _index()
    if index is None:
        return
    try:
        index.delete(
            namespace=NAMESPACE,
            filter={"session_id": {"$eq": session_id}},
        )
    except Exception as exc:
        logger.exception("Could not delete session %s from Pinecone", session_id)
        raise RuntimeError("Pinecone session deletion failed.") from exc
