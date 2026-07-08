from __future__ import annotations


def test_homepage_serves_browser_chat_ui(client):
    response = client.get("/")

    assert response.status_code == 200
    assert "AI Assistant" in response.text
    assert "loginForm" in response.text
    assert "data-login-type=\"teacher\"" in response.text
    assert "data-login-type=\"parent_student\"" in response.text
    assert "dashboardView" in response.text
    assert "/static/assets/login-campus.svg" in response.text
    assert "theme-switcher" in response.text
    assert response.text.count("data-theme=") == 4
    assert response.text.count("data-window=") == 2
    assert "data-window=\"homeWindow\"" in response.text
    assert "data-window=\"chatWindow\"" in response.text
    assert "Activity</button>" not in response.text
    assert "JSON</button>" not in response.text
    assert "/static/app.js" in response.text
    assert "authToken" in response.text
    assert "downloadChatButton" in response.text
    assert "Download Chat</button>" in response.text
    assert "loadHistoryButton" in response.text
    assert "historyList" in response.text
    assert "history-panel" in response.text
    assert "<h2>Chat History</h2>" in response.text
    assert "loadConversationsButton" not in response.text
    assert "conversationList" not in response.text
    assert "loadLogsButton" not in response.text
    assert "logList" not in response.text
    assert "outputPanel" not in response.text
    assert "<h2>Output</h2>" not in response.text
    assert "<h2>Plan</h2>" not in response.text
    assert "<h2>Sessions</h2>" not in response.text
    assert "<h2>Logs</h2>" not in response.text
    assert "<h2>Tools</h2>" not in response.text
    assert "toolList" not in response.text
    assert "rawSection" not in response.text
    assert "rawResponse" not in response.text
    assert "copyRawButton" not in response.text
    assert "downloadRawButton" not in response.text


def test_static_assets_are_served(client):
    script_response = client.get("/static/app.js")
    style_response = client.get("/static/styles.css")
    art_response = client.get("/static/assets/login-campus.svg")

    assert script_response.status_code == 200
    assert "sendMessage" in script_response.text
    assert "authHeaders" in script_response.text
    assert "X-ERP-Auth-Token" in script_response.text
    assert "downloadChat" in script_response.text
    assert "buildChatTranscript" in script_response.text
    assert "text/plain;charset=utf-8" in script_response.text
    assert ".txt" in script_response.text
    assert "loadHistory" in script_response.text
    assert "/chat/history" in script_response.text
    assert "loadConversations" not in script_response.text
    assert "/chat/conversations" not in script_response.text
    assert "loadLogs" not in script_response.text
    assert "/logs" not in script_response.text
    assert "responseToText" not in script_response.text
    assert "navigator.clipboard.writeText" not in script_response.text
    assert "school-erp-response.json" not in script_response.text
    assert "scrollIntoView" not in script_response.text
    assert "applyTheme" in script_response.text
    assert "renderFocusList" in script_response.text
    assert "appendAssistantResponse" in script_response.text
    assert "createOutputContent" in script_response.text
    assert "renderHistorySummary" in script_response.text
    assert "showHistoryItem" in script_response.text
    assert "toolList" not in script_response.text
    assert "rawResponse" not in script_response.text
    assert style_response.status_code == 200
    assert ".login-view" in style_response.text
    assert ".dashboard-view" in style_response.text
    assert ".metric-grid" in style_response.text
    assert ".theme-switcher" in style_response.text
    assert ".login-art-card" in style_response.text
    assert ".output-panel" in style_response.text
    assert ".history-item" in style_response.text
    assert ".chat-output" in style_response.text
    assert ".section-heading" in style_response.text
    assert art_response.status_code == 200
    assert "<svg" in art_response.text


def test_health_endpoint_reports_ready(client):
    response = client.get("/health")

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "ok"
    assert payload["database"] == "ready"
    assert "llm_provider" in payload


def test_openapi_exposes_typed_response_schemas(client):
    response = client.get("/openapi.json")

    assert response.status_code == 200
    schemas = response.json()["components"]["schemas"]
    assert "HealthResponse" in schemas
    assert "ToolsResponse" in schemas
    assert "StudentsResponse" in schemas
    assert "UsersResponse" in schemas
    assert "LogsResponse" in schemas
    assert "AuthLoginResponse" in schemas
    assert "DashboardResponse" in schemas


def test_login_endpoint_returns_token_and_accessible_students(client):
    response = client.post(
        "/auth/login",
        json={
            "login_type": "teacher",
            "user_id": "U_TEACHER_10A",
            "password": "teacher10a",
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["auth_token"] == "token-teacher-10a"
    assert payload["user"]["role"] == "teacher"
    assert [student["student_id"] for student in payload["students"]] == ["S001"]


def test_login_rejects_wrong_login_type_or_password(client):
    wrong_type = client.post(
        "/auth/login",
        json={
            "login_type": "teacher",
            "user_id": "U_STUDENT_001",
            "password": "student001",
        },
    )
    wrong_password = client.post(
        "/auth/login",
        json={
            "login_type": "parent_student",
            "user_id": "U_STUDENT_001",
            "password": "bad-password",
        },
    )

    assert wrong_type.status_code == 401
    assert wrong_type.json()["error_code"] == "INVALID_CREDENTIALS"
    assert wrong_password.status_code == 401
    assert wrong_password.json()["error_code"] == "INVALID_CREDENTIALS"


def test_dashboard_endpoint_returns_data_driven_metrics(client):
    response = client.get(
        "/dashboard",
        headers={"X-ERP-Auth-Token": "token-student-001"},
        params={"student_id": "S001"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["user"]["role"] == "student"
    assert payload["student"]["student_id"] == "S001"
    assert "attendance_percentage" in payload["metrics"]
    assert "average_marks" in payload["metrics"]
    assert "marks_by_subject" in payload["charts"]
    assert len(payload["charts"]["marks_by_subject"]) == 6
    assert [item["label"] for item in payload["charts"]["marks_by_subject"]].count("Mathematics") == 1
    assert "timetable" in payload["recent"]


def test_tools_endpoint_exposes_manifest(client):
    response = client.get("/tools")

    assert response.status_code == 200
    tools = response.json()["tools"]
    tool_names = {tool["name"] for tool in tools}
    assert {
        "attendance_tool",
        "marks_tool",
        "fee_status_tool",
        "homework_tool",
        "timetable_tool",
        "attendance_insight_tool",
        "exam_planner_tool",
        "parent_report_tool",
    }.issubset(tool_names)


def test_students_endpoint_loads_active_students_from_data_store(client):
    response = client.get("/students")

    assert response.status_code == 200
    students = response.json()["students"]
    assert len(students) == 1
    assert students[0]["student_id"]
    assert students[0]["name"]


def test_students_endpoint_accepts_user_filter(client):
    response = client.get("/students", params={"user_id": "U_STUDENT_001"})

    assert response.status_code == 200
    assert [student["student_id"] for student in response.json()["students"]] == ["S001"]


def test_homepage_does_not_embed_mock_student_options(client):
    response = client.get("/")

    assert response.status_code == 200
    assert "<select id=\"studentId\"></select>" in response.text
    assert "Ananya" not in response.text
    assert "S001" not in response.text
