from app.eval.dataset import EvalCase


def keyword_judge(case: EvalCase, answer: str, citations_count: int) -> dict:
    """Deterministic judge: every expected keyword must appear in the answer.

    Cases with no keywords are judged on getting any non-empty answer.
    """
    hit = [keyword for keyword in case.expected_keywords if keyword in answer]
    missing = [keyword for keyword in case.expected_keywords if keyword not in answer]
    correct = not missing and bool(answer.strip())
    if case.must_cite and citations_count == 0:
        correct = False
    return {
        "correct": correct,
        "hit_keywords": hit,
        "missing_keywords": missing,
    }
