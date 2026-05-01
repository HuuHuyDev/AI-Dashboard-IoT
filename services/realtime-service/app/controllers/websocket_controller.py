"""
WebSocket Controller - WebSocket endpoint
"""
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
import logging
import asyncio

from app.services.connection_manager import connection_manager

logger = logging.getLogger(__name__)

router = APIRouter()


@router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """
    WebSocket endpoint for real-time data streaming
    
    Args:
        websocket: WebSocket connection
    """
    # Accept connection
    connected = await connection_manager.connect(websocket)
    if not connected:
        await websocket.close(code=1008, reason="Max connections reached")
        return
    
    try:
        # Send welcome message
        await connection_manager.send_personal(websocket, {
            "type": "connection",
            "message": "Connected to IoT Dashboard real-time service",
            "connections": connection_manager.get_connection_count()
        })
        
        # Start heartbeat
        heartbeat_task = asyncio.create_task(connection_manager.heartbeat(websocket))
        
        # Keep connection alive and handle incoming messages
        while True:
            try:
                # Receive message from client (for potential commands)
                data = await websocket.receive_text()
                logger.debug(f"Received from client: {data}")
                
                # Echo back or handle command
                await connection_manager.send_personal(websocket, {
                    "type": "echo",
                    "message": f"Received: {data}"
                })
            except WebSocketDisconnect:
                logger.info("Client disconnected normally")
                break
            except Exception as e:
                logger.error(f"Error in WebSocket loop: {e}")
                break
    
    finally:
        # Cleanup
        heartbeat_task.cancel()
        connection_manager.disconnect(websocket)


@router.get("/connections")
async def get_connections():
    """Get number of active WebSocket connections"""
    return {
        "active_connections": connection_manager.get_connection_count(),
        "max_connections": connection_manager.max_connections
    }
