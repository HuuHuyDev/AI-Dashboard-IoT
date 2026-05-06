"""
Gemini ↔ MCP Bridge
====================
Converts FastMCP tool definitions → Gemini FunctionDeclarations
and drives the multi-turn agentic tool-calling loop.

Flow
----
1. get_gemini_tools()   – advertise all 7 MCP tools to Gemini
2. Gemini returns function_call(s)
3. execute_tool()       – runs the real MCP tool
4. Feed result back as FunctionResponse Part
5. Repeat until Gemini emits a `finalize_response` structured call
"""

import json
import logging
from typing import Any, Dict, List, Optional, Tuple
import re
import asyncio
import os
import time
from collections import deque

import google.generativeai as genai
import google.ai.generativelanguage as glm
from mcp.server.fastmcp import FastMCP

logger = logging.getLogger(__name__)

MAX_TOOL_ROUNDS = 10   # safety: never loop more than this many tool rounds

# Gemini free-tier quotas are very low (e.g., 5 generate_content requests/min/model).
# The agentic loop may require multiple requests per user query.
_GEMINI_RPM = int(os.getenv("GEMINI_MAX_RPM", "15"))  # Increased for paid tier
_GEMINI_WINDOW_SEC = int(os.getenv("GEMINI_RPM_WINDOW_SEC", "60"))
# 429 responses often include retry_delay ~60s. The agentic loop can require
# multiple Gemini calls, so defaults need to allow enough backoff time.
_GEMINI_MAX_RETRIES = int(os.getenv("GEMINI_429_MAX_RETRIES", "3"))  # Reduced retries
_GEMINI_MAX_TOTAL_WAIT_SEC = float(os.getenv("GEMINI_429_MAX_TOTAL_WAIT_SEC", "120"))  # Max 2 minutes wait

_rate_lock = asyncio.Lock()
_request_times: "deque[float]" = deque()


def _parse_retry_delay_seconds(message: str) -> Optional[float]:
    if not message:
        return None

    # Pattern: "Please retry in 19.2507s"
    m = re.search(r"retry\s+in\s+(\d+(?:\.\d+)?)s", message, flags=re.IGNORECASE)
    if m:
        try:
            return float(m.group(1))
        except ValueError:
            return None

    # Pattern: "retry_delay { seconds: 19 }"
    m = re.search(r"retry_delay\s*\{[^}]*seconds:\s*(\d+)", message, flags=re.IGNORECASE)
    if m:
        try:
            return float(m.group(1))
        except ValueError:
            return None

    return None


def _is_quota_429(exc: BaseException) -> bool:
    msg = str(exc) or ""
    return (
        "429" in msg
        or "ResourceExhausted" in msg
        or "exceeded your current quota" in msg
        or "rate-limits" in msg
        or "Quota exceeded" in msg
    )


async def _acquire_gemini_slot() -> None:
    """Simple in-process RPM limiter for Gemini requests."""
    if _GEMINI_RPM <= 0:
        return

    while True:
        async with _rate_lock:
            now = time.monotonic()
            # Drop old timestamps
            while _request_times and (now - _request_times[0]) >= _GEMINI_WINDOW_SEC:
                _request_times.popleft()

            if len(_request_times) < _GEMINI_RPM:
                _request_times.append(now)
                return

            # Need to wait until the oldest request falls out of window
            wait_for = _GEMINI_WINDOW_SEC - (now - _request_times[0])
            wait_for = max(0.5, wait_for)

        await asyncio.sleep(wait_for)


