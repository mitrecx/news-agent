"""Initialize database with users table and test user"""

import asyncio
import asyncpg
import bcrypt
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.agent.config import get_settings

settings = get_settings()


def hash_password(password: str) -> str:
    """Hash a password using bcrypt"""
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(password.encode('utf-8'), salt).decode('utf-8')


async def init_database():
    """Initialize database schema and create test user"""

    # Connect to database
    conn = await asyncpg.connect(
        host=settings.db_host,
        port=settings.db_port,
        user=settings.db_user,
        password=settings.db_password,
        database=settings.db_name
    )

    try:
        print(f"Connected to database: {settings.db_name}")

        # Create users table
        print("Creating users table...")
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id SERIAL PRIMARY KEY,
                username VARCHAR(50) UNIQUE NOT NULL,
                email VARCHAR(100),
                hashed_password VARCHAR(255) NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        print("✓ Users table created")

        # Create index on username
        print("Creating index on username...")
        await conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_users_username ON users(username)
        """)
        print("✓ Index created")

        # Create conversations table
        print("\nCreating conversations table...")
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS conversations (
                id SERIAL PRIMARY KEY,
                user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                title VARCHAR(200) NOT NULL DEFAULT '新对话',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        print("✓ Conversations table created")

        # Create index for conversations
        print("Creating indexes for conversations...")
        await conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_conversations_user_id ON conversations(user_id)
        """)
        await conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_conversations_updated_at ON conversations(updated_at DESC)
        """)
        print("✓ Indexes created")

        # Create messages table
        print("\nCreating messages table...")
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

        # Create index for messages
        print("Creating index for messages...")
        await conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_messages_conversation_id ON messages(conversation_id)
        """)
        print("✓ Index created")

        # Check if test user exists
        print("\nChecking for test user...")
        existing_user = await conn.fetchval(
            "SELECT id FROM users WHERE username = $1",
            "test"
        )

        if existing_user:
            print("⚠ Test user already exists, skipping creation")
        else:
            # Create test user
            print("Creating test user...")
            hashed_password = hash_password("test")
            await conn.execute(
                """
                INSERT INTO users (username, email, hashed_password)
                VALUES ($1, $2, $3)
                """,
                "test",
                "test@example.com",
                hashed_password
            )
            print("✓ Test user created")
            print("  Username: test")
            print("  Password: test")

        print("\n✅ Database initialization completed!")

    except Exception as e:
        print(f"❌ Error: {e}")
        raise
    finally:
        await conn.close()


if __name__ == "__main__":
    asyncio.run(init_database())
