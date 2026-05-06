"""
MCP Server – IoT Dashboard Database Tools
==========================================
Exposes 7 tools via Model Context Protocol so the LLM (Gemini) can:

  1. list_tables()              – discover what tables exist
  2. get_table_schema()         – get real column names / types
  3. get_device_list()          – list actual devices in DB
  4. get_data_range()           – know the time/value range of any column
  5. get_sample_data()          – preview real rows
  6. execute_sql_query()        – run a SELECT and get results (via Query Service)
  7. explain_sql_query()        – EXPLAIN ANALYZE to check efficiency

The tools are registered with FastMCP and then bridged to Gemini
Function Calling via GeminiBridge (gemini_bridge.py).
"""

import json
import logging
from typing import Optional

import httpx
from mcp.server.fastmcp import FastMCP

from app.mcp.database import mcp_database
from app.core.config import settings

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Allowed tables (whitelist – prevents schema leakage / injection)
# ---------------------------------------------------------------------------
ALLOWED_TABLES = {"devices", "logs", "daily_stats", "alerts"}

# ---------------------------------------------------------------------------
# FastMCP server instance
# ---------------------------------------------------------------------------
mcp_server = FastMCP(
    name="iot-dashboard-mcp",
    instructions=(
        "You are connected to an IoT dashboard PostgreSQL database. "
        "ALWAYS call get_table_schema() before writing SQL so you know "
        "the exact column names. Use get_data_range('logs','timestamp') "
        "to understand the available time window. "
        "Call execute_sql_query() as your LAST step to retrieve real data."
    ),
)


# ===========================================================================
# Tool 1 – list_tables
# ===========================================================================
@mcp_server.tool()
async def list_tables() -> str:
    """
    List all available tables in the IoT dashboard database with row counts.

    Call this FIRST to understand what data is available before writing any SQL.
    Returns table names and approximate row counts.
    """
    try:
        rows = await mcp_database.fetch(
            """
            SELECT table_name
            FROM information_schema.tables
            WHERE table_schema = 'public'
              AND table_type = 'BASE TABLE'
            ORDER BY table_name
            """
        )

        result = []
        for row in rows:
            tname = row["table_name"]
            try:
                cnt = await mcp_database.fetchval(f'SELECT COUNT(*) FROM "{tname}"')
            except Exception:
                cnt = -1
            result.append({"table": tname, "row_count": cnt})

        return json.dumps(
            {"tables": result, "total": len(result)},
            indent=2,
        )

    except Exception as exc:
        logger.error(f"list_tables error: {exc}")
        return json.dumps({"error": str(exc)})


# ===========================================================================
# Tool 2 – get_table_schema
# ===========================================================================
@mcp_server.tool()
async def get_table_schema(table_name: str) -> str:
    """
    Get the complete schema for a specific table: columns, data types,
    nullable flags, defaults, foreign keys, and index names.

    Args:
        table_name: One of 'devices', 'logs', 'daily_stats', 'alerts'

    Use this to know EXACT column names before writing any SQL query.
    """
    if table_name not in ALLOWED_TABLES:
        return json.dumps(
            {
                "error": f"Table '{table_name}' is not accessible.",
                "allowed_tables": sorted(ALLOWED_TABLES),
            }
        )

    try:
        columns = await mcp_database.fetch(
            """
            SELECT
                c.column_name,
                c.data_type,
                c.udt_name,
                c.is_nullable,
                c.column_default,
                c.character_maximum_length,
                c.ordinal_position
            FROM information_schema.columns c
            WHERE c.table_name   = $1
              AND c.table_schema = 'public'
            ORDER BY c.ordinal_position
            """,
            table_name,
        )

        if not columns:
            return json.dumps({"error": f"Table '{table_name}' not found or has no columns."})

        indexes = await mcp_database.fetch(
            "SELECT indexname FROM pg_indexes WHERE tablename = $1 ORDER BY indexname",
            table_name,
        )

        fkeys = await mcp_database.fetch(
            """
            SELECT
                kcu.column_name,
                ccu.table_name  AS ref_table,
                ccu.column_name AS ref_column
            FROM information_schema.table_constraints      tc
            JOIN information_schema.key_column_usage       kcu
              ON tc.constraint_name = kcu.constraint_name
             AND tc.table_schema    = kcu.table_schema
            JOIN information_schema.constraint_column_usage ccu
              ON ccu.constraint_name = tc.constraint_name
             AND ccu.table_schema    = tc.table_schema
            WHERE tc.constraint_type = 'FOREIGN KEY'
              AND tc.table_name      = $1
            """,
            table_name,
        )

        return json.dumps(
            {
                "table": table_name,
                "columns": [
                    {
                        "name":     col["column_name"],
                        "type":     col["udt_name"] or col["data_type"],
                        "nullable": col["is_nullable"] == "YES",
                        "default":  col["column_default"],
                    }
                    for col in columns
                ],
                "indexes":      [idx["indexname"] for idx in indexes],
                "foreign_keys": [
                    {
                        "column":     fk["column_name"],
                        "references": f"{fk['ref_table']}.{fk['ref_column']}",
                    }
                    for fk in fkeys
                ],
            },
            indent=2,
        )

    except Exception as exc:
        logger.error(f"get_table_schema({table_name}) error: {exc}")
        return json.dumps({"error": str(exc)})


