import os
import tempfile
from pathlib import Path

_TEST_DB = Path(tempfile.gettempdir()) / "challenge_hub_test.db"

# Переменные окружения важнее .env: тесты не ходят во внешние API и не трогают рабочую БД.
os.environ.update(
    {
        "DATABASE_URL": f"sqlite:///{_TEST_DB.as_posix()}",
        "SEED_ON_STARTUP": "true",
        "AI_PROVIDER": "stub",
        "AI_PROVIDER_CHAIN": "stub",
        "EMBED_PROVIDER_CHAIN": "tfidf",
        "OPENAI_API_KEY": "",
        "NVIDIA_API_KEY": "",
        "BREV_LLM_BASE_URL": "",
    }
)

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.seed import reset_and_seed


@pytest.fixture()
def client() -> TestClient:
    reset_and_seed()
    with TestClient(app) as test_client:
        yield test_client
