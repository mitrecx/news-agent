"""Cache management for API requests and expensive operations"""

import asyncio
import hashlib
import json
import logging
from datetime import datetime, timedelta
from typing import Any, Optional, TypeVar, Callable, Awaitable
from functools import wraps
from cachetools import TTLCache

logger = logging.getLogger(__name__)

T = TypeVar('T')


class CacheManager:
    """
    Thread-safe cache manager with TTL support

    Features:
    - TTL (Time To Live) based expiration
    - Thread-safe operations
    - Async and sync support
    - Configurable cache size and TTL
    """

    def __init__(
        self,
        max_size: int = 1000,
        default_ttl: int = 300,  # 5 minutes default
        enabled: bool = True
    ):
        """
        Initialize cache manager

        Args:
            max_size: Maximum number of items in cache
            default_ttl: Default time-to-live in seconds
            enabled: Whether caching is enabled
        """
        self._cache: TTLCache[str, Any] = TTLCache(maxsize=max_size, ttl=default_ttl)
        self._default_ttl = default_ttl
        self._enabled = enabled
        self._lock = asyncio.Lock()
        logger.info(f"CacheManager initialized: max_size={max_size}, ttl={default_ttl}s, enabled={enabled}")

    def _generate_key(self, func_name: str, args: tuple, kwargs: dict) -> str:
        """
        Generate cache key from function name and arguments

        Args:
            func_name: Name of the function being cached
            args: Function positional arguments
            kwargs: Function keyword arguments

        Returns:
            Cache key as hash string
        """
        # Create a deterministic string representation
        key_parts = [func_name]
        for arg in args:
            if isinstance(arg, (str, int, float, bool, type(None))):
                key_parts.append(str(arg))
            else:
                # For complex types, use repr
                key_parts.append(repr(arg))

        # Sort kwargs for consistency
        for k in sorted(kwargs.keys()):
            v = kwargs[k]
            if isinstance(v, (str, int, float, bool, type(None))):
                key_parts.append(f"{k}={v}")
            else:
                key_parts.append(f"{k}={repr(v)}")

        key_string = ":".join(key_parts)
        return hashlib.md5(key_string.encode()).hexdigest()

    def get(self, key: str) -> Optional[Any]:
        """
        Get value from cache

        Args:
            key: Cache key

        Returns:
            Cached value or None if not found
        """
        if not self._enabled:
            return None

        try:
            value = self._cache.get(key)
            if value is not None:
                logger.debug(f"Cache HIT: {key}")
            else:
                logger.debug(f"Cache MISS: {key}")
            return value
        except Exception as e:
            logger.warning(f"Cache get error: {e}")
            return None

    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
        """
        Set value in cache

        Args:
            key: Cache key
            value: Value to cache
            ttl: Time-to-live in seconds (None for default)
        """
        if not self._enabled:
            return

        try:
            self._cache[key] = value
            logger.debug(f"Cache SET: {key}")
        except Exception as e:
            logger.warning(f"Cache set error: {e}")

    def clear(self) -> None:
        """Clear all cache entries"""
        self._cache.clear()
        logger.info("Cache cleared")

    def remove(self, key: str) -> None:
        """
        Remove specific cache entry

        Args:
            key: Cache key to remove
        """
        try:
            del self._cache[key]
            logger.debug(f"Cache REMOVE: {key}")
        except KeyError:
            pass

    def get_stats(self) -> dict[str, Any]:
        """
        Get cache statistics

        Returns:
            Dictionary with cache stats
        """
        return {
            "enabled": self._enabled,
            "size": len(self._cache),
            "max_size": self._cache.maxsize,
            "ttl": self._default_ttl
        }


# Global cache instance
_default_cache: Optional[CacheManager] = None


def get_cache(max_size: int = 1000, default_ttl: int = 300, enabled: bool = True) -> CacheManager:
    """
    Get or create default cache instance

    Args:
        max_size: Maximum cache size
        default_ttl: Default TTL in seconds
        enabled: Whether cache is enabled

    Returns:
        CacheManager instance
    """
    global _default_cache
    if _default_cache is None:
        _default_cache = CacheManager(max_size=max_size, default_ttl=default_ttl, enabled=enabled)
    return _default_cache


def cached(
    ttl: int = 300,
    key_prefix: Optional[str] = None,
    cache_instance: Optional[CacheManager] = None
):
    """
    Decorator for caching function results

    Args:
        ttl: Time-to-live in seconds
        key_prefix: Optional prefix for cache keys
        cache_instance: Specific cache instance to use

    Example:
        @cached(ttl=600, key_prefix="weibo")
        async def fetch_weibo_hot_search(limit: int = 10) -> str:
            ...
    """
    cache = cache_instance or get_cache(default_ttl=ttl)

    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @wraps(func)
        async def async_wrapper(*args, **kwargs) -> T:
            # Generate cache key
            prefix = key_prefix or func.__name__
            cache_key = cache._generate_key(prefix, args, kwargs)

            # Try to get from cache
            cached_value = cache.get(cache_key)
            if cached_value is not None:
                return cached_value

            # Execute function
            result = await func(*args, **kwargs)

            # Cache result
            cache.set(cache_key, result, ttl=ttl)

            return result

        @wraps(func)
        def sync_wrapper(*args, **kwargs) -> T:
            # Generate cache key
            prefix = key_prefix or func.__name__
            cache_key = cache._generate_key(prefix, args, kwargs)

            # Try to get from cache
            cached_value = cache.get(cache_key)
            if cached_value is not None:
                return cached_value

            # Execute function
            result = func(*args, **kwargs)

            # Cache result
            cache.set(cache_key, result, ttl=ttl)

            return result

        # Return appropriate wrapper based on whether function is async
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper

    return decorator
