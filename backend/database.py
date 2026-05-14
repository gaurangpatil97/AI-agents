import os
import sqlite3
from typing import Any, Dict, List, Optional
from uuid import uuid4


DB_PATH = os.path.join(os.path.dirname(__file__), "sessions.db")


def _get_connection() -> sqlite3.Connection:
    connection = sqlite3.connect(DB_PATH)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    return connection


def init_db() -> None:
    with _get_connection() as connection:
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS sessions (
                session_id TEXT PRIMARY KEY,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                ended_at DATETIME,
                dataset_name TEXT,
                dataset_source TEXT,
                status TEXT DEFAULT 'active',
                summary TEXT
            )
            """
        )
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS messages (
                message_id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                question TEXT,
                answer TEXT,
                chart_path TEXT,
                FOREIGN KEY (session_id) REFERENCES sessions(session_id)
            )
            """
        )


def create_session(session_id: str, dataset_name: str = "unknown", dataset_source: str = "local") -> str:
    with _get_connection() as connection:
        connection.execute(
            """
            INSERT INTO sessions (session_id, dataset_name, dataset_source, status)
            VALUES (?, ?, ?, 'active')
            """,
            (session_id, dataset_name, dataset_source),
        )
    return session_id


def save_message(session_id: str, question: str, answer: str, chart_path: Optional[str] = None) -> None:
    with _get_connection() as connection:
        connection.execute(
            """
            INSERT INTO messages (session_id, question, answer, chart_path)
            VALUES (?, ?, ?, ?)
            """,
            (session_id, question, answer, chart_path),
        )


def end_session(session_id: str, summary: str) -> None:
    with _get_connection() as connection:
        connection.execute(
            """
            UPDATE sessions
            SET ended_at = CURRENT_TIMESTAMP,
                status = 'ended',
                summary = ?
            WHERE session_id = ?
            """,
            (summary, session_id),
        )


def get_session_messages(session_id: str) -> List[Dict[str, Any]]:
    with _get_connection() as connection:
        rows = connection.execute(
            """
            SELECT question, answer, chart_path, timestamp
            FROM messages
            WHERE session_id = ?
            ORDER BY timestamp ASC, message_id ASC
            """,
            (session_id,),
        ).fetchall()

    return [
        {
            "question": row["question"],
            "answer": row["answer"],
            "chart_path": row["chart_path"],
            "timestamp": row["timestamp"],
        }
        for row in rows
    ]


def get_all_sessions() -> List[Dict[str, Any]]:
    with _get_connection() as connection:
        rows = connection.execute(
            """
            SELECT session_id, created_at, ended_at, dataset_name, dataset_source, status, summary
            FROM sessions
            ORDER BY created_at DESC
            """
        ).fetchall()

    return [
        {
            "session_id": row["session_id"],
            "created_at": row["created_at"],
            "ended_at": row["ended_at"],
            "dataset_name": row["dataset_name"],
            "dataset_source": row["dataset_source"],
            "status": row["status"],
            "summary": row["summary"],
        }
        for row in rows
    ]


def generate_summary(session_id: str) -> str:
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute(
        "SELECT question, answer, chart_path FROM messages WHERE session_id = ?",
        (session_id,),
    )
    rows = cursor.fetchall()
    conn.close()

    total_questions = len(rows)
    charts = [r[2] for r in rows if r[2] is not None]
    total_charts = len(charts)
    questions_list = "\n".join([f"- {r[0]}" for r in rows])

    summary = f"Session Summary:\n"
    summary += f"Total questions asked: {total_questions}\n"
    summary += f"Charts generated: {total_charts}\n"
    summary += f"Questions covered:\n{questions_list}"
    return summary