# Project Technical Deep Dive

This document explains in depth how the Kanban MVP project was built technically, why decisions were made, and exactly how the pieces connect. It is intended for developers who want a complete, technical understanding of the codebase and deployment.

## Overview

- Frontend: `Next.js` (app router) + `React` + TypeScript
- Backend: `FastAPI` + Python 3.12 + Pydantic
- Persistence: SQLite (single-file DB at `backend/data/kanban.db`)
- Deployment: Docker multi-stage build + `docker compose`
- AI integration: OpenRouter HTTP API via `httpx` with a robust local fallback

The app presents a Kanban board UI and an AI chat sidebar that can answer questions about the board and (optionally) propose changes.

---

## High-level architecture

- Single container app (for MVP): the built static frontend is copied into the Python runtime image and served by the FastAPI app.
- HTTP API surface (backend):
  - `GET /api/ping` — simple health/ping
  - `GET /api/board` — returns persisted Kanban board JSON
  - `PUT /api/board` — saves board JSON to the DB
  - `POST /api/ai` — asks OpenRouter with board + question; falls back to local logic
  - `GET /health` — quick health check
- Data flow:
  - Browser requests `GET /api/board` -> backend reads from SQLite -> returns JSON
  - Browser sends `PUT /api/board` -> backend writes JSON into SQLite
  - Browser sends `POST /api/ai` -> backend calls OpenRouter with board JSON and question, returns response; if OpenRouter is unavailable, backend runs `local_ai_answer()` fallback

---

## Key files and responsibilities

- `Dockerfile` — multi-stage build (Node build stage -> Python runtime stage)
- `docker-compose.yml` — single service `app` with `./backend/data` bind-mounted for persistence and `env_file` for secrets
- `backend/main.py` — FastAPI app; contains API routes, DB init and accessors, AI call logic, and static file mounting
- `backend/requirements.txt` — Python dependencies (e.g., `fastapi`, `uvicorn`, `httpx`, `python-dotenv`, `pydantic`)
- `frontend/` — Next.js app source and component code; main components: `KanbanBoard.tsx`, `KanbanColumn.tsx`, `KanbanCard.tsx`, `ChatSidebar.tsx`
- `scripts/start.ps1` and `scripts/stop.ps1` — convenience wrappers for `docker compose up -d --build` and `docker compose down`
- `docs/` — design notes, developer guides, and deep dives

---

## Database design and persistence model

- Single table `boards` with schema:
  - `user TEXT PRIMARY KEY`
  - `data TEXT NOT NULL` (JSON serialized board)
  - `updated_at TEXT NOT NULL` (ISO timestamp)

- Rationale:
  - Simplicity: the MVP stores an entire board as JSON to avoid object-relational mapping complexity.
  - Local-first: SQLite is lightweight and suits a local containerized dev environment.

- File location:
  - Container path: `/app/backend/data/kanban.db`
  - Host path (bind mount): `./backend/data/kanban.db`

- Access functions (in `backend/main.py`):
  - `init_db()` — ensures the `backend/data` folder exists and creates the `boards` table
  - `initialize_board()` — seeds `INITIAL_BOARD` if no row for the default user exists (prevents overwriting persisted data)
  - `load_board()` — reads JSON from SQLite and returns a Python dict
  - `save_board_data()` — writes JSON using `INSERT OR REPLACE`

---

## Backend details and design choices

- FastAPI + Pydantic:
  - Pydantic models validate incoming/outgoing JSON, keeping the API contract explicit.
  - Route handlers return Pydantic objects or `JSONResponse` for consistent API behavior.

- Static file serving:
  - The build artifacts are copied into the runtime image at `frontend/out` and `FastAPI` mounts them with `StaticFiles(directory=str(BUILD_DIR), html=True)` when present.
  - If build artifacts are missing, `GET /` returns a JSON error instructing to build the frontend.

