from __future__ import annotations

import pytest

from app.agents.llm import GeminiClient, OllamaClient, OpenAIClient
from app.utils.config import get_settings, reset_settings_cache


class FakeHttpResponse:
    def __init__(self, payload: dict) -> None:
        self.payload = payload

    def raise_for_status(self) -> None:
        return None

    def json(self) -> dict:
        return self.payload


def test_ollama_client_posts_json_prompt(configured_env, monkeypatch):
    captured = {}
    monkeypatch.setenv("LLM_PROVIDER", "ollama")
    reset_settings_cache()

    def fake_post(url, **kwargs):
        captured["url"] = url
        captured["json"] = kwargs["json"]
        captured["timeout"] = kwargs["timeout"]
        return FakeHttpResponse({"response": '{"steps": []}'})

    monkeypatch.setattr("app.agents.llm.httpx.post", fake_post)

    payload = OllamaClient(get_settings()).generate_json("plan this")

    assert payload == {"steps": []}
    assert captured["url"].endswith("/api/generate")
    assert captured["json"]["format"] == "json"
    assert captured["json"]["options"]["temperature"] == 0


def test_openai_client_posts_chat_completion(configured_env, monkeypatch):
    captured = {}
    monkeypatch.setenv("LLM_PROVIDER", "openai")
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    monkeypatch.setenv("OPENAI_MODEL", "test-openai-model")
    reset_settings_cache()

    def fake_post(url, **kwargs):
        captured["url"] = url
        captured["headers"] = kwargs["headers"]
        captured["json"] = kwargs["json"]
        return FakeHttpResponse(
            {
                "choices": [
                    {"message": {"content": '{"steps": [{"tool": "marks_tool"}]}'}}
                ]
            }
        )

    monkeypatch.setattr("app.agents.llm.httpx.post", fake_post)

    payload = OpenAIClient(get_settings()).generate_json("plan this")

    assert payload["steps"][0]["tool"] == "marks_tool"
    assert captured["url"].endswith("/chat/completions")
    assert captured["headers"]["Authorization"] == "Bearer test-key"
    assert captured["json"]["model"] == "test-openai-model"
    assert captured["json"]["response_format"] == {"type": "json_object"}


def test_gemini_client_posts_generate_content(configured_env, monkeypatch):
    captured = {}
    monkeypatch.setenv("LLM_PROVIDER", "gemini")
    monkeypatch.setenv("GEMINI_API_KEY", "test-key")
    monkeypatch.setenv("GEMINI_MODEL", "test-gemini-model")
    reset_settings_cache()

    def fake_post(url, **kwargs):
        captured["url"] = url
        captured["params"] = kwargs["params"]
        captured["json"] = kwargs["json"]
        return FakeHttpResponse(
            {
                "candidates": [
                    {
                        "content": {
                            "parts": [{"text": '{"steps": [{"tool": "attendance_tool"}]}'}]
                        }
                    }
                ]
            }
        )

    monkeypatch.setattr("app.agents.llm.httpx.post", fake_post)

    payload = GeminiClient(get_settings()).generate_json("plan this")

    assert payload["steps"][0]["tool"] == "attendance_tool"
    assert captured["url"].endswith("/models/test-gemini-model:generateContent")
    assert captured["params"] == {"key": "test-key"}
    assert captured["json"]["generationConfig"]["responseMimeType"] == "application/json"


def test_openai_client_requires_api_key(configured_env, monkeypatch):
    monkeypatch.setenv("LLM_PROVIDER", "openai")
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    reset_settings_cache()

    with pytest.raises(ValueError, match="OPENAI_API_KEY"):
        OpenAIClient(get_settings()).generate_json("plan this")


def test_gemini_client_requires_api_key(configured_env, monkeypatch):
    monkeypatch.setenv("LLM_PROVIDER", "gemini")
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    reset_settings_cache()

    with pytest.raises(ValueError, match="GEMINI_API_KEY"):
        GeminiClient(get_settings()).generate_json("plan this")
