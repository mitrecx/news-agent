#!/bin/bash
# Start backend server script - handles port conflicts automatically

set -e

PORT=8000
echo "🚀 Starting News Agent backend..."

# Function to get PID of process using the port
get_port_pid() {
    lsof -ti :$1 2>/dev/null || true
}

# Function to kill process by PID
kill_process() {
    local pid=$1
    if [ -n "$pid" ]; then
        echo "🔪 Stopping existing process (PID: $pid)..."
        kill -9 $pid 2>/dev/null || true
        sleep 1
    fi
}

# Check if port is occupied
PORT_PID=$(get_port_pid $PORT)

if [ -n "$PORT_PID" ]; then
    echo "⚠️  Port $PORT is already in use (PID: $PORT_PID)"
    echo "🛑 Stopping existing service(s)..."

    # Kill all processes using the port
    for pid in $PORT_PID; do
        kill_process $pid
    done

    # Verify port is free
    PORT_PID=$(get_port_pid $PORT)
    if [ -n "$PORT_PID" ]; then
        echo "❌ Failed to free port $PORT. Please manually stop the process."
        echo "   Run: lsof -i :$PORT"
        exit 1
    fi

    echo "✅ Port $PORT is now free"
fi

# Start the backend
echo "▶️  Starting backend on port $PORT..."
uv run python run.py
