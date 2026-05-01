"""
Unit tests for Session Service
"""
import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch

from app.services.session_service import SessionService


@pytest.fixture
def mock_redis():
    """Mock Redis client"""
    redis = Mock()
    redis.hset = AsyncMock(return_value=1)
    redis.hgetall = AsyncMock(return_value={
        "user_id": "test_user",
        "created_at": "2024-01-01T00:00:00",
        "last_activity": "2024-01-01T00:00:00",
        "message_count": "0"
    })
    redis.expire = AsyncMock(return_value=True)
    redis.rpush = AsyncMock(return_value=1)
    redis.lrange = AsyncMock(return_value=[])
    redis.client = Mock()
    redis.client.delete = AsyncMock(return_value=1)
    return redis


@pytest.fixture
def session_service(mock_redis):
    """Session service with mocked Redis"""
    service = SessionService()
    service.redis = mock_redis
    return service


class TestSessionService:
    """Test session service"""
    
    @pytest.mark.asyncio
    async def test_create_session(self, session_service):
        """Test session creation"""
        session_id = await session_service.create_session("test_user")
        
        assert session_id is not None
        assert len(session_id) == 36  # UUID length
        session_service.redis.hset.assert_called_once()
        session_service.redis.expire.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_get_session(self, session_service):
        """Test getting session data"""
        session_data = await session_service.get_session("test_session_id")
        
        assert session_data is not None
        assert session_data["user_id"] == "test_user"
        session_service.redis.hgetall.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_add_message(self, session_service):
        """Test adding message to history"""
        message = {
            "role": "user",
            "content": "Test message",
            "timestamp": 1234567890
        }
        
        await session_service.add_message("test_session_id", message)
        
        session_service.redis.rpush.assert_called_once()
        session_service.redis.expire.assert_called()
    
    @pytest.mark.asyncio
    async def test_get_history(self, session_service):
        """Test getting conversation history"""
        history = await session_service.get_history("test_session_id", limit=10)
        
        assert isinstance(history, list)
        session_service.redis.lrange.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_clear_history(self, session_service):
        """Test clearing session history"""
        await session_service.clear_history("test_session_id")
        
        session_service.redis.client.delete.assert_called_once()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
