import hashlib
import logging
import re
import sys
from pathlib import Path
from typing import Any

import config


CATEGORY_ALIASES = {
    "manual": "manuals",
    "manuals": "manuals",
    "accessory": "accessories",
    "accessories": "accessories",
    "procedure": "procedures",
    "procedures": "procedures",
    "getting_started": "getting_started",
    "gettingstarted": "getting_started",
    "getting_start": "getting_started",
    "getting started": "getting_started",
    "getting-started": "getting_started",
}

DOCUMENT_TYPE_BY_CATEGORY = {
    "manuals": "manual",
    "accessories": "accessory_guide",
    "procedures": "procedure",
    "getting_started": "getting_started_guide",
}


def setup_logging(name: str = "isa") -> logging.Logger:
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
    logger = logging.getLogger(name)
    if logger.handlers:
        return logger

    logger.setLevel(logging.INFO)
    formatter = logging.Formatter(
        "[%(asctime)s] [%(levelname)s] [%(name)s] %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    console = logging.StreamHandler(sys.stdout)
    console.setLevel(logging.INFO)
    console.setFormatter(formatter)
    logger.addHandler(console)

    config.LOGS_DIR.mkdir(parents=True, exist_ok=True)
    file_handler = logging.FileHandler(config.LOGS_DIR / "isa.log", encoding="utf-8")
    file_handler.setLevel(logging.INFO)
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    return logger


logger = setup_logging()


def normalize_category(category: str | None) -> str:
    if not category:
        return "uncategorized"
    cleaned = str(category).strip().lower().replace("-", "_").replace(" ", "_")
    cleaned = re.sub(r"_+", "_", cleaned)
    return CATEGORY_ALIASES.get(cleaned, cleaned)


def category_from_path(pdf_path: Path, knowledge_dir: Path = config.KNOWLEDGE_DIR) -> str:
    try:
        relative = Path(pdf_path).resolve().relative_to(Path(knowledge_dir).resolve())
        if relative.parts:
            return normalize_category(relative.parts[0])
    except ValueError:
        pass
    parent_name = Path(pdf_path).parent.name
    return normalize_category(parent_name)


def guess_product(filename: str) -> str:
    name = Path(filename).stem.lower()
    normalized = re.sub(r"[^a-z0-9]+", " ", name)

    checks: list[tuple[str, str]] = [
        (r"\brove\s*4\b", "Rove 4"),
        (r"\brove\s*6\b", "Rove 6"),
        (r"\bvoxi\s*5\b", "Voxi 5"),
        (r"\bat\s*home\b", "At Home"),
        (r"\binogen\s+one\s+g\s*5\b|\bone\s+g\s*5\b", "One G5"),
        (r"\binogen\s+one\s+g\s*4\b|\bg\s*4\b", "G4"),
        (r"\bg\s*5\b", "G5"),
        (r"\binogen\s+one\b", "Inogen One"),
    ]
    for pattern, product in checks:
        if re.search(pattern, normalized):
            return product
    return "Unknown"


def document_type_from_category(category: str, filename: str = "") -> str:
    normalized_category = normalize_category(category)
    lower_name = filename.lower()
    if "faa" in lower_name or normalized_category == "faa":
        return "faa_information"
    if "warranty" in lower_name or normalized_category == "warranty":
        return "warranty"
    if "troubleshoot" in lower_name or normalized_category == "troubleshooting":
        return "troubleshooting"
    return DOCUMENT_TYPE_BY_CATEGORY.get(normalized_category, normalized_category or "document")


def stable_vector_id(relative_path: str, page_number: int, chunk_index: int) -> str:
    raw = f"{relative_path}|page:{page_number}|chunk:{chunk_index}"
    digest = hashlib.sha256(raw.encode("utf-8", errors="ignore")).hexdigest()
    return f"isa-{digest[:32]}"


def clean_text(text: str) -> str:
    text = text.replace("\x00", " ")
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n[ \t]+", "\n", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def snippet(text: str, limit: int = 320) -> str:
    compact = re.sub(r"\s+", " ", text).strip()
    if len(compact) <= limit:
        return compact
    return compact[: limit - 3].rstrip() + "..."


def pinecone_safe_metadata(metadata: dict[str, Any]) -> dict[str, Any]:
    safe: dict[str, Any] = {}
    for key, value in metadata.items():
        if value is None:
            continue
        if isinstance(value, (str, int, float, bool)):
            safe[key] = value
        elif isinstance(value, list):
            safe[key] = [str(item) for item in value]
        else:
            safe[key] = str(value)
    return safe

