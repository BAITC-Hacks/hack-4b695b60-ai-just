"""LLM routing, repair, grounding and offline fallback."""

import json
import time
from functools import lru_cache
from pathlib import Path
from typing import Any

from pydantic import BaseModel, ValidationError

from app.ai.contracts import AICallMeta, AIService, CardBuild, DraftAnalysis, QAPair
from app.ai.grounding import filter_grounded
from app.ai.pii import Redaction, redact_texts
from app.ai.providers import generate_json, provider_available, provider_model
from app.ai.question_bank import MAX_QUESTIONS, MIN_QUESTIONS, select_questions
from app.ai.stub import STUB_MODEL, StubAIService
from app.ai.trace import record_trace
from app.config import Settings, get_settings
from app.domain.fields import SCORED_FIELD_KEYS, TOPIC_KEYS

PROMPT_DIR = Path(__file__).parent / "prompts"
PROMPT_VERSION = "v2"
_mode_override: str | None = None
_unavailable_until: dict[str, float] = {}


class ProviderStatus(BaseModel):
    name: str
    model: str
    available: bool


def provider_mode() -> str:
    mode = _mode_override or get_settings().ai_provider
    return mode if mode in {"auto", "openai", "brev", "stub"} else "auto"


def set_provider_mode(mode: str) -> None:
    global _mode_override
    if mode not in {"auto", "openai", "brev", "stub"}:
        raise ValueError("Недопустимый режим AI")
    _mode_override = mode
    get_settings().ai_provider = mode


def _configured_chain(settings: Settings) -> list[str]:
    mode = provider_mode()
    return (
        [mode, "stub"]
        if mode not in {"auto", "stub"}
        else ["stub"]
        if mode == "stub"
        else list(
            dict.fromkeys(
                [*(name for name in settings.ai_chain if name in {"openai", "brev", "stub"}), "stub"]
            )
        )
    )


def provider_chain() -> list[ProviderStatus]:
    settings = get_settings()
    return [
        ProviderStatus(
            name=name,
            model=STUB_MODEL if name == "stub" else provider_model(name, settings),
            available=provider_available(name, settings)
            and time.monotonic() >= _unavailable_until.get(name, 0),
        )
        for name in _configured_chain(settings)
        if name in {"openai", "brev", "stub"}
    ]


def active_provider() -> str:
    return next((item.name for item in provider_chain() if item.available), "stub")


def embeddings_chain() -> tuple[list[str], str]:
    settings = get_settings()
    available = {
        "openai": bool(settings.openai_api_key),
        "tfidf": True,
    }
    chain = [name for name in settings.embed_chain if name in {"openai", "tfidf"}]
    return chain, next((name for name in chain if available.get(name)), "tfidf")


def _prompt(operation: str) -> str:
    return (PROMPT_DIR / f"{operation}.{PROMPT_VERSION}.md").read_text(encoding="utf-8")


def prompt_info() -> list[dict[str, Any]]:
    return [
        {
            "name": name,
            "version": PROMPT_VERSION,
            "system": _prompt(name),
            "user_template": template,
            "output_schema": schema.model_json_schema(),
        }
        for name, template, schema in (
            ("analyze_draft", '{"draft":"...","allowed_topics":["..."]}', DraftAnalysis),
            ("build_card", '{"draft":"...","answers":[...],"confirmed_fields":[...]}', CardBuild),
        )
    ]


def _restore_model(model: BaseModel, redaction: Redaction, schema: type[BaseModel]) -> BaseModel:
    def restore(value: Any) -> Any:
        if isinstance(value, str):
            return redaction.restore(value)
        if isinstance(value, list):
            return [restore(item) for item in value]
        if isinstance(value, dict):
            return {key: restore(item) for key, item in value.items()}
        return value

    return schema.model_validate(restore(model.model_dump()))


def _postprocess_analysis(
    result: DraftAnalysis, draft: str, topic: str | None
) -> tuple[DraftAnalysis, list[dict[str, str]]]:
    fields, rejected = filter_grounded(result.fields, {"draft": draft})
    missing = [field for field in SCORED_FIELD_KEYS if field not in {item.field for item in fields}]
    questions = []
    used: set[str] = set()
    for question in result.questions:
        if (
            question.field not in used
            and question.field in missing
            and question.question.strip()
            and len(question.question) <= 500
            and len(question.why) <= 500
        ):
            used.add(question.field)
            questions.append(question)
    if len(questions) < MIN_QUESTIONS:
        questions.extend(
            select_questions(
                missing,
                exclude=used,
                minimum=MIN_QUESTIONS - len(questions),
                maximum=MAX_QUESTIONS - len(questions),
            )
        )
    return DraftAnalysis(
        fields=fields,
        missing=missing,
        questions=questions[:MAX_QUESTIONS],
        topic=topic if topic in TOPIC_KEYS else result.topic if result.topic in TOPIC_KEYS else None,
    ), rejected


def _postprocess_card(
    result: CardBuild, sources: dict[str, str], confirmed: dict[str, str]
) -> tuple[CardBuild, list[dict[str, str]]]:
    fields, rejected = filter_grounded(result.fields, sources, confirmed)
    unresolved = [
        field
        for field in SCORED_FIELD_KEYS
        if field not in {item.field for item in fields} and field not in confirmed
    ]
    return CardBuild(fields=fields, unresolved=unresolved), rejected


