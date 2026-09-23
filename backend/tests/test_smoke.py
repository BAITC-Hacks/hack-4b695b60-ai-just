def test_health(client):
    body = client.get("/api/health").json()
    assert body["status"] == "ok"
    chain = {item["name"]: item for item in body["ai"]["chain"]}
    assert chain["stub"]["available"] is True
    assert body["embeddings"]["active"] == "tfidf"


def test_meta(client):
    body = client.get("/api/meta").json()
    assert len(body["fields"]) == 10
    assert sum(item["weight"] for item in body["criteria"]) == 100
    levels = body["levels"]
    assert [level["key"] for level in levels] == ["draft", "working", "ready", "priority"]
    assert levels[0]["min"] == 0 and levels[-1]["max"] == 100
    assert all(prev["max"] + 1 == nxt["min"] for prev, nxt in zip(levels, levels[1:], strict=False))
    assert len(body["topics"]) == 10


def test_participants(client):
    businesses = client.get("/api/businesses").json()
    teams = client.get("/api/teams").json()
    assert len(businesses) >= 6
    assert len(teams) >= 6
    assert {"Дала Логистик", "Жибек Маркет"} <= {item["name"] for item in businesses}
    assert "Nomad AI" in {item["name"] for item in teams}


def test_create_business(client):
    response = client.post("/api/businesses", json={"name": "Тест Компани", "industry": "other"})
    assert response.status_code == 201
    assert response.json()["name"] == "Тест Компани"


def test_team_not_found_uses_domain_error_format(client):
    response = client.get("/api/teams/9999")
    assert response.status_code == 404
    assert response.json() == {"detail": {"code": "TEAM_NOT_FOUND", "message": "Команда не найдена"}}


def test_admin_reset(client):
    client.post("/api/businesses", json={"name": "Временная"})
    assert client.post("/api/admin/reset").json() == {"ok": True}
    assert "Временная" not in {item["name"] for item in client.get("/api/businesses").json()}
