# Docker Runtime Deep Dive

This document explains in depth how the Kanban service is built and started using Docker and docker compose. It covers the `Dockerfile` multi-stage build, `docker-compose.yml` runtime, persistence and volumes, environment variables, healthchecks, common issues and debugging techniques, and practical developer workflows.

---

## 1. Goal

Make the full application startable and debuggable via Docker so that:
- the frontend is built and served as static files from the backend container
- the backend runs with `uvicorn` and exposes APIs on port `8000`
- the SQLite database file persists across container restarts
- environment variables (OpenRouter key) are provided securely
- the system is easy to rebuild and debug locally

---

## 2. Multi-stage `Dockerfile` explained

This repository uses a multi-stage build with two stages:

- Build stage (Node): installs and builds the Next.js frontend into static files (usually `out` directory).
- Runtime stage (Python): installs Python dependencies, copies backend, and copies built frontend artifacts into the final image.

Why multi-stage?
- Keeps final image small by excluding Node tooling and node_modules.
- Ensures the built frontend artifacts are reproducible inside the image.

Key points from the `Dockerfile`:

- Use an official Node image (e.g., `node:20-alpine`) for the build stage.
- Copy only the files required for building the frontend to leverage Docker cache.
- Run `npm install` then `npm run build` during the build stage.
- In the runtime stage, use a slim Python base (e.g., `python:3.12-slim`) and `pip install` the backend dependencies.
- Copy the built frontend (the `out` folder) from the build stage into the Python image.
- Set `CMD` to run `uvicorn main:app --host 0.0.0.0 --port 8000` in the backend working directory.

Example used in this repo (conceptually):

1. Build stage

```dockerfile
FROM node:20-alpine AS node-build
WORKDIR /app
COPY frontend/package.json ./package.json
COPY frontend/tsconfig.json ./tsconfig.json
COPY frontend/next.config.ts ./next.config.ts
COPY frontend/postcss.config.mjs ./postcss.config.mjs
COPY frontend/public ./public
COPY frontend/src ./src
RUN npm install
RUN npm run build
```

2. Runtime stage

```dockerfile
FROM python:3.12-slim
WORKDIR /app
COPY backend/requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt
COPY backend ./backend
COPY --from=node-build /app/out ./frontend/out
WORKDIR /app/backend
EXPOSE 8000
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
```

Notes:
- Keep COPY instructions as narrow as possible to improve build cache reuse.
- If you use environment variables to alter the build, cache won't be reused.

---

## 3. `docker-compose.yml` runtime behavior

The `docker-compose.yml` in this project defines a single service called `app` with:
- build context `.` (root)
- ports `8000:8000`
- a bind mount: `./backend/data:/app/backend/data`
- `env_file: .env`

Example snippet:

```yaml
version: "3.9"
services:
  app:
    build: .
    ports:
      - "8000:8000"
    volumes:
      - ./backend/data:/app/backend/data
    env_file:
      - .env
```

What this does at runtime:
- Builds the image (if not built or `--build` is passed).
- Runs the container and maps host port 8000 to container port 8000.
- Mounts the host folder `./backend/data` into the container path `/app/backend/data`.
  - This is the critical persistence mechanism: the SQLite file created by the backend will live on the host filesystem.
- Loads environment variables from `.env` into container's environment.

Important trade-offs:
- Bind mounts are simple and make the DB file visible on the host. On Windows, ensure path permissions are correct.
- For production, consider named volumes instead of bind mounts.

---

## 4. Startup sequence and what to expect

1. `docker compose up -d --build` will run the build stage then the runtime stage.
2. The Node build stage runs `npm install` and `npm run build` and emits a static `out` directory.
3. The Python image is built; dependencies installed via `pip`.
4. Container runs and `uvicorn` starts FastAPI app.
5. `@app.on_event("startup")` in `backend/main.py` runs `init_db()` and `initialize_board()` which:
   - create the DB folder and the `kanban.db` file inside the mounted `backend/data` (if missing)
   - seed the default board only if no persisted board exists
6. The app serves static files from the copied `frontend/out` folder.

Things to verify after `up`:
- `docker compose ps` shows the `app` service running.
- `docker compose logs -f` shows `uvicorn` started and the application is listening.
- `http://localhost:8000` serves the static frontend.
- `backend/data/kanban.db` exists on the host and gets updated when you make changes in the UI.

