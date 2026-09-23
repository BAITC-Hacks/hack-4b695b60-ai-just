def titles(items: list[dict]) -> list[str]:
    return [item["title"] for item in items]


def test_default_order_and_levels(client):
    page = client.get("/api/catalog").json()
    items = page["items"]
    assert page["total"] == 6
    assert [item["position"] for item in items] == [1, 2, 3, 4, 5, 6]
    scores = [item["score"] for item in items]
    assert scores == sorted(scores, reverse=True)

    first, last = items[0], items[-1]
    assert first["title"] == "Прогноз спроса на скоропортящиеся товары"
    assert first["level"]["key"] == "priority"
    assert first["highlighted"] is True
    assert first["proposals_count"] == 2
    assert first["published_at"].endswith("Z")
    assert last["title"] == "Оптимизация маршрутов курьеров"
    assert last["needs_clarification"] is True
    assert all(len(item["need_preview"]) <= 160 for item in items)


def test_filters_keep_global_positions(client):
    agro = client.get("/api/catalog", params={"topic": "agro"}).json()
    assert agro["total"] == 1
    assert agro["items"][0]["position"] == 2

    upper = client.get("/api/catalog", params=[("level", "ready"), ("level", "priority")]).json()
    assert upper["total"] == 3

    found = client.get("/api/catalog", params={"q": "маршрут"}).json()
    assert titles(found["items"]) == ["Оптимизация маршрутов курьеров"]

    newest = client.get("/api/catalog", params={"sort": "newest"}).json()
    assert newest["items"][0]["title"] == "Оптимизация маршрутов курьеров"

    page = client.get("/api/catalog", params={"limit": 2, "offset": 2}).json()
    assert page["total"] == 6
    assert [item["position"] for item in page["items"]] == [3, 4]

    assert client.get("/api/catalog", params={"level": "unknown"}).status_code == 422


def test_public_task_shows_only_confirmed_fields(client):
    items = client.get("/api/catalog").json()["items"]
    top = client.get(f"/api/catalog/{items[0]['id']}").json()
    assert top["position"] == 1
    assert top["rating"]["score"] == 94
    assert top["card"]["title"] == "Прогноз спроса на скоропортящиеся товары"

    weakest = client.get(f"/api/catalog/{items[-1]['id']}").json()
    assert set(weakest["card"]) == {"title", "need", "users", "expected_result"}
    assert weakest["rating"]["level"]["key"] == "draft"


def test_unpublished_task_is_not_in_public_catalog(client):
    draft = next(task for task in client.get("/api/tasks").json() if task["status"] == "clarifying")
    response = client.get(f"/api/catalog/{draft['id']}")
    assert response.status_code == 404
    assert response.json()["detail"]["code"] == "TASK_NOT_FOUND"
