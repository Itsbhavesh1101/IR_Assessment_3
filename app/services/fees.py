from __future__ import annotations

from datetime import date
from typing import Any

from app.services.database import Database


class FeeService:
    def __init__(self, database: Database) -> None:
        self.database = database

    def history(
        self,
        student_id: str,
        *,
        month: str | None = None,
        status: str | None = None,
    ) -> list[dict[str, Any]]:
        filters = ["student_id = ?"]
        params: list[Any] = [student_id]
        if month:
            filters.append("month = ?")
            params.append(month)
        if status:
            filters.append("LOWER(status) = LOWER(?)")
            params.append(status)
        query = f"""
            SELECT month, amount, paid_amount, status, paid_on
            FROM fees
            WHERE {' AND '.join(filters)}
            ORDER BY month
        """
        rows = self.database.fetch_all(query, params)
        for row in rows:
            row["pending_amount"] = max(row["amount"] - row["paid_amount"], 0)
        return rows

    def summarize(
        self,
        student_id: str,
        *,
        reference_date: date,
        month: str | None = None,
        only_unpaid: bool = False,
    ) -> dict[str, Any]:
        selected_month = month or reference_date.strftime("%Y-%m")
        status = None
        if only_unpaid:
            status = "unpaid"
        history = self.history(student_id, month=month, status=status)
        current = self.history(student_id, month=selected_month)
        pending_total = sum(row["pending_amount"] for row in history)
        paid_total = sum(row["paid_amount"] for row in history)
        billed_total = sum(row["amount"] for row in history)

        return {
            "month": selected_month,
            "history": history,
            "current_month": current[0] if current else None,
            "billed_total": billed_total,
            "paid_total": paid_total,
            "pending_total": pending_total,
            "has_pending": pending_total > 0,
        }

