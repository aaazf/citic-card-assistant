import asyncio
import logging
import math
from pathlib import Path

from app.rag.types import RetrievedChunk

logger = logging.getLogger(__name__)

# Process-wide cache: tokenizer + ONNX session are expensive to build.
_MODEL_CACHE: dict[str, tuple[object, object]] = {}

RERANKER_MODEL_ID = "BAAI/bge-reranker-base"
RERANKER_FILES = ("tokenizer.json", "onnx/model.onnx")


def _sigmoid(value: float) -> float:
    return 1.0 / (1.0 + math.exp(-value))


class LocalCrossEncoderReranker:
    """Local bge-reranker (ONNX) cross-encoder.

    The model is downloaded lazily on first use into ``model_dir`` and runs
    on CPU via onnxruntime. Scores are sigmoid-normalized logits in [0, 1].
    Any load failure raises so callers can fall back to vector order.
    """

    def __init__(
        self,
        model_dir: Path,
        model_id: str = RERANKER_MODEL_ID,
        max_length: int = 512,
    ) -> None:
        self.model_dir = model_dir
        self.model_id = model_id
        self.max_length = max_length
        self._session = None
        self._tokenizer = None

    async def rerank(
        self,
        query: str,
        results: list[RetrievedChunk],
        top_k: int,
    ) -> list[RetrievedChunk]:
        if not results:
            return []
        pairs = [(query, result.content[:900]) for result in results]
        scores = await asyncio.to_thread(self._score, pairs)
        reranked = [
            RetrievedChunk(
                chunk_id=result.chunk_id,
                document_id=result.document_id,
                content=result.content,
                score=score,
                metadata=result.metadata,
            )
            for result, score in zip(results, scores, strict=True)
        ]
        reranked.sort(key=lambda item: item.score, reverse=True)
        return reranked[:top_k]

    def _score(self, pairs: list[tuple[str, str]]) -> list[float]:
        self._ensure_model()
        encodings = self._tokenizer.encode_batch(
            [(query, passage) for query, passage in pairs]
        )
        available_inputs = {item.name for item in self._session.get_inputs()}
        feed: dict[str, list] = {}
        if "input_ids" in available_inputs:
            feed["input_ids"] = [encoding.ids for encoding in encodings]
        if "attention_mask" in available_inputs:
            feed["attention_mask"] = [encoding.attention_mask for encoding in encodings]
        if "token_type_ids" in available_inputs:
            feed["token_type_ids"] = [encoding.type_ids for encoding in encodings]
        outputs = self._session.run(None, feed)
        logits = outputs[0].reshape(-1)
        return [_sigmoid(float(logit)) for logit in logits]

    def _ensure_model(self) -> None:
        if self._session is not None:
            return
        cache_key = str(self.model_dir.resolve())
        cached = _MODEL_CACHE.get(cache_key)
        if cached is not None:
            self._tokenizer, self._session = cached
            return
        from huggingface_hub import hf_hub_download
        from tokenizers import Tokenizer

        self.model_dir.mkdir(parents=True, exist_ok=True)
        paths = {}
        for filename in RERANKER_FILES:
            cached = self.model_dir / filename
            if cached.exists():
                paths[filename] = str(cached)
            else:
                paths[filename] = hf_hub_download(
                    repo_id=self.model_id,
                    filename=filename,
                    local_dir=str(self.model_dir),
                )
        self._tokenizer = Tokenizer.from_file(paths["tokenizer.json"])
        self._tokenizer.enable_truncation(max_length=self.max_length)
        self._tokenizer.enable_padding(length=self.max_length)

        import onnxruntime

        self._session = onnxruntime.InferenceSession(
            paths["onnx/model.onnx"],
            providers=["CPUExecutionProvider"],
        )
        _MODEL_CACHE[cache_key] = (self._tokenizer, self._session)
        logger.info("local reranker loaded model=%s", self.model_id)
