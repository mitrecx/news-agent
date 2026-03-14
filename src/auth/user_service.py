"""User service for database operations.

This module provides business logic for user-related database operations
including registration, authentication, and user retrieval.
"""

import asyncpg
import logging
from typing import Optional
from .models import User, UserInDB, UserCreate
from .security import get_password_hash, verify_password

logger = logging.getLogger(__name__)


class UserService:
    """Service for user-related operations."""

    @staticmethod
    async def create_user(conn: asyncpg.Connection, user_data: UserCreate) -> UserInDB:
        """
        Create a new user with hashed password.

        Args:
            conn: Database connection
            user_data: User registration data

        Returns:
            Created user with ID and hashed password

        Raises:
            asyncpg.UniqueViolationError: If username already exists
            asyncpg.PostgresError: For database errors
        """
        try:
            # Hash password with bcrypt
            hashed_password = get_password_hash(user_data.password)

            row = await conn.fetchrow(
                """
                INSERT INTO users (username, email, hashed_password)
                VALUES ($1, $2, $3)
                RETURNING id, username, email, hashed_password, created_at
                """,
                user_data.username,
                user_data.email,
                hashed_password
            )

            logger.info(f"✓ Created new user: {user_data.username}")
            return UserInDB(
                id=row["id"],
                username=row["username"],
                email=row["email"],
                hashed_password=row["hashed_password"]
            )
        except asyncpg.UniqueViolationError as e:
            logger.warning(f"✗ Username already exists: {user_data.username}")
            raise
        except asyncpg.PostgresError as e:
            logger.error(f"✗ Database error creating user: {e}", exc_info=True)
            raise
        except Exception as e:
            logger.error(f"✗ Unexpected error creating user: {e}", exc_info=True)
            raise

    @staticmethod
    async def get_user_by_username(
        conn: asyncpg.Connection,
        username: str
    ) -> Optional[UserInDB]:
        """
        Get a user by username (including password hash).

        Args:
            conn: Database connection
            username: Username to look up

        Returns:
            User with password hash if found, None otherwise

        Raises:
            asyncpg.PostgresError: For database errors
        """
        try:
            row = await conn.fetchrow(
                """
                SELECT id, username, email, hashed_password
                FROM users
                WHERE username = $1
                """,
                username
            )

            if not row:
                logger.debug(f"User not found: {username}")
                return None

            return UserInDB(
                id=row["id"],
                username=row["username"],
                email=row["email"],
                hashed_password=row["hashed_password"]
            )
        except asyncpg.PostgresError as e:
            logger.error(f"✗ Database error fetching user: {e}", exc_info=True)
            raise

    @staticmethod
    async def get_user_by_id(
        conn: asyncpg.Connection,
        user_id: int
    ) -> Optional[User]:
        """
        Get a user by ID (without password hash for security).

        Args:
            conn: Database connection
            user_id: User ID to look up

        Returns:
            User without password if found, None otherwise

        Raises:
            asyncpg.PostgresError: For database errors
        """
        try:
            row = await conn.fetchrow(
                """
                SELECT id, username, email
                FROM users
                WHERE id = $1
                """,
                user_id
            )

            if not row:
                logger.debug(f"User not found by ID: {user_id}")
                return None

            return User(
                id=row["id"],
                username=row["username"],
                email=row["email"]
            )
        except asyncpg.PostgresError as e:
            logger.error(f"✗ Database error fetching user by ID: {e}", exc_info=True)
            raise

    @staticmethod
    async def authenticate_user(
        conn: asyncpg.Connection,
        username: str,
        password: str
    ) -> Optional[UserInDB]:
        """
        Authenticate a user by username and password.

        Args:
            conn: Database connection
            username: Username to authenticate
            password: Plain text password to verify

        Returns:
            Authenticated user with password hash if successful, None otherwise
        """
        try:
            user = await UserService.get_user_by_username(conn, username)
            if not user:
                logger.debug(f"Authentication failed: user not found: {username}")
                return None

            if not verify_password(password, user.hashed_password):
                logger.warning(f"Authentication failed: invalid password for: {username}")
                return None

            logger.info(f"✓ User authenticated successfully: {username}")
            return user
        except Exception as e:
            logger.error(f"✗ Unexpected error during authentication: {e}", exc_info=True)
            return None
