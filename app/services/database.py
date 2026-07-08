from __future__ import annotations

import sqlite3
from collections.abc import Iterable, Iterator
from contextlib import contextmanager
from typing import Any

from app.utils.config import Settings


class Database:
    def __init__(self, settings: Settings) -> None:
        self.path = settings.database_path

    def connect(self) -> sqlite3.Connection:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        connection = sqlite3.connect(self.path)
        connection.row_factory = sqlite3.Row
        return connection

    @contextmanager
    def session(self) -> Iterator[sqlite3.Connection]:
        connection = self.connect()
        try:
            yield connection
            connection.commit()
        except Exception:
            connection.rollback()
            raise
        finally:
            connection.close()

    def ensure_schema(self) -> None:
        with self.session() as connection:
            connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS students (
                    student_id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    role TEXT NOT NULL,
                    class_name TEXT NOT NULL,
                    section TEXT NOT NULL,
                    guardian_name TEXT,
                    active INTEGER NOT NULL DEFAULT 1
                );

                CREATE TABLE IF NOT EXISTS users (
                    user_id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    role TEXT NOT NULL,
                    password_hash TEXT,
                    api_token TEXT,
                    active INTEGER NOT NULL DEFAULT 1
                );

                CREATE TABLE IF NOT EXISTS user_student_access (
                    user_id TEXT NOT NULL,
                    student_id TEXT NOT NULL,
                    PRIMARY KEY (user_id, student_id),
                    FOREIGN KEY(user_id) REFERENCES users(user_id),
                    FOREIGN KEY(student_id) REFERENCES students(student_id)
                );

                CREATE TABLE IF NOT EXISTS attendance (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    student_id TEXT NOT NULL,
                    date TEXT NOT NULL,
                    subject TEXT NOT NULL,
                    status TEXT NOT NULL,
                    FOREIGN KEY(student_id) REFERENCES students(student_id)
                );

                CREATE TABLE IF NOT EXISTS marks (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    student_id TEXT NOT NULL,
                    subject TEXT NOT NULL,
                    exam TEXT NOT NULL,
                    term TEXT NOT NULL,
                    score REAL NOT NULL,
                    max_score REAL NOT NULL,
                    FOREIGN KEY(student_id) REFERENCES students(student_id)
                );

                CREATE TABLE IF NOT EXISTS fees (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    student_id TEXT NOT NULL,
                    month TEXT NOT NULL,
                    amount REAL NOT NULL,
                    paid_amount REAL NOT NULL,
                    status TEXT NOT NULL,
                    paid_on TEXT,
                    FOREIGN KEY(student_id) REFERENCES students(student_id)
                );

                CREATE TABLE IF NOT EXISTS homework (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    class_name TEXT NOT NULL,
                    section TEXT NOT NULL,
                    subject TEXT NOT NULL,
                    title TEXT NOT NULL,
                    assigned_date TEXT NOT NULL,
                    due_date TEXT NOT NULL,
                    status TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS timetable (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    class_name TEXT NOT NULL,
                    section TEXT NOT NULL,
                    day_of_week TEXT NOT NULL,
                    period INTEGER NOT NULL,
                    subject TEXT NOT NULL,
                    start_time TEXT NOT NULL,
                    end_time TEXT NOT NULL,
                    teacher TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS conversations (
                    conversation_id TEXT PRIMARY KEY,
                    user_id TEXT,
                    student_id TEXT NOT NULL,
                    role TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS chat_messages (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    conversation_id TEXT NOT NULL,
                    user_id TEXT,
                    student_id TEXT NOT NULL,
                    role TEXT NOT NULL,
                    message TEXT NOT NULL,
                    plan_json TEXT NOT NULL,
                    tool_results_json TEXT NOT NULL,
                    response_json TEXT NOT NULL,
                    created_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS execution_logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    conversation_id TEXT NOT NULL,
                    user_query TEXT NOT NULL,
                    identified_intent TEXT NOT NULL,
                    selected_tools_json TEXT NOT NULL,
                    execution_time_ms REAL NOT NULL,
                    response_json TEXT NOT NULL,
                    status TEXT NOT NULL,
                    timestamp TEXT NOT NULL
                );
                """
            )
            _ensure_column(connection, "users", "password_hash", "TEXT")
            _ensure_column(connection, "users", "api_token", "TEXT")
            _ensure_column(connection, "conversations", "user_id", "TEXT")
            _ensure_column(connection, "chat_messages", "user_id", "TEXT")

    def has_students(self) -> bool:
        with self.session() as connection:
            row = connection.execute("SELECT COUNT(*) AS count FROM students").fetchone()
            return bool(row and row["count"])

    def has_users(self) -> bool:
        with self.session() as connection:
            row = connection.execute("SELECT COUNT(*) AS count FROM users").fetchone()
            return bool(row and row["count"])

    def execute(self, query: str, params: Iterable[Any] = ()) -> None:
        with self.session() as connection:
            connection.execute(query, tuple(params))

    def fetch_all(self, query: str, params: Iterable[Any] = ()) -> list[dict[str, Any]]:
        with self.session() as connection:
            rows = connection.execute(query, tuple(params)).fetchall()
            return [dict(row) for row in rows]

    def fetch_one(self, query: str, params: Iterable[Any] = ()) -> dict[str, Any] | None:
        with self.session() as connection:
            row = connection.execute(query, tuple(params)).fetchone()
            return dict(row) if row else None

    def reset_data_tables(self) -> None:
        with self.session() as connection:
            for table in (
                "user_student_access",
                "attendance",
                "marks",
                "fees",
                "homework",
                "timetable",
                "users",
                "students",
            ):
                connection.execute(f"DELETE FROM {table}")


def remove_database_file(settings: Settings) -> None:
    path = settings.database_path
    if path.exists() and path.is_file():
        path.unlink()


def _ensure_column(
    connection: sqlite3.Connection,
    table: str,
    column: str,
    definition: str,
) -> None:
    existing_columns = {
        row["name"]
        for row in connection.execute(f"PRAGMA table_info({table})").fetchall()
    }
    if column not in existing_columns:
        connection.execute(f"ALTER TABLE {table} ADD COLUMN {column} {definition}")
