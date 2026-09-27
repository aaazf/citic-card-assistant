import asyncio
import logging

from app.providers.base import ChatMessage
from app.providers.llm import LLMProvider

logger = logging.getLogger(__name__)

_REWRITE_PROMPT = (
    "你是信用卡客服场景的查询改写器。结合对话历史，把用户的最新问题改写为"
    "独立、规范的业务查询句：补全省略的主语和指代（如“它”“这个”），"
    "把口语表达映射为业务术语（如“忘了还钱”→“逾期还款”）。"
    "只输出改写后的问题本身，不要回答，不要解释，不要加引号。"
    "若原问题已经独立完整，原样输出。"
)


class QueryRewriter:
    """Rewrites the latest user question into a standalone business query.

    Only runs when conversation history exists; any failure or timeout
    falls back to the original question so the main chain never breaks.
    """

    def __init__(self, llm_provider: LLMProvider, timeout_seconds: float = 10.0) -> None:
        self.llm_provider = llm_provider
        self.timeout_seconds = timeout_seconds

    async def rewrite(self, query: str, history: list[ChatMessage] | None = None) -> str:
        if not history:
            return query
        history_lines = "\n".join(
            f"{'用户' if message.role == 'user' else '助手'}: {message.content[:200]}"
            for message in history[-6:]
        )
        messages = [
            ChatMessage(role="system", content=_REWRITE_PROMPT),
            ChatMessage(
                role="user",
                content=f"对话历史：\n{history_lines}\n\n最新问题：{query}",
            ),
        ]
        try:
            response = await asyncio.wait_for(
                self.llm_provider.chat(messages),
                timeout=self.timeout_seconds,
            )
        except Exception:
            logger.info("query rewrite failed; using original query", exc_info=True)
            return query
        rewritten = response.content.strip().strip('"“”')
        if not rewritten or len(rewritten) > len(query) * 4 + 40:
            return query
        logger.info("query rewritten original=%r rewritten=%r", query, rewritten)
        return rewritten
