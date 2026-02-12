"""
websocket.py — WebSocket Connection Manager with Backpressure Handling

Each client has a 'ready' flag. If a client hasn't finished receiving
the previous frame, we skip it for this broadcast cycle.
This prevents queue buildup on slow clients without blocking fast ones.
"""
import asyncio
import logging
import time
from typing import List, Dict
from fastapi import WebSocket

logger = logging.getLogger(__name__)


class ClientState:
    """Per-client connection state."""
    __slots__ = ('ws', 'ready', 'last_send_time', 'frames_sent', 'frames_dropped')

    def __init__(self, ws: WebSocket):
        self.ws = ws
        self.ready = True
        self.last_send_time = 0.0
        self.frames_sent = 0
        self.frames_dropped = 0


class ConnectionManager:
    def __init__(self):
        self.clients: Dict[int, ClientState] = {}

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        cid = id(websocket)
        self.clients[cid] = ClientState(websocket)
        logger.info(f"Client {cid} connected. Total: {len(self.clients)}")

    def disconnect(self, websocket: WebSocket):
        cid = id(websocket)
        client = self.clients.pop(cid, None)
        if client:
            dropped_pct = 0
            if client.frames_sent + client.frames_dropped > 0:
                dropped_pct = client.frames_dropped / (client.frames_sent + client.frames_dropped) * 100
            logger.info(
                f"Client {cid} disconnected. "
                f"Sent={client.frames_sent}, Dropped={client.frames_dropped} ({dropped_pct:.0f}%). "
                f"Remaining: {len(self.clients)}"
            )

    @property
    def active_connections(self):
        """Compatibility property."""
        return [c.ws for c in self.clients.values()]

    async def broadcast(self, message: dict):
        """Broadcast with per-client backpressure. Slow clients get frames dropped."""
        if not self.clients:
            return

        tasks = []
        for cid, client in list(self.clients.items()):
            if client.ready:
                tasks.append(self._send_with_backpressure(cid, client, message))
            else:
                client.frames_dropped += 1

        if tasks:
            await asyncio.gather(*tasks)

    async def _send_with_backpressure(self, cid: int, client: ClientState, message: dict):
        """Send to a single client with backpressure tracking."""
        client.ready = False
        try:
            await client.ws.send_json(message)
            client.frames_sent += 1
            client.last_send_time = time.time()
        except Exception:
            # Client is dead — will be cleaned up by endpoint handler
            pass
        finally:
            client.ready = True


manager = ConnectionManager()
