from __future__ import annotations

import json
import os
import sqlite3
from datetime import datetime
from pathlib import Path

import httpx
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

ROOT_DIR = Path(__file__).resolve().parent
BUILD_DIR = ROOT_DIR.parent / "frontend" / "out"
DATA_DIR = ROOT_DIR / "data"
DB_PATH = DATA_DIR / "kanban.db"
DEFAULT_USER = "user"

load_dotenv(ROOT_DIR.parent / ".env")

OPENROUTER_API_KEY = os.environ.get("OPENROUTER_API_KEY")
OPENROUTER_MODEL = "openai/gpt-oss-120b"
OPENROUTER_URL = "https://openrouter.ai/v1/chat/completions"

app = FastAPI(title="Kanban MVP Backend")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


class Column(BaseModel):
    id: str
    title: str
    cardIds: list[str]


class Card(BaseModel):
    id: str
    title: str
    details: str


class BoardData(BaseModel):
    columns: list[Column]
    cards: dict[str, Card]


class ChatRequest(BaseModel):
    question: str


class AIResponse(BaseModel):
    response: str


INITIAL_BOARD = {
    "columns": [
        {"id": "col-backlog", "title": "Backlog", "cardIds": ["card-1", "card-2"]},
        {"id": "col-discovery", "title": "Discovery", "cardIds": ["card-3"]},
        {"id": "col-progress", "title": "In Progress", "cardIds": ["card-4", "card-5"]},
        {"id": "col-review", "title": "Review", "cardIds": ["card-6"]},
        {"id": "col-done", "title": "Done", "cardIds": ["card-7", "card-8"]},
    ],
    "cards": {
        "card-1": {
            "id": "card-1",
            "title": "Align roadmap themes",
            "details": "Draft quarterly themes with impact statements and metrics.",
        },
        "card-2": {
            "id": "card-2",
            "title": "Gather customer signals",
            "details": "Review support tags, sales notes, and churn feedback.",
        },
        "card-3": {
            "id": "card-3",
            "title": "Prototype analytics view",
            "details": "Sketch initial dashboard layout and key drill-downs.",
        },
        "card-4": {
            "id": "card-4",
            "title": "Refine status language",
            "details": "Standardize column labels and tone across the board.",
        },
        "card-5": {
            "id": "card-5",
            "title": "Design card layout",
            "details": "Add hierarchy and spacing for scanning dense lists.",
        },
        "card-6": {
            "id": "card-6",
            "title": "QA micro-interactions",
            "details": "Verify hover, focus, and loading states.",
        },
        "card-7": {
            "id": "card-7",
            "title": "Ship marketing page",
            "details": "Final copy approved and asset pack delivered.",
        },
        "card-8": {
            "id": "card-8",
            "title": "Close onboarding sprint",
            "details": "Document release notes and share internally.",
        },
    },
}


def init_db() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute(
            "CREATE TABLE IF NOT EXISTS boards (user TEXT PRIMARY KEY, data TEXT NOT NULL, updated_at TEXT NOT NULL)"
        )
        conn.commit()


def load_board(user: str = DEFAULT_USER) -> dict:
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.execute("SELECT data FROM boards WHERE user = ?", (user,))
        row = cursor.fetchone()
        if row is None:
            return initialize_board(user)
        return json.loads(row[0])


def initialize_board(user: str = DEFAULT_USER) -> dict:
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.execute("SELECT data FROM boards WHERE user = ?", (user,))
        row = cursor.fetchone()
        if row is not None:
            return json.loads(row[0])

        board_json = json.dumps(INITIAL_BOARD)
        updated_at = datetime.utcnow().isoformat() + "Z"
        conn.execute(
            "INSERT INTO boards (user, data, updated_at) VALUES (?, ?, ?)",
            (user, board_json, updated_at),
        )
        conn.commit()
    return INITIAL_BOARD.copy()


def save_board_data(board: dict, user: str = DEFAULT_USER) -> None:
    board_json = json.dumps(board)
    updated_at = datetime.utcnow().isoformat() + "Z"
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute(
            "INSERT OR REPLACE INTO boards (user, data, updated_at) VALUES (?, ?, ?)",
            (user, board_json, updated_at),
        )
        conn.commit()


def extract_openrouter_response(result: dict) -> str:
    if not isinstance(result, dict):
        raise ValueError("Invalid OpenRouter response")

    # Standard chat/completions structure
    if "choices" in result and isinstance(result["choices"], list):
        first = result["choices"][0]
        if isinstance(first, dict) and "message" in first and isinstance(first["message"], dict):
            return first["message"].get("content", "").strip()

    # Alternate structure: `output` array with content blocks
    if "output" in result and isinstance(result["output"], list) and result["output"]:
        first_output = result["output"][0]
        if isinstance(first_output, dict) and "content" in first_output:
            content = first_output["content"]
            if isinstance(content, list) and content:
                return str(content[0].get("text", "")).strip()
            return str(content).strip()

    raise ValueError("Unable to parse OpenRouter response")


