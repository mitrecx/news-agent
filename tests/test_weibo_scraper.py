"""Tests for Weibo scraper"""

import pytest
from datetime import datetime
from unittest.mock import Mock, patch, AsyncMock

from src.tools.weibo import WeiboScraper, HotSearchItem, HotCategory, get_scraper


class TestHotSearchItem:
    """Test HotSearchItem dataclass"""

    def test_hot_search_item_creation(self):
        """Test creating a HotSearchItem"""
        item = HotSearchItem(
            rank=1,
            title="测试热搜",
            hot_value="100万",
            category="科技",
            url="https://example.com"
        )

        assert item.rank == 1
        assert item.title == "测试热搜"
        assert item.hot_value == "100万"
        assert item.category == "科技"
        assert item.url == "https://example.com"
        assert item.icon is None
        assert isinstance(item.collected_at, datetime)

    def test_hot_search_item_with_icon(self):
        """Test HotSearchItem with icon"""
        item = HotSearchItem(
            rank=1,
            title="测试热搜",
            hot_value="100万",
            category="科技",
            url="https://example.com",
            icon="热"
        )

        assert item.icon == "热"

    def test_hot_search_item_to_dict(self):
        """Test converting HotSearchItem to dictionary"""
        item = HotSearchItem(
            rank=1,
            title="测试热搜",
            hot_value="100万",
            category="科技",
            url="https://example.com"
        )

        result = item.to_dict()

        assert isinstance(result, dict)
        assert result["rank"] == 1
        assert result["title"] == "测试热搜"
        assert result["hot_value"] == "100万"
        assert result["category"] == "科技"
        assert result["url"] == "https://example.com"
        assert result["icon"] is None
        assert "collected_at" in result

    def test_hot_search_item_str_representation(self):
        """Test string representation of HotSearchItem"""
        item = HotSearchItem(
            rank=1,
            title="测试热搜",
            hot_value="100万",
            category="科技",
            url="https://example.com"
        )

        str_repr = str(item)
        assert "1." in str_repr
        assert "测试热搜" in str_repr
        assert "100万" in str_repr

    def test_hot_search_item_str_with_icon(self):
        """Test string representation with icon"""
        item = HotSearchItem(
            rank=1,
            title="测试热搜",
            hot_value="100万",
            category="科技",
            url="https://example.com",
            icon="热"
        )

        str_repr = str(item)
        assert "[热]" in str_repr


class TestWeiboScraper:
    """Test WeiboScraper functionality"""

    def test_scraper_initialization(self):
        """Test scraper initialization"""
        scraper = WeiboScraper(timeout=10, use_selenium=False)
        assert scraper.timeout == 10
        assert scraper.use_selenium is False
        assert len(scraper.headers) > 0

    def test_scraper_headers(self):
        """Test that scraper has proper headers"""
        scraper = WeiboScraper()
        assert "User-Agent" in scraper.headers
        assert "Accept" in scraper.headers
        assert "Referer" in scraper.headers

    @pytest.mark.asyncio
    async def test_get_mock_data(self):
        """Test mock data generation"""
        scraper = WeiboScraper()
        mock_data = await scraper.fetch_hot_search(limit=5)

        # When all scraping methods fail, should return mock data
        assert len(mock_data) == 5
        assert all(isinstance(item, HotSearchItem) for item in mock_data)

    @pytest.mark.asyncio
    async def test_get_hot_search_summary(self):
        """Test getting hot search summary"""
        scraper = WeiboScraper()

        # Mock the fetch_hot_search to return test data
        test_items = [
            HotSearchItem(
                rank=1,
                title="测试热搜1",
                hot_value="100万",
                category="科技",
                url="https://example.com/1"
            ),
            HotSearchItem(
                rank=2,
                title="测试热搜2",
                hot_value="200万",
                category="娱乐",
                url="https://example.com/2"
            ),
        ]

        with patch.object(scraper, 'fetch_hot_search', return_value=test_items):
            summary = await scraper.get_hot_search_summary(limit=2)

            assert isinstance(summary, str)
            assert "微博热搜榜" in summary
            assert "测试热搜1" in summary
            assert "测试热搜2" in summary

    @pytest.mark.asyncio
    async def test_get_hot_search_summary_empty(self):
        """Test summary when no data available"""
        scraper = WeiboScraper()

        with patch.object(scraper, 'fetch_hot_search', return_value=[]):
            summary = await scraper.get_hot_search_summary()
            assert "无法获取" in summary


class TestHotCategory:
    """Test HotCategory enum"""

    def test_hot_category_values(self):
        """Test HotCategory enum values"""
        assert HotCategory.ALL == "全部"
        assert HotCategory.ENT == "娱乐"
        assert HotCategory.SOCIAL == "社会"
        assert HotCategory.TECH == "科技"
        assert HotCategory.FINANCE == "财经"


class TestGetScraper:
    """Test scraper singleton function"""

    def test_get_scraper_singleton(self):
        """Test that get_scraper returns singleton"""
        scraper1 = get_scraper(use_selenium=False)
        scraper2 = get_scraper(use_selenium=False)
        assert scraper1 is scraper2

    @patch('src.tools.weibo.get_settings')
    def test_get_scraper_from_config(self, mock_settings):
        """Test get_scraper reads from config"""
        mock_config = Mock()
        mock_config.weibo_use_selenium = True
        mock_settings.return_value = mock_config

        # Reset the singleton
        import src.tools.weibo
        src.tools.weibo._scraper = None

        scraper = get_scraper()
        assert scraper.use_selenium is True
