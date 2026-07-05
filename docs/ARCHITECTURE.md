# ISA Architecture

ISA is a small, interview-readable RAG application. The architecture is intentionally modular: ingestion, retrieval/generation, citations, and the frontend each have clear ownership.

## System Diagram

```mermaid
flowchart LR
    A[PDFs in knowledge/] --> B[PyMuPDF Parser]
    B --> C[Page Text]
    C --> D[Chunker]
    D --> E[Metadata Enrichment]
    E --> F[Gemini Embeddings]
    F --> G[Pinecone Index]

    U[User Question] --> H[Flask /api/chat]
    H --> I[Model Clarification Guard]
    I -->|Needs model| J[Clarification Response]
    I -->|Ready| K[Query Embedding]
    K --> G
    G --> L[Top-K Matches]
    L --> M[Context Formatter]
    M --> N[Grounded Gemini Prompt]
    N --> O[Answer]
    L --> P[Backend Citation Builder]
    O --> Q[JSON Response]
    P --> Q
    Q --> R[Chat UI + Source Chips]
    R --> S[/api/document PDF Links]
```

## Runtime Components

### Flask App

`app.py` owns the public web routes:

- `/` renders the chat UI.
- `/api/health` reports runtime configuration and knowledge PDF count.
- `/api/suggested-prompts` returns prompt cards.
- `/api/chat` executes the RAG flow.
- `/api/document/<relative_path>` serves cited PDFs from `knowledge/` after path validation.

### Ingestion Pipeline

The ingestion pipeline is run manually:

```bash
python ingest/ingest.py
```

Flow:

1. `find_pdf_files()` recursively locates PDFs under `knowledge/`.
2. `extract_pdf_pages()` extracts page text with PyMuPDF.
3. `chunk_pages()` creates page-aware chunks.
4. `GeminiEmbedder` embeds chunks with retry and pacing behavior.
5. Pinecone index is created if needed.
6. Vectors are upserted with text and metadata.

### Retrieval Pipeline

`rag/retriever.py` handles query-time retrieval:

1. Embed the user question.
2. Build optional Pinecone metadata filters from product/category selectors.
3. Query Pinecone for top matches.
4. Normalize match objects into dictionaries.
5. Format context blocks for Gemini.

### Prompting

`rag/prompts.py` defines ISA's core behavior:

- warm support-assistant voice
- answer only from retrieved context
- avoid unsupported product claims
- avoid medical diagnosis or oxygen-therapy advice
- ask for model details when needed
- cite retrieved sources

### Citations

`rag/citations.py` builds structured citations from retrieved metadata. The frontend does not trust the model to create source cards.

Each citation includes:

- filename
- relative path
- page number
- category
- product
- document type
- snippet
- retrieval score

### Frontend

`templates/index.html`, `static/css/style.css`, and `static/js/chat.js` provide the support-console UI.

Key UI behaviors:

- suggested prompt cards
- product/category selectors
- model clarification display
- source chips under assistant answers
- Source Pearls panel
- PDF source links
- pinboard
- scratchpad

## Data Boundaries

### Local Files

- `.env` contains secrets and is ignored.
- `knowledge/` contains private PDFs and PDFs are ignored.
- `conversations/` stores local JSONL chat turns and is ignored except `.gitkeep`.
- `logs/` stores local logs and is ignored except `.gitkeep`.

### Pinecone

Pinecone stores embeddings and chunk metadata. In the MVP, chunk text is stored in metadata for simplicity. A production implementation could move chunk text to a controlled document store and keep only IDs and metadata in Pinecone.

### Gemini

Gemini is used for embeddings and answer generation. The generation prompt receives retrieved context, the question, and safety constraints.

## Deployment Shape

For local use, ISA can run directly:

```bash
python app.py
```

For production, use a WSGI server such as Gunicorn or Waitress behind HTTPS, with environment variables provided by the hosting platform.
