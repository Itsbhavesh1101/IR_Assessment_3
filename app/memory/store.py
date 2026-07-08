from __future__ import annotations

import json
from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

from app.services.database import Database
from app.utils.errors import AppError


class ConversationMemory:
    def __init__(self, database: Database) -> None:
        self.database = database

    def get_or_create(
        self,
        *,
        conversation_id: str | None,
        user_id: str | None,
        student_id: str,
        role: str,
    ) -> str:
        timestamp = _utc_now()
        if conversation_id:
            existing = self.database.fetch_one(
                """
                SELECT conversation_id, user_id, student_id, role
                FROM conversations
                WHERE conversation_id = ?
                """,
                (conversation_id,),
            )
            if existing:
                if existing["user_id"] != user_id:
                    raise AppError(
                        "CONVERSATION_ACCESS_DENIED",
                        "The conversation_id does not belong to the selected ERP user.",
                        http_status=403,
                        details={
                            "conversation_id": conversation_id,
                            "user_id": user_id,
                        },
                    )
                if existing["student_id"] != student_id:
                    raise AppError(
                        "CONVERSATION_ACCESS_DENIED",
                        "The conversation_id does not belong to the selected student.",
                        http_status=403,
                        details={
                            "conversation_id": conversation_id,
                            "student_id": student_id,
                        },
                    )
                if existing["role"] != role:
                    raise AppError(
                        "CONVERSATION_ACCESS_DENIED",
                        "The conversation_id does not belong to the selected role.",
                        http_status=403,
                        details={
                            "conversation_id": conversation_id,
                            "role": role,
                        },
                    )
                self.database.execute(
                    "UPDATE conversations SET updated_at = ? WHERE conversation_id = ?",
                    (timestamp, conversation_id),
                )
                return conversation_id

        generated_id = str(uuid4())
        self.database.execute(
            """
            INSERT INTO conversations (
                conversation_id, user_id, student_id, role, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?)
            """,
            (generated_id, user_id, student_id, role, timestamp, timestamp),
        )
        return generated_id

    def add_exchange(
        self,
        *,
        conversation_id: str,
        user_id: str | None,
        student_id: str,
        role: str,
        message: str,
        plan: list[dict[str, Any]],
        tool_results: list[dict[str, Any]],
        response: dict[str, Any],
    ) -> None:
        timestamp = _utc_now()
        self.database.execute(
            """
            INSERT INTO chat_messages (
                conversation_id, user_id, student_id, role, message,
                plan_json, tool_results_json, response_json, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                conversation_id,
                user_id,
                student_id,
                role,
                message,
                json.dumps(plan),
                json.dumps(tool_results),
                json.dumps(response),
                timestamp,
            ),
        )
        self.database.execute(
            "UPDATE conversations SET updated_at = ? WHERE conversation_id = ?",
            (timestamp, conversation_id),
        )

    def recent_context(self, conversation_id: str, *, limit: int = 6) -> list[dict[str, Any]]:
        rows = self.database.fetch_all(
            """
            SELECT message, plan_json, tool_results_json, response_json, created_at
            FROM chat_messages
            WHERE conversation_id = ?
            ORDER BY id DESC
            LIMIT ?
            """,
            (conversation_id, limit),
        )
        context = []
        for row in reversed(rows):
            plan = json.loads(row["plan_json"])
            response = json.loads(row["response_json"])
            tool_results = json.loads(row["tool_results_json"])
            context.append(
                {
                    "message": row["message"],
                    "plan": plan,
                    "tools_used": [item["tool"] for item in tool_results],
                    "response": response,
                    "created_at": row["created_at"],
                }
            )
        return context

    def history(
        self,
        *,
        student_id: str | None = None,
        student_ids: list[str] | None = None,
        user_id: str | None = None,
        conversation_id: str | None = None,
        limit: int = 50,
    ) -> list[dict[str, Any]]:
        filters: list[str] = []
        params: list[Any] = []
        if user_id:
            filters.append("user_id = ?")
            params.append(user_id)
        if student_id:
            filters.append("student_id = ?")
            params.append(student_id)
        elif student_ids is not None:
            if not student_ids:
                return []
            placeholders = ", ".join("?" for _ in student_ids)
            filters.append(f"student_id IN ({placeholders})")
            params.extend(student_ids)
        if conversation_id:
            filters.append("conversation_id = ?")
            params.append(conversation_id)
        where = f"WHERE {' AND '.join(filters)}" if filters else ""
        bounded_limit = min(max(limit, 1), 100)
        params.append(bounded_limit)
        rows = self.database.fetch_all(
            f"""
            SELECT conversation_id, user_id, student_id, role, message,
                   response_json, plan_json, created_at
            FROM (
                SELECT conversation_id, user_id, student_id, role, message,
                       response_json, plan_json, created_at, id
                FROM chat_messages
                {where}
                ORDER BY created_at DESC, id DESC
                LIMIT ?
            )
            ORDER BY created_at, id
            """,
            params,
        )
        return [
            {
                "conversation_id": row["conversation_id"],
                "user_id": row["user_id"],
                "student_id": row["student_id"],
                "role": row["role"],
                "message": row["message"],
                "response": json.loads(row["response_json"]),
                "plan": json.loads(row["plan_json"]),
                "created_at": row["created_at"],
            }
            for row in rows
        ]

    def conversations(
        self,
        *,
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
                conversations.conversation_id,
                conversations.user_id,
                conversations.student_id,
                conversations.role,
                conversations.created_at,
                conversations.updated_at,
                COUNT(chat_messages.id) AS message_count,
                (
                    SELECT latest.message
                    FROM chat_messages latest
                    WHERE latest.conversation_id = conversations.conversation_id
                    ORDER BY latest.id DESC
                    LIMIT 1
                ) AS latest_message
            FROM conversations
            LEFT JOIN chat_messages
                ON chat_messages.conversation_id = conversations.conversation_id
            {where}
            GROUP BY
                conversations.conversation_id,
                conversations.user_id,
                conversations.student_id,
                conversations.role,
                conversations.created_at,
                conversations.updated_at
            ORDER BY conversations.updated_at DESC
            LIMIT ?
            """,
            params,
        )
        return [
            {
                "conversation_id": row["conversation_id"],
                "user_id": row["user_id"],
                "student_id": row["student_id"],
                "role": row["role"],
                "message_count": row["message_count"],
                "latest_message": row["latest_message"],
                "created_at": row["created_at"],
                "updated_at": row["updated_at"],
            }
            for row in rows
        ]


def _utc_now() -> str:
    return datetime.now(UTC).isoformat()
