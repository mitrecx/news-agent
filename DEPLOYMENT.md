# News Agent 服务器部署指南

本文档介绍如何将 News Agent 部署到 Linux 服务器上。

## 目录

- [前置要求](#前置要求)
- [环境准备](#环境准备)
- [安装必要软件](#安装必要软件)
- [配置数据库](#配置数据库)
- [部署项目](#部署项目)
- [配置 Nginx 反向代理](#配置-nginx-反向代理)
- [配置防火墙](#配置防火墙)
- [常见问题](#常见问题)

---

## 前置要求

### 服务器要求

- **操作系统**: Linux (推荐 CentOS 7+/Alibaba Cloud Linux 3/Ubuntu 20.04+)
- **CPU**: 2 核心及以上
- **内存**: 4GB 及以上
- **磁盘**: 20GB 及以上

### 本地环境

- Git 客户端
- SSH 客户端
- 文本编辑器

### 账号准备

- DeepSeek API Key ([获取地址](https://platform.deepseek.com/))

---

## 环境准备

### 1. 连接服务器

```bash
ssh username@your-server-ip

# 示例：
# ssh myuser@192.168.1.100
```

### 2. 更新系统

```bash
# CentOS/Alibaba Cloud Linux
sudo yum update -y

# Ubuntu/Debian
sudo apt update && sudo apt upgrade -y
```

---

## 安装必要软件

### 1. 安装 Python 3.11

```bash
# 安装依赖
sudo yum install -y gcc openssl-devel bzip2-devel libffi-devel zlib-devel

# 下载并编译 Python 3.11
cd /tmp
wget https://www.python.org/ftp/python/3.11.9/Python-3.11.9.tgz
tar -xzf Python-3.11.9.tgz
cd Python-3.11.9
./configure --enable-optimizations --prefix=/usr/local
make altinstall -j$(nproc)

# 创建软链接
sudo ln -sf /usr/local/bin/python3.11 /usr/local/bin/python3
sudo ln -sf /usr/local/bin/pip3.11 /usr/local/bin/pip3

# 验证安装
python3 --version
pip3 --version
```

### 2. 安装 uv 包管理器

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
export PATH="$HOME/.local/bin:$PATH"

# 验证安装
uv --version
```

### 3. 安装 PostgreSQL

```bash
# CentOS/Alibaba Cloud Linux
sudo yum install -y postgresql postgresql-server

# Ubuntu/Debian
sudo apt install -y postgresql postgresql-contrib

# 初始化数据库
sudo postgresql-setup --initdb || sudo /usr/bin/postgresql-setup --initdb

# 启动并设置开机自启
sudo systemctl start postgresql
sudo systemctl enable postgresql

# 验证
sudo systemctl status postgresql
```

### 4. 安装 Node.js

```bash
# 使用 NodeSource 仓库安装 Node.js 22.x
curl -fsSL https://rpm.nodesource.com/setup_22.x | sudo bash -
sudo yum install -y nodejs

# Ubuntu/Debian
# curl -fsSL https://deb.nodesource.com/setup_22.x | sudo -E bash -
# sudo apt install -y nodejs

# 验证
node --version
npm --version
```

### 5. 安装 Chrome 浏览器（Selenium 需要）

```bash
# 下载 Chrome RPM
wget https://dl.google.com/linux/direct/google-chrome-stable_current_x86_64.rpm

# 安装
sudo yum localinstall -y google-chrome-stable_current_x86_64.rpm

# 验证
google-chrome --version
```

### 6. 安装 Nginx

```bash
# CentOS/Alibaba Cloud Linux
sudo yum install -y nginx

# Ubuntu/Debian
sudo apt install -y nginx

# 启动并设置开机自启
sudo systemctl start nginx
sudo systemctl enable nginx

# 验证
nginx -v
```

---

## 配置数据库

### 1. 修改 PostgreSQL 认证配置

```bash
# 备份配置文件
sudo cp /var/lib/pgsql/data/pg_hba.conf /var/lib/pgsql/data/pg_hba.conf.bak

# 修改认证方式为 md5
sudo bash -c 'cat > /var/lib/pgsql/data/pg_hba.conf << EOF
# TYPE  DATABASE        USER            ADDRESS                 METHOD
local   all             all                                     md5
host    all             all             127.0.0.1/32            md5
host    all             all             ::1/128                 md5
EOF'

# 重启 PostgreSQL
sudo systemctl restart postgresql
```

### 2. 创建数据库和用户

```bash
# 切换到 postgres 用户
sudo -u postgres psql << 'EOF'
-- 创建数据库
CREATE DATABASE news_agent;

-- 创建用户（请修改密码）
CREATE USER your_username WITH PASSWORD 'your_secure_password';

-- 授予权限
GRANT ALL PRIVILEGES ON DATABASE news_agent TO your_username;

-- 退出
\q
EOF
```

> **注意**: 请将 `your_username` 和 `your_secure_password` 替换为实际值

---

## 部署项目

### 1. 克隆项目（或上传项目文件）

```bash
# 方法 1: 使用 Git（推荐）
cd ~
git clone https://github.com/your-username/news-agent.git
cd news-agent

# 方法 2: 上传项目文件
# 在本地执行：
# scp -r news-agent username@server-ip:~/
```

### 2. 配置环境变量

```bash
cd ~/news-agent

# 复制环境变量模板
cp .env.example .env

# 编辑 .env 文件
nano .env
```

在 `.env` 文件中配置以下关键参数：

```env
# DeepSeek API 配置
DEEPSEEK_API_KEY=your_deepseek_api_key_here
DEEPSEEK_BASE_URL=https://api.deepseek.com/v1

# 服务配置
HOST=127.0.0.1
PORT=8000

# 数据库配置（请替换为实际值）
DB_HOST=localhost
DB_PORT=5432
DB_USER=your_username
DB_PASSWORD=your_secure_password
DB_NAME=news_agent

# JWT 密钥（请修改为随机字符串）
JWT_SECRET=your-random-secret-key-change-this
```

### 3. 安装后端依赖

```bash
~/.local/bin/uv sync
```

### 4. 初始化数据库

```bash
~/.local/bin/uv run python scripts/init_db.py
```

这会创建：
- `users` 表
- `conversations` 表
- `messages` 表
- 默认测试用户（用户名: `test`, 密码: `test`）

### 5. 构建前端

```bash
cd src/frontend-vue
npm install
npm run build
```

### 6. 创建 systemd 服务

```bash
sudo tee /etc/systemd/system/news-agent-backend.service << 'EOF'
[Unit]
Description=News Agent Backend Service
After=network.target postgresql.service

[Service]
Type=simple
User=your_username
WorkingDirectory=/home/your_username/news-agent
Environment="PATH=/home/your_username/.local/bin:/usr/local/bin:/usr/bin:/bin"
Environment="PGPASSWORD=your_secure_password"
ExecStart=/home/your_username/.local/bin/uv run python run.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF
```

> **注意**: 将 `your_username` 和 `your_secure_password` 替换为实际值

启动后端服务：

```bash
sudo systemctl daemon-reload
sudo systemctl start news-agent-backend
sudo systemctl enable news-agent-backend

# 检查服务状态
sudo systemctl status news-agent-backend
```

---

## 配置 Nginx 反向代理

### 1. 复制前端静态文件

```bash
sudo mkdir -p /var/www/news-agent
sudo cp -r ~/news-agent/src/frontend-vue/dist/* /var/www/news-agent/
sudo chown -R nginx:nginx /var/www/news-agent/
sudo chmod -R 755 /var/www/news-agent/
```

### 2. 创建 Nginx 配置

```bash
sudo tee /etc/nginx/conf.d/news-agent.conf << 'EOF'
server {
    listen 80;
    server_name your-domain.com;  # 替换为你的域名或服务器 IP

    location / {
        root /var/www/news-agent;
        try_files $uri $uri/ /index.html;

        # 静态资源缓存
        location ~* \.(js|css|png|jpg|jpeg|gif|svg|ico|woff|woff2|ttf|eot)$ {
            expires 1y;
            add_header Cache-Control public;
        }
    }

    # 后端 API 代理（支持 SSE 流式响应）
    location /api/ {
        proxy_pass http://127.0.0.1:8000/api/;
        proxy_http_version 1.1;

        # SSE 支持 - 禁用缓冲
        proxy_buffering off;
        proxy_cache off;
        proxy_read_timeout 86400s;
        proxy_send_timeout 86400s;

        # Headers
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_request_buffering off;
    }

    # WebSocket 支持
    location /ws/ {
        proxy_pass http://127.0.0.1:8000/ws/;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection upgrade;
        proxy_set_header Host $host;
        proxy_read_timeout 86400;
    }

    # 健康检查端点
    location /health {
        proxy_pass http://127.0.0.1:8000/health;
        access_log off;
    }
}
EOF
```

> **注意**: 将 `your-domain.com` 替换为你的域名或服务器 IP

### 3. 测试并重新加载 Nginx

```bash
# 测试配置
sudo nginx -t

# 重新加载配置
sudo systemctl reload nginx

# 检查状态
sudo systemctl status nginx
```

---

## 配置防火墙

### 1. 配置服务器防火墙（可选）

```bash
# CentOS/Alibaba Cloud Linux (firewalld)
sudo firewall-cmd --permanent --add-service=http
sudo firewall-cmd --permanent --add-service=https
sudo firewall-cmd --reload

# Ubuntu (ufw)
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp
sudo ufw enable
```

### 2. 配置云服务商安全组（重要）

在云服务商控制台（阿里云/腾讯云/AWS等）配置安全组规则：

| 协议类型 | 端口范围 | 授权对象 | 描述 |
|---------|---------|---------|------|
| TCP | 80 | 0.0.0.0/0 | HTTP |
| TCP | 443 | 0.0.0.0/0 | HTTPS（可选） |
| TCP | 22 | 0.0.0.0/0 | SSH（建议限制 IP） |

---

## 测试部署

### 1. 测试后端健康检查

```bash
curl http://localhost:8000/health
# 应该返回：{"status":"ok","agent_ready":true}
```

### 2. 测试前端访问

在浏览器中访问：
- `http://your-server-ip` 或 `http://your-domain.com`

应该能看到登录页面。

### 3. 测试登录

使用默认测试账号：
- 用户名: `test`
- 密码: `test`

### 4. 测试对话功能

登录后发送消息，验证流式响应是否正常。

---

## 常见问题

### 1. 端口被占用

**问题**: `Address already in use`

**解决方法**:
```bash
# 查找占用端口的进程
sudo lsof -i :8000
sudo lsof -i :80

# 终止进程
sudo kill -9 <PID>
```

### 2. 数据库连接失败

**问题**: `connection refused` 或 `authentication failed`

**解决方法**:
```bash
# 检查 PostgreSQL 状态
sudo systemctl status postgresql

# 检查配置
sudo cat /var/lib/pgsql/data/pg_hba.conf

# 重启 PostgreSQL
sudo systemctl restart postgresql
```

### 3. 502 Bad Gateway

**问题**: 访问网站时显示 502 错误

**解决方法**:
```bash
# 检查后端服务状态
sudo systemctl status news-agent-backend

# 查看后端日志
sudo journalctl -u news-agent-backend -f

# 重启后端服务
sudo systemctl restart news-agent-backend
```

### 4. 静态文件 404

**问题**: 前端页面无法加载

**解决方法**:
```bash
# 检查文件是否存在
ls -la /var/www/news-agent/

# 重新复制文件
sudo cp -r ~/news-agent/src/frontend-vue/dist/* /var/www/news-agent/

# 检查权限
sudo chown -R nginx:nginx /var/www/news-agent/
sudo chmod -R 755 /var/www/news-agent/
```

### 5. SSE 流式响应不工作

**问题**: 对话时显示 "Expected content-type to be text/event-stream"

**解决方法**:
```bash
# 检查 Nginx 配置
sudo cat /etc/nginx/conf.d/news-agent.conf | grep -E '(proxy_buffering|proxy_cache)'

# 确保以下配置存在
# proxy_buffering off;
# proxy_cache off;

# 重新加载 Nginx
sudo systemctl reload nginx
```

### 6. API 认证失败

**问题**: "Not authenticated" 或 "Invalid authentication credentials"

**解决方法**:
```bash
# 检查 .env 配置
cat ~/news-agent/.env | grep -E '(DB_|JWT_)'

# 确认数据库配置正确后，重启后端
sudo systemctl restart news-agent-backend
```

### 7. 权限错误

**问题**: `Permission denied`

**解决方法**:
```bash
# 添加用户到 nginx 组（可选）
sudo usermod -a -G nginx your_username

# 修改文件权限
sudo chmod +x /home/your_username
sudo chmod +x /home/your_username/news-agent
sudo chmod -R 755 /var/www/news-agent
```

---

## 维护命令

### 重启服务

```bash
# 重启后端
sudo systemctl restart news-agent-backend

# 重启 Nginx
sudo systemctl restart nginx

# 重启 PostgreSQL
sudo systemctl restart postgresql
```

### 查看日志

```bash
# 后端服务日志
sudo journalctl -u news-agent-backend -f

# Nginx 访问日志
sudo tail -f /var/log/nginx/access.log

# Nginx 错误日志
sudo tail -f /var/log/nginx/error.log

# PostgreSQL 日志
sudo tail -f /var/lib/pgsql/data/log/postgresql-*.log
```

### 更新项目

```bash
cd ~/news-agent

# 拉取最新代码
git pull

# 更新后端依赖
~/.local/bin/uv sync

# 重新构建前端
cd src/frontend-vue
npm install
npm run build

# 更新静态文件
sudo cp -r dist/* /var/www/news-agent/

# 重启后端服务
sudo systemctl restart news-agent-backend
```

### 备份数据库

```bash
# 备份数据库
pg_dump -U your_username -h localhost news_agent > backup_$(date +%Y%m%d).sql

# 恢复数据库
psql -U your_username -h localhost news_agent < backup_20250314.sql
```

---

## 安全建议

1. **修改默认密码**: 登录后立即修改测试用户密码
2. **使用 HTTPS**: 配置 SSL 证书（Let's Encrypt）
3. **限制 SSH 访问**: 只允许特定 IP 访问 SSH 端口
4. **定期更新**: 定期更新系统和依赖包
5. **监控日志**: 定期检查异常日志

---

## 联系与支持

- 项目地址: https://github.com/mitrecx/news-agent
- 问题反馈: 在项目 GitHub 仓库提 Issue

---

**部署完成后，访问 `http://your-server-ip` 即可使用 News Agent！**
