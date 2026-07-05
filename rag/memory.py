import json
import re
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import config


def _conversation_path(conversation_id: str) -> Path:
    safe_id = re.sub(r"[^a-zA-Z0-9_-]", "", conversation_id)[:80]
    if not safe_id:
        safe_id = uuid.uuid4().hex
    return config.CONVERSATIONS_DIR / f"{safe_id}.jsonl"


def save_conversation_turn(
    conversation_id: str | None,
    user_message: str,
    assistant_answer: str,
    citations: list[dict[str, Any]] | None = None,
) -> str:
    conversation_id = conversation_id or uuid.uuid4().hex
    path = _conversation_path(conversation_id)
    path.parent.mkdir(parents=True, exist_ok=True)
    record = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "user": user_message,
        "assistant": assistant_answer,
        "citations": citations or [],
    }
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(record, ensure_ascii=False) + "\n")
    return path.stem


def load_recent_history(conversation_id: str, limit: int = 6) -> list[dict[str, Any]]:
    path = _conversation_path(conversation_id)
    if not path.exists():
        return []
    records: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            try:
                records.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    return records[-limit:]
