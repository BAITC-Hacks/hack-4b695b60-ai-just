from datetime import datetime, timedelta

from app.domain.catalog import RankEntry, position_preview, positions

NOW = datetime(2026, 9, 23, 12, 0, 0)


def entries() -> list[RankEntry]:
    return [
        RankEntry(id=1, score=80, published_at=NOW - timedelta(days=3)),
        RankEntry(id=2, score=94, published_at=NOW - timedelta(days=1)),
        RankEntry(id=3, score=80, published_at=NOW - timedelta(days=5)),
        RankEntry(id=4, score=30, published_at=NOW - timedelta(days=2)),
    ]


def test_order_by_score_then_earlier_publication():
    assert positions(entries()) == {2: 1, 3: 2, 1: 3, 4: 4}


def test_preview_for_unpublished_task_goes_after_equal_scores():
    assert position_preview(80, entries(), task_id=99, published_at=None, now=NOW) == 4
    assert position_preview(96, entries(), task_id=99, published_at=None, now=NOW) == 1


def test_preview_for_published_task_uses_its_own_date():
    assert position_preview(95, entries(), task_id=4, published_at=NOW - timedelta(days=2), now=NOW) == 1
