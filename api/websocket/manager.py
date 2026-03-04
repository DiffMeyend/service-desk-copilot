"""WebSocket connection manager for real-time updates."""

from __future__ import annotations

import json
from typing import Any, Dict, List

from fastapi import WebSocket


class WebSocketManager:
    """Manages WebSocket connections per ticket."""

    def __init__(self):
        # Map ticket_id -> list of connected WebSockets
        self._connections: Dict[str, List[WebSocket]] = {}

    async def connect(self, websocket: WebSocket, ticket_id: str) -> None:
        """Accept a WebSocket connection for a ticket."""
        await websocket.accept()

        if ticket_id not in self._connections:
            self._connections[ticket_id] = []

        self._connections[ticket_id].append(websocket)

    def disconnect(self, websocket: WebSocket, ticket_id: str) -> None:
        """Remove a WebSocket connection."""
        if ticket_id in self._connections:
            try:
                self._connections[ticket_id].remove(websocket)
            except ValueError:
                pass

            # Clean up empty lists
            if not self._connections[ticket_id]:
                del self._connections[ticket_id]

    async def broadcast(self, ticket_id: str, message: Dict[str, Any]) -> None:
        """Broadcast a message to all connections for a ticket."""
        if ticket_id not in self._connections:
            return

        json_message = json.dumps(message)
        dead_connections = []

        for websocket in self._connections[ticket_id]:
            try:
                await websocket.send_text(json_message)
            except Exception:
                # Connection is dead
                dead_connections.append(websocket)

        # Clean up dead connections
        for ws in dead_connections:
            self.disconnect(ws, ticket_id)

    async def send_cp_update(self, ticket_id: str, cp: Dict[str, Any]) -> None:
        """Send a CP update to all connections for a ticket."""
        await self.broadcast(
            ticket_id,
            {
                "type": "cp_update",
                "payload": cp,
            },
        )

    async def send_css_update(
        self, ticket_id: str, score: int, blockers: List[str]
    ) -> None:
        """Send a CSS score update."""
        await self.broadcast(
            ticket_id,
            {
                "type": "css_recalculated",
                "payload": {
                    "score": score,
                    "blockers": blockers,
                },
            },
        )

    async def send_hypothesis_collapsed(
        self, ticket_id: str, hypothesis_id: str, reason: str
    ) -> None:
        """Notify that a hypothesis was collapsed."""
        await self.broadcast(
            ticket_id,
            {
                "type": "hypothesis_collapsed",
                "payload": {
                    "id": hypothesis_id,
                    "reason": reason,
                },
            },
        )

    async def send_decision_ready(self, ticket_id: str, status: str) -> None:
        """Notify that a decision has been made or is ready."""
        await self.broadcast(
            ticket_id,
            {
                "type": "decision_ready",
                "payload": {
                    "status": status,
                },
            },
        )

    def get_connection_count(self, ticket_id: str) -> int:
        """Get number of active connections for a ticket."""
        return len(self._connections.get(ticket_id, []))


# Global singleton instance
ws_manager = WebSocketManager()
