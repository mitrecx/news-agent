"""Retry mechanism with exponential backoff"""

import asyncio
import logging
from typing import Any, Callable, Optional, TypeVar, Type
from functools import wraps
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
    before_sleep_log,
    after_log
)

logger = logging.getLogger(__name__)

T = TypeVar('T')


class RetryConfig:
    """Configuration for retry behavior"""

    def __init__(
        self,
        max_attempts: int = 3,
        min_wait: float = 1.0,
        max_wait: float = 60.0,
        exponential_base: int = 2,
        retry_on_exception: Optional[Type[Exception]] = None
    ):
        """
        Initialize retry configuration

        Args:
            max_attempts: Maximum number of retry attempts
            min_wait: Minimum wait time between retries in seconds
            max_wait: Maximum wait time between retries in seconds
            exponential_base: Base for exponential backoff
            retry_on_exception: Exception type to retry on (None for all)
        """
        self.max_attempts = max_attempts
        self.min_wait = min_wait
        self.max_wait = max_wait
        self.exponential_base = exponential_base
        self.retry_on_exception = retry_on_exception


def retry_with_backoff(
    config: Optional[RetryConfig] = None,
    exception_types: Optional[tuple[Type[Exception], ...]] = None
):
    """
    Decorator for retrying functions with exponential backoff

    Args:
        config: Retry configuration (None for default)
        exception_types: Tuple of exception types to retry on

    Example:
        @retry_with_backoff(max_attempts=3, exception_types=(ConnectionError, TimeoutError))
        async def fetch_data(url: str) -> dict:
            ...

        @retry_with_backoff()
        def process_request() -> str:
            ...
    """
    if config is None:
        config = RetryConfig()

    if exception_types is None:
        # Default: retry on common network/IO errors
        exception_types = (
            ConnectionError,
            TimeoutError,
            OSError,
        )

    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @wraps(func)
        async def async_wrapper(*args, **kwargs) -> T:
            # Use tenacity for async retry logic
            async def _attempt() -> T:
                return await func(*args, **kwargs)

            # Retry logic
            last_exception = None
            for attempt in range(1, config.max_attempts + 1):
                try:
                    return await _attempt()
                except exception_types as e:
                    last_exception = e
                    if attempt < config.max_attempts:
                        # Calculate wait time with exponential backoff
                        wait_time = min(
                            config.min_wait * (config.exponential_base ** (attempt - 1)),
                            config.max_wait
                        )
                        logger.warning(
                            f"Attempt {attempt}/{config.max_attempts} failed for {func.__name__}: {e}. "
                            f"Retrying in {wait_time:.1f}s..."
                        )
                        await asyncio.sleep(wait_time)
                    else:
                        logger.error(
                            f"All {config.max_attempts} attempts failed for {func.__name__}"
                        )

            # If we get here, all attempts failed
            raise last_exception

        @wraps(func)
        def sync_wrapper(*args, **kwargs) -> T:
            # Use tenacity for sync retry logic
            last_exception = None
            for attempt in range(1, config.max_attempts + 1):
                try:
                    return func(*args, **kwargs)
                except exception_types as e:
                    last_exception = e
                    if attempt < config.max_attempts:
                        # Calculate wait time with exponential backoff
                        wait_time = min(
                            config.min_wait * (config.exponential_base ** (attempt - 1)),
                            config.max_wait
                        )
                        logger.warning(
                            f"Attempt {attempt}/{config.max_attempts} failed for {func.__name__}: {e}. "
                            f"Retrying in {wait_time:.1f}s..."
                        )
                        import time
                        time.sleep(wait_time)
                    else:
                        logger.error(
                            f"All {config.max_attempts} attempts failed for {func.__name__}"
                        )

            # If we get here, all attempts failed
            raise last_exception

        # Return appropriate wrapper based on whether function is async
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper

    return decorator


def retry_async(
    max_attempts: int = 3,
    wait_min: float = 1.0,
    wait_max: float = 60.0,
    on: tuple[Type[Exception], ...] = (Exception,)
):
    """
    Simplified async retry decorator

    Args:
        max_attempts: Maximum number of attempts
        wait_min: Minimum wait time in seconds
        wait_max: Maximum wait time in seconds
        on: Exception types to retry on

    Example:
        @retry_async(max_attempts=3, on=(ConnectionError,))
        async def fetch_api():
            ...
    """
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @wraps(func)
        async def wrapper(*args, **kwargs) -> T:
            last_exception = None
            for attempt in range(1, max_attempts + 1):
                try:
                    return await func(*args, **kwargs)
                except on as e:
                    last_exception = e
                    if attempt < max_attempts:
                        # Exponential backoff
                        wait_time = min(wait_min * (2 ** (attempt - 1)), wait_max)
                        logger.warning(
                            f"Retry {attempt}/{max_attempts} for {func.__name__} after {wait_time}s"
                        )
                        await asyncio.sleep(wait_time)

            raise last_exception

        return wrapper

    return decorator
