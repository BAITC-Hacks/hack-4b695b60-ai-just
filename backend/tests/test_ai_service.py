from app.ai import service, trace
from app.ai.contracts import CardBuild, DraftAnalysis, EvidenceOut, FieldSuggestion, QAPair
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
                    value="Контакт [EMAIL_1]",
                    evidence=[EvidenceOut(source="draft", quote="Контакт [EMAIL_1]")],
                )
            ],
            missing=[],
            questions=[],
            topic=None,
        ).model_dump_json()

    monkeypatch.setattr(service, "generate_json", fake_generate)
    result, meta = RoutedAIService().analyze_draft("Контакт demo@example.com", None, None)
    assert "demo@example.com" not in seen[0]
    assert result.fields[0].value == "Контакт demo@example.com"
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


def test_unsupported_external_facts_are_traced_and_left_for_manual_input(monkeypatch) -> None:
    settings = Settings(ai_provider="openai", openai_api_key="test-key")
    monkeypatch.setattr(service, "get_settings", lambda: settings)
    monkeypatch.setattr(service, "_mode_override", None)
    service._unavailable_until.clear()
    invented = FieldSuggestion(
        field="data",
        value="Компания использует PostgreSQL и предоставляет полную историю заказов.",
        evidence=[EvidenceOut(source="draft", quote="Нужен бот для клиентов")],
    )
    answers = iter(
        [
            DraftAnalysis(fields=[invented], missing=[], questions=[], topic=None).model_dump_json(),
            CardBuild(fields=[invented], unresolved=[]).model_dump_json(),
        ]
    )
    monkeypatch.setattr(service, "generate_json", lambda *args: next(answers))
    ai = RoutedAIService()
    result, meta = ai.analyze_draft("Нужен бот для клиентов", None, None)
    assert result.fields == []
    assert "data" in result.missing
    assert len(result.questions) >= 3
    assert (
        trace._pending[meta.trace_ids[-1]].grounding_rejected[0]["reason"] == "value_not_supported_by_quotes"
    )
    card, meta = ai.build_card(
        "Нужен бот для клиентов",
        [QAPair(question_id="q1", field="data", question="Какие данные?", answer="Пока неизвестно")],
        {},
        None,
    )
    assert card.fields == []
    assert "data" in card.unresolved
    assert trace._pending[meta.trace_ids[-1]].grounding_rejected


def test_guard_preserves_offline_demo_extraction() -> None:
    from app.domain.card import apply_suggestions, empty_card
    from app.domain.rating import compute_rating
    from app.models import utcnow
    from app.services.task_service import suggestions_to_tuples

    result, _ = RoutedAIService().analyze_draft(
        "Хотим чат-бота для клиентов, чтобы меньше звонили в колл-центр.", None, None
    )
    assert {field.field for field in result.fields} == {"title", "users", "need", "expected_result"}
    card, _ = apply_suggestions(empty_card(), suggestions_to_tuples(result.fields), utcnow())
    assert compute_rating(card).potential_score == 31


def test_contacts_in_questions_are_masked_before_external_build(monkeypatch) -> None:
    settings = Settings(ai_provider="openai", openai_api_key="test-key")
    monkeypatch.setattr(service, "get_settings", lambda: settings)
    monkeypatch.setattr(service, "_mode_override", None)
    service._unavailable_until.clear()
    seen = []

    def fake_generate(_name, _settings, _system, user, _schema, _repair):
        seen.append(user)
        return CardBuild(fields=[], unresolved=[]).model_dump_json()

    monkeypatch.setattr(service, "generate_json", fake_generate)
    _, meta = RoutedAIService().build_card(
        "Нужен бот. Контакт demo@example.com.",
        [
            QAPair(
                question_id="q1",
                field="interaction_format",
                question="Можно писать на demo@example.com, other@example.com или @demo_team?",
                answer="Раз в неделю, телефон +7 700 123 45 67.",
            )
        ],
        {},
        None,
    )
    assert len(seen) == 1
    for contact in ("demo@example.com", "other@example.com", "@demo_team", "+7 700 123 45 67"):
        assert contact not in seen[0]
        assert contact not in trace._pending[meta.trace_ids[-1]].input_redacted
    assert seen[0].count("[EMAIL_1]") == 2
    assert "[EMAIL_2]" in seen[0]


def test_stub_preserves_negative_role_and_contact_context() -> None:
    result, _ = RoutedAIService().analyze_draft(
        "Решение нужно только менеджерам, не клиентам. Адрес old@example.com больше не используется.",
        None,
        None,
    )
    fields = {item.field: item.value for item in result.fields}
    assert fields["users"] == "Решение нужно только менеджерам, не клиентам."
    assert fields["contact"] == "Адрес old@example.com больше не используется."
