"""
VICTOR Persistent Long-Term Memory & Audit Store
SQLite-backed database for structured facts, conversation history, and security action logs.
Includes automated credential filtering and category tagging.
"""

import re
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import List, Tuple, Optional, Dict, Any

from src.config.settings import DATA_DIR

DB_PATH = DATA_DIR / "victor_memory.db"

# Sensitive information patterns to block from persistent memory
SENSITIVE_PATTERNS = [
    r"(?i)\bpassword\b",
    r"(?i)\bpasswd\b",
    r"(?i)\bapi[_-]?key\b",
    r"(?i)\bsecret[_-]?key\b",
    r"(?i)\bbearer\s+[A-Za-z0-9_\-\.]{20,}",
    r"(?i)\bghp_[A-Za-z0-9]{36}\b",  # GitHub token
    r"(?i)\bAIza[0-9A-Za-z\-_]{35}\b",  # Google API Key
    r"(?i)BEGIN (?:RSA|OPENSSH|DSA|EC) PRIVATE KEY",
    r"(?i)\b(?:credit|debit)\s*card\b",
    r"\b[0-9]{4}[- ]?[0-9]{4}[- ]?[0-9]{4}[- ]?[0-9]{4}\b",  # Credit Card format
]


from contextlib import contextmanager


def connect() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA journal_mode=WAL")  # Write-Ahead Logging for high concurrency
    return conn


@contextmanager
def get_db():
    conn = connect()
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def initialize():
    """Create all required tables and migrate existing columns if they do not exist."""
    with get_db() as db:
        # Structured Memories Table
        db.execute("""
            CREATE TABLE IF NOT EXISTS memories (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                category TEXT DEFAULT 'general',
                content TEXT NOT NULL UNIQUE,
                importance INTEGER DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_accessed TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Check existing columns in memories table to perform seamless migration
        cursor = db.execute("PRAGMA table_info(memories)")
        columns = [row[1] for row in cursor.fetchall()]

        if "category" not in columns:
            db.execute("ALTER TABLE memories ADD COLUMN category TEXT DEFAULT 'general'")
        if "importance" not in columns:
            db.execute("ALTER TABLE memories ADD COLUMN importance INTEGER DEFAULT 1")
        if "last_accessed" not in columns:
            db.execute("ALTER TABLE memories ADD COLUMN last_accessed TIMESTAMP")

        # Conversation History Table
        db.execute("""
            CREATE TABLE IF NOT EXISTS conversations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT NOT NULL,
                role TEXT NOT NULL,
                content TEXT NOT NULL,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Computer Control Audit Logs
        db.execute("""
            CREATE TABLE IF NOT EXISTS action_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                action_type TEXT NOT NULL,
                target TEXT,
                status TEXT NOT NULL,
                details TEXT,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)


def contains_sensitive_info(text: str) -> bool:
    """Check if text contains passwords, credentials, or sensitive tokens."""
    for pattern in SENSITIVE_PATTERNS:
        if re.search(pattern, text):
            return True
    return False


def save_memory(content: str, category: str = "general", importance: int = 1) -> str:
    """
    Save a persistent memory fact.
    Validates content to prevent storing sensitive credentials.
    """
    content = content.strip()
    if not content:
        return "Cannot store an empty memory."

    if len(content) > 600:
        return "Memory is too lengthy. Please provide a concise summary."

    if contains_sensitive_info(content):
        return "Security Guard: Credentials, tokens, or passwords cannot be stored in memory."

    try:
        with get_db() as db:
            db.execute(
                """
                INSERT INTO memories (category, content, importance, created_at, last_accessed)
                VALUES (?, ?, ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
                """,
                (category, content, importance)
            )
        return "Memory saved successfully."
    except sqlite3.IntegrityError:
        return "Victor already remembers this exact fact."
    except Exception as e:
        return f"Database error: {e}"


def get_memories(category: Optional[str] = None, search: Optional[str] = None, limit: int = 100) -> List[Dict[str, Any]]:
    """Retrieve memories with optional category filter or keyword search."""
    query = "SELECT id, category, content, importance, created_at FROM memories WHERE 1=1"
    params = []

    if category and category != "all":
        query += " AND category = ?"
        params.append(category)

    if search:
        query += " AND content LIKE ?"
        params.append(f"%{search}%")

    query += " ORDER BY importance DESC, id DESC LIMIT ?"
    params.append(limit)

    with get_db() as db:
        rows = db.execute(query, params).fetchall()
        return [
            {
                "id": r[0],
                "category": r[1],
                "content": r[2],
                "importance": r[3],
                "created_at": r[4]
            }
            for r in rows
        ]


def delete_memory(memory_id: int) -> bool:
    """Delete a memory by primary key ID."""
    with get_db() as db:
        cursor = db.execute("DELETE FROM memories WHERE id = ?", (memory_id,))
        return cursor.rowcount > 0


def clear_all_memories() -> int:
    """Delete all stored memories."""
    with get_db() as db:
        cursor = db.execute("DELETE FROM memories")
        return cursor.rowcount


def format_memories_for_prompt(limit: int = 15) -> str:
    """Format stored memories for LLM prompt context injection."""
    memories = get_memories(limit=limit)
    if not memories:
        return "No specific personal facts saved yet."

    lines = []
    for m in memories:
        lines.append(f"- [{m['category'].upper()}] {m['content']}")
    return "\n".join(lines)


# Conversation Logging
def save_conversation_turn(session_id: str, role: str, content: str):
    """Log user or assistant message to persistent conversation history."""
    try:
        with get_db() as db:
            db.execute(
                "INSERT INTO conversations (session_id, role, content) VALUES (?, ?, ?)",
                (session_id, role, content)
            )
    except Exception as e:
        print(f"[!] Error saving conversation turn: {e}")


def get_recent_conversation(limit: int = 10, session_id: Optional[str] = None) -> List[Dict[str, Any]]:
    """Get recent conversation history."""
    query = "SELECT role, content, timestamp FROM conversations"
    params = []
    if session_id:
        query += " WHERE session_id = ?"
        params.append(session_id)
    query += " ORDER BY id DESC LIMIT ?"
    params.append(limit)

    with get_db() as db:
        rows = db.execute(query, params).fetchall()
        # Return in chronological order
        return [{"role": r[0], "content": r[1], "timestamp": r[2]} for r in reversed(rows)]


# Security & Automation Audit Logging
def log_action(action_type: str, target: str, status: str, details: str = ""):
    """Record computer automation execution to audit logs."""
    try:
        with get_db() as db:
            db.execute(
                "INSERT INTO action_logs (action_type, target, status, details) VALUES (?, ?, ?, ?)",
                (action_type, target, status, details)
            )
    except Exception as e:
        print(f"[!] Error logging action: {e}")


def get_recent_action_logs(limit: int = 25) -> List[Dict[str, Any]]:
    """Retrieve recent automation audit logs."""
    with get_db() as db:
        rows = db.execute(
            "SELECT id, action_type, target, status, details, timestamp FROM action_logs ORDER BY id DESC LIMIT ?",
            (limit,)
        )
        return [
            {
                "id": r[0],
                "action_type": r[1],
                "target": r[2],
                "status": r[3],
                "details": r[4],
                "timestamp": r[5]
            }
            for r in rows
        ]


# Initialize schema immediately on import
initialize()
