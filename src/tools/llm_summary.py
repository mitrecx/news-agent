"""LLM 总结工具 - 为微博热搜生成描述"""

import logging
from typing import Optional

logger = logging.getLogger(__name__)


async def summarize_weibo_content(title: str, content: str) -> str | None:
    """
    使用 LLM 总结微博内容

    Args:
        title: 热搜标题
        content: 微博内容

    Returns:
        200字左右的描述，如果内容不足返回 None
    """
    # 如果内容不足，返回 None
    if not content or len(content.strip()) < 10:
        logger.info(f"⚠️ 内容不足，不生成描述: {title}")
        return None

    try:
        from langchain_openai import ChatOpenAI
        from langchain_core.prompts import ChatPromptTemplate
        from ..agent.config import get_settings

        settings = get_settings()

        # 创建 LLM
        llm = ChatOpenAI(
            model=settings.agent_model,
            api_key=settings.deepseek_api_key,
            base_url=settings.deepseek_base_url,
            temperature=0.7,
            max_tokens=300,
        )

        # 创建提示模板
        prompt = ChatPromptTemplate.from_messages([
            ("system", """你是一个专业的新闻摘要助手。请根据微博热搜标题和相关内容，生成200字左右的描述。

你的任务是分析热搜内容，提取关键信息，生成详细准确的描述。

要求：
1. 基于提供的微博内容进行总结（优先使用真实内容）
2. 如果内容不足，基于标题推断合理的新闻内容
3. 语言简洁明了，通俗易懂
4. 控制在200字左右
5. 突出新闻的核心信息（时间、地点、人物、事件）
6. 保持客观中立的语气
7. 可以包含更多背景信息和细节，使描述更丰富

示例：
- 标题："春节档电影票房创新高"
  内容："2025年春节档期间，多部国产电影表现亮眼，总票房突破100亿元大关，创历史新高。《热辣滚烫》《飞驰人生2》等影片获得观众热议，展现了强劲的市场活力。"
  描述："2025年春节档期间，多部国产电影表现亮眼，总票房突破100亿元大关，创历史新高。《热辣滚烫》《飞驰人生2》等影片获得观众热议。"
"""),
            ("user", "热搜标题：{title}\n\n微博内容：\n{content}\n\n请生成200字左右的描述：")
        ])

        # 生成总结
        chain = prompt | llm
        result = await chain.ainvoke({
            "title": title,
            "content": content[:1500]  # 限制内容长度避免超token
        })

        description = result.content.strip()

        # 确保长度合理
        if len(description) > 250:
            description = description[:250] + "..."

        logger.info(f"✅ LLM 总结成功: {description[:50]}...")
        return description

    except Exception as e:
        logger.error(f"❌ LLM 总结失败: {e}", exc_info=True)

        # 降级方案：截取内容
        if content and len(content) > 50:
            return content[:200] + "..." if len(content) > 200 else content
        else:
            return None


async def summarize_weibo_batch(items: list, max_concurrent: int = 3) -> None:
    """
    批量总结微博热搜（并发控制）

    Args:
        items: HotSearchItem 列表，会被就地修改
        max_concurrent: 最大并发数
    """
    import asyncio

    semaphore = asyncio.Semaphore(max_concurrent)

    async def summarize_one(item):
        async with semaphore:
            try:
                # 先获取内容
                from ..tools.weibo import get_scraper
                scraper = get_scraper()

                # 获取微博内容
                content = await scraper._fetch_item_content(item)

                # 生成描述
                if content:
                    description = await summarize_weibo_content(item.title, content)
                    if description:
                        item.description = description
                        item.description_source = "weibo_detail"
                        item.description_generated_at = datetime.now()
                    else:
                        item.description = None
                        item.description_source = None
                else:
                    item.description = None
                    item.description_source = None

                logger.info(f"✓ [{item.rank}] {item.title}: {item.description[:50]}...")

            except Exception as e:
                logger.warning(f"✗ [{item.rank}] {item.title}: {e}")
                item.description = None
                item.description_source = None

            # 避免请求过快
            await asyncio.sleep(0.5)

    # 并发执行
    tasks = [summarize_one(item) for item in items]
    await asyncio.gather(*tasks)

    logger.info(f"✅ 批量总结完成，共 {len(items)} 条")
