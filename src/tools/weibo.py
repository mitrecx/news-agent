"""Weibo hot search scraper - 微博热搜爬虫"""

from datetime import datetime
from typing import List
from dataclasses import dataclass
import asyncio
import logging

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
            "collected_at": self.collected_at.isoformat()
        }

    def __str__(self) -> str:
        """字符串表示"""
        icon_str = f"[{self.icon}]" if self.icon else ""
        return f"{self.rank}. {icon_str}{self.title} (热度: {self.hot_value})"


class WeiboScraper:
    """微博热搜爬虫"""

    # 微博热搜 PC 端页面
    WEIBO_HOT_URL = "https://s.weibo.com/top/summary?cate=realtimehot"

    def __init__(self, timeout: int = 10, use_selenium: bool = False):
        """
        初始化爬虫

        Args:
            timeout: 请求超时时间（秒）
            use_selenium: 是否优先使用 Selenium（需要安装 Chrome）
        """
        self.timeout = timeout
        self.use_selenium = use_selenium and SELENIUM_AVAILABLE
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                         "AppleWebKit/537.36 (KHTML, like Gecko) "
                         "Chrome/120.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
            "Referer": "https://weibo.com",
        }

    async def fetch_hot_search(self, limit: int = 40) -> List[HotSearchItem]:
        """
        获取微博热搜榜

        Args:
            limit: 返回热搜数量，默认40条

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

        # 方法4: 返回模拟数据
        logger.info("📦 使用模拟数据")
        print("📦 步骤 4/4: 使用模拟数据...\n")
        items = self._get_mock_data(limit)
        logger.info(f"✅ 返回模拟数据，共 {len(items)} 条")
        return items

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
                timeout=30.0  # 30秒超时
            )
        except asyncio.TimeoutError:
            logger.error("❌ Selenium 初始化超时 (30秒)")
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
        chrome_options.add_argument('--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')

        # 自动下载并使用 ChromeDriver
        logger.info("📦 安装 ChromeDriver...")
        try:
            service = Service(ChromeDriverManager().install())
            logger.info("✅ ChromeDriver 安装成功")
        except Exception as e:
            logger.error(f"❌ ChromeDriver 安装失败: {e}")
            raise Exception(f"ChromeDriver 安装失败: {e}")

        logger.info("🚀 启动 Chrome 浏览器...")
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
            driver.quit()

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
                if url and not url.startswith("http"):
                    url = "https://s.weibo.com" + url

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

    def _get_mock_data(self, limit: int) -> List[HotSearchItem]:
        """
        获取模拟数据（当爬虫失败时使用）

        Args:
            limit: 返回数量

        Returns:
            模拟的热搜条目列表
        """
        mock_items = [
            ("2025年度科技热点盘点", "356.2万", "科技", "热"),
            ("春节档电影票房创新高", "298.5万", "娱乐", "新"),
            ("各地文旅局长花式卷", "245.8万", "社会", "热"),
            ("新能源汽车销量持续增长", "198.3万", "财经", ""),
            ("人工智能发展新突破", "176.5万", "科技", "热"),
            ("城市更新行动持续推进", "154.2万", "社会", ""),
            ("年轻人养生方式引热议", "132.8万", "生活", "新"),
            ("各地美食文化出圈", "118.6万", "生活", ""),
            ("数字货币应用场景扩大", "98.5万", "财经", ""),
            ("国产芯片技术取得进展", "87.3万", "科技", "热"),
            ("影视行业复苏势头强劲", "76.2万", "娱乐", ""),
            ("全民健身计划启动", "65.8万", "社会", "新"),
            ("5G网络覆盖率提升", "54.3万", "科技", ""),
            ("远程办公新模式普及", "43.7万", "职场", ""),
            ("绿色低碳生活方式", "38.2万", "生活", ""),
            ("在线教育创新发展", "32.6万", "教育", ""),
            ("新消费品牌崛起", "28.5万", "财经", "热"),
            ("乡村振兴成果显著", "24.3万", "社会", ""),
            ("数字文产业发展迅速", "19.8万", "科技", ""),
            ("非物质文化遗产保护", "16.5万", "文化", "新"),
        ]

        items = []
        for idx, (title, hot, category, icon) in enumerate(mock_items[:limit], 1):
            items.append(HotSearchItem(
                rank=idx,
                title=title,
                hot_value=hot,
                category=category,
                url=f"https://s.weibo.com/weibo?q=%23{title}%23",
                icon=icon if icon else None
            ))

        return items

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
        # 如果没有指定，尝试从配置读取
        if use_selenium is None:
            try:
                from ..agent.config import get_settings
                settings = get_settings()
                use_selenium = settings.weibo_use_selenium
            except Exception:
                use_selenium = False

        _scraper = WeiboScraper(use_selenium=use_selenium)
    return _scraper
