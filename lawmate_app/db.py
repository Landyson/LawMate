from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Optional, List, Dict, Any
from datetime import datetime

def utc_now_iso() -> str:
    return datetime.utcnow().replace(microsecond=0).isoformat()

class Database:
    def __init__(self, db_path: Path):
        self.db_path = db_path
        self.conn = sqlite3.connect(str(db_path))
        self.conn.row_factory = sqlite3.Row
        self._init_schema()

    def _init_schema(self) -> None:
        cur = self.conn.cursor()
        cur.executescript(
            """
            PRAGMA journal_mode=WAL;

            CREATE TABLE IF NOT EXISTS sessions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                category TEXT NOT NULL,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id INTEGER NOT NULL,
                role TEXT NOT NULL,
                content TEXT NOT NULL,
                traffic_light TEXT,
                sources_json TEXT,
                created_at TEXT NOT NULL,
                FOREIGN KEY(session_id) REFERENCES sessions(id)
            );
            """
        )
        self.conn.commit()

    def create_session(self, title: str, category: str) -> int:
        now = utc_now_iso()
        cur = self.conn.cursor()
        cur.execute(
            "INSERT INTO sessions (title, category, created_at, updated_at) VALUES (?, ?, ?, ?)",
            (title, category, now, now),
        )
        self.conn.commit()
        return int(cur.lastrowid)

    def list_sessions(self) -> List[Dict[str, Any]]:
        cur = self.conn.cursor()
        rows = cur.execute(
            "SELECT id, title, category, created_at, updated_at FROM sessions ORDER BY updated_at DESC"
        ).fetchall()
        return [dict(r) for r in rows]

    def delete_session(self, session_id: int) -> None:
        cur = self.conn.cursor()
        cur.execute("DELETE FROM messages WHERE session_id=?", (session_id,))
        cur.execute("DELETE FROM sessions WHERE id=?", (session_id,))
        self.conn.commit()

    def add_message(
        self,
        session_id: int,
        role: str,
        content: str,
        traffic_light: Optional[str] = None,
        sources_json: Optional[str] = None,
    ) -> int:
        cur = self.conn.cursor()
        cur.execute(
            """
            INSERT INTO messages (session_id, role, content, traffic_light, sources_json, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (session_id, role, content, traffic_light, sources_json, utc_now_iso()),
        )
        cur.execute("UPDATE sessions SET updated_at=? WHERE id=?", (utc_now_iso(), session_id))
        self.conn.commit()
        return int(cur.lastrowid)

    def get_messages(self, session_id: int) -> List[Dict[str, Any]]:
        cur = self.conn.cursor()
        rows = cur.execute(
            """
            SELECT id, role, content, traffic_light, sources_json, created_at
            FROM messages
            WHERE session_id=?
            ORDER BY id ASC
            """,
            (session_id,),
        ).fetchall()
        return [dict(r) for r in rows]
