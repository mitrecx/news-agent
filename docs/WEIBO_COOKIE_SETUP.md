# 微博热搜描述功能 - Cookie 配置指南

## 问题说明

微博有 **Sina Visitor System** 反爬验证系统，直接访问热搜详情页会被拦截，需要通过人机验证。

## 解决方案：使用 Cookie

使用真实用户的 Cookie 可以绕过验证系统，直接访问微博内容。

---

## 快速开始（5分钟）

### 第一步：获取 Cookie

#### 方法 1：Chrome 浏览器（推荐）

1. **登录微博**
   - 访问 https://weibo.com
   - 使用你的微博账号登录

2. **打开开发者工具**
   - Mac: 按 `Cmd + Option + I`
   - Windows: 按 `Ctrl + Shift + I`

3. **找到 Cookie**
   - 点击顶部 "Application" 标签（或 "应用"）
   - 左侧菜单展开 "Cookies"
   - 点击 "https://s.weibo.com"

4. **复制 Cookie 值**
   找到并复制以下 Cookie 的值（不是名称）：
   - `SUB` - 最重要，包含登录信息
   - `SUBP`
   - `ALF`

5. **组合 Cookie**
   格式：`SUB=值1; SUBP=值2; ALF=值3`

   示例：
   ```
   SUB=_2A25xY...; SUBP=0033...; ALF=173888...
   ```

#### 方法 2：使用 EditThisCookie 插件

1. 安装 Chrome 插件 "EditThisCookie"
2. 登录微博
3. 点击插件图标
4. 选择 "导出" → "复制为 JSON"
5. 从 JSON 中提取 `SUB`、`SUBP`、`ALF` 的值

### 第二步：配置 Cookie

编辑项目根目录的 `.env` 文件：

```bash
# 微博 Cookie（用于绕过 Sina Visitor System 验证）
WEIBO_COOKIE=SUB=你的SUB值; SUBP=你的SUBP值; ALF=你的ALF值
```

### 第三步：验证 Cookie

运行测试脚本验证 Cookie 是否有效：

```bash
python tests/verify_cookie.py
```

如果看到 "✅ Cookie 验证通过！"，说明配置成功！

---

## 详细说明

### Cookie 包含哪些字段？

| 字段 | 说明 | 必需 |
|------|------|------|
| `SUB` | 用户身份凭证 | ✅ 是 |
| `SUBP` | 验证参数 | ✅ 是 |
| `ALF` | 过期时间戳 | ⚠️ 建议 |

### Cookie 有效期多久？

- **SUB**: 通常 30 天
- **SUBP**: 通常 30 天
- **ALF**: 绝对时间戳

建议每隔 2-3 周更新一次 Cookie。

### Cookie 过期了怎么办？

重新按上述步骤获取新的 Cookie 并更新 `.env` 文件。

---

## 测试描述生成功能

Cookie 配置完成后，测试完整的热搜描述生成：

```bash
python tests/test_weibo_description.py
```

你应该看到类似输出：

```
============================================================
微博热搜描述生成功能测试
============================================================

✅ 成功爬取 6 条热搜
📝 后台生成热搜描述（6 条）
✅ 使用 Cookie 认证
============================================================
  [1] 某某事件
  ✓ 成功生成描述...
============================================================
```

---

## 常见问题

### Q1: 使用了 Cookie 还是被拦截？

**A:** 可能的原因：

1. **Cookie 格式错误**
   - 检查是否有多余的空格
   - 确保使用英文分号 `;` 分隔
   - 确保每个字段都是 `name=value` 格式

2. **Cookie 已过期**
   - 重新登录微博获取新 Cookie
   - 运行 `python tests/verify_cookie.py` 验证

3. **爬取频率过高**
   - 降低并发数量（已在代码中限制为 2）
   - 增加请求间隔（已设置为 1 秒）
   - 考虑使用多个账号的 Cookie 轮换

### Q2: 如何查看当前使用的 Cookie？

运行以下命令：

```python
from src.agent.config import get_settings

settings = get_settings()
print(f"Cookie: {settings.weibo_cookie[:50]}...")
```

### Q3: 能否使用多个账号的 Cookie？

可以！轮换使用多个账号的 Cookie 可以：
- 降低单个账号的使用频率
- 避免触发反爬机制
- 提高成功率

实现方法：在代码中维护一个 Cookie 池，轮换使用。

### Q4: Cookie 安全吗？

**安全提醒**：
- Cookie 相当于你的登录凭证
- 请勿将 Cookie 提交到公共代码仓库
- `.env` 文件已在 `.gitignore` 中，不会被提交
- 定期更换密码和 Cookie

---

## 故障排查

### 问题：Cookie 验证失败

**运行诊断**：
```bash
python tests/diagnose_network.py
```

**检查清单**：
- [ ] Cookie 格式正确（使用 `;` 分隔）
- [ ] 包含必需字段（SUB、SUBP）
- [ ] Cookie 未过期
- [ ] 能够登录 https://weibo.com

### 问题：能爬取热搜列表，但无法获取详情

**原因**：详情页需要 Cookie 认证

**解决**：
1. 确保 Cookie 配置正确
2. 运行 `verify_cookie.py` 验证
3. 检查日志中的错误信息

---

## 进阶：Cookie 池

对于生产环境，建议使用 Cookie 池：

```python
# 在 .env 中配置多个 Cookie
WEIBO_COOKIE_1=SUB=xxx1; SUBP=yyy1; ALF=zzz1
WEIBO_COOKIE_2=SUB=xxx2; SUBP=yyy2; ALF=zzz2
WEIBO_COOKIE_3=SUB=xxx3; SUBP=yyy3; ALF=zzz3
```

在代码中轮换使用：

```python
import random

cookies = [
    os.getenv("WEIBO_COOKIE_1"),
    os.getenv("WEIBO_COOKIE_2"),
    os.getenv("WEIBO_COOKIE_3"),
]

cookie = random.choice([c for c in cookies if c])
scraper = WeiboScraper(cookie=cookie)
```

---

## 总结

✅ **已完成**：
1. Cookie 配置支持
2. 绕过 Sina Visitor System 验证
3. 恢复微博详情页内容爬取
4. LLM 基于真实内容生成描述

🎯 **下一步**：
1. 获取你的微博 Cookie
2. 配置到 `.env` 文件
3. 运行 `python tests/verify_cookie.py` 验证
4. 测试完整功能

需要帮助？查看：
- [Cookie 获取指南](WEIBO_COOKIE_GUIDE.md)
- [网络诊断工具](diagnose_network.py)
- [Cookie 验证测试](verify_cookie.py)
