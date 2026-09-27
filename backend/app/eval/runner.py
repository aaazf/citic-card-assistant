import time
from dataclasses import dataclass, field

from fastapi.testclient import TestClient

from app.eval.dataset import EvalCase
from app.eval.judge import keyword_judge


@dataclass(frozen=True)
class EvalResult:
    question: str
    answer: str
    route: str | None
    citations_count: int
    latency_ms: float
    correct: bool
    hit_keywords: list[str] = field(default_factory=list)
    missing_keywords: list[str] = field(default_factory=list)
    error: str | None = None


def run_eval(app, cases: list[EvalCase], judge=keyword_judge) -> dict:
    """Runs every case through POST /api/v1/chat (JSON mode) and judges it."""
    results: list[EvalResult] = []
    with TestClient(app) as client:
        for case in cases:
            started = time.perf_counter()
            try:
                response = client.post(
                    "/api/v1/chat",
                    json={"message": case.question, "channel": "staff", "purpose": "eval"},
                )
                latency_ms = round((time.perf_counter() - started) * 1000, 2)
                if response.status_code != 200:
                    results.append(
                        EvalResult(
                            question=case.question,
                            answer="",
                            route=None,
                            citations_count=0,
                            latency_ms=latency_ms,
                            correct=False,
                            error=f"HTTP {response.status_code}: {response.text[:200]}",
                        )
                    )
                    continue
                payload = response.json()
                answer = str(payload.get("answer", ""))
                citations = payload.get("citations", [])
                verdict = judge(case, answer, len(citations))
                results.append(
                    EvalResult(
                        question=case.question,
                        answer=answer,
                        route=payload.get("route"),
                        citations_count=len(citations),
                        latency_ms=latency_ms,
                        correct=bool(verdict["correct"]),
                        hit_keywords=list(verdict.get("hit_keywords", [])),
                        missing_keywords=list(verdict.get("missing_keywords", [])),
                    )
                )
            except Exception as exc:
                results.append(
                    EvalResult(
                        question=case.question,
                        answer="",
                        route=None,
                        citations_count=0,
                        latency_ms=round((time.perf_counter() - started) * 1000, 2),
                        correct=False,
                        error=str(exc),
                    )
                )
    correct_count = sum(1 for result in results if result.correct)
    total = len(results)
    return {
        "total": total,
        "correct": correct_count,
        "accuracy": round(correct_count / total, 4) if total else 0.0,
        "results": [result.__dict__ for result in results],
    }
