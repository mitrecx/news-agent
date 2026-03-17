# News-Agent 消息处理流程详解

本文档详细描述了当用户发送消息 "今日微博热搜" 时，news-agent 系统的完整处理流程。

---

## 目录

1. [系统架构概览](#系统架构概览)
2. [前端处理流程](#前端处理流程)
3. [后端 API 处理流程](#后端-api-处理流程)
4. [Agent 处理流程](#agent-处理流程)
5. [工具执行流程](#工具执行流程)
6. [响应返回流程](#响应返回流程)
7. [数据持久化](#数据持久化)
8. [时序图](#时序图)

---

## 系统架构概览

news-agent 采用前后端分离架构，主要组件包括：

- **前端**: Vue.js 3 + TypeScript + Pinia + Element Plus
- **后端**: FastAPI + LangChain + DeepSeek LLM
- **数据库**: PostgreSQL (asyncpg)
- **爬虫**: Selenium + BeautifulSoup + httpx

```
┌─────────────────┐      HTTP/SSE      ┌─────────────────┐
│                 │  ◄──────────────►  │                 │
│  Vue.js 前端    │                     │  FastAPI 后端   │
│  (端口 6173)    │                     │  (端口 8000)    │
└─────────────────┘                     └─────────────────┘
                                                 │
                                                 ▼
                                        ┌─────────────────┐
                                        │                 │
                                        │  LangChain Agent│
                                        │  + DeepSeek LLM │
                                        └─────────────────┘
                                                 │
                                                 ▼
                                        ┌─────────────────┐
                                        │                 │
                                        │  微博热搜爬虫   │
                                        │  (Selenium/HTTP)│
                                        └─────────────────┘
```

---

## 前端处理流程

### 1. 用户输入

**位置**: [ChatView.vue](../src/frontend-vue/src/views/ChatView.vue)

用户在聊天输入框中输入 "今日微博热搜" 并点击发送按钮。

```vue
<!-- ChatInput 组件 -->
<ChatInput
  :is-streaming="chatStore.isStreaming"
  :is-connected="chatStore.isConnected"
  :messages="chatStore.messages"
  @send="handleSend"
/>
```

### 2. 消息发送触发

**位置**: [useChatStream.ts](../src/frontend-vue/src/composables/useChatStream.ts):36-132

```typescript
const sendMessage = async (message: string) => {
  // 1. 防重复提交检查
  if (chatStore.isSending) {
    return // 正在发送中，忽略重复请求
  }

  // 2. 认证检查
  if (!authStore.token) {
    ElMessage.error('请先登录')
    return
  }

  // 3. 连接状态检查
  if (!chatStore.isConnected) {
    ElMessage.error('Agent 未就绪，请稍后重试')
    return
  }

  // 4. 添加用户消息到本地状态
  chatStore.addMessage({ role: 'user', content: message })

  // 5. 添加空的助手消息（用于流式更新）
  chatStore.addMessage({ role: 'assistant', content: '' })

  // 6. 发起 SSE 请求
  await sendChatStream(
    {
      message,
      history: chatStore.messages.slice(0, -1),  // 排除刚添加的空消息
      conversation_id: chatStore.conversationId ?? undefined,
    },
    // onChunk 回调
    (content: string) => {
      currentResponse.value += content
      chatStore.updateLastMessage(currentResponse.value)
    },
    // onError 回调
    (error: string) => {
      ElMessage.error('发生错误: ' + error)
    },
    // onComplete 回调
    async (convId?: number) => {
      if (convId) {
        chatStore.setConversationId(convId)
      }
    },
    authStore.token,
    // onProgress 回调
    (message: string) => {
      progressMessage.value = message
    }
  )
}
```

### 3. SSE 请求发送

**位置**: [chat.ts](../src/frontend-vue/src/api/chat.ts):15-90

使用 `@microsoft/fetch-event-source` 库建立 SSE 连接：

```typescript
await fetchEventSource('/api/chat/stream', {
  method: 'POST',
  headers: {
    'Content-Type': 'application/json',
    Authorization: `Bearer ${token}`,
  },
  body: JSON.stringify(data),
  onmessage: (event) => {
    const chunk = JSON.parse(event.data)
    if (chunk.content) {
      onChunk(chunk.content)  // 逐块更新 UI
    } else if (chunk.done) {
      onComplete(chunk.conversation_id)
    }
  },
  openWhenHidden: false,
})
```

**请求数据格式**:
```json
{
  "message": "今日微博热搜",
  "history": [],
  "conversation_id": null
}
```

---

## 后端 API 处理流程

### 1. 请求接收与认证

**位置**: [server.py](../src/api/server.py):324-432

```python
@app.post("/api/chat/stream")
async def chat_stream(
    request: ChatRequest,
    current_user: User = Depends(get_current_user)
):
```

**认证流程**:

1. 从 HTTP Header 中提取 JWT Token: `Authorization: Bearer <token>`
2. 验证 Token 有效性
3. 解析 Token 获取用户信息
4. 如果 Token 无效，返回 401 Unauthorized

**认证实现**: [auth/router.py](../src/auth/router.py)

```python
def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(HTTPBearer())
) -> User:
    token = credentials.credentials
    payload = jwt.decode(token, settings.secret_key, algorithms=[settings.algorithm])
    user_id = payload.get("sub")
    # 从数据库获取用户信息
    user = get_user_by_id(db, user_id)
    return user
```

### 2. 对话管理

**位置**: [server.py](../src/api/server.py):342-365

```python
conversation_id = request.conversation_id
async with db.pool.acquire() as conn:
    # 创建新对话或获取已有对话
    if not conversation_id:
        conversation = await ConversationService.create_conversation(
            conn, current_user.id, "新对话"
        )
        conversation_id = conversation["id"]
    else:
        conversation = await ConversationService.get_conversation_by_id(
            conn, conversation_id, current_user.id
        )

    # 保存用户消息
    await ConversationService.add_message(
        conn, conversation_id, "user", request.message
    )

    # 获取历史消息（用于 Agent 上下文）
    history = await ConversationService.get_message_history_for_agent(
        conn, conversation_id, current_user.id, exclude_last=True
    )
```

**数据库表结构**:

```sql
-- conversations 表
CREATE TABLE conversations (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL,
    title VARCHAR(255) DEFAULT '新对话',
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- messages 表
CREATE TABLE messages (
    id SERIAL PRIMARY KEY,
    conversation_id INTEGER NOT NULL,
    role VARCHAR(20) NOT NULL,  -- 'user' or 'assistant'
    content TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT NOW()
);
```

### 3. Agent 调用

**位置**: [server.py](../src/api/server.py):377-432

```python
async def generate():
    """生成流式响应"""
    try:
        full_response = ""

        # 发送开始信号
        yield f"data: {json.dumps({'type': 'start', 'message': '正在处理您的请求...'})}\n\n"

        # 流式响应
        async for chunk in agent.chat_stream(request.message, history):
            full_response += chunk
            # SSE 格式发送
            yield f"data: {json.dumps({'content': chunk})}\n\n"

        # 发送保存进度
        yield f"data: {json.dumps({'type': 'progress', 'message': '正在保存对话...'})}\n\n"

        # 保存助手响应
        async with db.pool.acquire() as conn:
            await ConversationService.add_message(
                conn, conversation_id, "assistant", full_response
            )

        # 发送完成信号
        yield f"data: {json.dumps({'conversation_id': conversation_id, 'done': True})}\n\n"

    except Exception as e:
        yield f"data: {json.dumps({'error': str(e)})}\n\n"

return StreamingResponse(
    generate(),
    media_type="text/event-stream",
    headers={
        "Cache-Control": "no-cache",
        "Connection": "keep-alive",
    }
)
```

---

## Agent 处理流程

### 1. NewsAgent 初始化

**位置**: [base.py](../src/agent/base.py):22-39

```python
class NewsAgent:
    def __init__(self, tools: list | None = None):
        # 创建 DeepSeek LLM 实例
        self.llm = ChatOpenAI(
            model=settings.agent_model,          # "deepseek-chat"
            api_key=settings.deepseek_api_key,
            base_url=settings.deepseek_base_url, # "https://api.deepseek.com"
            temperature=0.7,
            max_tokens=2000,
        )

        # 绑定工具
        self.tools = tools or []
        if self.tools:
            self.llm_with_tools = self.llm.bind_tools(self.tools)
```

### 2. 流式聊天入口

**位置**: [base.py](../src/agent/base.py):124-255

```python
async def chat_stream(self, message: str, history: list[dict] | None = None):
    # 1. 构建消息历史
    messages = []
    for msg in history:
        if msg.get("role") == "user":
            messages.append(("human", msg.get("content")))
        elif msg.get("role") == "assistant":
            messages.append(("ai", msg.get("content")))

    # 添加当前消息
    messages.append(("human", message))

    # 2. 转换为 LangChain 格式
    from langchain_core.messages import HumanMessage, AIMessage
    lc_messages = []
    for role, content in messages:
        if role == "human":
            lc_messages.append(HumanMessage(content=content))
        else:
            lc_messages.append(AIMessage(content=content))

    # 3. 调用 LLM（检测是否需要工具）
    response = await self.llm_with_tools.ainvoke(lc_messages)
```

### 3. 工具调用检测

**位置**: [base.py](../src/agent/base.py):187-232

```python
# 检查 LLM 响应是否包含工具调用
if hasattr(response, 'tool_calls') and response.tool_calls:
    # 判断是否是微博热搜工具
    is_weibo_tool = any(
        tc.get('name') == 'fetch_weibo_hot_search'
        for tc in response.tool_calls
    )

    # 执行工具调用
    for tool_call in response.tool_calls:
        tool_name = tool_call.get('name')
        tool_args = tool_call.get('args', {})

        # 查找并执行工具
        for tool in self.tools:
            if tool.name == tool_name:
                result = await tool.ainvoke(tool_args)

                # 添加工具结果到消息列表
                lc_messages.append(response)
                lc_messages.append(ToolMessage(
                    content=result,
                    tool_call_id=tool_call.get('id', '')
                ))

                # 如果是微博热搜，直接返回结果
                if result.startswith("📊 微博热搜榜："):
                    yield result
                    return
```

---

## 工具执行流程

### 1. 工具定义

**位置**: [weibo.py](../src/tools/__init__.py):11-66

```python
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

### 2. 爬虫初始化

**位置**: [weibo.py](../src/tools/weibo.py):76-103

```python
def get_scraper(use_selenium: bool | None = None) -> WeiboScraper:
    global _scraper
    if _scraper is None:
        settings = get_settings()
        use_selenium = settings.weibo_use_selenium
        cookie = settings.weibo_cookie

        _scraper = WeiboScraper(
            use_selenium=use_selenium,
            cookie=cookie
        )
    return _scraper
```

### 3. 三级降级爬取策略

**位置**: [weibo.py](../src/tools/weibo.py):623-693

```python
async def _fetch_hot_search_items(self, limit: int) -> list[HotSearchItem]:
    # 策略 1: Selenium 爬虫（优先）
    if self.use_selenium:
        try:
            logger.info("🌐 尝试使用 Selenium 爬取...")
            items = await self._fetch_with_selenium(limit)
            return items
        except Exception as e:
            logger.warning(f"⚠️ Selenium 爬取失败: {e}")

    # 策略 2: HTTP 爬虫（降级）
    try:
        logger.info("🌐 尝试使用 HTTP 爬虫...")
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.get(
                self.WEIBO_HOT_URL,
                headers=self.headers,
                follow_redirects=True
            )
        items = self._parse_hot_search(response.text, limit)
        return items
    except Exception as e:
        logger.warning(f"⚠️ HTTP 爬取失败: {e}")

    # 策略 3: Selenium（如果之前没用过）
    if not self.use_selenium and SELENIUM_AVAILABLE:
        try:
            items = await self._fetch_with_selenium(limit)
            return items
        except Exception as e:
            logger.warning(f"⚠️ Selenium 爬取也失败: {e}")

    # 策略 4: 模拟数据（兜底）
    logger.info("📦 使用模拟数据")
    items = self._get_mock_data(limit)
    return items
```

### 4. Selenium 爬虫详细流程

**位置**: [weibo.py](../src/tools/weibo.py):107-204

```python
async def _fetch_with_selenium(self, limit: int) -> List[HotSearchItem]:
    # 在线程池中运行 Selenium（避免阻塞事件循环）
    loop = asyncio.get_event_loop()
    return await asyncio.wait_for(
        loop.run_in_executor(None, self._selenium_fetch_sync, limit),
        timeout=30.0
    )

def _selenium_fetch_sync(self, limit: int) -> List[HotSearchItem]:
    # 1. 配置 Chrome 选项
    chrome_options = Options()
    chrome_options.add_argument('--headless')  # 无头模式
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
        time.sleep(2)  # 等待动态内容加载

        # 5. 获取页面源码
        page_source = driver.page_source

        # 6. 解析热搜数据
        items = self._parse_hot_search(page_source, limit)
        return items
    finally:
        driver.quit()
```

### 5. HTML 解析

**位置**: [weibo.py](../src/tools/weibo.py):206-305

```python
def _parse_hot_search(self, html: str, limit: int) -> List[HotSearchItem]:
    soup = BeautifulSoup(html, "lxml")
    items = []

    # 微博热搜在 #pl_top_realtimehot table tbody 中
    tbody = soup.select_one("#pl_top_realtimehot table tbody")
    rows = tbody.find_all("tr", limit=limit + 1)

    for idx, row in enumerate(rows):
        # 跳过表头
        if idx == 0 and row.find("th"):
            continue

        cells = row.find_all("td")

        # 解析排名
        rank = int(cells[0].get_text(strip=True))

        # 解析标题和链接
        link = cells[1].find("a")
        title = link.get_text(strip=True)
        url = link.get("href", "")
        if url and not url.startswith("http"):
            url = "https://s.weibo.com" + url

        # 解析热度值
        hot_value = cells[2].get_text(strip=True)

        # 解析图标（热、新等）
        icon_span = cells[1].find("span", class_="icon")
        icon = icon_span.get_text(strip=True) if icon_span else None

        # 创建热搜条目
        item = HotSearchItem(
            rank=rank,
            title=title,
            hot_value=hot_value,
            category="",
            url=url,
            icon=icon
        )
        items.append(item)

    return items
```

### 6. 缓存加载

**位置**: [weibo.py](../src/tools/weibo.py):703-729

```python
async def _load_cached_descriptions(self, items: list) -> None:
    """从数据库缓存加载已有描述"""
    await self._ensure_cache_manager()

    titles = [item.title for item in items]
    cache_map = await self._cache_manager.batch_get(titles)

    now = datetime.now()
    for item in items:
        cached = cache_map.get(item.title)
        if cached:
            # 检查缓存是否过期（8小时）
            age = (now - cached['created_at']).total_seconds()
            if age < 28800:  # 8小时
                item.description = cached['description']
                item.description_source = cached['description_source']
```

**缓存表结构**:
```sql
CREATE TABLE weibo_hot_search_cache (
    id SERIAL PRIMARY KEY,
    title VARCHAR(200) UNIQUE NOT NULL,
    description TEXT NOT NULL,
    description_source VARCHAR(50) NOT NULL,  -- 'weibo_detail' | 'llm' | 'cache' | 'error'
    created_at TIMESTAMP DEFAULT NOW()
);
```

---

## 响应返回流程

### 1. 工具结果返回

**位置**: [base.py](../src/agent/base.py):216-219

```python
# 检查结果是否应直接返回
if result.startswith("📊 微博热搜榜："):
    # 微博热搜直接返回（不再经过 LLM 处理）
    yield result
    return
```

### 2. Agent 到 API 层

**位置**: [base.py](../src/agent/base.py):124-255

```python
async def chat_stream(self, message: str, history: list[dict] | None = None):
    # ... 执行工具 ...

    # 返回结果（yield 生成器）
    if weibo_returned:
        return  # 直接返回工具结果
```

**位置**: [server.py](../src/api/server.py):386-389

```python
# Stream the response
async for chunk in agent.chat_stream(request.message, history):
    full_response += chunk
    # SSE 格式发送
    yield f"data: {json.dumps({'content': chunk})}\n\n"
```

### 3. SSE 响应格式

**响应示例**:
```
data: {"type": "start", "message": "正在处理您的请求..."}

data: {"content": "📊 微博热搜榜：\n"}

data: {"content": "  1. 2025年度科技热点盘点 (热度: 356.2万)\n"}

data: {"content": "  2. 春节档电影票房创新高 (热度: 298.5万)\n"}

...

data: {"type": "progress", "message": "正在保存对话..."}

data: {"conversation_id": 123, "done": true}
```

### 4. 前端接收和渲染

**位置**: [chat.ts](../src/frontend-vue/src/api/chat.ts):35-62

```typescript
onmessage: (event) => {
  const chunk = JSON.parse(event.data)

  if (chunk.type === 'start') {
    // 显示加载提示
  } else if (chunk.content) {
    // 逐块更新消息内容
    onChunk(chunk.content)
  } else if (chunk.done) {
    // 流式传输完成
    onComplete(chunk.conversation_id)
  }
}
```

**位置**: [useChatStream.ts](../src/frontend-vue/src/composables/useChatStream.ts):85-88

```typescript
// onChunk 回调
(content: string) => {
  currentResponse.value += content
  chatStore.updateLastMessage(currentResponse.value)
}
```

**位置**: [chat.ts](../src/frontend-vue/src/stores/chat.ts):18-25

```typescript
const updateLastMessage = (content: string) => {
  if (messages.value.length > 0) {
    const lastMessage = messages.value[messages.value.length - 1]
    if (lastMessage.role === 'assistant') {
      lastMessage.content = content
    }
  }
}
```

---

## 数据持久化

### 1. 用户消息保存

**位置**: [server.py](../src/api/server.py):357-360

```python
# 在调用 Agent 前，先保存用户消息
await ConversationService.add_message(
    conn, conversation_id, "user", request.message
)
```

**SQL 操作**:
```sql
INSERT INTO messages (conversation_id, role, content, created_at)
VALUES (123, 'user', '今日微博热搜', NOW());
```

### 2. 助手响应保存

**位置**: [server.py](../src/api/server.py):395-398

```python
# 流式传输完成后，保存完整响应
await ConversationService.add_message(
    conn, conversation_id, "assistant", full_response
)
```

**SQL 操作**:
```sql
INSERT INTO messages (conversation_id, role, content, created_at)
VALUES (123, 'assistant', '📊 微博热搜榜：\n  1. ...', NOW());
```

### 3. 对话时间戳更新

**位置**: [server.py](../src/api/server.py):414

```python
await ConversationService.update_conversation_timestamp(conn, conversation_id)
```

**SQL 操作**:
```sql
UPDATE conversations
SET updated_at = NOW()
WHERE id = 123;
```

### 4. 对话标题生成

**位置**: [server.py](../src/api/server.py):400-412

```python
# 如果是新对话（标题为 "新对话"），生成 AI 标题
if conversation and conversation["title"] == "新对话":
    yield f"data: {json.dumps({'type': 'progress', 'message': '正在生成对话标题...'})}\n\n"

    # 根据配置的策略生成标题
    title = await generate_conversation_title(request.message, full_response)

    # 更新对话标题
    await ConversationService.update_conversation(
        conn, conversation_id, current_user.id, title
    )
```

**标题生成策略**:

1. **AI 生成策略** (title_generation_strategy = "ai"):
   ```python
   prompt = f"""根据以下对话内容，生成一个简洁的标题（不超过10个字）：

   用户：{first_message[:100]}

   只返回标题，不要其他内容。"""
   title = await agent.chat(prompt, history=None)
   ```

2. **截断策略** (title_generation_strategy = "truncate"):
   ```python
   title = first_message[:7] + ("..." if len(first_message) > 7 else "")
   # 示例: "今日微博热..."
   ```

**SQL 操作**:
```sql
UPDATE conversations
SET title = '微博热搜查询'
WHERE id = 123;
```

---

## 时序图

```
用户          前端              后端 API           Agent            工具            微博           数据库
 │             │                  │                 │               │              │              │
 │  输入消息    │                  │                 │               │              │              │
 ├────────────►│                  │                 │               │              │              │
 │             │  添加用户消息     │                 │               │              │              │
 │             │  (本地状态)       │                 │               │              │              │
 │             │  SSE 请求        │                 │               │              │              │
 │             ├─────────────────►│                 │               │              │              │
 │             │                  │  JWT 认证       │               │              │              │
 │             │                  ├───────────────►│               │              │              │
 │             │                  │  ✓ 认证成功     │               │              │              │
 │             │                  │                 │               │              │              │
 │             │                  │  创建/获取对话  │               │              │              │
 │             │                  ├─────────────────────────────────────────────────────────────►│
 │             │                  │  ✓ conversation_id=123           │              │              │
 │             │                  │                 │               │              │              │
 │             │                  │  保存用户消息   │               │              │              │
 │             │                  ├─────────────────────────────────────────────────────────────►│
 │             │                  │  ✓ 已保存       │               │              │              │
 │             │                  │                 │               │              │              │
 │             │                  │  调用 chat_stream│              │              │              │
 │             │                  ├────────────────►│               │              │              │
 │             │                  │                 │               │              │              │
 │             │                  │                 │  构建消息     │              │              │
 │             │                  │                 │  调用 LLM     │              │              │
 │             │                  │                 ├──────────────►│              │              │
 │             │                  │                 │               │              │              │
 │             │                  │                 │  LLM 决策: 需要工具 │            │              │
 │             │                  │                 │◄──────────────┤              │              │
 │             │                  │                 │               │              │              │
 │             │                  │                 │  执行工具调用  │              │              │
 │             │                  │                 ├──────────────►│              │              │
 │             │                  │                 │               │              │              │
 │             │                  │                 │               │  三级降级策略 │              │
 │             │                  │                 │               │              │              │
 │             │                  │                 │               │  尝试 Selenium             │
 │             │                  │                 │               ├────────────►│              │
 │             │                  │                 │               │              │              │
 │             │                  │                 │               │  获取页面    │              │
 │             │                  │                 │               │◄────────────┤              │
 │             │                  │                 │               │              │              │
 │             │                  │                 │               │  解析 HTML   │              │
 │             │                  │                 │               │  提取热搜    │              │
 │             │                  │                 │               │              │              │
 │             │                  │                 │               │  加载缓存    │              │
 │             │                  │                 │               ├─────────────────────────────►│
 │             │                  │                 │               │  ✓ 缓存命中  │              │
 │             │                  │                 │               │              │              │
 │             │                  │                 │               │  格式化结果  │              │              │
 │             │                  │                 │◄──────────────┤              │              │
 │             │                  │                 │               │              │              │
 │             │                  │  SSE: 开始      │               │              │              │
 │             │◄═════════════════╪═════════════════╪═══════════════╪═══════════════╪═══════════════╪═══════════════╡
 │             │                  │                 │               │              │              │
 │             │                  │  SSE: 内容块 1  │               │              │              │
 │             │◄═════════════════╪═════════════════╪═══════════════╪═══════════════╪═══════════════╪═══════════════╡
 │  显示内容   │                  │                 │               │              │              │
 │◄════════════╪═════════════════╪═════════════════╪═══════════════╪═══════════════╪═══════════════╪═══════════════╡
 │             │                  │                 │               │              │              │
 │             │                  │  SSE: 内容块 2  │               │              │              │
 │             │◄═════════════════╪═════════════════╪═══════════════╪═══════════════╪═══════════════╪═══════════════╡
 │  追加内容   │                  │                 │               │              │              │
 │◄════════════╪═════════════════╪═════════════════╪═══════════════╪═══════════════╪═══════════════╪═══════════════╡
 │             │                  │                 │               │              │              │
 │             │                  │  ... (继续流式)                 │              │              │
 │             │◄═════════════════╪═════════════════╪═══════════════╪═══════════════╪═══════════════╪═══════════════╡
 │             │                  │                 │               │              │              │
 │             │                  │  SSE: 保存进度  │               │              │              │
 │             │◄═════════════════╪═════════════════╪═══════════════╪═══════════════╪═══════════════╪═══════════════╡
 │             │                  │                 │               │              │              │
 │             │                  │  保存助手响应   │               │              │              │
 │             │                  ├─────────────────────────────────────────────────────────────►│
 │             │                  │  ✓ 已保存       │               │              │              │
 │             │                  │                 │               │              │              │
 │             │                  │  更新对话时间戳 │               │              │              │
 │             │                  ├─────────────────────────────────────────────────────────────►│
 │             │                  │  ✓ 已更新       │               │              │              │
 │             │                  │                 │               │              │              │
 │             │                  │  生成 AI 标题   │               │              │              │
 │             │                  │  SSE: 生成标题中│               │              │              │
 │             │◄═════════════════╪═════════════════╪═══════════════╪═══════════════╪═══════════════╪═══════════════╡
 │             │                  │                 │               │              │              │
 │             │                  │  更新对话标题   │               │              │              │
 │             │                  ├─────────────────────────────────────────────────────────────►│
 │             │                  │  ✓ 已更新       │               │              │              │
 │             │                  │                 │               │              │              │
 │             │                  │  SSE: 完成      │               │              │              │
 │             │◄═════════════════╪═════════════════╪═══════════════╪═══════════════╪═══════════════╪═══════════════╡
 │             │                  │                 │               │              │              │
 │             │  更新 conversation_id               │              │              │              │
 │             │  刷新对话列表  │                  │               │              │              │
 │             │                  │                 │               │              │              │
```

---

## 关键技术点

### 1. 流式响应 (SSE)

- **前端**: 使用 `@microsoft/fetch-event-source` 库
- **后端**: FastAPI `StreamingResponse` + `text/event-stream`
- **格式**: `data: {json}\n\n`

### 2. JWT 认证

- **Token 生成**: 用户登录时生成
- **Token 验证**: 每次 API 请求时验证
- **Token 格式**: `Bearer <token>`

### 3. 三级降级策略

1. **优先**: Selenium + ChromeDriver（爬取动态内容）
2. **降级**: httpx + BeautifulSoup（简单 HTTP 请求）
3. **兜底**: 模拟数据（保证服务可用）

### 4. 数据库连接池

- **库**: asyncpg (异步 PostgreSQL)
- **模式**: 单例连接池
- **管理**: `async with db.pool.acquire() as conn:`

### 5. LangChain 工具

- **工具定义**: `@tool` 装饰器
- **工具绑定**: `llm.bind_tools(tools)`
- **工具调用**: LLM 自动决策何时调用
- **结果处理**: `ToolMessage` 添加到消息历史

### 6. 缓存机制

- **表**: `weibo_hot_search_cache`
- **键**: 热搜标题 (唯一)
- **值**: 描述内容 + 来源 + 时间戳
- **过期**: 8 小时

---

## 配置项

**.env 配置**:

```env
# DeepSeek API
DEEPSEEK_API_KEY=your_api_key
DEEPSEEK_BASE_URL=https://api.deepseek.com
AGENT_MODEL=deepseek-chat
AGENT_TEMPERATURE=0.7
AGENT_MAX_TOKENS=2000

# 微博爬虫
WEIBO_USE_SELENIUM=true
WEIBO_COOKIE=your_cookie

# 对话标题生成策略
TITLE_GENERATION_STRATEGY=truncate  # ai | truncate

# 数据库
DATABASE_URL=postgresql+asyncpg://user:pass@localhost/newsagent
```

---

## 日志示例

```
[2025-03-16 10:30:15] INFO     📨 [流式] 收到聊天请求 (用户: test): 今日微博热搜...
============================================================
💬 [流式] 用户: test
💬 [流式] 用户消息: 今日微博热搜
📜 对话ID: 123
📜 历史记录数: 0
============================================================

[2025-03-16 10:30:15] INFO     🔍 开始获取微博热搜，数量限制: 40
📍 URL: https://s.weibo.com/top/summary?cate=realtimehot
🔧 使用 Selenium: True
✅ Selenium 可用: True
🌐 步骤 1/4: 启动 Selenium 爬虫...
🔧 初始化 Chrome 浏览器...
   ├─ 下载 ChromeDriver...
   ├─ 配置无头模式...
   └─ 启动浏览器...
✅ ChromeDriver 安装成功
🚀 启动 Chrome 浏览器...
✅ Chrome 浏览器启动成功
📍 访问页面: https://s.weibo.com/top/summary?cate=realtimehot
   └─ URL: https://s.weibo.com/top/summary?cate=realtimehot
⏳ 等待页面加载...
   └─ 等待动态内容加载...
   └─ 页面加载完成
📄 获取页面源码...
   └─ 页面大小: 152345 字符
🔍 解析热搜数据...
   └─ 使用 BeautifulSoup 解析...
   └─ 找到 50 行数据
   └─ 解析完成，获取 40 条数据
✅ 成功解析 40 条热搜
✅ Selenium 爬取成功，获取 40 条热搜

✓ Cache loaded: 35/40 hits

[2025-03-16 10:30:45] INFO     ✅ 获取 40 条热搜，其中 35 条含描述

[2025-03-16 10:30:45] INFO     ✓ [流式] 响应生成完成: 2543 字符

[2025-03-16 10:30:46] INFO     ✓ [流式] 对话标题已生成: 微博热搜查询

============================================================
```

---

## 总结

news-agent 处理 "今日微博热搜" 消息的完整流程包括：

1. **前端**: 用户输入 → SSE 请求发送
2. **后端 API**: JWT 认证 → 对话管理 → Agent 调用
3. **Agent**: LLM 决策 → 工具调用 → 结果返回
4. **工具**: 三级降级爬取 → HTML 解析 → 缓存加载 → 格式化输出
5. **数据库**: 消息保存 → 对话管理 → 标题生成
6. **响应**: SSE 流式返回 → 前端逐块渲染

整个流程采用异步编程模型，通过 SSE 实现流式响应，提供良好的用户体验。爬虫采用三级降级策略，确保服务的高可用性。
