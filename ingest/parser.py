from pathlib import Path
from typing import Any

import fitz

import config
from ingest.utils import category_from_path, clean_text, logger


def find_pdf_files(knowledge_dir: Path | str = config.KNOWLEDGE_DIR) -> list[Path]:
    root = Path(knowledge_dir)
    if not root.exists():
        logger.warning("Knowledge directory does not exist: %s", root)
        return []
    return sorted(path for path in root.rglob("*") if path.is_file() and path.suffix.lower() == ".pdf")


def extract_pdf_pages(pdf_path: Path | str, knowledge_dir: Path | str = config.KNOWLEDGE_DIR) -> list[dict[str, Any]]:
    path = Path(pdf_path)
    pages: list[dict[str, Any]] = []
    document = None

    try:
        relative_path = path.resolve().relative_to(Path(knowledge_dir).resolve()).as_posix()
    except ValueError:
        relative_path = path.name

    category = category_from_path(path, Path(knowledge_dir))

    try:
        document = fitz.open(path)
        for page_index in range(document.page_count):
            page_number = page_index + 1
            try:
                page = document.load_page(page_index)
                text = clean_text(page.get_text("text") or "")
                if not text:
                    continue
                pages.append(
                    {
                        "text": text,
                        "page_number": page_number,
                        "filename": path.name,
                        "relative_path": relative_path,
                        "category": category,
                    }
                )
            except Exception as page_error:
                logger.warning("Skipping page %s in %s: %s", page_number, path.name, page_error)
    except Exception as error:
        logger.error("Could not parse PDF %s: %s", path, error)
    finally:
        if document is not None:
            document.close()

    return pages
