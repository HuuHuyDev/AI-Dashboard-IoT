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

import google.generativeai as genai
from mcp.server.fastmcp import FastMCP

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# JSON Schema → Gemini proto type mapping
# ---------------------------------------------------------------------------
_TYPE_MAP: Dict[str, Any] = {
    "string":  genai.protos.Type.STRING,
    "number":  genai.protos.Type.NUMBER,
    "float":   genai.protos.Type.NUMBER,
    "integer": genai.protos.Type.INTEGER,
    "boolean": genai.protos.Type.BOOLEAN,
    "array":   genai.protos.Type.ARRAY,
    "object":  genai.protos.Type.OBJECT,
}

MAX_TOOL_ROUNDS = 10   # safety: never loop more than this many tool rounds


def _json_schema_to_gemini(schema: dict) -> genai.protos.Schema:
    """Recursively convert a JSON Schema dict → genai.protos.Schema."""
    raw_type  = schema.get("type", "string")
    gtype     = _TYPE_MAP.get(str(raw_type).lower(), genai.protos.Type.STRING)
    kwargs: Dict[str, Any] = {
        "type":        gtype,
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

    return genai.protos.Schema(**kwargs)


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
        self._gemini_tools_cache: Optional[List[genai.protos.Tool]] = None
        self._tool_names: List[str] = []

    # ── Tool registration ──────────────────────────────────────────────────

    def get_gemini_tools(self) -> List[genai.protos.Tool]:
        """
        Convert every MCP tool to a Gemini FunctionDeclaration.
        Result is cached after first call.
        """
        if self._gemini_tools_cache is not None:
            return self._gemini_tools_cache

        declarations: List[genai.protos.FunctionDeclaration] = []

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

                    func_decl = genai.protos.FunctionDeclaration(
                        name        = tool_name,
                        description = tool.description or f"MCP tool: {tool_name}",
                        parameters  = genai.protos.Schema(
                            type       = genai.protos.Type.OBJECT,
                            properties = properties,
                            required   = required,
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
        finalize_decl = genai.protos.FunctionDeclaration(
            name        = "finalize_response",
            description = (
                "Call this LAST when you have gathered enough information and "
                "are ready to return the final SQL query and chart configuration. "
                "Do NOT call this until you have verified column names via get_table_schema."
            ),
            parameters  = genai.protos.Schema(
                type       = genai.protos.Type.OBJECT,
                properties = {
                    "sql": genai.protos.Schema(
                        type        = genai.protos.Type.STRING,
                        description = "The final optimised PostgreSQL SELECT query",
                    ),
                    "explanation": genai.protos.Schema(
                        type        = genai.protos.Type.STRING,
                        description = "Plain-English explanation of what the query does",
                    ),
                    "chart_type": genai.protos.Schema(
                        type        = genai.protos.Type.STRING,
                        description = "Best chart type: line | bar | pie | scatter | table",
                    ),
                    "x_axis": genai.protos.Schema(
                        type        = genai.protos.Type.STRING,
                        description = "Column name for X axis",
                    ),
                    "y_axis": genai.protos.Schema(
                        type        = genai.protos.Type.STRING,
                        description = "Column name for Y axis",
                    ),
                    "chart_title": genai.protos.Schema(
                        type        = genai.protos.Type.STRING,
                        description = "Human-readable chart title",
                    ),
                },
                required = ["sql", "explanation", "chart_type"],
            ),
        )
        declarations.append(finalize_decl)

        logger.info(
            f"GeminiBridge: registered {len(declarations)} functions "
            f"({len(self._tool_names)} MCP + 1 finalize)"
        )
        self._gemini_tools_cache = [genai.protos.Tool(function_declarations=declarations)]
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
        chat        = model.start_chat(enable_automatic_function_calling=False)
        tool_trace  : List[dict] = []
        rounds      = 0

        # ── Start with the system prompt + user question ───────────────────
        full_prompt = f"{system_prompt}\n\nUser question: {user_prompt}"

        # Inject optional conversation history as context
        if conversation_history:
            history_text = "\n".join(
                f"{m['role'].upper()}: {m.get('content', '')}"
                for m in conversation_history[-6:]     # last 3 turns
            )
            full_prompt = f"Previous conversation:\n{history_text}\n\n{full_prompt}"

        response = chat.send_message(full_prompt)

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
                # Gemini returned plain text – no structured output
                logger.warning("Gemini returned plain text instead of function call")
                break

            response_parts: List[genai.protos.Part] = []

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
                    genai.protos.Part(
                        function_response=genai.protos.FunctionResponse(
                            name     = fc_name,
                            response = result_data,
                        )
                    )
                )

            if not response_parts:
                break

            # Feed all tool results back to Gemini
            response = chat.send_message(response_parts)

        # Fallback – Gemini never called finalize_response
        logger.warning(f"Agentic loop ended after {rounds} rounds without finalize_response")
        return {}, tool_trace

    # ── Helper ────────────────────────────────────────────────────────────

    @property
    def registered_tool_names(self) -> List[str]:
        return self._tool_names.copy()
