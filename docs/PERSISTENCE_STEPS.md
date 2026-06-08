# Persistence Fix and Implementation Steps

## Persistence status

The application now persists board state across restarts.

### What changed

1. The backend stores the Kanban board in SQLite at `backend/data/kanban.db`.
2. `docker-compose.yml` mounts `./backend/data` into the container at `/app/backend/data`.
3. The backend now only initializes the board with the default data the first time the database is empty.
   - This prevents the board from being reset on every startup.
4. The frontend saves board changes through `PUT /api/board`.
5. The backend reads board state through `GET /api/board`.

## Key files

- `backend/main.py`
  - `load_board()` reads persisted board data.
  - `save_board_data()` writes board changes.
  - `initialize_board()` now checks whether the board already exists before inserting default data.
- `docker-compose.yml`
  - Mounts `./backend/data:/app/backend/data` so the SQLite file is preserved across container restarts.
- `frontend/src/components/KanbanBoard.tsx`
  - Fetches board state from the backend on load.
  - Saves updates to the backend after user actions.

## How persistence works now

- On first startup, if no board exists for the default user, the backend creates the board in SQLite.
- On later startups, the backend loads the persisted board from `backend/data/kanban.db`.
- Client changes are saved immediately to the database.
- The Docker volume ensures the database file is not lost when the container is stopped or recreated.

## How to verify persistence

1. Start the app.
2. Change the board state in the browser (move cards, rename columns, add or delete cards).
3. Stop the app.
4. Restart the app.
5. Confirm the board state remains the same.

## Run commands

### Start

```powershell
cd C:\Users\Himaja\pm\scripts
powershell -ExecutionPolicy Bypass -File .\start.ps1
```

### Stop

```powershell
powershell -ExecutionPolicy Bypass -File .\stop.ps1
```

### Direct Docker commands

```bash
docker compose up -d --build
docker compose down
```

## Notes

- The persistence fix is now in `backend/main.py`.
- If you want, I can also add a small health-check endpoint that reports whether the SQLite database exists and is writable.
