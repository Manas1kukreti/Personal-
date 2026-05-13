import json
from collections import defaultdict

from fastapi import WebSocket


class WebSocketManager:
    def __init__(self) -> None:
        self.channels: dict[str, set[WebSocket]] = defaultdict(set)

    async def connect(self, websocket: WebSocket, channel: str) -> None:
        await websocket.accept()
        self.channels[channel].add(websocket)

    def disconnect(self, websocket: WebSocket, channel: str) -> None:
        self.channels[channel].discard(websocket)

    async def broadcast(self, channel: str, event: str, payload: dict) -> None:
        message = json.dumps({"event": event, "payload": payload}, default=str)
        stale: list[WebSocket] = []
        for websocket in self.channels[channel]:
            try:
                await websocket.send_text(message)
            except RuntimeError:
                stale.append(websocket)
        for websocket in stale:
            self.channels[channel].discard(websocket)


ws_manager = WebSocketManager()
