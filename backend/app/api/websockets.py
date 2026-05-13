from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app.services.websocket_manager import ws_manager

router = APIRouter(tags=["websockets"])


@router.websocket("/ws/{channel}")
async def websocket_channel(websocket: WebSocket, channel: str) -> None:
    await ws_manager.connect(websocket, channel)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        ws_manager.disconnect(websocket, channel)
