"""微博热搜定时抓取任务"""

import asyncio
import asyncpg
import logging
from celery import shared_task
from datetime import datetime

logger = logging.getLogger(__name__)


async def _fetch_and_save_hot_search_titles_async(limit: int = 50):
    """
    异步函数：抓取并保存热搜标题

    Args:
        limit: 抓取热搜数量

    Returns:
        dict: 统计信息
    """
    from ..tools.weibo import get_scraper, HotSearchItem, WeiboScraper
    from ..tools.weibo_cache import WeiboHotSearchCache
    from ..agent.config import get_settings

    settings = get_settings()

    # 创建数据库连接池
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
        logger.info(f"🔍 开始抓取微博热搜标题，数量: {limit}")

        # 1. 获取爬虫实例（不使用全局单例的缓存管理器）
        scraper = get_scraper()

        # 重置缓存管理器，使用当前线程的连接池
        scraper._cache_manager = WeiboHotSearchCache(pool)

        # 2. 只抓取标题（不获取描述）
        items = await scraper.fetch_hot_search(limit=limit, fetch_descriptions=False)
        logger.info(f"✅ 抓取到 {len(items)} 条热搜")

        # 3. 去重：检查哪些热搜已存在
        cache = WeiboHotSearchCache(pool)
        titles = [item.title for item in items]
        existing_titles = await cache.batch_exists(titles)
        logger.info(f"✓ 已存在 {len(existing_titles)} 条热搜")

        # 4. 筛选出新增热搜
        new_items = [item for item in items if item.title not in existing_titles]
        logger.info(f"✓ 新增 {len(new_items)} 条热搜")

        # 构建每条热搜的状态详情
        items_status = []
        for item in items:
            is_new = item.title not in existing_titles
            items_status.append({
                'title': item.title,
                'rank': item.rank,
                'status': 'new' if is_new else 'duplicate',
                'saved': False
            })

        if not new_items:
            logger.info("✅ 没有新增热搜，任务完成")
            return {
                'total_fetched': len(items),
                'new_items': 0,
                'cached_items': len(existing_titles),
                'description_tasks_queued': 0,
                'items': items_status
            }

        # 5. 保存新增热搜（初始描述为空）
        inserted_count = 0
        for item in new_items:
            saved = await cache.insert_initial(item.title)
            if saved:
                inserted_count += 1
                # 更新状态
                for status in items_status:
                    if status['title'] == item.title:
                        status['saved'] = True
                        break

        logger.info(f"✅ 成功保存 {inserted_count} 条新增热搜")

        # 6. 为每条新增热搜触发异步描述生成任务
        tasks_queued = 0
        for item in new_items:
            try:
                fetch_and_update_description.delay(
                    title=item.title,
                    url=item.url,
                    rank=item.rank
                )
                tasks_queued += 1
            except Exception as e:
                logger.warning(f"⚠️  无法触发描述任务: {item.title}, 错误: {e}")
                # Celery 不可用时继续处理其他任务

        if tasks_queued > 0:
            logger.info(f"✅ 已触发 {tasks_queued} 个描述生成任务")
        else:
            logger.info("ℹ️  描述生成任务未触发（Celery 不可用，请使用批量抓取描述功能）")

        return {
            'total_fetched': len(items),
            'new_items': len(new_items),
            'cached_items': len(existing_titles),
            'description_tasks_queued': tasks_queued,
            'items': items_status,
            'timestamp': datetime.now().isoformat()
        }

    finally:
        await pool.close()


@shared_task(
    name='src.tasks.weibo_tasks.fetch_and_save_hot_search_titles',
    bind=True,
    max_retries=3,
    default_retry_delay=300,  # 5分钟后重试
)
def fetch_and_save_hot_search_titles(self, limit: int = 50):
    """
    定时任务：每小时抓取微博热搜标题并保存到数据库

    流程：
    1. 使用 asyncio 运行异步爬虫
    2. 调用 fetch_hot_search(fetch_descriptions=False) 只获取标题
    3. 去重：检查 title_hash 是否已存在
    4. 只保存新增热搜（description 初始为空）
    5. 为每条新增热搜触发异步描述生成任务

    Args:
        limit: 抓取热搜数量，默认50条

    Returns:
        dict: {
            'total_fetched': int,      # 抓取到的总数
            'new_items': int,          # 新增热搜数
            'cached_items': int,       # 已缓存（跳过）数
            'description_tasks_queued': int  # 触发的描述任务数
        }
    """
    try:
        # 使用 asyncio 运行异步函数
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        try:
            result = loop.run_until_complete(
                _fetch_and_save_hot_search_titles_async(limit)
            )

            logger.info(f"✅ 微博热搜标题抓取任务完成："
                       f"总计 {result['total_fetched']} 条，"
                       f"新增 {result['new_items']} 条，"
                       f"已存在 {result['cached_items']} 条，"
                       f"触发 {result['description_tasks_queued']} 个描述任务")

            return result

        finally:
            loop.close()

    except Exception as e:
        logger.error(f"❌ 微博热搜标题抓取任务失败: {e}", exc_info=True)

        # 重试逻辑
        if self.request.retries < self.max_retries:
            logger.info(f"⏳ 5分钟后重试 (第 {self.request.retries + 1}/{self.max_retries} 次)")
            raise self.retry(exc=e)

        return {
            'status': 'failed',
            'error': str(e),
            'timestamp': datetime.now().isoformat()
        }


