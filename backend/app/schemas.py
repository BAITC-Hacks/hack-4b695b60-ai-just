"""DTO API. Совпадают с docs/api-contract.md."""

from datetime import UTC, datetime
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, PlainSerializer

from app.ai.service import ProviderStatus
from app.domain.fields import CriterionKey, FieldKey
from app.domain.rating import Level


def _utc_iso(moment: datetime) -> str:
    aware = moment.replace(tzinfo=UTC) if moment.tzinfo is None else moment.astimezone(UTC)
    return aware.replace(microsecond=0).isoformat().replace("+00:00", "Z")


UtcDatetime = Annotated[datetime, PlainSerializer(_utc_iso, return_type=str)]


class OrmModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class OkResponse(BaseModel):
    ok: bool = True


class BusinessOut(OrmModel):
    id: int
    name: str
    industry: str | None


class BusinessCreate(BaseModel):
    name: str = Field(min_length=2, max_length=120)
    industry: str | None = Field(default=None, max_length=60)


class TeamOut(OrmModel):
    id: int
    name: str
    interests: list[str]
    skills: list[str]
    technologies: list[str]
    progress_points: int


class AIStatus(BaseModel):
    mode: str
    chain: list[ProviderStatus]


class EmbeddingsStatus(BaseModel):
    chain: list[str]
    active: str


class Health(BaseModel):
    status: Literal["ok"] = "ok"
    version: str
    ai: AIStatus
    embeddings: EmbeddingsStatus


class FieldMeta(BaseModel):
    key: FieldKey
    label: str
    criterion: CriterionKey | None
    placeholder: str


class CriterionMeta(BaseModel):
    key: CriterionKey
    label: str
    weight: int
    description: str


class TopicMeta(BaseModel):
    key: str
    label: str


class Meta(BaseModel):
    fields: list[FieldMeta]
    criteria: list[CriterionMeta]
    levels: list[Level]
    topics: list[TopicMeta]
