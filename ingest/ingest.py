import sys
import time
from pathlib import Path
from typing import Any

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from pinecone import Pinecone, ServerlessSpec
from tqdm import tqdm

import config
from ingest.chunker import chunk_pages
from ingest.embedder import GeminiEmbedder
from ingest.parser import extract_pdf_pages, find_pdf_files
from ingest.utils import logger


def _index_names(pc: Pinecone) -> set[str]:
    try:
        names = pc.list_indexes().names()
        return set(names)
    except Exception:
        indexes = pc.list_indexes()
        names: set[str] = set()
        for index in indexes:
            if isinstance(index, dict):
                name = index.get("name")
            else:
                name = getattr(index, "name", None)
            if name:
                names.add(name)
        return names


def get_or_create_index(dimension: int):
    config.validate_required_env()
    pc = Pinecone(api_key=config.PINECONE_API_KEY)
    index_name = config.PINECONE_INDEX_NAME

    if index_name not in _index_names(pc):
        logger.info("Creating Pinecone index %s with dimension %s", index_name, dimension)
        pc.create_index(
            name=index_name,
            dimension=dimension,
            metric="cosine",
            spec=ServerlessSpec(cloud=config.PINECONE_CLOUD, region=config.PINECONE_REGION),
        )
        for _ in range(60):
            description = pc.describe_index(index_name)
            status = getattr(description, "status", None)
            ready = False
            if isinstance(status, dict):
                ready = bool(status.get("ready"))
            elif status is not None:
                ready = bool(getattr(status, "ready", False))
            if ready:
                break
            time.sleep(1)

    return pc.Index(index_name)


def upsert_embedded_chunks(index: Any, embedded_chunks: list[dict[str, Any]]) -> int:
    uploaded = 0
    batch_size = config.PINECONE_UPSERT_BATCH_SIZE

    for start in range(0, len(embedded_chunks), batch_size):
        batch = embedded_chunks[start : start + batch_size]
        vectors = [
            {
                "id": chunk["id"],
                "values": chunk["embedding"],
                "metadata": chunk["metadata"],
            }
            for chunk in batch
        ]
        if config.PINECONE_NAMESPACE:
            index.upsert(vectors=vectors, namespace=config.PINECONE_NAMESPACE)
        else:
            index.upsert(vectors=vectors)
        uploaded += len(vectors)

    return uploaded


def run_ingestion() -> dict[str, int]:
    config.validate_required_env()
    pdfs = find_pdf_files(config.KNOWLEDGE_DIR)
    pages: list[dict[str, Any]] = []
    pdf_failures = 0

    for pdf_path in tqdm(pdfs, desc="Parsing PDFs", unit="pdf"):
        extracted = extract_pdf_pages(pdf_path, config.KNOWLEDGE_DIR)
        if not extracted:
            pdf_failures += 1
        pages.extend(extracted)

    chunks = chunk_pages(pages)
    index = get_or_create_index(config.EMBEDDING_DIMENSION)

    embedder = GeminiEmbedder()
    embedded_chunks, embedding_failures = embedder.embed_documents(chunks)

    uploaded = 0
    if embedded_chunks:
        uploaded = upsert_embedded_chunks(index, embedded_chunks)

    return {
        "pdfs_found": len(pdfs),
        "pages_extracted": len(pages),
        "chunks_created": len(chunks),
        "vectors_uploaded": uploaded,
        "failures": pdf_failures + len(embedding_failures),
    }


def main() -> int:
    try:
        stats = run_ingestion()
    except config.ConfigurationError as error:
        print(f"Configuration error: {error}")
        return 1
    except Exception as error:
        logger.exception("Ingestion failed: %s", error)
        print(f"Ingestion failed: {error}")
        return 1

    print("\nISA ingestion complete")
    print(f"PDFs found: {stats['pdfs_found']}")
    print(f"Pages extracted: {stats['pages_extracted']}")
    print(f"Chunks created: {stats['chunks_created']}")
    print(f"Vectors uploaded: {stats['vectors_uploaded']}")
    print(f"Failures: {stats['failures']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

