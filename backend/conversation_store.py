"""SQLite persistence for student conversations and their messages."""

from __future__ import annotations

import os
import sqlite3
import uuid
from datetime import datetime, timezone
from pathlib import Path

DB_PATH = Path(os.getenv("SATHEE_AUTH_DB", Path(__file__).parent / "sathee_auth.db"))


def _connection() -> sqlite3.Connection:
    connection = sqlite3.connect(DB_PATH)
    connection.row_factory = sqlite3.Row
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS conversations (
            id TEXT PRIMARY KEY,
            email TEXT NOT NULL COLLATE NOCASE,
            title TEXT NOT NULL,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        )
        """
    )
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS conversation_messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            conversation_id TEXT NOT NULL,
            role TEXT NOT NULL CHECK (role IN ('user', 'assistant')),
            content TEXT NOT NULL,
            created_at TEXT NOT NULL,
            FOREIGN KEY (conversation_id) REFERENCES conversations(id) ON DELETE CASCADE
        )
        """
    )
    connection.commit()
    return connection


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def create(email: str, conversation_id: str | None = None) -> str:
    conversation_id = conversation_id or str(uuid.uuid4())
    now = _now()
    connection = _connection()
    try:
        connection.execute(
            "INSERT INTO conversations (id, email, title, created_at, updated_at) VALUES (?, ?, ?, ?, ?)",
            (conversation_id, email, "New chat", now, now),
        )
        connection.commit()
    finally:
        connection.close()
    return conversation_id


def list_for_user(email: str) -> list[dict[str, str]]:
    connection = _connection()
    try:
        rows = connection.execute(
            """
            SELECT id, title, created_at, updated_at
            FROM conversations
            WHERE email = ?
            ORDER BY updated_at DESC
            """,
            (email,),
        ).fetchall()
    finally:
        connection.close()
    return [dict(row) for row in rows]


def belongs_to_user(conversation_id: str, email: str) -> bool:
    connection = _connection()
    try:
        row = connection.execute(
            "SELECT 1 FROM conversations WHERE id = ? AND email = ?",
            (conversation_id, email),
        ).fetchone()
    finally:
        connection.close()
    return row is not None


def history(conversation_id: str, email: str) -> list[dict[str, str]]:
    connection = _connection()
    try:
        rows = connection.execute(
            """
            SELECT role, content
            FROM conversation_messages
            WHERE conversation_id = ?
              AND EXISTS (
                  SELECT 1 FROM conversations
                  WHERE id = conversation_id AND email = ?
              )
            ORDER BY id
            """,
            (conversation_id, email),
        ).fetchall()
    finally:
        connection.close()
    return [dict(row) for row in rows]


def append(conversation_id: str, email: str, role: str, content: str) -> None:
    if role not in {"user", "assistant"}:
        raise ValueError("Unsupported conversation message role.")
    now = _now()
    connection = _connection()
    try:
        conversation = connection.execute(
            "SELECT title FROM conversations WHERE id = ? AND email = ?",
            (conversation_id, email),
        ).fetchone()
        if not conversation:
            raise ValueError("Conversation does not belong to this student.")
        title = conversation["title"]
        if title == "New chat" and role == "user":
            title = _title_from_message(content)
        connection.execute(
            "INSERT INTO conversation_messages (conversation_id, role, content, created_at) VALUES (?, ?, ?, ?)",
            (conversation_id, role, content, now),
        )
        connection.execute(
            "UPDATE conversations SET title = ?, updated_at = ? WHERE id = ?",
            (title, now, conversation_id),
        )
        connection.commit()
    finally:
        connection.close()


def _title_from_message(content: str) -> str:
    cleaned = " ".join(content.split())
    prefixes = (
        "can you help me with ",
        "help me with ",
        "can you ",
        "please ",
        "i want to ",
        "i need help with ",
        "tell me about ",
    )
    lowered = cleaned.lower()
    for prefix in prefixes:
        if lowered.startswith(prefix):
            cleaned = cleaned[len(prefix):]
            break
    title = cleaned.rstrip("?.! ").capitalize()
    return title[:60] or "New chat"
