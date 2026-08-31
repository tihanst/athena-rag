# Athena

Self-hosted, LLM-powered, hybrid search-based RAG research application. Upload documents in the sidebar, then chat with them in the main panel.

## Stack

- **Frontend**: React + TypeScript + Vite + Tailwind CSS (`frontend/`)
- **Backend**: FastAPI, managed with `uv` (`backend/`)

## How it works

- **Ingestion**: uploaded PDFs/DOCX/TXT/MD are converted to markdown, chunked, and embedded (`uploader.py`, `text_extractor.py`, `sem_search.py`).
- **Retrieval**: queries are run through hybrid search — SQLite FTS5 lexical search fused with BGE dense-embedding similarity (`lex_search.py`, `sem_search.py`, `search_executor.py`), then reranked with a cross-encoder (`rerank.py`).
- **Chat**: the orchestrator extracts search terms from the conversation, retrieves and reranks relevant chunks, assembles them into a prompt, and streams a response from an LLM via `litellm` (`orchestrator.py`, `prompt_constructor.py`, `llm.py`).

## Configuration

The backend needs a `backend/.env` file (gitignored) defining the LLM and cross-encoder settings read by `config.py`:

```bash
SEARCH_PLANNER_LLM__MODEL_PROVIDER=...
SEARCH_PLANNER_LLM__MODEL_NAME=...
SEARCH_PLANNER_LLM__MODEL_ID=...

CHAT_LLM__MODEL_PROVIDER=...
CHAT_LLM__MODEL_NAME=...
CHAT_LLM__MODEL_ID=...

SUMMARIZER_LLM__MODEL_PROVIDER=...
SUMMARIZER_LLM__MODEL_NAME=...
SUMMARIZER_LLM__MODEL_ID=...

CROSS_ENCODER_MODEL=...
CROSS_ENCODER_TOP_K=...
```

Plus whatever API key(s) your chosen LLM provider(s) need (see [litellm's provider docs](https://docs.litellm.ai/docs/providers)).

## Running locally

The project root has its own `package.json` that uses [`concurrently`](https://www.npmjs.com/package/concurrently) to run the backend and frontend dev servers as a single process, so you don't have to manage two terminals.

One-time setup:

```bash
npm install   # installs concurrently at the project root
```

Then, from the project root:

```bash
npm run dev
```

This runs `uv run uvicorn app.main:app --reload` (backend, `http://127.0.0.1:8000`) and `npm run dev` inside `frontend/` (Vite, `http://localhost:5173`) at the same time, with color-coded `[backend]`/`[frontend]` log prefixes. Ctrl+C stops both.

The Vite dev server proxies `/api/*` requests to the FastAPI backend (see `frontend/vite.config.ts`), so the app works at `http://localhost:5173` with no extra configuration.

Prefer separate terminals? You can still run each side on its own:

```bash
# backend
cd backend && uv run uvicorn app.main:app --reload

# frontend
cd frontend && npm run dev
```

## API

- `POST /api/chat` — accepts `{ message, history }`, runs the RAG pipeline, returns the assistant's response.
- `POST /api/upload` — accepts a multipart file, ingests it (chunk + embed + index), returns file metadata.
- `GET /api/files` — lists uploaded file metadata.
- `GET /api/files/status` — flags files referenced in the database but missing on disk.
- `DELETE /api/files/{id}` — removes a file's metadata and its saved copy.
