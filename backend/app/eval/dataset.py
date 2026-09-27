import json
from dataclasses import dataclass, field
from pathlib import Path


@dataclass(frozen=True)
class EvalCase:
    question: str
    reference_answer: str
    expected_keywords: list[str] = field(default_factory=list)
    must_cite: bool = False


def load_dataset(path: Path) -> list[EvalCase]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, list) or not payload:
        raise ValueError(f"Dataset {path} must be a non-empty JSON array.")
    cases = []
    for index, item in enumerate(payload):
        if not isinstance(item, dict) or not item.get("question"):
            raise ValueError(f"Dataset case #{index + 1} requires a question.")
        cases.append(
            EvalCase(
                question=str(item["question"]),
                reference_answer=str(item.get("reference_answer", "")),
                expected_keywords=[str(k) for k in item.get("expected_keywords", [])],
                must_cite=bool(item.get("must_cite", False)),
            )
        )
    return cases
