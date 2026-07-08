from __future__ import annotations

import json
from typing import Any

from app.services.database import Database


class AuditLogService:
    def __init__(self, database: Database) -> None:
        self.database = database

    def entries(
        self,
        *,
        conversation_id: str | None = None,
        student_id: str | None = None,
        student_ids: list[str] | None = None,
        user_id: str | None = None,
        limit: int = 20,
    ) -> list[dict[str, Any]]:
        filters: list[str] = []
        params: list[Any] = []
        if user_id:
            filters.append("conversations.user_id = ?")
            params.append(user_id)
        if conversation_id:
            filters.append("logs.conversation_id = ?")
            params.append(conversation_id)
        if student_id:
            filters.append("conversations.student_id = ?")
            params.append(student_id)
        elif student_ids is not None:
            if not student_ids:
                return []
            placeholders = ", ".join("?" for _ in student_ids)
            filters.append(f"conversations.student_id IN ({placeholders})")
            params.extend(student_ids)

        bounded_limit = min(max(limit, 1), 100)
        params.append(bounded_limit)
        where = f"WHERE {' AND '.join(filters)}" if filters else ""
        rows = self.database.fetch_all(
            f"""
            SELECT
                logs.id,
                logs.conversation_id,
                conversations.user_id,
                conversations.student_id,
                conversations.role,
                logs.user_query,
                logs.identified_intent,
                logs.selected_tools_json,
                logs.execution_time_ms,
                logs.response_json,
                logs.status,
                logs.timestamp
            FROM execution_logs logs
            LEFT JOIN conversations
                ON conversations.conversation_id = logs.conversation_id
            {where}
            ORDER BY logs.id DESC
            LIMIT ?
            """,
            params,
        )
        return [_parse_entry(row) for row in rows]


def _parse_entry(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": row["id"],
        "conversation_id": row["conversation_id"],
        "user_id": row["user_id"],
        "student_id": row["student_id"],
        "role": row["role"],
        "user_query": row["user_query"],
        "identified_intent": row["identified_intent"],
        "selected_tools": json.loads(row["selected_tools_json"]),
        "execution_time_ms": row["execution_time_ms"],
        "response": json.loads(row["response_json"]),
        "status": row["status"],
        "timestamp": row["timestamp"],
    }
