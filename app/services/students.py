from __future__ import annotations

from typing import Any

from app.services.database import Database


class StudentService:
    def __init__(self, database: Database) -> None:
        self.database = database

    def active_students(self) -> list[dict[str, Any]]:
        return self.database.fetch_all(
            """
            SELECT student_id, name, role, class_name, section, guardian_name
            FROM students
            WHERE active = 1
            ORDER BY student_id
            """
        )

    def resolve_student(self, student_id: str | None) -> dict[str, Any] | None:
        if student_id:
            return self.database.fetch_one(
                "SELECT * FROM students WHERE student_id = ? AND active = 1",
                (student_id,),
            )
        return self.database.fetch_one(
            "SELECT * FROM students WHERE active = 1 ORDER BY student_id LIMIT 1"
        )

    def available_subjects(self, student: dict[str, Any]) -> list[str]:
        mark_rows = self.database.fetch_all(
            "SELECT DISTINCT subject FROM marks WHERE student_id = ?",
            (student["student_id"],),
        )
        timetable_rows = self.database.fetch_all(
            """
            SELECT DISTINCT subject FROM timetable
            WHERE class_name = ? AND section = ?
            """,
            (student["class_name"], student["section"]),
        )
        subjects = {row["subject"] for row in mark_rows + timetable_rows}
        return sorted(subjects)
