# News Agent

微博热搜与 AI 阅读工作台，提供热点采集、摘要阅读、智能对话和页面配置。

## 页面与功能

- **热点资讯**：单列清单展示标题、摘要状态和更新时间，点击条目进入独立详情。支持标题搜索、日期范围、摘要状态筛选和分页；返回列表时保留筛选、页码和浏览位置。采集标题后立即保存并加入摘要队列，后台逐条处理，页面自动更新「排队中 / 生成中 / 待重试 / 已有摘要」。详情可查看原文或重新排队，链接可直接打开或刷新。
- **智能对话**：通过顶部导航进入，支持对话历史、Markdown 回复和请求中断。
- **设置 → 模型配置**：每个用户可添加多个模型连接，独立配置显示名称、API 地址、API Key、模型 ID 和生成参数；支持获取模型列表、连接测试、编辑、删除和切换启用。
- **设置 → 微博连接**：保存微博 Cookie 后立即对后续采集生效，无需重启。

个人模型配置保存在 PostgreSQL 的 `user_model_profiles` 表，每个用户最多启用一个模型。API Key 经加密存储，接口只返回是否已设置，不回显密钥。编辑时留空 API Key 可保留该模型的密钥；新增模型需填写自己的密钥，修改 API 地址时必须重新填写对应密钥。

聊天、对话标题和手动采集派生的摘要使用发起用户启用的模型。定时采集及历史待处理资讯使用 `WEIBO_SUMMARY_USERNAME` 指定账号的启用模型；配置缺失时保留任务并等待恢复，不借用其他用户的密钥。每条任务执行时读取最新的模型配置，已经开始的调用继续使用原配置。资讯库与微博 Cookie 当前由工作台共享，模型配置按用户隔离。

## 本地启动

需要 Python 3.12+、Node.js（满足 Vite 8 的运行要求）、uv、PostgreSQL；定时任务还需要 Redis，浏览器采集需要 Chrome。

```bash
uv sync --frozen
cp .env.example .env
```

在 `.env` 中设置数据库连接和独立的 `JWT_SECRET`。模型通过页面配置；`.env` 中的模型字段只用于下述一次性导入，不作为运行时默认配置。

数据库需提前创建，然后执行：

```bash
uv run python scripts/init_db.py
uv run python scripts/migrate_weibo_cache.py
uv run python scripts/migrate_model_settings.py
uv run python scripts/migrate_summary_queue.py
```

初始化会创建本地测试账号 `test`，密码 `test123456`。

启动后端：

```bash
uv run uvicorn src.api.server:app --host 127.0.0.1 --port 8000 --reload
```

另开终端启动前端：

```bash
cd src/frontend-vue
npm ci
npm run dev -- --host 127.0.0.1 --port 6173
```

访问 `http://localhost:6173`，API 文档为 `http://localhost:8000/docs`。

> `scripts/start_backend.sh` 是旧的远程数据库隧道启动器；使用本机 PostgreSQL 时请使用上面的命令。

## 页面配置模型

1. 登录后进入「设置 → 模型配置」，点击「添加模型」。
2. 填写显示名称、API 根地址（如 `https://api.deepseek.com/v1`）、API Key 和服务商提供的模型 ID。
3. 可通过「获取模型列表」选择模型；不支持模型列表的服务也可手动输入。
4. 点击「测试连接」检查实际调用，再点击「添加模型」。测试不会保存或切换配置。
5. 第一个模型自动启用，后续添加的模型作为备用；点击模型卡片上的「启用」切换。
6. 后续聊天和手动摘要使用已启用的模型，已经开始的请求继续使用原配置。删除当前模型前需先切换到另一个；删除最后一个模型后需重新添加才能使用 AI。

配置支持 Chat Completions 兼容接口。API 地址需为根地址，不包含 `/chat/completions`、查询参数或 URL 中的用户名密码。

已有 `.env` 模型可以显式导入指定账号：

```bash
uv run python scripts/import_model_from_env.py --username test --name "我的第一个模型"
```

