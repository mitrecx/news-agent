# 新闻助手 Agent - 项目规划文档

## 项目概述

**目标**: 开发一个个人新闻助手 agent，从微博热搜获取实时热点信息，为用户提供个性化的新闻摘要服务。

**当前范围**: 仅支持微博热搜单一数据源，后续可扩展至其他新闻源。

---

## 功能需求

### MVP (最小可行产品)

#### 1. 微博热搜采集
- 定时抓取微博热搜榜单（实时榜、热议榜等）
- 提取热搜标题、排名、热度值、分类标签
- 数据去重（基于标题相似度或唯一ID）

#### 2. 基础内容处理
- 生成热搜摘要（可选，使用 LLM）
- 关键词提取
- 简单分类（如：娱乐、社会、科技、财经等）

#### 3. 用户交互
- 命令行界面 (CLI)
- 查看当前热搜列表
- 按分类筛选
- 搜索关键词

#### 4. 通知推送
- 邮件推送（每日/每小时摘要）
- 支持 markdown 格式输出

---

## 技术架构

### 技术栈

```
语言: Python 3.12+
框架: FastAPI (Web服务) / Click (CLI)
数据库: SQLite (初期) → PostgreSQL (后期)
缓存: Redis
任务调度: APScheduler / Celery
HTTP客户端: httpx
HTML解析: BeautifulSoup4
LLM集成: OpenAI API / Anthropic API (可选)
```

### 项目结构

```
news-agent/
├── src/
│   ├── agents/
│   │   ├── weibo_agent.py      # 微博热搜采集 Agent
│   │   └── base.py             # Agent 基类
│   ├── services/
│   │   ├── collector.py        # 数据收集服务
│   │   ├── processor.py        # 内容处理服务
│   │   └── notifier.py         # 通知服务
│   ├── models/
│   │   └── news.py             # 数据模型
│   ├── database/
│   │   ├── client.py           # 数据库客户端
│   │   └── repositories.py     # 数据访问层
│   ├── config.py               # 配置管理
│   └── main.py                 # CLI 入口
├── data/
│   └── cache/                  # 缓存目录
├── tests/
├── requirements.txt
└── .env.example
```

---

## 数据模型

### 热搜条目 (NewsItem)

```python
{
    "id": "str",                  # 唯一标识
    "title": "str",               # 热搜标题
    "rank": "int",                # 排名
    "hot_value": "int",           # 热度值
    "category": "str",            # 分类
    "url": "str",                 # 微博链接
    "collected_at": "datetime",   # 采集时间
    "summary": "str | None",      # 摘要（可选）
    "keywords": "List[str]"       # 关键词
}
```

---

## 实现阶段

### Phase 1: 基础采集 (Week 1)
- [ ] 微博热搜爬虫实现
- [ ] 数据模型定义
- [ ] SQLite 数据库初始化
- [ ] 基础数据存储

### Phase 2: CLI 工具 (Week 2)
- [ ] CLI 命令框架搭建
- [ ] 查看热搜列表命令
- [ ] 按分类筛选功能
- [ ] 搜索功能

### Phase 3: 增强功能 (Week 3)
- [ ] 定时任务调度
- [ ] 数据去重优化
- [ ] 关键词提取
- [ ] 邮件通知功能

### Phase 4: LLM 集成 (可选, Week 4)
- [ ] 接入 LLM API
- [ ] 智能摘要生成
- [ ] 智能分类
- [ ] 个性化推荐

---

## 扩展规划 (未来)

### 数据源扩展
- 知乎热榜
- GitHub Trending
- Hacker News
- Reddit
- V2EX
- 各大新闻网站 RSS

### 功能增强
- Web 界面
- 多用户支持
- 订阅管理
- 历史趋势分析
- 舆情监控告警

---

## 配置示例

```env
# 数据采集
COLLECTION_INTERVAL=3600  # 采集间隔（秒）

# 邮件通知
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=your_email@gmail.com
SMTP_PASSWORD=your_password
NOTIFICATION_RECIPIENT=recipient@example.com

# LLM (可选)
OPENAI_API_KEY=sk-xxx
LLM_MODEL=gpt-4o-mini

# 数据库
DATABASE_URL=sqlite:///./data/news.db
```

---

## 依赖包

```
# 核心
fastapi
uvicorn
click

# 爬虫
httpx
beautifulsoup4
lxml

# 数据库
sqlalchemy
alembic

# 任务调度
apscheduler

# 工具
python-dotenv
pydantic
```

---

## 风险与注意事项

1. **反爬虫机制**: 微博可能有反爬措施，需要设置合理的请求频率和 User-Agent
2. **数据合规**: 仅用于个人使用，遵守相关服务条款
3. **API 限制**: 如使用 LLM API，注意调用频率限制
4. **隐私保护**: 本地存储，不上传敏感数据

---

## 下一步行动

1. 初始化 Python 项目结构
2. 配置开发环境和依赖
3. 实现微博热搜采集模块
4. 搭建 CLI 基础框架
