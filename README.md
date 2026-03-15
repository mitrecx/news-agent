# News Agent

基于 LangChain 和 DeepSeek 的新闻助手 Agent，支持查询微博热搜。

## 功能

- 基于 LangChain 框架的智能对话
- 使用 DeepSeek 模型进行对话
- 流式输出响应
- 微博热搜查询功能（Agent 自动判断何时调用）
- 支持 Selenium 爬虫绕过反爬
- 自动降级策略（Selenium → HTTP → 模拟数据）
- **用户认证系统** - 需要登录才能使用
- Web 界面访问

## 用户认证

系统需要用户登录才能使用。

- 使用用户名和密码登录
- 默认测试账号：用户名 `test`，密码 `test123456`
- 登录后可以与 Agent 对话，查询微博热搜等

### 数据库配置

首次启动前需要初始化数据库：

```bash
# 运行数据库初始化脚本
uv run python scripts/init_db.py
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

   # 编辑 .env 文件，填入你的 DeepSeek API Key
   # DEEPSEEK_API_KEY=your_actual_api_key_here
   ```

### 启动服务

```bash
uv run python run.py
```

启动成功后会看到类似输出：
```
✓ News Agent initialized with model: deepseek-chat
✓ Loaded 1 tool(s): ['fetch_weibo_hot_search']
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
│   │   └── models.py    # 请求/响应模型
│   ├── auth/            # 认证模块
│   │   ├── router.py    # 认证路由
│   │   ├── models.py    # 用户模型
│   │   ├── security.py  # 安全工具（密码哈希、JWT）
│   │   ├── database.py  # 数据库连接
│   │   └── user_service.py # 用户服务
│   ├── tools/           # LangChain 工具集成
│   │   ├── __init__.py  # 工具导出
│   │   └── weibo.py     # 微博热搜爬虫
│   └── frontend/        # 前端页面
│       └── index.html
├── scripts/             # 脚本目录
│   └── init_db.py       # 数据库初始化脚本
├── .env.example         # 环境变量示例
├── pyproject.toml       # 项目配置
└── run.py              # 启动脚本
```

## 配置说明

| 环境变量 | 说明 | 默认值 |
|---------|------|--------|
| `DEEPSEEK_API_KEY` | DeepSeek API 密钥 | 必填 |
| `DEEPSEEK_BASE_URL` | DeepSeek API 地址 | `https://api.deepseek.com/v1` |
| `HOST` | 服务监听地址 | `0.0.0.0` |
| `PORT` | 服务端口 | `8000` |
| `AGENT_MODEL` | 使用的模型 | `deepseek-chat` |
| `AGENT_TEMPERATURE` | 模型温度参数 | `0.7` |
| `AGENT_MAX_TOKENS` | 最大 token 数 | `2000` |
| `WEIBO_SCRAPER_TIMEOUT` | 微博爬虫超时时间（秒） | `10` |
| `WEIBO_USE_SELENIUM` | 是否使用 Selenium 爬虫 | `true` |
| `DB_HOST` | 数据库主机 | `localhost` |
| `DB_PORT` | 数据库端口 | `5432` |
| `DB_USER` | 数据库用户名 | `your_username` |
| `DB_PASSWORD` | 数据库密码 | `your_password` |
| `DB_NAME` | 数据库名称 | `news_agent` |
| `JWT_SECRET` | JWT 密钥 | `your-secret-key-change-this` |

## 技术实现

### 微博热搜爬虫

支持两种爬虫方式，自动降级：

1. **Selenium 爬虫（推荐）** - 使用真实浏览器，能处理复杂反爬
   - 自动下载 ChromeDriver
   - 无头模式运行
   - 能绕过大部分反爬机制

2. **HTTP 爬虫** - 使用 `httpx` + `BeautifulSoup`
   - 轻量级，速度快
   - 可能被反爬拦截


### LangChain 工具集成

微博热搜功能作为 LangChain Tool 集成：

```python
@tool
async def fetch_weibo_hot_search(limit: int = 10) -> str:
    """获取微博热搜榜..."""
```

Agent 会自动判断用户意图，当用户询问热搜相关问题时自动调用该工具。

## 后期扩展计划

- [x] 微博热搜爬虫工具
- [ ] 其他新闻源（知乎、Hacker News 等）
- [ ] 数据持久化
- [ ] 定时任务调度
- [ ] 邮件通知功能
- [ ] 多轮对话优化
