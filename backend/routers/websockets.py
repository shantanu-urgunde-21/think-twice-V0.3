from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from typing import List, Dict
import json

router = APIRouter(prefix="/api", tags=["WebSockets"])

class ConnectionManager:
    def __init__(self):
        # game_id -> list of websockets
        self.game_connections: Dict[int, List[WebSocket]] = {}
        # list of websockets for general lobby (index.html)
        self.lobby_connections: List[WebSocket] = []

    async def connect_lobby(self, websocket: WebSocket):
        await websocket.accept()
        self.lobby_connections.append(websocket)

    def disconnect_lobby(self, websocket: WebSocket):
        if websocket in self.lobby_connections:
            self.lobby_connections.remove(websocket)

    async def broadcast_lobby(self, message: dict):
        for connection in list(self.lobby_connections):
            try:
                await connection.send_text(json.dumps(message))
            except Exception:
                self.disconnect_lobby(connection)

    async def connect_game(self, game_id: int, websocket: WebSocket):
        await websocket.accept()
        if game_id not in self.game_connections:
            self.game_connections[game_id] = []
        self.game_connections[game_id].append(websocket)

    def disconnect_game(self, game_id: int, websocket: WebSocket):
        if game_id in self.game_connections:
            if websocket in self.game_connections[game_id]:
                self.game_connections[game_id].remove(websocket)
            if not self.game_connections[game_id]:
                del self.game_connections[game_id]

    async def broadcast_game(self, game_id: int, message: dict):
        if game_id in self.game_connections:
            for connection in list(self.game_connections[game_id]):
                try:
                    await connection.send_text(json.dumps(message))
                except Exception:
                    self.disconnect_game(game_id, connection)

manager = ConnectionManager()

@router.websocket("/ws/lobby")
async def websocket_lobby(websocket: WebSocket):
    await manager.connect_lobby(websocket)
    try:
        while True:
            # Keep connection alive
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect_lobby(websocket)

@router.websocket("/ws/game/{game_id}")
async def websocket_game(game_id: int, websocket: WebSocket):
    await manager.connect_game(game_id, websocket)
    try:
        while True:
            # Keep connection alive
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect_game(game_id, websocket)
