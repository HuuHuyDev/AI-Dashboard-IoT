"""
Query Controller - API Endpoints
"""
from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
import logging

from app.models.schemas import QueryRequest, QueryResponse, ErrorResponse
from app.services.query_service import QueryService
from app.core.database import get_db

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/execute", response_model=QueryResponse)
async def execute_query(
    request: QueryRequest,
    db: Session = Depends(get_db)
) -> QueryResponse:
    """
    Execute SQL query with caching
    
    Args:
        request: Query request with SQL
        db: Database session
        
    Returns:
        QueryResponse with results
    """
    try:
        logger.info(f"Executing query: {request.sql[:100]}...")
        
        # Create service instance
        query_service = QueryService(db)
        
        # Execute query
        result = await query_service.execute_query(
            sql=request.sql,
            use_cache=request.use_cache
        )
        
        return QueryResponse(**result)
        
    except ValueError as e:
        logger.error(f"Validation error: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Query execution error: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Query execution failed: {str(e)}")


@router.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "service": "query-controller"}
