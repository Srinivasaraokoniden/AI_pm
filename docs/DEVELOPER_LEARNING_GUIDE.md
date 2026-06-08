# Developer Learning Guide

This guide is a step-by-step learning path for the Kanban MVP project in this repository. It is organized by technology, with commands, file-level explanations, and exercises to help you understand the full stack.

---

## 1. Project overview

This project is a full-stack Kanban board application.

Stack:
- Frontend: `Next.js` + `React` + `TypeScript`
- Backend: `FastAPI` + Python + `SQLite`
- Deployment: `Docker` + `docker compose`
- AI integration: `OpenRouter` via `httpx`
- Configuration: `.env`

What it does:
- loads a Kanban board in the browser
- saves board state to a backend API
- persists state in SQLite
- serves the built frontend from the backend container
- allows simple AI chat using board state

---

## 2. Repository structure

Root files:
- `Dockerfile` — builds the frontend and backend containers
- `docker-compose.yml` — runs the application locally with Docker
- `scripts/start.ps1` — starts the app on Windows
- `scripts/stop.ps1` — stops the app on Windows
- `docs/` — documentation and project guidance

Important folders:
- `frontend/` — Next.js application and UI components
- `backend/` — FastAPI server, SQLite persistence, AI integration
- `backend/data/` — persisted SQLite database file

---

## 3. Setup and run commands

### 3.1 Install prerequisites

Install on Windows:
- Docker Desktop
- Node.js 20+
- Python 3.12+
- Git

### 3.2 Run with Docker

From the repo root:

```powershell
cd C:\Users\Himaja\pm
docker compose up -d --build
```

Open the app in a browser:

```text
http://localhost:8000
```

Stop the app:

```powershell
docker compose down
```

### 3.3 Use the helper scripts

Start:

```powershell
cd C:\Users\Himaja\pm\scripts
powershell -ExecutionPolicy Bypass -File .\start.ps1
```

Stop:

```powershell
powershell -ExecutionPolicy Bypass -File .\stop.ps1
```

### 3.4 Verify APIs

```powershell
curl http://localhost:8000/api/ping
curl http://localhost:8000/api/board
curl -X POST http://localhost:8000/api/ai -H "Content-Type: application/json" -d '{"question":"What is in Review?"}'
```

---

## 4. Frontend learning path

### 4.1 Key files to study

- `frontend/package.json`
- `frontend/tsconfig.json`
- `frontend/src/app/page.tsx`
- `frontend/src/components/KanbanBoard.tsx`
- `frontend/src/components/KanbanCard.tsx`
- `frontend/src/components/KanbanColumn.tsx`
- `frontend/src/components/NewCardForm.tsx`

### 4.2 What to learn first

1. `package.json`: understand dependencies and scripts.
2. `page.tsx`: learn how the Next.js page loads the app.
3. `KanbanBoard.tsx`: see how board data is fetched from the backend and rendered.
4. `KanbanColumn.tsx` + `KanbanCard.tsx`: learn component composition.
5. `@dnd-kit`: learn how drag and drop works in React.

### 4.3 Frontend commands

```powershell
cd C:\Users\Himaja\pm\frontend
npm install
npm run dev
npm run build
npm run test
```

### 4.4 Exercises

1. Open `KanbanBoard.tsx` and find where `GET /api/board` is called.
2. Change one card title in the UI and observe the network request.
3. Add a new console log in `KanbanColumn.tsx` to print each column title.
4. Inspect the drag-and-drop logic and identify where `onDragEnd` updates state.
5. Run `npm run test` and read any test output.

---

## 5. Backend learning path

### 5.1 Key files to study

- `backend/main.py`
- `backend/requirements.txt`
- `backend/data/` (for the SQLite file)

### 5.2 What to learn first

1. `main.py`: this is the backend application entry point.
2. `FastAPI` decorators: `@app.get`, `@app.put`, `@app.post`.
3. `Pydantic` models: `BoardData`, `Column`, `Card`, `ChatRequest`, `AIResponse`.
4. SQLite persistence: functions `init_db()`, `load_board()`, `save_board_data()`.
5. Static file serving: `app.mount('/', StaticFiles(...))`.

### 5.3 Backend commands

```powershell
cd C:\Users\Himaja\pm\backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python -m uvicorn main:app --reload --host 0.0.0.0 --port 8000
python -m py_compile main.py
```

### 5.4 Exercises

