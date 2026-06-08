# Build the frontend
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

# Build the Python backend image
FROM python:3.12-slim
WORKDIR /app

COPY backend/requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

COPY backend ./backend
COPY --from=node-build /app/out ./frontend/out

WORKDIR /app/backend
EXPOSE 8000
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
