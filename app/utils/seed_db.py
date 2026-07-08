from __future__ import annotations

import json
from hashlib import sha256
from pathlib import Path
from typing import Any

from app.services.database import Database
from app.utils.config import get_settings

DATA_FILES = {
    "students": "students.json",
    "users": "users.json",
    "attendance": "attendance.json",
    "marks": "marks.json",
    "fees": "fees.json",
    "homework": "homework.json",
    "timetable": "timetable.json",
}


def _load_json(path: Path) -> list[dict[str, Any]]:
    with path.open("r", encoding="utf-8") as file:
        data = json.load(file)
    if not isinstance(data, list):
        raise ValueError(f"{path.name} must contain a JSON array.")
    return data


def _password_hash(password: str | None) -> str | None:
    if not password:
        return None
    return sha256(password.encode("utf-8")).hexdigest()


def seed_database(database: Database, data_dir: Path, *, reset: bool = False) -> None:
    database.ensure_schema()
    if reset:
        database.reset_data_tables()

    payloads = {
        table: _load_json(data_dir / filename)
        for table, filename in DATA_FILES.items()
    }

    with database.session() as connection:
        for item in payloads["students"]:
            connection.execute(
                """
                INSERT OR REPLACE INTO students (
                    student_id, name, role, class_name, section, guardian_name, active
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    item["student_id"],
                    item["name"],
                    item["role"],
                    item["class_name"],
                    item["section"],
                    item.get("guardian_name"),
                    1 if item.get("active", True) else 0,
                ),
            )

        for item in payloads["users"]:
            connection.execute(
                """
                INSERT OR REPLACE INTO users (
                    user_id, name, role, password_hash, api_token, active
                ) VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    item["user_id"],
                    item["name"],
                    item["role"],
                    _password_hash(item.get("password")),
                    item.get("api_token"),
                    1 if item.get("active", True) else 0,
                ),
            )
            for student_id in item.get("student_ids", []):
                connection.execute(
                    """
                    INSERT OR REPLACE INTO user_student_access (user_id, student_id)
                    VALUES (?, ?)
                    """,
                    (item["user_id"], student_id),
                )

        for item in payloads["attendance"]:
            connection.execute(
                """
                INSERT INTO attendance (student_id, date, subject, status)
                VALUES (?, ?, ?, ?)
                """,
                (item["student_id"], item["date"], item["subject"], item["status"]),
            )

        for item in payloads["marks"]:
            connection.execute(
                """
                INSERT INTO marks (student_id, subject, exam, term, score, max_score)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    item["student_id"],
                    item["subject"],
                    item["exam"],
                    item["term"],
                    item["score"],
                    item["max_score"],
                ),
            )

        for item in payloads["fees"]:
            connection.execute(
                """
                INSERT INTO fees (student_id, month, amount, paid_amount, status, paid_on)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    item["student_id"],
                    item["month"],
                    item["amount"],
                    item["paid_amount"],
                    item["status"],
                    item.get("paid_on"),
                ),
            )

        for item in payloads["homework"]:
            connection.execute(
                """
                INSERT INTO homework (
                    class_name, section, subject, title, assigned_date, due_date, status
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    item["class_name"],
                    item["section"],
                    item["subject"],
                    item["title"],
                    item["assigned_date"],
                    item["due_date"],
                    item["status"],
                ),
            )

        for item in payloads["timetable"]:
            connection.execute(
                """
                INSERT INTO timetable (
                    class_name, section, day_of_week, period, subject,
                    start_time, end_time, teacher
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    item["class_name"],
                    item["section"],
                    item["day_of_week"],
                    item["period"],
                    item["subject"],
                    item["start_time"],
                    item["end_time"],
                    item["teacher"],
                ),
            )


def seed_user_access(database: Database, data_dir: Path) -> None:
    database.ensure_schema()
    users = _load_json(data_dir / DATA_FILES["users"])
    with database.session() as connection:
        for item in users:
            connection.execute(
                """
                INSERT OR REPLACE INTO users (
                    user_id, name, role, password_hash, api_token, active
                ) VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    item["user_id"],
                    item["name"],
                    item["role"],
                    _password_hash(item.get("password")),
                    item.get("api_token"),
                    1 if item.get("active", True) else 0,
                ),
            )
            for student_id in item.get("student_ids", []):
                connection.execute(
                    """
                    INSERT OR REPLACE INTO user_student_access (user_id, student_id)
                    VALUES (?, ?)
                    """,
                    (item["user_id"], student_id),
                )


def ensure_seed_data(database: Database, data_dir: Path) -> None:
    database.ensure_schema()
    if not database.has_students():
        seed_database(database, data_dir, reset=True)
    else:
        seed_user_access(database, data_dir)


def main() -> None:
    settings = get_settings()
    seed_database(Database(settings), settings.mock_data_dir, reset=True)
    print(f"Seeded database at {settings.database_path}")


if __name__ == "__main__":
    main()
