from app.ai import service
from eval.run_eval import evaluate


def test_eval_reports_guard_checks_without_claiming_semantic_certainty(monkeypatch) -> None:
    monkeypatch.setattr(service, "_mode_override", None)
    report = evaluate(
        "stub",
        [
            {
                "draft": "Хотим бот для клиентов.",
                "gold": {"present": ["expected_result", "users"]},
                "traps": [],
            }
        ],
    )
    assert report["prompt_version"] == "v2"
    assert report["provider_used"] == {"stub": 1}
    assert report["final_guard_failure_rate"] == 0
    assert report["semantic_hallucination_rate"] is None
    assert "final_hallucination_rate" not in report
