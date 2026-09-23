"""Точка входа AI-слоя для ядра backend."""

from functools import lru_cache

from pydantic import BaseModel

from app.ai.contracts import AIService
from app.ai.stub import STUB_MODEL, STUB_PROVIDER, StubAIService
from app.config import get_settings


class ProviderStatus(BaseModel):
    name: str
    model: str
    available: bool


@lru_cache
def get_ai_service() -> AIService:
    return StubAIService()


def provider_chain() -> list[ProviderStatus]:
    settings = get_settings()
    known = {
        "openai": ProviderStatus(
            name="openai", model=settings.openai_model, available=bool(settings.openai_api_key)
        ),
        "nvidia": ProviderStatus(
            name="nvidia", model=settings.nvidia_model, available=bool(settings.nvidia_api_key)
        ),
        "brev": ProviderStatus(
            name="brev", model=settings.brev_llm_model, available=bool(settings.brev_llm_base_url)
        ),
        STUB_PROVIDER: ProviderStatus(name=STUB_PROVIDER, model=STUB_MODEL, available=True),
    }
    chain = [known[name] for name in settings.ai_chain if name in known]
    if STUB_PROVIDER not in settings.ai_chain:
        chain.append(known[STUB_PROVIDER])
    return chain


def embeddings_chain() -> tuple[list[str], str]:
    settings = get_settings()
    available = {
        "nvidia": bool(settings.nvidia_api_key),
        "openai": bool(settings.openai_api_key),
        "tfidf": True,
    }
    chain = settings.embed_chain
    active = next((name for name in chain if available.get(name)), "tfidf")
    return chain, active
