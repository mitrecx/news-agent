"""测试 Agent API 是否正常工作"""
import asyncio
from src.agent.base import NewsAgent
from src.tools import fetch_weibo_hot_search


async def main():
    print("=" * 60)
    print("测试 Agent API")
    print("=" * 60)

    agent = NewsAgent(tools=[fetch_weibo_hot_search])

    # 测试用例
    test_cases = [
        {
            "question": "你好",
            "description": "简单问候",
            "expect_direct_return": False
        },
        {
            "question": "微博热搜",
            "description": "微博热搜（应该直接返回）",
            "expect_direct_return": True
        },
        {
            "question": "请介绍一下今天的新闻",
            "description": "普通问题",
            "expect_direct_return": False
        },
        {
            "question": "热搜榜",
            "description": "热搜（别名）",
            "expect_direct_return": True
        }
    ]

    for i, test_case in enumerate(test_cases, 1):
        question = test_case["question"]
        description = test_case["description"]
        expect_direct = test_case["expect_direct_return"]

        print(f"\n测试 {i}: {description}")
        print(f"问题: {question}")

        try:
            result = await agent.chat(question, history=None)

            # 检查结果
            if expect_direct:
                if result.startswith("📊 微博热搜榜："):
                    print(f"✓ 成功 - 直接返回热搜列表 ({len(result)} 字符)")
                else:
                    print(f"✗ 失败 - 期望直接返回热搜，但得到: {result[:100]}...")
            else:
                print(f"✓ 成功 - 返回 {len(result)} 字符")
                print(f"前100字: {result[:100]}...")

        except Exception as e:
            print(f"✗ 异常: {e}")
            import traceback
            traceback.print_exc()

    print("\n" + "=" * 60)
    print("测试完成")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
