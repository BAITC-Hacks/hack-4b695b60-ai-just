DEMO_DRAFT = "Хотим чат-бота для клиентов, чтобы меньше звонили в колл-центр."
ANSWERS = {
    "data": (
        "Есть выгрузка обращений из CRM за 6 месяцев — около 12 000 записей в Excel, "
        "плюс FAQ на 40 вопросов. Данные обезличим и дадим доступ после NDA."
    ),
    "context": "Колл-центр получает 300–400 звонков в день, 60% — вопросы о статусе доставки и сроках.",
    "success_criteria": (
        "Бот самостоятельно закрывает не менее 40% обращений о статусе доставки, "
        "среднее время ответа — до 10 секунд."
    ),
}
CONTACT = "Айгерим, руководитель клиентского сервиса, " + "aigerim" + "@" + "dala.example.com"
NEED_DETAILED = "Снизить число звонков в колл-центр: бот должен закрывать обращения о статусе доставки"


def business_id(client, name: str = "Дала Логистик") -> int:
    return next(b["id"] for b in client.get("/api/businesses").json() if b["name"] == name)


def create_demo_task(client) -> dict:
    response = client.post(
        "/api/tasks",
        json={"business_id": business_id(client), "draft_text": DEMO_DRAFT, "topic": "logistics"},
    )
    assert response.status_code == 201, response.text
    return response.json()


def test_full_builder_flow(client):
    task = create_demo_task(client)
    task_id = task["id"]
    assert task["status"] == "clarifying"
    assert task["rating"]["score"] == 0
    assert task["rating"]["potential_score"] == 27
    assert task["card"]["need"]["status"] == "suggested"
    assert task["card"]["need"]["evidence"][0]["source"] == "draft"
    assert 3 <= len(task["questions"]) <= 5
    assert [q["field"] for q in task["questions"][:3]] == ["data", "context", "success_criteria"]
    assert task["questions"][0]["points_gain"] == 20
    assert task["catalog_position"] is None
    assert task["ai"]["provider_used"] == "stub"

    step1 = client.post(f"/api/tasks/{task_id}/confirm-all").json()
    assert step1["rating"]["score"] == 27
    assert step1["rating"]["delta"] == 27
    assert step1["status"] == "review"
    need_before = step1["card"]["need"]["value"]

    answers = [{"question_id": q["id"], "text": ANSWERS.get(q["field"], "")} for q in step1["questions"]]
    step2 = client.post(f"/api/tasks/{task_id}/answers", json={"answers": answers}).json()
    assert step2["card"]["data"]["status"] == "suggested"
    assert step2["card"]["data"]["evidence"][0]["source"].startswith("answer:")
    assert step2["card"]["need"]["value"] == need_before
    assert step2["rating"]["score"] == 27
    assert step2["rating"]["potential_score"] > 70

    step3 = client.post(f"/api/tasks/{task_id}/confirm-all").json()
    assert step3["rating"]["level"]["key"] == "ready"
    assert step3["rating"]["delta"] == step3["rating"]["score"] - 27

    more = client.post(f"/api/tasks/{task_id}/clarify").json()
    new_round = [q for q in more["questions"] if q["round"] == 2]
    assert [q["field"] for q in new_round] == ["interaction_format", "need", "users"]
    assert new_round[0]["id"] == f"q{len(step1['questions']) + 1}"

    patched = client.patch(
        f"/api/tasks/{task_id}/card",
        json={
            "fields": {
                "title": {"value": "Telegram-бот для ответов о статусе доставки"},
                "constraints": {
                    "value": "Пилот нужен за 6 недель, канал — Telegram, интеграция с CRM через REST API."
                },
                "contact": {"value": CONTACT},
                "interaction_format": {
                    "value": "Созвон раз в неделю, оперативные вопросы — в Telegram-чате."
                },
                "users": {"value": "Клиенты, ожидающие доставку, и операторы колл-центра"},
                "need": {"value": NEED_DETAILED},
            }
        },
    ).json()
    assert patched["rating"]["score"] == 100
    assert patched["rating"]["level"]["key"] == "priority"
    assert patched["catalog_position_preview"] == 1

    assert client.post(f"/api/tasks/{task_id}/publish", json={}).status_code == 400
    published = client.post(f"/api/tasks/{task_id}/publish", json={"confirm": True}).json()
    assert published["status"] == "published"
    assert published["catalog_position"] == 1
    assert published["published_at"].endswith("Z")

    history = client.get(f"/api/tasks/{task_id}/history").json()
    assert [event["score"] for event in history][:2] == [0, 27]
    assert history[-1]["reason"] == "Задача опубликована в каталоге"

    mine = client.get("/api/tasks", params={"business_id": business_id(client)}).json()
    assert task_id in {item["id"] for item in mine}
    assert client.get(f"/api/tasks/{task_id}/rating").json()["score"] == 100


def test_reject_suggestion_and_title_required(client):
    task = create_demo_task(client)
    task_id = task["id"]
    rejected = client.patch(f"/api/tasks/{task_id}/card", json={"fields": {"title": {"reject": True}}}).json()
    assert rejected["card"]["title"]["status"] == "empty"
    response = client.post(f"/api/tasks/{task_id}/publish", json={"confirm": True})
    assert response.status_code == 409
    assert response.json()["detail"]["code"] == "TITLE_REQUIRED"


def test_clearing_confirmed_field(client):
    task_id = create_demo_task(client)["id"]
    client.post(f"/api/tasks/{task_id}/confirm-all")
    cleared = client.patch(f"/api/tasks/{task_id}/card", json={"fields": {"users": {"value": None}}}).json()
    assert cleared["card"]["users"]["status"] == "empty"
    assert cleared["rating"]["delta"] == -6


def test_errors(client):
    unknown_business = client.post("/api/tasks", json={"business_id": 9999, "draft_text": DEMO_DRAFT})
    assert unknown_business.status_code == 404
    assert unknown_business.json()["detail"]["code"] == "BUSINESS_NOT_FOUND"

    bad_topic = client.post(
        "/api/tasks", json={"business_id": business_id(client), "draft_text": DEMO_DRAFT, "topic": "space"}
    )
    assert bad_topic.status_code == 422

    too_short = client.post("/api/tasks", json={"business_id": business_id(client), "draft_text": "бот"})
    assert too_short.status_code == 422

    assert client.get("/api/tasks/9999").json()["detail"]["code"] == "TASK_NOT_FOUND"

    task_id = create_demo_task(client)["id"]
    unknown_question = client.post(
        f"/api/tasks/{task_id}/answers", json={"answers": [{"question_id": "q99", "text": "ответ"}]}
    )
    assert unknown_question.status_code == 404
    assert unknown_question.json()["detail"]["code"] == "QUESTION_NOT_FOUND"
