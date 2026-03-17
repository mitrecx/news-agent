"""微博热搜描述缓存管理"""

import hashlib
import logging
from datetime import datetime, timedelta
from typing import Optional

logger = logging.getLogger(__name__)


class WeiboHotSearchCache:
    """微博热搜描述缓存管理器"""

    # 缓存有效期：永久（100年）
    CACHE_TTL = timedelta(days=365*100)  # 永久缓存

    def __init__(self, pool=None):
        """
        初始化缓存管理器

        Args:
            pool: asyncpg.Pool 数据库连接池（可选，如果不提供则创建新的连接）
        """
        self.pool = pool
        self._own_connection = None

    async def _get_connection(self):
        """获取数据库连接（如果是池则返回acquire上下文）"""
        if self.pool:
            # 返回 acquire 上下文管理器
            return self.pool.acquire()
        else:
            # 如果没有连接池，创建新的连接
            if self._own_connection is None:
                from ..agent.config import get_settings
                settings = get_settings()
                import asyncpg
                self._own_connection = await asyncpg.connect(
                    host=settings.db_host,
                    port=settings.db_port,
                    user=settings.db_user,
                    password=settings.db_password,
                    database=settings.db_name
                )
            # 对于直接连接，返回一个模拟上下文管理器
            class _ConnectionContextManager:
                def __init__(self, conn):
                    self.conn = conn
                async def __aenter__(self):
                    return self.conn
                async def __aexit__(self, *args):
                    pass
            return _ConnectionContextManager(self._own_connection)

    async def close(self):
        """关闭拥有的连接"""
        if self._own_connection:
            await self._own_connection.close()
            self._own_connection = None

    @staticmethod
    def hash_title(title: str) -> str:
        """
        生成标题的 SHA256 hash

        Args:
            title: 热搜标题

        Returns:
            SHA256 hash 字符串（64字符）
        """
        return hashlib.sha256(title.encode('utf-8')).hexdigest()

    async def get(self, title: str) -> Optional[dict]:
        """
        获取热搜描述缓存

        Args:
            title: 热搜标题

        Returns:
            缓存数据字典，如果不存在或已过期返回 None
        """
        async with await self._get_connection() as conn:
            title_hash = self.hash_title(title)

            query = """
                SELECT title, description, description_source,
                       created_at, updated_at, expires_at
                FROM weibo_hot_search_cache
                WHERE title_hash = $1
                  AND expires_at > NOW()
            """

            row = await conn.fetchrow(query, title_hash)

            if row:
                logger.debug(f"✓ Cache hit: {title[:30]}...")
                return {
                    'title': row['title'],
                    'description': row['description'],
                    'description_source': row['description_source'],
                    'created_at': row['created_at'],
                    'updated_at': row['updated_at'],
                    'expires_at': row['expires_at'],
                }

            logger.debug(f"✗ Cache miss: {title[:30]}...")
            return None

    async def set(
        self,
        title: str,
        description: str,
        description_source: str = "llm"
    ) -> None:
        """
        设置热搜描述缓存

        Args:
            title: 热搜标题
            description: 描述内容
            description_source: 描述来源（weibo_detail/llm/fallback）
        """
        async with await self._get_connection() as conn:
            title_hash = self.hash_title(title)
            now = datetime.now()
            expires_at = now + self.CACHE_TTL

            # 使用 UPSERT（PostgreSQL 特有）
            query = """
                INSERT INTO weibo_hot_search_cache
                    (title_hash, title, description, description_source,
                     created_at, updated_at, expires_at)
                VALUES ($1, $2, $3, $4, $5, $6, $7)
                ON CONFLICT (title_hash)
                DO UPDATE SET
                    description = EXCLUDED.description,
                    description_source = EXCLUDED.description_source,
                    updated_at = EXCLUDED.updated_at,
                    expires_at = EXCLUDED.expires_at
            """

            await conn.execute(
                query,
                title_hash, title, description, description_source,
                now, now, expires_at
            )

            logger.info(f"✓ Cached: {title[:30]}... (expires at {expires_at.strftime('%H:%M:%S')})")

    async def batch_get(self, titles: list[str]) -> dict[str, dict]:
        """
        批量获取缓存

        Args:
            titles: 热搜标题列表

        Returns:
            标题 -> 缓存数据的字典
        """
        async with await self._get_connection() as conn:
            title_hashes = [self.hash_title(title) for title in titles]

            query = """
                SELECT title_hash, title, description, description_source,
                       created_at, updated_at, expires_at
                FROM weibo_hot_search_cache
                WHERE title_hash = ANY($1::varchar(64)[])
                  AND expires_at > NOW()
            """

            rows = await conn.fetch(query, title_hashes)

            # 构建 {title: cache_data} 字典
            cache_map = {
                row['title']: {
                    'description': row['description'],
                    'description_source': row['description_source'],
                    'created_at': row['created_at'],
                    'updated_at': row['updated_at'],
                    'expires_at': row['expires_at'],
                }
                for row in rows
            }

            logger.info(f"✓ Batch cache: {len(cache_map)}/{len(titles)} hits")
            return cache_map

    async def batch_set(self, items: list) -> None:
        """
        批量设置缓存

        Args:
            items: HotSearchItem 对象列表
        """
        async with await self._get_connection() as conn:
            now = datetime.now()
            expires_at = now + self.CACHE_TTL

            # 批量插入
            query = """
                INSERT INTO weibo_hot_search_cache
                    (title_hash, title, description, description_source,
                     created_at, updated_at, expires_at)
                VALUES ($1, $2, $3, $4, $5, $6, $7)
                ON CONFLICT (title_hash)
                DO UPDATE SET
                    description = EXCLUDED.description,
                    description_source = EXCLUDED.description_source,
                    updated_at = EXCLUDED.updated_at,
                    expires_at = EXCLUDED.expires_at
            """

            # 使用事务批量执行
            async with conn.transaction():
                for item in items:
                    title_hash = self.hash_title(item.title)
                    await conn.execute(
                        query,
                        title_hash,
                        item.title,
                        item.description,
                        item.description_source or "llm",
                        now,
                        now,
                        expires_at
                    )

            logger.info(f"✓ Batch cached {len(items)} items")

    async def delete_expired(self) -> int:
        """
        删除过期的缓存

        Returns:
            删除的行数
        """
        async with await self._get_connection() as conn:
            result = await conn.execute(
                "DELETE FROM weibo_hot_search_cache WHERE expires_at < NOW()"
            )

            # 解析 "DELETE n" 返回值
            count = int(result.split()[-1])
            logger.info(f"✓ Deleted {count} expired cache entries")
            return count

    async def get_stats(self) -> dict:
        """
        获取缓存统计信息

        Returns:
            包含缓存统计的字典
        """
        async with await self._get_connection() as conn:
            stats = await conn.fetchrow("""
                SELECT
                    COUNT(*) as total_entries,
                    COUNT(*) FILTER (WHERE expires_at > NOW()) as active_entries,
                    COUNT(*) FILTER (WHERE expires_at <= NOW()) as expired_entries,
                    COUNT(*) FILTER (WHERE created_at > NOW() - INTERVAL '1 hour') as created_last_hour,
                    COUNT(*) FILTER (WHERE description_source = 'weibo_detail') as from_weibo,
                    COUNT(*) FILTER (WHERE description_source = 'llm') as from_llm,
                    COUNT(*) FILTER (WHERE description_source = 'fallback') as from_fallback
                FROM weibo_hot_search_cache
            """)

            return dict(stats)
