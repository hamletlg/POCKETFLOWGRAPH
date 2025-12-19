"""
ENHANCED VERSION of backend/websockets.py with better error handling and logging
Replace the entire websockets.py file with this version
"""

from fastapi import WebSocket
from typing import List
import logging

logger = logging.getLogger(__name__)

class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []
        logger.info("ConnectionManager initialized")

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)
        logger.info(f"WebSocket connected. Total connections: {len(self.active_connections)}")

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
            logger.info(f"WebSocket disconnected. Total connections: {len(self.active_connections)}")
        else:
            logger.warning("Attempted to disconnect WebSocket that wasn't in active connections")

    async def broadcast(self, message: str):
        logger.info(f"Broadcasting message to {len(self.active_connections)} connections: {message}")
        
        dead_connections = []
        successful_sends = 0
        
        for i, connection in enumerate(self.active_connections):
            try:
                await connection.send_text(message)
                successful_sends += 1
                logger.debug(f"Successfully sent to connection {i}")
            except Exception as e:
                logger.error(f"Failed to send to connection {i}: {e}")
                dead_connections.append(connection)
        
        # Remove dead connections
        for dead_conn in dead_connections:
            self.disconnect(dead_conn)
            
        logger.info(f"Broadcast completed: {successful_sends} successful, {len(dead_connections)} failed")
        
        if successful_sends == 0:
            logger.warning("No active WebSocket connections to receive broadcast")
                
manager = ConnectionManager()
