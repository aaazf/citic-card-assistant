from collections.abc import AsyncIterator
from dataclasses import dataclass
from pathlib import Path

from sqlalchemy.orm import Session

from app.models.conversation import Message, MessageRole
from app.providers.base import ChatMessage
from app.providers.factory import EmbeddingProviderFactory, LLMProviderFactory
from app.providers.llm import LLMProvider
from app.rag.follow_ups import FollowUpSuggester
from app.rag.local_reranker import LocalCrossEncoderReranker
from app.rag.query_rewrite import QueryRewriter
from app.rag.reranker import LLMReranker
from app.rag.router import RelevanceRouter
from app.rag.types import (
    RAGAnswer,
    RAGStreamEvent,
    RetrievedChunk,
    StreamCompletedEvent,
    StreamDeltaEvent,
)
from app.services.rag_service import RAGService
from app.services.retrieval_service import RetrievalService
from app.services.session_service import SessionService
from app.services.usage_service import UsageService
from app.vectorstores.base import VectorStore


@dataclass(frozen=True)
class ChatAnswer:
    conversation_id: str
    knowledge_base_id: str | None
    answer: RAGAnswer


@dataclass(frozen=True)
class StreamChatAnswer:
    conversation_id: str
    knowledge_base_id: str | None
    events: AsyncIterator[RAGStreamEvent]


class ChatService:
    def __init__(
        self,
        session: Session,
        vector_store: VectorStore,
        embedding_provider_factory: EmbeddingProviderFactory,
        llm_provider_factory: LLMProviderFactory,
        session_service: SessionService,
        usage_service: UsageService | None = None,
        similarity_threshold: float = 0.5,
        reranker_enabled: bool = False,
        reranker_backend: str = "llm",
        data_dir: Path | None = None,
    ) -> None:
        self.session = session
        self.vector_store = vector_store
        self.embedding_provider_factory = embedding_provider_factory
        self.llm_provider_factory = llm_provider_factory
        self.session_service = session_service
        self.usage_service = usage_service or UsageService(session)
        self.similarity_threshold = similarity_threshold
        self.reranker_enabled = reranker_enabled
        self.reranker_backend = reranker_backend
        self.data_dir = data_dir

    def _build_reranker(self, llm_provider: LLMProvider):
        if not self.reranker_enabled:
            return None
        if self.reranker_backend == "local" and self.data_dir is not None:
            return LocalCrossEncoderReranker(self.data_dir / "models" / "reranker")
        return LLMReranker(llm_provider)

    def _build_rag_service(self) -> RAGService:
        embedding_provider = self.embedding_provider_factory(self.session)
        llm_provider = self.llm_provider_factory(self.session)
        return RAGService(
            retrieval_service=RetrievalService(embedding_provider, self.vector_store),
            llm_provider=llm_provider,
            router=RelevanceRouter(self.similarity_threshold),
            reranker=self._build_reranker(llm_provider),
            query_rewriter=QueryRewriter(llm_provider),
            follow_up_suggester=FollowUpSuggester(llm_provider),
        )

    async def answer(
        self,
        message: str,
        conversation_id: str | None = None,
        knowledge_base_id: str | None = None,
        allow_general_fallback: bool = False,
        channel: str = "customer",
        purpose: str = "chat",
        top_k: int = 5,
    ) -> ChatAnswer:
        conversation = self.session_service.ensure_conversation(
            conversation_id,
            message,
            knowledge_base_id=knowledge_base_id,
            channel=channel,
        )
        scope_id = conversation.knowledge_base_id
        where = {"knowledge_base_id": scope_id} if scope_id else None
        history = self._chat_history(self.session_service.list_history(conversation.id))
        rag_service = self._build_rag_service()
        self.session_service.add_message(conversation.id, MessageRole.USER, message)

        answer = await rag_service.answer(
            message,
            top_k,
            history=history,
            where=where,
            strict_scope=scope_id is not None and not allow_general_fallback,
            allow_general=allow_general_fallback,
        )
        self.session_service.add_message(
            conversation.id,
            MessageRole.ASSISTANT,
            answer.content,
            citations=[self._citation_payload(citation) for citation in answer.citations],
        )
        self.usage_service.record(
            source=purpose,
            model=answer.model or "",
            prompt_tokens=answer.prompt_tokens,
            completion_tokens=answer.completion_tokens,
        )
        self.session.commit()
        return ChatAnswer(
            conversation_id=conversation.id,
            knowledge_base_id=scope_id,
            answer=answer,
        )

    async def stream_answer(
        self,
        message: str,
        conversation_id: str | None = None,
        knowledge_base_id: str | None = None,
        allow_general_fallback: bool = False,
        channel: str = "customer",
        purpose: str = "chat",
        top_k: int = 5,
    ) -> StreamChatAnswer:
        conversation = self.session_service.ensure_conversation(
            conversation_id,
            message,
            knowledge_base_id=knowledge_base_id,
            channel=channel,
        )
        scope_id = conversation.knowledge_base_id
        where = {"knowledge_base_id": scope_id} if scope_id else None
        history = self._chat_history(self.session_service.list_history(conversation.id))
        rag_service = self._build_rag_service()
        self.session_service.add_message(conversation.id, MessageRole.USER, message)
        events = rag_service.stream_answer(
            message,
            top_k,
            history=history,
            where=where,
            strict_scope=scope_id is not None and not allow_general_fallback,
            allow_general=allow_general_fallback,
        )

        async def persist_completed_stream() -> AsyncIterator[RAGStreamEvent]:
            answer_parts: list[str] = []
            async for event in events:
                if isinstance(event, StreamDeltaEvent):
                    answer_parts.append(event.delta)
                elif isinstance(event, StreamCompletedEvent):
                    citations = [
                        self._citation_payload(citation) for citation in event.citations
                    ]
                    self.session_service.add_message(
                        conversation.id,
                        MessageRole.ASSISTANT,
                        "".join(answer_parts),
                        citations=citations,
                    )
                    self.usage_service.record(
                        source=purpose,
                        model=event.model or "",
                        prompt_tokens=event.prompt_tokens,
                        completion_tokens=event.completion_tokens,
                    )
                    self.session.commit()
                yield event

        return StreamChatAnswer(
            conversation_id=conversation.id,
            knowledge_base_id=scope_id,
            events=persist_completed_stream(),
        )

    @staticmethod
    def _citation_payload(citation: RetrievedChunk) -> dict[str, object]:
        return {
            "document_id": citation.document_id,
            "filename": str(citation.metadata.get("filename", "未知文件")),
            "page": citation.metadata.get("page"),
            "chunk_id": citation.chunk_id,
            "score": citation.score,
        }

    @staticmethod
    def _chat_history(messages: list[Message]) -> list[ChatMessage]:
        return [
            ChatMessage(role=message.role.value, content=message.content)
            for message in messages
            if message.role in {MessageRole.USER, MessageRole.ASSISTANT}
        ]
