from typing import Any
import time

from google import genai
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

try:
    from google.genai import types
except Exception:  # pragma: no cover - older SDK shape fallback
    types = None

import config
from ingest.utils import logger


class GeminiEmbedder:
    def __init__(self, api_key: str | None = None, model: str | None = None):
        self.api_key = api_key or config.GEMINI_API_KEY
        self.model = model or config.GEMINI_EMBEDDING_MODEL
        self._last_batch_at = 0.0
        if not self.api_key:
            raise config.ConfigurationError("GEMINI_API_KEY is required for embeddings.")
        self.client = genai.Client(api_key=self.api_key)

    def _embed_config(self, task_type: str | None) -> Any:
        options: dict[str, Any] = {"output_dimensionality": config.EMBEDDING_DIMENSION}
        if task_type and "gemini-embedding-2" not in self.model:
            options["task_type"] = task_type
        if types is None:
            return options
        return types.EmbedContentConfig(**options)

    @staticmethod
    def _extract_vectors(response: Any, expected_count: int) -> list[list[float]]:
        raw_embeddings = getattr(response, "embeddings", None)
        if raw_embeddings is None:
            single = getattr(response, "embedding", None)
            raw_embeddings = [single] if single is not None else []

        vectors: list[list[float]] = []
        for embedding in raw_embeddings:
            values = getattr(embedding, "values", None)
            if values is None:
                values = getattr(embedding, "embedding", None)
            if values is None and isinstance(embedding, dict):
                values = embedding.get("values") or embedding.get("embedding")
            if values is None:
                values = embedding
            vectors.append([float(value) for value in values])

        if len(vectors) != expected_count:
            raise ValueError(f"Expected {expected_count} embedding(s), received {len(vectors)}")
        return vectors

    @staticmethod
    def _is_quota_error(error: Exception) -> bool:
        message = str(error)
        return "429" in message or "RESOURCE_EXHAUSTED" in message or "quota" in message.lower()

    def _pace_batch(self, item_count: int) -> None:
        if item_count <= 0:
            return
        items_per_minute = max(1, config.EMBEDDING_MAX_ITEMS_PER_MINUTE)
        min_interval = max(
            config.EMBEDDING_MIN_BATCH_INTERVAL_SECONDS,
            60.0 * item_count / items_per_minute,
        )
        elapsed = time.monotonic() - self._last_batch_at
        if self._last_batch_at and elapsed < min_interval:
            wait_for = min_interval - elapsed
            logger.info("Pacing Gemini embeddings for %.1f seconds to stay under quota.", wait_for)
            time.sleep(wait_for)
        self._last_batch_at = time.monotonic()

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=2, min=5, max=75),
        retry=retry_if_exception_type(Exception),
        reraise=True,
    )
    def _embed_batch(self, texts: list[str], task_type: str) -> list[list[float]]:
        response = self.client.models.embed_content(
            model=self.model,
            contents=texts,
            config=self._embed_config(task_type),
        )
        return self._extract_vectors(response, expected_count=len(texts))

    def _embed_batch_with_quota_retries(self, texts: list[str], task_type: str) -> list[list[float]]:
        attempts = max(1, config.EMBEDDING_QUOTA_RETRY_ATTEMPTS)
        for attempt in range(1, attempts + 1):
            self._pace_batch(len(texts))
            try:
                return self._embed_batch(texts, task_type=task_type)
            except Exception as error:
                if not self._is_quota_error(error) or attempt == attempts:
                    raise
                logger.warning(
                    "Gemini embedding quota hit for batch; waiting %.1f seconds before retry %s/%s.",
                    config.EMBEDDING_QUOTA_COOLDOWN_SECONDS,
                    attempt + 1,
                    attempts,
                )
                time.sleep(config.EMBEDDING_QUOTA_COOLDOWN_SECONDS)
        raise RuntimeError("Embedding batch retry loop exited unexpectedly.")

    def embed_text(self, text: str, task_type: str = "RETRIEVAL_DOCUMENT") -> list[float] | None:
        if not text or not text.strip():
            return None
        try:
            return self._embed_batch_with_quota_retries([text], task_type=task_type)[0]
        except Exception as error:
            logger.error("Embedding failed for chunk: %s", error)
            return None

    def embed_documents(
        self,
        chunks: list[dict[str, Any]],
        batch_size: int | None = None,
    ) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
        batch_size = batch_size or config.EMBEDDING_BATCH_SIZE
        embedded: list[dict[str, Any]] = []
        failures: list[dict[str, Any]] = []

        for start in range(0, len(chunks), batch_size):
            batch = chunks[start : start + batch_size]
            texts = [chunk["text"] for chunk in batch]
            try:
                vectors = self._embed_batch_with_quota_retries(texts, task_type="RETRIEVAL_DOCUMENT")
            except Exception as batch_error:
                logger.error("Batch embedding failed after retries; skipping %s chunks: %s", len(batch), batch_error)
                failures.extend(batch)
                continue

            for chunk, vector in zip(batch, vectors):
                if not vector:
                    failures.append(chunk)
                    logger.error("Skipping chunk after embedding failure: %s", chunk.get("id"))
                    continue
                enriched = dict(chunk)
                enriched["embedding"] = vector
                embedded.append(enriched)

        return embedded, failures


_default_embedder: GeminiEmbedder | None = None


def get_embedder() -> GeminiEmbedder:
    global _default_embedder
    if _default_embedder is None:
        _default_embedder = GeminiEmbedder()
    return _default_embedder


def embed_text(text: str, task_type: str = "RETRIEVAL_DOCUMENT") -> list[float] | None:
    return get_embedder().embed_text(text, task_type=task_type)


def embed_documents(chunks: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    return get_embedder().embed_documents(chunks)
