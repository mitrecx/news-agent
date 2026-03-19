#!/bin/bash
# Start backend server script - handles port conflicts automatically

set -e

# Trap to ensure cleanup happens on exit
trap stop_db_tunnel EXIT INT TERM

PORT=8000
DB_PORT=5432
DB_TUNNEL_HOST="shenzhi@47.100.74.209"
DB_REMOTE_HOST="localhost"  # 数据库在远程服务器上的地址

echo "🚀 Starting News Agent backend..."

# Function to get PID of process using the port
get_port_pid() {
    lsof -ti :$1 2>/dev/null || true
}

# Function to start SSH tunnel for database
start_db_tunnel() {
    local tunnel_pid=$(ps aux | grep "ssh.*-L.*${DB_PORT}" | grep -v grep | awk '{print $2}')

    if [ -n "$tunnel_pid" ]; then
        echo "✅ Database tunnel already running (PID: $tunnel_pid)"
    else
        echo "🔧 Starting SSH tunnel for database..."
        ssh -f -N -L ${DB_PORT}:${DB_REMOTE_HOST}:${DB_PORT} ${DB_TUNNEL_HOST}

        # Wait for tunnel to be established
        sleep 2

        # Verify tunnel is running
        tunnel_pid=$(ps aux | grep "ssh.*-L.*${DB_PORT}" | grep -v grep | awk '{print $2}')
        if [ -n "$tunnel_pid" ]; then
            echo "✅ Database tunnel started successfully (PID: $tunnel_pid)"
        else
            echo "⚠️  Warning: Failed to start database tunnel"
        fi
    fi
}

# Function to stop SSH tunnel
stop_db_tunnel() {
    local tunnel_pid=$(ps aux | grep "ssh.*-L.*${DB_PORT}" | grep -v grep | awk '{print $2}')

    if [ -n "$tunnel_pid" ]; then
        echo "🛑 Stopping database tunnel (PID: $tunnel_pid)..."
        kill $tunnel_pid 2>/dev/null || true
        echo "✅ Database tunnel stopped"
    fi
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

# Start database tunnel
start_db_tunnel

# Start the backend
echo "▶️  Starting backend on port $PORT..."
uv run python run.py