1. Find `initialize_board()` and explain why it only inserts a board once.
2. Modify `local_ai_answer()` to add a new fallback case for the phrase "what cards are due".
3. Add a new route `GET /api/health` and test it in Postman or curl.
4. Open `requirements.txt` and learn why each package is needed.
5. Run `python -m py_compile backend/main.py` to confirm syntax.

---

## 6. Database and persistence learning path

### 6.1 Data model

- Table: `boards`
- Columns:
  - `user` — primary key
  - `data` — JSON text of the Kanban board
  - `updated_at` — timestamp string

### 6.2 Important functions

- `init_db()`: creates the table if missing.
- `load_board()`: loads the row for the default user.
- `save_board_data()`: saves board JSON using `INSERT OR REPLACE`.
- `initialize_board()`: only seeds the default board when no row exists.

### 6.3 Exercises

1. Open the SQLite file in a browser tool or CLI and inspect stored JSON.
2. Stop and restart the container, then verify the file still exists.
3. Add a `SELECT updated_at FROM boards` debug print in the backend.
4. Write a small Python script that queries `backend/data/kanban.db` directly.
5. Change the default board in `INITIAL_BOARD` and restart the app to see how seeding behaves.

---

## 7. Docker learning path

### 7.1 Key files

- `Dockerfile`
- `docker-compose.yml`
- `scripts/start.ps1`
- `scripts/stop.ps1`

### 7.2 What to learn first

1. Multi-stage build in `Dockerfile`.
2. Build stage: Node container builds the Next.js frontend.
3. Runtime stage: Python container installs backend dependencies.
4. Volume mount in `docker-compose.yml` for `backend/data`.
5. How `uvicorn` starts the backend.

### 7.3 Commands

```powershell
cd C:\Users\Himaja\pm
docker compose build
docker compose up -d
docker compose ps
docker compose logs -f
docker compose down
```

### 7.4 Exercises

1. Run `docker compose up -d --build` and watch the build logs.
2. Inspect the running container with `docker compose ps`.
3. Enter the backend container filesystem with `docker compose exec app sh`.
4. Check that `frontend/out` exists inside the container.
5. Remove the `backend/data` folder, restart the app, and observe how the board resets.

---

## 8. AI integration learning path

### 8.1 Key files

- `backend/main.py`
- `.env`

### 8.2 What to learn first

1. How the backend reads `OPENROUTER_API_KEY` from `.env`.
2. The `query_openrouter()` request payload and model configuration.
3. How the backend parses the external response with `extract_openrouter_response()`.
4. Fallback logic in `local_ai_answer()`.
5. The frontend call to `POST /api/ai`.

### 8.3 Exercises

1. Inspect the environment variable usage in `main.py`.
2. Add a new prompt field in the OpenRouter payload and test a different assistant tone.
3. Simulate an AI failure by unsetting the API key and confirming fallback behavior.
4. Log the AI response shape when `result.json()` is returned.
5. Extend the AI endpoint to include the `updated_at` timestamp in the response.

---

## 9. Practical learning exercises

### Exercise 1: End-to-end feature change

1. Add a new button to the UI to add a card with a fixed title.
2. Update the frontend to send the new board state via `PUT /api/board`.
3. Confirm the backend saves it in SQLite.
4. Refresh the page and verify the card remains.

### Exercise 2: Add a health check page

1. Add `GET /api/health` in `backend/main.py`.
2. Add a simple `/health` fetch in the frontend.
3. Display the health status in the app footer.

### Exercise 3: Improve AI fallback

1. Change `local_ai_answer()` to answer "what card is in progress" more clearly.
2. Test without `OPENROUTER_API_KEY` and confirm fallback is returned.
3. Add a new frontend message when AI is using fallback.

### Exercise 4: Learn by reading

1. Read `docs/PLAN.md` to understand how the project was intended to grow.
2. Compare the project code to the plan and identify which steps are complete.
3. Write a short note in `docs/` describing one backend route and one frontend component.

---

## 10. How to extend this app next

If you want to continue learning, here are useful next steps:

- Add user authentication instead of a hardcoded `user`.
- Support multiple boards per user.
- Make AI updates apply changes to cards automatically.
- Add tests for the backend and frontend.
- Add logging and error monitoring.

---

## 11. Notes

This guide is intended to help you learn the exact technologies used in this project by reading the code, running the app, and making small changes. Use the commands in each section as a checklist, and follow the exercises to build confidence.
