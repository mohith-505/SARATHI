"""SARATHI Daemon (FastAPI)."""

from __future__ import annotations

import asyncio
from pathlib import Path

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from apps.daemon.rpc import RPCConnection
from core.config.settings import SarathiSettings
from core.logging.logger import get_logger
from core.storage.sqlite import SQLiteStore

log = get_logger("daemon.main")

app = FastAPI(
    title="SARATHI Daemon",
    description="Backend for SARATHI Personal AI Companion",
    version="0.2.0",
)

# Restrict CORS to localhost origins
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:8000",
        "http://127.0.0.1:8000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

DB_PATH = Path("data/sarathi.db")
store = SQLiteStore(DB_PATH)


@app.on_event("startup")
async def startup_event():
    log.info("Starting SARATHI Daemon on 127.0.0.1...")
    await store.connect()


@app.on_event("shutdown")
async def shutdown_event():
    log.info("Shutting down SARATHI Daemon...")
    await store.close()


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "ok", "version": "0.2.0", "host": "127.0.0.1"}


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket connection for JSON-RPC 2.0."""
    await websocket.accept()
    log.info("New WebSocket connection accepted.")

    settings = SarathiSettings.load(Path("config/default.toml"))
    rpc = RPCConnection(websocket, store, settings)

    try:
        while True:
            data = await websocket.receive_text()
            asyncio.create_task(rpc.handle_message(data))
    except WebSocketDisconnect:
        log.info("WebSocket disconnected.")
    except Exception as e:
        log.error("WebSocket error: %s", e)


# Serve static HUD if frontend has been built
FRONTEND_DIST = Path("frontend/dist")
if FRONTEND_DIST.exists():
    app.mount("/", StaticFiles(directory=str(FRONTEND_DIST), html=True), name="frontend")
