# Project Run Instructions

This document explains what was implemented and how to run the application from the beginning to the browser.

## 1. What was built

- A Python FastAPI backend in `backend/main.py`.
- A Next.js frontend in `frontend/` with the Kanban board UI.
- A SQLite database for board persistence in `backend/data/kanban.db`.
- AI chat support via OpenRouter using the model `openai/gpt-oss-120b`.
- Docker support to build and run the full application in a container.
- Start and stop scripts for Windows and macOS/Linux.

## 2. Key project files

- `backend/main.py` - FastAPI app, database logic, board API routes, AI route.
- `backend/requirements.txt` - Python dependencies.
- `frontend/next.config.ts` - Next.js export configuration.
- `frontend/src/components/KanbanBoard.tsx` - Kanban board component with backend persistence.
- `frontend/src/components/ChatSidebar.tsx` - AI chat sidebar component.
- `.env` - contains `OPENROUTER_API_KEY` for AI connectivity.
- `Dockerfile` - builds the frontend and backend into one container.
- `docker-compose.yml` - starts the container and exposes port 8000.
- `scripts/start.ps1` / `scripts/stop.ps1` - Windows start/stop scripts.
- `scripts/start.sh` / `scripts/stop.sh` - macOS/Linux start/stop scripts.

## 3. How the application works

1. The frontend is built with Next.js and configured for static export.
2. The backend serves the exported frontend files from `frontend/out`.
3. The backend also exposes REST APIs:
   - `GET /api/ping` - health check endpoint.
   - `GET /api/board` - returns the current board state.
   - `PUT /api/board` - saves board updates.
   - `POST /api/ai` - sends board state and the user question to OpenRouter.
4. The hosted frontend reads board data from `/api/board` and saves updates there.
5. The chat sidebar sends user questions to `/api/ai` and displays the AI response.
6. Board state is persisted in SQLite and survives container restarts.

## 4. Prerequisites

- Docker installed and running.
- Node.js installed for local frontend build if needed.
- PowerShell for Windows scripts.
- The `.env` file in the project root with a valid `OPENROUTER_API_KEY`.

## 5. Running the application with Docker (recommended)

### Windows

1. Open PowerShell.
2. Navigate to the scripts folder:

```powershell
cd C:\Users\Himaja\pm\scripts
```

3. Start the application:

```powershell
powershell -ExecutionPolicy Bypass -File .\start.ps1
```

4. Open your browser and go to:

```text
http://localhost:8000
```

### macOS / Linux

1. Open a terminal.
2. Navigate to the scripts folder:

```bash
cd /path/to/pm/scripts
```

3. Start the application:

```bash
./start.sh
```

4. Open your browser and go to:

```text
http://localhost:8000
```

## 6. Stopping the application

### Windows

```powershell
powershell -ExecutionPolicy Bypass -File .\stop.ps1
```

### macOS / Linux

```bash
./stop.sh
```

## 7. Troubleshooting

- If PowerShell blocks script execution, use `powershell -ExecutionPolicy Bypass -File .\start.ps1`.
- If the AI chat does not work, verify `OPENROUTER_API_KEY` is present in `.env`.
- If the frontend does not appear, make sure Docker built the app successfully and the container is running.
- Check logs with Docker commands if needed:

```powershell
docker compose logs --follow
```

## 8. Additional notes

- The backend automatically initializes the board in SQLite on first startup.
- The AI uses `openai/gpt-oss-120b` via OpenRouter and the current board data.
- The chat sidebar is designed for questions about cards and board details.
- The application is available on `http://localhost:8000` once the container starts.
