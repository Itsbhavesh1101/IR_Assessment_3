from __future__ import annotations


def test_users_endpoint_lists_mock_erp_users(client):
    response = client.get("/users")

    assert response.status_code == 200
    users = response.json()["users"]
    roles = {user["role"] for user in users}
    assert roles == {"student", "teacher"}


def test_students_endpoint_accepts_auth_token(client):
    response = client.get(
        "/students",
        headers={"X-ERP-Auth-Token": "token-student-001"},
    )

    assert response.status_code == 200
    students = response.json()["students"]
    assert [student["student_id"] for student in students] == ["S001"]


def test_students_endpoint_filters_by_user_access(client):
    response = client.get("/students", params={"user_id": "U_STUDENT_001"})

    assert response.status_code == 200
    students = response.json()["students"]
    assert [student["student_id"] for student in students] == ["S001"]


def test_chat_accepts_auth_token_without_body_user_id(client):
    chat_response = client.post(
        "/chat",
        headers={"X-ERP-Auth-Token": "token-student-001"},
        json={
            "student_id": "S001",
            "message": "Show my marks.",
        },
    )

    assert chat_response.status_code == 200
    conversation_id = chat_response.json()["conversation_id"]

    history_response = client.get(
        "/chat/history",
        headers={"X-ERP-Auth-Token": "token-student-001"},
        params={"student_id": "S001", "conversation_id": conversation_id},
    )

    assert history_response.status_code == 200
    history = history_response.json()["history"]
    assert history[0]["user_id"] == "U_STUDENT_001"
    assert history[0]["role"] == "student"


def test_invalid_auth_token_is_graceful(client):
    response = client.get(
        "/students",
        headers={"X-ERP-Auth-Token": "not-a-token"},
    )

    assert response.status_code == 401
    assert response.json()["error_code"] == "INVALID_AUTH_TOKEN"


def test_auth_token_and_user_id_mismatch_is_graceful(client):
    response = client.post(
        "/chat",
        headers={"X-ERP-Auth-Token": "token-student-001"},
        json={
            "user_id": "U_TEACHER_10A",
            "student_id": "S001",
            "message": "Show my marks.",
        },
    )

    assert response.status_code == 403
    assert response.json()["error_code"] == "AUTH_USER_MISMATCH"


def test_chat_enforces_student_access(client):
    response = client.post(
        "/chat",
        json={
            "user_id": "U_STUDENT_001",
            "student_id": "S999",
            "message": "Show my attendance.",
        },
    )

    assert response.status_code == 403
    assert response.json()["error_code"] == "ACCESS_DENIED"


def test_chat_uses_user_role_when_user_id_is_provided(client):
    response = client.post(
        "/chat",
        json={
            "user_id": "U_STUDENT_001",
            "student_id": "S001",
            "role": "teacher",
            "message": "Show my marks.",
        },
    )

    assert response.status_code == 200
    history_response = client.get(
        "/chat/history",
        params={
            "user_id": "U_STUDENT_001",
            "conversation_id": response.json()["conversation_id"],
        },
    )
    history = history_response.json()["history"]
    assert history[0]["role"] == "student"


def test_chat_history_is_scoped_to_accessible_students(client):
    allowed = client.post(
        "/chat",
        json={
            "user_id": "U_STUDENT_001",
            "student_id": "S001",
            "message": "Show my attendance.",
        },
    )
    teacher = client.post(
        "/chat",
        json={
            "user_id": "U_TEACHER_10A",
            "student_id": "S001",
            "message": "Show my attendance.",
        },
    )

    assert allowed.status_code == 200
    assert teacher.status_code == 200

    history_response = client.get(
        "/chat/history",
        params={"user_id": "U_STUDENT_001"},
    )
    history = history_response.json()["history"]
    student_ids = {item["student_id"] for item in history}
    assert student_ids == {"S001"}


def test_chat_history_is_scoped_to_exact_user_for_shared_student(client):
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
        "/chat/history",
        params={"user_id": "U_STUDENT_001", "student_id": "S001"},
    )

    assert response.status_code == 200
    history = response.json()["history"]
    assert [item["user_id"] for item in history] == ["U_STUDENT_001"]
    assert [item["message"] for item in history] == ["Show my attendance."]


