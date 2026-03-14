# News Agent

基于 LangChain 和 DeepSeek 的新闻助手 Agent，支持查询微博热搜。

## 功能特性

- **智能对话** - 基于 LangChain 框架的 AI 对话能力
- **DeepSeek 模型** - 使用 DeepSeek 高性能模型
- **流式输出** - 实时响应，更好的用户体验
- **微博热搜查询** - Agent 自动判断何时调用
- **多爬虫支持** - Selenium / HTTP 自动降级策略
- **用户认证系统** - JWT 认证，安全可靠
- **对话管理** - 支持多轮对话历史记录
- **请求缓存** - 微博热搜结果缓存（5分钟 TTL）
- **安全防护** - 速率限制、安全 headers、CORS 配置
- **性能优化** - 数据库连接池、索引优化

## 安全最佳实践

### 生产环境部署前必做

1. **生成强随机 JWT 密钥**
   ```bash
   python -c "import secrets; print(secrets.token_urlsafe(32))"
   ```
   将生成的密钥设置到 `.env` 文件的 `JWT_SECRET` 变量

2. **设置数据库凭据**
   - 不要在代码中硬编码数据库密码
   - 使用强密码（至少16字符，包含大小写字母、数字、特殊字符）
   - 限制数据库用户权限（不需要超级用户权限）

3. **环境变量配置**
   ```bash
   # 必填项
   DEEPSEEK_API_KEY=your_deepseek_api_key
   JWT_SECRET=your_generated_secret_key
   DB_USER=your_db_user
   DB_PASSWORD=your_strong_password
   ```

4. **HTTPS 部署**
   - 生产环境必须使用 HTTPS
   - 配置反向代理（Nginx/Caddy）
   - 启用 HSTS（HTTP Strict Transport Security）

5. **速率限制**
   - 默认配置：60 请求/分钟，1000 请求/小时
   - 可在 `src/api/middleware.py` 中调整

## 用户认证

系统需要用户登录才能使用。

- 使用用户名和密码登录
- 默认测试账号：用户名 `test`，密码 `test`
- 登录后可以与 Agent 对话，查询微博热搜等

### 数据库配置

首次启动前需要初始化数据库：

```bash
# 运行数据库初始化脚本
uv run python scripts/init_db.py

# （可选）运行数据库优化脚本，添加索引提升性能
uv run python scripts/optimize_db.py
```

这会创建 `news_agent` 数据库和测试用户。

## 如何启动

### 前置要求

1. **Python 3.10+**
   - 检查版本: `python --version`

2. **uv 包管理器** (推荐)
   - 安装: `curl -LsSf https://astral.sh/uv/install.sh | sh`
   - 或 macOS: `brew install uv`

3. **Chrome 浏览器** (Selenium 爬虫需要)
   - **macOS**: `brew install --cask google-chrome`
   - **Ubuntu**: `sudo apt-get install google-chrome-stable`
   - **Windows**: 从 https://www.google.com/chrome/ 下载

### 安装步骤

1. **克隆项目**
   ```bash
   git clone https://github.com/mitrecx/news-agent.git
   cd news-agent
   ```

2. **安装依赖**
   ```bash
   uv sync
   ```

3. **配置环境变量**
   ```bash
   # 复制环境变量模板
   cp .env.example .env

   # 编辑 .env 文件，填入你的配置
   # 必须配置：
   # - DEEPSEEK_API_KEY
   # - JWT_SECRET（生产环境）
   # - DB_USER 和 DB_PASSWORD
   ```

4. **初始化数据库**
   ```bash
   uv run python scripts/init_db.py
   ```

### 启动服务

```bash
uv run python run.py
```

启动成功后会看到类似输出：
```
✓ Connected to database: news_agent
✓ News Agent initialized with model: deepseek-chat
✓ Loaded 1 tool(s): ['fetch_weibo_hot_search']
✓ CORS configured for origins: [...]
✓ Security middleware configured (rate limit: 60/min, 1000/hour)
INFO:     Uvicorn running on http://0.0.0.0:8000
```

### 访问应用

- **Web 界面**: http://localhost:8000
- **API 文档**: http://localhost:8000/docs
- **健康检查**: http://localhost:8000/health

### 测试微博热搜

在 Web 界面中输入以下任一问题：
- "今天有什么热搜？"
- "微博上最近有什么热门话题？"
- "看看现在的热搜榜"

Agent 会自动识别并调用微博热搜工具获取最新数据。

## 项目结构

```
news-agent/
├── src/
│   ├── agent/           # Agent 核心逻辑
│   │   ├── base.py      # Agent 实现（支持工具绑定）
│   │   └── config.py    # 配置管理
│   ├── api/             # API 服务
│   │   ├── server.py    # FastAPI 服务器
│   │   ├── models.py    # 请求/响应模型
│   │   └── middleware.py # 安全中间件
│   ├── auth/            # 认证模块
│   │   ├── router.py    # 认证路由
│   │   ├── models.py    # 用户模型
│   │   ├── security.py  # 安全工具（密码哈希、JWT）
│   │   ├── database.py  # 数据库连接池
│   │   ├── user_service.py # 用户服务
│   │   └── conversation_service.py # 对话服务
│   ├── tools/           # LangChain 工具集成
│   │   ├── __init__.py  # 工具导出（含缓存）
│   │   └── weibo.py     # 微博热搜爬虫
│   └── frontend/        # 前端页面
│       └── index.html
├── scripts/             # 脚本目录
│   ├── init_db.py       # 数据库初始化脚本
│   ├── optimize_db.py   # 数据库优化脚本
│   ├── test_auth.py     # 认证测试
│   └── test_frontend_integration.py
├── .env.example         # 环境变量示例
├── pyproject.toml       # 项目配置
└── run.py              # 启动脚本
```

