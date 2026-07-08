from __future__ import annotations

import json
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]


def test_dockerfile_runs_fastapi_app():
    text = (PROJECT_ROOT / "Dockerfile").read_text(encoding="utf-8")

    assert "FROM python:3.13-slim" in text
    assert "COPY app ./app" in text
    assert "COPY mock_data ./mock_data" in text
    assert '"uvicorn"' in text
    assert '"app.main:app"' in text
    assert "LLM_PROVIDER=disabled" in text


def test_compose_exposes_api_and_persists_data():
    text = (PROJECT_ROOT / "docker-compose.yml").read_text(encoding="utf-8")

    assert "8000:8000" in text
    assert "school_ai_data:/data" in text
    assert "DATABASE_URL: sqlite:////data/school_erp.db" in text
    assert "LLM_PROVIDER: ${LLM_PROVIDER:-disabled}" in text
    assert "/health" in text


def test_dockerignore_excludes_runtime_artifacts():
    text = (PROJECT_ROOT / ".dockerignore").read_text(encoding="utf-8")

    assert "school_erp.db" in text
    assert "logs/*.log" in text
    assert ".env" in text
    assert "tests/" in text


def test_demo_script_exercises_core_flow():
    text = (PROJECT_ROOT / "scripts" / "demo_requests.ps1").read_text(encoding="utf-8")

    assert "/health" in text
    assert "/chat" in text
    assert "/logs" in text
    assert "conversation_id" in text
    assert "Show my attendance, Mathematics marks, and pending fees." in text


def test_local_server_script_starts_offline_demo():
    text = (PROJECT_ROOT / "scripts" / "start_local_server.ps1").read_text(encoding="utf-8")

    assert 'LlmProvider = "disabled"' in text
    assert "$env:LLM_PROVIDER = $LlmProvider" in text
    assert "python -m app.utils.seed_db" in text
    assert "python -m uvicorn app.main:app" in text
    assert "--host $HostName --port $Port" in text


def test_ci_workflow_runs_project_quality_gate():
    text = (PROJECT_ROOT / ".github" / "workflows" / "ci.yml").read_text(encoding="utf-8")

    assert "actions/checkout@v4" in text
    assert "actions/setup-python@v5" in text
    assert "python -m compileall app tests" in text
    assert "python -m ruff check ." in text
    assert "python scripts/export_openapi.py" in text
    assert "python -m pytest --cov=app --cov-fail-under=90 -q" in text
    assert "docker compose config --quiet" in text
    assert "LLM_PROVIDER: disabled" in text


def test_http_collection_covers_core_and_bonus_requests():
    text = (PROJECT_ROOT / "api_examples.http").read_text(encoding="utf-8")

    assert "GET {{baseUrl}}/health" in text
    assert "GET {{baseUrl}}/readiness" in text
    assert "POST {{baseUrl}}/chat" in text
    assert "X-ERP-Auth-Token: {{authToken}}" in text
    assert "Show my attendance, Mathematics marks, and pending fees." in text
    assert "Which one is highest?" in text
    assert "Summarize my academic performance this semester." in text
    assert "Can I maintain 90% attendance this semester?" in text
    assert "My exams start in 15 days. Create a study plan." in text
    assert "GET {{baseUrl}}/chat/conversations" in text
    assert "GET {{baseUrl}}/logs" in text


