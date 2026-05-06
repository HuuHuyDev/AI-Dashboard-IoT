"""
Chatbot Service - Business Logic
Orchestrates LLM service and Query service with MCP agentic SQL generation
"""
import logging
import time
import httpx
from typing import Optional, List

from app.models.schemas import ChatResponse
from app.services.llm_service import LLMService
from app.core.config import settings

logger = logging.getLogger(__name__)


class ChatbotService:
    """Chatbot service for processing natural language queries via MCP+LLM"""

    def __init__(self):
        self.llm_service = LLMService()
        self.query_service_url = settings.QUERY_SERVICE_URL

    async def process_query(
        self,
        prompt: str,
        session_id: Optional[str] = None,
        conversation_history: Optional[List[dict]] = None,
    ) -> ChatResponse:
        """
        Process user query through the MCP agentic loop and return results.

        Args:
            prompt:               User's natural language query
            session_id:           Optional session ID for logging
            conversation_history: Previous messages for multi-turn context

        Returns:
            ChatResponse with SQL, data, chart config, and explanation
        """
        start = time.time()
        try:
            # Step 1: MCP agentic loop → generates and validates SQL
            logger.info(f"[ChatbotService] Processing prompt (session={session_id}): {prompt[:80]}")
            sql_response = await self.llm_service.generate_sql(
                prompt=prompt,
                conversation_history=conversation_history,
            )

            if not sql_response.sql:
                return ChatResponse(
                    message=(
                        "I couldn't generate a valid SQL query from your request. "
                        "Please try rephrasing."
                    ),
                    sql=None,
                    data=None,
                    chart=None,
                )

            logger.info(f"[ChatbotService] SQL generated: {sql_response.sql[:120]}")

            # Step 2: Use data from MCP tool if available, otherwise query Query Service
            if sql_response.data is not None:
                # Data already fetched by execute_sql_query MCP tool
                logger.info(f"[ChatbotService] Using data from MCP tool: {sql_response.row_count} rows")
                query_result = {
                    "data": sql_response.data,
                    "row_count": sql_response.row_count or len(sql_response.data),
                    "source": sql_response.source or "database",
                    "cached": sql_response.cached or False,
                }
            else:
                # Fallback: query Query Service (for cases where execute_sql_query wasn't called)
                logger.info("[ChatbotService] No data from MCP tool, querying Query Service")
                query_result = await self._execute_query(sql_response.sql)

            # Step 3: build human-readable message
            message = self._build_message(query_result)

            execution_time = time.time() - start
            logger.info(
                f"[ChatbotService] Completed in {execution_time:.2f}s, "
                f"rows={query_result.get('row_count', 0)}, source={query_result.get('source')}"
            )

            return ChatResponse(
                message        = message,
                sql            = sql_response.sql,
                data           = query_result.get("data", []),
                chart          = sql_response.chart,
                source         = query_result.get("source", "database"),
                explanation    = sql_response.explanation,
                execution_time = execution_time,
            )

        except Exception as exc:
            logger.error(f"[ChatbotService] Error: {exc}", exc_info=True)
            return ChatResponse(
                message=f"I encountered an error processing your request: {exc}",
                sql    = None,
                data   = None,
                chart  = None,
            )

    # ── private helpers ────────────────────────────────────────────────────

    async def _execute_query(self, sql: str) -> dict:
        """Forward SQL to Query Service (handles Redis cache + security)."""
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                resp = await client.post(
                    f"{self.query_service_url}/api/v1/query/execute",
                    json={"sql": sql},
                )
                resp.raise_for_status()
                return resp.json()

        except httpx.TimeoutException:
            logger.error("[ChatbotService] Query Service timeout")
            raise Exception("Query execution timed out. Please try a simpler query.")
        except httpx.HTTPStatusError as exc:
            logger.error(f"[ChatbotService] Query Service HTTP {exc.response.status_code}")
            raise Exception(f"Query execution failed: {exc.response.text}")
        except Exception as exc:
            logger.error(f"[ChatbotService] _execute_query error: {exc}")
            raise Exception(f"Failed to execute query: {exc}")

    @staticmethod
    def _build_message(query_result: dict) -> str:
        """Build a short human-readable summary of the query outcome."""
        data   = query_result.get("data", [])
        source = query_result.get("source", "database")

        if not data:
            return "No data found matching your query."

        source_label = "from cache" if source == "cache" else "from database"
        return f"Found {len(data)} result(s) {source_label}. The data is displayed below."
