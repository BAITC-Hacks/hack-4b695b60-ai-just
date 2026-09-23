from app.ai import service, trace
from app.ai.contracts import DraftAnalysis, EvidenceOut, FieldSuggestion
from app.ai.service import RoutedAIService
from app.config import Settings


def test_invalid_json_is_repaired_once(monkeypatch) -> None:
    settings = Settings(ai_provider="openai", openai_api_key="test-key", ai_max_repair_attempts=1)
    monkeypatch.setattr(service, "get_settings", lambda: settings)
    monkeypatch.setattr(service, "_mode_override", None)
    service._unavailable_until.clear()
    answers = iter(
        ["{broken", DraftAnalysis(fields=[], missing=[], questions=[], topic=None).model_dump_json()]
    )
    calls = []

    def fake_generate(*args):
        calls.append(args)
        return next(answers)

    monkeypatch.setattr(service, "generate_json", fake_generate)
    result, meta = RoutedAIService().analyze_draft("Нужен бот", None, None)
    assert len(calls) == 2
    assert meta.provider == "openai" and not meta.degraded
    assert len(meta.trace_ids) == 2
    assert trace._pending[meta.trace_ids[0]].status == "failed"
    assert len(result.questions) >= 3
    assert trace._pending[meta.trace_ids[-1]].status == "repaired"


def test_provider_failure_falls_back_to_grounded_stub(monkeypatch) -> None:
    settings = Settings(ai_provider="openai", openai_api_key="test-key")
    monkeypatch.setattr(service, "get_settings", lambda: settings)
    monkeypatch.setattr(service, "_mode_override", None)
    service._unavailable_until.clear()
    monkeypatch.setattr(
        service, "generate_json", lambda *args: (_ for _ in ()).throw(RuntimeError("offline"))
    )
    result, meta = RoutedAIService().analyze_draft("Хотим бот для клиентов", None, None)
    assert meta.provider == "stub" and meta.degraded
    assert len(meta.trace_ids) == 2
    assert trace._pending[meta.trace_ids[0]].status == "failed"
    assert trace._pending[meta.trace_ids[1]].status == "fallback"
    assert all(item.evidence for item in result.fields)


def test_two_invalid_responses_trigger_stub_after_one_repair(monkeypatch) -> None:
    settings = Settings(ai_provider="openai", openai_api_key="test-key", ai_max_repair_attempts=5)
    monkeypatch.setattr(service, "get_settings", lambda: settings)
    monkeypatch.setattr(service, "_mode_override", None)
    service._unavailable_until.clear()
    calls = []

    def invalid(*args):
        calls.append(args)
        return "{broken"

    monkeypatch.setattr(service, "generate_json", invalid)
    _, meta = RoutedAIService().analyze_draft("Нужен бот", None, None)
    assert len(calls) == 2
    assert meta.provider == "stub"
    assert [trace._pending[identifier].status for identifier in meta.trace_ids] == [
        "failed",
        "failed",
        "fallback",
    ]


def test_external_provider_only_sees_masked_contact(monkeypatch) -> None:
    settings = Settings(ai_provider="openai", openai_api_key="test-key", ai_redact_pii=True)
    monkeypatch.setattr(service, "get_settings", lambda: settings)
    monkeypatch.setattr(service, "_mode_override", None)
    service._unavailable_until.clear()
    seen = []

    def fake_generate(_name, _settings, _system, user, _schema, _repair):
        seen.append(user)
        return DraftAnalysis(
            fields=[
                FieldSuggestion(
                    field="contact",
                    value="[EMAIL_1]",
                    evidence=[EvidenceOut(source="draft", quote="[EMAIL_1]")],
                )
            ],
            missing=[],
            questions=[],
            topic=None,
        ).model_dump_json()

    monkeypatch.setattr(service, "generate_json", fake_generate)
    result, meta = RoutedAIService().analyze_draft("Контакт demo@example.com", None, None)
    assert "demo@example.com" not in seen[0]
    assert result.fields[0].value == "demo@example.com"
    assert "demo@example.com" not in trace._pending[meta.trace_ids[0]].input_redacted


def test_inspector_and_runtime_provider_routes(client) -> None:
    from app.ai.service import get_ai_service

    provider = client.put("/api/ai/provider", json={"mode": "stub"})
    assert provider.status_code == 200
    assert provider.json()["active"] == "stub"
    assert client.get("/api/health").json()["ai"]["mode"] == "stub"
    _, meta = get_ai_service().analyze_draft("Нужен бот для клиентов", None, None)
    traces = client.get("/api/ai/traces")
    assert traces.status_code == 200
    assert any(row["id"] == meta.trace_ids[0] for row in traces.json())
    prompts = client.get("/api/ai/prompts")
    assert prompts.status_code == 200
    assert {item["name"] for item in prompts.json()} == {"analyze_draft", "build_card"}
    client.put("/api/ai/provider", json={"mode": "auto"})


def test_hosted_nvidia_provider_is_not_exposed(client) -> None:
    response = client.get("/api/ai/provider")
    assert response.status_code == 200
    assert "nvidia" not in [item["name"] for item in response.json()["chain"]]
    assert client.put("/api/ai/provider", json={"mode": "nvidia"}).status_code == 422


def test_task_creation_commits_ai_trace_with_task(client) -> None:
    from sqlmodel import Session, select

    from app.db import engine
    from app.models import AITrace

    business_id = client.get("/api/businesses").json()[0]["id"]
    response = client.post(
        "/api/tasks",
        json={
            "business_id": business_id,
            "draft_text": "Хотим бот для клиентов, чтобы быстрее отвечать.",
            "topic": None,
        },
    )
    assert response.status_code == 201
    task_id = response.json()["id"]
    trace_ids = response.json()["ai"]["trace_ids"]
    with Session(engine) as session:
        rows = session.exec(select(AITrace).where(AITrace.task_id == task_id)).all()
    assert rows and rows[-1].provider == "stub"
    assert rows[-1].id in trace_ids