---

## 5. Persistence: SQLite, volumes, and file ownership

Persistence approach used:
- The SQLite DB file `kanban.db` is written to `/app/backend/data` inside the container.
- Docker bind mount maps this to `./backend/data` on the host.

Windows note:
- Docker Desktop on Windows handles mounts differently. Ensure that your project directory is shared with Docker (Docker Desktop settings -> Resources -> File Sharing or WSL integration).
- If you run into permission issues, check file ownership and adjust (for WSL, use the WSL distro shell to inspect files in `/mnt/c/...`).

Ownership/permission fixes:
- If the container can't write to the mounted directory, ensure the host folder is writable by your user and Docker.
- You can inspect the container user by running `docker compose exec app id` and adjust `chown` from inside the container if necessary.

Persistence verification commands:

```bash
# After app is running
ls -la backend/data
sqlite3 backend/data/kanban.db "SELECT name FROM sqlite_master WHERE type='table';"
```

---

## 6. Environment variables and secrets

This repo uses `.env` and `env_file` in `docker-compose.yml` to inject `OPENROUTER_API_KEY`.

Best practices:
- Never commit `.env` with secrets to source control.
- For local development, `.env` is fine.
- For production, use a secrets manager or docker-compose `secrets`.

Quick check to see environment inside running container:

```bash
docker compose exec app env | grep OPENROUTER
```

If the key is missing, the AI call will fall back to `local_ai_answer()`.

---

## 7. Healthchecks, restart policies, and compose enhancements

Add a `healthcheck` in `docker-compose.yml` to allow orchestrators and `docker compose ps` to know whether the service is healthy:

```yaml
services:
  app:
    build: .
    ports:
      - "8000:8000"
    volumes:
      - ./backend/data:/app/backend/data
    env_file:
      - .env
    healthcheck:
      test: ["CMD-SHELL", "curl -f http://localhost:8000/health || exit 1"]
      interval: 30s
      timeout: 10s
      retries: 3
    restart: unless-stopped
```

Restart policies:
- `restart: unless-stopped` will attempt to restart a crashed container but not if stopped manually.
- Alternative: `restart: on-failure` with a max retry limit.

---

## 8. Useful developer commands

Build & run:

```powershell
# from repo root
docker compose up -d --build
```

Recreate with no cache:

```bash
docker compose build --no-cache
docker compose up -d --force-recreate --no-deps app
```

Stop:

```bash
docker compose down
```

Follow logs:

```bash
docker compose logs -f
docker compose logs -f app
```

Get a shell inside the container (inspect files, run sqlite3, curl):

```bash
docker compose exec app sh
# or bash if available
```

Inspect the built frontend in the container:

```bash
docker compose exec app ls -la /app/frontend/out
```

Check the SQLite DB from host (requires sqlite3 installed):

```bash
sqlite3 backend/data/kanban.db "SELECT count(*) FROM boards;"
```

Check running containers and ports:

```bash
docker compose ps
docker compose port app 8000
```

Prune unused images and volumes (careful—destructive):

```bash
docker image prune -af
docker volume prune -f
```

---

## 9. Debugging common issues

Symptom: Frontend shows "Frontend build not found" JSON error
- Cause: The `out` directory was not copied into the runtime image or build failed in the Node stage.
- Fix:
  - Re-run `docker compose build` and watch Node build logs.
  - Confirm `/app/frontend/out` exists inside the container.

Symptom: DB file missing after restart
- Cause: Bind mount not working or path not shared with Docker Desktop.
- Fix:
  - Ensure `./backend/data` exists on host.
  - Check Docker Desktop file sharing settings (Windows) or WSL mount settings.
  - Run `docker compose exec app ls -la /app/backend/data` to inspect.

Symptom: App crashes on startup with Python errors
- Cause: missing dependencies, wrong Python version, syntax error.
- Fix:
  - Inspect logs with `docker compose logs -f` or `docker compose exec app tail -n 200 /path/to/log`.
  - Rebuild image after fixing code.

Symptom: OpenRouter calls failing (401/403 or network error)
- Cause: `OPENROUTER_API_KEY` missing, expired, or incorrect; network egress blocked.
- Fix:
  - Verify `.env` contains the key and `docker compose` loaded it.
  - In container: `docker compose exec app env | grep OPENROUTER`.
  - From container, run `curl -v https://openrouter.ai` to test connectivity (if allowed).

