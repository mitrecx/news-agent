#!/bin/bash
# 启动 Celery Beat 定时任务调度器

# 设置项目根目录
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PROJECT_ROOT" || exit 1

# 激活虚拟环境
source .venv/bin/activate

# 设置环境变量（如果需要）
export PYTHONPATH="$PROJECT_ROOT:$PYTHONPATH"

# 日志目录
LOG_DIR="$PROJECT_ROOT/logs/celery"
mkdir -p "$LOG_DIR"

echo "🚀 启动 Celery Beat..."
echo "项目目录: $PROJECT_ROOT"
echo "日志目录: $LOG_DIR"

# 启动 beat scheduler
celery -A src.celery_app beat \
    --loglevel=info \
    --logfile="$LOG_DIR/beat.log" \
    --pidfile="$LOG_DIR/beat.pid"