导入只在该账号没有模型时执行，保存为普通的个人模型并自动启用，不输出连接地址或密钥。旧 `user_model_settings` 数据会在迁移或启动时转换为一个个人模型；删除后不会重新导入。

修改 `JWT_SECRET` 会使现有登录令牌失效，并使原有模型密钥无法解密，需要重新填写；请保持该值稳定并与数据库备份一同保管。

## 微博连接

热搜榜单与正文的访问限制不同。榜单可能可匿名访问，正文可能跳转到微博登录页。

在已登录微博的浏览器中，从 Network 请求头复制 Cookie，在「设置 → 微博连接」保存。已保存的 Cookie 不回显，值也不写入应用日志。后端与任务进程在下一次操作时读取最新 Cookie。

## 定时任务

配置 `.env` 中的 `REDIS_HOST`、`REDIS_PORT`，启动 Redis，再运行：

```bash
uv run --env-file .env celery -A src.celery_app worker --loglevel=info
uv run --env-file .env celery -A src.celery_app beat --loglevel=info
```

每 3 小时采集一次微博热搜标题，每 10 分钟清理过期数据。请在 `.env` 中设置 `WEIBO_SUMMARY_USERNAME=你的账号`，并在页面为该账号添加和启用模型；修改此项后重启后台 worker。

标题与摘要任务在同一个数据库事务中保存，采集不等待正文抓取或模型调用，也不依赖 Redis 当时可用。Celery 每 5 秒检查数据库队列，每次只处理一条；处理结束立即继续下一条。数据库锁保证多个 worker 也不会并行生成摘要。

网络、微博登录或模型调用失败时，任务保留并延后重试，间隔从 1 分钟逐步增加至最多 1 小时，其他任务继续处理。服务重启后恢复未完成条目，并自动补齐历史缺失摘要。Redis / worker / beat 恢复后继续消费；已成功生成的摘要不会重复处理。原文长期不可访问时会保持待重试，无法承诺每一条都能成功生成。

## 配置项

| 环境变量 | 用途 |
| --- | --- |
| `DB_HOST`、`DB_PORT`、`DB_USER`、`DB_PASSWORD`、`DB_NAME` | PostgreSQL 连接 |
| `JWT_SECRET` | 登录签名及个人模型密钥加密，需保持稳定 |
| `DEEPSEEK_API_KEY`、`DEEPSEEK_BASE_URL` | 仅供一次性导入的模型连接（运行时不读取） |
| `AGENT_MODEL`、`AGENT_TEMPERATURE`、`AGENT_MAX_TOKENS` | 仅供一次性导入的模型 ID 及生成参数 |
| `WEIBO_COOKIE` | 工作台共享的微博采集凭据，支持页面更新 |
| `WEIBO_SUMMARY_USERNAME` | 定时采集与历史待处理摘要使用的模型账号，读取该账号启用的模型 |
| `REDIS_HOST`、`REDIS_PORT` | Celery 消息队列与任务结果 |

不要提交 `.env` 或凭据文件。

## 验证

```bash
# 多模型增删改、切换、用户隔离、迁移、密钥保护、模型调用和 Cookie 即时生效
uv run python -m unittest tests.test_model_settings -v

# 验证单条详情、摘要状态与日期筛选、分页计数、过期数据及摘要生成边界
uv run python -m unittest tests.test_hotsearch_summary -v

# 验证采集与入队原子性、去重、逐条处理、跨 worker 互斥、重试和中断恢复
uv run python -m unittest tests.test_summary_queue -v

# 前端类型检查与生产构建
cd src/frontend-vue
npm run build
```

模型配置集成测试需要可连接的 PostgreSQL：测试只创建、清理独立 schema，不使用或修改现有用户数据。模型调用测试使用临时本地 HTTP 服务，无需真实模型额度。

## 项目结构

```text
src/
  frontend-vue/  Vue 3、Pinia、Element Plus 工作台
  api/           FastAPI 聊天、热搜及微博连接 API
  settings/      个人模型配置、加密存储和连接测试
  auth/          登录、用户及会话持久化
  agent/         模型客户端与工具调用
  tools/         微博采集、缓存和摘要
  tasks/         Celery 定时采集及摘要任务
```
