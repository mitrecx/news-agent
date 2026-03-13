"""Conversation service for database operations"""

import asyncpg
from typing import Optional, List
from datetime import datetime


class ConversationService:
    """Service for conversation-related operations"""

    @staticmethod
    async def create_conversation(
        conn: asyncpg.Connection,
        user_id: int,
        title: str
    ) -> dict:
        """Create a new conversation"""
        row = await conn.fetchrow(
            """
            INSERT INTO conversations (user_id, title)
            VALUES ($1, $2)
            RETURNING id, user_id, title, created_at, updated_at
            """,
            user_id,
            title
        )
        return {
            "id": row["id"],
            "user_id": row["user_id"],
            "title": row["title"],
            "created_at": row["created_at"].isoformat(),
            "updated_at": row["updated_at"].isoformat()
        }

    @staticmethod
    async def get_conversation_by_id(
        conn: asyncpg.Connection,
        conversation_id: int,
        user_id: int
    ) -> Optional[dict]:
        """Get a conversation by ID (with user validation)"""
        row = await conn.fetchrow(
            """
            SELECT id, user_id, title, created_at, updated_at
            FROM conversations
            WHERE id = $1 AND user_id = $2
            """,
            conversation_id,
            user_id
        )
        if not row:
            return None
        return {
            "id": row["id"],
            "user_id": row["user_id"],
            "title": row["title"],
            "created_at": row["created_at"].isoformat(),
            "updated_at": row["updated_at"].isoformat()
        }

    @staticmethod
    async def list_conversations(
        conn: asyncpg.Connection,
        user_id: int,
        limit: int = 50,
        offset: int = 0
    ) -> List[dict]:
        """List all conversations for a user (paginated)"""
        rows = await conn.fetch(
            """
            SELECT id, user_id, title, created_at, updated_at
            FROM conversations
            WHERE user_id = $1
            ORDER BY updated_at DESC
            LIMIT $2 OFFSET $3
            """,
            user_id,
            limit,
            offset
        )
        return [
            {
                "id": row["id"],
                "user_id": row["user_id"],
                "title": row["title"],
                "created_at": row["created_at"].isoformat(),
                "updated_at": row["updated_at"].isoformat()
            }
            for row in rows
        ]

    @staticmethod
    async def update_conversation(
        conn: asyncpg.Connection,
        conversation_id: int,
        user_id: int,
        title: str
    ) -> Optional[dict]:
        """Update conversation title"""
        row = await conn.fetchrow(
            """
            UPDATE conversations
            SET title = $1, updated_at = CURRENT_TIMESTAMP
            WHERE id = $2 AND user_id = $3
            RETURNING id, user_id, title, created_at, updated_at
            """,
            title,
            conversation_id,
            user_id
        )
        if not row:
            return None
        return {
            "id": row["id"],
            "user_id": row["user_id"],
            "title": row["title"],
            "created_at": row["created_at"].isoformat(),
            "updated_at": row["updated_at"].isoformat()
        }

    @staticmethod
    async def delete_conversation(
        conn: asyncpg.Connection,
        conversation_id: int,
        user_id: int
    ) -> bool:
        """Delete a conversation (messages will be cascade deleted)"""
        result = await conn.execute(
            """
            DELETE FROM conversations
            WHERE id = $1 AND user_id = $2
            """,
            conversation_id,
            user_id
        )
        return result == "DELETE 1"

    @staticmethod
    async def add_message(
        conn: asyncpg.Connection,
        conversation_id: int,
        role: str,
        content: str
    ) -> dict:
        """Add a message to a conversation"""
        row = await conn.fetchrow(
            """
            INSERT INTO messages (conversation_id, role, content)
            VALUES ($1, $2, $3)
            RETURNING id, conversation_id, role, content, created_at
            """,
            conversation_id,
            role,
            content
        )
        return {
            "id": row["id"],
            "conversation_id": row["conversation_id"],
            "role": row["role"],
            "content": row["content"],
            "created_at": row["created_at"].isoformat()
        }

    @staticmethod
    async def get_messages(
        conn: asyncpg.Connection,
        conversation_id: int,
        user_id: int
    ) -> List[dict]:
        """Get all messages for a conversation (with user validation)"""
        # Verify conversation belongs to user
        conv = await ConversationService.get_conversation_by_id(conn, conversation_id, user_id)
        if not conv:
            return []

        rows = await conn.fetch(
            """
            SELECT id, conversation_id, role, content, created_at
            FROM messages
            WHERE conversation_id = $1
            ORDER BY created_at ASC
            """,
            conversation_id
        )
        return [
            {
                "id": row["id"],
                "conversation_id": row["conversation_id"],
                "role": row["role"],
                "content": row["content"],
                "created_at": row["created_at"].isoformat()
            }
            for row in rows
        ]

    @staticmethod
    async def update_conversation_timestamp(
        conn: asyncpg.Connection,
        conversation_id: int
    ):
        """Update conversation's updated_at timestamp"""
        await conn.execute(
            """
            UPDATE conversations
            SET updated_at = CURRENT_TIMESTAMP
            WHERE id = $1
            """,
            conversation_id
        )

    @staticmethod
    async def get_message_history_for_agent(
        conn: asyncpg.Connection,
        conversation_id: int,
        user_id: int,
        exclude_last: bool = False
    ) -> Optional[List[dict]]:
        """
        Get message history formatted for agent consumption.
        If exclude_last is True, excludes the last message (useful when sending current message separately).
        """
        messages = await ConversationService.get_messages(conn, conversation_id, user_id)
        if not messages:
            return None

        if exclude_last and len(messages) > 0:
            messages = messages[:-1]

        # Convert to agent format
        return [
            {"role": msg["role"], "content": msg["content"]}
            for msg in messages
        ]
