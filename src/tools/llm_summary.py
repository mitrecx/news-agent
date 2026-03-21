"""LLM 总结工具 - 为微博热搜生成描述"""

import logging
import re

logger = logging.getLogger(__name__)


def clean_description_text(text: str) -> str:
    """
    清理描述文本，删除换行符和多余空行，智能添加标点符号

    Args:
        text: 原始文本

    Returns:
        清理后的文本
    """
    # 定义中文结束标点符号
    ending_punctuation = {'。', '！', '？', '；', '：', '.', '!', '?', ';', ':'}

    # 第一步：将所有换行符和连续空格替换为单个空格
    text = re.sub(r'\s+', ' ', text)

    # 第二步：智能处理标点符号
    # 匹配模式：标点 + 空格 + 非标点字符
    # 如果标点后面跟着非标点字符，确保有空格
    text = re.sub(r'([。！？；：.!?;:])\s*([^。！？；：.!?;:\s])', r'\1 \2', text)

    # 第三步：处理缺少标点的情况
    # 如果两个句子之间只有空格没有标点，添加句号
    # 检测：中文字符/英文字母 + 空格 + 中文字符/英文字母（且前面不是标点）
    text = re.sub(r'([\u4e00-\u9fff\w])\s+([\u4e00-\u9fff\w])', r'\1 \2', text)

    # 第四步：删除多余的空格（只保留单词间的一个空格）
    text = re.sub(r' +', ' ', text)

    # 第五步：删除首尾空格
    text = text.strip()

    return text


async def summarize_weibo_content(title: str, content: str) -> str | None:
    """
    使用 LLM 总结微博内容

    Args:
        title: 热搜标题
        content: 微博内容

    Returns:
        500字左右的描述，如果内容为空返回 None
    """
    # 如果内容为空，返回 None
    if not content or len(content.strip()) < 10:
        logger.info(f"⚠️ 内容为空，不生成描述: {title}")
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
            max_tokens=500,
        )

        # 创建提示模板
        prompt = ChatPromptTemplate.from_messages([
            ("system", """你是一个专业的新闻摘要助手。请根据微博热搜标题和相关内容，生成500字左右的描述。

你的任务是分析热搜内容，提取关键信息，生成详细准确的描述。

要求：
1. 基于提供的微博内容进行总结（优先使用真实内容）
2. 语言简洁明了，通俗易懂
3. 控制在500字左右
4. 突出新闻的核心信息（时间、地点、人物、事件）
5. 可以包含更多背景信息和细节，使描述更丰富

"""),
            ("user", "热搜标题：{title}\n\n微博内容：\n{content}\n\n请生成500字左右的描述：")
        ])

        # 生成总结
        chain = prompt | llm
        result = await chain.ainvoke({
            "title": title,
            "content": content[:2000]  # 限制内容长度避免超token
        })

        description = result.content.strip()

        # 清理描述文本：删除换行符和空行
        description = clean_description_text(description)

        # 确保长度合理
        if len(description) > 550:
            description = description[:550] + "..."

        logger.info(f"✅ LLM 总结成功: {description[:50]}...")
        return "Agent总结: " + description

    except Exception as e:
        logger.error(f"❌ LLM 总结失败: {e}", exc_info=True)

        # 降级方案：截取内容
        if content and len(content) > 100:
            # 清理内容中的换行符
            cleaned_content = clean_description_text(content)
            truncated_content = cleaned_content[:500] + "..." if len(cleaned_content) > 500 else cleaned_content
            return "截断: " + truncated_content
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
