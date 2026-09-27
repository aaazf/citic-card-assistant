import logging
import time
from collections.abc import AsyncIterator

from app.providers.base import ChatMessage
from app.providers.llm import LLMProvider
from app.rag.follow_ups import FollowUpSuggester
from app.rag.query_rewrite import QueryRewriter
from app.rag.realtime import (
    RealtimeCategory,
    build_realtime_system_prompt,
    detect_realtime_category,
)
from app.rag.reranker import Reranker
from app.rag.router import RelevanceRouter, Router, RoutingDecision
from app.rag.types import (
    RAGAnswer,
    RAGStreamEvent,
    RetrievedChunk,
    RouteMode,
    SearchStatus,
    StreamCitationEvent,
    StreamCompletedEvent,
    StreamDeltaEvent,
    StreamStatusEvent,
)
from app.services.retrieval_service import RetrievalService, is_retrieval_worthy

logger = logging.getLogger(__name__)

NO_EVIDENCE_ANSWER = "当前知识库中没有找到足够依据。"

MONEY_TERMS = (
    "利息",
    "利率",
    "年费",
    "手续费",
    "违约金",
    "滞纳金",
    "罚息",
    "取现",
    "最低还款",
)

MONEY_REFUSAL_ANSWER = (
    "这个问题涉及费用或利率等资金信息，但当前业务资料中没有找到足够依据。"
    "为避免误导，我不能凭通用知识回答具体金额或费率。"
    "建议拨打中信银行客服热线 95558 核实，或前往附近网点咨询。"
)

STRICT_NO_EVIDENCE_ANSWER = (
    "抱歉，这个问题超出了信用卡业务资料的范围，为避免误导，我不能凭通用知识回答。"
    "您可以补充描述与信用卡业务相关的问题，或拨打中信银行客服热线 95558 咨询人工服务。"
)


def is_money_related(query: str) -> bool:
    return any(term in query for term in MONEY_TERMS)
def short_query_answer(where: dict[str, object] | None = None) -> str:
    if where:
        return (
            "您好，我是中信银行信用卡智能客服。\n\n"
            "您的问题还比较简短，可以告诉我您想咨询的信用卡业务，例如：\n"
            "- 账单还款日与还款方式\n"
            "- 年费减免政策\n"
            "- 额度调整与积分使用"
        )
    return (
        "您好，我是中信银行信用卡智能客服。\n\n"
        "您的问题还比较简短，可以告诉我您想咨询的信用卡业务，例如：\n"
        "- 账单还款日与还款方式\n"
        "- 年费减免政策\n"
        "- 额度调整与积分使用"
    )


