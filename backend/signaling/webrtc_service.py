import json
from fastapi.websockets import WebSocket

class WebRTCSessionManager:
    """Manages WebRTC sessions between peers."""
    
    def __init__(self):
        self.sessions = {}  # Stores {peer_id: websocket}

    async def add_peer(self, peer_id: str, websocket: WebSocket):
        """Adds a new peer to the session."""
        self.sessions[peer_id] = websocket

    async def remove_peer(self, peer_id: str):
        """Removes a peer from the session."""
        if peer_id in self.sessions:
            del self.sessions[peer_id]

    async def send_message(self, peer_id: str, message: dict):
        """Sends a message to a specific peer."""
        if peer_id in self.sessions:
            await self.sessions[peer_id].send_text(json.dumps(message))

    async def process_signaling_message(self, websocket: WebSocket, message: dict):
        """Handles WebRTC signaling messages (offer, answer, ICE candidates)."""
        msg_type = message.get("type")
        peer_id = message.get("peer_id")  # Unique ID for the peer

        if msg_type == "register":
            await self.add_peer(peer_id, websocket)
            print(f"Peer {peer_id} registered.")

        elif msg_type in ["offer", "answer", "ice-candidate"]:
            target_peer = message.get("target_peer")
            if target_peer in self.sessions:
                await self.send_message(target_peer, message)
            else:
                print(f"Target peer {target_peer} not found.")

        elif msg_type == "disconnect":
            await self.remove_peer(peer_id)
            print(f"Peer {peer_id} disconnected.")

# Initialize WebRTC session manager
webrtc_service = WebRTCSessionManager()
