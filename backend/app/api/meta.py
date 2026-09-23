from fastapi import APIRouter

from app import __version__
from app.ai.service import embeddings_chain, provider_chain
from app.config import get_settings
from app.domain.fields import CRITERIA, FIELDS, LEVELS, TOPICS
from app.domain.rating import Level
from app.schemas import AIStatus, CriterionMeta, EmbeddingsStatus, FieldMeta, Health, Meta, TopicMeta

router = APIRouter(prefix="/api", tags=["meta"])


@router.get("/health", response_model=Health)
def health() -> Health:
    chain, active = embeddings_chain()
    return Health(
        version=__version__,
        ai=AIStatus(mode=get_settings().ai_provider, chain=provider_chain()),
        embeddings=EmbeddingsStatus(chain=chain, active=active),
    )


@router.get("/meta", response_model=Meta)
def meta() -> Meta:
    return Meta(
        fields=[
            FieldMeta(key=f.key, label=f.label, criterion=f.criterion, placeholder=f.placeholder)
            for f in FIELDS
        ],
        criteria=[
            CriterionMeta(key=c.key, label=c.label, weight=c.weight, description=c.description)
            for c in CRITERIA
        ],
        levels=[Level(key=lv.key, label=lv.label, min=lv.min, max=lv.max) for lv in LEVELS],
        topics=[TopicMeta(key=key, label=label) for key, label in TOPICS],
    )
