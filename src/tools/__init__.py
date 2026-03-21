"""Tools module - LangChain 工具集成"""

import logging
from langchain_core.tools import tool
from .weibo import get_scraper

# 配置日志
logger = logging.getLogger(__name__)


@tool
async def fetch_weibo_hot_search(limit: int = 40) -> str:
    """
    获取最新的微博热搜榜。

    必须在以下情况调用此工具：
    - 用户询问"微博热搜"、"热搜榜"、"热门话题"
    - 用户询问"今天有什么热点"、"最新新闻"、"今日热点"
    - 用户询问"最近有什么热门事件"、"热门话题"
    - 用户想了解当前流行趋势或热门事件

    Args:
        limit: 返回热搜数量，默认40条，最多50条

    Returns:
        格式化的热搜列表（包含排名、标题、热度和描述）
    """
    if limit < 1:
        limit = 10
    if limit > 50:
        limit = 50

    logger.info(f"🔍 开始获取微博热搜，数量限制: {limit}")

    scraper = get_scraper()
    try:
        # 获取热搜（描述在后台异步生成）
        items = await scraper.fetch_hot_search(limit, fetch_descriptions=False)

        # 统计描述状态
        with_desc = sum(1 for item in items if item.description)
        logger.info(f"✅ 获取 {len(items)} 条热搜，其中 {with_desc} 条含描述")

        # 格式化输出
        lines = ["📊 微博热搜榜：\n"]
        for item in items:
            if item.description:
                lines.append(f"  {item.rank}. {item.title} (热度: {item.hot_value})\n     💡 {item.description}\n")
            else:
                lines.append(f"  {item.rank}. {item.title} (热度: {item.hot_value})\n")

        result = "\n".join(lines)

        # 如果有描述正在生成，添加提示
        if with_desc < len(items):
            result += "\n\n💡 部分热搜的详细描述正在后台生成中，请稍后刷新查看。"

        return result

    except Exception as e:
        error_msg = f"获取微博热搜失败: {e}"
        logger.error(error_msg)
        return error_msg


# 导出所有工具
__all__ = ["fetch_weibo_hot_search"]
