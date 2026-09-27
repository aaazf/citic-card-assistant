from dataclasses import dataclass
from typing import Protocol

from app.rag.types import RetrievedChunk, RouteMode


@dataclass(frozen=True)
class RoutingDecision:
    route: RouteMode
    results: list[RetrievedChunk]


class Router(Protocol):
    def decide(self, query: str, results: list[RetrievedChunk]) -> RoutingDecision: ...


class RelevanceRouter:
    def __init__(self, similarity_threshold: float = 0.5, hybrid_ratio: float = 0.5) -> None:
        if not 0.0 <= similarity_threshold <= 1.0:
            raise ValueError("similarity_threshold must be between 0 and 1.")
        if not 0.0 < hybrid_ratio <= 1.0:
            raise ValueError("hybrid_ratio must be between 0 and 1.")
        self.similarity_threshold = similarity_threshold
        self.hybrid_floor = similarity_threshold * hybrid_ratio

    def decide(self, query: str, results: list[RetrievedChunk]) -> RoutingDecision:
        del query
        ordered = sorted(results, key=lambda item: item.score, reverse=True)
        if not ordered:
            return RoutingDecision(route=RouteMode.GENERAL, results=[])

        relevant = [item for item in ordered if item.score >= self.similarity_threshold]
        if relevant:
            return RoutingDecision(route=RouteMode.KNOWLEDGE, results=relevant)

        partially_relevant = [item for item in ordered if item.score >= self.hybrid_floor]
        if partially_relevant:
            return RoutingDecision(route=RouteMode.HYBRID, results=partially_relevant)

        return RoutingDecision(route=RouteMode.GENERAL, results=[])
