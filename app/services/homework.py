from __future__ import annotations

from datetime import date
from typing import Any

from app.services.database import Database
from app.utils.dates import period_bounds


class HomeworkService:
    def __init__(self, database: Database) -> None:
        self.database = database

    def tasks(
        self,
        student: dict[str, Any],
        *,
        period: str | None,
        reference_date: date,
        status: str | None = None,
        subject: str | None = None,
    ) -> list[dict[str, Any]]:
        start, end = period_bounds(period, reference_date)
        filters = ["class_name = ?", "section = ?"]
        params: list[Any] = [student["class_name"], student["section"]]

        if start and end:
            filters.append("due_date BETWEEN ? AND ?")
            params.extend([start.isoformat(), end.isoformat()])
        if status:
            filters.append("LOWER(status) = LOWER(?)")
            params.append(status)
        if subject:
            filters.append("LOWER(subject) = LOWER(?)")
            params.append(subject)

        query = f"""
            SELECT subject, title, assigned_date, due_date, status
            FROM homework
            WHERE {' AND '.join(filters)}
            ORDER BY due_date, subject
        """
        return self.database.fetch_all(query, params)

    def summarize(
        self,
        student: dict[str, Any],
        *,
        period: str | None,
        reference_date: date,
        status: str | None = None,
        subject: str | None = None,
    ) -> dict[str, Any]:
        tasks = self.tasks(
            student,
            period=period,
            reference_date=reference_date,
            status=status,
            subject=subject,
        )
        pending = [task for task in tasks if task["status"].lower() == "pending"]
        completed = [task for task in tasks if task["status"].lower() == "completed"]
        return {
            "period": period or "all",
            "subject": subject,
            "tasks": tasks,
            "pending_count": len(pending),
            "completed_count": len(completed),
            "total_count": len(tasks),
        }

