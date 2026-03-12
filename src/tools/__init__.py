"""Tools module - LangChain 工具集成"""

import logging
from langchain_core.tools import tool
from .weibo import get_scraper

# 配置日志
logger = logging.getLogger(__name__)


@tool
async def fetch_weibo_hot_search(limit: int = 10) -> str:
    """
    获取微博热搜榜，返回当前最热门的话题

    当用户询问以下内容时，使用此工具：
    - "微博热搜"、"热搜榜"、"热门话题"
    - "今天有什么热点"、"最近有什么新闻"
    - "热门事件"、"大家都在聊什么"

    Args:
        limit: 返回热搜数量，默认10条，最多50条

    Returns:
        格式化的热搜列表文本，包含排名、标题和热度值
    """
    if limit < 1:
        limit = 10
    if limit > 50:
        limit = 50

    # 打印日志
    logger.info(f"🔍 开始获取微博热搜，数量限制: {limit}")
    print(f"\n{'='*60}")
    print(f"📊 微博热搜工具调用")
    print(f"{'='*60}")
    print(f"⏰ 时间: {__import__('datetime').datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"📝 获取数量: {limit} 条")
    print(f"{'='*60}\n")

    scraper = get_scraper()
    try:
        result = await scraper.get_hot_search_summary(limit)

        # 打印结果日志
        print(f"✅ 微博热搜获取成功")
        print(f"{'='*60}")
        print(result)
        print(f"{'='*60}\n")

        logger.info(f"✅ 成功获取微博热搜，返回 {result.count(chr(10))} 行数据")
        return result
    except Exception as e:
        error_msg = f"获取微博热搜失败: {e}"
        print(f"❌ {error_msg}")
        print(f"{'='*60}\n")
        logger.error(error_msg)
        return error_msg


# 导出所有工具
__all__ = ["fetch_weibo_hot_search"]
