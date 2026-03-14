"""Database connection and session management.

This module provides a connection pool manager for PostgreSQL database
connections using asyncpg.
"""

import asyncpg
import logging
from typing import AsyncIterator
from contextlib import asynccontextmanager
from ..agent.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


class Database:
    """
    Database connection manager with connection pooling.

    Attributes:
        pool: The asyncpg connection pool
    """

    def __init__(self) -> None:
        """Initialize the database manager."""
        self.pool: asyncpg.Pool | None = None

    async def connect(self) -> None:
        """
        Create a connection pool to the PostgreSQL database.

        Raises:
            asyncpg.PostgresError: If connection fails
            ValueError: If required configuration is missing
        """
        # Validate configuration
        if not all([settings.db_host, settings.db_user, settings.db_password, settings.db_name]):
            missing = [
                name for name, value in [
                    ("DB_HOST", settings.db_host),
                    ("DB_USER", settings.db_user),
                    ("DB_PASSWORD", settings.db_password),
                    ("DB_NAME", settings.db_name)
                ]
                if not value
            ]
            raise ValueError(
                f"Missing database configuration: {', '.join(missing)}. "
                "Please set these environment variables."
            )

        try:
            # Create connection pool with optimized settings
            self.pool = await asyncpg.create_pool(
                host=settings.db_host,
                port=settings.db_port,
                user=settings.db_user,
                password=settings.db_password,
                database=settings.db_name,
                min_size=2,  # Increased from 1 for better performance
                max_size=20,  # Increased from 10 for better concurrency
                command_timeout=60,  # Add command timeout
                max_inactive_connection_lifetime=300,  # 5 minutes
            )
            logger.info(
                f"✓ Connected to database: {settings.db_name} "
                f"@ {settings.db_host}:{settings.db_port}"
            )
            print(f"✓ Connected to database: {settings.db_name}")
        except asyncpg.PostgresError as e:
            logger.error(f"Failed to connect to database: {e}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error connecting to database: {e}")
            raise

    async def disconnect(self) -> None:
        """Close the connection pool gracefully."""
        if self.pool:
            try:
                await self.pool.close()
                logger.info("✓ Database connection closed")
                print("✓ Database connection closed")
            except Exception as e:
                logger.error(f"Error closing database connection: {e}")
                raise

    @asynccontextmanager
    async def get_connection(self) -> AsyncIterator[asyncpg.Connection]:
        """
        Get a connection from the pool.

        Yields:
            asyncpg.Connection: A database connection

        Raises:
            RuntimeError: If database is not connected
        """
        if not self.pool:
            raise RuntimeError(
                "Database not connected. Call connect() first."
            )
        async with self.pool.acquire() as conn:
            try:
                yield conn
            except asyncpg.PostgresError as e:
                logger.error(f"Database operation error: {e}")
                raise
            except Exception as e:
                logger.error(f"Unexpected database error: {e}")
                raise

    def is_connected(self) -> bool:
        """
        Check if the database is connected.

        Returns:
            bool: True if connected, False otherwise
        """
        return self.pool is not None


# Global database instance
db: Database = Database()


async def get_db() -> AsyncIterator[asyncpg.Connection]:
    """
    Dependency injection function for FastAPI routes.

    Yields:
        asyncpg.Connection: A database connection from the pool

    Raises:
        RuntimeError: If database is not connected
    """
    try:
        async with db.get_connection() as conn:
            yield conn
    except RuntimeError as e:
        logger.error("Database connection not available")
        raise
    except Exception as e:
        logger.error(f"Unexpected error in get_db: {e}")
        raise
