#!/bin/bash
# 启动 Celery Worker 和 Beat 调度器

# 设置项目根目录
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PROJECT_ROOT" || exit 1

echo "🚀 启动 Celery 服务..."
echo "项目目录: $PROJECT_ROOT"
echo ""

# 检查 Redis 连接
echo "📡 检查 Redis 连接..."
if ! redis-cli -h 127.0.0.1 -p 6379 ping > /dev/null 2>&1; then
    echo "❌ Redis 未运行，请先启动 Redis"
    exit 1
fi
echo "✅ Redis 连接正常"
echo ""

# 启动 Worker
echo "📦 启动 Celery Worker..."
bash "$PROJECT_ROOT/scripts/celery_worker.sh" &
WORKER_PID=$!
echo "✅ Worker 已启动 (PID: $WORKER_PID)"
echo ""

# 等待2秒让 Worker 完全启动
sleep 2

# 启动 Beat
echo "⏰ 启动 Celery Beat..."
bash "$PROJECT_ROOT/scripts/celery_beat.sh" &
BEAT_PID=$!
echo "✅ Beat 已启动 (PID: $BEAT_PID)"
echo ""

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "✅ Celery 服务启动完成"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "Worker PID: $WORKER_PID"
echo "Beat PID: $BEAT_PID"
echo ""
echo "查看日志:"
echo "  - Worker: tail -f logs/celery/worker.log"
echo "  - Beat: tail -f logs/celery/beat.log"
echo ""
echo "停止服务:"
echo "  bash scripts/stop_celery.sh"
echo ""
