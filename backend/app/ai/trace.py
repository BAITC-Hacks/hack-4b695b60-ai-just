"""Trace staging avoids SQLite write locks during the caller's task transaction."""

import threading
import time
from typing import Any

from sqlalchemy import event
from sqlmodel import Session, select

from app.models import AITrace

_lock = threading.Lock()
_pending: dict[int, AITrace] = {}
_last_id = 0


def record_trace(**values: Any) -> int:
    global _last_id
    with _lock:
        _last_id = max(_last_id + 1, time.time_ns() // 1000)
        row = AITrace(id=_last_id, **values)
        _pending[_last_id] = row
        return _last_id


def pending_trace(trace_id: int) -> AITrace | None:
    with _lock:
        return _pending.get(trace_id)


@event.listens_for(Session, "before_commit")
def _attach_pending(session: Session) -> None:
    """Store traces in the next application transaction, including task creation."""
    with _lock:
        rows = list(_pending.values())
        _pending.clear()
    if rows:
        session.info["ai_trace_staged"] = rows
        session.add_all(rows)


@event.listens_for(Session, "after_commit")
def _clear_staged(session: Session) -> None:
    session.info.pop("ai_trace_staged", None)


@event.listens_for(Session, "after_rollback")
def _restore_staged(session: Session) -> None:
    rows = session.info.pop("ai_trace_staged", [])
    with _lock:
        _pending.update({row.id: row for row in rows})


def flush_pending(session: Session) -> None:
    """Also support direct AI calls that have no surrounding task transaction."""
    with _lock:
        has_pending = bool(_pending)
    if has_pending:
        session.commit()


def list_traces(session: Session, task_id: int | None, limit: int) -> list[AITrace]:
    flush_pending(session)
    statement = select(AITrace)
    if task_id is not None:
        statement = statement.where(AITrace.task_id == task_id)
    return list(session.exec(statement.order_by(AITrace.id.desc()).limit(limit)).all())
