"""创建微博热搜缓存表"""

import asyncio
import asyncpg
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.agent.config import get_settings

settings = get_settings()


async def migrate():
    """执行数据库迁移"""

    # Connect to database
    conn = await asyncpg.connect(
        host=settings.db_host,
        port=settings.db_port,
        user=settings.db_user,
        password=settings.db_password,
        database=settings.db_name
    )

    try:
        print(f"✓ Connected to database: {settings.db_name}")

        # Create weibo_hot_search_cache table
        print("\nCreating weibo_hot_search_cache table...")
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS weibo_hot_search_cache (
                id SERIAL PRIMARY KEY,
                title_hash VARCHAR(64) NOT NULL UNIQUE,
                title VARCHAR(500) NOT NULL,
                description TEXT NOT NULL,
                description_source VARCHAR(50) NOT NULL,
                created_at TIMESTAMP NOT NULL DEFAULT NOW(),
                updated_at TIMESTAMP NOT NULL DEFAULT NOW(),
                expires_at TIMESTAMP NOT NULL,
                CONSTRAINT check_expires_after_created CHECK (expires_at > created_at)
            )
        """)
        print("✓ Table created")

        # Create indexes
        print("\nCreating indexes...")
        await conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_weibo_cache_title_hash
            ON weibo_hot_search_cache(title_hash)
        """)

        await conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_weibo_cache_expires_at
            ON weibo_hot_search_cache(expires_at)
        """)

        await conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_weibo_cache_created_at
            ON weibo_hot_search_cache(created_at DESC)
        """)
        print("✓ Indexes created")

        # Create cleanup function
        print("\nCreating cleanup function...")
        await conn.execute("""
            CREATE OR REPLACE FUNCTION clean_expired_weibo_cache()
            RETURNS void AS $$
            BEGIN
                DELETE FROM weibo_hot_search_cache
                WHERE expires_at < NOW();
                RAISE NOTICE 'Deleted % expired cache entries',
                    (SELECT ROW_COUNT);
            END;
            $$ LANGUAGE plpgsql
        """)
        print("✓ Cleanup function created")

        # Show table info
        print("\n" + "=" * 60)
        print("Table Information")
        print("=" * 60)

        stats = await conn.fetchrow("""
            SELECT
                COUNT(*) as total_entries,
                COUNT(*) FILTER (WHERE expires_at > NOW()) as active_entries,
                COUNT(*) FILTER (WHERE expires_at <= NOW()) as expired_entries
            FROM weibo_hot_search_cache
        """)

        print(f"Total entries: {stats['total_entries']}")
        print(f"Active entries: {stats['active_entries']}")
        print(f"Expired entries: {stats['expired_entries']}")

        print("\n" + "=" * 60)
        print("✅ Migration completed successfully!")
        print("=" * 60)

    except Exception as e:
        print(f"❌ Migration failed: {e}")
        raise
    finally:
        await conn.close()


if __name__ == "__main__":
    asyncio.run(migrate())
