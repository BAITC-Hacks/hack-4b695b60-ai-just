"""OpenAI-compatible LLM adapters. Validation and fallback live in service.py."""

import json
from typing import Any

from openai import OpenAI
from pydantic import BaseModel

from app.config import Settings


def provider_model(name: str, settings: Settings) -> str:
    return {
        "openai": settings.openai_model,
        "brev": settings.brev_llm_model,
    }[name]


def provider_available(name: str, settings: Settings) -> bool:
    return {
        "openai": bool(settings.openai_api_key),
        "brev": bool(settings.brev_llm_base_url and settings.brev_llm_api_key),
        "stub": True,
    }.get(name, False)


def _client(name: str, settings: Settings) -> OpenAI:
    if name == "openai":
        return OpenAI(
            api_key=settings.openai_api_key,
            timeout=settings.ai_timeout_seconds,
            max_retries=1,
        )
    return OpenAI(
        api_key=settings.brev_llm_api_key,
        base_url=settings.brev_llm_base_url,
        timeout=settings.ai_timeout_seconds,
        max_retries=1,
    )


def generate_json(
    name: str,
    settings: Settings,
    system: str,
    user: str,
    schema: type[BaseModel],
    repair: tuple[str, str] | None = None,
) -> str:
    """Return raw JSON text so the caller can validate and trace it."""
    messages: list[dict[str, str]] = [
        {"role": "system", "content": system},
        {"role": "user", "content": user},
    ]
    if repair is not None:
        previous, instruction = repair
        messages += [{"role": "assistant", "content": previous}, {"role": "user", "content": instruction}]

    kwargs: dict[str, Any] = {
        "model": provider_model(name, settings),
        "messages": messages,
        "response_format": {"type": "json_object"},
    }
    if name == "openai":
        kwargs["reasoning_effort"] = settings.openai_reasoning_effort
        kwargs["response_format"] = {
            "type": "json_schema",
            "json_schema": {"name": schema.__name__, "strict": False, "schema": schema.model_json_schema()},
        }
    elif name == "brev":
        kwargs["response_format"] = {
            "type": "json_schema",
            "json_schema": {"name": schema.__name__, "schema": schema.model_json_schema()},
        }
    if name == "brev":
        kwargs["extra_body"] = {"chat_template_kwargs": {"enable_thinking": False}}

    with _client(name, settings) as client:
        response = client.chat.completions.create(**kwargs)
    content = response.choices[0].message.content
    if isinstance(content, str):
        return content
    return json.dumps(content, ensure_ascii=False)
