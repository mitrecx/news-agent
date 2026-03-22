"""Celery 应用配置"""

import os
from celery import Celery
from celery.schedules import crontab

# Redis 配置
REDIS_HOST = os.getenv('REDIS_HOST', '127.0.0.1')
REDIS_PORT = os.getenv('REDIS_PORT', '6379')
REDIS_URL = f'redis://{REDIS_HOST}:{REDIS_PORT}/0'

# 创建 Celery 应用
celery_app = Celery(
    'news_agent',
    broker=REDIS_URL,
    backend=REDIS_URL,
    include=['src.tasks.cache_tasks', 'src.tasks.weibo_tasks']  # 导入任务模块
)

# Celery 配置
celery_app.conf.update(
    # 任务结果过期时间（1小时）
    result_expires=3600,

    # 任务执行时间限制（5分钟）
    task_time_limit=300,

    # 任务软时间限制（4分钟，触发 SoftTimeLimitExceeded 异常）
    task_soft_time_limit=240,

    # 任务重试配置
    task_acks_late=True,              # 任务执行后才确认
    worker_prefetch_multiplier=1,      # 每次只预取1个任务
    worker_max_tasks_per_child=100,    # 执行100个任务后重启 worker

    # 时区设置
    timezone='Asia/Shanghai',
    enable_utc=True,

    # 任务序列化
    task_serializer='json',
    accept_content=['json'],
    result_serializer='json',
)

# 定时任务配置
celery_app.conf.beat_schedule = {
    # 每10分钟清理一次过期缓存
    'clean-expired-weibo-cache': {
        'task': 'src.tasks.cache_tasks.clean_expired_cache',
        'schedule': crontab(minute='*/10'),  # 每10分钟
    },
    # 每3小时抓取微博热搜标题（从0点开始：0:00, 3:00, 6:00, 9:00, 12:00, 15:00, 18:00, 21:00）
    'fetch-weibo-hot-search-titles': {
        'task': 'src.tasks.weibo_tasks.fetch_and_save_hot_search_titles',
        'schedule': crontab(hour='*/3', minute=0),  # 每3小时整点执行
    },
}
