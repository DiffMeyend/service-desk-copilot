"""FastAPI application for QF_Wiz Web API."""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from dotenv import load_dotenv
from fastapi import Depends, FastAPI, HTTPException, Request, WebSocket, WebSocketDisconnect

load_dotenv()  # loads .env into os.environ so ANTHROPIC_API_KEY is available
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

logger = logging.getLogger(__name__)

from api.config import settings
from api.routers import agent_router, branch_packs_router, commands_router, intake_router, tickets_router
from api.services.runtime_service import runtime_service
from api.websocket import ws_manager


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Startup and shutdown events."""
    # Startup: Initialize runtime loader
    if not runtime_service.initialize():
        print("[qf-wiz-api] WARNING: Failed to load some runtime files:")
        for error in runtime_service.errors:
            print(f"  - {error}")
    else:
        print("[qf-wiz-api] Runtime files loaded successfully")

    yield

    # Shutdown: cleanup if needed
    print("[qf-wiz-api] Shutting down")


app = FastAPI(
    title="QF_Wiz API",
    description="REST API for QF_Wiz troubleshooting orchestration",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS middleware for web UI
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# API key authentication dependency
async def verify_api_key(request: Request) -> None:
    """Verify API key if configured."""
    if not settings.api_key:
        return  # No API key configured, allow all requests

    api_key = request.headers.get("X-API-Key")
    if api_key != settings.api_key:
        raise HTTPException(status_code=401, detail="Unauthorized")


# Include routers
app.include_router(tickets_router, dependencies=[Depends(verify_api_key)])
app.include_router(commands_router, dependencies=[Depends(verify_api_key)])
app.include_router(branch_packs_router, dependencies=[Depends(verify_api_key)])
app.include_router(intake_router, dependencies=[Depends(verify_api_key)])
app.include_router(agent_router, dependencies=[Depends(verify_api_key)])


@app.get("/")
async def root() -> dict:
    """Root endpoint - API info."""
    return {
        "name": "QF_Wiz API",
        "version": "1.0.0",
        "docs": "/docs",
    }


@app.get("/health")
async def health() -> dict:
    """Health check endpoint."""
    return {
        "status": "ok",
        "runtime_loaded": runtime_service.is_loaded,
        "errors": runtime_service.errors if not runtime_service.is_loaded else [],
    }


@app.websocket("/api/v1/tickets/{ticket_id}/stream")
async def ticket_stream(websocket: WebSocket, ticket_id: str) -> None:
    """WebSocket endpoint for real-time ticket updates."""
    # Optional: verify API key for WebSocket
    # api_key = websocket.headers.get("X-API-Key")
    # if settings.api_key and api_key != settings.api_key:
    #     await websocket.close(code=4001)
    #     return

    # Verify API key for WebSocket if configured
    api_key = websocket.headers.get("X-API-Key")
    if settings.api_key and api_key != settings.api_key:
        await websocket.close(code=4001)
        return

    await ws_manager.connect(websocket, ticket_id)

    try:
        while True:
            # Wait for messages from client (heartbeat, etc.)
            data = await websocket.receive_text()

            # Echo back for now (could handle client commands later)
            await websocket.send_text(f"received: {data}")

    except WebSocketDisconnect:
        ws_manager.disconnect(websocket, ticket_id)


# Exception handlers
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Global exception handler."""
    logger.error("Unhandled exception on %s %s: %s", request.method, request.url.path, exc, exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"error": "Internal server error"},
    )


def main() -> None:
    """Run the server using uvicorn."""
    import uvicorn

    print(f"[qf-wiz-api] Starting server on http://{settings.host}:{settings.port}")
    uvicorn.run(
        "api.main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug,
    )


if __name__ == "__main__":
    main()
