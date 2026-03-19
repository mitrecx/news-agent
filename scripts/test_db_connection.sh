#!/bin/bash
# Test database connection via SSH tunnel

set -e

DB_PORT=5432
DB_TUNNEL_HOST="shenzhi@47.100.74.209"
DB_REMOTE_HOST="localhost"
TUNNEL_PORT=15432  # 使用不同的本地端口避免冲突

echo "🔧 Testing SSH tunnel for database connection..."

# 检查是否已有隧道在使用测试端口
existing_tunnel=$(ps aux | grep "ssh.*-L.*${TUNNEL_PORT}" | grep -v grep | awk '{print $2}')
if [ -n "$existing_tunnel" ]; then
    echo "⚠️  Cleaning up existing tunnel on port ${TUNNEL_PORT}..."
    kill $existing_tunnel 2>/dev/null || true
    sleep 1
fi

# 启动测试隧道
echo "▶️  Starting SSH tunnel (localhost:${TUNNEL_PORT} -> ${DB_REMOTE_HOST}:${DB_PORT})..."
ssh -f -N -L ${TUNNEL_PORT}:${DB_REMOTE_HOST}:${DB_PORT} ${DB_TUNNEL_HOST}

# 等待隧道建立
sleep 2

# 验证隧道是否运行
tunnel_pid=$(ps aux | grep "ssh.*-L.*${TUNNEL_PORT}" | grep -v grep | awk '{print $2}')
if [ -z "$tunnel_pid" ]; then
    echo "❌ Failed to start SSH tunnel"
    exit 1
fi

echo "✅ SSH tunnel started successfully (PID: $tunnel_pid)"

# 测试数据库连接
echo "🔗 Testing database connection..."

# 临时修改环境变量进行测试
export DB_HOST=localhost
export DB_PORT=${TUNNEL_PORT}

# 使用Python测试连接
uv run python -c "
import asyncio
import asyncpg
import os
from dotenv import load_dotenv

load_dotenv()

async def test_connection():
    try:
        print(f'Connecting to: {os.getenv(\"DB_HOST\")}:{os.getenv(\"DB_PORT\")}')
        conn = await asyncpg.connect(
            host=os.getenv('DB_HOST'),
            port=int(os.getenv('DB_PORT')),
            user=os.getenv('DB_USER'),
            password=os.getenv('DB_PASSWORD'),
            database=os.getenv('DB_NAME')
        )
        print('✅ Database connection successful!')

        # 测试查询
        version = await conn.fetchval('SELECT version()')
        print(f'📊 Database version: {version[:50]}...')

        # 检查表
        tables = await conn.fetch(\"\"\"
            SELECT table_name FROM information_schema.tables
            WHERE table_schema = 'public'
            ORDER BY table_name
        \"\"\")
        print(f'📋 Found {len(tables)} tables:')
        for table in tables:
            print(f'   - {table[\"table_name\"]}')

        await conn.close()
        return True
    except Exception as e:
        print(f'❌ Database connection failed: {e}')
        return False

result = asyncio.run(test_connection())
exit(0 if result else 1)
"

# 清理测试隧道
echo ""
echo "🧹 Cleaning up test tunnel..."
kill $tunnel_pid 2>/dev/null || true

echo "✅ Test completed!"
