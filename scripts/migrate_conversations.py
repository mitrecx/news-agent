"""Add conversations and messages tables for dialog history"""

import asyncio
import asyncpg
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.agent.config import get_settings

settings = get_settings()


async def migrate():
    """Create conversations and messages tables"""
    conn = await asyncpg.connect(
        host=settings.db_host,
        port=settings.db_port,
        user=settings.db_user,
        password=settings.db_password,
        database=settings.db_name
    )

    try:
        print("Creating conversations table...")
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS conversations (
                id SERIAL PRIMARY KEY,
                user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                title VARCHAR(200) NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        print("✓ Conversations table created")

        print("Creating messages table...")
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS messages (
                id SERIAL PRIMARY KEY,
                conversation_id INTEGER NOT NULL REFERENCES conversations(id) ON DELETE CASCADE,
                role VARCHAR(20) NOT NULL CHECK (role IN ('user', 'assistant')),
                content TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        print("✓ Messages table created")

        print("Creating indexes...")
        await conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_conversations_user_id ON conversations(user_id)
        """)
        await conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_conversations_updated_at ON conversations(updated_at DESC)
        """)
        await conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_messages_conversation_id ON messages(conversation_id)
        """)
        await conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_messages_created_at ON messages(created_at)
        """)
        print("✓ Indexes created")

        print("\n✅ Migration completed!")

    except Exception as e:
        print(f"❌ Error: {e}")
        raise
    finally:
        await conn.close()


if __name__ == "__main__":
    asyncio.run(migrate())