class RoutedAIService:
    def __init__(self) -> None:
        self.stub = StubAIService()

    def _run(
        self,
        operation: str,
        schema: type[DraftAnalysis] | type[CardBuild],
        payload: dict[str, Any],
        sources: dict[str, str],
        confirmed: dict[str, str],
        task_id: int | None,
    ) -> tuple[DraftAnalysis | CardBuild, AICallMeta]:
        settings = get_settings()
        chain = _configured_chain(settings)
        first = chain[0]
        trace_ids: list[int] = []
        # Questions can echo contacts restored after the preceding AI response.
        # Redact the entire input, including those questions, with one mapping.
        masked_inputs, redaction = redact_texts([json.dumps(payload, ensure_ascii=False)])
        input_redacted = masked_inputs[0]

        for name in chain:
            if name == "stub":
                started = time.monotonic()
                if operation == "analyze_draft":
                    result, _ = self.stub.analyze_draft(payload["draft"], payload.get("topic"), task_id)
                else:
                    qa = [QAPair.model_validate(item) for item in payload["answers"]]
                    result, _ = self.stub.build_card(payload["draft"], qa, confirmed, task_id)
                if isinstance(result, DraftAnalysis):
                    result, rejected = _postprocess_analysis(result, payload["draft"], payload.get("topic"))
                else:
                    result, rejected = _postprocess_card(result, sources, confirmed)
                trace_ids.append(
                    record_trace(
                        task_id=task_id,
                        operation=operation,
                        provider=name,
                        model=STUB_MODEL,
                        prompt_version=PROMPT_VERSION,
                        input_redacted=input_redacted,
                        raw_output=redaction.mask(result.model_dump_json()),
                        parsed=result.model_dump(),
                        status="fallback" if name != first else "ok",
                        errors=[],
                        grounding_rejected=rejected,
                        latency_ms=int((time.monotonic() - started) * 1000),
                    )
                )
                return result, AICallMeta(
                    provider=name, model=STUB_MODEL, degraded=name != first, trace_ids=trace_ids
                )
            if not provider_available(name, settings) or time.monotonic() < _unavailable_until.get(name, 0):
                continue

            started = time.monotonic()
            model_name = provider_model(name, settings)
            raw = ""
            errors: list[str] = []
            repaired = False
            try:
                for attempt in range(min(1, max(0, settings.ai_max_repair_attempts)) + 1):
                    attempt_started = time.monotonic()
                    repair = None
                    if attempt:
                        repaired = True
                        repair = (
                            raw,
                            f"Invalid JSON: {errors[-1]}. Return corrected JSON only; add no facts.",
                        )
                    raw = generate_json(name, settings, _prompt(operation), input_redacted, schema, repair)
                    try:
                        parsed = schema.model_validate_json(raw)
                        break
                    except ValidationError as exc:
                        errors.append(redaction.mask(str(exc)))
                        trace_ids.append(
                            record_trace(
                                task_id=task_id,
                                operation=operation,
                                provider=name,
                                model=model_name,
                                prompt_version=PROMPT_VERSION,
                                input_redacted=input_redacted,
                                raw_output=redaction.mask(raw),
                                parsed=None,
                                status="failed",
                                errors=[errors[-1]],
                                grounding_rejected=[],
                                latency_ms=int((time.monotonic() - attempt_started) * 1000),
                            )
                        )
                else:
                    raise ValueError("validation_failed")
                result = _restore_model(parsed, redaction, schema)
                if isinstance(result, DraftAnalysis):
                    result, rejected = _postprocess_analysis(result, payload["draft"], payload.get("topic"))
                else:
                    result, rejected = _postprocess_card(result, sources, confirmed)
                trace_ids.append(
                    record_trace(
                        task_id=task_id,
                        operation=operation,
                        provider=name,
                        model=model_name,
                        prompt_version=PROMPT_VERSION,
                        input_redacted=input_redacted,
                        raw_output=raw,
                        parsed=result.model_dump(),
                        status="repaired" if repaired else "fallback" if name != first else "ok",
                        errors=errors,
                        grounding_rejected=rejected,
                        latency_ms=int((time.monotonic() - attempt_started) * 1000),
                    )
                )
                return result, AICallMeta(
                    provider=name, model=model_name, degraded=name != first, trace_ids=trace_ids
                )
            except Exception as exc:
                _unavailable_until[name] = time.monotonic() + 60
                if not (isinstance(exc, ValueError) and str(exc) == "validation_failed"):
                    errors.append(type(exc).__name__)
                    trace_ids.append(
                        record_trace(
                            task_id=task_id,
                            operation=operation,
                            provider=name,
                            model=model_name,
                            prompt_version=PROMPT_VERSION,
                            input_redacted=input_redacted,
                            raw_output=redaction.mask(raw),
                            parsed=None,
                            status="failed",
                            errors=errors,
                            grounding_rejected=[],
                            latency_ms=int((time.monotonic() - started) * 1000),
                        )
                    )
        raise RuntimeError("Stub provider missing from chain")

    def analyze_draft(
        self, draft: str, topic: str | None, task_id: int | None
    ) -> tuple[DraftAnalysis, AICallMeta]:
        result, meta = self._run(
            "analyze_draft",
            DraftAnalysis,
            {"draft": draft, "topic": topic, "allowed_topics": sorted(TOPIC_KEYS)},
            {"draft": draft},
            {},
            task_id,
        )
        assert isinstance(result, DraftAnalysis)
        return result, meta

    def build_card(
        self, draft: str, qa: list[QAPair], confirmed: dict[str, str], task_id: int | None
    ) -> tuple[CardBuild, AICallMeta]:
        answers = [pair.model_dump() for pair in qa]
        sources = {"draft": draft, **{f"answer:{pair.question_id}": pair.answer for pair in qa}}
        payload = {"draft": draft, "answers": answers, "confirmed_fields": list(confirmed)}
        result, meta = self._run("build_card", CardBuild, payload, sources, confirmed, task_id)
        assert isinstance(result, CardBuild)
        return result, meta


@lru_cache
def get_ai_service() -> AIService:
    return RoutedAIService()
