"""LLM 总结工具 - 为微博热搜生成描述"""

import logging
from typing import Optional

logger = logging.getLogger(__name__)


async def summarize_from_title(title: str) -> str:
    """
    基于热搜标题生成推断性描述（降级方案）

    当无法获取微博详情内容时，使用 LLM 基于标题生成合理的描述。

    Args:
        title: 热搜标题

    Returns:
        100-150字左右的推断性描述
    """
    try:
        from langchain_openai import ChatOpenAI
        from langchain_core.prompts import ChatPromptTemplate
        from ..agent.config import get_settings

        settings = get_settings()

        # 创建 LLM（使用较低温度以获得更稳定的推断）
        llm = ChatOpenAI(
            model=settings.agent_model,
            api_key=settings.deepseek_api_key,
            base_url=settings.deepseek_base_url,
            temperature=0.5,  # 降低温度以获得更确定性的推断
            max_tokens=200,
        )

        # 创建提示模板
        prompt = ChatPromptTemplate.from_messages([
            ("system", """你是一个新闻事件推断助手。根据微博热搜标题，生成100-150字的推断性描述。

你的任务是基于标题推断可能的新闻事件内容。

要求：
1. 基于标题进行合理推断，提供可能的背景和细节
2. 使用"可能"、"据称"、"相关"等不确定性词汇
3. 语言简洁明了，保持客观中立
4. 控制在100-150字
5. 不要编造具体的日期、时间或地点（除非标题中明确提到）
6. 如果标题是人名，推测其可能的身份或相关事件
7. 如果标题是事件，推测可能的起因和影响

示例：
- 标题："湘雅医院失联学生确认坠江身亡"
  描述："该事件可能涉及某医学院校学生在湘雅医院附近失联，经过搜救后确认不幸遇难。事件可能引发对校园安全、心理健康等问题的关注和讨论。"

- 标题："小米新SU7发布定档3月19日"
  描述："小米汽车可能即将发布新款SU7车型，官方可能已确定发布日期为3月19日。这可能是小米在电动汽车领域的重要产品更新，可能引发市场关注。"
"""),
            ("user", "微博热搜标题：{title}\n\n请生成100-150字的推断性描述：")
        ])

        # 生成推断
        chain = prompt | llm
        result = await chain.ainvoke({"title": title})

        description = result.content.strip()

        # 确保长度合理
        if len(description) > 180:
            description = description[:180] + "..."

        logger.info(f"✅ LLM 推断成功: {description[:50]}...")
        return description

    except Exception as e:
        logger.error(f"❌ LLM 推断失败: {e}", exc_info=True)

        # 最终降级方案：返回带有说明的简单描述
        return f"微博热门话题：{title}。这是一个在社交媒体上引起关注的话题，相关讨论和观点可能在持续发酵中。"


async def summarize_weibo_content(title: str, content: str) -> str:
    """
    使用 LLM 总结微博内容

    Args:
        title: 热搜标题
        content: 微博内容

    Returns:
        200字左右的描述
    """
    # 如果内容不足，使用基于标题的推断
    if not content or len(content.strip()) < 10:
        logger.info(f"⚠️ 内容不足，使用基于标题的推断: {title}")
        return await summarize_from_title(title)

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
7. 使用现在时态描述
8. 可以包含更多背景信息和细节，使描述更丰富

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

        # 降级方案：截取内容或使用标题
        if content and len(content) > 50:
            return content[:200] + "..." if len(content) > 200 else content
        else:
            return f"微博热门话题：{title}"


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
                    item.description = description
                    item.description_source = "weibo_detail"
                    item.description_generated_at = datetime.now()
                else:
                    item.description = f"微博热门话题：{item.title}"
                    item.description_source = "fallback"

                logger.info(f"✓ [{item.rank}] {item.title}: {item.description[:50]}...")

            except Exception as e:
                logger.warning(f"✗ [{item.rank}] {item.title}: {e}")
                item.description = f"微博热门话题：{item.title}"
                item.description_source = "error"

            # 避免请求过快
            await asyncio.sleep(0.5)

    # 并发执行
    tasks = [summarize_one(item) for item in items]
    await asyncio.gather(*tasks)

    logger.info(f"✅ 批量总结完成，共 {len(items)} 条")