# ===========================================================================
# Tool 3 – get_device_list
# ===========================================================================
@mcp_server.tool()
async def get_device_list(
    status_filter: Optional[str] = None,
    device_type_filter: Optional[str] = None,
    limit: int = 50,
) -> str:
    """
    Return the list of IoT devices currently registered in the database.

    Args:
        status_filter:      Optional – filter by status ('active', 'inactive', 'maintenance')
        device_type_filter: Optional – filter by device type (e.g. 'temperature_sensor')
        limit:              Max devices to return (default 50)

    Use this when a user query mentions specific devices, locations, or device types
    so you can reference real device_id values in WHERE clauses.
    """
    try:
        query = """
            SELECT device_id, device_name, device_type, location, status
            FROM   devices
            WHERE  1 = 1
        """
        params: list = []

        if status_filter:
            params.append(status_filter)
            query += f" AND status = ${len(params)}"

        if device_type_filter:
            params.append(device_type_filter)
            query += f" AND device_type = ${len(params)}"

        params.append(min(limit, 200))
        query += f" ORDER BY device_id LIMIT ${len(params)}"

        devices = await mcp_database.fetch(query, *params)

        # Summary by type
        type_summary = await mcp_database.fetch(
            """
            SELECT
                device_type,
                COUNT(*)                                              AS total,
                SUM(CASE WHEN status = 'active' THEN 1 ELSE 0 END)   AS active
            FROM devices
            GROUP BY device_type
            ORDER BY total DESC
            """
        )

        return json.dumps(
            {
                "devices":      [dict(d) for d in devices],
                "returned":     len(devices),
                "type_summary": [dict(t) for t in type_summary],
            },
            indent=2,
            default=str,
        )

    except Exception as exc:
        logger.error(f"get_device_list error: {exc}")
        return json.dumps({"error": str(exc)})


# ===========================================================================
# Tool 4 – get_data_range
# ===========================================================================
@mcp_server.tool()
async def get_data_range(table_name: str, column_name: str) -> str:
    """
    Get MIN / MAX / COUNT for any column in a table.

    Args:
        table_name:  Table to inspect ('logs', 'daily_stats', 'devices', 'alerts')
        column_name: Column to range-check (e.g. 'timestamp', 'temperature', 'humidity')

    Critical for time-based queries: call get_data_range('logs', 'timestamp')
    to know what date range contains data BEFORE writing WHERE clauses.
    """
    if table_name not in ALLOWED_TABLES:
        return json.dumps({"error": f"Table '{table_name}' is not accessible."})

    try:
        row = await mcp_database.fetchrow(
            f"""
            SELECT
                MIN("{column_name}")   AS min_value,
                MAX("{column_name}")   AS max_value,
                COUNT("{column_name}") AS non_null_count,
                COUNT(*)               AS total_rows
            FROM "{table_name}"
            """
        )

        return json.dumps(
            {
                "table":          table_name,
                "column":         column_name,
                "min_value":      str(row["min_value"]) if row["min_value"] is not None else None,
                "max_value":      str(row["max_value"]) if row["max_value"] is not None else None,
                "non_null_count": row["non_null_count"],
                "total_rows":     row["total_rows"],
            },
            indent=2,
        )

    except Exception as exc:
        logger.error(f"get_data_range({table_name}, {column_name}) error: {exc}")
        return json.dumps({"error": str(exc)})


