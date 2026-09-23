"""Rank eligible published tasks against team interests, skills and technologies."""

import re
from collections.abc import Sequence

import numpy as np
from openai import OpenAI
from sklearn.feature_extraction.text import TfidfVectorizer

from app.ai.pii import redact_texts
from app.config import get_settings
from app.domain.card import confirmed_values
from app.domain.fields import TOPICS
from app.models import Task, Team

_TERM_SPLIT_RE = re.compile(r"[,;/]|\s+и\s+", re.IGNORECASE)
_SYNONYMS = {"питон": "python", "тг": "telegram", "телеграм": "telegram", "эксель": "excel"}
_TOPIC_LABELS = dict(TOPICS)


def _term(value: str) -> str:
    cleaned = value.casefold().replace("ё", "е").strip()
    return _SYNONYMS.get(cleaned, cleaned)


def _strings(items: Sequence[str] | None) -> list[str]:
    return [item.strip() for item in (items or []) if item.strip()]


def team_terms(team: Team) -> list[str]:
    values = [*_strings(team.skills), *_strings(team.technologies)]
    return list(
        dict.fromkeys(_term(part) for value in values for part in _TERM_SPLIT_RE.split(value) if part.strip())
    )


def team_text(team: Team) -> str:
    interests = ", ".join(_strings(team.interests))
    skills = ", ".join(_strings(team.skills))
    technologies = ", ".join(_strings(team.technologies))
    return f"Интересы: {interests}. Навыки: {skills}. Технологии: {technologies}."


def task_text(task: Task) -> str:
    fields = confirmed_values(task.card)
    title = fields.get("title", "")
    need = fields.get("need", "")
    expected = fields.get("expected_result", "")
    data = fields.get("data", "")
    constraints = fields.get("constraints", "")
    return f"{title}. {need} {expected} Данные: {data}. Ограничения: {constraints}."


def _cosine(left: np.ndarray, right: np.ndarray) -> float:
    denominator = float(np.linalg.norm(left) * np.linalg.norm(right))
    return max(0.0, float(np.dot(left, right) / denominator)) if denominator else 0.0


def _tfidf(query: str, passages: list[str]) -> list[float]:
    vectors = TfidfVectorizer(analyzer="char_wb", ngram_range=(3, 5)).fit_transform([query, *passages])
    return [float(vectors[0].multiply(vectors[index]).sum()) for index in range(1, vectors.shape[0])]


def _external(query: str, passages: list[str]) -> tuple[list[float], str]:
    settings = get_settings()
    model = settings.openai_embed_model
    if not settings.openai_api_key:
        raise ValueError("provider_unavailable")
    masked, _ = redact_texts([query, *passages])
    with OpenAI(api_key=settings.openai_api_key, timeout=settings.ai_timeout_seconds) as client:
        response = client.embeddings.create(model=model, input=masked)
        query_vec = response.data[0].embedding
        passage_vecs = response.data[1:]
    left = np.asarray(query_vec, dtype=float)
    return [
        _cosine(left, np.asarray(item.embedding, dtype=float)) for item in passage_vecs
    ], f"embeddings:{model}"


def similarities(query: str, passages: list[str]) -> tuple[list[float], str]:
    if not passages:
        return [], "tfidf"
    settings = get_settings()
    for provider in settings.embed_chain:
        if provider == "openai":
            try:
                return _external(query, passages)
            except Exception:
                continue
        if provider == "tfidf":
            return _tfidf(query, passages), "tfidf"
    return _tfidf(query, passages), "tfidf"


def recommend(team: Team, tasks: list[Task], limit: int) -> tuple[list[dict[str, object]], str]:
    candidates = [
        task for task in tasks if task.status == "published" and task.published_at and task.score >= 40
    ]
    if not candidates:
        return [], "tfidf"
    query = team_text(team)
    texts = [task_text(task) for task in candidates]
    cosine_scores, method = similarities(query, texts)
    terms = team_terms(team)
    interests = {_term(value) for value in _strings(team.interests)}
    results: list[dict[str, object]] = []
    for task, passage, cosine_score in zip(candidates, texts, cosine_scores, strict=True):
        normalized_passage = passage.casefold().replace("ё", "е")
        matched = [term for term in terms if term and term in normalized_passage]
        overlap = len(matched) / max(1, len(terms))
        score = round(min(1.0, 0.6 * cosine_score + 0.3 * overlap + 0.1 * task.score / 100), 4)
        reasons = []
        if matched:
            reasons.append("Совпадают навыки: " + ", ".join(matched))
        if task.topic in interests or _term(_TOPIC_LABELS.get(task.topic, "")) in interests:
            reasons.append("Тема совпадает с интересами: " + _TOPIC_LABELS.get(task.topic, task.topic))
        reasons.append(f"Готовность задачи: {task.score}/100")
        results.append({"task": task, "match": score, "reasons": reasons, "matched_terms": matched})
    results.sort(key=lambda item: (-item["match"], -item["task"].score, item["task"].id))
    return results[:limit], method
