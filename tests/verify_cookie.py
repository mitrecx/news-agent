"""测试微博 Cookie 是否有效"""

import asyncio
import sys
import os

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


async def test_cookie():
    """测试 Cookie 是否有效"""
    print("=" * 60)
    print("微博 Cookie 验证测试")
    print("=" * 60)

    # 检查是否配置了 Cookie
    from src.agent.config import get_settings

    settings = get_settings()

    if not settings.weibo_cookie:
        print("\n❌ 未配置 Cookie")
        print("\n请按以下步骤获取 Cookie：")
        print("1. 参考 docs/WEIBO_COOKIE_GUIDE.md")
        print("2. 在 .env 文件中添加: WEIBO_COOKIE=SUB=xxx; SUBP=xxx; ALF=xxx")
        print("3. 重新运行此测试")
        return

    print(f"\n✅ 已配置 Cookie")
    print(f"Cookie 预览: {settings.weibo_cookie[:50]}...")

    # 测试 Cookie
    from src.tools.weibo import WeiboScraper

    scraper = WeiboScraper(
        timeout=10,
        use_selenium=False,
        cookie=settings.weibo_cookie
    )

    # 测试1: 访问热搜列表页
    print("\n" + "=" * 60)
    print("测试 1: 访问热搜列表页")
    print("=" * 60)

    try:
        import httpx

        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(
                "https://s.weibo.com/top/summary?cate=realtimehot",
                headers=scraper.headers,
                follow_redirects=True
            )

            print(f"✅ 成功访问热搜页")
            print(f"   状态码: {response.status_code}")

            # 检查是否被重定向到验证系统
            if "Sina Visitor System" in response.text:
                print(f"❌ Cookie 无效或已过期")
                print(f"   页面标题: Sina Visitor System")
                print(f"\n请重新获取 Cookie 并更新配置")
                return
            elif "pl_top_realtimehot" in response.text:
                print(f"✅ Cookie 有效，成功绕过验证系统")
            else:
                print(f"⚠️ 页面结构可能已变化")

    except Exception as e:
        print(f"❌ 访问失败: {e}")
        return

    # 测试2: 访问话题页
    print("\n" + "=" * 60)
    print("测试 2: 访问话题搜索页")
    print("=" * 60)

    try:
        test_url = "https://s.weibo.com/weibo?q=%23春节档电影票房创新高%23"

        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(
                test_url,
                headers=scraper.headers,
                follow_redirects=True
            )

            print(f"✅ 成功访问话题页")
            print(f"   URL: {test_url}")
            print(f"   状态码: {response.status_code}")

            # 检查是否有微博内容
            from bs4 import BeautifulSoup
            soup = BeautifulSoup(response.text, "lxml")

            # 保存HTML用于调试
            with open("verify_page.html", "w", encoding="utf-8") as f:
                f.write(response.text)
            print(f"📄 页面已保存到 verify_page.html")

            # 查找微博内容
            has_content = False
            selectors = ["div.card-wrap[action-type='feed_list_item']", "div.card-wrap", "div.WB_text", "div.WB_cardwrap"]

            for selector in selectors:
                elements = soup.select(selector)
                if elements:
                    print(f"✅ 找到微博内容（选择器: {selector}）")
                    print(f"   数量: {len(elements)}")

                    # 显示第一条微博的预览
                    # 话题搜索页使用 p.txt, 个人微博页使用 div.WB_text
                    text_elem = elements[0].select_one("p.txt") or elements[0].select_one("p[node-type='feed_list_content']") or elements[0].select_one("div.WB_text")

                    # 调试：打印元素结构
                    if not text_elem:
                        # 打印第一个元素的子元素
                        print(f"   调试: 第一个元素的class: {elements[0].get('class')}")
                        children = list(elements[0].children)
                        print(f"   调试: 直接子元素数量: {len([c for c in children if hasattr(c, 'name')])}")
                        for i, child in enumerate(elements[0].find_all(True)[:5]):
                            print(f"   调试: 子元素[{i}] {child.name}: class={child.get('class')}")

                    if text_elem:
                        text = text_elem.get_text(strip=True)
                        print(f"   内容预览: {text[:100]}...")
                        has_content = True
                    break

            if not has_content:
                print(f"⚠️ 未找到微博内容")

    except Exception as e:
        print(f"❌ 访问失败: {e}")
        return

    print("\n" + "=" * 60)
    print("✅ Cookie 验证通过！")
    print("=" * 60)
    print("\n💡 提示：")
    print("1. Cookie 有效期通常为 30 天")
    print("2. 如果频繁失效，请降低爬取频率")
    print("3. 可以使用多个账号的 Cookie 轮换")


if __name__ == "__main__":
    asyncio.run(test_cookie())
