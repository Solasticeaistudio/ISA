from __future__ import annotations

import os
from typing import Any

from flask import Flask, abort, jsonify, render_template, request, send_from_directory
from google import genai

import config
from rag.citations import build_citations
from rag.clarification import MODEL_CLARIFICATION_RESPONSE, should_ask_for_model
from rag.memory import save_conversation_turn
from rag.prompts import build_chat_prompt
from rag.retriever import format_context, retrieve_context


SUGGESTED_PROMPTS = [
    "How do I replace the columns?",
    "Why won't my battery charge?",
    "What does this alarm mean?",
    "Compare the Rove 6 and G5.",
    "Is this device FAA approved?",
]

app = Flask(__name__)
app.config["SECRET_KEY"] = config.FLASK_SECRET_KEY


def _extract_model_text(response: Any) -> str:
    text = getattr(response, "text", None)
    if text:
        return str(text).strip()

    candidates = getattr(response, "candidates", None) or []
    parts: list[str] = []
    for candidate in candidates:
        content = getattr(candidate, "content", None)
        for part in getattr(content, "parts", []) or []:
            part_text = getattr(part, "text", None)
            if part_text:
                parts.append(str(part_text))
    return "\n".join(parts).strip()


def _generate_answer(question: str, context: str) -> str:
    prompt = build_chat_prompt(question, context)
    client = genai.Client(api_key=config.GEMINI_API_KEY)

    try:
        response = client.models.generate_content(model=config.GEMINI_MODEL, contents=prompt)
        answer = _extract_model_text(response)
    except AttributeError:
        interaction = client.interactions.create(model=config.GEMINI_MODEL, input=prompt)
        answer = getattr(interaction, "output_text", "").strip()

    if not answer:
        raise RuntimeError("Gemini returned an empty response.")
    return answer


def _knowledge_pdf_count() -> int:
    if not config.KNOWLEDGE_DIR.exists():
        return 0
    return sum(1 for path in config.KNOWLEDGE_DIR.rglob("*") if path.is_file() and path.suffix.lower() == ".pdf")


@app.get("/")
def index():
    return render_template("index.html", suggested_prompts=SUGGESTED_PROMPTS)


@app.get("/api/health")
def health():
    missing = config.missing_required_env()
    return jsonify(
        {
            "status": "ok" if not missing else "degraded",
            "missing_env": missing,
            "gemini_model": config.GEMINI_MODEL,
            "embedding_model": config.GEMINI_EMBEDDING_MODEL,
            "pinecone_index": config.PINECONE_INDEX_NAME,
            "knowledge_pdfs": _knowledge_pdf_count(),
        }
    )



@app.get("/api/document/<path:relative_path>")
def document(relative_path: str):
    root = config.KNOWLEDGE_DIR.resolve()
    candidate = (root / relative_path).resolve()

    try:
        candidate.relative_to(root)
    except ValueError:
        abort(404)

    if not candidate.is_file() or candidate.suffix.lower() != ".pdf":
        abort(404)

    safe_relative = candidate.relative_to(root).as_posix()
    return send_from_directory(root, safe_relative, mimetype="application/pdf", as_attachment=False)

@app.get("/api/suggested-prompts")
def suggested_prompts():
    return jsonify({"prompts": SUGGESTED_PROMPTS})


@app.post("/api/chat")
def chat():
    payload = request.get_json(silent=True) or {}
    message = str(payload.get("message", "")).strip()
    if not message:
        return jsonify({"error": "Message is required."}), 400

    missing = config.missing_required_env()
    if missing:
        return (
            jsonify(
                {
                    "error": "ISA is missing required environment variables.",
                    "missing_env": missing,
                }
            ),
            503,
        )

    product = payload.get("product") or None
    category = payload.get("category") or None
    conversation_id = payload.get("conversation_id") or None

    try:
        if should_ask_for_model(message, product):
            saved_conversation_id = save_conversation_turn(
                conversation_id,
                message,
                MODEL_CLARIFICATION_RESPONSE,
                [],
            )
            return jsonify(
                {
                    "answer": MODEL_CLARIFICATION_RESPONSE,
                    "citations": [],
                    "conversation_id": saved_conversation_id,
                    "needs_clarification": True,
                }
            )

        matches = retrieve_context(
            message,
            top_k=config.RETRIEVAL_TOP_K,
            product=product,
            category=category,
        )
        citations = build_citations(matches)

        if not matches:
            answer = (
                "I do not have enough information in the uploaded Inogen documents to answer that. "
                "Please check that the relevant PDF has been added to the knowledge folder and ingested. "
                "For product safety, medical, or urgent issues, contact Inogen support, emergency services, "
                "or a healthcare provider as appropriate."
            )
        else:
            answer = _generate_answer(message, format_context(matches))

        saved_conversation_id = save_conversation_turn(conversation_id, message, answer, citations)
        return jsonify(
            {
                "answer": answer,
                "citations": citations,
                "conversation_id": saved_conversation_id,
            }
        )
    except config.ConfigurationError as error:
        return jsonify({"error": str(error)}), 503
    except Exception as error:
        app.logger.exception("Chat request failed: %s", error)
        return jsonify({"error": "ISA could not complete the chat request.", "detail": str(error)}), 502


if __name__ == "__main__":
    port = int(os.getenv("PORT", os.getenv("FLASK_RUN_PORT", "5000")))
    app.run(debug=config.FLASK_ENV == "development", host="127.0.0.1", port=port)


