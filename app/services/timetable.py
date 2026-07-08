from __future__ import annotations

from datetime import date
from typing import Any

from app.services.database import Database
from app.utils.dates import day_name_for_period


class TimetableService:
    def __init__(self, database: Database) -> None:
        self.database = database

    def entries(
        self,
        student: dict[str, Any],
        *,
        period: str | None,
        reference_date: date,
        subject: str | None = None,
        first_only: bool = False,
    ) -> list[dict[str, Any]]:
        day_name = day_name_for_period(period, reference_date)
        filters = ["class_name = ?", "section = ?", "day_of_week = ?"]
        params: list[Any] = [student["class_name"], student["section"], day_name]
        if subject:
            filters.append("LOWER(subject) = LOWER(?)")
            params.append(subject)
        limit = "LIMIT 1" if first_only else ""
        query = f"""
            SELECT day_of_week, period, subject, start_time, end_time, teacher
            FROM timetable
            WHERE {' AND '.join(filters)}
            ORDER BY period
            {limit}
        """
        return self.database.fetch_all(query, params)

    def summarize(
        self,
        student: dict[str, Any],
        *,
        period: str | None,
        reference_date: date,
        subject: str | None = None,
        first_only: bool = False,
    ) -> dict[str, Any]:
        entries = self.entries(
            student,
            period=period,
            reference_date=reference_date,
            subject=subject,
            first_only=first_only,
        )
        return {
            "period": period or "today",
            "day_of_week": day_name_for_period(period, reference_date),
            "subject": subject,
            "first_only": first_only,
            "entries": entries,
            "total_classes": len(entries),
        }

