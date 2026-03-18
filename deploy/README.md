# Celery 定时任务部署说明

## 概述

`deploy.sh` 脚本已经更新，现在会自动部署 Celery Worker 和 Celery Beat 服务，用于运行定时任务。

## 自动部署的服务

部署脚本会自动部署以下服务：

1. **news-agent-backend** - FastAPI 后端服务
2. **news-agent-celery-worker** - Celery Worker（执行异步任务）
3. **news-agent-celery-beat** - Celery Beat（定时任务调度器）

## 定时任务

已配置的定时任务：

- **每小时整点**：抓取微博热搜标题并保存到数据库
- **每10分钟**：清理过期的微博热搜缓存

## 部署步骤

### 1. 确保环境变量配置正确

在 `.env` 文件中添加 Redis 配置：

```bash
# Redis 配置（用于 Celery）
REDIS_HOST=127.0.0.1
REDIS_PORT=6379
```

### 2. 确保 Redis 已安装并运行

在服务器上安装 Redis：

```bash
# Ubuntu/Debian
sudo apt update
sudo apt install redis-server -y
sudo systemctl start redis
sudo systemctl enable redis

# 验证 Redis 运行状态
redis-cli ping
# 应该返回: PONG
```

### 3. 运行部署脚本

```bash
./deploy.sh
```

部署脚本会自动：
- 上传项目文件到服务器
- 部署前端和后端
- 部署 Celery Worker 和 Beat 服务
- 重启所有服务

## 验证部署

### 检查服务状态

```bash
# 检查所有服务状态
ssh user@your-server 'sudo systemctl status news-agent-*'

# 单独检查 Celery Worker
ssh user@your-server 'sudo systemctl status news-agent-celery-worker'

# 单独检查 Celery Beat
ssh user@your-server 'sudo systemctl status news-agent-celery-beat'
```

### 查看日志

```bash
# 使用 systemd journal 查看
ssh user@your-server 'sudo journalctl -u news-agent-celery-worker -f'
ssh user@your-server 'sudo journalctl -u news-agent-celery-beat -f'

# 查看日志文件
ssh user@your-server 'tail -f ~/news-agent/logs/celery/worker.log'
ssh user@your-server 'tail -f ~/news-agent/logs/celery/beat.log'
```

### 验证定时任务

等待下一个整点（如 14:00、15:00 等），然后检查日志：

```bash
# 查看定时任务执行记录
ssh user@your-server 'grep "开始抓取微博热搜标题" ~/news-agent/logs/celery/worker.log'
```

或手动触发任务测试：

```python
# 在服务器上运行
cd ~/news-agent
source .venv/bin/activate
python -c "
from src.tasks.weibo_tasks import fetch_and_save_hot_search_titles
result = fetch_and_save_hot_search_titles.delay(limit=5)
print('Task ID:', result.id)
print('Result:', result.get(timeout=60))
"
```

## 手动管理服务

### 启动/停止/重启服务

```bash
# Celery Worker
ssh user@your-server 'sudo systemctl start news-agent-celery-worker'
ssh user@your-server 'sudo systemctl stop news-agent-celery-worker'
ssh user@your-server 'sudo systemctl restart news-agent-celery-worker'

# Celery Beat
ssh user@your-server 'sudo systemctl start news-agent-celery-beat'
ssh user@your-server 'sudo systemctl stop news-agent-celery-beat'
ssh user@your-server 'sudo systemctl restart news-agent-celery-beat'
```

### 查看已注册的任务

```bash
ssh user@your-server 'cd ~/news-agent && source .venv/bin/activate && celery -A src.celery_app inspect registered'
```

### 查看定时任务配置

```bash
ssh user@your-server 'cd ~/news-agent && source .venv/bin/activate && celery -A src.celery_app inspect beat'
```

## 故障排查

### 1. Redis 未运行

```bash
# 检查 Redis 状态
sudo systemctl status redis

# 启动 Redis
sudo systemctl start redis
```

### 2. Celery 服务启动失败

查看详细错误信息：

```bash
sudo journalctl -u news-agent-celery-worker -n 50
sudo journalctl -u news-agent-celery-beat -n 50
```

### 3. 权限问题

确保日志目录有正确的权限：

```bash
ssh user@your-server 'mkdir -p ~/news-agent/logs/celery'
ssh user@your-server 'chmod 755 ~/news-agent/logs/celery'
```

### 4. 虚拟环境路径问题

systemd 服务文件中的路径会自动替换为实际的项目路径，但如果遇到问题，可以手动检查：

```bash
ssh user@your-server 'cat /etc/systemd/system/news-agent-celery-worker.service'
```

## 数据库验证

检查微博热搜缓存表：

```sql
-- 连接到数据库
psql -U news_agent -d news_agent

-- 查看最新的热搜记录
SELECT
    title,
    description_source,
    created_at
FROM weibo_hot_search_cache
ORDER BY created_at DESC
LIMIT 20;

-- 查看过去1小时的统计
SELECT
    description_source,
    COUNT(*) as count
FROM weibo_hot_search_cache
WHERE created_at > NOW() - INTERVAL '1 hour'
GROUP BY description_source;
```

## 总结

现在使用 `./deploy.sh` 部署时，**不需要额外手动部署定时任务**。脚本会自动：

✅ 部署 Celery Worker 服务
✅ 部署 Celery Beat 服务
✅ 配置定时任务（每小时抓取热搜）
✅ 启动并启用所有服务
✅ 验证服务运行状态

定时任务会自动在每小时整点运行，无需手动干预。
