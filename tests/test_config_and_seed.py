from __future__ import annotations

from app.agents.llm import DisabledLLMClient, GeminiClient, OllamaClient, OpenAIClient, build_llm_client
from app.utils.config import get_settings, reset_settings_cache
from app.utils.seed_db import ensure_seed_data


def test_config_reads_environment_values(configured_env, monkeypatch):
    monkeypatch.setenv("OLLAMA_MODEL", "test-model")
    monkeypatch.setenv("OLLAMA_TIMEOUT_SECONDS", "1.5")
    monkeypatch.setenv("LLM_TEMPERATURE", "0.2")
    monkeypatch.setenv("OPENAI_MODEL", "openai-test-model")
    monkeypatch.setenv("GEMINI_MODEL", "gemini-test-model")
    reset_settings_cache()

    settings = get_settings()

    assert settings.ollama_model == "test-model"
    assert settings.ollama_timeout_seconds == 1.5
    assert settings.llm_temperature == 0.2
    assert settings.openai_model == "openai-test-model"
    assert settings.gemini_model == "gemini-test-model"
    assert settings.database_path.name == "test_school_erp.db"


def test_llm_provider_selection(configured_env, monkeypatch):
    monkeypatch.setenv("LLM_PROVIDER", "disabled")
    reset_settings_cache()

    assert isinstance(build_llm_client(get_settings()), DisabledLLMClient)

    monkeypatch.setenv("LLM_PROVIDER", "ollama")
    reset_settings_cache()

    assert isinstance(build_llm_client(get_settings()), OllamaClient)

    monkeypatch.setenv("LLM_PROVIDER", "openai")
    reset_settings_cache()

    assert isinstance(build_llm_client(get_settings()), OpenAIClient)

    monkeypatch.setenv("LLM_PROVIDER", "gemini")
    reset_settings_cache()

    assert isinstance(build_llm_client(get_settings()), GeminiClient)


def test_seed_creates_required_tables(database):
    rows = database.fetch_all(
        """
        SELECT name FROM sqlite_master
        WHERE type = 'table'
        """
    )
    table_names = {row["name"] for row in rows}

    assert {
        "students",
        "users",
        "user_student_access",
        "attendance",
        "marks",
        "fees",
        "homework",
        "timetable",
        "conversations",
        "chat_messages",
        "execution_logs",
    }.issubset(table_names)


def test_schema_tracks_conversation_user_ownership(database):
    conversation_columns = database.fetch_all("PRAGMA table_info(conversations)")
    message_columns = database.fetch_all("PRAGMA table_info(chat_messages)")
    user_columns = database.fetch_all("PRAGMA table_info(users)")

    assert "api_token" in {column["name"] for column in user_columns}
    assert "user_id" in {column["name"] for column in conversation_columns}
    assert "user_id" in {column["name"] for column in message_columns}


def test_ensure_seed_data_refreshes_mock_user_tokens(database):
    database.execute("UPDATE users SET api_token = NULL")

    ensure_seed_data(database, get_settings().mock_data_dir)

    user = database.fetch_one(
        "SELECT api_token FROM users WHERE user_id = ?",
        ("U_STUDENT_001",),
    )
    assert user["api_token"] == "token-student-001"
