# 如何获取微博 Cookie

微博的 Sina Visitor System 反爬验证可以通过使用真实用户的 Cookie 来绕过。

## 方法一：从浏览器获取 Cookie（推荐）

### Chrome 浏览器

1. **登录微博**
   - 访问 https://weibo.com
   - 使用你的账号登录

2. **打开开发者工具**
   - Mac: `Cmd + Option + I`
   - Windows: `Ctrl + Shift + I`

3. **进入 Application 标签**
   - 点击顶部的 "Application" 标签
   - 左侧菜单找到 "Cookies" -> "https://s.weibo.com"

4. **复制关键 Cookie**
   需要复制以下 Cookie 的值：
   - `SUB` (最重要，包含登录信息)
   - `SUBP`
   - `ALF`

5. **格式化 Cookie**
   将 Cookie 格式化为：`SUB=xxx; SUBP=xxx; ALF=xxx`

### 方法二：使用浏览器插件

1. 安装 "EditThisCookie" 或 "Cookie-Editor" 插件
2. 登录微博
3. 点击插件图标，导出 Cookie
4. 复制导出的 JSON 或文本

## 配置到项目中

### 方式一：环境变量（推荐）

编辑 `.env` 文件：

```bash
# 微博 Cookie（用于绕过 Sina Visitor System 验证）
WEIBO_COOKIE=SUB=xxx; SUBP=xxx; ALF=xxx
```

### 方式二：配置文件

编辑 `src/agent/config.py`，添加：

```python
# 微博 Cookie
weibo_cookie: str = ""  # 从浏览器获取的 Cookie
```

## Cookie 有效期

- **SUB**: 通常有效期 30 天左右
- **SUBP**: 通常有效期 30 天左右
- **ALF**: 过期时间戳

建议每隔几周更新一次 Cookie。

## 注意事项

⚠️ **安全提醒**：
- Cookie 相当于你的登录凭证，请妥善保管
- 不要将 Cookie 提交到公共代码仓库
- 可以使用 `.env` 文件管理（已加入 .gitignore）

## 验证 Cookie 是否有效

运行测试脚本：

```bash
python tests/verify_cookie.py
```

如果输出显示成功访问微博内容，说明 Cookie 有效。

## 常见问题

### Q1: Cookie 过期了怎么办？
A: 重新登录微博，按照上述步骤获取新的 Cookie。

### Q2: 为什么使用了 Cookie 还是被拦截？
A: 可能的原因：
   - Cookie 格式错误
   - Cookie 已过期
   - 爬取频率过高，被识别为机器人
   - 需要同时设置 User-Agent

### Q3: 如何避免 Cookie 频繁失效？
A:
   - 降低爬取频率（每秒不超过 1 次）
   - 使用真实的浏览器 User-Agent
   - 随机化请求间隔
   - 轮换使用多个账号的 Cookie
