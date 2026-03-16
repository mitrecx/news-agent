"""Celery 任务定义"""

import asyncio
import asyncpg
import logging
from celery import shared_task
from datetime import datetime

logger = logging.getLogger(__name__)


async def _clean_expired_cache_async():
    """
    异步清理过期缓存的内部函数
    """
    from ..tools.weibo_cache import WeiboHotSearchCache
    from ..agent.config import get_settings

    settings = get_settings()

    # 创建连接池
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
        # 创建缓存管理器并执行清理（传入连接池）
        cache = WeiboHotSearchCache(pool)
        deleted_count = await cache.delete_expired()
        return deleted_count

    finally:
        await pool.close()


@shared_task(
    name='src.tasks.cache_tasks.clean_expired_cache',
    bind=True,
    max_retries=3,
    default_retry_delay=60,
)
def clean_expired_cache(self):
    """
    清理过期的微博热搜缓存
    定时任务：每10分钟执行一次
    """
    try:
        # 使用 asyncio 运行异步清理函数
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        try:
            # 执行清理
            deleted_count = loop.run_until_complete(
                _clean_expired_cache_async()
            )

            logger.info(f"✅ Celery 清理任务完成：删除 {deleted_count} 条过期缓存")
            return {
                'status': 'success',
                'deleted_count': deleted_count,
                'timestamp': datetime.now().isoformat()
            }

        finally:
            loop.close()

    except Exception as e:
        logger.error(f"❌ Celery 清理任务失败: {e}", exc_info=True)

        # 重试逻辑
        if self.request.retries < self.max_retries:
            logger.info(f"⏳ 60秒后重试 (第 {self.request.retries + 1}/{self.max_retries} 次)")
            raise self.retry(exc=e)

        return {
            'status': 'failed',
            'error': str(e),
            'timestamp': datetime.now().isoformat()
        }
