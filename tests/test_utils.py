"""Tests for utility modules"""

import pytest
import asyncio
from datetime import datetime

from src.utils.cache import CacheManager, cached, get_cache
from src.utils.retry import RetryConfig, retry_with_backoff


class TestCacheManager:
    """Test CacheManager functionality"""

    def test_cache_initialization(self):
        """Test cache manager initialization"""
        cache = CacheManager(max_size=100, default_ttl=60, enabled=True)
        assert cache._enabled is True
        assert cache._default_ttl == 60

    def test_cache_set_and_get(self):
        """Test basic cache set and get operations"""
        cache = CacheManager(max_size=100, default_ttl=60)
        cache.set("test_key", "test_value")
        assert cache.get("test_key") == "test_value"

    def test_cache_miss(self):
        """Test cache miss scenario"""
        cache = CacheManager(max_size=100, default_ttl=60)
        assert cache.get("non_existent_key") is None

    def test_cache_remove(self):
        """Test cache removal"""
        cache = CacheManager(max_size=100, default_ttl=60)
        cache.set("test_key", "test_value")
        cache.remove("test_key")
        assert cache.get("test_key") is None

    def test_cache_clear(self):
        """Test cache clearing"""
        cache = CacheManager(max_size=100, default_ttl=60)
        cache.set("key1", "value1")
        cache.set("key2", "value2")
        cache.clear()
        assert cache.get("key1") is None
        assert cache.get("key2") is None

    def test_cache_disabled(self):
        """Test cache when disabled"""
        cache = CacheManager(max_size=100, default_ttl=60, enabled=False)
        cache.set("test_key", "test_value")
        assert cache.get("test_key") is None

    def test_cache_stats(self):
        """Test cache statistics"""
        cache = CacheManager(max_size=100, default_ttl=60)
        cache.set("key1", "value1")
        stats = cache.get_stats()
        assert stats["enabled"] is True
        assert stats["size"] == 1
        assert stats["max_size"] == 100
        assert stats["ttl"] == 60

    def test_cached_decorator_sync(self):
        """Test cached decorator for sync functions"""
        cache = CacheManager(max_size=100, default_ttl=60)

        call_count = 0

        @cached(cache_instance=cache)
        def expensive_function(x: int) -> int:
            nonlocal call_count
            call_count += 1
            return x * 2

        # First call
        result1 = expensive_function(5)
        assert result1 == 10
        assert call_count == 1

        # Second call should use cache
        result2 = expensive_function(5)
        assert result2 == 10
        assert call_count == 1  # Should not increment

        # Different argument should call function
        result3 = expensive_function(10)
        assert result3 == 20
        assert call_count == 2

    @pytest.mark.asyncio
    async def test_cached_decorator_async(self):
        """Test cached decorator for async functions"""
        cache = CacheManager(max_size=100, default_ttl=60)

        call_count = 0

        @cached(cache_instance=cache)
        async def expensive_async_function(x: int) -> int:
            nonlocal call_count
            call_count += 1
            await asyncio.sleep(0.01)
            return x * 2

        # First call
        result1 = await expensive_async_function(5)
        assert result1 == 10
        assert call_count == 1

        # Second call should use cache
        result2 = await expensive_async_function(5)
        assert result2 == 10
        assert call_count == 1

    def test_get_cache_singleton(self):
        """Test global cache singleton"""
        cache1 = get_cache()
        cache2 = get_cache()
        assert cache1 is cache2


class TestRetryMechanism:
    """Test retry mechanism"""

    @pytest.mark.asyncio
    async def test_retry_success_on_first_attempt(self):
        """Test retry when function succeeds on first attempt"""
        call_count = 0

        @retry_with_backoff(config=RetryConfig(max_attempts=3))
        async def test_function():
            nonlocal call_count
            call_count += 1
            return "success"

        result = await test_function()
        assert result == "success"
        assert call_count == 1

    @pytest.mark.asyncio
    async def test_retry_success_after_failure(self):
        """Test retry when function fails then succeeds"""
        call_count = 0

        @retry_with_backoff(config=RetryConfig(max_attempts=3, min_wait=0.1))
        async def test_function():
            nonlocal call_count
            call_count += 1
            if call_count < 2:
                raise ConnectionError("Temporary failure")
            return "success"

        result = await test_function()
        assert result == "success"
        assert call_count == 2

    @pytest.mark.asyncio
    async def test_retry_exhausted(self):
        """Test retry when all attempts fail"""
        call_count = 0

        @retry_with_backoff(config=RetryConfig(max_attempts=3, min_wait=0.1))
        async def test_function():
            nonlocal call_count
            call_count += 1
            raise ConnectionError("Persistent failure")

        with pytest.raises(ConnectionError):
            await test_function()

        assert call_count == 3

    def test_retry_sync_function(self):
        """Test retry decorator with sync function"""
        call_count = 0

        @retry_with_backoff(config=RetryConfig(max_attempts=3, min_wait=0.1))
        def test_function():
            nonlocal call_count
            call_count += 1
            if call_count < 2:
                raise ConnectionError("Temporary failure")
            return "success"

        result = test_function()
        assert result == "success"
        assert call_count == 2

    @pytest.mark.asyncio
    async def test_retry_specific_exception(self):
        """Test retry only on specific exceptions"""
        call_count = 0

        @retry_with_backoff(
            config=RetryConfig(max_attempts=3, min_wait=0.1),
            exception_types=(ConnectionError,)
        )
        async def test_function():
            nonlocal call_count
            call_count += 1
            if call_count < 2:
                raise ConnectionError("Network error")
            raise ValueError("Logic error")

        with pytest.raises(ValueError):
            await test_function()

        # Should have retried on ConnectionError before raising ValueError
        assert call_count == 2
