"""
MCP (Model Context Protocol) Package for IoT Dashboard
Provides real-time database tools for Gemini LLM to generate accurate SQL
"""
from app.mcp.server import mcp_server
from app.mcp.gemini_bridge import GeminiBridge

__all__ = ["mcp_server", "GeminiBridge"]
