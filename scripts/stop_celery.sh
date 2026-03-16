#!/bin/bash
# 停止 Celery Worker 和 Beat 调度器

# 设置项目根目录
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PROJECT_ROOT" || exit 1

LOG_DIR="$PROJECT_ROOT/logs/celery"
mkdir -p "$LOG_DIR"

echo "🛑 停止 Celery 服务..."
echo ""

# 停止 Worker
if [ -f "$LOG_DIR/worker.pid" ]; then
    WORKER_PID=$(cat "$LOG_DIR/worker.pid")
    echo "📦 停止 Worker (PID: $WORKER_PID)..."

    if kill -0 "$WORKER_PID" 2>/dev/null; then
        kill "$WORKER_PID"
        sleep 1

        # 如果进程还在，强制杀死
        if kill -0 "$WORKER_PID" 2>/dev/null; then
            echo "⚠️ 强制停止 Worker..."
            kill -9 "$WORKER_PID"
        fi

        rm -f "$LOG_DIR/worker.pid"
        echo "✅ Worker 已停止"
    else
        echo "⚠️ Worker 进程不存在"
        rm -f "$LOG_DIR/worker.pid"
    fi
else
    echo "⚠️ Worker PID 文件不存在"
fi

echo ""

# 停止 Beat
if [ -f "$LOG_DIR/beat.pid" ]; then
    BEAT_PID=$(cat "$LOG_DIR/beat.pid")
    echo "⏰ 停止 Beat (PID: $BEAT_PID)..."

    if kill -0 "$BEAT_PID" 2>/dev/null; then
        kill "$BEAT_PID"
        sleep 1

        # 如果进程还在，强制杀死
        if kill -0 "$BEAT_PID" 2>/dev/null; then
            echo "⚠️ 强制停止 Beat..."
            kill -9 "$BEAT_PID"
        fi

        rm -f "$LOG_DIR/beat.pid"
        echo "✅ Beat 已停止"
    else
        echo "⚠️ Beat 进程不存在"
        rm -f "$LOG_DIR/beat.pid"
    fi
else
    echo "⚠️ Beat PID 文件不存在"
fi

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "✅ Celery 服务已停止"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
