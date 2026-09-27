import json

from app.eval.dataset import EvalCase, load_dataset
from app.eval.judge import keyword_judge
from app.eval.report import latest_report, write_report
from app.eval.runner import run_eval


def test_load_dataset_validates_shape(tmp_path) -> None:
    path = tmp_path / "dataset.json"
    path.write_text(
        json.dumps([{"question": "年费？", "expected_keywords": ["年费"]}]),
        encoding="utf-8",
    )

    cases = load_dataset(path)

    assert cases[0].question == "年费？"
    assert cases[0].expected_keywords == ["年费"]


def test_load_dataset_rejects_empty(tmp_path) -> None:
    path = tmp_path / "empty.json"
    path.write_text("[]", encoding="utf-8")

    try:
        load_dataset(path)
        raise AssertionError("should have raised")
    except ValueError:
        pass


def test_keyword_judge_hit_and_missing() -> None:
    case = EvalCase(question="q", reference_answer="", expected_keywords=["逾期", "利息"])

    verdict = keyword_judge(case, "逾期会产生利息", 1)

    assert verdict["correct"] is True
    assert verdict["hit_keywords"] == ["逾期", "利息"]


def test_keyword_judge_must_cite() -> None:
    case = EvalCase(question="q", reference_answer="", expected_keywords=[], must_cite=True)

    assert keyword_judge(case, "有回答", 0)["correct"] is False
    assert keyword_judge(case, "有回答", 2)["correct"] is True


def test_report_roundtrip(tmp_path) -> None:
    report_payload = {"total": 1, "correct": 1, "accuracy": 1.0, "results": []}
    path = write_report(report_payload, tmp_path, "demo")

    report = latest_report(tmp_path)

    assert path.exists()
    assert report["dataset"] == "demo"
    assert report["accuracy"] == 1.0


def test_latest_report_empty_dir(tmp_path) -> None:
    assert latest_report(tmp_path / "nope") is None


def test_run_eval_end_to_end(test_app) -> None:
    cases = [EvalCase(question="年费怎么收", reference_answer="", expected_keywords=[])]

    report = run_eval(test_app, cases)

    assert report["total"] == 1
    assert report["correct"] == 1
    assert report["results"][0]["route"] == "general"
    assert report["results"][0]["error"] is None


def test_eval_report_api_404_then_serves_latest(client, test_settings) -> None:
    assert client.get("/api/v1/eval/reports/latest").status_code == 404

    reports_dir = test_settings.data_dir / "eval" / "reports"
    write_report({"total": 2, "correct": 1, "accuracy": 0.5, "results": []}, reports_dir, "demo")

    response = client.get("/api/v1/eval/reports/latest")

    assert response.status_code == 200
    assert response.json()["accuracy"] == 0.5


def test_run_eval_api_creates_report(client, test_settings) -> None:
    response = client.post("/api/v1/eval/run")

    assert response.status_code == 201
    payload = response.json()
    assert payload["dataset"] == "citic-demo"
    assert payload["total"] >= 1
    assert 0.0 <= payload["accuracy"] <= 1.0

    latest = client.get("/api/v1/eval/reports/latest")
    assert latest.status_code == 200
    assert latest.json()["dataset"] == "citic-demo"