def test_postman_collection_covers_evaluator_flow():
    collection_path = PROJECT_ROOT / "postman_collection.json"
    collection = json.loads(collection_path.read_text(encoding="utf-8"))
    text = json.dumps(collection)

    assert collection["info"]["schema"].endswith("/collection/v2.1.0/collection.json")
    assert {variable["key"] for variable in collection["variable"]}.issuperset(
        {"baseUrl", "userId", "studentId", "conversationId", "authToken"}
    )
    assert "{{baseUrl}}/health" in text
    assert "{{baseUrl}}/readiness" in text
    assert "{{baseUrl}}/users" in text
    assert "{{baseUrl}}/students?user_id={{userId}}" in text
    assert "{{baseUrl}}/tools" in text
    assert "{{baseUrl}}/chat" in text
    assert "Show my attendance, Mathematics marks, and pending fees." in text
    assert "X-ERP-Auth-Token" in text
    assert "Show my marks." in text
    assert "pm.collectionVariables.set('conversationId'" in text
    assert "Which one is highest?" in text
    assert "Summarize my academic performance this semester." in text
    assert "Can I maintain 90% attendance this semester?" in text
    assert "My exams start in 15 days. Create a study plan." in text
    assert "Generate a parent progress report." in text
    assert "{{baseUrl}}/chat/history?user_id={{userId}}&student_id={{studentId}}&limit=20" in text
    assert "{{baseUrl}}/chat/conversations?user_id={{userId}}&student_id={{studentId}}&limit=20" in text
    assert "{{baseUrl}}/logs?user_id={{userId}}&student_id={{studentId}}&limit=10" in text
    assert "Tell me a joke about school." in text


def test_openapi_export_file_is_current_and_covers_routes():
    from app.main import app

    exported = json.loads((PROJECT_ROOT / "openapi.json").read_text(encoding="utf-8"))
    current = json.loads(json.dumps(app.openapi()))

    assert exported == current
    assert exported["info"]["title"] == "AI School ERP Assistant"
    assert exported["paths"]["/auth/login"]["post"]["tags"] == ["auth"]
    assert exported["paths"]["/readiness"]["get"]["tags"] == ["system"]
    assert exported["paths"]["/dashboard"]["get"]["tags"] == ["dashboard"]
    assert exported["paths"]["/chat"]["post"]["tags"] == ["chat"]
    assert exported["paths"]["/chat/conversations"]["get"]["tags"] == ["chat"]
    assert exported["paths"]["/chat/history"]["get"]["tags"] == ["chat"]
    assert exported["paths"]["/logs"]["get"]["tags"] == ["logs"]
    assert "ChatResponse" in exported["components"]["schemas"]
    assert "ChatConversationsResponse" in exported["components"]["schemas"]
    assert "ReadinessResponse" in exported["components"]["schemas"]
    assert "ErrorResponse" in exported["components"]["schemas"]
    assert "AuthLoginResponse" in exported["components"]["schemas"]
    assert "DashboardResponse" in exported["components"]["schemas"]


def test_openapi_export_script_is_documented():
    readme = (PROJECT_ROOT / "README.md").read_text(encoding="utf-8")
    script = (PROJECT_ROOT / "scripts" / "export_openapi.py").read_text(encoding="utf-8")

    assert "Use `openapi.json` for a static API contract." in readme
    assert "python scripts/export_openapi.py" in readme
    assert "def export_openapi" in script
    assert 'PROJECT_ROOT / "openapi.json"' in script


def test_env_example_documents_runtime_settings():
    text = (PROJECT_ROOT / ".env.example").read_text(encoding="utf-8")

    assert "DATABASE_URL=sqlite:///school_erp.db" in text
    assert "LLM_PROVIDER=ollama" in text
    assert "OLLAMA_MODEL=llama3.1" in text
    assert "OPENAI_API_KEY=" in text
    assert "GEMINI_API_KEY=" in text
    assert "APP_TIMEZONE=Asia/Calcutta" in text
    assert "LOG_FILE_PATH=logs/assistant.log" in text
    assert "MOCK_DATA_DIR=mock_data" in text
    assert "AUTO_SEED=true" in text


def test_coverage_threshold_is_configured():
    text = (PROJECT_ROOT / "pyproject.toml").read_text(encoding="utf-8")

    assert "[tool.coverage.run]" in text
    assert 'source = ["app"]' in text
    assert "[tool.coverage.report]" in text
    assert "fail_under = 90" in text
