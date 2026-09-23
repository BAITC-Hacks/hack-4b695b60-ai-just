"""Run the same guarded pipeline on a small synthetic, manually labeled set."""

import argparse
import json
import statistics
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from app.ai.grounding import check_suggestion
from app.ai.service import PROMPT_VERSION, get_ai_service, set_provider_mode
from app.ai.trace import pending_trace

DATASET = Path(__file__).with_name("dataset.jsonl")


def _load() -> list[dict[str, Any]]:
    return [json.loads(line) for line in DATASET.read_text(encoding="utf-8").splitlines() if line.strip()]


def _ratio(numerator: int, denominator: int) -> float:
    return round(numerator / denominator, 4) if denominator else 0.0


def evaluate(provider: str, rows: list[dict[str, Any]]) -> dict[str, Any]:
    set_provider_mode(provider)
    true_positive = false_positive = false_negative = 0
    questions_ok = guard_failures = rejected = proposed = 0
    first_try = repaired = injection_ok = injection_count = 0
    latencies: list[float] = []
    provider_counts: dict[str, int] = {}
    service = get_ai_service()
    for row in rows:
        started = time.monotonic()
        result, meta = service.analyze_draft(row["draft"], row.get("topic"), None)
        latencies.append((time.monotonic() - started) * 1000)
        provider_counts[meta.provider] = provider_counts.get(meta.provider, 0) + 1
        predicted = {field.field for field in result.fields if field.field != "title"}
        gold = set(row["gold"]["present"])
        true_positive += len(predicted & gold)
        false_positive += len(predicted - gold)
        false_negative += len(gold - predicted)
        questions_ok += int(
            len(result.questions) >= 3
            and len({item.field for item in result.questions}) == len(result.questions)
        )
        guard_failures += sum(
            check_suggestion(field, {"draft": row["draft"]}) is not None for field in result.fields
        )
        traces = [pending_trace(identifier) for identifier in meta.trace_ids]
        final = traces[-1]
        first_try += int(meta.provider == provider and final is not None and final.status == "ok")
        repaired += int(meta.provider == provider and final is not None and final.status == "repaired")
        if final is not None:
            rejected += len(final.grounding_rejected)
            proposed += len(result.fields) + len(final.grounding_rejected)
        if "injection" in row["traps"]:
            injection_count += 1
            injection_ok += int("constraints" not in predicted)
        if "no_numbers" in row["traps"]:
            injection_count += 1
            injection_ok += int(all(not any(char.isdigit() for char in item.value) for item in result.fields))
    precision = _ratio(true_positive, true_positive + false_positive)
    recall = _ratio(true_positive, true_positive + false_negative)
    ordered = sorted(latencies)
    p95_index = min(len(ordered) - 1, max(0, int(len(ordered) * 0.95 + 0.9999) - 1))
    return {
        "requested_provider": provider,
        "prompt_version": PROMPT_VERSION,
        "cases": len(rows),
        "provider_used": provider_counts,
        "schema_valid_first_try": _ratio(first_try, len(rows)),
        "valid_after_repair": _ratio(repaired, len(rows)),
        "field_precision": precision,
        "field_recall": recall,
        "field_f1": round(2 * precision * recall / (precision + recall), 4) if precision + recall else 0.0,
        "grounding_reject_rate": _ratio(rejected, proposed),
        "final_guard_failure_rate": _ratio(guard_failures, proposed),
        "semantic_hallucination_rate": None,
        "questions_ok_rate": _ratio(questions_ok, len(rows)),
        "injection_resisted": _ratio(injection_ok, injection_count),
        "latency_p50_ms": round(statistics.median(latencies), 1),
        "latency_p95_ms": round(ordered[p95_index], 1),
        "cost_per_draft": None,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--providers", default="stub,openai,brev")
    parser.add_argument("--out", type=Path, default=Path(__file__).with_name("reports"))
    args = parser.parse_args()
    rows = _load()
    reports = [evaluate(name.strip(), rows) for name in args.providers.split(",") if name.strip()]
    args.out.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    (args.out / f"{timestamp}.json").write_text(
        json.dumps(reports, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    table = [
        "# Качество AI на синтетических черновиках",
        "",
        "Если ключ недоступен, результат относится к fallback-провайдеру из `provider_used`.",
        f"Версия промпта: `{PROMPT_VERSION}`. Field F1 проверяет наличие типов полей, не смысл текста.",
        "Final guard failures повторяет программную проверку уже отфильтрованных полей; "
        "это не независимая оценка смысловой достоверности. Семантическая оценка не проводилась.",
        "Вопросы ≥3 проверяет количество и уникальность полей, а не уместность формулировок.",
        "Стоимость не указана, если провайдер не сообщил расход токенов.",
        "",
        "| Запрошен | Реально ответил | Precision | Recall | F1 | Guard reject | "
        "Final guard failures | Вопросы ≥3 | P95, мс |",
        "| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for report in reports:
        used = ", ".join(f"{name}: {count}" for name, count in report["provider_used"].items())
        table.append(
            f"| {report['requested_provider']} | {used} | {report['field_precision']} | "
            f"{report['field_recall']} | {report['field_f1']} | {report['grounding_reject_rate']} | "
            f"{report['final_guard_failure_rate']} | {report['questions_ok_rate']} | "
            f"{report['latency_p95_ms']} |"
        )
    (args.out / "latest.md").write_text("\n".join(table) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
