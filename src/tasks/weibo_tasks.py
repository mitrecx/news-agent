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

        # 5. 保存新增热搜（初始描述为空，同时保存URL）
        inserted_count = 0
        for item in new_items:
            saved = await cache.insert_initial(item.title, item.url)
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

    支持两种方案（通过配置切换）：
    1. 旧方案：使用 Selenium 爬虫获取微博内容（use_selenium_for_descriptions=True）
    2. 新方案：使用 HTTP 爬虫获取微博内容（use_selenium_for_descriptions=False，默认）

    注意：
    - 如果URL为空，直接返回失败
    - 如果无法获取微博内容，返回失败，不生成描述
    - 只使用真实的微博内容生成描述，不使用LLM猜测

    Args:
        title: 热搜标题
        url: 热搜链接
        rank: 热搜排名

    Returns:
        dict: 结果信息
    """
    from ..tools.weibo import get_scraper, HotSearchItem, WeiboScraper
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

        # 如果URL为空，无法获取内容，直接返回失败
        if not url:
            logger.warning(f"  ⚠️ URL为空，无法获取微博内容: {title}")
            return {
                'title': title,
                'rank': rank,
                'success': False,
                'description': None,
                'description_source': None,
                'error': 'URL is empty, cannot fetch content',
                'timestamp': datetime.now().isoformat()
            }

        # 方案选择：根据配置决定使用哪种方案
        if settings.use_selenium_for_descriptions:
            # ========== 旧方案：使用 Selenium 爬虫 ==========
            logger.info(f"  → 使用旧方案（Selenium 爬虫）")
            return await _fetch_with_selenium(title, url, rank, pool, settings)
        else:
            # ========== 新方案：使用 HTTP 爬虫 ==========
            logger.info(f"  → 使用新方案（HTTP 爬虫）")
            return await _fetch_with_http(title, url, rank, pool)

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


async def _fetch_with_selenium(title: str, url: str, rank: int, pool, settings):
    """
    旧方案：使用 Selenium 爬虫获取微博内容

    保留此函数作为备选方案，可以通过配置快速切换回旧方案
    """
    from ..tools.weibo import HotSearchItem, WeiboScraper
    from ..tools.weibo_cache import WeiboHotSearchCache
    from ..tools.llm_summary import summarize_weibo_content

    try:
        # 创建临时 HotSearchItem 对象
        item = HotSearchItem(
            rank=rank,
            title=title,
            url=url,
            hot_value="",
            category=""
        )

        # 使用 Selenium 爬虫获取内容
        scraper = WeiboScraper(use_selenium=True)
        scraper._cache_manager = WeiboHotSearchCache(pool)

        logger.debug(f"  → 使用 Selenium 爬虫访问: {url}")
        content = await scraper._fetch_item_content(item)

        if content:
            # 使用微博内容生成描述
            description = await summarize_weibo_content(title, content)
            if description:
                # 保存到数据库
                cache = WeiboHotSearchCache(pool)
                await cache.set(
                    title=title,
                    description=description,
                    description_source="weibo_selenium"
                )

                logger.info(f"✅ 描述生成成功（Selenium）：[{rank}] {title[:30]}...")
                logger.debug(f"  描述: {description[:100]}...")

                return {
                    'title': title,
                    'rank': rank,
                    'success': True,
                    'description': description,
                    'description_source': 'weibo_selenium',
                    'timestamp': datetime.now().isoformat()
                }

        # Selenium 失败，返回失败结果
        logger.warning(f"⚠️ Selenium 爬取失败：[{rank}] {title[:30]}...")
        return {
            'title': title,
            'rank': rank,
            'success': False,
            'description': None,
            'description_source': None,
            'timestamp': datetime.now().isoformat()
        }

    except Exception as e:
        logger.warning(f"  ⚠️ Selenium 爬取异常: {e}")
        return {
            'title': title,
            'rank': rank,
            'success': False,
            'description': None,
            'description_source': None,
            'error': str(e),
            'timestamp': datetime.now().isoformat()
        }


async def _fetch_with_http(title: str, url: str, rank: int, pool):
    """
    新方案：使用 HTTP 爬虫获取微博内容

    如果无法获取内容，则返回失败（不再使用LLM降级）
    """
    from ..tools.weibo_cache import WeiboHotSearchCache
    from ..tools.llm_summary import summarize_weibo_content
    from ..agent.config import get_settings

    settings = get_settings()

    # 使用 HTTP 爬虫尝试获取内容
    try:
        import httpx
        from bs4 import BeautifulSoup

        logger.debug(f"  → 使用 HTTP 爬虫访问: {url}")

        # 配置更真实的请求头，包含Cookie
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'Referer': 'https://weibo.com'
        }

        # 如果配置了Cookie，添加到请求头
        if settings.weibo_cookie:
            headers['Cookie'] = settings.weibo_cookie
            logger.debug("  → 使用微博Cookie")
        else:
            logger.debug("  → 未配置Cookie，可能无法绕过反爬")

        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(url, headers=headers, follow_redirects=True)
            if response.status_code == 200:
                html = response.text
                soup = BeautifulSoup(html, 'html.parser')

                # 尝试提取微博内容
                # 查找微博正文
                content_elem = soup.find('div', class_='WB_text')
                if content_elem:
                    content = content_elem.get_text(strip=True)
                    logger.debug(f"  ✓ HTTP 爬取成功，内容长度: {len(content)} 字符")
                else:
                    # 如果没有找到正文，尝试其他选择器
                    paragraphs = soup.find_all('p')
                    content = ' '.join([p.get_text(strip=True) for p in paragraphs if p.get_text(strip=True)])
                    if content:
                        logger.debug(f"  ✓ 提取到备用内容，长度: {len(content)} 字符")
                    else:
                        logger.warning(f"  ⚠️ 未找到微博内容")
                        content = None
            else:
                logger.warning(f"  ⚠️ HTTP 请求失败: {response.status_code}")
                content = None

    except Exception as e:
        logger.warning(f"  ⚠️ HTTP 爬取失败: {e}")
        content = None

    # 生成描述
    if content:
        # 使用微博内容生成描述
        description = await summarize_weibo_content(title, content)
        if description:
            # 保存到数据库
            cache = WeiboHotSearchCache(pool)
            await cache.set(
                title=title,
                description=description,
                description_source="weibo_http"
            )

            logger.info(f"✅ 描述生成成功：[{rank}] {title[:30]}... (weibo_http)")
            logger.debug(f"  描述: {description[:100]}...")

            return {
                'title': title,
                'rank': rank,
                'success': True,
                'description': description,
                'description_source': 'weibo_http',
                'timestamp': datetime.now().isoformat()
            }

    # 无法获取内容，返回失败
    logger.warning(f"⚠️ 无法获取微博内容，描述生成失败：[{rank}] {title[:30]}...")

    return {
        'title': title,
        'rank': rank,
        'success': False,
        'description': None,
        'description_source': None,
        'error': 'Failed to fetch weibo content',
        'timestamp': datetime.now().isoformat()
    }


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
