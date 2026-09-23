import json

from sqlmodel import Session, select

from app.config import get_settings
from app.db import engine
from app.models import Milestone, Proposal, Question, Task, Team


def test_seed_declared_readiness_matches_engine(client):
    cards = json.loads((get_settings().seed_dir / "cards.json").read_text(encoding="utf-8"))
    declared = {card["card"]["title"]: (card["readiness_score"], card["expected_level"]) for card in cards}
    with Session(engine) as session:
        published = session.exec(select(Task).where(Task.status == "published")).all()
        actual = {task.card["title"]["value"]: (task.score, task.level) for task in published}
    assert actual == declared


def test_seed_volumes(client):
    with Session(engine) as session:
        tasks = session.exec(select(Task)).all()
        assert len([task for task in tasks if task.status == "published"]) == 6
        assert len([task for task in tasks if task.status == "clarifying"]) == 6
        assert len(session.exec(select(Proposal)).all()) == 8
        assert len(session.exec(select(Milestone)).all()) == 2


def test_seed_cards_cover_all_levels(client):
    with Session(engine) as session:
        published = session.exec(select(Task).where(Task.status == "published")).all()
        scores = {task.card["title"]["value"]: (task.score, task.level) for task in published}
    assert scores["Прогноз спроса на скоропортящиеся товары"] == (94, "priority")
    assert {level for _, level in scores.values()} == {"draft", "working", "ready", "priority"}
    assert max(score for score, _ in scores.values()) < 96


def test_seed_drafts_have_questions(client):
    with Session(engine) as session:
        drafts = session.exec(select(Task).where(Task.status == "clarifying")).all()
        for task in drafts:
            questions = session.exec(select(Question).where(Question.task_id == task.id)).all()
            assert 3 <= len(questions) <= 5
            assert [q.key for q in questions] == [f"q{i}" for i in range(1, len(questions) + 1)]
            # AI may omit a long title rather than truncate meaningful qualifiers.
            # Seed drafts must still wait for human confirmation before earning points.
            assert task.score == 0
            assert all(field["status"] != "confirmed" for field in task.card.values())


def test_confirmed_milestone_gives_team_points(client):
    with Session(engine) as session:
        team = session.exec(select(Team).where(Team.name == "Steppe Data")).one()
        assert team.progress_points == 10
