# ISA Interview Demo Script

This script is designed to keep the interview focused. The goal is to show that ISA is a real RAG support assistant, explain the engineering decisions clearly, and be honest about what is MVP versus production hardening.

## 30-Second Summary

ISA is a Flask-based RAG support copilot for Inogen documentation. It ingests PDFs, extracts page text with PyMuPDF, chunks the text with metadata, embeds chunks with Gemini, stores them in Pinecone, retrieves relevant chunks for a question, and asks Gemini to answer only from that context with citations.

## Suggested Demo Flow

### 1. Start With The Problem

Say:

> Support teams need fast answers from manuals and procedures, but product documentation is scattered across PDFs. ISA turns those documents into a cited support copilot.

### 2. Show The Repo Shape

Point out:

- `ingest/` handles PDFs, chunks, embeddings, and Pinecone upserts.
- `rag/` handles retrieval, prompting, citations, memory, and clarification.
- `app.py` exposes the Flask routes.
- `templates/` and `static/` provide the support-console UI.
- `.env.example` documents secrets without committing them.

### 3. Explain Ingestion

Open `ingest/ingest.py`, `ingest/parser.py`, and `ingest/chunker.py`.

Key talking points:

- Recursive PDF ingestion under `knowledge/`.
- Page-aware extraction with PyMuPDF.
- Chunks preserve filename, relative path, category, page number, chunk index, product guess, and document type.
- Bad PDFs do not crash the whole ingestion run.
- Vector IDs are deterministic.

### 4. Explain Retrieval

Open `rag/retriever.py`.

Key talking points:

- User question is embedded as a retrieval query.
- Pinecone returns top matching chunks.
- Product and category selectors map into metadata filters.
- Retrieved chunks are formatted as labeled sources for the model.

### 5. Explain Grounding And Citations

Open `rag/prompts.py` and `rag/citations.py`.

Key talking points:

- The prompt tells ISA to answer only from retrieved context.
- Backend citation cards are built from Pinecone metadata, not model-generated citation text.
- If context is insufficient, ISA says it does not have enough information.
- Medical diagnosis and oxygen-therapy advice are out of scope.

### 6. Show The UI

Run:

```bash
python app.py
```

Open:

```text
http://127.0.0.1:5000
```

If using a custom local port:

```powershell
$env:PORT="5001"
python app.py
```

Open:

```text
http://127.0.0.1:5001
```

### 7. Ask High-Signal Questions

Use these in order:

1. `How do I replace the columns?`

Expected behavior: ISA should ask for the model if no model is selected.

2. Select `Rove 6`, then ask:

```text
How do I replace the columns?
```

Expected behavior: ISA retrieves source material and answers with citations.

3. Ask:

```text
Compare the Rove 6 and G5.
```

Expected behavior: ISA retrieves sources for both products and gives a grounded comparison.

4. Ask:

```text
What oxygen flow setting should I use?
```

Expected behavior: ISA should avoid medical guidance and recommend the appropriate support or healthcare contact path.

### 8. Click Source Chips

Show that source chips open the local PDF route with a page anchor:

```text
/api/document/<relative_path>#page=<page>
```

Explain that the backend validates the path stays inside `knowledge/` and only serves PDFs.

### 9. Discuss Testing

Point to:

- `tests/test_clarification.py`
- `tests/test_app_clarification.py`
- `.github/workflows/ci.yml`

Say:

> I kept tests focused on behavior that matters for support safety: model clarification and route behavior. The CI checks Python syntax, unit tests, and frontend JavaScript syntax.

### 10. Close With The Roadmap

Open `FUTURE_ENHANCEMENTS.md` and `SECURITY.md`.

Say:

> I intentionally did not overbuild the production analytics and admin layers before the interview. The MVP proves the workflow; the roadmap shows exactly how I would harden and extend it inside Inogen's environment.

## Good Interview Framing

Strong answer if asked about limitations:

> ISA is an MVP, not a fully hardened enterprise deployment. It already has grounding, source citations, model clarification, safe local PDF links, and repository hygiene. The next production phase would add prompt-injection scanning, auth, rate limits, document governance, analytics, and deployment hardening.

## Commands To Verify Before The Interview

```bash
python -m py_compile app.py config.py ingest/ingest.py ingest/parser.py ingest/chunker.py ingest/embedder.py ingest/utils.py rag/retriever.py rag/prompts.py rag/citations.py rag/memory.py rag/clarification.py
python -m unittest discover -s tests -v
node --check static/js/chat.js
```
