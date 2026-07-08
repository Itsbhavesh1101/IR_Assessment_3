from __future__ import annotations

from hashlib import sha256
from hmac import compare_digest
from typing import Any

from app.services.database import Database
from app.utils.errors import AppError


class UserAccessService:
    def __init__(self, database: Database) -> None:
        self.database = database

    def active_users(self) -> list[dict[str, Any]]:
        return self.database.fetch_all(
            """
            SELECT user_id, name, role
            FROM users
            WHERE active = 1
            ORDER BY role, user_id
            """
        )

    def resolve_user(self, user_id: str) -> dict[str, Any]:
        user = self.database.fetch_one(
            """
            SELECT user_id, name, role
            FROM users
            WHERE user_id = ? AND active = 1
            """,
            (user_id,),
        )
        if user is None:
            raise AppError(
                "INVALID_USER_ID",
                "No active ERP user was found for the provided user_id.",
                details={"user_id": user_id},
            )
        return user

    def resolve_user_by_token(self, api_token: str) -> dict[str, Any]:
        user = self.database.fetch_one(
            """
            SELECT user_id, name, role
            FROM users
            WHERE api_token = ? AND active = 1
            """,
            (api_token,),
        )
        if user is None:
            raise AppError(
                "INVALID_AUTH_TOKEN",
                "No active ERP user was found for the provided auth token.",
                details={},
                http_status=401,
            )
        return user

    def authenticate(
        self,
        *,
        login_type: str,
        user_id: str,
        password: str,
    ) -> dict[str, Any]:
        user = self.database.fetch_one(
            """
            SELECT user_id, name, role, password_hash, api_token
            FROM users
            WHERE user_id = ? AND active = 1
            """,
            (user_id,),
        )
        if user is None or not _role_matches(login_type, user["role"]):
            raise _invalid_credentials()

        password_hash = user.get("password_hash")
        if not password_hash or not compare_digest(password_hash, _password_hash(password)):
            raise _invalid_credentials()

        return {
            "user_id": user["user_id"],
            "name": user["name"],
            "role": user["role"],
            "api_token": user["api_token"],
        }

    def accessible_students(self, user_id: str) -> list[dict[str, Any]]:
        self.resolve_user(user_id)
        return self.database.fetch_all(
            """
            SELECT s.student_id, s.name, s.role, s.class_name, s.section, s.guardian_name
            FROM students s
            INNER JOIN user_student_access access ON access.student_id = s.student_id
            WHERE access.user_id = ? AND s.active = 1
            ORDER BY s.student_id
            """,
            (user_id,),
        )

    def resolve_accessible_student(
        self,
        *,
        user_id: str,
        student_id: str | None,
    ) -> tuple[dict[str, Any], dict[str, Any]]:
        user = self.resolve_user(user_id)
        students = self.accessible_students(user_id)
        if not students:
            raise AppError(
                "NO_ACCESSIBLE_STUDENTS",
                "The ERP user does not have access to any active students.",
                details={"user_id": user_id},
            )
        if student_id is None:
            return user, students[0]

        for student in students:
            if student["student_id"] == student_id:
                return user, student

        raise AppError(
            "ACCESS_DENIED",
            "The ERP user does not have access to the requested student.",
            details={"user_id": user_id, "student_id": student_id},
            http_status=403,
        )

    def assert_student_access(self, *, user_id: str, student_id: str) -> dict[str, Any]:
        _user, student = self.resolve_accessible_student(user_id=user_id, student_id=student_id)
        return student


def _password_hash(password: str) -> str:
    return sha256(password.encode("utf-8")).hexdigest()


def _role_matches(login_type: str, role: str) -> bool:
    if login_type == "teacher":
        return role == "teacher"
    if login_type == "parent_student":
        return role in {"parent", "student"}
    return False


def _invalid_credentials() -> AppError:
    return AppError(
        "INVALID_CREDENTIALS",
        "The login type, user ID, or password is incorrect.",
        details={},
        http_status=401,
    )
