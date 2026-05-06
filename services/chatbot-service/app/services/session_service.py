"""
Session Service - Manages chat sessions and conversation history
"""
import logging
import json
import uuid
from datetime import datetime
from typing import Optional, List, Dict, Any

from app.core.redis_client import redis_client
from app.core.config import settings

logger = logging.getLogger(__name__)


class SessionService:
    """Service for managing chat sessions in Redis"""
    
    def __init__(self):
        self.redis = redis_client
        self.session_ttl = settings.SESSION_TTL
    
    async def create_session(self, user_id: str = "default") -> str:
        """
        Create a new chat session
        
        Args:
            user_id: User identifier
            
        Returns:
            Session ID
        """
        try:
            session_id = str(uuid.uuid4())
            
            # Store session metadata
            await self.redis.hset(
                f"chat_sessions:{session_id}",
                mapping={
                    "user_id": user_id,
                    "created_at": datetime.utcnow().isoformat(),
                    "last_activity": datetime.utcnow().isoformat(),
                    "message_count": "0"
                }
            )
            
            # Set expiration
            await self.redis.expire(f"chat_sessions:{session_id}", self.session_ttl)
            
            logger.info(f"Created session: {session_id}")
            return session_id
            
        except Exception as e:
            logger.error(f"Error creating session: {e}")
            raise
    
    async def get_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        """
        Get session metadata
        
        Args:
            session_id: Session ID
            
        Returns:
            Session metadata or None
        """
        try:
            session_data = await self.redis.hgetall(f"chat_sessions:{session_id}")
            
            if not session_data:
                return None
            
            return session_data
            
        except Exception as e:
            logger.error(f"Error getting session: {e}")
            return None
    
    async def update_activity(self, session_id: str):
        """
        Update session last activity timestamp
        
        Args:
            session_id: Session ID
        """
        try:
            await self.redis.hset(
                f"chat_sessions:{session_id}",
                mapping={
                    "last_activity": datetime.utcnow().isoformat()
                }
            )
            
            # Refresh expiration
            await self.redis.expire(f"chat_sessions:{session_id}", self.session_ttl)
            
        except Exception as e:
            logger.error(f"Error updating activity: {e}")
    
    async def add_message(self, session_id: str, message: Dict[str, Any]):
        """
        Add message to conversation history
        
        Args:
            session_id: Session ID
            message: Message data
        """
        try:
            # Add to history list
            await self.redis.rpush(
                f"chat_history:{session_id}",
                json.dumps(message)
            )
            
            # Set expiration
            await self.redis.expire(f"chat_history:{session_id}", self.session_ttl)
            
            # Increment message count
            session_data = await self.redis.hgetall(f"chat_sessions:{session_id}")
            message_count = int(session_data.get("message_count", 0)) + 1
            
            await self.redis.hset(
                f"chat_sessions:{session_id}",
                mapping={"message_count": str(message_count)}
            )
            
            logger.debug(f"Added message to session {session_id}")
            
        except Exception as e:
            logger.error(f"Error adding message: {e}")
    
    async def get_history(self, session_id: str, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Get conversation history
        
        Args:
            session_id: Session ID
            limit: Maximum number of messages to return
            
        Returns:
            List of messages
        """
        try:
            # Get last N messages
            messages = await self.redis.lrange(
                f"chat_history:{session_id}",
                -limit,
                -1
            )
            
            return [json.loads(msg) for msg in messages]
            
        except Exception as e:
            logger.error(f"Error getting history: {e}")
            return []
    
    async def clear_history(self, session_id: str):
        """
        Clear conversation history
        
        Args:
            session_id: Session ID
        """
        try:
            await self.redis.delete(f"chat_history:{session_id}")
            logger.info(f"Cleared history for session {session_id}")
            
        except Exception as e:
            logger.error(f"Error clearing history: {e}")
