"""测试微博热搜缓存集成"""

import asyncio
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.tools.weibo import get_scraper
from src.auth.database import db


async def test_cache_integration():
    """测试缓存集成"""
    print("🧪 测试微博热搜缓存集成")
    print("=" * 60)

    # 初始化数据库连接
    print("\n🔗 初始化数据库连接...")
    await db.connect()
    print("✓ 数据库已连接\n")

    try:
        scraper = get_scraper()

        # 第一次获取热搜（会生成缓存）
        print("📥 第一次获取热搜（应生成新缓存）...")
        items_1 = await scraper.fetch_hot_search()

        if items_1:
            print(f"✓ 获取到 {len(items_1)} 条热搜")

            # 统计缓存命中情况
            cached_count = sum(1 for item in items_1 if item.description)
            print(f"✓ 有描述的条目: {cached_count}/{len(items_1)}")

            # 检查前3条的描述来源
            print("\n前3条热搜描述来源:")
            for i, item in enumerate(items_1[:3], 1):
                desc_source = getattr(item, 'description_source', 'none')
                desc_preview = (item.description or '')[:50] + '...' if item.description else '无'
                print(f"  {i}. [{item.rank}] {item.title}")
                print(f"     来源: {desc_source}, 描述: {desc_preview}")

            # 第二次获取热搜（应使用缓存）
            print("\n📥 第二次获取热搜（应使用缓存）...")
            items_2 = await scraper.fetch_hot_search()

            if items_2:
                print(f"✓ 获取到 {len(items_2)} 条热搜")
                cached_count_2 = sum(1 for item in items_2 if item.description)
                print(f"✓ 有描述的条目: {cached_count_2}/{len(items_2)}")

                print("\n前3条热搜描述来源:")
                for i, item in enumerate(items_2[:3], 1):
                    desc_source = getattr(item, 'description_source', 'none')
                    desc_preview = (item.description or '')[:50] + '...' if item.description else '无'
                    print(f"  {i}. [{item.rank}] {item.title}")
                    print(f"     来源: {desc_source}, 描述: {desc_preview}")

            print("\n" + "=" * 60)
            print("✅ 缓存集成测试完成")
            print("=" * 60)

        else:
            print("❌ 未能获取热搜数据")

    finally:
        # 关闭数据库连接
        await db.disconnect()
        print("\n✓ 数据库连接已关闭")


if __name__ == "__main__":
    asyncio.run(test_cache_integration())
