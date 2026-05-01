"""
Connection Manager - Manages WebSocket connections
"""
import logging
import json
from typing import Dict
from datetime import datetime
from fastapi import WebSocket

from app.core.redis_client import redis_client
from app.core.config import settings

logger = logging.getLogger(__name__)


class ConnectionManager:
    """Manages WebSocket connections and subscriptions"""
    
    def __init__(self):
        self.active_connections: Dict[str, WebSocket] = {}
    
    async def connect(self, websocket: WebSocket, connection_id: str, user_id: str = "anonymous"):
        """
        Accept WebSocket connection and store in Redis
        
        Args:
            websocket: WebSocket connection
            connection_id: Unique connection ID
            user_id: User identifier
        """
        await websocket.accept()
        self.active_connections[connection_id] = websocket
        
        # Store in Redis
        await redis_client.hset(
            f"active_connections:{connection_id}",
            mapping={
                "user_id": user_id,
                "connected_at": datetime.utcnow().isoformat(),
                "subscriptions": json.dumps([])
            }
        )
        
        logger.info(f"Connection {connection_id} established for user {user_id}")
    
    async def disconnect(self, connection_id: str):
        """
        Disconnect WebSocket and cleanup Redis
        
        Args:
            connection_id: Connection ID
        """
        if connection_id in self.active_connections:
            del self.active_connections[connection_id]
        
        # Get subscriptions before cleanup
        conn_data = await redis_client.hgetall(f"active_connections:{connection_id}")
        if conn_data:
            subscriptions = json.loads(conn_data.get("subscriptions", "[]"))
            
            # Remove from device subscriptions
            for device_id in subscriptions:
                await redis_client.srem(f"device_subscriptions:{device_id}", connection_id)
        
        logger.info(f"Connection {connection_id} disconnected")
    
    async def subscribe(self, connection_id: str, device_id: str):
        """
        Subscribe connection to device events
        
        Args:
            connection_id: Connection ID
            device_id: Device ID to subscribe to
        """
        # Add to device subscriptions
        await redis_client.sadd(f"device_subscriptions:{device_id}", connection_id)
        
        # Update connection subscriptions
        conn_data = await redis_client.hgetall(f"active_connections:{connection_id}")
        subscriptions = json.loads(conn_data.get("subscriptions", "[]"))
        
        if device_id not in subscriptions:
            subscriptions.append(device_id)
            await redis_client.hset(
                f"active_connections:{connection_id}",
                mapping={"subscriptions": json.dumps(subscriptions)}
            )
        
        logger.info(f"Connection {connection_id} subscribed to device {device_id}")
    
    async def unsubscribe(self, connection_id: str, device_id: str):
        """
        Unsubscribe connection from device events
        
        Args:
            connection_id: Connection ID
            device_id: Device ID to unsubscribe from
        """
        # Remove from device subscriptions
        await redis_client.srem(f"device_subscriptions:{device_id}", connection_id)
        
        # Update connection subscriptions
        conn_data = await redis_client.hgetall(f"active_connections:{connection_id}")
        subscriptions = json.loads(conn_data.get("subscriptions", "[]"))
        
        if device_id in subscriptions:
            subscriptions.remove(device_id)
            await redis_client.hset(
                f"active_connections:{connection_id}",
                mapping={"subscriptions": json.dumps(subscriptions)}
            )
        
        logger.info(f"Connection {connection_id} unsubscribed from device {device_id}")
    
    async def broadcast_to_device(self, device_id: str, message: dict):
        """
        Broadcast message to all connections subscribed to device
        
        Args:
            device_id: Device ID
            message: Message to broadcast
        """
        # Get all connections subscribed to this device
        connection_ids = await redis_client.smembers(f"device_subscriptions:{device_id}")
        
        sent_count = 0
        for conn_id in connection_ids:
            if conn_id in self.active_connections:
                try:
                    await self.active_connections[conn_id].send_json(message)
                    sent_count += 1
                except Exception as e:
                    logger.error(f"Error sending to connection {conn_id}: {e}")
                    await self.disconnect(conn_id)
        
        logger.debug(f"Broadcasted to {sent_count} connections for device {device_id}")
    
    async def send_personal_message(self, connection_id: str, message: dict):
        """
        Send message to specific connection
        
        Args:
            connection_id: Connection ID
            message: Message to send
        """
        if connection_id in self.active_connections:
            try:
                await self.active_connections[connection_id].send_json(message)
            except Exception as e:
                logger.error(f"Error sending personal message: {e}")
                await self.disconnect(connection_id)
    
    def get_connection_count(self) -> int:
        """Get number of active connections"""
        return len(self.active_connections)


connection_manager = ConnectionManager()