def test_chat_conversations_are_scoped_to_exact_user_for_shared_student(client):
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
        "/chat/conversations",
        params={"user_id": "U_STUDENT_001", "student_id": "S001"},
    )

    assert response.status_code == 200
    conversations = response.json()["conversations"]
    assert len(conversations) == 1
    assert conversations[0]["conversation_id"] == student_chat.json()["conversation_id"]
    assert conversations[0]["user_id"] == "U_STUDENT_001"
    assert conversations[0]["latest_message"] == "Show my attendance."


def test_history_conversation_id_can_continue_context(client):
    first_response = client.post(
        "/chat",
        json={
            "user_id": "U_STUDENT_001",
            "student_id": "S001",
            "message": "Show my marks.",
        },
    )
    conversation_id = first_response.json()["conversation_id"]

    history_response = client.get(
        "/chat/history",
        params={
            "user_id": "U_STUDENT_001",
            "student_id": "S001",
            "conversation_id": conversation_id,
        },
    )
    history = history_response.json()["history"]

    follow_up = client.post(
        "/chat",
        json={
            "user_id": "U_STUDENT_001",
            "student_id": "S001",
            "conversation_id": history[-1]["conversation_id"],
            "message": "Which one is highest?",
        },
    )

    assert follow_up.status_code == 200
    payload = follow_up.json()
    assert payload["conversation_id"] == conversation_id
    assert payload["tools_used"] == ["marks_tool"]
    assert payload["response"]["data"]["highest_subject"]["subject"] == "Computer Science"


def test_chat_denies_inaccessible_student_for_teacher(client):
    first_response = client.post(
        "/chat",
        json={
            "user_id": "U_TEACHER_10A",
            "student_id": "S001",
            "message": "Show my marks.",
        },
    )
    conversation_id = first_response.json()["conversation_id"]

    response = client.post(
        "/chat",
        json={
            "user_id": "U_TEACHER_10A",
            "student_id": "S999",
            "conversation_id": conversation_id,
            "message": "Which one is highest?",
        },
    )

    assert response.status_code == 403
    payload = response.json()
    assert payload["error_code"] == "ACCESS_DENIED"
    assert payload["details"]["student_id"] == "S999"


def test_chat_denies_cross_user_conversation_reuse_for_same_student(client):
    first_response = client.post(
        "/chat",
        json={
            "user_id": "U_STUDENT_001",
            "student_id": "S001",
            "message": "Show my marks.",
        },
    )
    conversation_id = first_response.json()["conversation_id"]

    response = client.post(
        "/chat",
        json={
            "user_id": "U_TEACHER_10A",
            "student_id": "S001",
            "conversation_id": conversation_id,
            "message": "Which one is highest?",
        },
    )

    assert response.status_code == 403
    payload = response.json()
    assert payload["error_code"] == "CONVERSATION_ACCESS_DENIED"
    assert payload["details"]["conversation_id"] == conversation_id
    assert payload["details"]["user_id"] == "U_TEACHER_10A"


def test_chat_denies_cross_role_conversation_reuse_for_anonymous_user(client):
    first_response = client.post(
        "/chat",
        json={
            "role": "student",
            "student_id": "S001",
            "message": "Show my marks.",
        },
    )
    conversation_id = first_response.json()["conversation_id"]

    response = client.post(
        "/chat",
        json={
            "role": "teacher",
            "student_id": "S001",
            "conversation_id": conversation_id,
            "message": "Which one is highest?",
        },
    )

    assert response.status_code == 403
    payload = response.json()
    assert payload["error_code"] == "CONVERSATION_ACCESS_DENIED"
    assert payload["details"]["conversation_id"] == conversation_id
    assert payload["details"]["role"] == "teacher"


def test_invalid_user_id_is_graceful(client):
    response = client.post(
        "/chat",
        json={
            "user_id": "missing-user",
            "student_id": "S001",
            "message": "Show my attendance.",
        },
    )

    assert response.status_code == 400
    assert response.json()["error_code"] == "INVALID_USER_ID"
