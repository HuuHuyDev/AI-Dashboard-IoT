"""
MCP Database - Direct PostgreSQL Connection
Used by MCP tools to query real schema metadata and run EXPLAIN
"""
import asyncpg
import logging
from typing import Optional, List, Dict, Any

from app.core.config import settings

logger = logging.getLogger(__name__)


class MCPDatabase:
    """
    Async PostgreSQL connection pool dedicated to MCP tools.
    Separate from Query Service to allow schema introspection
    (information_schema, pg_class, EXPLAIN ANALYZE, etc.)
    """

    def __init__(self):
        self._pool: Optional[asyncpg.Pool] = None

    async def connect(self) -> None:
        """Create connection pool"""
        try:
            self._pool = await asyncpg.create_pool(
                host=settings.POSTGRES_HOST,
                port=settings.POSTGRES_PORT,
                user=settings.POSTGRES_USER,
                password=settings.POSTGRES_PASSWORD,
                database=settings.POSTGRES_DB,
                min_size=1,
                max_size=5,
                command_timeout=30,
            )
            logger.info(
                f"MCP Database pool created → "
                f"{settings.POSTGRES_HOST}:{settings.POSTGRES_PORT}/{settings.POSTGRES_DB}"
            )
        except Exception as e:
            logger.error(f"MCP Database connection failed: {e}")
            raise

    async def close(self) -> None:
        """Close connection pool"""
        if self._pool:
            await self._pool.close()
            logger.info("MCP Database pool closed")

    # ── helpers ──────────────────────────────────────────────────────────────

    async def fetch(self, query: str, *args) -> List[Dict[str, Any]]:
        """Execute query, return list of row dicts"""
        async with self._pool.acquire() as conn:
            rows = await conn.fetch(query, *args)
            return [dict(row) for row in rows]

    async def fetchrow(self, query: str, *args) -> Optional[Dict[str, Any]]:
        """Execute query, return first row as dict"""
        async with self._pool.acquire() as conn:
            row = await conn.fetchrow(query, *args)
            return dict(row) if row else None

    async def fetchval(self, query: str, *args) -> Any:
        """Execute query, return scalar value"""
        async with self._pool.acquire() as conn:
            return await conn.fetchval(query, *args)

    @property
    def is_connected(self) -> bool:
        return self._pool is not None and not self._pool._closed


# Singleton – imported by MCP tools
mcp_database = MCPDatabase()
