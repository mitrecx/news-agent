"""Weibo hot search scraper - 微博热搜爬虫"""

from datetime import datetime
from typing import List
from dataclasses import dataclass
import asyncio
import logging
import os

import httpx
from bs4 import BeautifulSoup

# 配置日志
logger = logging.getLogger(__name__)

# Selenium 相关导入（可选）
try:
    from selenium import webdriver
    from selenium.webdriver.chrome.service import Service
    from selenium.webdriver.chrome.options import Options
    from selenium.webdriver.common.by import By
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC
    from webdriver_manager.chrome import ChromeDriverManager
    SELENIUM_AVAILABLE = True
except ImportError:
    SELENIUM_AVAILABLE = False


@dataclass
class HotSearchItem:
    """热搜条目"""
    rank: int                    # 排名
    title: str                   # 标题
    hot_value: str               # 热度值（如 "234.5万"）
    category: str                # 分类
    url: str                     # 链接
    icon: str | None = None      # 图标类型（热、新、等）
    collected_at: datetime = None  # 采集时间

    # 描述相关字段
    description: str | None = None           # 热搜描述（100字左右）
    description_source: str | None = None    # 描述来源：weibo_detail/llm/cache/error
    description_generated_at: datetime | None = None  # 描述生成时间

    def __post_init__(self):
        if self.collected_at is None:
            self.collected_at = datetime.now()

    def to_dict(self) -> dict:
        """转换为字典"""
        return {
            "rank": self.rank,
            "title": self.title,
            "hot_value": self.hot_value,
            "category": self.category,
            "url": self.url,
            "icon": self.icon,
            "collected_at": self.collected_at.isoformat(),
            "description": self.description,
            "description_source": self.description_source,
            "description_generated_at": self.description_generated_at.isoformat() if self.description_generated_at else None,
        }

    def __str__(self) -> str:
        """字符串表示"""
        icon_str = f"[{self.icon}]" if self.icon else ""
        return f"{self.rank}. {icon_str}{self.title} (热度: {self.hot_value})"


