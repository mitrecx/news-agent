"""Celery 任务模块"""

from .cache_tasks import clean_expired_cache

__all__ = ['clean_expired_cache']
