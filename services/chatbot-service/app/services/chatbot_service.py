"""
Chatbot Service - Business Logic
Orchestrates LLM service and Query service
"""
import logging
import httpx
from typing import Optional

from app.models.schemas import ChatResponse, ChartConfig
from app.services.llm_service import LLMService
from app.core.config import settings

logger = logging.getLogger(__name__)


class ChatbotService:
    """Chatbot service for processing natural language queries"""
    
    def __init__(self):
        self.llm_service = LLMService()
        self.query_service_url = settings.QUERY_SERVICE_URL
    
    async def process_query(self, prompt: str, session_id: Optional[str] = None) -> ChatResponse:
        """
        Process user query through LLM and execute SQL
        
        Args:
            prompt: User's natural language query
            session_id: Optional session ID for context
            
        Returns:
            ChatResponse with results
        """
        try:
            # Step 1: Generate SQL and chart config using LLM
            logger.info("Generating SQL from prompt...")
            sql_response = await self.llm_service.generate_sql(prompt)
            
            if not sql_response.sql:
                return ChatResponse(
                    message="I couldn't generate a valid SQL query from your request. Please try rephrasing.",
                    sql=None,
                    data=None,
                    chart=None
                )
            
            logger.info(f"Generated SQL: {sql_response.sql}")
            
            # Step 2: Execute SQL through Query Service
            logger.info("Executing SQL query...")
            query_result = await self._execute_query(sql_response.sql)
            
            # Step 3: Build response
            message = self._build_response_message(prompt, query_result)
            
            return ChatResponse(
                message=message,
                sql=sql_response.sql,
                data=query_result.get("data", []),
                chart=sql_response.chart,
                source=query_result.get("source", "database"),
                explanation=sql_response.explanation
            )
            
        except Exception as e:
            logger.error(f"Error processing query: {str(e)}", exc_info=True)
            return ChatResponse(
                message=f"I encountered an error processing your request: {str(e)}",
                sql=None,
                data=None,
                chart=None
            )
    
    async def _execute_query(self, sql: str) -> dict:
        """
        Execute SQL query through Query Service
        
        Args:
            sql: SQL query to execute
            
        Returns:
            Query results
        """
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    f"{self.query_service_url}/api/v1/query/execute",
                    json={"sql": sql}
                )
                response.raise_for_status()
                return response.json()
                
        except httpx.TimeoutException:
            logger.error("Query service timeout")
            raise Exception("Query execution timed out. Please try a simpler query.")
        except httpx.HTTPStatusError as e:
            logger.error(f"Query service HTTP error: {e.response.status_code}")
            raise Exception(f"Query execution failed: {e.response.text}")
        except Exception as e:
            logger.error(f"Error executing query: {str(e)}")
            raise Exception(f"Failed to execute query: {str(e)}")
    
    def _build_response_message(self, prompt: str, query_result: dict) -> str:
        """
        Build human-readable response message
        
        Args:
            prompt: Original user prompt
            query_result: Query execution results
            
        Returns:
            Response message
        """
        data = query_result.get("data", [])
        source = query_result.get("source", "database")
        
        if not data:
            return "No data found matching your query."
        
        row_count = len(data)
        source_text = "from cache" if source == "cache" else "from database"
        
        return f"Found {row_count} result(s) {source_text}. The data is displayed below."