class WeiboScraper:
    """微博热搜爬虫"""

    # 微博热搜 PC 端页面
    WEIBO_HOT_URL = "https://s.weibo.com/top/summary?cate=realtimehot"

    def __init__(self, timeout: int = 10, use_selenium: bool = False, proxy: str | None = None, cookie: str | None = None):
        """
        初始化爬虫

        Args:
            timeout: 请求超时时间（秒）
            use_selenium: 是否优先使用 Selenium（需要安装 Chrome）
            proxy: 代理服务器地址，格式: http://host:port 或 socks5://host:port
            cookie: 微博 Cookie，用于绕过 Sina Visitor System 验证
        """
        self.timeout = timeout
        self.use_selenium = use_selenium and SELENIUM_AVAILABLE
        self.proxy = proxy
        self.cookie = cookie

        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                         "AppleWebKit/537.36 (KHTML, like Gecko) "
                         "Chrome/120.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
            "Referer": "https://weibo.com",
        }

        # 如果提供了Cookie，添加到请求头中
        if self.cookie:
            self.headers["Cookie"] = self.cookie

        # 如果提供了 Cookie，添加到 headers
        if self.cookie:
            self.headers["Cookie"] = self.cookie

        # 数据库缓存管理器（延迟初始化）
        self._cache_manager = None

    async def _fetch_with_selenium(self, limit: int) -> List[HotSearchItem]:
        """
        使用 Selenium 爬取微博热搜

        Args:
            limit: 返回数量

        Returns:
            热搜条目列表
        """
        if not SELENIUM_AVAILABLE:
            raise Exception("Selenium 未安装")

        # 在新线程中运行 Selenium（避免阻塞事件循环），添加超时
        loop = asyncio.get_event_loop()
        try:
            return await asyncio.wait_for(
                loop.run_in_executor(None, self._selenium_fetch_sync, limit),
                timeout=60.0  # 60秒超时（增加以提高稳定性）
            )
        except asyncio.TimeoutError:
            logger.error("❌ Selenium 初始化超时 (60秒)")
            raise Exception("Selenium 初始化超时，可能 Chrome 浏览器未安装或启动失败")

    def _selenium_fetch_sync(self, limit: int) -> List[HotSearchItem]:
        """
        Selenium 同步爬取（在单独线程中运行）

        Args:
            limit: 返回数量

        Returns:
            热搜条目列表
        """
        logger.info("🔧 初始化 Chrome 浏览器...")
        print("   ├─ 下载 ChromeDriver...")
        print("   ├─ 配置无头模式...")
        print("   └─ 启动浏览器...")

        # 配置 Chrome 选项
        chrome_options = Options()
        chrome_options.add_argument('--headless')  # 无头模式
        chrome_options.add_argument('--no-sandbox')
        chrome_options.add_argument('--disable-dev-shm-usage')
        chrome_options.add_argument('--disable-gpu')
        chrome_options.add_argument('--window-size=1920,1080')
        chrome_options.add_argument('--disable-blink-features=AutomationControlled')  # 避免被检测为自动化
        chrome_options.add_argument('--disable-extensions')
        chrome_options.add_argument('--disable-infobars')
        chrome_options.add_argument('--disable-notifications')
        chrome_options.add_argument('--disable-popup-blocking')
        chrome_options.add_experimental_option('excludeSwitches', ['enable-automation'])
        chrome_options.add_experimental_option('useAutomationExtension', False)
        chrome_options.add_argument('--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')

        # 设置页面加载超时和脚本超时
        chrome_options.page_load_timeout = 30
        chrome_options.script_timeout = 30

        # 自动下载并使用 ChromeDriver
        logger.info("📦 安装 ChromeDriver...")
        service = None
        try:
            service = Service(ChromeDriverManager().install())
            logger.info("✅ ChromeDriver 安装成功")
        except Exception as e:
            logger.error(f"❌ ChromeDriver 安装失败: {e}")
            raise Exception(f"ChromeDriver 安装失败: {e}")

        logger.info("🚀 启动 Chrome 浏览器...")
        driver = None
        try:
            driver = webdriver.Chrome(service=service, options=chrome_options)
            logger.info("✅ Chrome 浏览器启动成功")
        except Exception as e:
            logger.error(f"❌ Chrome 浏览器启动失败: {e}")
            raise Exception(f"Chrome 浏览器启动失败: {e}")

        try:
            # 访问页面
            logger.info(f"📍 访问页面: {self.WEIBO_HOT_URL}")
            print(f"   └─ URL: {self.WEIBO_HOT_URL}")
            driver.get(self.WEIBO_HOT_URL)

            # 等待页面加载
            logger.info("⏳ 等待页面加载...")
            print("   └─ 等待动态内容加载...")
            WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.TAG_NAME, "body"))
            )

            # 额外等待，确保动态内容加载完成
            import time
            time.sleep(2)
            print("   └─ 页面加载完成")

            # 获取页面源码
            logger.info("📄 获取页面源码...")
            page_source = driver.page_source
            print(f"   └─ 页面大小: {len(page_source)} 字符")

            # 解析数据
            logger.info("🔍 解析热搜数据...")
            items = self._parse_hot_search(page_source, limit)
            print(f"   └─ 解析完成，获取 {len(items)} 条数据")

            return items

        finally:
            logger.info("🧹 关闭浏览器")
            # 强制清理所有 Chrome 和 ChromeDriver 进程
            if driver:
                try:
                    driver.quit()
                except Exception:
                    pass
            # 额外清理：确保 Service 进程被终止
            if service:
                try:
                    service.stop()
                except Exception:
                    pass
            # 强制清理残留的 Chrome 进程
            try:
                import subprocess
                result = subprocess.run(
                    ["ps", "aux"],
                    capture_output=True,
                    text=True,
                    timeout=5
                )
                for line in result.stdout.split('\n'):
                    if 'chromedriver' in line and '--headless' in line:
                        parts = line.split()
                        if len(parts) >= 2:
                            try:
                                pid = int(parts[1])
                                os.kill(pid, 9)  # SIGKILL
                            except (ValueError, ProcessLookupError, OSError):
                                pass
            except Exception:
                pass

    def _parse_hot_search(self, html: str, limit: int) -> List[HotSearchItem]:
        """
        解析微博热搜页面

        Args:
            html: HTML内容
            limit: 返回数量限制

        Returns:
            热搜条目列表
        """
        soup = BeautifulSoup(html, "lxml")
        items = []

        logger.debug(f"🔍 解析 HTML，限制: {limit}")
        print("   └─ 使用 BeautifulSoup 解析...")

        # 微博热搜在 #pl_top_realtimehot table tbody 中
        tbody = soup.select_one("#pl_top_realtimehot table tbody")
        if not tbody:
            # 尝试其他选择器
            logger.debug("⚠️ 未找到 #pl_top_realtimehot，尝试其他选择器")
            tbody = soup.select_one("tbody")

        if not tbody:
            logger.error("❌ 未找到热搜数据，页面结构可能已变化")
            raise Exception("未找到热搜数据，页面结构可能已变化")

        rows = tbody.find_all("tr", limit=limit + 1)  # +1 因为第一行可能是标题
        logger.debug(f"📊 找到 {len(rows)} 行数据")
        print(f"   └─ 找到 {len(rows)} 行数据")

        parsed_count = 0
        for idx, row in enumerate(rows):
            # 检查是否已达到限制
            if parsed_count >= limit:
                logger.debug(f"   └─ 已达到限制 {limit} 条，停止解析")
                break

            if idx == 0:
                # 跳过表头
                if row.find("th"):
                    logger.debug("   └─ 跳过表头")
                    continue

            cells = row.find_all("td")
            if len(cells) < 2:
                continue

            try:
                # 解析排名
                rank_cell = cells[0]
                rank = rank_cell.get_text(strip=True)
                if not rank.isdigit():
                    # 尝试从 class 获取排名
                    rank = str(idx)

                # 解析标题和链接
                title_cell = cells[1]
                link = title_cell.find("a")
                if not link:
                    continue

                title = link.get_text(strip=True)
                url = link.get("href", "")

                # 验证和清理 URL
                if url:
                    # 跳过无效的 URL (javascript:, mailto:, #, etc.)
                    if url.startswith(("javascript:", "mailto:", "#", "void")):
                        # 构建默认的话题搜索 URL
                        from urllib.parse import quote
                        encoded_title = quote(f"#{title}#")
                        url = f"https://s.weibo.com/weibo?q={encoded_title}"
                    elif not url.startswith("http"):
                        # 相对路径，添加域名
                        url = "https://s.weibo.com" + url
                else:
                    # 没有 URL，构建默认搜索链接
                    from urllib.parse import quote
                    encoded_title = quote(f"#{title}#")
                    url = f"https://s.weibo.com/weibo?q={encoded_title}"

                # 解析热度值
                hot_value = ""
                if len(cells) > 2:
                    hot_cell = cells[2]
                    hot_value = hot_cell.get_text(strip=True)

                # 解析图标（热、新等）
                icon = None
                icon_span = title_cell.find("span", class_="icon")
                if icon_span:
                    icon = icon_span.get_text(strip=True)

                # 解析分类（不显示）
                category = ""
                category_cell = row.find("td", class_="cate")
                if category_cell:
                    category = category_cell.get_text(strip=True)

                item = HotSearchItem(
                    rank=int(rank) if rank.isdigit() else idx,
                    title=title,
                    hot_value=hot_value,
                    category=category,
                    url=url,
                    icon=icon
                )
                items.append(item)
                parsed_count += 1
                logger.debug(f"   └─ 解析第 {parsed_count} 条: {title[:30]}...")

            except (ValueError, AttributeError) as e:
                # 跳过解析失败的行
                logger.debug(f"   ⚠️ 跳过第 {idx} 行: {e}")
                continue

        logger.info(f"✅ 成功解析 {len(items)} 条热搜")
        return items

    async def _fetch_item_content(self, item: HotSearchItem) -> str:
        """
        为单条热搜获取微博内容

        Args:
            item: 热搜条目

        Returns:
            微博内容字符串
        """
        url = item.url

        # 判断链接类型
        if "/weibo?q=" in url or "/weibo/search" in url:
            # 话题搜索页
            return await self._fetch_topic_page(url)
        elif "weibo.com/" in url and "/weibo?q=" not in url:
            # 具体微博详情页
            return await self._fetch_weibo_post(url)
        else:
            # 未知类型，返回空
            logger.warning(f"未知的链接类型: {url}")
            return ""

    async def _fetch_topic_page(self, url: str, max_retries: int = 3) -> str:
        """
        爬取话题搜索页面

        Args:
            url: 话题搜索页 URL
            max_retries: 最大重试次数（默认3次）

        Returns:
            提取的微博内容
        """
        if not SELENIUM_AVAILABLE:
            logger.warning("Selenium 不可用，无法爬取话题页")
            return ""

        logger.info(f"  爬取话题页: {url}")

        # 重试机制
        for attempt in range(max_retries + 1):
            try:
                # 在线程池中运行 Selenium
                loop = asyncio.get_event_loop()
                result = await asyncio.wait_for(
                    loop.run_in_executor(None, self._fetch_topic_page_sync, url),
                    timeout=45.0  # 增加超时到45秒
                )
                return result
            except asyncio.TimeoutError:
                logger.warning(f"话题页爬取超时 (尝试 {attempt + 1}/{max_retries + 1}): {url}")
                if attempt < max_retries:
                    await asyncio.sleep(2 ** attempt)  # 指数退避
                else:
                    logger.error(f"话题页爬取失败，已达最大重试次数: {url}")
                    return ""
            except Exception as e:
                logger.warning(f"话题页爬取异常 (尝试 {attempt + 1}/{max_retries + 1}): {e}")
                if attempt < max_retries:
                    await asyncio.sleep(2 ** attempt)
                else:
                    logger.error(f"话题页爬取失败: {e}")
                    return ""

    def _fetch_topic_page_sync(self, url: str) -> str:
        """
        同步爬取话题页（Selenium）

        Args:
            url: 话题页 URL

        Returns:
            微博内容
        """
        if not SELENIUM_AVAILABLE:
            return ""

        # 配置 Chrome
        chrome_options = Options()
        chrome_options.add_argument('--headless')
        chrome_options.add_argument('--no-sandbox')
        chrome_options.add_argument('--disable-dev-shm-usage')
        chrome_options.add_argument('--disable-gpu')
        chrome_options.add_argument('--window-size=1920,1080')
        chrome_options.add_argument('--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36')

        driver = None
        service = None
        try:
            service = Service(ChromeDriverManager().install())
            driver = webdriver.Chrome(service=service, options=chrome_options)

            # 如果提供了 Cookie，先设置 Cookie
            if self.cookie:
                try:
                    # 先访问微博域名以设置 Cookie 作用域
                    driver.get("https://s.weibo.com")

                    # 解析并设置 Cookie
                    # Cookie 格式: "SUB=xxx; SUBP=xxx; ALF=xxx"
                    for cookie_part in self.cookie.split(';'):
                        cookie_part = cookie_part.strip()
                        if '=' in cookie_part:
                            name, value = cookie_part.split('=', 1)
                            # 为多个域名添加 Cookie
                            for domain in ['.weibo.com', 's.weibo.com', 'weibo.com']:
                                driver.add_cookie({
                                    'name': name.strip(),
                                    'value': value.strip(),
                                    'domain': domain,
                                    'path': '/'
                                })

                    logger.debug("✅ 已设置微博 Cookie")
                except Exception as e:
                    logger.warning(f"⚠️ 设置 Cookie 失败: {e}")

            # 访问页面
            driver.get(url)

            # 等待加载
            WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.TAG_NAME, "body"))
            )

            import time
            time.sleep(2)

            # 提取微博内容
            soup = BeautifulSoup(driver.page_source, "lxml")

            # 尝试多个选择器
            selectors = [
                "div.card-wrap[action-type='feed_list_item']",  # 话题搜索页（过滤掉发微博输入框）
                "div.card-wrap",
                "div.WB_cardwrap",
                "article.WB_cardwrap",
                "div.WB_feed_type",
                "div[node-type='feed_list']",
            ]

            contents = []
            for selector in selectors:
                post_cards = soup.select(selector)
                if post_cards:
                    logger.debug(f"找到 {len(post_cards)} 条微博（选择器: {selector}）")

                    for card in post_cards[:3]:  # 取前3条
                        # 提取正文 - 话题搜索页使用 p.txt, 个人微博页使用 div.WB_text
                        text_elem = card.select_one("p.txt") or card.select_one("p[node-type='feed_list_content']") or card.select_one("div.WB_text")
                        if text_elem:
                            text = text_elem.get_text(strip=True)
                            if text:
                                # 移除话题标签
                                import re
                                text = re.sub(r'#.*?#', '', text)
                                text = text.strip()
                                if text:
                                    contents.append(text)

                    if contents:
                        break

            return "\n\n".join(contents) if contents else ""

        except Exception as e:
            logger.error(f"爬取话题页失败: {e}")
            return ""
        finally:
            # 强制清理所有 Chrome 和 ChromeDriver 进程
            if driver:
                try:
                    driver.quit()
                except Exception:
                    pass
            # 额外清理：确保 Service 进程被终止
            if service:
                try:
                    service.stop()
                except Exception:
                    pass
            # 强制清理残留的 Chrome 进程（仅当前会话创建的）
            try:
                import subprocess
                # 查找并杀死 chromedriver 进程（限制为最近1分钟创建的）
                result = subprocess.run(
                    ["ps", "aux"],
                    capture_output=True,
                    text=True,
                    timeout=5
                )
                for line in result.stdout.split('\n'):
                    if 'chromedriver' in line and '--headless' in line:
                        parts = line.split()
                        if len(parts) >= 2:
                            try:
                                pid = int(parts[1])
                                os.kill(pid, 9)  # SIGKILL
                            except (ValueError, ProcessLookupError, OSError):
                                pass
            except Exception:
                pass

    async def _fetch_weibo_post(self, url: str) -> str:
        """
        爬取单条微博详情页

        Args:
            url: 微博详情页 URL

        Returns:
            微博内容
        """
        logger.info(f"  爬取微博详情页: {url}")

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(url, headers=self.headers, follow_redirects=True)
                response.raise_for_status()

            soup = BeautifulSoup(response.text, "lxml")

            # 检查页面类型
            if "s.weibo.com/weibo?q=" in url:
                # 话题搜索页 - 使用 card-wrap 选择器（过滤掉发微博输入框）
                contents = []
                cards = soup.select("div.card-wrap[action-type='feed_list_item']")
                logger.debug(f"  找到 {len(cards)} 条微博")

                for card in cards[:3]:  # 取前3条
                    text_elem = card.select_one("p.txt") or card.select_one("p[node-type='feed_list_content']")
                    if text_elem:
                        text = text_elem.get_text(strip=True)
                        if text:
                            # 移除话题标签
                            import re
                            text = re.sub(r'#.*?#', '', text)
                            text = text.strip()
                            if text:
                                contents.append(text)

                return "\n\n".join(contents) if contents else ""
            else:
                # 个人微博详情页 - 使用 WB_text 选择器
                text_elem = soup.select_one("div.WB_text")
                if text_elem:
                    content = text_elem.get_text(strip=True)

                    # 提取评论（可选）
                    comments = []
                    comment_elems = soup.select("div.WB_text, .comment-list .WB_text")
                    for elem in comment_elems[:3]:
                        comment_text = elem.get_text(strip=True)
                        if comment_text and comment_text != content:
                            comments.append(comment_text)

                    if comments:
                        content += "\n\n热门评论：\n" + "\n".join(comments)

                    return content
                else:
                    logger.warning(f"未找到微博内容: {url}")
                    return ""

        except Exception as e:
            logger.error(f"爬取微博详情页失败: {e}")
            return ""

    async def fetch_hot_search(self, limit: int = 40, fetch_descriptions: bool = False) -> list[HotSearchItem]:
        """
        获取微博热搜榜

        Args:
            limit: 返回热搜数量
            fetch_descriptions: 是否立即获取描述（同步），否则后台异步获取

        Returns:
            热搜条目列表
        """
        logger.info(f"🔍 开始获取微博热搜，数量: {limit}, 获取描述: {fetch_descriptions}")

        # 1. 爬取基础数据
        items = await self._fetch_hot_search_items(limit)

        # 2. 加载缓存描述
        await self._load_cached_descriptions(items)

        # 3. 生成缺失的描述
        missing_items = [item for item in items if not item.description]

        if fetch_descriptions:
            # 同步生成
            await self._generate_descriptions_sync(missing_items)
        else:
            # 后台异步生成
            if missing_items:
                asyncio.create_task(self._generate_descriptions_async(missing_items))

        return items

    async def _fetch_hot_search_items(self, limit: int) -> list[HotSearchItem]:
        """
        获取热搜基础数据（不含描述）

        Args:
            limit: 返回数量

        Returns:
            热搜条目列表
        """
        logger.info(f"🔍 开始获取微博热搜，数量: {limit}")
        print(f"📍 URL: {self.WEIBO_HOT_URL}")
        print(f"🔧 使用 Selenium: {self.use_selenium}")
        print(f"✅ Selenium 可用: {SELENIUM_AVAILABLE}")

        # 方法1: 如果配置了使用 Selenium，优先尝试
        if self.use_selenium:
            try:
                logger.info("🌐 尝试使用 Selenium 爬取...")
                print("🌐 步骤 1/4: 启动 Selenium 爬虫...")
                items = await self._fetch_with_selenium(limit)
                logger.info(f"✅ Selenium 爬取成功，获取 {len(items)} 条数据")
                print(f"✅ Selenium 爬取成功，获取 {len(items)} 条热搜\n")
                return items
            except Exception as e:
                logger.warning(f"⚠️ Selenium 爬取失败: {e}，尝试简单爬虫...")
                print(f"⚠️ Selenium 爬取失败: {e}")
                print(f"🔄 降级到 HTTP 爬虫...\n")

        # 方法2: 尝试简单 HTTP 爬虫
        try:
            logger.info("🌐 尝试使用 HTTP 爬虫...")
            print("🌐 步骤 2/4: 启动 HTTP 爬虫...")
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(
                    self.WEIBO_HOT_URL,
                    headers=self.headers,
                    follow_redirects=True
                )
                response.raise_for_status()

            items = self._parse_hot_search(response.text, limit)
            logger.info(f"✅ HTTP 爬取成功，获取 {len(items)} 条数据")
            print(f"✅ HTTP 爬取成功，获取 {len(items)} 条热搜\n")
            return items
        except httpx.HTTPError as e:
            logger.warning(f"⚠️ HTTP 爬取失败: {e}")
            print(f"⚠️ HTTP 爬取失败: {e}")
        except Exception as e:
            logger.warning(f"⚠️ 解析失败: {e}")
            print(f"⚠️ 解析失败: {e}")

        # 方法3: 尝试 Selenium（如果之前没用过）
        if not self.use_selenium and SELENIUM_AVAILABLE:
            try:
                logger.info("🌐 最后尝试使用 Selenium 爬取...")
                print("🌐 步骤 3/4: 最后尝试 Selenium...")
                items = await self._fetch_with_selenium(limit)
                logger.info(f"✅ Selenium 爬取成功，获取 {len(items)} 条数据")
                print(f"✅ Selenium 爬取成功，获取 {len(items)} 条热搜\n")
                return items
            except Exception as e:
                logger.warning(f"⚠️ Selenium 爬取也失败: {e}")
                print(f"⚠️ Selenium 爬取也失败: {e}")

        # 所有爬取方法都失败，抛出异常
        logger.error("❌ 所有爬取方法都失败，无法获取微博热搜数据")
        print("❌ 错误: 所有爬取方法都失败，请检查网络连接或微博 Cookie 配置")
        raise Exception("所有爬取方法都失败，无法获取微博热搜数据。请检查：1) 网络连接 2) 微博 Cookie 是否有效 3) 微博是否可访问")

    async def _ensure_cache_manager(self):
        """确保缓存管理器已初始化"""
        if self._cache_manager is None:
            from ..auth.database import db
            from .weibo_cache import WeiboHotSearchCache
            # 传入连接池而不是连接
            self._cache_manager = WeiboHotSearchCache(db.pool)

    async def _load_cached_descriptions(self, items: list) -> None:
        """
        从数据库缓存加载已有描述

        Args:
            items: 热搜条目列表，会被就地修改
        """
        await self._ensure_cache_manager()

        titles = [item.title for item in items]
        cache_map = await self._cache_manager.batch_get(titles)

        cache_hits = 0
        now = datetime.now()

        for item in items:
            cached = cache_map.get(item.title)
            if cached:
                # 检查缓存是否过期（8小时）
                age = (now - cached['created_at']).total_seconds()
                if age < 28800:  # 8小时 = 28800秒
                    item.description = cached['description']
                    item.description_source = cached['description_source']
                    item.description_generated_at = cached['created_at']
                    cache_hits += 1

        logger.info(f"✓ Cache loaded: {cache_hits}/{len(items)} hits")

    async def _generate_descriptions_async(self, items: list) -> None:
        """
        后台异步生成描述

        注意：需要配置微博 Cookie 才能成功爬取详情页。
        详见 docs/WEIBO_COOKIE_GUIDE.md

        Args:
            items: 需要生成描述的热搜列表
        """
        if not items:
            return

        logger.info(f"📝 后台任务开始，为 {len(items)} 条热搜生成描述")
        print("\n" + "=" * 60)
        print(f"📝 后台生成热搜描述（{len(items)} 条）")
        if self.cookie:
            print("✅ 使用 Cookie 认证")
        else:
            print("⚠️  未配置 Cookie，可能被 Sina Visitor System 拦截")
            print("💡 参考 docs/WEIBO_COOKIE_GUIDE.md 获取 Cookie")
        print("=" * 60)

        # 控制并发数（避免过载）
        # 使用串行执行（并发=1）以避免 ChromeDriver 连接冲突
        semaphore = asyncio.Semaphore(1)

        # 限制生成数量
        items_to_process = items[:50]  # 最多50条

        async def generate_one(item: HotSearchItem):
            async with semaphore:
                try:
                    print(f"  [{item.rank}] {item.title}")

                    # 爬取微博详情页内容
                    content = await self._fetch_item_content(item)

                    # 使用 LLM 总结
                    if content:
                        from .llm_summary import summarize_weibo_content
                        description = await summarize_weibo_content(item.title, content)
                        if description:
                            item.description = description
                            item.description_source = "weibo_detail"
                            item.description_generated_at = datetime.now()

                            # ✅ 保存到数据库缓存
                            await self._cache_manager.set(
                                title=item.title,
                                description=description,
                                description_source="weibo_detail"
                            )

                            print(f"  ✓ {description[:60]}...")
                        else:
                            # 如果没有生成描述，留空
                            logger.warning(f"未生成描述: {item.title}")
                            item.description = None
                            item.description_source = None
                    else:
                        # 如果没有获取到内容，描述留空
                        logger.warning(f"未获取到微博内容，描述留空: {item.title}")
                        item.description = None
                        item.description_source = None

                except Exception as e:
                    logger.warning(f"  ✗ 失败: {item.title}, 错误: {e}")
                    # 描述留空
                    item.description = None
                    item.description_source = None

                # 避免请求过快
                await asyncio.sleep(1.0)

        # 并发执行
        tasks = [generate_one(item) for item in items_to_process]
        await asyncio.gather(*tasks)

        print(f"{'='*60}")
        logger.info(f"✅ 后台任务完成")

    async def _generate_descriptions_sync(self, items: list) -> None:
        """
        同步生成描述

        Args:
            items: 需要生成描述的热搜列表
        """
        if not items:
            return

        logger.info(f"📝 同步生成描述，共 {len(items)} 条")
        await self._generate_descriptions_async(items)

    async def get_hot_search_summary(self, limit: int = 40) -> str:
        """
        获取热搜摘要（用于 Agent 工具）

        Args:
            limit: 返回热搜数量，默认40条

        Returns:
            格式化的热搜摘要文本
        """
        items = await self.fetch_hot_search(limit)

        if not items:
            return "当前无法获取微博热搜数据"

        lines = ["📊 微博热搜榜：\n"]
        for item in items:
            lines.append(f"  {item}")

        return "\n".join(lines)


# 单例实例
_scraper: WeiboScraper | None = None


def get_scraper(use_selenium: bool | None = None) -> WeiboScraper:
    """
    获取爬虫单例

    Args:
        use_selenium: 是否使用 Selenium，None 则从配置读取
    """
    global _scraper
    if _scraper is None:
        # 从配置读取设置
        try:
            from ..agent.config import get_settings
            settings = get_settings()
            if use_selenium is None:
                use_selenium = settings.weibo_use_selenium
            cookie = settings.weibo_cookie
        except Exception:
            if use_selenium is None:
                use_selenium = False
            cookie = None

        _scraper = WeiboScraper(use_selenium=use_selenium, cookie=cookie)
    return _scraper
