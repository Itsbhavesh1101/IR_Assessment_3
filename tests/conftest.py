from __future__ import annotations

import shutil
from collections.abc import Iterator
from pathlib import Path
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from app.services.database import Database
from app.utils.config import get_settings, reset_settings_cache
from app.utils.seed_db import seed_database


@pytest.fixture()
def configured_env(monkeypatch) -> Iterator[None]:
    test_root = Path(__file__).resolve().parents[1] / ".test_tmp" / str(uuid4())
    test_root.mkdir(parents=True, exist_ok=True)
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{test_root / 'test_school_erp.db'}")
    monkeypatch.setenv("LOG_FILE_PATH", str(test_root / "assistant.log"))
    monkeypatch.setenv("LLM_PROVIDER", "disabled")
    monkeypatch.setenv("APP_TIMEZONE", "Asia/Calcutta")
    monkeypatch.setenv("AUTO_SEED", "true")
    reset_settings_cache()
    yield
    reset_settings_cache()
    shutil.rmtree(test_root, ignore_errors=True)


@pytest.fixture()
def database(configured_env) -> Database:
    settings = get_settings()
    db = Database(settings)
    seed_database(db, settings.mock_data_dir, reset=True)
    return db


@pytest.fixture()
def client(configured_env) -> Iterator[TestClient]:
    from app.main import app

    with TestClient(app) as test_client:
        yield test_client