def local_ai_answer(question: str, board: dict, fallback_reason: str | None = None) -> str:
    # Very small local fallback to answer basic card/column queries when external AI is unavailable
    question_lower = question.lower()
    cards = board.get("cards", {})
    columns = board.get("columns", [])

    def card_detail(card_id: str) -> str:
        card = cards.get(card_id)
        if not card:
            return ""
        return f"{card['title']}: {card['details']}"

    # If user mentions a card id or title, return its details
    for card in cards.values():
        if card["id"].lower() in question_lower or card["title"].lower() in question_lower:
            return f"{card['title']} - {card['details']}"

    # If user asks about a column, list card titles in that column
    for column in columns:
        if column["title"].lower() in question_lower or column["id"].lower() in question_lower:
            if len(column["cardIds"]) == 0:
                return f"The {column['title']} column is currently empty."
            details = " ".join(card_detail(card_id) for card_id in column["cardIds"])
            return f"{column['title']} contains {len(column['cardIds'])} cards: {details}"

    # If user asks for a summary
    if any(term in question_lower for term in ["summary", "overview", "status", "what is", "what are"]):
        summary = []
        for column in columns:
            summary.append(f"{column['title']} ({len(column['cardIds'])})")
        board_summary = ", ".join(summary)
        return f"Board summary: {board_summary}."

    # Otherwise, provide a simple fallback listing
    fallback = []
    for column in columns:
        if column["cardIds"]:
            fallback.append(f"{column['title']}: {', '.join(cards[c]['title'] for c in column['cardIds'])}")
    fallback_text = " | ".join(fallback)
    prefix = "AI fallback: " if fallback_reason else ""
    return f"{prefix}I couldn't reach the external AI service. Here is the current board state: {fallback_text}"


def query_openrouter(question: str, board: dict) -> str:
    if not OPENROUTER_API_KEY:
        raise RuntimeError("OPENROUTER_API_KEY is not configured")

    payload = {
        "model": OPENROUTER_MODEL,
        "messages": [
            {
                "role": "system",
                "content": (
                    "You are a helpful project management assistant. "
                    "Use the current Kanban board state to answer questions about cards, columns, and project status. "
                    "If the question asks about a specific card, include the card title and details."
                ),
            },
            {
                "role": "user",
                "content": (
                    f"Here is the current board state:\n{json.dumps(board, indent=2)}\n\nQuestion: {question}"
                ),
            },
        ],
        "temperature": 0.2,
    }

    with httpx.Client(timeout=30.0) as client:
        response = client.post(
            OPENROUTER_URL,
            headers={
                "Authorization": f"Bearer {OPENROUTER_API_KEY}",
                "Content-Type": "application/json",
            },
            json=payload,
        )
        response.raise_for_status()
        result = response.json()

    return extract_openrouter_response(result)


@app.on_event("startup")
def on_startup() -> None:
    init_db()
    initialize_board()


@app.get("/api/ping")
def ping() -> JSONResponse:
    return JSONResponse({"status": "ok", "time": datetime.utcnow().isoformat() + "Z"})


@app.get("/api/board", response_model=BoardData)
def get_board() -> BoardData:
    try:
        raw_board = load_board()
        return BoardData(**raw_board)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@app.put("/api/board")
def update_board(board: BoardData) -> JSONResponse:
    try:
        save_board_data(board.dict())
        return JSONResponse({"status": "ok"})
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@app.post("/api/ai", response_model=AIResponse)
def ask_ai(request: ChatRequest) -> AIResponse:
    board = load_board()
    try:
        answer = query_openrouter(request.question, board)
        return AIResponse(response=answer)
    except Exception as exc:
        # Log and return a local fallback so the UI remains usable
        try:
            fallback = local_ai_answer(request.question, board, fallback_reason=str(exc))
            return AIResponse(response=fallback)
        except Exception:
            raise HTTPException(status_code=500, detail="AI service unavailable and fallback failed")


@app.get("/health")
def health() -> JSONResponse:
    return JSONResponse({"status": "ok"})


if BUILD_DIR.exists():
    app.mount("/", StaticFiles(directory=str(BUILD_DIR), html=True), name="frontend")
else:
    @app.get("/")
    def root() -> JSONResponse:
        return JSONResponse(
            {"status": "error", "message": "Frontend build not found. Please build the frontend before starting the app."}
        )
