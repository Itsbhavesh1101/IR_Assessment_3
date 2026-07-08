from __future__ import annotations


def test_chat_attendance_returns_structured_response(client):
    response = client.post(
        "/chat",
        json={"message": "Show my attendance for this month.", "student_id": "S001"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["intent"] == "attendance"
    assert payload["status"] == "success"
    assert payload["tools_used"] == ["attendance_tool"]
    assert payload["response"]["data"]["attendance_percentage"] == 88.89


def test_chat_supports_multi_step_tool_execution(client):
    response = client.post(
        "/chat",
        json={
            "student_id": "S001",
            "message": (
                "Show my attendance, display my Mathematics marks, "
                "and tell me if I have any pending fees."
            ),
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "success"
    assert payload["tools_used"] == [
        "attendance_tool",
        "marks_tool",
        "fee_status_tool",
    ]
    assert len(payload["response"]["sections"]) == 3


def test_chat_uses_conversation_memory_for_follow_up(client):
    first = client.post(
        "/chat",
        json={"message": "Show my marks.", "student_id": "S001"},
    ).json()

    second = client.post(
        "/chat",
        json={
            "message": "Which one is highest?",
            "student_id": "S001",
            "conversation_id": first["conversation_id"],
        },
    )

    assert second.status_code == 200
    payload = second.json()
    assert payload["tools_used"] == ["marks_tool"]
    assert payload["response"]["data"]["highest_subject"]["subject"] == "Computer Science"


def test_chat_history_returns_previous_conversations(client):
    created = client.post(
        "/chat",
        json={"message": "Show my homework due tomorrow.", "student_id": "S001"},
    ).json()

    response = client.get(
        "/chat/history",
        params={"student_id": "S001", "conversation_id": created["conversation_id"]},
    )

    assert response.status_code == 200
    history = response.json()["history"]
    assert len(history) == 1
    assert history[0]["message"] == "Show my homework due tomorrow."


def test_chat_history_supports_bounded_latest_results(client):
    messages = [
        "Show my attendance.",
        "Show my marks.",
        "Show my pending fees.",
    ]
    for message in messages:
        response = client.post(
            "/chat",
            json={"message": message, "student_id": "S001"},
        )
        assert response.status_code == 200

    response = client.get(
        "/chat/history",
        params={"student_id": "S001", "limit": 2},
    )

    assert response.status_code == 200
    history_messages = [item["message"] for item in response.json()["history"]]
    assert history_messages == messages[-2:]


def test_chat_conversations_returns_session_summaries(client):
    first = client.post(
        "/chat",
        json={"message": "Show my attendance.", "student_id": "S001"},
    )
    second = client.post(
        "/chat",
        json={"message": "Show my marks.", "student_id": "S001"},
    )

    assert first.status_code == 200
    assert second.status_code == 200

    response = client.get(
        "/chat/conversations",
        params={"student_id": "S001", "limit": 2},
    )

    assert response.status_code == 200
    conversations = response.json()["conversations"]
    assert len(conversations) == 2
    assert conversations[0]["conversation_id"] == second.json()["conversation_id"]
    assert conversations[0]["latest_message"] == "Show my marks."
    assert conversations[0]["message_count"] == 1
    assert conversations[1]["conversation_id"] == first.json()["conversation_id"]


def test_invalid_student_id_is_graceful(client):
    response = client.post(
        "/chat",
        json={"message": "Show my attendance.", "student_id": "missing"},
    )

    assert response.status_code == 400
    assert response.json()["error_code"] == "INVALID_STUDENT_ID"


def test_empty_message_is_graceful(client):
    response = client.post(
        "/chat",
        json={"message": "   ", "student_id": "S001"},
    )

    assert response.status_code == 400
    assert response.json()["error_code"] == "EMPTY_REQUEST"


def test_missing_message_field_is_graceful(client):
    response = client.post("/chat", json={"student_id": "S001"})

    assert response.status_code == 400
    assert response.json()["error_code"] == "INVALID_REQUEST"


def test_readiness_endpoint_reports_assignment_capabilities(client):
    response = client.get("/readiness")

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "ready"
    assert payload["required_tools"] == [
        "attendance_tool",
        "marks_tool",
        "fee_status_tool",
        "homework_tool",
        "timetable_tool",
    ]
    assert set(payload["required_tools"]).issubset(payload["implemented_tools"])
    bonus_names = {feature["name"] for feature in payload["bonus_features"]}
    assert {
        "Multi-step task execution",
        "Academic performance summary",
        "Smart recommendations",
        "Attendance insights",
        "Exam preparation planner",
        "Parent progress report",
    }.issubset(bonus_names)
    assert all(feature["status"] == "ready" for feature in payload["capabilities"])
    capability_names = {feature["name"] for feature in payload["capabilities"]}
    assert "Token-aware access" in capability_names
    assert payload["data_store"]["type"] == "sqlite"
    assert payload["data_store"]["tables"]["students"] >= 1
    assert payload["verification"]["coverage_floor_percent"] == 90
