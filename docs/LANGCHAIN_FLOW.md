# News-Agent LangChain 处理流程（简化版）

本文档详细描述 LangChain Agent 处理 "今日微博热搜" 的核心流程。

---

## 目录

1. [整体流程](#整体流程)
2. [Agent 初始化](#agent-初始化)
3. [LLM 工具调用机制](#llm-工具调用机制)
4. [工具执行流程](#工具执行流程)
5. [响应返回](#响应返回)
6. [时序图](#时序图)

---

## 整体流程

```
用户消息 "今日微博热搜"
         ↓
    [构建 LangChain 消息]
         ↓
    [调用 LLM (DeepSeek)]
         ↓
    [LLM 决策: 需要工具]
         ↓
    [执行工具: fetch_weibo_hot_search]
         ↓
    [爬取微博热搜]
         ↓
    [返回结果给 LLM]
         ↓
    [格式化输出]
         ↓
    [流式返回给用户]
```

---

## Agent 初始化

**位置**: [src/agent/base.py](../src/agent/base.py:22-39)

```python
from langchain_openai import ChatOpenAI
from langchain_core.tools import tool

class NewsAgent:
    def __init__(self, tools: list | None = None):
        # 1. 创建 DeepSeek LLM 实例
        self.llm = ChatOpenAI(
            model="deepseek-chat",
            api_key=settings.deepseek_api_key,
            base_url="https://api.deepseek.com",
            temperature=0.7,
            max_tokens=2000,
        )

        # 2. 定义工具
        self.tools = tools or []

        # 3. 绑定工具到 LLM
        if self.tools:
            self.llm_with_tools = self.llm.bind_tools(self.tools)
        else:
            self.llm_with_tools = self.llm
```

**工具定义**: [src/tools/__init__.py](../src/tools/__init__.py:11-66)

```python
from langchain_core.tools import tool

@tool
async def fetch_weibo_hot_search(limit: int = 40) -> str:
    """
    获取微博热搜榜 TOP 40

    使用场景：当用户询问微博热搜、热门话题、今日热点等

    Args:
        limit: 返回热搜数量，默认40条，最多50条

    Returns:
        格式化的热搜列表（包含描述）
    """
    scraper = get_scraper()
    items = await scraper.fetch_hot_search(limit, fetch_descriptions=False)

    # 格式化输出
    lines = ["📊 微博热搜榜：\n"]
    for item in items:
        if item.description:
            lines.append(f"  {item.rank}. {item.title} (热度: {item.hot_value})\n     💡 {item.description}\n")
        else:
            lines.append(f"  {item.rank}. {item.title} (热度: {item.hot_value})\n")

    return "\n".join(lines)
```

---

## LLM 工具调用机制

### 1. 流式聊天入口

**位置**: [src/agent/base.py](../src/agent/base.py:124-180)

```python
async def chat_stream(self, message: str, history: list[dict] | None = None):
    """
    流式聊天入口

    Args:
        message: 用户消息
        history: 对话历史

    Yields:
        响应内容片段
    """
    from langchain_core.messages import HumanMessage, AIMessage

    # 1. 构建消息历史
    lc_messages = []
    for msg in history:
        if msg.get("role") == "user":
            lc_messages.append(HumanMessage(content=msg.get("content")))
        elif msg.get("role") == "assistant":
            lc_messages.append(AIMessage(content=msg.get("content")))

    # 2. 添加当前用户消息
    lc_messages.append(HumanMessage(content=message))

    # 3. 调用 LLM（首次，检测是否需要工具）
    response = await self.llm_with_tools.ainvoke(lc_messages)
```

### 2. LangChain 消息格式

**消息类型**:

```python
from langchain_core.messages import HumanMessage, AIMessage, ToolMessage

# 用户消息
human_msg = HumanMessage(content="今日微博热搜")

# AI 消息（可能包含工具调用）
ai_msg = AIMessage(
    content="",
    tool_calls=[
        {
            "id": "call_abc123",
            "name": "fetch_weibo_hot_search",
            "args": {"limit": 40}
        }
    ]
)

# 工具结果消息
tool_msg = ToolMessage(
    content="📊 微博热搜榜：\n  1. ...",
    tool_call_id="call_abc123"
)
```

### 3. 工具调用检测

**位置**: [src/agent/base.py](../src/agent/base.py:186-232)

```python
# 检查 LLM 响应是否包含工具调用
if hasattr(response, 'tool_calls') and response.tool_calls:
    # 示例: response.tool_calls = [
    #   {
    #     'name': 'fetch_weibo_hot_search',
    #     'args': {'limit': 40},
    #     'id': 'call_abc123'
    #   }
    # ]

    # 判断是否是微博热搜工具
    is_weibo_tool = any(
        tc.get('name') == 'fetch_weibo_hot_search'
        for tc in response.tool_calls
    )

    # 执行工具调用
    weibo_returned = False
    for tool_call in response.tool_calls:
        tool_name = tool_call.get('name')
        tool_args = tool_call.get('args', {})

        # 查找并执行工具
        for tool in self.tools:
            if tool.name == tool_name:
                # 执行工具
                result = await tool.ainvoke(tool_args)

                # 添加工具结果到消息历史
                lc_messages.append(response)      # AI 消息（包含 tool_calls）
                lc_messages.append(ToolMessage(
                    content=result,
                    tool_call_id=tool_call.get('id', '')
                ))

                # 如果是微博热搜，直接返回
                if result.startswith("📊 微博热搜榜："):
                    yield result
                    weibo_returned = True
                break

    # 如果微博热搜已返回，跳过后续 LLM 处理
    if weibo_returned:
        return
```

---

## 工具执行流程

### 1. 工具调用入口

**位置**: [src/tools/__init__.py](../src/tools/__init__.py:30-65)

```python
@tool
async def fetch_weibo_hot_search(limit: int = 40) -> str:
    """
    工具被 LangChain 自动调用

    参数由 LLM 自动生成:
    - limit: LLM 根据用户需求决定数量
    """
    # 参数验证
    if limit < 1:
        limit = 10
    if limit > 50:
        limit = 50

    logger.info(f"🔍 工具被调用: fetch_weibo_hot_search(limit={limit})")

    # 获取爬虫实例
    scraper = get_scraper()

    # 执行爬取
    items = await scraper.fetch_hot_search(limit, fetch_descriptions=False)

    # 格式化返回
    lines = ["📊 微博热搜榜：\n"]
    for item in items:
        if item.description:
            lines.append(f"  {item.rank}. {item.title} (热度: {item.hot_value})\n     💡 {item.description}\n")
        else:
            lines.append(f"  {item.rank}. {item.title} (热度: {item.hot_value})\n")

    return "\n".join(lines)
```

### 2. 三级降级爬取策略

**位置**: [src/tools/weibo.py](../src/tools/weibo.py:623-693)

```python
async def _fetch_hot_search_items(self, limit: int):
    """
    三级降级策略，确保服务高可用
    """

    # 策略 1: Selenium 爬虫（优先，能处理动态内容）
    if self.use_selenium:
        try:
            logger.info("🌐 尝试使用 Selenium 爬取...")
            items = await self._fetch_with_selenium(limit)
            logger.info(f"✅ Selenium 爬取成功: {len(items)} 条")
            return items
        except Exception as e:
            logger.warning(f"⚠️ Selenium 爬取失败: {e}")

    # 策略 2: HTTP 爬虫（降级，速度快但可能被拦截）
    try:
        logger.info("🌐 尝试使用 HTTP 爬虫...")
        async with httpx.AsyncClient(timeout=10) as client:
            response = await client.get(
                "https://s.weibo.com/top/summary?cate=realtimehot",
                headers=self.headers
            )
        items = self._parse_hot_search(response.text, limit)
        logger.info(f"✅ HTTP 爬取成功: {len(items)} 条")
        return items
    except Exception as e:
        logger.warning(f"⚠️ HTTP 爬取失败: {e}")

    # 策略 3: Selenium（如果之前没用过）
    if not self.use_selenium and SELENIUM_AVAILABLE:
        try:
            items = await self._fetch_with_selenium(limit)
            return items
        except Exception as e:
            logger.warning(f"⚠️ Selenium 也失败: {e}")

    # 策略 4: 模拟数据（兜底，保证服务可用）
    logger.info("📦 使用模拟数据")
    items = self._get_mock_data(limit)
    return items
```

### 3. Selenium 爬虫详细流程

**位置**: [src/tools/weibo.py](../src/tools/weibo.py:131-204)

```python
def _selenium_fetch_sync(self, limit: int):
    """
    Selenium 同步爬取（在线程池中运行）
    """
    from selenium import webdriver
    from selenium.webdriver.chrome.service import Service
    from webdriver_manager.chrome import ChromeDriverManager

    # 1. 配置 Chrome（无头模式）
    chrome_options = Options()
    chrome_options.add_argument('--headless')
    chrome_options.add_argument('--no-sandbox')
    chrome_options.add_argument('--disable-dev-shm-usage')

    # 2. 自动下载 ChromeDriver
    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=chrome_options)

    try:
        # 3. 访问微博热搜页面
        driver.get("https://s.weibo.com/top/summary?cate=realtimehot")

        # 4. 等待页面加载
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.TAG_NAME, "body"))
        )
        time.sleep(2)  # 等待动态内容

        # 5. 获取页面源码
        page_source = driver.page_source

        # 6. 解析热搜数据
        items = self._parse_hot_search(page_source, limit)
        return items

    finally:
        driver.quit()
```

### 4. HTML 解析

**位置**: [src/tools/weibo.py](../src/tools/weibo.py:206-305)

```python
def _parse_hot_search(self, html: str, limit: int):
    """
    使用 BeautifulSoup 解析微博热搜页面
    """
    from bs4 import BeautifulSoup

    soup = BeautifulSoup(html, "lxml")
    items = []

    # 微博热搜在 #pl_top_realtimehot table tbody 中
    tbody = soup.select_one("#pl_top_realtimehot table tbody")
    rows = tbody.find_all("tr", limit=limit + 1)

    for idx, row in enumerate(rows):
        if idx == 0 and row.find("th"):
            continue  # 跳过表头

        cells = row.find_all("td")

        # 解析排名
        rank = int(cells[0].get_text(strip=True))

        # 解析标题和链接
        link = cells[1].find("a")
        title = link.get_text(strip=True)
        url = link.get("href", "")
        if url and not url.startswith("http"):
            url = "https://s.weibo.com" + url

        # 解析热度
        hot_value = cells[2].get_text(strip=True)

        # 解析图标（热、新等）
        icon_span = cells[1].find("span", class_="icon")
        icon = icon_span.get_text(strip=True) if icon_span else None

        items.append(HotSearchItem(
            rank=rank,
            title=title,
            hot_value=hot_value,
            category="",
            url=url,
            icon=icon
        ))

    return items
```

### 5. 缓存加载

**位置**: [src/tools/weibo.py](../src/tools/weibo.py:703-729)

```python
async def _load_cached_descriptions(self, items: list):
    """
    从数据库缓存加载已有描述（避免重复爬取）
    """
    await self._ensure_cache_manager()

    # 批量查询缓存
    titles = [item.title for item in items]
    cache_map = await self._cache_manager.batch_get(titles)

    now = datetime.now()
    cache_hits = 0

    for item in items:
        cached = cache_map.get(item.title)
        if cached:
            # 检查缓存是否过期（8小时）
            age = (now - cached['created_at']).total_seconds()
            if age < 28800:  # 8小时 = 28800秒
                item.description = cached['description']
                item.description_source = cached['description_source']
                cache_hits += 1

    logger.info(f"✓ 缓存命中: {cache_hits}/{len(items)}")
```

---

## 响应返回

### 1. 工具结果返回

**位置**: [src/agent/base.py](../src/agent/base.py:216-232)

```python
# 执行工具
result = await tool.ainvoke(tool_args)
# result = "📊 微博热搜榜：\n  1. 2025年度科技热点盘点..."

# 添加工具结果到消息历史
lc_messages.append(response)  # AI 消息（包含 tool_calls）
lc_messages.append(ToolMessage(
    content=result,
    tool_call_id=tool_call.get('id', '')
))

# 检查是否是微博热搜结果
if result.startswith("📊 微博热搜榜："):
    # 直接返回，不再经过 LLM
    yield result
    return
```

### 2. 流式返回

**位置**: [src/agent/base.py](../src/agent/base.py:124-255)

```python
async def chat_stream(self, message: str, history: list[dict] | None = None):
    """
    流式返回响应
    """
    # ... 构建 lc_messages ...

    # 调用 LLM
    response = await self.llm_with_tools.ainvoke(lc_messages)

    # 检测工具调用
    if hasattr(response, 'tool_calls') and response.tool_calls:
        # ... 执行工具 ...

        # 微博热搜直接返回
        if result.startswith("📊 微博热搜榜："):
            yield result  # yield 生成器
            return

    # 其他情况，流式返回 LLM 响应
    async for chunk in self.llm_with_tools.astream(lc_messages):
        if hasattr(chunk, 'content') and chunk.content:
            yield chunk.content
```

### 3. 生成器调用链

```
agent.chat_stream("今日微博热搜")
  └─ yield "📊 微博热搜榜：\n"
  └─ yield "  1. 2025年度科技热点盘点 (热度: 356.2万)\n"
  └─ yield "  2. 春节档电影票房创新高 (热度: 298.5万)\n"
  └─ ...
```

---

## 时序图

```
调用方          NewsAgent              LLM (DeepSeek)          工具                    微博
   │                 │                      │                     │                      │
   │  chat_stream()  │                      │                     │                      │
   ├────────────────►│                      │                     │                      │
   │                 │                      │                     │                      │
   │                 │  构建消息            │                     │                      │
   │                 │  HumanMessage("今日微博热搜")            │                      │
   │                 │                      │                     │                      │
   │                 │  ainvoke(lc_messages)│                     │                      │
   │                 ├─────────────────────►│                     │                      │
   │                 │                      │                     │                      │
   │                 │                      │  分析用户意图       │                      │
   │                 │                      │  检索可用工具       │                      │
   │                 │                      │                     │                      │
   │                 │                      │  决策: 需要调用工具  │                      │
   │                 │◄─────────────────────┤                     │                      │
   │                 │  AIMessage with      │                     │                      │
   │                 │  tool_calls=[        │                     │                      │
   │                 │    {name: "fetch_    │                     │                      │
   │                 │     weibo_hot_       │                     │                      │
   │                 │     search",         │                     │                      │
   │                 │     args: {limit:40}│                     │                      │
   │                 │    }                 │                     │                      │
   │                 │  ]                   │                     │                      │
   │                 │                      │                     │                      │
   │                 │  检测 tool_calls     │                     │                      │
   │                 │  执行工具            │                     │                      │
   │                 ├──────────────────────────────────────────►│                      │
   │                 │                      │                     │                      │
   │                 │                      │                     │  三级降级策略        │
   │                 │                      │                     │                      │
   │                 │                      │                     │  1. 尝试 Selenium    │
   │                 │                      │                     ├─────────────────────►│
   │                 │                      │                     │                      │
   │                 │                      │                     │  2. 访问热搜页面     │
   │                 │                      │                     │◄─────────────────────┤
   │                 │                      │                     │                      │
   │                 │                      │                     │  3. 解析 HTML        │
   │                 │                      │                     │  4. 加载缓存         │
   │                 │                      │                     │  5. 格式化输出       │
   │                 │                      │                     │                      │
   │                 │◄──────────────────────────────────────────┤  str result          │
   │                 │  "📊 微博热搜榜：\n  1. ..."             │                      │
   │                 │                      │                     │                      │
   │                 │  添加 ToolMessage    │                     │                      │
   │                 │  lc_messages.append( │                     │                      │
   │                 │    ToolMessage(      │                     │                      │
   │                 │      content=result, │                     │                      │
   │                 │      tool_call_id=...│                     │                      │
   │                 │    )                 │                      │
   │                 │  )                   │                     │                      │
   │                 │                      │                     │                      │
   │                 │  检查结果类型        │                     │                      │
   │                 │  is_weibo_result =   │                     │                      │
   │                 │    True              │                     │                      │
   │                 │                      │                     │                      │
   │                 │  直接返回（跳过 LLM） │                     │                      │
   │◄════════════════╪═════════════════════╪═════════════════════╪═══════════════════════╪═══════════════╡
   │  yield result   │                      │                     │                      │
   │                 │                      │                     │                      │
```

---

## 关键概念

### 1. LangChain 消息类型

| 类型 | 说明 | 示例 |
|------|------|------|
| `HumanMessage` | 用户消息 | `HumanMessage(content="今日微博热搜")` |
| `AIMessage` | AI 响应（可能包含 tool_calls） | `AIMessage(content="", tool_calls=[...])` |
| `ToolMessage` | 工具执行结果 | `ToolMessage(content="热搜数据", tool_call_id="xxx")` |

### 2. 工具调用流程

```
1. LLM 分析用户意图
   └─ 决定是否需要工具

2. LLM 返回 AIMessage
   └─ 包含 tool_calls 字段

3. Agent 检测 tool_calls
   └─ 提取工具名称和参数

4. 执行工具
   └─ await tool.ainvoke(args)

5. 添加 ToolMessage
   └─ 将工具结果加入消息历史

6. 决定下一步
   └─ 微博热搜: 直接返回
   └─ 其他工具: 再次调用 LLM 生成最终响应
```

### 3. bind_tools 机制

```python
# 绑定工具前
llm = ChatOpenAI(model="deepseek-chat")

# 绑定工具后
llm_with_tools = llm.bind_tools([fetch_weibo_hot_search])

# LLM 会自动感知工具定义
# 在响应中自动生成 tool_calls
```

**LLM 收到的系统提示**（自动生成）:

```
You have access to the following tools:

fetch_weibo_hot_search: 获取微博热搜榜 TOP 40
Args:
  limit: 返回热搜数量，默认40条，最多50条 (type: integer)

When you need to call a tool, respond with a JSON object
in the following format:
{
  "tool_calls": [
    {
      "name": "tool_name",
      "arguments": {"arg1": "value1"}
    }
  ]
}
```

### 4. 流式 vs 非流式

| 方法 | 说明 | 用途 |
|------|------|------|
| `ainvoke()` | 一次性获取完整响应 | 工具调用决策 |
| `astream()` | 流式返回响应片段 | 最终响应输出 |
| `ainvoke()` + yield | 手动流式 | 微博热搜直接返回 |

---

## 代码示例：完整流程

```python
# 1. 初始化 Agent
agent = NewsAgent(tools=[fetch_weibo_hot_search])

# 2. 调用流式聊天
async for chunk in agent.chat_stream("今日微博热搜", history=[]):
    print(chunk, end="")

# 输出:
# 📊 微博热搜榜：
#   1. 2025年度科技热点盘点 (热度: 356.2万)
#      💡 这是关于2025年科技领域的热点话题...
#   2. 春节档电影票房创新高 (热度: 298.5万)
#      💡 春节期间多部影片票房表现亮眼...
#   ...
```

---

## 总结

LangChain 处理 "今日微博热搜" 的核心流程：

1. **消息构建**: 将用户输入转换为 `HumanMessage`
2. **LLM 决策**: DeepSeek 分析意图，决定调用工具
3. **工具执行**: `fetch_weibo_hot_search` 爬取微博热搜
4. **结果返回**: 直接 yield 工具结果（跳过二次 LLM 处理）
5. **流式输出**: 生成器逐块返回给调用方

**关键特性**:
- ✅ 自动工具调用（LLM 自主决策）
- ✅ 异步执行（async/await）
- ✅ 流式返回（提高用户体验）
- ✅ 三级降级（保证高可用）
- ✅ 缓存机制（减少重复爬取）
