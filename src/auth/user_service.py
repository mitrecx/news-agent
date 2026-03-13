"""User service for database operations"""

import asyncpg
from typing import Optional
from .models import User, UserInDB, UserCreate
from .security import get_password_hash, verify_password


class UserService:
    """Service for user-related operations"""

    @staticmethod
    async def create_user(conn: asyncpg.Connection, user_data: UserCreate) -> UserInDB:
        """Create a new user"""
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

        return UserInDB(
            id=row["id"],
            username=row["username"],
            email=row["email"],
            hashed_password=row["hashed_password"]
        )

    @staticmethod
    async def get_user_by_username(conn: asyncpg.Connection, username: str) -> Optional[UserInDB]:
        """Get a user by username"""
        row = await conn.fetchrow(
            """
            SELECT id, username, email, hashed_password
            FROM users
            WHERE username = $1
            """,
            username
        )

        if not row:
            return None

        return UserInDB(
            id=row["id"],
            username=row["username"],
            email=row["email"],
            hashed_password=row["hashed_password"]
        )

    @staticmethod
    async def get_user_by_id(conn: asyncpg.Connection, user_id: int) -> Optional[User]:
        """Get a user by ID (without password)"""
        row = await conn.fetchrow(
            """
            SELECT id, username, email
            FROM users
            WHERE id = $1
            """,
            user_id
        )

        if not row:
            return None

        return User(
            id=row["id"],
            username=row["username"],
            email=row["email"]
        )

    @staticmethod
    async def authenticate_user(
        conn: asyncpg.Connection,
        username: str,
        password: str
    ) -> Optional[UserInDB]:
        """Authenticate a user by username and password"""
        user = await UserService.get_user_by_username(conn, username)
        if not user:
            return None
        if not verify_password(password, user.hashed_password):
            return None
        return user
