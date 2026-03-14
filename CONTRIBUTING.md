# Contributing to News Agent

感谢您对 News Agent 项目的关注！我们欢迎任何形式的贡献，包括但不限于：

- 🐛 Bug 报告
- 💡 功能建议
- 📖 文档改进
- 🔧 代码贡献
- 🧪 测试用例

## 开发环境设置

### 1. Fork 和克隆项目

```bash
# Fork 项目到您的 GitHub 账户
# 然后克隆您的 fork
git clone https://github.com/YOUR_USERNAME/news-agent.git
cd news-agent
```

### 2. 创建虚拟环境

```bash
# 使用 uv（推荐）
uv sync

# 或使用传统方式
python -m venv venv
source venv/bin/activate  # Linux/Mac
# 或
venv\Scripts\activate  # Windows
pip install -e ".[dev]"
```

### 3. 配置环境变量

```bash
cp .env.example .env
# 编辑 .env 文件，填入您的配置
```

### 4. 运行测试

```bash
# 运行所有测试
uv run pytest

# 运行特定测试文件
uv run pytest tests/test_utils.py

# 运行测试并显示覆盖率
uv run pytest --cov=src --cov-report=html
```

## 开发流程

### 1. 创建功能分支

```bash
git checkout -b feature/your-feature-name
# 或
git checkout -b fix/your-bug-fix
```

### 2. 编写代码

请遵循以下规范：

#### 代码风格

- 使用 **Python 3.12+** 类型注解
- 遵循 **PEP 8** 代码风格
- 使用有意义的变量和函数名
- 添加文档字符串（docstrings）

```python
from typing import List, Optional

async def fetch_weibo_hot_search(
    limit: int = 10,
    category: Optional[str] = None
) -> List[HotSearchItem]:
    """
    获取微博热搜榜

    Args:
        limit: 返回热搜数量，默认10条
        category: 热搜分类筛选

    Returns:
        热搜条目列表

    Raises:
        ConnectionError: 网络连接失败
        ValueError: 参数错误
    """
    pass
```

#### 错误处理

- 使用具体的异常类型
- 提供有意义的错误信息
- 记录错误日志

```python
from ..utils.logger import get_logger

logger = get_logger(__name__)

try:
    result = await fetch_data()
except ConnectionError as e:
    logger.error(f"网络连接失败: {e}")
    raise
except ValueError as e:
    logger.warning(f"参数错误: {e}")
    raise
```

#### 缓存和重试

对于外部 API 调用，使用缓存和重试机制：

```python
from ..utils.cache import cached
from ..utils.retry import retry_with_backoff, RetryConfig

@cached(ttl=300, key_prefix="weibo")
@retry_with_backoff(config=RetryConfig(max_attempts=3))
async def fetch_external_api():
    pass
```

### 3. 编写测试

- 为新功能添加单元测试
- 测试覆盖率应 > 80%
- 使用 pytest 和 pytest-asyncio

```python
import pytest
from src.your_module import your_function

class TestYourFunction:
    @pytest.mark.asyncio
    async def test_basic_case(self):
        result = await your_function(input_data)
        assert result == expected_output

    def test_error_handling(self):
        with pytest.raises(ValueError):
            your_function(invalid_input)
```

### 4. 运行代码检查

```bash
# 运行测试
uv run pytest

# 检查类型（如果使用 mypy）
uv run mypy src/

# 格式化代码（如果使用 black）
uv run black src/
```

### 5. 提交代码

```bash
git add .
git commit -m "feat: 添加知乎热搜爬虫功能

- 实现知乎热搜页面解析
- 添加数据模型和验证
- 添加单元测试和集成测试
- 更新文档"
```

#### 提交信息规范

使用语义化提交信息：

- `feat:` 新功能
- `fix:` Bug 修复
- `docs:` 文档更新
- `style:` 代码格式（不影响功能）
- `refactor:` 重构
- `test:` 添加测试
- `chore:` 构建/工具更新

### 6. 推送和创建 Pull Request

```bash
git push origin feature/your-feature-name
```

然后在 GitHub 上创建 Pull Request。

## Pull Request 检查清单

在提交 PR 前，请确保：

- [ ] 代码通过所有测试
- [ ] 添加了新的测试用例
- [ ] 更新了相关文档
- [ ] 遵循代码风格规范
- [ ] 提交信息清晰明确
- [ ] PR 描述详细说明了改动内容

## 项目结构

```
news-agent/
├── src/
│   ├── agent/          # Agent 核心逻辑
│   │   ├── base.py     # Agent 实现
│   │   └── config.py   # 配置管理
│   ├── api/            # API 服务
│   │   ├── server.py   # FastAPI 服务器
│   │   └── models.py   # 数据模型
│   ├── tools/          # LangChain 工具
│   │   ├── weibo.py    # 微博热搜工具
│   │   └── __init__.py
│   ├── utils/          # 工具模块
│   │   ├── cache.py    # 缓存管理
│   │   ├── retry.py    # 重试机制
│   │   └── logger.py   # 日志配置
│   └── config.py       # 全局配置
├── tests/              # 测试文件
│   ├── conftest.py     # pytest 配置
│   ├── test_utils.py   # 工具测试
│   ├── test_weibo_scraper.py  # 爬虫测试
│   └── test_integration.py    # 集成测试
├── docs/               # 文档（可选）
├── .env.example        # 环境变量示例
├── pyproject.toml      # 项目配置
├── README.md           # 项目说明
└── CONTRIBUTING.md     # 贡献指南
```

## 添加新的新闻源

### 1. 创建工具模块

在 `src/tools/` 下创建新的工具文件：

```python
# src/tools/zhihu.py
from langchain_core.tools import tool
from ..utils.cache import cached
from ..utils.retry import retry_with_backoff, RetryConfig
from ..utils.logger import get_logger

logger = get_logger(__name__)

@cached(ttl=300, key_prefix="zhihu")
@retry_with_backoff(config=RetryConfig(max_attempts=3))
@tool
async def fetch_zhihu_hot_search(limit: int = 10) -> str:
    """
    获取知乎热榜

    Args:
        limit: 返回热榜数量

    Returns:
        格式化的热榜文本
    """
    # 实现爬虫逻辑
    pass
```

### 2. 注册工具

在 `src/tools/__init__.py` 中导出：

```python
from .zhihu import fetch_zhihu_hot_search

__all__ = ["fetch_weibo_hot_search", "fetch_zhihu_hot_search"]
```

### 3. 更新 Agent

在 `src/api/server.py` 中注册工具：

```python
from ..tools import fetch_weibo_hot_search, fetch_zhihu_hot_search

tools = [fetch_weibo_hot_search, fetch_zhihu_hot_search]
agent = NewsAgent(tools=tools)
```

### 4. 添加测试

创建对应的测试文件 `tests/test_zhihu_scraper.py`

## 常见问题

### 如何运行开发服务器？

```bash
uv run python run.py
```

### 如何调试爬虫？

启用详细日志：

```python
from ..utils.logger import get_logger, set_global_log_level

logger = get_logger(__name__)
set_global_log_level('DEBUG')
```

### 如何处理反爬？

1. 使用 Selenium 模拟真实浏览器
2. 设置合理的请求间隔
3. 使用代理 IP（高级）
4. 实现 User-Agent 轮换

## 获取帮助

如果您有任何问题：

- 📧 提交 Issue
- 💬 加入讨论（如果有讨论区）
- 📖 查看文档

## 行为准则

- 尊重所有贡献者
- 保持友好和建设性的讨论
- 接受反馈并持续改进

再次感谢您的贡献！🎉
