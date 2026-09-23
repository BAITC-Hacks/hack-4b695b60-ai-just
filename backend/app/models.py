from datetime import UTC, datetime
from typing import Any

from sqlalchemy import JSON, Column
from sqlmodel import Field, SQLModel


def utcnow() -> datetime:
    return datetime.now(UTC).replace(microsecond=0)


class Business(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    name: str
    industry: str | None = None
    created_at: datetime = Field(default_factory=utcnow)


class Team(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    name: str
    interests: list[str] = Field(default_factory=list, sa_column=Column(JSON, nullable=False))
    skills: list[str] = Field(default_factory=list, sa_column=Column(JSON, nullable=False))
    technologies: list[str] = Field(default_factory=list, sa_column=Column(JSON, nullable=False))
    progress_points: int = 0
    last_points_at: datetime | None = None


class Task(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    business_id: int = Field(foreign_key="business.id", index=True)
    status: str = Field(default="clarifying", index=True)
    topic: str | None = None
    draft_text: str
    card: dict[str, Any] = Field(default_factory=dict, sa_column=Column(JSON, nullable=False))
    score: int = 0
    potential_score: int = 0
    level: str = "draft"
    ai_meta: dict[str, Any] | None = Field(default=None, sa_column=Column(JSON, nullable=True))
    created_at: datetime = Field(default_factory=utcnow)
    updated_at: datetime = Field(default_factory=utcnow)
    published_at: datetime | None = None


class Question(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    task_id: int = Field(foreign_key="task.id", index=True)
    key: str
    field: str
    question: str
    why: str = ""
    points_gain: int = 0
    answer: str | None = None
    round: int = 1
    created_at: datetime = Field(default_factory=utcnow)


class ScoreEvent(SQLModel, table=True):
    __tablename__ = "score_event"

    id: int | None = Field(default=None, primary_key=True)
    task_id: int = Field(foreign_key="task.id", index=True)
    score: int
    delta: int
    level: str
    reason: str
    created_at: datetime = Field(default_factory=utcnow)


class Proposal(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    task_id: int = Field(foreign_key="task.id", index=True)
    team_id: int = Field(foreign_key="team.id", index=True)
    idea: str
    plan: str
    timeline: str
    prototype_url: str | None = None
    status: str = "submitted"
    business_comment: str | None = None
    created_at: datetime = Field(default_factory=utcnow)
    decided_at: datetime | None = None


class Milestone(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    proposal_id: int = Field(foreign_key="proposal.id", index=True)
    title: str
    points: int = 10
    status: str = "pending"
    created_at: datetime = Field(default_factory=utcnow)
    confirmed_at: datetime | None = None


class AITrace(SQLModel, table=True):
    __tablename__ = "ai_trace"

    id: int | None = Field(default=None, primary_key=True)
    task_id: int | None = Field(default=None, index=True)
    operation: str
    provider: str
    model: str
    prompt_version: str | None = None
    input_redacted: str = ""
    raw_output: str = ""
    parsed: dict[str, Any] | None = Field(default=None, sa_column=Column(JSON, nullable=True))
    status: str = "ok"
    errors: list[str] = Field(default_factory=list, sa_column=Column(JSON, nullable=False))
    grounding_rejected: list[dict[str, Any]] = Field(
        default_factory=list, sa_column=Column(JSON, nullable=False)
    )
    latency_ms: int = 0
    created_at: datetime = Field(default_factory=utcnow)