# ===========================================================================
# Tool 5 – get_sample_data
# ===========================================================================
@mcp_server.tool()
async def get_sample_data(table_name: str, limit: int = 3) -> str:
    """
    Fetch a small number of real rows from a table to understand data format.

    Args:
        table_name: Table to preview
        limit:      Number of rows to return (default 3, max 10)

    Useful for understanding exact value formats, units, and data patterns
    before constructing a precise SQL query.
    """
    if table_name not in ALLOWED_TABLES:
        return json.dumps({"error": f"Table '{table_name}' is not accessible."})

    try:
        limit = min(max(limit, 1), 10)
        rows = await mcp_database.fetch(
            f'SELECT * FROM "{table_name}" ORDER BY RANDOM() LIMIT $1',
            limit,
        )
        return json.dumps(
            {"table": table_name, "sample_rows": rows, "returned": len(rows)},
            indent=2,
            default=str,
        )

    except Exception as exc:
        logger.error(f"get_sample_data({table_name}) error: {exc}")
        return json.dumps({"error": str(exc)})


# ===========================================================================
# Tool 6 – execute_sql_query
# ===========================================================================
@mcp_server.tool()
async def execute_sql_query(sql: str, use_cache: bool = True) -> str:
    """
    Execute a SQL SELECT query and return the results.

    Args:
        sql:       A valid PostgreSQL SELECT statement
        use_cache: Whether to use Redis result cache (default True)

    Proxies the request through the Query Service which enforces security
    (SELECT-only) and caches results in Redis.
    Only call this AFTER you have verified the table and column names.
    """
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(
                f"{settings.QUERY_SERVICE_URL}/api/v1/query/execute",
                json={"sql": sql, "use_cache": use_cache},
            )
            resp.raise_for_status()
            result = resp.json()

        data = result.get("data", [])
        preview = data[:20]           # cap tool response size

        return json.dumps(
            {
                "success":        True,
                "sql":            sql,
                "row_count":      result.get("row_count", len(data)),
                "source":         result.get("source", "database"),
                "execution_time": result.get("execution_time"),
                "cached":         result.get("cached", False),
                "data":           preview,
                "truncated":      len(data) > 20,
            },
            indent=2,
            default=str,
        )

    except httpx.HTTPStatusError as exc:
        body = exc.response.text if exc.response else str(exc)
        return json.dumps({"success": False, "error": f"HTTP {exc.response.status_code}: {body}"})
    except Exception as exc:
        logger.error(f"execute_sql_query error: {exc}")
        return json.dumps({"success": False, "error": str(exc)})


# ===========================================================================
# Tool 7 – explain_sql_query
# ===========================================================================
@mcp_server.tool()
async def explain_sql_query(sql: str) -> str:
    """
    Run EXPLAIN (without execution) on a SELECT query and return the plan.

    Args:
        sql: The SQL SELECT query to analyse

    Returns estimated cost, index usage, and join strategies.
    Use this to verify a complex query is efficient BEFORE executing it.
    Helps identify missing indexes or sequential scans on large tables.
    """
    clean = sql.strip().upper()
    if not clean.startswith("SELECT"):
        return json.dumps({"error": "Only SELECT statements can be explained."})

    try:
        rows = await mcp_database.fetch(f"EXPLAIN (FORMAT JSON) {sql}")
        plan = list(rows[0].values())[0] if rows and rows[0] else {}
        return json.dumps({"query": sql, "plan": plan}, indent=2, default=str)

    except Exception as exc:
        logger.error(f"explain_sql_query error: {exc}")
        return json.dumps({"error": str(exc)})
