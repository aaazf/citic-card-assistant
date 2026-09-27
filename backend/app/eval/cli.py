import argparse
from pathlib import Path

from app.core.config import BACKEND_DIR, get_settings
from app.eval.dataset import load_dataset
from app.eval.report import write_report
from app.eval.runner import run_eval
from app.main import create_app


def main() -> None:
    parser = argparse.ArgumentParser(description="Run offline answer-quality evaluation.")
    parser.add_argument(
        "--dataset",
        type=Path,
        default=BACKEND_DIR / "eval" / "datasets" / "citic-demo.json",
    )
    parser.add_argument("--top-k", type=int, default=5)
    args = parser.parse_args()

    cases = load_dataset(args.dataset)
    app = create_app()
    report = run_eval(app, cases)
    reports_dir = get_settings().data_dir / "eval" / "reports"
    path = write_report(report, reports_dir, args.dataset.stem)
    print(f"accuracy: {report['correct']}/{report['total']} = {report['accuracy']:.1%}")
    for result in report["results"]:
        mark = "OK " if result["correct"] else "BAD"
        print(f"[{mark}] {result['question']} -> {result['route']} ({result['latency_ms']} ms)")
        if result["error"]:
            print(f"      error: {result['error']}")
        if result["missing_keywords"]:
            print(f"      missing: {', '.join(result['missing_keywords'])}")
    print(f"report: {path}")


if __name__ == "__main__":
    main()
