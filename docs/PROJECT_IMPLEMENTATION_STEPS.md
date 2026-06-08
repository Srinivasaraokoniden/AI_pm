# Project Implementation Steps

This document records the exact steps taken to make the Kanban MVP project work from the start. It explains the technologies used, the architecture decisions, the file-level changes, and the commands that were executed.

## 1. Initial review and planning

1. Open the repository and inspect the folder structure.
   - Confirm the presence of `frontend/`, `backend/`, `Dockerfile`, `docker-compose.yml`, and `scripts/`.
   - Read `docs/PLAN.md` to understand the intended project goals.
2. Identify the main implementation areas:
   - frontend React/Next.js app
   - backend FastAPI server
   - persistence via SQLite
   - Docker container build and runtime
   - AI integration using OpenRouter
3. Decide on an end-to-end flow:
   - frontend fetches and updates board state through backend APIs
   - backend persists board state in SQLite
   - Docker builds frontend and backend, then serves the frontend as static assets
   - AI endpoint uses OpenRouter and falls back to local logic when necessary

## 2. Setting up the frontend

1. Inspect `frontend/package.json` and confirm dependencies:
   - `next@16.1.6`, `react@19.2.3`, `@dnd-kit/core`, `@dnd-kit/sortable`
   - testing tools like `vitest` and `@playwright/test`
2. Confirm the UI components and routes:
   - `frontend/src/app/page.tsx` is the main page entry point
   - `frontend/src/components/KanbanBoard.tsx` contains board state management and API calls
   - `frontend/src/components/ChatSidebar.tsx` implements the AI chat integration
3. Run the frontend build to verify the app compiles successfully:
   - `cd C:\Users\Himaja\pm\frontend`
   - `npm install`
   - `npm run build`
4. Note the success criteria:
   - Next.js build completes without TypeScript or runtime compilation errors
   - the frontend can be built independently before Docker integration

## 3. Setting up the backend

1. Open `backend/main.py` and read the code structure.
   - FastAPI application creation
   - CORS middleware configuration
   - Pydantic models for `BoardData`, `Column`, `Card`, `ChatRequest`, `AIResponse`
   - initial board data in `INITIAL_BOARD`
2. Confirm database persistence logic exists.
   - `init_db()` creates `boards` table in `backend/data/kanban.db`
   - `load_board()`, `initialize_board()`, and `save_board_data()` handle data access
3. Ensure AI integration is present.
   - `query_openrouter()` posts to OpenRouter with the board state and question
   - `extract_openrouter_response()` parses the returned JSON
   - `local_ai_answer()` is the fallback when external AI is unavailable
4. Validate Python syntax for the backend:
   - `python -m py_compile backend/main.py`
   - Confirm it passes to ensure no syntax errors exist

## 4. Implementing persistence properly

1. Identify the persistence issue.
   - `initialize_board()` was being called on every startup and could overwrite state
   - the database must only be seeded when no existing row exists
2. Update `initialize_board()` as follows:
   - check `SELECT data FROM boards WHERE user = ?`
   - if a row exists, return the persisted board JSON
   - if no row exists, insert `INITIAL_BOARD` and return the default board
3. Confirm the persisted database location.
   - `DATA_DIR = ROOT_DIR / "data"`
   - `DB_PATH = DATA_DIR / "kanban.db"`
4. Verify the backend startup hooks.
   - `@app.on_event("startup")` calls both `init_db()` and `initialize_board()`
   - this ensures the database exists and the board is seeded once

## 5. Dockerizing the application

1. Read `Dockerfile` and understand the multi-stage build:
   - Stage 1: build the frontend using `node:20-alpine`
     - copy frontend files
     - run `npm install`
     - run `npm run build`
   - Stage 2: build Python backend using `python:3.12-slim`
     - install backend dependencies from `backend/requirements.txt`
     - copy backend source
     - copy generated frontend output from stage 1 into `/app/frontend/out`
     - start the app with `uvicorn main:app --host 0.0.0.0 --port 8000`
2. Read `docker-compose.yml`:
   - single service `app`
   - ports: `8000:8000`
   - volume mount: `./backend/data:/app/backend/data`
   - `env_file: .env`
3. Confirm `scripts/start.ps1` and `scripts/stop.ps1` run Docker compose commands:
   - `docker compose up -d --build`
   - `docker compose down`

## 6. Wiring the frontend to the backend

1. Confirm API endpoints and frontend requests.
   - frontend GET `/api/board` to fetch the current board
   - frontend PUT `/api/board` to save updates
   - frontend POST `/api/ai` to ask AI questions
2. Verify the frontend uses `fetch()` correctly.
3. Confirm backend routes in `backend/main.py`:
   - `GET /api/ping`
   - `GET /api/board`
   - `PUT /api/board`
   - `POST /api/ai`
   - `GET /health`
4. Validate the static file serving.
   - `if BUILD_DIR.exists()` mount `StaticFiles(directory=str(BUILD_DIR), html=True)` on `/`
   - else return a JSON error message for the root path

## 7. AI integration and fallback

1. Confirm `.env` usage.
   - `load_dotenv(ROOT_DIR.parent / ".env")`
   - `OPENROUTER_API_KEY = os.environ.get("OPENROUTER_API_KEY")`
2. Inspect `query_openrouter()` payload.
   - `model`: `openai/gpt-oss-120b`
   - `messages`: system prompt + user prompt containing board state
   - `temperature`: `0.2`
3. Confirm response parsing.
   - `extract_openrouter_response()` handles both standard `choices` and alternate `output` blocks
4. Confirm fallback behavior.
   - if OpenRouter fails, `local_ai_answer()` answers using board and question keywords
   - the backend returns fallback text instead of failing when possible

## 8. Verifying persistence across restarts

1. Start the entire app with Docker:
   - `docker compose up -d --build`
2. Open `http://localhost:8000`.
3. Make board changes in the browser.
4. Stop the app with `docker compose down`.
5. Restart it with `docker compose up -d`.
6. Confirm the board state remains unchanged.

This works because:
- the SQLite file lives in `backend/data/kanban.db`
- Docker mounts `./backend/data` into the container
- the backend reads and writes the same persisted database file

## 9. Commands executed during implementation

### Frontend build

```powershell
cd C:\Users\Himaja\pm\frontend
npm install
npm run build
```

### Backend syntax verification

```powershell
cd C:\Users\Himaja\pm
python -m py_compile backend/main.py
```

### Docker run

```powershell
cd C:\Users\Himaja\pm
docker compose up -d --build
docker compose down
```

### Helper script usage

```powershell
cd C:\Users\Himaja\pm\scripts
powershell -ExecutionPolicy Bypass -File .\start.ps1
powershell -ExecutionPolicy Bypass -File .\stop.ps1
```

## 10. Notes and improvements

- The backend is designed to support a default hardcoded user for the MVP.
- The frontend and backend are decoupled by API contracts.
- The Docker setup builds the frontend first and then copies the built static output into the Python container.
- Persistence is implemented using JSON stored in an SQLite text column.
- AI integration is built so the app continues working even if OpenRouter is unavailable.

---

## 11. Why this approach was chosen

- Multi-stage Docker build keeps the final image small and encapsulates both frontend and backend.
- SQLite persistence is simple and reliable for a local MVP.
- FastAPI provides fast, type-safe Python routes with Pydantic validation.
- Serving the built frontend from the backend makes the deployment self-contained.
- A fallback AI path ensures usability without requiring a fully operational external API.
