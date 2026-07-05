from typing import Any

from pinecone import Pinecone

import config
from ingest.embedder import GeminiEmbedder
from ingest.utils import logger, normalize_category


PRODUCT_FILTER_ALIASES = {
    "G5": ["G5", "One G5"],
    "One G5": ["One G5", "G5"],
    "Inogen One": ["Inogen One", "One G5", "G4", "G5"],
}


def _clean_selector(value: str | None, all_prefix: str) -> str | None:
    if not value:
        return None
    value = str(value).strip()
    if not value or value.lower().startswith(all_prefix.lower()):
        return None
    return value


def _build_filter(product: str | None = None, category: str | None = None) -> dict[str, Any] | None:
    filters: dict[str, Any] = {}
    clean_product = _clean_selector(product, "all products")
    clean_category = _clean_selector(category, "all categories")

    if clean_product:
        products = PRODUCT_FILTER_ALIASES.get(clean_product, [clean_product])
        filters["product"] = {"$in": products}
    if clean_category:
        filters["category"] = {"$eq": normalize_category(clean_category)}

    return filters or None


def _normalize_match(match: Any) -> dict[str, Any]:
    if isinstance(match, dict):
        return {
            "id": match.get("id"),
            "score": match.get("score", 0.0),
            "metadata": match.get("metadata") or {},
        }
    return {
        "id": getattr(match, "id", None),
        "score": getattr(match, "score", 0.0),
        "metadata": getattr(match, "metadata", {}) or {},
    }


def _get_index():
    config.validate_required_env()
    pc = Pinecone(api_key=config.PINECONE_API_KEY)
    return pc.Index(config.PINECONE_INDEX_NAME)


def retrieve_context(
    question: str,
    top_k: int = 6,
    product: str | None = None,
    category: str | None = None,
) -> list[dict[str, Any]]:
    embedder = GeminiEmbedder()
    query_vector = embedder.embed_text(question, task_type="RETRIEVAL_QUERY")
    if not query_vector:
        logger.error("Could not embed user query.")
        return []

    index = _get_index()
    query_args: dict[str, Any] = {
        "vector": query_vector,
        "top_k": top_k,
        "include_metadata": True,
    }
    filter_dict = _build_filter(product=product, category=category)
    if filter_dict:
        query_args["filter"] = filter_dict
    if config.PINECONE_NAMESPACE:
        query_args["namespace"] = config.PINECONE_NAMESPACE

    response = index.query(**query_args)
    matches = getattr(response, "matches", None)
    if matches is None and isinstance(response, dict):
        matches = response.get("matches", [])
    return [_normalize_match(match) for match in matches or []]


def format_context(matches: list[dict[str, Any]]) -> str:
    sections: list[str] = []
    for number, match in enumerate(matches, start=1):
        metadata = match.get("metadata", {})
        filename = metadata.get("filename", "Unknown document")
        page = metadata.get("page_number", "?")
        category = metadata.get("category", "uncategorized")
        product = metadata.get("product", "Unknown")
        text = metadata.get("text") or metadata.get("snippet") or ""
        sections.append(
            f"[{number}] Source: {filename} | Page: {page} | Category: {category} | Product: {product}\n{text}"
        )
    return "\n\n".join(sections)
