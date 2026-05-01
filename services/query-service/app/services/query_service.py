"""
Query Service - Business Logic
Handles SQL validation, caching, and execution on read models (CQRS)
"""
import logging
import hashlib
import json
from typing import Dict, Any, List
from sqlalchemy.orm import Session
from sqlalchemy import text
import time

from app.core.redis_client import redis_client
from app.core.config import settings

logger = logging.getLogger(__name__)


class QueryService:
    """Service for query execution with caching on read models"""
    
    def __init__(self, db: Session):
        self.db = db
    
    async def execute_query(self, sql: str, use_cache: bool = True) -> Dict[str, Any]:
        """
        Execute SQL query with caching on read models
        
        Args:
            sql: SQL query to execute
            use_cache: Whether to use cache
            
        Returns:
            Query results with metadata
        """
        # Generate cache key
        cache_key = self._generate_cache_key(sql)
        
        # Try to get from cache
        if use_cache:
            cached_result = await self._get_from_cache(cache_key)
            if cached_result:
                logger.info("Returning cached result")
                return {
                    "data": cached_result,
                    "row_count": len(cached_result),
                    "source": "cache",
                    "cached": True
                }
        
        # Execute query on read models
        logger.info("Executing query on read models")
        data, execution_time = self._execute_query_on_read_models(sql)
        
        # Cache the result
        if use_cache and data:
            await self._set_cache(cache_key, data)
        
        return {
            "data": data,
            "row_count": len(data),
            "source": "database",
            "execution_time": execution_time,
            "cached": False
        }
    
    def _execute_query_on_read_models(self, sql: str) -> tuple[List[Dict[str, Any]], float]:
        """
        Execute SQL query on read models
        
        Args:
            sql: SQL query
            
        Returns:
            Tuple of (data, execution_time)
        """
        start_time = time.time()
        
        try:
            # Execute query
            result = self.db.execute(text(sql))
            
            # Convert to list of dicts
            columns = result.keys()
            data = [dict(zip(columns, row)) for row in result.fetchall()]
            
            execution_time = time.time() - start_time
            
            logger.info(f"Query executed in {execution_time:.3f}s, returned {len(data)} rows")
            
            return data, execution_time
            
        except Exception as e:
            logger.error(f"Query execution error: {e}")
            raise
    
    def _generate_cache_key(self, sql: str) -> str:
        """
        Generate cache key from SQL query
        
        Args:
            sql: SQL query
            
        Returns:
            Cache key (hash)
        """
        # Normalize SQL (remove extra whitespace, convert to lowercase)
        normalized_sql = " ".join(sql.lower().split())
        
        # Generate hash
        hash_object = hashlib.sha256(normalized_sql.encode())
        cache_key = f"query:{hash_object.hexdigest()}"
        
        return cache_key
    
    async def _get_from_cache(self, cache_key: str) -> Any:
        """
        Get query result from cache
        
        Args:
            cache_key: Cache key
            
        Returns:
            Cached data or None
        """
        try:
            cached_value = await redis_client.get(cache_key)
            if cached_value:
                return json.loads(cached_value)
        except Exception as e:
            logger.error(f"Cache retrieval error: {e}")
        return None
    
    async def _set_cache(self, cache_key: str, data: Any) -> bool:
        """
        Set query result in cache
        
        Args:
            cache_key: Cache key
            data: Data to cache
            
        Returns:
            Success status
        """
        try:
            json_data = json.dumps(data, default=str)
            return await redis_client.set(cache_key, json_data, ttl=settings.CACHE_TTL)
        except Exception as e:
            logger.error(f"Cache storage error: {e}")
            return False
