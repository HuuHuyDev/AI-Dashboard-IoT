"""
Log Repository - Database access layer for query execution
"""
import logging
from typing import List, Dict, Any
from sqlalchemy import text
from sqlalchemy.orm import Session
import time

from app.core.config import settings

logger = logging.getLogger(__name__)


class LogRepository:
    """Repository for executing SQL queries"""
    
    def __init__(self, db: Session):
        self.db = db
    
    def execute_query(self, sql: str) -> tuple[List[Dict[str, Any]], float]:
        """
        Execute SQL query and return results
        
        Args:
            sql: SQL query to execute
            
        Returns:
            Tuple of (results list, execution time)
        """
        start_time = time.time()
        
        try:
            # Execute query with timeout
            result = self.db.execute(
                text(sql).execution_options(timeout=settings.QUERY_TIMEOUT)
            )
            
            # Convert results to list of dictionaries
            columns = result.keys()
            rows = result.fetchall()
            
            # Limit results
            if len(rows) > settings.MAX_QUERY_RESULTS:
                logger.warning(f"Query returned {len(rows)} rows, limiting to {settings.MAX_QUERY_RESULTS}")
                rows = rows[:settings.MAX_QUERY_RESULTS]
            
            data = [dict(zip(columns, row)) for row in rows]
            
            execution_time = time.time() - start_time
            logger.info(f"Query executed successfully: {len(data)} rows in {execution_time:.3f}s")
            
            return data, execution_time
            
        except Exception as e:
            logger.error(f"Query execution error: {str(e)}")
            raise Exception(f"Database query failed: {str(e)}")
