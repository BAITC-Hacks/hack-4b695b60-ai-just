"""Порядок каталога: рейтинг по убыванию, затем кто раньше опубликовал, затем id."""

from collections.abc import Iterable
from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class RankEntry:
    id: int
    score: int
    published_at: datetime


def rank_key(entry: RankEntry) -> tuple[int, datetime, int]:
    return (-entry.score, entry.published_at, entry.id)


def ranked(entries: Iterable[RankEntry]) -> list[RankEntry]:
    return sorted(entries, key=rank_key)


def positions(entries: Iterable[RankEntry]) -> dict[int, int]:
    return {entry.id: index for index, entry in enumerate(ranked(entries), start=1)}


def position_preview(
    score: int,
    published: Iterable[RankEntry],
    *,
    task_id: int,
    published_at: datetime | None,
    now: datetime,
) -> int:
    """Место задачи в каталоге при данном рейтинге; неопубликованная считается опубликованной сейчас."""
    candidate = RankEntry(id=task_id, score=score, published_at=published_at or now)
    pool = [entry for entry in published if entry.id != task_id]
    pool.append(candidate)
    return ranked(pool).index(candidate) + 1
