# RAG Portal

A Slack-style front end for a RAG (retrieval-augmented generation) pipeline. Upload documents in the left sidebar, then chat with them in the main panel. The backend is currently a mock — it echoes canned responses so the front end can be built and tested independently of the real retrieval pipeline.

## Stack

- **Frontend**: React + TypeScript + Vite + Tailwind CSS (`frontend/`)
- **Backend**: FastAPI, managed with `uv` (`backend/`)

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

## Mock backend endpoints

- `POST /api/chat` — accepts `{ message, history }`, returns a canned assistant response.
- `POST /api/upload` — accepts a multipart file, saves it to `backend/uploads/`, returns file metadata.
- `GET /api/files` — lists uploaded file metadata (in-memory for now).
- `DELETE /api/files/{id}` — removes a file's metadata and its saved copy.

These will be replaced with real ingestion, chunking, embedding, and retrieval against a SQLite-backed corpus.
