# News Agent

基于 LangChain 和 DeepSeek 的新闻助手 Agent，支持查询微博热搜。

## 功能

- 基于 LangChain 框架的智能对话
- 使用 DeepSeek 模型进行对话
- 流式输出响应
- 微博热搜查询功能（Agent 自动判断何时调用）
- 支持 Selenium 爬虫绕过反爬
- 自动降级策略（Selenium → HTTP → 模拟数据）
- Web 界面访问

## 微博热搜功能说明

微博热搜功能使用 Selenium 爬虫获取真实数据，具有以下特点：

1. **自动降级策略**
   - 优先使用 Selenium 获取真实数据
   - 失败时降级到 HTTP 爬虫
   - 最终降级到模拟数据

2. **Selenium 配置**
   - 环境变量 `WEIBO_USE_SELENIUM=true` 启用
   - 首次运行会自动下载 ChromeDriver
   - 需要系统安装 Chrome 浏览器

3. **Chrome 安装**
   - **macOS**: `brew install --cask google-chrome`
   - **Ubuntu**: `sudo apt-get install google-chrome-stable`
   - **Windows**: 从 https://www.google.com/chrome/ 下载

4. **测试工具**
   - 访问 `/api/tools/test` 端点测试爬虫
   - Agent 会自动判断何时调用热搜工具

## 使用示例

你可以这样与 News Agent 对话：

- "今天有什么热搜？"
- "微博上最近有什么热门话题？"
- "看看现在的热搜榜"
- "大家都在讨论什么？"

Agent 会自动识别并调用微博热搜工具获取最新数据。

## API 文档

启动服务后，访问 `http://localhost:8000/docs` 查看 API 文档。

### 核心 API

#### POST /api/chat

与 Agent 进行对话（非流式）

**请求体：**
```json
{
  "message": "今天有什么热搜？",
  "history": []
}
```

**响应：**
```json
{
  "response": "📊 微博热搜榜：\n  1. xxx事件 (热度: 234.5万)\n  2. xxx话题..."
}
```

#### POST /api/chat/stream

与 Agent 进行对话（流式输出）

**请求体：**
```json
{
  "message": "今天有什么热搜？",
  "history": []
}
```

**响应：** Server-Sent Events (SSE) 流式数据

#### GET /health

健康检查

**响应：**
```json
{
  "status": "ok",
  "agent_ready": true
}
```

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
│   ├── tools/           # LangChain 工具集成
│   │   ├── __init__.py  # 工具导出
│   │   └── weibo.py     # 微博热搜爬虫
│   └── frontend/        # 前端页面
│       └── index.html
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

3. **模拟数据** - 当以上方式都失败时使用
   - 确保功能可用
   - 用于演示测试

**降级策略：** Selenium → HTTP 爬虫 → 模拟数据

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
