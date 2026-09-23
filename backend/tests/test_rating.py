import pytest

from app.domain.card import empty_card
from app.domain.fields import CRITERIA, level_for
from app.domain.rating import CHECKS, compute_rating, field_gain

STEP_1 = {
    "title": "Чат-бот для клиентов",
    "need": "Меньше звонков клиентов в колл-центр",
    "users": "Клиенты",
    "expected_result": "Чат-бот для клиентов",
}
STEP_2 = {
    **STEP_1,
    "context": "Колл-центр получает 300–400 звонков в день, 60% — вопросы о статусе доставки и сроках.",
    "need": "Снизить число звонков в колл-центр: бот должен закрывать обращения о статусе доставки",
    "data": (
        "Есть выгрузка обращений из CRM за 6 месяцев — около 12 000 записей в Excel, "
        "плюс FAQ на 40 вопросов. Данные обезличим и дадим доступ после NDA."
    ),
    "success_criteria": (
        "Бот самостоятельно закрывает не менее 40% обращений о статусе доставки, "
        "среднее время ответа — до 10 секунд."
    ),
}
STEP_3 = {
    **STEP_2,
    "constraints": "Пилот нужен за 6 недель, канал — Telegram, интеграция с нашей CRM через REST API.",
    "contact": "Айгерим, руководитель клиентского сервиса, aigerim@dala.example.com",
    "interaction_format": "Созвон раз в неделю, оперативные вопросы — в Telegram-чате.",
}
STEP_4 = {**STEP_3, "users": "Клиенты, ожидающие доставку, и операторы колл-центра"}


def make_card(values: dict[str, str], status: str = "confirmed") -> dict:
    card = empty_card()
    for field, value in values.items():
        card[field] = {**card[field], "value": value, "status": status}
    return card


def test_checks_sum_to_criterion_weights():
    for criterion in CRITERIA:
        assert sum(c.points for c in CHECKS if c.criterion == criterion.key) == criterion.weight
    assert sum(c.points for c in CHECKS) == 100
    assert len(CHECKS) == 18


def test_empty_card():
    rating = compute_rating(empty_card())
    assert rating.score == 0
    assert rating.potential_score == 0
    assert rating.level.key == "draft"
    assert len(rating.missing) == 18
    assert rating.next_level is not None and rating.next_level.points_needed == 40


def test_suggested_fields_give_potential_only():
    rating = compute_rating(make_card(STEP_1, status="suggested"))
    assert rating.score == 0
    assert rating.potential_score == 27


@pytest.mark.parametrize(
    ("values", "expected_score", "expected_level"),
    [(STEP_1, 27, "draft"), (STEP_2, 76, "ready"), (STEP_3, 96, "priority"), (STEP_4, 100, "priority")],
)
def test_demo_steps(values, expected_score, expected_level):
    rating = compute_rating(make_card(values))
    assert rating.score == expected_score
    assert rating.level.key == expected_level


def test_breakdown_is_consistent():
    rating = compute_rating(make_card(STEP_3))
    assert len(rating.breakdown) == 7
    assert sum(item.max for item in rating.breakdown) == 100
    assert all(item.earned <= item.max for item in rating.breakdown)
    assert sum(item.earned for item in rating.breakdown) == rating.score
    assert [item.check_id for item in rating.missing] == ["users.specific"]


def test_perfect_card_achievements():
    rating = compute_rating(make_card(STEP_4))
    assert all(achievement.earned for achievement in rating.achievements)
    assert rating.next_level is None
    assert rating.missing == []


def test_missing_sorted_by_gain():
    gains = [item.points_gain for item in compute_rating(make_card(STEP_1)).missing]
    assert gains == sorted(gains, reverse=True)


def test_delta():
    assert compute_rating(make_card(STEP_2), previous_score=27).delta == 49


def test_field_gain():
    card = make_card(STEP_1)
    assert field_gain(card, "data") == 20
    assert field_gain(card, "need") == 4
    assert field_gain(card, "expected_result") == 0


@pytest.mark.parametrize(
    ("score", "level"),
    [
        (0, "draft"),
        (39, "draft"),
        (40, "working"),
        (69, "working"),
        (70, "ready"),
        (89, "ready"),
        (90, "priority"),
        (100, "priority"),
    ],
)
def test_level_boundaries(score, level):
    assert level_for(score).key == level
