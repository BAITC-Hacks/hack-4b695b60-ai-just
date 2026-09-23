import pytest

from app.schemas import BusinessCreate, MilestoneCreate, ProposalCreate, TaskCreate

PROPOSAL = {
    "team_id": 1,
    "idea": "Прототип маршрутизации курьеров с учётом окон доставки.",
    "plan": "Собрать адреса и окна доставки, затем проверить маршруты на тестовых данных.",
    "timeline": "5 недель",
}

REQUIRED_TEXT_CASES = [
    ("/api/businesses", BusinessCreate, {"name": "Тест Компания"}, "name", 2),
    (
        "/api/tasks",
        TaskCreate,
        {"business_id": 1, "draft_text": "Нужен бот для обработки обращений клиентов."},
        "draft_text",
        10,
    ),
    ("/api/tasks/1/proposals", ProposalCreate, PROPOSAL, "idea", 20),
    ("/api/tasks/1/proposals", ProposalCreate, PROPOSAL, "plan", 20),
    ("/api/tasks/1/proposals", ProposalCreate, PROPOSAL, "timeline", 1),
    (
        "/api/proposals/1/milestones",
        MilestoneCreate,
        {"business_id": 1, "title": "Проверенный прототип"},
        "title",
        3,
    ),
]


@pytest.mark.parametrize("path,model,payload,field,minimum", REQUIRED_TEXT_CASES)
@pytest.mark.parametrize("kind", ["blank", "padded_short"])
def test_required_text_rejects_whitespace_padding(client, path, model, payload, field, minimum, kind):
    # Enough raw characters used to bypass min_length before the service stripped them.
    content = "" if kind == "blank" else "а" * (minimum - 1)
    response = client.post(path, json={**payload, field: f" \t\n{content}{' ' * 30}"})

    assert response.status_code == 422, response.text
    assert any(error["loc"] == ["body", field] for error in response.json()["detail"])


@pytest.mark.parametrize("path,model,payload,field,minimum", REQUIRED_TEXT_CASES)
def test_required_text_preserves_content_and_accepts_real_minimum(path, model, payload, field, minimum):
    multiline = "Первая строка  с пробелами\nВторая строка"
    parsed = model.model_validate({**payload, field: f" \t\n{multiline}\n "})
    assert getattr(parsed, field) == multiline

    at_minimum = "а" * minimum
    parsed = model.model_validate({**payload, field: f"  {at_minimum}  "})
    assert getattr(parsed, field) == at_minimum
