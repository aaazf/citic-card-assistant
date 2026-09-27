from fastapi import APIRouter, HTTPException, Request, status

from app.core.config import BACKEND_DIR
from app.eval.dataset import load_dataset
from app.eval.report import latest_report, write_report
from app.eval.runner import run_eval

router = APIRouter(prefix="/eval", tags=["eval"])

DEFAULT_DATASET = BACKEND_DIR / "eval" / "datasets" / "citic-demo.json"


@router.get("/reports/latest")
def get_latest_eval_report(request: Request) -> dict:
    reports_dir = request.app.state.settings.data_dir / "eval" / "reports"
    report = latest_report(reports_dir)
    if report is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="还没有评估报告。请先运行 python -m app.eval.cli。",
        )
    return report


@router.post("/run", status_code=status.HTTP_201_CREATED)
def run_eval_now(request: Request) -> dict:
    """Runs the built-in dataset against this app and persists a new report."""
    cases = load_dataset(DEFAULT_DATASET)
    report = run_eval(request.app, cases)
    reports_dir = request.app.state.settings.data_dir / "eval" / "reports"
    write_report(report, reports_dir, DEFAULT_DATASET.stem)
    return {"dataset": DEFAULT_DATASET.stem, **report}
