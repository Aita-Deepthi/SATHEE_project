"""Local account storage for SATHEE.

Passwords are stored as salted scrypt hashes. The SQLite database stores no
plaintext passwords or other authentication secrets.
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import os
import re
import secrets
import sqlite3
from pathlib import Path

_DB_PATH = Path(os.getenv("SATHEE_AUTH_DB", Path(__file__).parent / "sathee_auth.db"))
_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def _connection() -> sqlite3.Connection:
    connection = sqlite3.connect(_DB_PATH)
    connection.row_factory = sqlite3.Row
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            email TEXT NOT NULL UNIQUE COLLATE NOCASE,
            password_hash TEXT NOT NULL,
            session_id TEXT NOT NULL,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        )
        """
    )
    connection.commit()
    return connection


def _normalize_email(email: str) -> str:
    normalized = email.strip().lower()
    if not _EMAIL_RE.fullmatch(normalized):
        raise ValueError("Enter a valid email address.")
    return normalized


def _hash_password(password: str) -> str:
    salt = secrets.token_bytes(16)
    digest = hashlib.scrypt(password.encode("utf-8"), salt=salt, n=2**14, r=8, p=1)
    return "scrypt$" + base64.b64encode(salt).decode() + "$" + base64.b64encode(digest).decode()


def _verify_password(password: str, stored_hash: str) -> bool:
    try:
        _, salt_text, digest_text = stored_hash.split("$")
        salt = base64.b64decode(salt_text)
        expected = base64.b64decode(digest_text)
        actual = hashlib.scrypt(password.encode("utf-8"), salt=salt, n=2**14, r=8, p=1)
        return hmac.compare_digest(actual, expected)
    except (ValueError, TypeError):
        return False


def register(email: str, password: str) -> dict[str, str]:
    normalized = _normalize_email(email)
    if len(password) < 8:
        raise ValueError("Password must contain at least 8 characters.")
    session_id = secrets.token_urlsafe(32)
    connection = _connection()
    try:
        connection.execute(
            "INSERT INTO users (email, password_hash, session_id) VALUES (?, ?, ?)",
            (normalized, _hash_password(password), session_id),
        )
        connection.commit()
    except sqlite3.IntegrityError as exc:
        raise ValueError("This email address has already been used.") from exc
    finally:
        connection.close()
    return {"email": normalized, "session_id": session_id}


def login(email: str, password: str) -> dict[str, str]:
    normalized = _normalize_email(email)
    connection = _connection()
    try:
        user = connection.execute(
            "SELECT email, password_hash, session_id FROM users WHERE email = ?",
            (normalized,),
        ).fetchone()
    finally:
        connection.close()
    if not user or not _verify_password(password, user["password_hash"]):
        raise ValueError("Email or password is incorrect.")
    return {"email": user["email"], "session_id": user["session_id"]}


def get_session_user(session_id: str) -> dict[str, str] | None:
    if not session_id:
        return None
    connection = _connection()
    try:
        user = connection.execute(
            "SELECT email, session_id FROM users WHERE session_id = ?",
            (session_id,),
        ).fetchone()
    finally:
        connection.close()
    if not user:
        return None
    return {"email": user["email"], "session_id": user["session_id"]}