class RAGService:
    """Shared by ChatService and the Agent API; never includes transport concerns."""

    def __init__(
        self,
        retrieval_service: RetrievalService,
        llm_provider: LLMProvider,
        router: Router | None = None,
        reranker: Reranker | None = None,
        query_rewriter: QueryRewriter | None = None,
        follow_up_suggester: FollowUpSuggester | None = None,
    ) -> None:
        self.retrieval_service = retrieval_service
        self.llm_provider = llm_provider
        self.router = router or RelevanceRouter()
        self.reranker = reranker
        self.query_rewriter = query_rewriter
        self.follow_up_suggester = follow_up_suggester

    async def _suggest_follow_ups(self, query: str, answer: str, route: RouteMode) -> list[str]:
        if self.follow_up_suggester is None:
            return []
        if route not in (RouteMode.KNOWLEDGE, RouteMode.HYBRID):
            return []
        return await self.follow_up_suggester.suggest(query, answer)

    async def _effective_query(
        self,
        query: str,
        history: list[ChatMessage] | None,
    ) -> str:
        if self.query_rewriter is None:
            return query
        return await self.query_rewriter.rewrite(query, history)

    async def search(self, query: str, top_k: int) -> list[RetrievedChunk]:
        return await self.retrieval_service.retrieve(query, top_k)

    async def answer(
        self,
        query: str,
        top_k: int = 5,
        history: list[ChatMessage] | None = None,
        where: dict[str, object] | None = None,
        strict_scope: bool = False,
        allow_general: bool = False,
    ) -> RAGAnswer:
        started_at = time.perf_counter()
        try:
            effective_query = await self._effective_query(query, history)
            if not is_retrieval_worthy(effective_query):
                return RAGAnswer(
                    content=short_query_answer(where),
                    route=RouteMode.GUIDANCE,
                    citations=[],
                )
            realtime = detect_realtime_category(query)
            retrieved, decision, messages = await self._prepare(
                effective_query,
                query,
                top_k,
                history,
                where,
                realtime,
            )
            if strict_scope and decision.route is RouteMode.GENERAL:
                return RAGAnswer(
                    content=NO_EVIDENCE_ANSWER,
                    route=decision.route,
                    citations=[],
                    suggest_human=True,
                )
            if decision.route is RouteMode.GENERAL and realtime is None:
                if is_money_related(query):
                    self._log_answer(query, retrieved, decision, None, started_at)
                    return RAGAnswer(
                        content=MONEY_REFUSAL_ANSWER,
                        route=decision.route,
                        citations=[],
                        suggest_human=True,
                    )
                if not allow_general:
                    self._log_answer(query, retrieved, decision, None, started_at)
                    return RAGAnswer(
                        content=STRICT_NO_EVIDENCE_ANSWER,
                        route=decision.route,
                        citations=[],
                        suggest_human=True,
                    )
            response = await self.llm_provider.chat(messages)
            self._log_answer(query, retrieved, decision, response.model, started_at)
            follow_ups = await self._suggest_follow_ups(query, response.content, decision.route)
            return RAGAnswer(
                content=response.content,
                route=decision.route,
                citations=decision.results,
                model=response.model,
                prompt_tokens=response.prompt_tokens,
                completion_tokens=response.completion_tokens,
                follow_ups=follow_ups,
            )
        except Exception:
            self._log_failure(query, started_at)
            raise

    async def stream_answer(
        self,
        query: str,
        top_k: int = 5,
        history: list[ChatMessage] | None = None,
        where: dict[str, object] | None = None,
        strict_scope: bool = False,
        allow_general: bool = False,
    ) -> AsyncIterator[RAGStreamEvent]:
        started_at = time.perf_counter()
        yield StreamStatusEvent(
            status=SearchStatus.UNDERSTANDING,
            message="正在理解问题……",
        )
        effective_query = await self._effective_query(query, history)
        realtime = detect_realtime_category(query)
        if not is_retrieval_worthy(effective_query):
            yield StreamStatusEvent(
                status=SearchStatus.GENERATING,
                message="正在整理回答……",
            )
            yield StreamDeltaEvent(delta=short_query_answer(where))
            yield StreamCompletedEvent(route=RouteMode.GUIDANCE, citations=[])
            return

        yield StreamStatusEvent(
            status=SearchStatus.SEARCHING,
            message="正在查询业务资料……",
        )
        try:
            retrieved = await self._retrieve(effective_query, top_k, where)
            decision = self.router.decide(effective_query, retrieved)
            yield StreamStatusEvent(
                status=SearchStatus.FOUND,
                message=f"找到 {len(decision.results)} 条相关资料",
                count=len(decision.results),
            )
            yield StreamStatusEvent(
                status=SearchStatus.EVALUATING,
                message="正在核对资料……",
            )
            yield StreamStatusEvent(
                status=SearchStatus.GENERATING,
                message="正在整理答案……",
            )
            if strict_scope and decision.route is RouteMode.GENERAL:
                yield StreamDeltaEvent(delta=NO_EVIDENCE_ANSWER)
                yield StreamCompletedEvent(route=decision.route, citations=[], suggest_human=True)
                self._log_answer(query, retrieved, decision, None, started_at)
                return
            if decision.route is RouteMode.GENERAL and realtime is None:
                if is_money_related(query):
                    yield StreamDeltaEvent(delta=MONEY_REFUSAL_ANSWER)
                    yield StreamCompletedEvent(
                        route=decision.route, citations=[], suggest_human=True
                    )
                    self._log_answer(query, retrieved, decision, None, started_at)
                    return
                if not allow_general:
                    yield StreamDeltaEvent(delta=STRICT_NO_EVIDENCE_ANSWER)
                    yield StreamCompletedEvent(
                        route=decision.route, citations=[], suggest_human=True
                    )
                    self._log_answer(query, retrieved, decision, None, started_at)
                    return
            for result in decision.results:
                yield StreamCitationEvent(citation=result)

            messages = self._build_messages(
                query,
                decision.route,
                decision.results,
                history,
                realtime,
            )
            answer_parts: list[str] = []
            async for delta in self.llm_provider.stream_chat(messages):
                if delta:
                    answer_parts.append(delta)
                    yield StreamDeltaEvent(delta=delta)

            stream_usage = getattr(self.llm_provider, "last_stream_usage", None)
            full_answer = "".join(answer_parts)
            follow_ups = await self._suggest_follow_ups(query, full_answer, decision.route)
            yield StreamCompletedEvent(
                route=decision.route,
                citations=decision.results,
                model=getattr(self.llm_provider, "model", None),
                prompt_tokens=stream_usage[0] if stream_usage else None,
                completion_tokens=stream_usage[1] if stream_usage else None,
                follow_ups=follow_ups,
            )
            self._log_answer(query, retrieved, decision, None, started_at)
        except Exception:
            self._log_failure(query, started_at)
            raise

    async def _prepare(
        self,
        retrieval_query: str,
        user_query: str,
        top_k: int,
        history: list[ChatMessage] | None = None,
        where: dict[str, object] | None = None,
        realtime: RealtimeCategory | None = None,
    ) -> tuple[list[RetrievedChunk], RoutingDecision, list[ChatMessage]]:
        retrieved = await self._retrieve(retrieval_query, top_k, where)
        decision = self.router.decide(retrieval_query, retrieved)
        messages = self._build_messages(
            user_query,
            decision.route,
            decision.results,
            history,
            realtime,
        )
        return retrieved, decision, messages

    async def _retrieve(
        self,
        query: str,
        top_k: int,
        where: dict[str, object] | None = None,
    ) -> list[RetrievedChunk]:
        candidate_k = top_k if self.reranker is None else max(top_k * 2, 10)
        vector_results = await self.retrieval_service.retrieve(query, candidate_k, where=where)
        bm25_results = await self.retrieval_service.bm25_search(
            query,
            candidate_k,
            where=where,
        )
        results = self._merge_results(vector_results, bm25_results, candidate_k)
        if self.reranker is not None and results:
            try:
                return await self.reranker.rerank(query, results, top_k)
            except Exception:
                logger.warning("reranker failed, falling back to fused order", exc_info=True)
        return results[:top_k]

    @staticmethod
    def _merge_results(
        vector_results: list[RetrievedChunk],
        bm25_results: list[RetrievedChunk],
        top_k: int,
    ) -> list[RetrievedChunk]:
        """Fuses vector and BM25 rankings with RRF.

        Ordering follows the fused rank. The exposed score keeps the
        strongest evidence from either channel: the vector cosine score
        (absolute, drives routing thresholds) or the BM25 score normalized
        relative to the best BM25 hit into the 0.4-0.9 band, so that exact
        keyword hits still reach the router even when vectors rank them low.
        """
        rrf_scores: dict[str, float] = {}
        best: dict[str, RetrievedChunk] = {}
        for results in (vector_results, bm25_results):
            for rank, item in enumerate(results):
                rrf_scores[item.chunk_id] = rrf_scores.get(item.chunk_id, 0.0) + 1.0 / (
                    60 + rank + 1
                )
                best.setdefault(item.chunk_id, item)

        bm25_scores = {item.chunk_id: item.score for item in bm25_results}
        bm25_max = max(bm25_scores.values(), default=0.0)
        vector_scores = {item.chunk_id: item.score for item in vector_results}

        merged: list[RetrievedChunk] = []
        for chunk_id, item in best.items():
            bm25_evidence = (
                0.4 + 0.5 * (bm25_scores[chunk_id] / bm25_max)
                if chunk_id in bm25_scores and bm25_max > 0
                else 0.0
            )
            score = max(vector_scores.get(chunk_id, 0.0), bm25_evidence)
            merged.append(
                RetrievedChunk(
                    chunk_id=chunk_id,
                    document_id=item.document_id,
                    content=item.content,
                    score=score,
                    metadata=item.metadata,
                )
            )
        merged.sort(key=lambda item: rrf_scores[item.chunk_id], reverse=True)
        return merged[:top_k]

    @staticmethod
    def _log_answer(
        query: str,
        retrieved: list[RetrievedChunk],
        decision: RoutingDecision,
        model: str | None,
        started_at: float,
    ) -> None:
        logger.info(
            "rag answer query=%r retrieval_count=%s selected_count=%s top_score=%s "
            "route=%s model=%s latency_ms=%s",
            query,
            len(retrieved),
            len(decision.results),
            retrieved[0].score if retrieved else None,
            decision.route.value,
            model,
            round((time.perf_counter() - started_at) * 1000, 2),
        )

    @staticmethod
    def _log_failure(query: str, started_at: float) -> None:
        logger.exception(
            "rag answer failed query=%r latency_ms=%s",
            query,
            round((time.perf_counter() - started_at) * 1000, 2),
        )

    @staticmethod
    def _build_messages(
        query: str,
        route: RouteMode,
        results: list[RetrievedChunk],
        history: list[ChatMessage] | None = None,
        realtime: RealtimeCategory | None = None,
    ) -> list[ChatMessage]:
        if route is RouteMode.GENERAL:
            if realtime is not None:
                return [
                    ChatMessage(
                        role="system",
                        content=build_realtime_system_prompt(realtime),
                    ),
                    *(history or []),
                    ChatMessage(role="user", content=query),
                ]
            return [
                ChatMessage(
                    role="system",
                    content=(
                        "没有足够相关的业务资料。请使用通用知识正常回答，"
                        "并在回答开头标明“通用回答”。"
                    ),
                ),
                *(history or []),
                ChatMessage(role="user", content=query),
            ]

        context = "\n\n".join(
            f"[{index}] 文件：{result.metadata.get('filename', '未知文件')}\n{result.content}"
            for index, result in enumerate(results, start=1)
        )
        if route is RouteMode.HYBRID:
            instruction = (
                "检索结果与问题部分相关。请仅依据提供的业务资料回答，"
                "资料未覆盖的部分明确告知“这一点业务资料中暂未说明”，"
                "不要使用通用知识编造或补充。"
                "引用业务资料时使用 [1]、[2] 形式标注对应资料。"
                "当用户提出“假定”“假设”“如果……会怎样”等前提条件时，把该前提视为计算条件，先在该前提下依据业务资料计算或说明，再补充资料中的实际依据；仅当前提与业务资料明确矛盾时指出矛盾，但不要拒绝回答。资料中出现多个并列产品名称（如“爱吃版”“爱行版”“爱家版”）时，视为相互独立的产品，各自的限额与权益分别计算，不得合并为一个产品理解。"
            )
        else:
            instruction = (
                "仅当问题涉及多个对象对比或金额计算时（如多张卡、多个场景、多档费率）才使用表格，"
                "简单事实类问题直接用简短文字回答、不要套用表格。涉及对比或计算的问题，"
                "先用一个 Markdown 表格列出关键维度（如：项目/适用卡种/规则/比例或金额/上限），"
                "表格单元格内不要用 <br> 等 HTML 标签，需要分行时用顿号或分号分隔；"
                "表格之后用要点列出关键限制条件（每条带来源标注）；"
                "结尾单独一段用醒目方式给出明确结论数字，方便客户直接看懂。"
                "检索结果与问题高度相关。请严格依据提供的业务资料回答，"
                "不要编造；资料不足时明确说明“业务资料中未提及”。"
                "引用业务资料时使用 [1]、[2] 形式标注对应资料。"
                "当用户提出“假定”“假设”“如果……会怎样”等前提条件时，把该前提视为计算条件，先在该前提下依据业务资料计算或说明，再补充资料中的实际依据；仅当前提与业务资料明确矛盾时指出矛盾，但不要拒绝回答。资料中出现多个并列产品名称（如“爱吃版”“爱行版”“爱家版”）时，视为相互独立的产品，各自的限额与权益分别计算，不得合并为一个产品理解。"
            )

        return [
            ChatMessage(
                role="system",
                content=f"{instruction}\n\n业务资料：\n{context}",
            ),
            *(history or []),
            ChatMessage(role="user", content=query),
        ]
