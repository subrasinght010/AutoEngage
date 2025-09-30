from fastapi import WebSocket, WebSocketDisconnect
import json
import logging

logger = logging.getLogger(__name__)

class WebSocketConnectionManager:
    """Manages WebSocket connections for WebRTC signaling."""
    
    def __init__(self):
        self.active_connections = {}  # Stores WebSocket connections by user ID

    async def connect(self, websocket: WebSocket, user_id: str):
        """Accepts a WebSocket connection and stores it."""
        await websocket.accept()
        self.active_connections[user_id] = websocket
        logger.info(f"User {user_id} connected")

    async def disconnect(self, user_id: str):
        """Removes a WebSocket connection and notifies the frontend."""
        websocket = self.active_connections.pop(user_id, None)
        if websocket:
            try:
                await websocket.send_text(json.dumps({"type": "disconnect"}))  # Notify frontend
                await websocket.close()
                logger.info(f"User {user_id} forcefully disconnected")
            except Exception as e:
                logger.error(f"Error disconnecting user {user_id}: {e}")

    async def send_to(self, user_id: str, message: dict):
        """Sends a message to a specific user."""
        websocket = self.active_connections.get(user_id)
        if websocket:
            try:
                await websocket.send_text(json.dumps(message))
            except Exception as e:
                logger.error(f"Error sending message to {user_id}: {e}")

    async def broadcast(self, message: dict):
        """Sends a message to all active users."""
        disconnected_users = []
        for user_id, websocket in self.active_connections.items():
            try:
                await websocket.send_text(json.dumps(message))
            except Exception as e:
                logger.error(f"Error sending message to {user_id}: {e}")
                disconnected_users.append(user_id)

        # Remove disconnected users
        for user_id in disconnected_users:
            await self.disconnect(user_id)

ws_manager = WebSocketConnectionManager()

async def handle_websocket(websocket: WebSocket, user_id: str):
    """Handles WebRTC signaling messages over WebSocket."""
    await ws_manager.connect(websocket, user_id)
    try:
        while True:
            message = await websocket.receive_text()
            try:
                message_data = json.loads(message)
                message_type = message_data.get("type")

                if message_type not in {"offer", "answer", "ice-candidate", "disconnect"}:
                    logger.warning(f"Invalid message type received from {user_id}")
                    await websocket.send_text(json.dumps({"error": "Invalid message type"}))
                    continue

                if message_type == "disconnect":
                    await ws_manager.disconnect(user_id)
                    break  # Exit loop and close connection

                await webrtc_service.process_signaling_message(websocket, message_data)

            except json.JSONDecodeError:
                logger.warning(f"Invalid JSON received from {user_id}")
                await websocket.send_text(json.dumps({"error": "Invalid JSON format"}))

    except WebSocketDisconnect:
        logger.info(f"User {user_id} disconnected")
        await ws_manager.disconnect(user_id)

    except Exception as e:
        logger.error(f"Unexpected WebSocket error for {user_id}: {e}")
