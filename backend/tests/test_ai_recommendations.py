from app.config import Settings
from app.ml import recommend as recommender
from app.models import Task, Team, utcnow


def test_only_ready_enough_published_tasks_are_recommended(monkeypatch) -> None:
    monkeypatch.setattr(recommender, "get_settings", lambda: Settings(embed_provider_chain="tfidf"))
    team = Team(name="Команда", interests=["logistics"], skills=["Python"], technologies=["Telegram"])

    def task(identifier: int, status: str, score: int) -> Task:
        return Task(
            id=identifier,
            business_id=1,
            status=status,
            score=score,
            published_at=utcnow(),
            draft_text="тест",
            card={
                "title": {"status": "confirmed", "value": "Python Telegram бот"},
                "need": {"status": "confirmed", "value": "Автоматизировать доставку"},
            },
        )

    items, method = recommender.recommend(
        team, [task(1, "published", 39), task(2, "review", 80), task(3, "published", 40)], 5
    )
    assert method == "tfidf"
    assert [item["task"].id for item in items] == [3]
    assert items[0]["matched_terms"] == ["python", "telegram"]


def test_recommendations_route_returns_catalog_items(client) -> None:
    team_id = client.get("/api/teams").json()[0]["id"]
    response = client.get(f"/api/teams/{team_id}/recommendations")
    assert response.status_code == 200
    body = response.json()
    assert body["method"] == "tfidf"
    assert body["note"]
    assert all(item["task"]["score"] >= 40 for item in body["items"])
    assert all(item["task"]["position"] >= 1 for item in body["items"])
