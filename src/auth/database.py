"""Database connection and session management"""

import asyncpg
from typing import AsyncIterator
from contextlib import asynccontextmanager
from ..agent.config import get_settings

settings = get_settings()


class Database:
    """Database connection manager"""

    def __init__(self):
        self.pool: asyncpg.Pool | None = None

    async def connect(self):
        """Create connection pool"""
        self.pool = await asyncpg.create_pool(
            host=settings.db_host,
            port=settings.db_port,
            user=settings.db_user,
            password=settings.db_password,
            database=settings.db_name,
            min_size=1,
            max_size=10
        )
        print(f"✓ Connected to database: {settings.db_name}")

    async def disconnect(self):
        """Close connection pool"""
        if self.pool:
            await self.pool.close()
            print("✓ Database connection closed")

    @asynccontextmanager
    async def get_connection(self) -> AsyncIterator[asyncpg.Connection]:
        """Get a connection from the pool"""
        if not self.pool:
            raise RuntimeError("Database not connected")
        async with self.pool.acquire() as conn:
            yield conn


# Global database instance
db = Database()


async def get_db() -> AsyncIterator[asyncpg.Connection]:
    """Dependency injection for database connection"""
    async with db.get_connection() as conn:
        yield conn
