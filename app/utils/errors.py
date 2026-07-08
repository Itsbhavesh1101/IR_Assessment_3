from __future__ import annotations

from typing import Any


class AppError(Exception):
    def __init__(
        self,
        error_code: str,
        message: str,
        *,
        http_status: int = 400,
        details: dict[str, Any] | None = None,
    ) -> None:
        self.error_code = error_code
        self.message = message
        self.http_status = http_status
        self.details = details or {}
        super().__init__(message)

    def to_dict(self) -> dict[str, Any]:
        return {
            "status": "error",
            "error_code": self.error_code,
            "message": self.message,
            "details": self.details,
        }