Symptom: Permission denied writing to `backend/data`
- Cause: host folder permissions or SELinux/AppArmor blocking writes.
- Fix:
  - Adjust folder permissions on the host: `chmod -R u+rwx backend/data` (Linux/macOS).
  - On Windows, ensure Docker Desktop shares the drive.

---

## 10. Advanced: speeding up builds and good practices

- Keep frontend copy steps focused: copy `package.json` and lockfile first, run `npm ci`, then copy source. This lets layer caching work when only source changes.
- Use `.dockerignore` to avoid copying node_modules, logs, and build artifacts into the image context.
- For large projects, split services into separate containers (frontend static server vs backend API) so you can iterate faster on frontend locally using `next dev`.
- Use named volumes for production data stability (e.g., `volumes: - kanban-data:/app/backend/data`), and bind mounts for local dev.

---

## 11. Example: adding a compose override for development

Create `docker-compose.override.yml` to mount the frontend source for live development (optional):

```yaml
services:
  app:
    volumes:
      - ./backend/data:/app/backend/data
      - ./frontend:/app/frontend-src:cached
    environment:
      - DEV_MODE=1
```

You could then modify the backend to serve frontend files from a different path in dev, or run `next dev` directly during development.

---

## 12. Checklist to bring the service up (copyable)

```bash
# ensure prerequisites installed: docker, docker compose, node (for local frontend builds)
cd C:\Users\Himaja\pm
# build and start the service
docker compose up -d --build
# watch logs
docker compose logs -f
# verify the API
curl http://localhost:8000/api/ping
curl http://localhost:8000/api/board
# make UI changes in a browser at http://localhost:8000
# stop
docker compose down
```


## Issues encountered and fixes (runtime & Docker)

- **Frontend build missing in runtime image**: the Node build stage failed during an early attempt and `frontend/out` was not present in the runtime image.
  - Fix: re-run the frontend build locally to reproduce the error (`npm run build`), fix build issues, and ensure `COPY --from=node-build /app/out ./frontend/out` is present in the `Dockerfile`.

- **DB persistence not surviving restarts initially**: caused by `initialize_board()` overwriting persisted data and/or the host mount not being set correctly.
  - Fix: updated `initialize_board()` to not overwrite existing rows, ensured `docker-compose.yml` bind-mount `./backend/data:/app/backend/data`, and verified `backend/data/kanban.db` exists on host.

- **Container couldn't write to mounted volume on Windows**: permissions or Docker Desktop file-sharing misconfiguration prevented writes.
  - Fix: documented Windows steps (enable file sharing/WSL integration), checked host folder permissions, and used `docker compose exec app id` to inspect container user.

- **Health & startup flakiness**: app occasionally took time to create DB and seed data, causing early health probes to show failures.
  - Fix: recommended adding a `healthcheck` to `docker-compose.yml` that retries and wait intervals, and using `restart: unless-stopped` for transient failures.

- **OpenRouter network/API errors inside container**: connectivity or missing env var caused AI calls to fail.
  - Fix: validated `.env` loaded by `docker-compose` and added defensive fallback `local_ai_answer()` to keep UI usable.

Verification commands used while fixing issues:

```bash
docker compose up -d --build
docker compose logs -f
docker compose exec app ls -la /app/frontend/out
docker compose exec app ls -la /app/backend/data
sqlite3 backend/data/kanban.db "SELECT count(*) FROM boards;"
docker compose exec app env | grep OPENROUTER || true
```

## 13. Next steps and suggestions

- Add `healthcheck` and `restart` policy in `docker-compose.yml` (example above).
- Consider adding a `Makefile` or `npm` script to wrap common compose commands.
- For more robust dev experience, split frontend into its own service and run `next dev` locally without rebuilding Docker for every change.

---

## 14. Where to look in this repo

- `Dockerfile` — multi-stage build
- `docker-compose.yml` — runtime configuration and bind mount for persistence
- `backend/main.py` — startup sequence, DB seeding, and static file serving
- `backend/data/` — persisted SQLite file (on the host when compose is used)

If you'd like, I can:
- add a `healthcheck` and `restart` policy to `docker-compose.yml` and commit it,
- add a `docker-compose.override.yml` to support a faster development loop,
- or add a `README` section with the copyable commands tailored to your Windows setup.

