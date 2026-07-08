from __future__ import annotations

import json
from datetime import UTC, datetime
from typing import Any

from app.services.database import Database
from app.utils.config import Settings


class JsonAuditLogger:
    def __init__(self, settings: Settings, database: Database) -> None:
        self.settings = settings
        self.database = database

    def log_chat_event(
        self,
        *,
        conversation_id: str,
        user_query: str,
        identified_intent: str,
        selected_tools: list[str],
        execution_time_ms: float,
        response: dict[str, Any],
        status: str,
    ) -> None:
        timestamp = datetime.now(UTC).isoformat()
        event = {
            "timestamp": timestamp,
            "conversation_id": conversation_id,
            "user_query": user_query,
            "identified_intent": identified_intent,
            "selected_tools": selected_tools,
            "execution_time_ms": execution_time_ms,
            "response": response,
            "status": status,
        }
        self.settings.log_file_path.parent.mkdir(parents=True, exist_ok=True)
        with self.settings.log_file_path.open("a", encoding="utf-8") as file:
            file.write(json.dumps(event) + "\n")

        self.database.execute(
            """
            INSERT INTO execution_logs (
                conversation_id, user_query, identified_intent, selected_tools_json,
                execution_time_ms, response_json, status, timestamp
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                conversation_id,
                user_query,
                identified_intent,
                json.dumps(selected_tools),
                execution_time_ms,
                json.dumps(response),
                status,
                timestamp,
            ),
        )

