import os
from pathlib import Path
from typing import Iterable

from dotenv import load_dotenv


BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env", override=True)

KNOWLEDGE_DIR = BASE_DIR / "knowledge"
UPLOAD_DIR = BASE_DIR / "uploads"
CONVERSATIONS_DIR = BASE_DIR / "conversations"
LOGS_DIR = BASE_DIR / "logs"
TEMPLATES_DIR = BASE_DIR / "templates"
STATIC_DIR = BASE_DIR / "static"

CATEGORIES = ("manuals", "accessories", "procedures", "getting_started")
PRODUCTS = ("Rove 4", "Rove 6", "G4", "G5", "At Home", "Voxi 5", "One G5", "Inogen One")

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "").strip()
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.5-flash").strip()
GEMINI_EMBEDDING_MODEL = os.getenv("GEMINI_EMBEDDING_MODEL", "text-embedding-004").strip()

PINECONE_API_KEY = os.getenv("PINECONE_API_KEY", "").strip()
PINECONE_INDEX_NAME = os.getenv("PINECONE_INDEX_NAME", "isa-support").strip()
PINECONE_NAMESPACE = os.getenv("PINECONE_NAMESPACE", "").strip()
PINECONE_CLOUD = os.getenv("PINECONE_CLOUD", "aws").strip()
PINECONE_REGION = os.getenv("PINECONE_REGION", "us-east-1").strip()

EMBEDDING_DIMENSION = int(os.getenv("EMBEDDING_DIMENSION", "768"))
EMBEDDING_BATCH_SIZE = int(os.getenv("EMBEDDING_BATCH_SIZE", "16"))
EMBEDDING_MAX_ITEMS_PER_MINUTE = int(os.getenv("EMBEDDING_MAX_ITEMS_PER_MINUTE", "80"))
EMBEDDING_MIN_BATCH_INTERVAL_SECONDS = float(os.getenv("EMBEDDING_MIN_BATCH_INTERVAL_SECONDS", "0"))
EMBEDDING_QUOTA_COOLDOWN_SECONDS = float(os.getenv("EMBEDDING_QUOTA_COOLDOWN_SECONDS", "65"))
EMBEDDING_QUOTA_RETRY_ATTEMPTS = int(os.getenv("EMBEDDING_QUOTA_RETRY_ATTEMPTS", "6"))
PINECONE_UPSERT_BATCH_SIZE = int(os.getenv("PINECONE_UPSERT_BATCH_SIZE", "100"))

CHUNK_MAX_CHARS = int(os.getenv("CHUNK_MAX_CHARS", "1800"))
CHUNK_OVERLAP_CHARS = int(os.getenv("CHUNK_OVERLAP_CHARS", "250"))
RETRIEVAL_TOP_K = int(os.getenv("RETRIEVAL_TOP_K", "6"))

FLASK_SECRET_KEY = os.getenv("FLASK_SECRET_KEY", "change-me")
FLASK_ENV = os.getenv("FLASK_ENV", "development")

for directory in (KNOWLEDGE_DIR, UPLOAD_DIR, CONVERSATIONS_DIR, LOGS_DIR, TEMPLATES_DIR, STATIC_DIR):
    directory.mkdir(parents=True, exist_ok=True)

for category in CATEGORIES:
    (KNOWLEDGE_DIR / category).mkdir(parents=True, exist_ok=True)


class ConfigurationError(RuntimeError):
    """Raised when required runtime configuration is missing."""


def missing_required_env(required: Iterable[str] | None = None) -> list[str]:
    required_names = list(required or ("GEMINI_API_KEY", "PINECONE_API_KEY", "PINECONE_INDEX_NAME"))
    missing: list[str] = []
    for name in required_names:
        if not os.getenv(name, "").strip():
            missing.append(name)
    return missing


def validate_required_env(required: Iterable[str] | None = None) -> None:
    missing = missing_required_env(required)
    if missing:
        joined = ", ".join(missing)
        raise ConfigurationError(f"Missing required environment variable(s): {joined}")



