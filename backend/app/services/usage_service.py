"""Token usage metering: records LLM token consumption and estimates cost."""

from datetime import UTC, datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.usage import TokenUsageRecord
from app.repositories.settings_repository import SettingsRepository

DEFAULT_PRICING = {
    "input_per_million": 2.0,
    "output_per_million": 8.0,
}


class UsageService:
    def __init__(self, session: Session) -> None:
        self.session = session
        self.settings_repository = SettingsRepository(session)

    def record(
        self,
        *,
        source: str,
        model: str,
        prompt_tokens: int | None,
        completion_tokens: int | None,
    ) -> None:
        """Persists one LLM call's usage. Skips silently when the provider
        did not report token counts (nothing honest to record)."""
        if prompt_tokens is None and completion_tokens is None:
            return
        self.session.add(
            TokenUsageRecord(
                source=source,
                model=model,
                prompt_tokens=prompt_tokens or 0,
                completion_tokens=completion_tokens or 0,
            )
        )

    def pricing(self) -> dict[str, float]:
        setting = self.settings_repository.get_system_setting("pricing")
        merged = DEFAULT_PRICING | (setting.value if setting else {})
        return {key: float(value) for key, value in merged.items()}

    def summary(self, recent_limit: int = 20) -> dict[str, Any]:
        pricing = self.pricing()
        records = list(
            self.session.scalars(
                select(TokenUsageRecord).order_by(TokenUsageRecord.created_at.desc())
            ).all()
        )
        local_now = datetime.now().astimezone()
        start_of_today = local_now.replace(hour=0, minute=0, second=0, microsecond=0)

        def cost_of(record: TokenUsageRecord) -> float:
            return (
                record.prompt_tokens / 1_000_000 * pricing["input_per_million"]
                + record.completion_tokens / 1_000_000 * pricing["output_per_million"]
            )

        def created_local(record: TokenUsageRecord) -> datetime:
            created = record.created_at
            if created.tzinfo is None:
                created = created.replace(tzinfo=UTC)
            return created.astimezone()

        def aggregate(items: list[TokenUsageRecord]) -> dict[str, Any]:
            return {
                "calls": len(items),
                "prompt_tokens": sum(item.prompt_tokens for item in items),
                "completion_tokens": sum(item.completion_tokens for item in items),
                "total_tokens": sum(item.prompt_tokens + item.completion_tokens for item in items),
                "cost_cny": round(sum(cost_of(item) for item in items), 4),
            }

        today_items = [
            record for record in records if created_local(record) >= start_of_today
        ]
        return {
            "today": aggregate(today_items),
            "total": aggregate(records),
            "pricing": pricing,
            "recent": [
                {
                    "created_at": created_local(record).isoformat(),
                    "source": record.source,
                    "model": record.model,
                    "prompt_tokens": record.prompt_tokens,
                    "completion_tokens": record.completion_tokens,
                    "cost_cny": round(cost_of(record), 6),
                }
                for record in records[:recent_limit]
            ],
        }
