from __future__ import annotations

import json
from typing import Any, Protocol

import httpx

from app.utils.config import Settings


class LLMClient(Protocol):
    def generate_json(self, prompt: str) -> dict[str, Any]:
        """Return a JSON object generated from the prompt."""


class OllamaClient:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    def generate_json(self, prompt: str) -> dict[str, Any]:
        response = httpx.post(
            f"{self.settings.ollama_base_url.rstrip('/')}/api/generate",
            json={
                "model": self.settings.ollama_model,
                "prompt": prompt,
                "stream": False,
                "format": "json",
                "options": {"temperature": self.settings.llm_temperature},
            },
            timeout=self.settings.ollama_timeout_seconds,
        )
        response.raise_for_status()
        payload = response.json()
        generated = payload.get("response", "{}")
        parsed = json.loads(generated)
        if not isinstance(parsed, dict):
            raise ValueError("LLM response must be a JSON object.")
        return parsed


class OpenAIClient:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    def generate_json(self, prompt: str) -> dict[str, Any]:
        if not self.settings.openai_api_key:
            raise ValueError("OPENAI_API_KEY is required when LLM_PROVIDER=openai.")

        response = httpx.post(
            f"{self.settings.openai_base_url.rstrip('/')}/chat/completions",
            headers={"Authorization": f"Bearer {self.settings.openai_api_key}"},
            json={
                "model": self.settings.openai_model,
                "messages": [
                    {
                        "role": "system",
                        "content": "Return only a JSON object. Do not include markdown.",
                    },
                    {"role": "user", "content": prompt},
                ],
                "temperature": self.settings.llm_temperature,
                "response_format": {"type": "json_object"},
            },
            timeout=self.settings.openai_timeout_seconds,
        )
        response.raise_for_status()
        payload = response.json()
        content = payload["choices"][0]["message"]["content"]
        parsed = json.loads(content)
        if not isinstance(parsed, dict):
            raise ValueError("OpenAI response must be a JSON object.")
        return parsed


class GeminiClient:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    def generate_json(self, prompt: str) -> dict[str, Any]:
        if not self.settings.gemini_api_key:
            raise ValueError("GEMINI_API_KEY is required when LLM_PROVIDER=gemini.")

        response = httpx.post(
            f"{self.settings.gemini_base_url.rstrip('/')}/models/"
            f"{self.settings.gemini_model}:generateContent",
            params={"key": self.settings.gemini_api_key},
            json={
                "contents": [
                    {
                        "role": "user",
                        "parts": [
                            {
                                "text": (
                                    "Return only a JSON object. Do not include markdown.\n\n"
                                    f"{prompt}"
                                )
                            }
                        ],
                    }
                ],
                "generationConfig": {
                    "temperature": self.settings.llm_temperature,
                    "responseMimeType": "application/json",
                },
            },
            timeout=self.settings.gemini_timeout_seconds,
        )
        response.raise_for_status()
        payload = response.json()
        content = payload["candidates"][0]["content"]["parts"][0]["text"]
        parsed = json.loads(content)
        if not isinstance(parsed, dict):
            raise ValueError("Gemini response must be a JSON object.")
        return parsed


class DisabledLLMClient:
    def generate_json(self, prompt: str) -> dict[str, Any]:
        raise RuntimeError("LLM client is disabled.")


def build_llm_client(settings: Settings) -> LLMClient:
    provider = settings.llm_provider.strip().lower()
    if provider == "ollama":
        return OllamaClient(settings)
    if provider == "openai":
        return OpenAIClient(settings)
    if provider == "gemini":
        return GeminiClient(settings)
    return DisabledLLMClient()
