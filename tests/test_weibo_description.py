"""测试微博热搜描述生成功能"""

import asyncio
import sys
import os

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


async def test_fetch_hot_search():
    """测试获取微博热搜"""
    from src.tools.weibo import get_scraper

    print("测试：获取微博热搜（5条）")
    print("=" * 60)

    scraper = get_scraper()

    # 获取热搜
    items = await scraper.fetch_hot_search(limit=5, fetch_descriptions=False)

    print(f"\n获取到 {len(items)} 条热搜：")
    print("-" * 60)

    for item in items:
        print(f"\n[{item.rank}] {item.title}")
        print(f"  热度: {item.hot_value}")
        print(f"  链接: {item.url}")
        print(f"  分类: {item.category}")
        print(f"  描述: {item.description or '（生成中...）'}")
        print(f"  来源: {item.description_source or '-'}")

    print("\n" + "=" * 60)
    print("描述正在后台生成中，请稍候...")


async def test_fetch_item_content():
    """测试获取单条热搜内容"""
    from src.tools.weibo import HotSearchItem, get_scraper

    print("\n测试：获取单条热搜内容")
    print("=" * 60)

    scraper = get_scraper()

    # 创建测试热搜项
    test_item = HotSearchItem(
        rank=1,
        title="春节档电影票房创新高",
        hot_value="298.5万",
        category="娱乐",
        url="https://s.weibo.com/weibo?q=%23春节档电影票房创新高%23",
        icon="新"
    )

    print(f"热搜标题: {test_item.title}")
    print(f"热搜链接: {test_item.url}")

    # 获取内容
    content = await scraper._fetch_item_content(test_item)

    print(f"\n获取到的内容（前200字）:")
    print("-" * 60)
    print(content[:200] if content else "（未获取到内容）")
    print("-" * 60)

    return content


async def test_llm_summary():
    """测试 LLM 总结功能"""
    from src.tools.llm_summary import summarize_weibo_content

    print("\n测试：LLM 总结")
    print("=" * 60)

    title = "春节档电影票房创新高"
    content = """
    2025年春节档电影票房突破100亿元大关，创下历史新高。
    其中《热辣滚烫》《飞驰人生2》《第二十条》等影片表现亮眼。
    观影人次超过2亿，同比增长15%。
    业内人士认为，这标志着中国电影市场的强劲复苏。
    """

    print(f"热搜标题: {title}")
    print(f"原始内容: {content.strip()}")

    # 生成总结
    description = await summarize_weibo_content(title, content)

    print(f"\n生成的描述:")
    print("-" * 60)
    print(description)
    print("-" * 60)


async def main():
    """主测试函数"""
    print("\n" + "=" * 60)
    print("微博热搜描述生成功能测试")
    print("=" * 60)

    # 测试1: 获取热搜列表
    await test_fetch_hot_search()

    # 等待一段时间让后台任务生成描述
    print("\n等待30秒，让后台任务生成描述...")
    await asyncio.sleep(30)

    # 测试2: 获取单条内容
    # await test_fetch_item_content()

    # 测试3: LLM 总结
    # await test_llm_summary()

    print("\n" + "=" * 60)
    print("测试完成！")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
