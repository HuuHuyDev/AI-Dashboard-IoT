"""
LLM Service – Google Gemini + MCP Agentic SQL Generation
=========================================================
Replaces the old static Function Calling with a full multi-turn
agentic loop powered by the MCP server:

  1. Gemini receives the user prompt + system instructions
  2. Gemini calls MCP tools (list_tables, get_table_schema, get_device_list,
     get_data_range, get_sample_data, execute_sql_query, explain_sql_query)
     to gather REAL information from the database
  3. When satisfied, Gemini calls finalize_response(sql, chart_type, …)
  4. We cache the result in Redis and return a SQLResponse

This ensures the generated SQL uses EXACT column / table names,
real device IDs, and the correct date range – no more hallucinations.
"""

import hashlib
import json
import logging
from typing import Optional

import google.generativeai as genai

from app.core.config import settings
from app.core.redis_client import redis_client
from app.mcp.server import mcp_server
from app.mcp.gemini_bridge import GeminiBridge
from app.models.schemas import ChartConfig, SQLResponse
from app.services.sql_validator import sql_validator

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# System prompt
# ---------------------------------------------------------------------------
SYSTEM_PROMPT = """\
You are an expert SQL analyst for an IoT monitoring dashboard backed by PostgreSQL.

You have access to MCP tools that let you interact with the REAL database:
  • list_tables()             – see all available tables
  • get_table_schema(table)   – get EXACT column names and types
  • get_device_list(...)      – list real device IDs and types
  • get_data_range(table,col) – find min/max of any column (time range!)
  • get_sample_data(table)    – preview real rows
  • execute_sql_query(sql)    – run a SELECT and get real results
  • explain_sql_query(sql)    – check query efficiency (optional)

MANDATORY WORKFLOW – follow this EVERY time:
  Step 1  → call get_table_schema() for EACH table you plan to query
  Step 2  → call get_data_range('logs', 'timestamp') for time-based questions
  Step 3  → call get_device_list() if the question mentions devices/sensors
  Step 4  → write the SQL using EXACT column names you discovered
  Step 5  → call execute_sql_query(sql) to verify results
  Step 6  → call finalize_response(sql, explanation, chart_type, …)

SQL rules:
  • PostgreSQL syntax only
  • SELECT statements only – never INSERT / UPDATE / DELETE / DROP
  • Always add LIMIT (default 1000, smaller for aggregations)
  • Use NOW() and INTERVAL for relative time: WHERE timestamp > NOW() - INTERVAL '24 hours'
  • Use DATE_TRUNC for grouping by time bucket
  • Prefer JOINs over sub-selects where possible

Chart type selection:
  • line   → time-series trends
  • bar    → comparisons between devices / categories
  • pie    → proportions / share
  • scatter → correlations between two metrics
  • table  → raw records or mixed data
"""


class LLMService:
    """
    LLM service using Google Gemini + MCP agentic loop to generate SQL queries.
    """

    def __init__(self):
        genai.configure(api_key=settings.GEMINI_API_KEY)

        # Gemini bridge wraps the FastMCP server
        self.bridge = GeminiBridge(mcp_server)

        # Generation config
        gen_cfg = genai.GenerationConfig(
            temperature      = settings.GEMINI_TEMPERATURE,
            max_output_tokens = settings.GEMINI_MAX_TOKENS,
        )

        # Model with all MCP tools advertised
        self.model = genai.GenerativeModel(
            model_name         = settings.GEMINI_MODEL,
            generation_config  = gen_cfg,
            tools              = self.bridge.get_gemini_tools(),
        )

        logger.info(
            f"LLMService ready – model={settings.GEMINI_MODEL}, "
            f"tools={self.bridge.registered_tool_names}"
        )

    # -----------------------------------------------------------------------

    async def generate_sql(
        self,
        prompt: str,
        conversation_history: Optional[list] = None,
    ) -> SQLResponse:
        """
        Generate a validated SQL query from a natural-language prompt.

        Process
        -------
        1. Sanitise input
        2. Check Redis cache (cache key = MD5 of sanitised prompt)
        3. Run Gemini agentic loop via GeminiBridge
        4. Validate SQL with SQLValidator
        5. Cache result
        6. Return SQLResponse

        Args:
            prompt:               User's natural-language question
            conversation_history: Optional previous messages for context

        Returns:
            SQLResponse with sql, chart, explanation fields
        """
        # ── 1. Sanitise ────────────────────────────────────────────────────
        sanitised = sql_validator.sanitize_input(prompt)
        logger.info(f"[LLM] Processing: {sanitised[:120]}")

        # ── 2. Cache lookup ────────────────────────────────────────────────
        cache_key = f"sql_cache:{hashlib.md5(sanitised.encode()).hexdigest()}"
        cached    = await redis_client.get(cache_key)
        if cached:
            logger.info("[LLM] Cache hit – returning cached SQLResponse")
            return SQLResponse(**json.loads(cached))

        # ── 3. Agentic loop ────────────────────────────────────────────────
        logger.info("[LLM] Starting MCP agentic loop …")
        try:
            final_args, tool_trace = await self.bridge.run_agentic_loop(
                model                = self.model,
                system_prompt        = SYSTEM_PROMPT,
                user_prompt          = sanitised,
                conversation_history = conversation_history,
            )
        except Exception as exc:
            logger.error(f"[LLM] Agentic loop error: {exc}", exc_info=True)
            raise Exception(f"Failed to run agentic loop: {exc}")

        # Log tool usage
        if tool_trace:
            tool_names = [t["tool"] for t in tool_trace]
            logger.info(f"[LLM] Tools called: {tool_names}")

        # ── 4. Extract & validate SQL ──────────────────────────────────────
        sql = (final_args.get("sql") or "").strip()

        if not sql:
            logger.warning("[LLM] finalize_response returned empty SQL")
            return SQLResponse(
                sql         = "",
                chart       = None,
                explanation = "Could not generate a SQL query for your request.",
            )

        is_valid, err_msg = sql_validator.validate(sql)
        if not is_valid:
            logger.error(f"[LLM] SQL validation failed: {err_msg} | sql={sql[:120]}")
            raise ValueError(f"Security validation failed: {err_msg}")

        logger.info(f"[LLM] SQL validated: {sql[:120]}")

        # ── 5. Build chart config ──────────────────────────────────────────
        chart_type = final_args.get("chart_type", "table")
        chart: Optional[ChartConfig] = None
        if chart_type and chart_type.lower() != "table":
            chart = ChartConfig(
                type  = chart_type,
                x     = final_args.get("x_axis"),
                y     = final_args.get("y_axis"),
                title = final_args.get("chart_title"),
            )

        sql_response = SQLResponse(
            sql         = sql,
            chart       = chart,
            explanation = final_args.get("explanation", ""),
        )

        # ── 6. Cache result ────────────────────────────────────────────────
        try:
            await redis_client.set(
                cache_key,
                json.dumps(sql_response.model_dump(), default=str),
                ttl=settings.SQL_CACHE_TTL,
            )
            logger.info(f"[LLM] Cached result – key={cache_key}")
        except Exception as exc:
            logger.warning(f"[LLM] Failed to cache result: {exc}")

        return sql_response
