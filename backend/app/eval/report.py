import json
from datetime import UTC, datetime
from pathlib import Path


def write_report(report: dict, reports_dir: Path, dataset_name: str) -> Path:
    reports_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now(UTC).strftime("%Y%m%d%H%M%S")
    path = reports_dir / f"eval-{dataset_name}-{timestamp}.json"
    payload = {
        "dataset": dataset_name,
        "created_at": datetime.now(UTC).isoformat(),
        **report,
    }
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return path


def latest_report(reports_dir: Path) -> dict | None:
    if not reports_dir.exists():
        return None
    reports = sorted(reports_dir.glob("eval-*.json"))
    if not reports:
        return None
    return json.loads(reports[-1].read_text(encoding="utf-8"))
