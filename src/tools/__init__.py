"""Tools module - LangChain 工具集成.

This module provides LangChain tools for the news agent, including
Weibo hot search with caching support.
"""

import logging
import asyncio
import time
from typing import Optional
from datetime import datetime
from langchain_core.tools import tool
from .weibo import get_scraper

# 配置日志
logger = logging.getLogger(__name__)

# Cache configuration
CACHE_TTL = 300  # Cache time-to-live: 5 minutes
_cache: dict[str, tuple[str, float]] = {}  # {key: (result, timestamp)}


def _get_cache_key(limit: int) -> str:
    """Generate cache key for weibo hot search."""
    return f"weibo_hot_search_{limit}"


def _get_cached_result(limit: int) -> Optional[str]:
    """
    Get cached result if available and not expired.

    Args:
        limit: The limit parameter for the query

    Returns:
        Cached result if valid, None otherwise
    """
    cache_key = _get_cache_key(limit)
    if cache_key in _cache:
        result, timestamp = _cache[cache_key]
        if time.time() - timestamp < CACHE_TTL:
            age = int(time.time() - timestamp)
            logger.info(f"📦 Using cached weibo hot search (age: {age}s)")
            return result
        else:
            # Expired cache, remove it
            del _cache[cache_key]
    return None


def _set_cached_result(limit: int, result: str) -> None:
    """
    Store result in cache with current timestamp.

    Args:
        limit: The limit parameter for the query
        result: The result to cache
    """
    cache_key = _get_cache_key(limit)
    _cache[cache_key] = (result, time.time())
    logger.info(f"💾 Cached weibo hot search result (TTL: {CACHE_TTL}s)")


@tool
async def fetch_weibo_hot_search(limit: int = 40) -> str:
    """
    获取微博热搜榜 TOP 40

    使用场景：当用户询问微博热搜、热门话题、今日热点等

    Args:
        limit: 返回热搜数量，默认40条，最多50条

    Returns:
        格式化的热搜列表

    注意：工具返回结果已经是最终答案，直接原样返回给用户即可。
    """
    # Validate limit
    if limit < 1:
        limit = 10
    if limit > 50:
        limit = 50

    # Check cache first
    cached_result = _get_cached_result(limit)
    if cached_result:
        return cached_result

    # 打印日志
    logger.info(f"🔍 开始获取微博热搜，数量限制: {limit}")
    print(f"\n{'='*60}")
    print(f"📊 微博热搜工具调用")
    print(f"{'='*60}")
    print(f"⏰ 时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"📝 获取数量: {limit} 条")
    print(f"{'='*60}\n")

    scraper = get_scraper()
    try:
        result = await scraper.get_hot_search_summary(limit)

        # Cache the result
        _set_cached_result(limit, result)

        # 打印结果日志
        print(f"✅ 微博热搜获取成功")
        print(f"{'='*60}")
        print(result)
        print(f"{'='*60}\n")

        logger.info(f"✅ 成功获取微博热搜，返回 {result.count(chr(10))} 行数据")
        return result
    except Exception as e:
        error_msg = f"获取微博热搜失败: {e}"
        print(f"❌ {error_msg}")
        print(f"{'='*60}\n")
        logger.error(error_msg, exc_info=True)
        return error_msg


def clear_weibo_cache() -> None:
    """Clear the weibo hot search cache."""
    global _cache
    _cache.clear()
    logger.info("🗑️ Cleared weibo hot search cache")


def get_cache_stats() -> dict:
    """
    Get cache statistics.

    Returns:
        Dictionary with cache statistics
    """
    cache_keys = list(_cache.keys())
    stats = {
        "cached_queries": len(cache_keys),
        "ttl_seconds": CACHE_TTL,
        "queries": []
    }
    for key in cache_keys:
        result, timestamp = _cache[key]
        age = int(time.time() - timestamp)
        stats["queries"].append({
            "key": key,
            "age_seconds": age,
            "expired": age >= CACHE_TTL
        })
    return stats


# 导出所有工具
__all__ = [
    "fetch_weibo_hot_search",
    "clear_weibo_cache",
    "get_cache_stats"
]