- AI integration:
  - `query_openrouter(question, board)` constructs a `messages` payload with a `system` prompt and a `user` prompt that includes the serialized `board`.
  - The response parsing is defensive: `extract_openrouter_response()` supports multiple response shapes (`choices[].message.content` and `output`-style blocks).
  - `local_ai_answer()` implements a compact rule-based fallback for common queries (card lookup, column listing, summary).
  - If OpenRouter key (`OPENROUTER_API_KEY`) is missing, the app raises and the controller returns a fallback response instead of failing the request.

- Error handling:
  - Most route handlers catch exceptions and return `HTTPException(status_code=500, detail=str(exc))` so failures are visible.
  - The AI endpoint specifically attempts fallback before giving up.

---

## Frontend details and design choices

- Next.js app router provides a single-page UI which fetches board state on load.
- Components decomposition:
  - `KanbanBoard`: top-level state, fetches `/api/board`, handles drag-and-drop `onDragEnd`, and issues `PUT /api/board` when the board changes.
  - `KanbanColumn`: renders the column and its cards.
  - `KanbanCard`: represents a single card; supports editing and details view.
  - `ChatSidebar`: sends `POST /api/ai` requests and displays AI responses.

- Drag-and-drop:
  - Implemented with `@dnd-kit/core` and `@dnd-kit/sortable`.
  - `onDragEnd` computes new `columns` and `cardIds` arrays and triggers a `PUT /api/board`.

- Local dev workflow:
  - You can run `npm run dev` inside `frontend/` to iterate fast without rebuilding Docker.
  - For Docker-based dev, a `docker-compose.override.yml` can mount source and enable `DEV_MODE`.

---

## Build and run (exact commands)

Requirements: Docker, Docker Compose, Node 20+, Python 3.12+ (for local backend dev)

Build + run (Docker):

```bash
cd C:\Users\Himaja\pm
# build and start
docker compose up -d --build
# watch logs
docker compose logs -f
# stop
docker compose down
```

Build frontend locally (standalone):

```bash
cd frontend
npm install
npm run build
```

Run backend locally (standalone):

```bash
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1  # Windows PowerShell
pip install -r requirements.txt
python -m uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

Verify API endpoints:

```bash
curl http://localhost:8000/api/ping
curl http://localhost:8000/api/board
curl -X POST http://localhost:8000/api/ai -H "Content-Type: application/json" -d '{"question":"What is in Review?"}'
```

---

## Docker runtime specifics and best practices

- Use bind mounts for host-visible persistence during development (`./backend/data:/app/backend/data`).
- Use named volumes for production (e.g., `volumes: - kanban-data:/app/backend/data`).
- Add a `healthcheck` (e.g., `curl -f http://localhost:8000/health`) and a `restart` policy in `docker-compose.yml`.
- Use `.dockerignore` to keep build contexts small and allow cache reuse.
- When changing only frontend sources, you can avoid reinstalling Python deps by relying on Docker cache when Dockerfile `COPY` steps are ordered correctly.

---

## Security and secret handling

- The `.env` file contains `OPENROUTER_API_KEY` for local development. Do NOT commit it.
- For production, use a secrets manager or Docker Swarm/Kubernetes secrets.
- Keep the backend container network-limited in production; the MVP uses `allow_origins: ["*"]` CORS for simplicity but should be restricted for deployed services.

---

## Testing and verification

- Frontend unit tests: `npm run test` (uses `vitest`)
- E2E: `npm run test:e2e` (uses Playwright)
- Backend: there are simple Python-based tests in `backend/` if present; otherwise, you can write `pytest` tests to call the FastAPI test client.
- Manual verification: start the app, change the board, restart, and check `backend/data/kanban.db` and `GET /api/board`.

---

## Troubleshooting checklist

- `Frontend build not found` -> re-run `npm run build` in `frontend` or rebuild Docker
- `SQLITE file missing` -> ensure `./backend/data` exists and is writable, check Docker Desktop file share settings on Windows
- `OPENROUTER` errors -> verify `.env` key and container env via `docker compose exec app env | grep OPENROUTER`
- `Permission denied` writing DB -> inspect container user and host folder permissions