async def _send_message_with_retry(chat, content):
    """Send a Gemini message with RPM limiting and 429 retry support."""
    retries = 0
    total_wait = 0.0

    while True:
        await _acquire_gemini_slot()
        try:
            # google-generativeai is sync; run in a thread to avoid blocking the event loop.
            return await asyncio.to_thread(chat.send_message, content)
        except Exception as exc:
            if not _is_quota_429(exc):
                raise

            retries += 1
            # Use exponential backoff with jitter instead of fixed delay
            base_delay = min(2 ** retries, 30)  # Cap at 30 seconds
            jitter = base_delay * 0.2  # 20% jitter
            delay = base_delay + (jitter * (2 * asyncio.get_event_loop().time() % 1 - 1))
            
            # Parse server-suggested delay if available
            suggested_delay = _parse_retry_delay_seconds(str(exc))
            if suggested_delay:
                delay = min(suggested_delay, 30)  # Cap at 30 seconds

            logger.warning(
                "Gemini 429 quota hit (attempt %s/%s). Sleeping %.2fs then retrying...",
                retries,
                _GEMINI_MAX_RETRIES,
                delay,
            )

            total_wait += delay
            if retries > _GEMINI_MAX_RETRIES or total_wait > _GEMINI_MAX_TOTAL_WAIT_SEC:
                logger.error(
                    "Gemini quota exhausted after %s retries (%.2fs total wait). "
                    "Consider upgrading to paid tier or reducing request rate.",
                    retries,
                    total_wait,
                )
                raise

            await asyncio.sleep(delay)


# ---------------------------------------------------------------------------
# JSON Schema → Gemini proto Schema mapping
# ---------------------------------------------------------------------------

_TYPE_MAP: Dict[str, glm.Type] = {
    "string": glm.Type.STRING,
    "number": glm.Type.NUMBER,
    "float": glm.Type.NUMBER,
    "integer": glm.Type.INTEGER,
    "boolean": glm.Type.BOOLEAN,
    "array": glm.Type.ARRAY,
    "object": glm.Type.OBJECT,
}


def _json_schema_to_gemini(schema: dict) -> glm.Schema:
    """Recursively convert a JSON Schema dict → google.ai.generativelanguage.Schema."""
    raw_type = str(schema.get("type", "string")).lower()
    gtype = _TYPE_MAP.get(raw_type, glm.Type.STRING)

    kwargs: Dict[str, Any] = {
        "type_": gtype,
        "description": schema.get("description", ""),
    }

    if raw_type == "object" and "properties" in schema:
        kwargs["properties"] = {
            k: _json_schema_to_gemini(v)
            for k, v in schema["properties"].items()
        }
        if "required" in schema:
            kwargs["required"] = schema["required"]

    elif raw_type == "array" and "items" in schema:
        kwargs["items"] = _json_schema_to_gemini(schema["items"])

    if "enum" in schema:
        kwargs["enum"] = [str(e) for e in schema["enum"]]

    return glm.Schema(**kwargs)


def _extract_sql_from_text(text: str) -> str:
    """Best-effort SQL extraction from a model plain-text response."""
    if not text:
        return ""

    # Prefer fenced ```sql blocks
    fenced = re.search(r"```\s*sql\s*(.*?)```", text, flags=re.IGNORECASE | re.DOTALL)
    if fenced:
        candidate = fenced.group(1).strip()
        return candidate

    # Otherwise, grab from first SELECT onwards
    m = re.search(r"\bselect\b[\s\S]*", text, flags=re.IGNORECASE)
    if not m:
        return ""

    candidate = m.group(0).strip()

    # Trim any trailing markdown fences
    candidate = re.sub(r"```[\s\S]*$", "", candidate).strip()
    return candidate


# ---------------------------------------------------------------------------
# Bridge class
# ---------------------------------------------------------------------------

