"""
Chatbot Controller - API Endpoints
"""
from fastapi import APIRouter, HTTPException, Depends
from typing import Dict, Any
import logging
import time

from app.models.schemas import ChatRequest, ChatResponse, ErrorResponse
from app.services.chatbot_service import ChatbotService
from app.services.session_service import SessionService
from app.services.sql_validator import sql_validator

logger = logging.getLogger(__name__)

router = APIRouter()


def get_chatbot_service() -> ChatbotService:
    """Dependency injection for chatbot service"""
    return ChatbotService()


def get_session_service() -> SessionService:
    """Dependency injection for session service"""
    return SessionService()


@router.post("/chat", response_model=ChatResponse)
async def chat(
    request: ChatRequest,
    chatbot_service: ChatbotService = Depends(get_chatbot_service),
    session_service: SessionService = Depends(get_session_service)
) -> ChatResponse:
    """
    Process natural language query and return results
    
    Args:
        request: Chat request with user prompt
        chatbot_service: Injected chatbot service
        session_service: Injected session service
        
    Returns:
        ChatResponse with SQL, data, and chart configuration
    """
    start_time = time.time()
    
    try:
        logger.info(f"Processing chat request: {request.prompt[:100]}...")
        
        # Create or validate session
        session_id = request.session_id
        if not session_id:
            session_id = await session_service.create_session()
            logger.info(f"Created new session: {session_id}")
        else:
            # Update session activity
            await session_service.update_activity(session_id)
        
        # Fetch conversation history for multi-turn context
        history = await session_service.get_history(session_id, limit=6)

        # Process the chat request (MCP agentic loop)
        response = await chatbot_service.process_query(
            prompt=request.prompt,
            session_id=session_id,
            conversation_history=history,
        )
        
        # Store message in history
        await session_service.add_message(session_id, {
            "role": "user",
            "content": request.prompt,
            "timestamp": time.time()
        })
        
        await session_service.add_message(session_id, {
            "role": "assistant",
            "content": response.explanation,
            "sql": response.sql,
            "timestamp": time.time()
        })
        
        execution_time = time.time() - start_time
        response.execution_time = execution_time
        response.session_id = session_id
        
        logger.info(f"Chat request processed successfully in {execution_time:.2f}s")
        return response
        
    except ValueError as e:
        logger.error(f"Validation error: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error processing chat request: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@router.get("/session/{session_id}/history")
async def get_session_history(
    session_id: str,
    limit: int = 10,
    session_service: SessionService = Depends(get_session_service)
) -> Dict[str, Any]:
    """
    Get conversation history for a session
    
    Args:
        session_id: Session ID
        limit: Maximum number of messages to return
        session_service: Injected session service
        
    Returns:
        Conversation history
    """
    try:
        history = await session_service.get_history(session_id, limit)
        session_data = await session_service.get_session(session_id)
        
        return {
            "session_id": session_id,
            "session_data": session_data,
            "history": history,
            "message_count": len(history)
        }
        
    except Exception as e:
        logger.error(f"Error getting session history: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/session/{session_id}")
async def clear_session(
    session_id: str,
    session_service: SessionService = Depends(get_session_service)
) -> Dict[str, str]:
    """
    Clear session history
    
    Args:
        session_id: Session ID
        session_service: Injected session service
        
    Returns:
        Success message
    """
    try:
        await session_service.clear_history(session_id)
        return {"message": f"Session {session_id} cleared successfully"}
        
    except Exception as e:
        logger.error(f"Error clearing session: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/health")
async def health_check() -> Dict[str, str]:
    """Health check endpoint"""
    return {"status": "healthy", "service": "chatbot-controller"}


@router.get("/validation-rules")
async def get_validation_rules() -> Dict[str, Any]:
    """
    Get SQL validation rules and security policies
    
    Returns:
        Dictionary containing validation rules
    """
    try:
        rules = sql_validator.get_validation_summary()
        return {
            "status": "success",
            "validation_rules": rules,
            "description": "SQL security validation rules for chatbot queries"
        }
    except Exception as e:
        logger.error(f"Error getting validation rules: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
