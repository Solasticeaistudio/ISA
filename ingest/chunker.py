import re
from collections import defaultdict
from typing import Any

import config
from ingest.utils import (
    document_type_from_category,
    guess_product,
    normalize_category,
    pinecone_safe_metadata,
    snippet,
    stable_vector_id,
)


_SENTENCE_BOUNDARY = re.compile(r"(?<=[.!?])\s+(?=[A-Z0-9(])")


def _hard_split(text: str, max_chars: int, overlap: int) -> list[str]:
    parts: list[str] = []
    start = 0
    text = text.strip()
    overlap = min(max(overlap, 0), max_chars // 2)

    while start < len(text):
        end = min(start + max_chars, len(text))
        if end < len(text):
            split_at = max(text.rfind(" ", start, end), text.rfind("\n", start, end))
            if split_at > start + max_chars // 2:
                end = split_at
        part = text[start:end].strip()
        if part:
            parts.append(part)
        if end >= len(text):
            break
        start = max(end - overlap, start + 1)

    return parts


def _split_block(block: str, max_chars: int, overlap: int) -> list[str]:
    block = block.strip()
    if not block:
        return []
    if len(block) <= max_chars:
        return [block]

    sentences = [sentence.strip() for sentence in _SENTENCE_BOUNDARY.split(block) if sentence.strip()]
    if len(sentences) <= 1:
        return _hard_split(block, max_chars, overlap)

    units: list[str] = []
    current = ""
    for sentence in sentences:
        if len(sentence) > max_chars:
            if current:
                units.append(current.strip())
                current = ""
            units.extend(_hard_split(sentence, max_chars, overlap))
            continue

        candidate = f"{current} {sentence}".strip() if current else sentence
        if len(candidate) <= max_chars:
            current = candidate
        else:
            if current:
                units.append(current.strip())
            current = sentence

    if current:
        units.append(current.strip())
    return units


def _tail_overlap(text: str, overlap: int) -> str:
    if overlap <= 0 or not text:
        return ""
    tail = text[-overlap:]
    first_space = tail.find(" ")
    if first_space > 0:
        tail = tail[first_space + 1 :]
    return tail.strip()


def chunk_text(text: str, max_chars: int = 1800, overlap: int = 250) -> list[str]:
    text = text.strip()
    if not text:
        return []

    max_chars = max(500, max_chars)
    overlap = min(max(overlap, 0), max_chars // 2)
    blocks = [block.strip() for block in re.split(r"\n\s*\n+", text) if block.strip()]
    if not blocks:
        blocks = [text]

    units: list[str] = []
    for block in blocks:
        units.extend(_split_block(block, max_chars, overlap))

    chunks: list[str] = []
    current = ""
    for unit in units:
        candidate = f"{current}\n\n{unit}".strip() if current else unit
        if len(candidate) <= max_chars:
            current = candidate
            continue

        if current:
            chunks.append(current.strip())

        carry = _tail_overlap(current, overlap)
        with_overlap = f"{carry}\n\n{unit}".strip() if carry else unit
        current = with_overlap if len(with_overlap) <= max_chars else unit

        if len(current) > max_chars:
            chunks.extend(_hard_split(current, max_chars, overlap))
            current = ""

    if current:
        chunks.append(current.strip())

    return [chunk for chunk in chunks if chunk]


def chunk_pages(pages: list[dict[str, Any]]) -> list[dict[str, Any]]:
    chunks: list[dict[str, Any]] = []
    chunk_counters: defaultdict[str, int] = defaultdict(int)

    for page in pages:
        relative_path = page["relative_path"]
        filename = page["filename"]
        category = normalize_category(page.get("category"))
        page_number = int(page["page_number"])
        product = guess_product(filename)
        document_type = document_type_from_category(category, filename)

        for text in chunk_text(
            page["text"],
            max_chars=config.CHUNK_MAX_CHARS,
            overlap=config.CHUNK_OVERLAP_CHARS,
        ):
            chunk_counters[relative_path] += 1
            chunk_index = chunk_counters[relative_path]
            vector_id = stable_vector_id(relative_path, page_number, chunk_index)
            metadata = {
                "filename": filename,
                "relative_path": relative_path,
                "category": category,
                "page_number": page_number,
                "chunk_index": chunk_index,
                "product": product,
                "document_type": document_type,
                "text": text,
                "snippet": snippet(text),
            }
            chunks.append(
                {
                    "id": vector_id,
                    "text": text,
                    "metadata": pinecone_safe_metadata(metadata),
                }
            )

    return chunks
