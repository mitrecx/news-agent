# News Agent 前端

Vue 3 + TypeScript + Pinia + Element Plus。

## 启动

```bash
npm ci
npm run dev -- --host 127.0.0.1 --port 6173
```

开发服务器代理 `/api` 和 `/health` 到 `http://localhost:8000`。

## 页面

- `/`：热点列表、筛选、摘要阅读和采集。操作栏批量生成摘要；详情区只获取当前选中话题并生成摘要，完成后保留页码与选中项。
- `/chat`：用户会话、Markdown 回复、停止生成。
- `/settings`：个人多模型管理、获取模型列表、连接测试、编辑删除和启用切换。
- `/settings?tab=weibo`：共享微博连接。旧 `/weibo-login` 路径自动重定向。
- `/login`：登录工作台。

所有业务页面共用 AppShell 的侧栏和工作区；窄屏使用图标导航，对话历史可展开。模型密钥只在编辑表单中短暂存在，保存后清空，不写入 localStorage。

热点资讯在桌面端按窗口高度分配阅读空间，资讯列表和正文独立滚动，分页与详情栏保持可见；窄屏改为上下排列，各阅读区域仍可滚动。

```bash
npm run build
```

运行方式、数据库迁移及配置作用范围请参阅项目根目录 README。