class GeminiBridge:
    """
    Bridges Google Gemini Function Calling with an MCP FastMCP server.

    Usage
    -----
    bridge = GeminiBridge(mcp_server)
    tools  = bridge.get_gemini_tools()          # advertise to Gemini model
    result = await bridge.run_agentic_loop(
                 model, chat_history, user_prompt
             )
    """

    def __init__(self, mcp: FastMCP):
        self.mcp  = mcp
        self._gemini_tools_cache: Optional[List[glm.Tool]] = None
        self._tool_names: List[str] = []

    # ── Tool registration ──────────────────────────────────────────────────

    def get_gemini_tools(self) -> List[glm.Tool]:
        """
        Convert every MCP tool to a Gemini Tool definition.
        Result is cached after first call.
        """
        if self._gemini_tools_cache is not None:
            return self._gemini_tools_cache

        declarations: List[glm.FunctionDeclaration] = []

        # ──  MCP discovery tools  ──────────────────────────────────────────
        try:
            tool_manager = self.mcp._tool_manager
            mcp_tools    = tool_manager._tools          # dict[name, Tool]

            for tool_name, tool in mcp_tools.items():
                try:
                    param_schema   = tool.parameters or {}
                    properties     = {}
                    required: list = []

                    if "properties" in param_schema:
                        for pname, pschema in param_schema["properties"].items():
                            properties[pname] = _json_schema_to_gemini(pschema)
                        required = param_schema.get("required", [])

                    func_decl = glm.FunctionDeclaration(
                        name=tool_name,
                        description=tool.description or f"MCP tool: {tool_name}",
                        parameters=glm.Schema(
                            type_=glm.Type.OBJECT,
                            properties=properties,
                            required=required,
                        ),
                    )
                    declarations.append(func_decl)
                    self._tool_names.append(tool_name)
                    logger.debug(f"Registered MCP→Gemini: {tool_name}")

                except Exception as e:
                    logger.warning(f"Skipping tool {tool_name}: {e}")

        except Exception as e:
            logger.error(f"Failed to enumerate MCP tools: {e}")

        # ── Final structured-output function (NOT an MCP tool) ─────────────
        # Gemini calls this when it is ready to commit to a SQL + chart config.
        finalize_decl = glm.FunctionDeclaration(
            name="finalize_response",
            description=(
                "Call this LAST when you have gathered enough information and "
                "are ready to return the final SQL query and chart configuration. "
                "Do NOT call this until you have verified column names via get_table_schema."
            ),
            parameters=glm.Schema(
                type_=glm.Type.OBJECT,
                properties={
                    "sql": glm.Schema(
                        type_=glm.Type.STRING,
                        description="The final optimised PostgreSQL SELECT query",
                    ),
                    "explanation": glm.Schema(
                        type_=glm.Type.STRING,
                        description="Plain-English explanation of what the query does",
                    ),
                    "chart_type": glm.Schema(
                        type_=glm.Type.STRING,
                        description="Best chart type: line | bar | pie | scatter | table",
                    ),
                    "x_axis": glm.Schema(
                        type_=glm.Type.STRING,
                        description="Column name for X axis",
                    ),
                    "y_axis": glm.Schema(
                        type_=glm.Type.STRING,
                        description="Column name for Y axis",
                    ),
                    "chart_title": glm.Schema(
                        type_=glm.Type.STRING,
                        description="Human-readable chart title",
                    ),
                },
                required=["sql", "explanation", "chart_type"],
            ),
        )
        declarations.append(finalize_decl)

        logger.info(
            f"GeminiBridge: registered {len(declarations)} functions "
            f"({len(self._tool_names)} MCP + 1 finalize)"
        )
        self._gemini_tools_cache = [glm.Tool(function_declarations=declarations)]
        return self._gemini_tools_cache

    # ── Tool execution ─────────────────────────────────────────────────────

    async def execute_tool(self, tool_name: str, tool_args: dict) -> str:
        """Execute one MCP tool and return result as a string."""
        try:
            logger.info(f"▶ MCP tool call: {tool_name}({list(tool_args.keys())})")
            result = await self.mcp.call_tool(tool_name, tool_args)

            # Extract text from MCP CallToolResult
            if hasattr(result, "content"):
                parts = [p.text for p in result.content if hasattr(p, "text")]
                text  = "\n".join(parts)
            elif isinstance(result, list):
                text = "\n".join(p.text for p in result if hasattr(p, "text"))
            else:
                text = str(result)

            logger.info(f"◀ {tool_name} → {len(text)} chars")
            return text

        except Exception as exc:
            err = f"Tool '{tool_name}' failed: {exc}"
            logger.error(err)
            return json.dumps({"error": err})

    # ── Agentic loop ───────────────────────────────────────────────────────

    async def run_agentic_loop(
        self,
        model: genai.GenerativeModel,
        system_prompt: str,
        user_prompt: str,
        conversation_history: Optional[List[dict]] = None,
    ) -> Tuple[dict, List[dict]]:
        """
        Drive the full multi-turn agentic loop:
          prompt → tool calls → results → … → finalize_response

        Returns
        -------
        (final_args, tool_trace)
            final_args   : dict from Gemini's finalize_response call
                           keys: sql, explanation, chart_type, x_axis, y_axis, chart_title
            tool_trace   : list of {"tool", "args", "result"} dicts for debugging
        """
        chat        = model.start_chat()
        tool_trace  : List[dict] = []
        rounds      = 0
        nudged_finalize = False

        # ── Start with the system prompt + user question ───────────────────
        full_prompt = f"{system_prompt}\n\nUser question: {user_prompt}"

        # Inject optional conversation history as context
        if conversation_history:
            history_text = "\n".join(
                f"{m['role'].upper()}: {m.get('content', '')}"
                for m in conversation_history[-6:]     # last 3 turns
            )
            full_prompt = f"Previous conversation:\n{history_text}\n\n{full_prompt}"

        # Initial model call (may be rate-limited)
        response = await _send_message_with_retry(chat, full_prompt)

        # ── Tool-calling loop ──────────────────────────────────────────────
        while rounds < MAX_TOOL_ROUNDS:
            rounds += 1

            # Collect all function calls from this response
            function_calls = [
                part.function_call
                for part in response.candidates[0].content.parts
                if hasattr(part, "function_call") and part.function_call.name
            ]

            if not function_calls:
                # Gemini returned plain text – try to extract SQL or nudge finalize.
                text_parts = [
                    getattr(part, "text", "")
                    for part in response.candidates[0].content.parts
                    if getattr(part, "text", "")
                ]
                plain_text = "\n".join(text_parts).strip()

                if plain_text:
                    logger.warning(
                        "Gemini plain-text (snippet): %s",
                        plain_text[:300].replace("\n", " "),
                    )

                sql = _extract_sql_from_text(plain_text)
                if sql:
                    logger.info("✔ Extracted SQL from plain-text response")
                    return {
                        "sql": sql,
                        "explanation": plain_text or "Extracted from model response.",
                        "chart_type": "table",
                    }, tool_trace

                if not nudged_finalize:
                    nudged_finalize = True
                    logger.warning(
                        "Gemini returned plain text without SQL; nudging finalize_response"
                    )
                    response = await _send_message_with_retry(
                        chat,
                        "Please CALL finalize_response now. "
                        "Return ONLY a function call with: sql (SELECT only), explanation, chart_type.",
                    )
                    continue

                logger.warning("Gemini returned plain text instead of function call")
                break

            response_parts: List[glm.Part] = []

            for fc in function_calls:
                fc_name = fc.name
                fc_args = dict(fc.args)

                # ── finalize_response → end the loop ──────────────────────
                if fc_name == "finalize_response":
                    logger.info(f"✔ Gemini finalized after {rounds} rounds")
                    return fc_args, tool_trace

                # ── real MCP tool call ─────────────────────────────────────
                tool_result = await self.execute_tool(fc_name, fc_args)
                tool_trace.append(
                    {"tool": fc_name, "args": fc_args, "result": tool_result[:500]}
                )

                # Parse JSON for structured FunctionResponse
                try:
                    result_data = json.loads(tool_result)
                except (json.JSONDecodeError, TypeError):
                    result_data = {"output": tool_result}

                response_parts.append(
                    glm.Part(
                        function_response=glm.FunctionResponse(
                            name=fc_name,
                            response=result_data,
                        )
                    )
                )

            if not response_parts:
                break

            # Strongly steer the model to continue via tool calls only.
            response_parts.append(
                glm.Part(
                    text=(
                        "Next step: DO NOT answer in plain text. "
                        "Either call another tool to gather missing info, "
                        "or CALL finalize_response with sql/explanation/chart_type."
                    )
                )
            )

            # Feed all tool results back to Gemini
            response = await _send_message_with_retry(chat, response_parts)

        # Fallback – Gemini never called finalize_response
        logger.warning(f"Agentic loop ended after {rounds} rounds without finalize_response")
        return {}, tool_trace

    # ── Helper ────────────────────────────────────────────────────────────

    @property
    def registered_tool_names(self) -> List[str]:
        return self._tool_names.copy()
