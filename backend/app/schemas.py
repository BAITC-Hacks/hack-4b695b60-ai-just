"""DTO API. Совпадают с docs/api-contract.md."""

from datetime import UTC, datetime
from typing import Annotated, Literal

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    HttpUrl,
    PlainSerializer,
    StringConstraints,
    field_validator,
)

from app.ai.service import ProviderStatus
from app.domain.fields import TOPIC_KEYS, CriterionKey, FieldKey, LevelKey
from app.domain.rating import Level, Rating

TaskStatus = Literal["clarifying", "review", "published"]
FieldStatus = Literal["empty", "suggested", "confirmed"]
TrimmedText = Annotated[str, StringConstraints(strip_whitespace=True)]


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
    name: TrimmedText = Field(min_length=2, max_length=120)
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


class EvidenceDTO(BaseModel):
    source: str
    quote: str


class CardFieldDTO(BaseModel):
    value: str | None
    status: FieldStatus
    source: Literal["ai", "user"] | None
    evidence: list[EvidenceDTO]
    updated_at: str | None


class CardDTO(BaseModel):
    title: CardFieldDTO
    context: CardFieldDTO
    need: CardFieldDTO
    users: CardFieldDTO
    data: CardFieldDTO
    constraints: CardFieldDTO
    expected_result: CardFieldDTO
    success_criteria: CardFieldDTO
    contact: CardFieldDTO
    interaction_format: CardFieldDTO


class QuestionDTO(BaseModel):
    id: str
    field: FieldKey
    question: str
    why: str
    points_gain: int
    answer: str | None
    round: int


class AiMeta(BaseModel):
    provider_used: str
    model: str
    degraded: bool
    trace_ids: list[int]


class BusinessRef(BaseModel):
    id: int
    name: str


class TaskDetail(BaseModel):
    id: int
    business: BusinessRef
    status: TaskStatus
    topic: str | None
    draft_text: str
    card: CardDTO
    questions: list[QuestionDTO]
    rating: Rating
    catalog_position: int | None
    catalog_position_preview: int
    proposals_count: int
    ai: AiMeta | None
    created_at: UtcDatetime
    updated_at: UtcDatetime
    published_at: UtcDatetime | None


class TaskSummary(BaseModel):
    id: int
    title: str | None
    status: TaskStatus
    topic: str | None
    score: int
    level: Level
    proposals_count: int
    updated_at: UtcDatetime


class ScoreEventOut(OrmModel):
    score: int
    delta: int
    level: LevelKey
    reason: str
    created_at: UtcDatetime


class TaskCreate(BaseModel):
    business_id: int
    draft_text: TrimmedText = Field(min_length=10, max_length=4000)
    topic: str | None = None

    @field_validator("topic")
    @classmethod
    def _known_topic(cls, value: str | None) -> str | None:
        if value is not None and value not in TOPIC_KEYS:
            raise ValueError(f"Неизвестная тема: {value}")
        return value


class AnswerIn(BaseModel):
    question_id: str = Field(min_length=1, max_length=20)
    text: str = Field(default="", max_length=2000)


class AnswersIn(BaseModel):
    answers: list[AnswerIn] = Field(min_length=1, max_length=20)


class FieldPatch(BaseModel):
    value: str | None = Field(default=None, max_length=2000)
    confirm: bool = False
    reject: bool = False


class CardPatch(BaseModel):
    fields: dict[FieldKey, FieldPatch] = Field(min_length=1)


class PublishIn(BaseModel):
    confirm: bool = False


class CatalogItem(BaseModel):
    id: int
    title: str
    topic: str | None
    business_name: str
    score: int
    level: Level
    highlighted: bool
    needs_clarification: bool
    need_preview: str
    proposals_count: int
    position: int
    published_at: UtcDatetime


class CatalogPage(BaseModel):
    items: list[CatalogItem]
    total: int


class PublicTask(BaseModel):
    id: int
    title: str
    topic: str | None
    business_name: str
    card: dict[FieldKey, str]
    rating: Rating
    position: int
    proposals_count: int
    published_at: UtcDatetime


class TaskRef(BaseModel):
    id: int
    title: str


class MilestoneOut(OrmModel):
    id: int
    proposal_id: int
    title: str
    points: int
    status: Literal["pending", "confirmed"]
    confirmed_at: UtcDatetime | None


class ProposalOut(BaseModel):
    id: int
    task: TaskRef
    team: TeamOut
    idea: str
    plan: str
    timeline: str
    prototype_url: str | None
    status: Literal["submitted", "selected", "rejected"]
    business_comment: str | None
    milestones: list[MilestoneOut]
    created_at: UtcDatetime
    decided_at: UtcDatetime | None


class ProposalCreate(BaseModel):
    team_id: int
    idea: TrimmedText = Field(min_length=20, max_length=3000)
    plan: TrimmedText = Field(min_length=20, max_length=3000)
    timeline: TrimmedText = Field(min_length=1, max_length=200)
    prototype_url: HttpUrl | None = None


class DecisionIn(BaseModel):
    business_id: int
    decision: Literal["selected", "rejected"]
    comment: str | None = Field(default=None, max_length=500)


class MilestoneCreate(BaseModel):
    business_id: int
    title: TrimmedText = Field(min_length=3, max_length=200)
    points: int = Field(default=10, ge=5, le=30)


class BusinessAction(BaseModel):
    business_id: int


class MilestoneConfirmOut(BaseModel):
    milestone: MilestoneOut
    team: TeamOut


class TeamRank(BaseModel):
    rank: int
    team: TeamOut
    confirmed_milestones: int


class TeamLeaderboard(BaseModel):
    items: list[TeamRank]


class BusinessRank(BaseModel):
    rank: int
    business: BusinessOut
    avg_score: float
    published_tasks: int


class BusinessLeaderboard(BaseModel):
    items: list[BusinessRank]