async def _fetch_and_update_description_async(title: str, url: str, rank: int):
    """
    异步函数：抓取并更新单条热搜描述

    Args:
        title: 热搜标题
        url: 热搜链接
        rank: 热搜排名

    Returns:
        dict: 结果信息
    """
    from ..tools.weibo import get_scraper, HotSearchItem
    from ..tools.weibo_cache import WeiboHotSearchCache
    from ..tools.llm_summary import summarize_weibo_content
    from ..agent.config import get_settings

    settings = get_settings()

    # 创建数据库连接池
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
        logger.info(f"📝 开始为热搜生成描述：[{rank}] {title}")

        # 获取爬虫实例（重置缓存管理器以使用当前线程的连接池）
        scraper = get_scraper()
        scraper._cache_manager = WeiboHotSearchCache(pool)

        # 如果URL为空，重新抓取热搜列表来获取URL
        if not url:
            logger.info(f"  URL为空，重新抓取热搜列表获取URL: {title}")
            items = await scraper.fetch_hot_search(limit=50, fetch_descriptions=False)
            # 查找匹配的热搜
            found = False
            for item in items:
                if item.title == title:
                    url = item.url
                    rank = item.rank
                    found = True
                    logger.info(f"  ✓ 找到匹配热搜，URL: {url}")
                    break

            if not found:
                logger.warning(f"  ✗ 未在热搜列表中找到: {title}")
                return {
                    'title': title,
                    'rank': rank,
                    'success': False,
                    'description': None,
                    'description_source': None,
                    'error': 'Title not found in hot search list',
                    'timestamp': datetime.now().isoformat()
                }

        # 1. 创建临时 HotSearchItem 对象
        item = HotSearchItem(
            rank=rank,
            title=title,
            url=url,
            hot_value="",
            category=""
        )

        # 2. 尝试爬取微博内容
        content = await scraper._fetch_item_content(item)

        # 3. 生成描述
        if content:
            logger.debug(f"  ✓ 爬取到微博内容，长度: {len(content)} 字符")
            description = await summarize_weibo_content(title, content)
            if description:
                description_source = "weibo_detail"
            else:
                description = None
                description_source = None
        else:
            # 未获取到内容，描述留空
            logger.warning(f"  ⚠️ 未获取到微博内容，描述留空: {title}")
            description = None
            description_source = None

        # 5. 保存到数据库（仅当有描述时）
        if description:
            cache = WeiboHotSearchCache(pool)
            await cache.set(
                title=title,
                description=description,
                description_source=description_source
            )

            logger.info(f"✅ 描述生成成功：[{rank}] {title[:30]}... ({description_source})")
            logger.debug(f"  描述: {description[:100]}...")

            return {
                'title': title,
                'rank': rank,
                'success': True,
                'description': description,
                'description_source': description_source,
                'timestamp': datetime.now().isoformat()
            }
        else:
            logger.warning(f"⚠️ 描述生成失败：[{rank}] {title[:30]}... (无描述)")

            return {
                'title': title,
                'rank': rank,
                'success': False,
                'description': None,
                'description_source': None,
                'timestamp': datetime.now().isoformat()
            }

    except Exception as e:
        logger.error(f"❌ 描述生成失败：{title}, 错误: {e}", exc_info=True)

        # 描述留空，不使用降级方案
        return {
            'title': title,
            'rank': rank,
            'success': False,
            'description': None,
            'description_source': None,
            'error': str(e),
            'timestamp': datetime.now().isoformat()
        }

    finally:
        await pool.close()


@shared_task(
    name='src.tasks.weibo_tasks.fetch_and_update_description',
    bind=True,
    max_retries=3,
    default_retry_delay=60,  # 1分钟后重试
)
def fetch_and_update_description(self, title: str, url: str, rank: int):
    """
    异步任务：为单条热搜抓取描述并更新数据库

    Args:
        title: 热搜标题
        url: 热搜链接
        rank: 热搜排名

    流程：
    1. 调用 WeiboScraper._fetch_item_content() 爬取微博内容
    2. 调用 LLM 生成描述（summarize_weibo_content）
    3. 更新数据库记录（使用 WeiboHotSearchCache.set()）
    4. 失败时自动重试（最多3次），描述留空

    Returns:
        dict: {
            'title': str,
            'rank': int,
            'success': bool,
            'description': str | None,
            'description_source': str | None,  # 'weibo_detail' | None
            'timestamp': str
        }
    """
    try:
        # 使用 asyncio 运行异步函数
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        try:
            result = loop.run_until_complete(
                _fetch_and_update_description_async(title, url, rank)
            )

            if result['success']:
                logger.info(f"✅ 热搜描述任务成功：[{rank}] {title[:30]}...")
            else:
                logger.warning(f"⚠️ 热搜描述任务失败：[{rank}] {title[:30]}...")

            return result

        finally:
            loop.close()

    except Exception as e:
        logger.error(f"❌ 热搜描述任务异常：{title}, 错误: {e}", exc_info=True)

        # 重试逻辑
        if self.request.retries < self.max_retries:
            logger.info(f"⏳ 1分钟后重试 (第 {self.request.retries + 1}/{self.max_retries} 次)")
            raise self.retry(exc=e)

        return {
            'title': title,
            'rank': rank,
            'success': False,
            'description': None,
            'description_source': 'error',
            'error': str(e),
            'retries': self.request.retries,
            'timestamp': datetime.now().isoformat()
        }