## 配置说明

| 环境变量 | 说明 | 默认值 | 必填 |
|---------|------|--------|------|
| `DEEPSEEK_API_KEY` | DeepSeek API 密钥 | - | ✅ |
| `DEEPSEEK_BASE_URL` | DeepSeek API 地址 | `https://api.deepseek.com/v1` | - |
| `HOST` | 服务监听地址 | `0.0.0.0` | - |
| `PORT` | 服务端口 | `8000` | - |
| `AGENT_MODEL` | 使用的模型 | `deepseek-chat` | - |
| `AGENT_TEMPERATURE` | 模型温度参数 | `0.7` | - |
| `AGENT_MAX_TOKENS` | 最大 token 数 | `2000` | - |
| `WEIBO_SCRAPER_TIMEOUT` | 微博爬虫超时时间（秒） | `10` | - |
| `WEIBO_USE_SELENIUM` | 是否使用 Selenium 爬虫 | `true` | - |
| `DB_HOST` | 数据库主机 | `localhost` | - |
| `DB_PORT` | 数据库端口 | `5432` | - |
| `DB_USER` | 数据库用户名 | - | ✅ |
| `DB_PASSWORD` | 数据库密码 | - | ✅ |
| `DB_NAME` | 数据库名称 | `news_agent` | - |
| `JWT_SECRET` | JWT 密钥 | - | ✅ (生产) |
| `JWT_ALGORITHM` | JWT 算法 | `HS256` | - |
| `JWT_ACCESS_TOKEN_EXPIRE_MINUTES` | Token 过期时间（分钟） | `10080` (7天) | - |

## 技术实现

### 安全特性

1. **密码加密**
   - 使用 bcrypt 哈希算法（12轮）
   - 自动加盐，无需手动管理

2. **JWT 认证**
   - 包含 issued-at 和 expiration claims
   - Token 验证失败自动拒绝

3. **SQL 注入防护**
   - 所有查询使用参数化语句
   - 使用 asyncpg 的安全绑定

4. **安全 Headers**
   - X-Content-Type-Options: nosniff
   - X-Frame-Options: DENY
   - X-XSS-Protection: 1; mode=block
   - Strict-Transport-Security: max-age=31536000
   - Content-Security-Policy: strict policy

5. **速率限制**
   - 基于内存的滑动窗口算法
   - IP 地址哈希化（GDPR 合规）

### 性能优化

1. **数据库优化**
   - 连接池（最小2，最大20连接）
   - 命令超时（60秒）
   - 自动清理空闲连接

2. **查询优化**
   - 关键字段索引
   - 复合索引优化
   - 定期 ANALYZE 更新统计

3. **缓存策略**
   - 微博热搜结果缓存（5分钟）
   - 内存存储，自动过期

### 微博热搜爬虫

支持两种爬虫方式，自动降级：

1. **Selenium 爬虫（推荐）** - 使用真实浏览器，能处理复杂反爬
   - 自动下载 ChromeDriver
   - 无头模式运行
   - 能绕过大部分反爬机制

2. **HTTP 爬虫** - 使用 `httpx` + `BeautifulSoup`
   - 轻量级，速度快
   - 可能被反爬拦截

3. **模拟数据** - 最后的降级方案
   - 当爬虫全部失败时使用
   - 确保功能可用

### LangChain 工具集成

微博热搜功能作为 LangChain Tool 集成：

```python
@tool
async def fetch_weibo_hot_search(limit: int = 40) -> str:
    """获取微博热搜榜..."""
```

Agent 会自动判断用户意图，当用户询问热搜相关问题时自动调用该工具。

## API 文档

完整的 API 文档可通过以下地址访问：

- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

### 主要端点

| 端点 | 方法 | 描述 | 认证 |
|------|------|------|------|
| `/api/auth/register` | POST | 用户注册 | 否 |
| `/api/auth/login` | POST | 用户登录 | 否 |
| `/api/auth/me` | GET | 获取当前用户 | 是 |
| `/api/chat` | POST | 发送消息（非流式） | 是 |
| `/api/chat/stream` | POST | 发送消息（流式） | 是 |
| `/api/conversations` | GET | 获取对话列表 | 是 |
| `/api/conversations/{id}` | GET | 获取对话详情 | 是 |
| `/api/conversations/{id}` | PUT | 更新对话标题 | 是 |
| `/api/conversations/{id}` | DELETE | 删除对话 | 是 |
| `/api/conversations/{id}/messages` | GET | 获取对话消息 | 是 |
| `/health` | GET | 健康检查 | 否 |

## 后期扩展计划

- [x] 微博热搜爬虫工具
- [x] 用户认证系统
- [x] 对话历史管理
- [x] 安全中间件和速率限制
- [x] 请求缓存优化
- [x] 数据库性能优化
- [ ] 其他新闻源（知乎、Hacker News 等）
- [ ] 定时任务调度
- [ ] 邮件通知功能
- [ ] 多轮对话上下文优化
- [ ] Prometheus 监控指标
- [ ] 分布式缓存（Redis）
- [ ] 消息队列（Celery/RQ）

## 故障排除

### 数据库连接失败
```
✗ Failed to connect to database: connection refused
```
- 检查 PostgreSQL 是否运行
- 确认数据库配置正确
- 验证用户权限

### JWT 警告
```
RuntimeWarning: JWT_SECRET is not set or is using default value!
```
- 生成新密钥：`python -c "import secrets; print(secrets.token_urlsafe(32))"`
- 更新 `.env` 文件中的 `JWT_SECRET`

### Selenium 爬虫失败
- 确保 Chrome 浏览器已安装
- 检查网络连接
- 查看 `WEIBO_USE_SELENIUM` 配置

## 许可证

MIT License
