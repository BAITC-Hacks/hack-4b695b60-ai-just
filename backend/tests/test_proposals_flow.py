PROPOSAL = {
    "idea": "Сервис маршрутизации курьеров с учётом пробок и окон доставки.",
    "plan": "1) Сбор адресов и окон доставки. 2) Прототип маршрутизации. 3) Сравнение с текущими маршрутами.",
    "timeline": "5 недель",
    "prototype_url": "https://github.com/example/nomad-routes-v2",
}


def lookup(client) -> tuple[dict[str, int], dict[str, int], dict[str, int]]:
    businesses = {item["name"]: item["id"] for item in client.get("/api/businesses").json()}
    teams = {item["name"]: item["id"] for item in client.get("/api/teams").json()}
    catalog = {item["title"]: item["id"] for item in client.get("/api/catalog").json()["items"]}
    return businesses, teams, catalog


def test_proposal_decision_and_milestone_flow(client):
    businesses, teams, catalog = lookup(client)
    dala, zhibek = businesses["Дала Логистик"], businesses["Жибек Маркет"]
    nomad = teams["Nomad AI"]
    task_id = catalog["Оптимизация маршрутов курьеров"]

    created = client.post(f"/api/tasks/{task_id}/proposals", json={**PROPOSAL, "team_id": nomad})
    assert created.status_code == 201, created.text
    proposal = created.json()
    assert proposal["status"] == "submitted"
    assert proposal["team"]["name"] == "Nomad AI"
    assert proposal["task"]["title"] == "Оптимизация маршрутов курьеров"

    foreign = client.get(f"/api/tasks/{task_id}/proposals", params={"business_id": zhibek})
    assert foreign.status_code == 403
    assert foreign.json()["detail"]["code"] == "NOT_TASK_OWNER"
    listed = client.get(f"/api/tasks/{task_id}/proposals", params={"business_id": dala}).json()
    assert len(listed) == 3
    assert listed[-1]["id"] == proposal["id"]

    early = client.post(
        f"/api/proposals/{proposal['id']}/milestones",
        json={"business_id": dala, "title": "Прототип маршрутов"},
    )
    assert early.status_code == 409
    assert early.json()["detail"]["code"] == "PROPOSAL_NOT_SELECTED"

    stranger = client.post(
        f"/api/proposals/{proposal['id']}/decision", json={"business_id": zhibek, "decision": "selected"}
    )
    assert stranger.status_code == 403

    selected = client.post(
        f"/api/proposals/{proposal['id']}/decision",
        json={"business_id": dala, "decision": "selected", "comment": "Берём в пилот"},
    ).json()
    assert selected["status"] == "selected"
    assert selected["business_comment"] == "Берём в пилот"
    assert selected["decided_at"].endswith("Z")

    other = next(item for item in listed if item["team"]["name"] == "QazCode")
    rejected = client.post(
        f"/api/proposals/{other['id']}/decision", json={"business_id": dala, "decision": "rejected"}
    ).json()
    assert rejected["status"] == "rejected"

    milestone = client.post(
        f"/api/proposals/{proposal['id']}/milestones",
        json={"business_id": dala, "title": "Прототип маршрутов", "points": 20},
    ).json()
    assert milestone["status"] == "pending"
    confirmed = client.post(f"/api/milestones/{milestone['id']}/confirm", json={"business_id": dala}).json()
    assert confirmed["milestone"]["status"] == "confirmed"
    assert confirmed["team"]["progress_points"] == 20

    again = client.post(f"/api/milestones/{milestone['id']}/confirm", json={"business_id": dala})
    assert again.status_code == 409
    assert again.json()["detail"]["code"] == "MILESTONE_ALREADY_CONFIRMED"

    board = client.get("/api/leaderboard/teams").json()["items"]
    assert [row["team"]["name"] for row in board[:2]] == ["Nomad AI", "Steppe Data"]
    assert board[0]["rank"] == 1
    assert board[0]["confirmed_milestones"] == 1

    mine = client.get(f"/api/teams/{nomad}/proposals").json()
    assert mine[0]["id"] == proposal["id"]
    assert mine[0]["milestones"][0]["status"] == "confirmed"

    catalog_item = next(i for i in client.get("/api/catalog").json()["items"] if i["id"] == task_id)
    assert catalog_item["proposals_count"] == 3


def test_proposal_validation(client):
    businesses, teams, catalog = lookup(client)
    nomad = teams["Nomad AI"]
    task_id = catalog["Прогноз спроса на скоропортящиеся товары"]

    draft = next(task for task in client.get("/api/tasks").json() if task["status"] == "clarifying")
    unpublished = client.post(f"/api/tasks/{draft['id']}/proposals", json={**PROPOSAL, "team_id": nomad})
    assert unpublished.status_code == 409
    assert unpublished.json()["detail"]["code"] == "TASK_NOT_PUBLISHED"

    bad_url = client.post(
        f"/api/tasks/{task_id}/proposals", json={**PROPOSAL, "team_id": nomad, "prototype_url": "не ссылка"}
    )
    assert bad_url.status_code == 422

    short = client.post(f"/api/tasks/{task_id}/proposals", json={**PROPOSAL, "team_id": nomad, "idea": "бот"})
    assert short.status_code == 422

    no_link = client.post(
        f"/api/tasks/{task_id}/proposals", json={**PROPOSAL, "team_id": nomad, "prototype_url": None}
    )
    assert no_link.status_code == 201

    unknown_team = client.post(f"/api/tasks/{task_id}/proposals", json={**PROPOSAL, "team_id": 9999})
    assert unknown_team.json()["detail"]["code"] == "TEAM_NOT_FOUND"

    missing = client.post("/api/proposals/9999/decision", json={"business_id": 1, "decision": "selected"})
    assert missing.json()["detail"]["code"] == "PROPOSAL_NOT_FOUND"


def test_business_leaderboard(client):
    items = client.get("/api/leaderboard/businesses").json()["items"]
    assert len(items) == 6
    assert items[0]["business"]["name"] == "Жибек Маркет"
    assert items[0]["avg_score"] == 94.0
    assert items[-1]["business"]["name"] == "Дала Логистик"
