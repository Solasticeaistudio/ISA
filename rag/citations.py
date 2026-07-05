from typing import Any

from ingest.utils import snippet


def build_citations(matches: list[dict[str, Any]]) -> list[dict[str, Any]]:
    citations: list[dict[str, Any]] = []
    seen: set[tuple[str, int, int]] = set()

    for match in matches:
        metadata = match.get("metadata", {})
        filename = str(metadata.get("filename", "Unknown document"))
        page_number = int(metadata.get("page_number") or 0)
        chunk_index = int(metadata.get("chunk_index") or 0)
        key = (filename, page_number, chunk_index)
        if key in seen:
            continue
        seen.add(key)

        text = metadata.get("snippet") or metadata.get("text") or ""
        citations.append(
            {
                "filename": filename,
                "relative_path": metadata.get("relative_path", ""),
                "page_number": page_number,
                "category": metadata.get("category", "uncategorized"),
                "product": metadata.get("product", "Unknown"),
                "document_type": metadata.get("document_type", "document"),
                "snippet": snippet(str(text)),
                "score": float(match.get("score") or 0.0),
            }
        )

    return citations
