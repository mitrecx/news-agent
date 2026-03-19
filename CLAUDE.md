---
description: 
alwaysApply: true
---

# CLAUDE.md

本文件为 Claude Code (claude.ai/code) 在此代码库中工作时提供指导。

## 项目概述

news-agent 是一个基于 LangChain 的 AI 助手，可从微博热搜获取实时新闻。应用包含以下部分：

- **后端**: FastAPI 服务器，包含认证、对话持久化和流式聊天响应
- **前端**: Vue.js 单页应用，使用 Pinia 状态管理和 Element Plus UI
- **Agent**: LangChain 代理，使用 DeepSeek LLM 并集成微博热搜工具
- **数据库**: PostgreSQL 存储用户、对话和消息

## 开发命令

### 环境设置

```bash
# 安装依赖（使用 uv 包管理器）
uv sync
```

### 本地运行 news-agent

```bash
# 启动后端 FastAPI 服务器（端口 8000）
./scripts/start_backend.sh

# 启动前端开发服务器（端口 6173）
./scripts/start_frontend.sh
```

### 测试(非常重要)

参考 test-news-agent skill 进行测试

### 部署到远程服务器(上线)

```bash
./deploy.sh
```

## 架构概览

### 请求流程

```
用户输入 (Vue.js)
  → POST /api/chat/stream (FastAPI)
  → JWT 认证
  → NewsAgent.chat_stream()
  → LangChain Agent → DeepSeek LLM
  → 工具: fetch_weibo_hot_search() (如需要)
  → 流式 SSE 响应
  → 保存到 PostgreSQL (用户消息 + 助手回复)
  → 生成对话标题 (AI 或截断)
  → 前端实时显示数据块
```

### 组件关系

**认证与数据层** (`src/auth/`):
- `database.py`: 单例 asyncpg 连接池
- `models.py`: User、UserCreate、Token 的 Pydantic 模型
- `security.py`: 密码哈希 (bcrypt) 和 JWT 令牌操作
- `router.py`: FastAPI 路由，包括 /register、/login、/me
- `user_service.py`: 用户 CRUD 操作
- `conversation_service.py`: 对话和消息持久化

**Agent 层** (`src/agent/`):
- `base.py`: NewsAgent 类，封装 LangChain 代理并支持流式响应
- `config.py`: 使用 Pydantic settings 管理配置，从 `.env` 加载

**工具** (`src/tools/`):
- `weibo.py`: LangChain @tool 装饰的函数，三级降级策略：
  1. Selenium 爬虫（webdriver-manager 自动下载 ChromeDriver）
  2. httpx + BeautifulSoup HTTP 爬虫
  3. 两者都失败时使用模拟数据

**API 层** (`src/api/`):
- `server.py`: FastAPI 应用，包含生命周期管理，处理 /chat 和 /chat/stream 端点
- `models.py`: Pydantic 请求/响应模型 (ChatRequest、ChatResponse)

**前端** (`src/frontend-vue/`):
- `src/composables/useChatStream.ts`: 管理流式聊天连接和消息发送
- `src/stores/chat.ts`: Pinia 状态存储（messages、isStreaming、isSending 标志）
- `src/stores/conversation.ts`: 对话列表和选择管理
- `src/api/chat.ts`: 使用 @microsoft/fetch-event-source 的 SSE 客户端
