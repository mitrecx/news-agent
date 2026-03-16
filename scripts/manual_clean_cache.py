"""手动清理过期缓存（用于本地开发）

本地开发环境不需要启动 Celery 服务，可以使用此脚本手动清理过期缓存。
"""

import asyncio
import asyncpg
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.agent.config import get_settings
from src.tools.weibo_cache import WeiboHotSearchCache


async def main():
    """手动清理过期缓存"""
    print("🧹 手动清理过期微博热搜缓存")
    print("=" * 60)

    # 创建连接池
    settings = get_settings()
    pool = await asyncpg.create_pool(
        host=settings.db_host,
        port=settings.db_port,
        user=settings.db_user,
        password=settings.db_password,
        database=settings.db_name,
        min_size=1,
        max_size=10
    )

    try:
        print(f"✓ 已连接数据库: {settings.db_name}\n")

        # 创建缓存管理器（传入连接池）
        cache = WeiboHotSearchCache(pool)

        # 获取清理前统计
        stats_before = await cache.get_stats()

        print(f"清理前:")
        print(f"  - 总缓存条目: {stats_before['total_entries']}")
        print(f"  - 有效缓存: {stats_before['active_entries']}")
        print(f"  - 过期缓存: {stats_before['expired_entries']}")
        print()

        # 执行清理
        print("开始清理...")
        deleted_count = await cache.delete_expired()
        print(f"✅ 清理完成: 删除了 {deleted_count} 条过期缓存")
        print()

        # 获取清理后统计
        stats_after = await cache.get_stats()

        print(f"清理后:")
        print(f"  - 总缓存条目: {stats_after['total_entries']}")
        print(f"  - 有效缓存: {stats_after['active_entries']}")
        print(f"  - 过期缓存: {stats_after['expired_entries']}")
        print()

        print("=" * 60)

    finally:
        await pool.close()
        print("\n✓ 数据库连接池已关闭")


if __name__ == "__main__":
    asyncio.run(main())
