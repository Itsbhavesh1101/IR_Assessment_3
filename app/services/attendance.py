from __future__ import annotations

from datetime import date
from typing import Any

from app.services.database import Database
from app.utils.dates import period_bounds


class AttendanceService:
    def __init__(self, database: Database) -> None:
        self.database = database

    def records(
        self,
        student_id: str,
        *,
        period: str | None,
        reference_date: date,
        subject: str | None = None,
    ) -> list[dict[str, Any]]:
        start, end = period_bounds(period, reference_date)
        filters = ["student_id = ?"]
        params: list[Any] = [student_id]

        if start and end:
            filters.append("date BETWEEN ? AND ?")
            params.extend([start.isoformat(), end.isoformat()])
        if subject:
            filters.append("LOWER(subject) = LOWER(?)")
            params.append(subject)

        query = f"""
            SELECT date, subject, status
            FROM attendance
            WHERE {' AND '.join(filters)}
            ORDER BY date, subject
        """
        return self.database.fetch_all(query, params)

    def summarize(
        self,
        student_id: str,
        *,
        period: str | None,
        reference_date: date,
        subject: str | None = None,
    ) -> dict[str, Any]:
        records = self.records(
            student_id,
            period=period,
            reference_date=reference_date,
            subject=subject,
        )
        total = len(records)
        present = sum(1 for row in records if row["status"].lower() == "present")
        absent = sum(1 for row in records if row["status"].lower() == "absent")
        percentage = round((present / total) * 100, 2) if total else None

        if percentage is None:
            standing = "no_records"
        elif percentage >= 90:
            standing = "strong"
        elif percentage >= 75:
            standing = "watch"
        else:
            standing = "needs_attention"

        return {
            "period": period or "all",
            "subject": subject,
            "total_classes": total,
            "present_classes": present,
            "missed_classes": absent,
            "attendance_percentage": percentage,
            "standing": standing,
            "records": records,
        }

