---
name: test-news-agent
description: 当用户要求测试news-agent时，使用浏览器自动化测试 news-agent 应用。此技能通过实际的浏览器交互，确保前端 UI 和后端集成的完整端到端测试。
---

# 测试 news-agent

此技能使用浏览器自动化对 news-agent 应用进行完整的端到端测试。

## 前置条件

```bash
# 启动服务：
./scripts/start_backend.sh   # 终端 1：后端在端口 8000
./scripts/start_frontend.sh  # 终端 2：前端在端口 6173
```
测试前，确保后端和前端服务正在正常运行。

## 测试账号信息

- **用户名**：`test`
- **密码**：`test123456`

⚠️ **重要**：请勿注册新用户。测试用户已存在于数据库中。

## 测试步骤

### 步骤 1：打开浏览器并导航

使用 `mcp__chrome-devtools__new_page` 打开新的浏览器标签页：

```
URL: http://localhost:6173
```

### 步骤 2：获取初始快照

使用 `mcp__chrome-devtools__take_snapshot` 查看登录页面结构。

### 步骤 3：登录

使用 `mcp__chrome-devtools__fill` 工具：
1. 输入用户名：`test`
2. 输入密码：`test123456`
3. 点击登录按钮

### 步骤 4：进入对话页面

登录成功后，获取快照以确认你已在对话页面上。

### 步骤 5：发送测试消息

使用不同类型的消息测试 agent：

**测试 1：微博热搜（工具调用）**
- 消息："今日微博热搜" 或 "微博热搜"
- 预期：Agent 应该调用微博热搜工具并返回热搜列表
- 验证：流式响应正确显示，实时更新

**测试 2：简单问候（不调用工具）**
- 消息："你好" 或 "hello"
- 预期：Agent 应该友好回应并主动提供查看微博热搜
- 验证：回复友好并能引导用户交互

### 步骤 6：验证对话功能

发送消息后，验证：
- 消息在聊天界面正确显示，格式正确
- 流式响应逐步出现（不是一次性全部显示）
- 对话列表显示最近的对话
- 切换对话时消息历史得到保留

### 步骤 7：检查错误

使用 `mcp__chrome-devtools__list_console_messages` 检查是否有任何 JavaScript 错误或警告。

## 成功标准

成功的测试应该验证：
- ✅ 用户可以使用测试凭据登录
- ✅ 聊天界面加载并正确显示
- ✅ 可以发送消息并收到响应
- ✅ 流式响应实时显示
- ✅ 微博热搜工具在适当时被调用
- ✅ 控制台无错误或警告
- ✅ 对话历史得到维护

## 故障排除

### Chrome DevTools MCP 无法创建新浏览器标签页

**错误信息：** "The browser is already running for /Users/chenxing/.cache/chrome-devtools-mcp/chrome-profile"

**原因：** Chrome DevTools MCP 的缓存目录被现有进程锁定。

**解决方案：**

1. 停止 Chrome DevTools MCP 服务器进程：
   ```bash
   # 查找并停止相关进程
   ps aux | grep chrome-devtools-mcp | grep -v grep
   kill <PID>
   ```

2. 清除 Chrome DevTools MCP 缓存：
   ```bash
   rm -rf /Users/chenxing/.cache/chrome-devtools-mcp/chrome-profile
   ```

3. 重新执行测试

### 其他浏览器问题

**如果浏览器无法打开：**
- 检查 Chrome 是否已在运行，改用 `mcp__chrome-devtools__list_pages`
- 尝试使用隔离上下文：`isolatedContext: "test-context"`


## 重要注意事项

- **严禁使用 `curl` 或直接 API 调用**进行测试 - 始终通过浏览器 UI 测试
- **始终验证前端 UI 渲染** - 仅后端 API 成功是不够的
- 测试必须由 Claude 执行，而不是由用户执行
