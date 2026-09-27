"""Generates short follow-up question suggestions after a knowledge answer."""

import asyncio
import logging

from app.providers.base import ChatMessage
from app.providers.llm import LLMProvider

logger = logging.getLogger(__name__)

_FOLLOW_UP_PROMPT = (
    "你是中信银行信用卡智能客服。根据客户的问题和你的回答，"
    "生成 2-3 个客户最可能接着问的信用卡业务问题。\n"
    "要求：\n"
    "1. 每个问题单独一行，不要序号、不要引号、不要解释。\n"
    "2. 必须是信用卡业务相关问题，简短口语化，20 字以内。\n"
    "3. 不要重复客户已经问过的内容，不要生成与回答无关的问题。"
)


class FollowUpSuggester:
    """Suggests 2-3 follow-up questions. Any failure falls back to none
    so the main answer chain is never blocked or delayed on errors."""

    def __init__(self, llm_provider: LLMProvider, timeout_seconds: float = 10.0) -> None:
        self.llm_provider = llm_provider
        self.timeout_seconds = timeout_seconds

    async def suggest(self, query: str, answer: str) -> list[str]:
        messages = [
            ChatMessage(role="system", content=_FOLLOW_UP_PROMPT),
            ChatMessage(
                role="user",
                content=f"客户问题：{query}\n\n助手回答：{answer[:600]}",
            ),
        ]
        try:
            response = await asyncio.wait_for(
                self.llm_provider.chat(messages),
                timeout=self.timeout_seconds,
            )
        except Exception:
            logger.info("follow-up suggestion failed; skipping", exc_info=True)
            return []
        suggestions: list[str] = []
        for line in response.content.splitlines():
            cleaned = line.strip().strip("-•*").lstrip("0123456789.、)） ").strip().strip('"“”')
            if 4 <= len(cleaned) <= 40 and cleaned not in suggestions:
                suggestions.append(cleaned)
        return suggestions[:3]
