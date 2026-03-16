"""网络诊断工具 - 检查网络连接问题"""

import asyncio
import socket
import sys
import os

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


async def test_dns_resolution():
    """测试 DNS 解析"""
    print("\n" + "=" * 60)
    print("1. DNS 解析测试")
    print("=" * 60)

    hosts = [
        "s.weibo.com",
        "weibo.com",
        "www.baidu.com",
        "www.google.com"
    ]

    for host in hosts:
        try:
            ip = socket.gethostbyname(host)
            print(f"✅ {host} -> {ip}")
        except socket.gaierror as e:
            print(f"❌ {host} - DNS 解析失败: {e}")


async def test_tcp_connection():
    """测试 TCP 连接"""
    print("\n" + "=" * 60)
    print("2. TCP 连接测试")
    print("=" * 60)

    targets = [
        ("s.weibo.com", 443),
        ("weibo.com", 443),
        ("www.baidu.com", 443),
        ("www.google.com", 80)
    ]

    for host, port in targets:
        try:
            reader, writer = await asyncio.wait_for(
                asyncio.open_connection(host, port),
                timeout=5.0
            )
            print(f"✅ {host}:{port} - 连接成功")
            writer.close()
            await writer.wait_closed()
        except asyncio.TimeoutError:
            print(f"❌ {host}:{port} - 连接超时")
        except ConnectionRefusedError:
            print(f"❌ {host}:{port} - 连接被拒绝")
        except Exception as e:
            print(f"❌ {host}:{port} - 连接失败: {e}")


async def test_http_request():
    """测试 HTTP 请求"""
    print("\n" + "=" * 60)
    print("3. HTTP 请求测试")
    print("=" * 60)

    import httpx

    urls = [
        "https://s.weibo.com/top/summary?cate=realtimehot",
        "https://weibo.com",
        "https://www.baidu.com"
    ]

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                     "AppleWebKit/537.36 (KHTML, like Gecko) "
                     "Chrome/120.0.0.0 Safari/537.36"
    }

    for url in urls:
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(url, headers=headers, follow_redirects=True)
                print(f"✅ {url}")
                print(f"   状态码: {response.status_code}")
                print(f"   内容长度: {len(response.content)} 字节")
        except httpx.ConnectError as e:
            print(f"❌ {url}")
            print(f"   连接错误: {e}")
        except httpx.TimeoutException:
            print(f"❌ {url}")
            print(f"   请求超时")
        except Exception as e:
            print(f"❌ {url}")
            print(f"   错误: {e}")


async def test_weibo_scraper():
    """测试微博热搜爬虫"""
    print("\n" + "=" * 60)
    print("4. 微博热搜爬虫测试")
    print("=" * 60)

    from src.tools.weibo import get_scraper

    scraper = get_scraper()

    # 测试基础爬取
    print("\n测试基础热搜爬取...")
    try:
        items = await scraper._fetch_hot_search_items(limit=5)
        print(f"✅ 成功爬取 {len(items)} 条热搜")

        if items:
            print("\n热搜列表:")
            for item in items[:3]:
                print(f"  [{item.rank}] {item.title}")
                print(f"      链接: {item.url[:80]}...")

                # 测试单条热搜内容获取
                print(f"\n  测试获取内容...")
                content = await scraper._fetch_item_content(item)
                if content:
                    print(f"  ✓ 成功获取内容: {len(content)} 字符")
                    print(f"  内容预览: {content[:100]}...")
                else:
                    print(f"  ✗ 未获取到内容")

    except Exception as e:
        print(f"❌ 爬取失败: {e}")
        import traceback
        traceback.print_exc()


async def test_selenium_availability():
    """测试 Selenium 可用性"""
    print("\n" + "=" * 60)
    print("5. Selenium 可用性测试")
    print("=" * 60)

    try:
        from selenium import webdriver
        from selenium.webdriver.chrome.service import Service
        from webdriver_manager.chrome import ChromeDriverManager

        print("✅ Selenium 已安装")

        # 尝试启动 Chrome
        try:
            from selenium.webdriver.chrome.options import Options

            chrome_options = Options()
            chrome_options.add_argument('--headless')
            chrome_options.add_argument('--no-sandbox')
            chrome_options.add_argument('--disable-dev-shm-usage')

            service = Service(ChromeDriverManager().install())
            driver = webdriver.Chrome(service=service, options=chrome_options)

            print("✅ Chrome 浏览器启动成功")

            # 测试访问微博
            driver.get("https://s.weibo.com/top/summary?cate=realtimehot")

            print(f"✅ 成功访问微博热搜页")
            print(f"   页面标题: {driver.title}")
            print(f"   页面长度: {len(driver.page_source)} 字符")

            driver.quit()

        except Exception as e:
            print(f"❌ Chrome 浏览器测试失败: {e}")

    except ImportError:
        print("❌ Selenium 未安装")


async def check_firewall_proxy():
    """检查防火墙和代理设置"""
    print("\n" + "=" * 60)
    print("6. 环境检查")
    print("=" * 60)

    # 检查环境变量
    proxy_vars = ["HTTP_PROXY", "HTTPS_PROXY", "http_proxy", "https_proxy", "ALL_PROXY", "all_proxy"]
    has_proxy = False

    for var in proxy_vars:
        value = os.environ.get(var)
        if value:
            print(f"📡 代理设置: {var}={value}")
            has_proxy = True

    if not has_proxy:
        print("✓ 未检测到代理设置")

    # 检查 Python 版本
    print(f"\n🐍 Python 版本: {sys.version}")

    # 检查操作系统
    import platform
    print(f"💻 操作系统: {platform.system()} {platform.release()}")


async def main():
    """主诊断函数"""
    print("\n" + "=" * 60)
    print("网络诊断工具")
    print("=" * 60)
    print("此工具将诊断以下问题:")
    print("1. DNS 解析")
    print("2. TCP 连接")
    print("3. HTTP/HTTPS 请求")
    print("4. 微博热搜爬虫")
    print("5. Selenium 可用性")
    print("6. 环境配置")

    try:
        await test_dns_resolution()
        await test_tcp_connection()
        await test_http_request()
        await test_weibo_scraper()
        await test_selenium_availability()
        await check_firewall_proxy()

        print("\n" + "=" * 60)
        print("诊断完成！")
        print("=" * 60)

        print("\n💡 建议:")
        print("1. 如果 DNS 解析失败: 检查网络连接，尝试更换 DNS 服务器")
        print("2. 如果 TCP 连接失败: 检查防火墙设置，确保端口开放")
        print("3. 如果 HTTP 请求失败: 可能需要配置代理")
        print("4. 如果爬虫失败: 检查 Selenium 和 Chrome 是否正确安装")

    except Exception as e:
        print(f"\n❌ 诊断过程出错: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
