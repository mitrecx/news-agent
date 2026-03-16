"""调试微博内容获取"""

import asyncio
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


async def main():
    print("=" * 60)
    print("微博内容获取调试")
    print("=" * 60)

    from src.tools.weibo import WeiboScraper
    from src.agent.config import get_settings

    settings = get_settings()

    scraper = WeiboScraper(
        timeout=10,
        use_selenium=False,
        cookie=settings.weibo_cookie
    )

    # 测试URL
    test_urls = [
        "https://s.weibo.com/weibo?q=%23鹿哈或需赔偿消费者26.9%E4%BA%BF%E8%B4%B9%E8%80%8526.9%E4%BA%BF%E5%85%83",
        "https://s.weibo.com/weibo?q=%23315%23",
    ]

    for url in test_urls:
        print(f"\n{'='*60}")
        print(f"测试 URL: {url}")
        print(f"{'='*60}")

        # 方法1: HTTP 请求
        print("\n方法1: HTTP 请求")
        try:
            import httpx
            from bs4 import BeautifulSoup

            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(
                    url,
                    headers=scraper.headers,
                    follow_redirects=True
                )

                print(f"状态码: {response.status_code}")
                print(f"内容长度: {len(response.text)} 字节")

                # 检查是否被重定向到验证系统
                if "Sina Visitor System" in response.text:
                    print("❌ 被重定向到 Sina Visitor System")
                elif "pl_top_realtimehot" in response.text:
                    print("⚠️ 这是热搜列表页，不是详情页")
                else:
                    print("✅ 正常页面")

                # 尝试提取内容
                soup = BeautifulSoup(response.text, "lxml")

                # 保存HTML用于分析
                debug_file = f"debug_page_{len(url)}.html"
                with open(debug_file, "w", encoding="utf-8") as f:
                    f.write(response.text)
                print(f"📄 页面已保存到 {debug_file}")

                # 查找各种可能的选择器
                selectors = [
                    "div.WB_text",
                    "div.WB_detail",
                    "div[node-type='feed_list'] div.WB_text",
                    "article div.WB_text",
                    ".WB_text",
                    "div.card-wrap",
                    "div.card",
                    ".card-wrap",
                    "div[class*='card']",
                    "div[class*='feed']",
                    "div.WB_feed",
                    ".WB_feed",
                ]

                found_any = False
                for selector in selectors:
                    elements = soup.select(selector)
                    if elements:
                        print(f"✅ 找到 {len(elements)} 个元素（选择器: {selector}）")
                        found_any = True
                        for i, elem in enumerate(elements[:3]):
                            text = elem.get_text(strip=True)
                            if text:
                                print(f"   [{i+1}] {text[:80]}...")
                        break

                if not found_any:
                    print(f"❌ 所有选择器都未找到内容")
                    # 尝试找到所有带class的div，看看页面结构
                    all_divs = soup.find_all("div", class_=True)
                    print(f"\n页面中有 {len(all_divs)} 个带class的div")
                    print("前20个div的class:")
                    for i, div in enumerate(all_divs[:20]):
                        classes = " ".join(div.get("class", []))
                        print(f"  [{i+1}] {classes[:100]}")

        except Exception as e:
            print(f"❌ HTTP 请求失败: {e}")

        # 方法2: 检查是否需要使用其他URL格式
        print("\n方法2: 检查链接类型")
        if "/weibo?q=" in url:
            print("这是话题搜索页，需要解析话题页内容")
        elif "weibo.com/" in url:
            print("这是微博详情页")

        print(f"\n提示: URL 可能需要解码：")
        import urllib.parse
        decoded = urllib.parse.unquote(url)
        print(f"解码后: {decoded}")


if __name__ == "__main__":
    asyncio.run(main())