---

## How the feature set was implemented (step-by-step summary)

1. Create React components for columns and cards; wire up `@dnd-kit` events.
2. Add `fetch('/api/board')` on frontend mount to load state.
3. Implement `PUT /api/board` to persist state.
4. Add `init_db()` and `initialize_board()` to create and seed the DB only once.
5. Add Docker multi-stage build to produce a single deployable image serving both frontend and backend.
6. Add AI endpoint with robust parsing and fallback so UI remains usable when external AI is unavailable.
7. Add `docker-compose.yml` with a bind mount for persistence and `.env` wiring for the OpenRouter key.

---

## Suggested next improvements

- Replace single-file JSON storage with normalized tables for cards, columns, users for easier queries and concurrency handling.
- Add user authentication and multi-board support.
- Split frontend into its own service in `docker-compose` for a faster dev loop.
- Add automated integration tests that start `docker compose` and exercise the HTTP APIs.
- Add structured AI output format so the LLM can propose board modifications deterministically.

---

## File references (where to look)

- `Dockerfile`
- `docker-compose.yml`
- `backend/main.py`
- `backend/requirements.txt`
- `frontend/package.json`
- `frontend/src/components/KanbanBoard.tsx`
- `frontend/src/components/ChatSidebar.tsx`

---

## Conclusion

This document captures how the project is constructed and deployed end-to-end. If you want, I can:
- add a diagram (Mermaid) showing request flows,
- create a `docker-compose.override.yml` for dev, or
- implement the `healthcheck`/`restart` changes directly in `docker-compose.yml` and commit them.

---

## Issues encountered and how they were fixed

- **Backend syntax error on startup**: a recent edit introduced a Python syntax error that prevented the backend from starting.
  - Fix: ran `python -m py_compile backend/main.py` to locate the error, corrected the malformed code, and recompiled.

- **Board reset on every restart**: `initialize_board()` previously overwrote persisted data by seeding unconditionally.
  - Fix: updated `initialize_board()` to SELECT first and only insert `INITIAL_BOARD` if no persisted row exists.

- **PowerShell / shell command misuse during debugging**: attempted use of bash-style heredocs and `cmd.exe` from PowerShell caused errors while running quick checks.
  - Fix: use PowerShell-appropriate commands (or open WSL/bash) and avoid Unix heredoc syntax in PowerShell; document correct commands in `docs/`.

- **Missing or invalid `OPENROUTER_API_KEY`**: AI calls failed (or were not attempted) when the environment variable was missing.
  - Fix: added defensive logic to `query_openrouter()` and `ask_ai()` to fall back to `local_ai_answer()` when the key is not set or OpenRouter returns an error; documented `.env` usage.

- **Frontend build not found at runtime**: when the Node build stage failed or artifacts weren't copied, the backend returned a JSON error instead of serving the app.
  - Fix: re-ran the frontend build (`npm run build`) to produce `out`, ensured Docker multi-stage `COPY --from=node-build /app/out ./frontend/out` is correct, and added verification steps to the docs.

- **File permission / Docker mount issues on Windows**: the bind mount for `./backend/data` sometimes failed to allow writes in the container.
  - Fix: documented Windows-specific checks (Docker Desktop file sharing, WSL path access) and suggested verifying permissions and using `docker compose exec app id` and `ls -la /app/backend/data` to debug.

Each fix was verified with these commands while implementing the project:

```bash
python -m py_compile backend/main.py
docker compose up -d --build
docker compose logs -f
curl http://localhost:8000/api/board
ls -la backend/data
sqlite3 backend/data/kanban.db "SELECT count(*) FROM boards;"
```

These verification steps are included in `docs/PROJECT_IMPLEMENTATION_STEPS.md` and the other deep-dive docs.
