from __future__ import annotations

import json
from pathlib import Path

from app.utils.config import get_settings


def test_chat_writes_json_log(client):
    response = client.post(
        "/chat",
        json={"message": "Show payment history.", "student_id": "S001"},
    )

    assert response.status_code == 200
    log_path = get_settings().log_file_path
    lines = log_path.read_text(encoding="utf-8").strip().splitlines()
    event = json.loads(lines[-1])
    assert event["user_query"] == "Show payment history."
    assert event["identified_intent"] == "fees"
    assert event["selected_tools"] == ["fee_status_tool"]
    assert "execution_time_ms" in event
    assert "timestamp" in event


def test_logs_endpoint_returns_execution_log_fields(client):
    chat_response = client.post(
        "/chat",
        json={
            "user_id": "U_STUDENT_001",
            "student_id": "S001",
            "message": "Show only unpaid fees.",
        },
    )

    assert chat_response.status_code == 200
    response = client.get(
        "/logs",
        params={"conversation_id": chat_response.json()["conversation_id"]},
    )

    assert response.status_code == 200
    logs = response.json()["logs"]
    assert len(logs) == 1
    assert logs[0]["user_query"] == "Show only unpaid fees."
    assert logs[0]["identified_intent"] == "fees"
    assert logs[0]["selected_tools"] == ["fee_status_tool"]
    assert "execution_time_ms" in logs[0]
    assert "timestamp" in logs[0]
    assert logs[0]["response"]["data"]["action"] == "unpaid"


def test_logs_endpoint_is_scoped_by_user_access(client):
    student_chat = client.post(
        "/chat",
        json={
            "user_id": "U_STUDENT_001",
            "student_id": "S001",
            "message": "Show my attendance.",
        },
    )
    teacher_chat = client.post(
        "/chat",
        json={
            "user_id": "U_TEACHER_10A",
            "student_id": "S001",
            "message": "Show my attendance.",
        },
    )

    assert student_chat.status_code == 200
    assert teacher_chat.status_code == 200
    response = client.get("/logs", params={"user_id": "U_STUDENT_001"})

    assert response.status_code == 200
    student_ids = {entry["student_id"] for entry in response.json()["logs"]}
    assert student_ids == {"S001"}


def test_logs_endpoint_is_scoped_to_exact_user_for_shared_student(client):
    student_chat = client.post(
        "/chat",
        json={
            "user_id": "U_STUDENT_001",
            "student_id": "S001",
            "message": "Show my attendance.",
        },
    )
    teacher_chat = client.post(
        "/chat",
        json={
            "user_id": "U_TEACHER_10A",
            "student_id": "S001",
            "message": "Show my marks.",
        },
    )

    assert student_chat.status_code == 200
    assert teacher_chat.status_code == 200

    response = client.get(
        "/logs",
        params={"user_id": "U_STUDENT_001", "student_id": "S001"},
    )

    assert response.status_code == 200
    logs = response.json()["logs"]
    assert [entry["user_id"] for entry in logs] == ["U_STUDENT_001"]
    assert [entry["user_query"] for entry in logs] == ["Show my attendance."]


def test_logs_endpoint_denies_inaccessible_student_filter(client):
    response = client.get(
        "/logs",
        params={"user_id": "U_STUDENT_001", "student_id": "S999"},
    )

    assert response.status_code == 403
    assert response.json()["error_code"] == "ACCESS_DENIED"


def test_application_code_and_static_ui_do_not_embed_mock_business_records():
    app_root = Path(__file__).resolve().parents[1] / "app"
    forbidden_fragments = [
        "S001",
        "Ananya",
        "2026-",
        "92%",
        "Your attendance is",
    ]

    checked_paths = [
        path
        for path in app_root.rglob("*")
        if path.suffix in {".py", ".html", ".js", ".css"}
    ]

    for path in checked_paths:
        text = path.read_text(encoding="utf-8")
        for fragment in forbidden_fragments:
            assert fragment not in text, f"{fragment!r} was found in {path}"
