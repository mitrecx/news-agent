"""Database optimization script.

This script adds indexes and optimizations to improve database performance.
Run this after initializing the database.
"""

import asyncio
import asyncpg
import logging
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def optimize_database():
    """Add indexes and optimize the database schema."""

    # Connect to database
    conn = await asyncpg.connect(
        host=os.getenv("DB_HOST", "localhost"),
        port=int(os.getenv("DB_PORT", 5432)),
        user=os.getenv("DB_USER"),
        password=os.getenv("DB_PASSWORD"),
        database=os.getenv("DB_NAME", "news_agent")
    )

    try:
        logger.info("🔧 Starting database optimization...")

        # Indexes for users table
        logger.info("📊 Creating indexes for users table...")

        # Username unique index (should exist from unique constraint)
        await conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_users_username
            ON users(username);
        """)
        logger.info("  ✓ Index on users.username")

        # Indexes for conversations table
        logger.info("📊 Creating indexes for conversations table...")

        # User ID index for faster user conversation lookup
        await conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_conversations_user_id
            ON conversations(user_id);
        """)
        logger.info("  ✓ Index on conversations.user_id")

        # Composite index for user conversations ordered by update time
        await conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_conversations_user_updated
            ON conversations(user_id, updated_at DESC);
        """)
        logger.info("  ✓ Composite index on (user_id, updated_at)")

        # Indexes for messages table
        logger.info("📊 Creating indexes for messages table...")

        # Conversation ID index for faster message retrieval
        await conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_messages_conversation_id
            ON messages(conversation_id);
        """)
        logger.info("  ✓ Index on messages.conversation_id")

        # Composite index for messages ordered by time
        await conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_messages_conv_created
            ON messages(conversation_id, created_at ASC);
        """)
        logger.info("  ✓ Composite index on (conversation_id, created_at)")

        # Analyze tables to update statistics
        logger.info("📈 Analyzing tables...")
        await conn.execute("ANALYZE users;")
        await conn.execute("ANALYZE conversations;")
        await conn.execute("ANALYZE messages;")
        logger.info("  ✓ Table statistics updated")

        # Show table sizes
        logger.info("📏 Database statistics:")
        for table in ["users", "conversations", "messages"]:
            result = await conn.fetchrow("""
                SELECT
                    pg_size_pretty(pg_total_relation_size($1)) as size,
                    (SELECT count(*) FROM $1) as row_count
            """, f"public.{table}" if table != "users" else table)
            logger.info(f"  {table}: {result['size']}, {result['row_count']} rows")

        logger.info("✅ Database optimization completed!")

    except Exception as e:
        logger.error(f"✗ Error during optimization: {e}", exc_info=True)
        raise
    finally:
        await conn.close()
        logger.info("✓ Database connection closed")


if __name__ == "__main__":
    print("\n" + "=" * 60)
    print("Database Optimization Script")
    print("=" * 60 + "\n")

    asyncio.run(optimize_database())

    print("\n" + "=" * 60)
    print("Optimization completed!")
    print("=" * 60 + "\n")
