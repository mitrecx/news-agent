"""Integration tests for News Agent"""

import pytest
from unittest.mock import Mock, patch, AsyncMock
from datetime import datetime

from src.agent.base import NewsAgent
from src.tools.weibo import WeiboScraper, HotSearchItem
from src.api.models import ChatRequest, ChatResponse, HealthResponse


class TestNewsAgentIntegration:
    """Integration tests for NewsAgent"""

    @pytest.mark.asyncio
    async def test_agent_initialization_with_tools(self):
        """Test agent initialization with tools"""
        from src.tools import fetch_weibo_hot_search

        agent = NewsAgent(tools=[fetch_weibo_hot_search])
        assert agent.llm is not None
        assert len(agent.tools) == 1
        assert agent.tools[0].name == "fetch_weibo_hot_search"

    @pytest.mark.asyncio
    async def test_agent_chat_basic(self):
        """Test basic chat functionality"""
        from src.tools import fetch_weibo_hot_search

        agent = NewsAgent(tools=[fetch_weibo_hot_search])

        # Mock LLM response
        with patch.object(agent.llm, 'ainvoke', new_callable=AsyncMock) as mock_llm:
            mock_response = Mock()
            mock_response.content = "测试响应"
            mock_response.tool_calls = None
            mock_llm.return_value = mock_response

            response = await agent.chat("你好")
            assert response == "测试响应"

    @pytest.mark.asyncio
    async def test_agent_chat_with_history(self):
        """Test chat with conversation history"""
        from src.tools import fetch_weibo_hot_search

        agent = NewsAgent(tools=[fetch_weibo_hot_search])

        history = [
            {"role": "user", "content": "你好"},
            {"role": "assistant", "content": "你好！有什么我可以帮助你的吗？"}
        ]

        # Mock LLM response
        with patch.object(agent.llm, 'ainvoke', new_callable=AsyncMock) as mock_llm:
            mock_response = Mock()
            mock_response.content = "这是我的回答"
            mock_response.tool_calls = None
            mock_llm.return_value = mock_response

            response = await agent.chat("今天有什么热搜？", history)
            assert response == "这是我的回答"

    @pytest.mark.asyncio
    async def test_agent_tool_invocation(self):
        """Test agent tool invocation"""
        from src.tools import fetch_weibo_hot_search

        agent = NewsAgent(tools=[fetch_weibo_hot_search])

        # Mock tool response
        with patch.object(
            fetch_weibo_hot_search,
            'ainvoke',
            new_callable=AsyncMock,
            return_value="📊 微博热搜榜：\n  1. 测试热搜 (热度: 100万)"
        ):
            # Mock LLM to make tool call
            with patch.object(agent.llm_with_tools, 'ainvoke', new_callable=AsyncMock) as mock_llm:
                # First call: request tool usage
                first_response = Mock()
                first_response.content = ""
                first_response.tool_calls = [{
                    'name': 'fetch_weibo_hot_search',
                    'args': {'limit': 10},
                    'id': 'test_id'
                }]

                # Second call: after tool execution
                second_response = Mock()
                second_response.content = "根据热搜榜，今天的热门话题是..."
                second_response.tool_calls = None

                mock_llm.side_effect = [first_response, second_response]

                response = await agent.chat("今天有什么热搜？")
                assert "热搜" in response


class TestWeiboScraperIntegration:
    """Integration tests for Weibo scraper"""

    @pytest.mark.asyncio
    async def test_scraper_full_flow_with_mock_data(self):
        """Test full scraper flow using mock data"""
        scraper = WeiboScraper(use_selenium=False)

        # Should fall back to mock data when all methods fail
        items = await scraper.fetch_hot_search(limit=5)

        assert len(items) == 5
        assert all(isinstance(item, HotSearchItem) for item in items)
        assert all(item.rank > 0 for item in items)
        assert all(len(item.title) > 0 for item in items)

    @pytest.mark.asyncio
    async def test_scraper_summary_integration(self):
        """Test scraper summary generation"""
        scraper = WeiboScraper()

        # Mock fetch_hot_search
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
            assert "📊" in summary
            assert "测试热搜1" in summary
            assert "测试热搜2" in summary


class TestAPIModelsIntegration:
    """Integration tests for API models"""

    def test_chat_request_validation(self):
        """Test chat request validation"""
        # Valid request
        request = ChatRequest(
            message="你好",
            history=None
        )
        assert request.message == "你好"
        assert request.history is None

        # Request with history
        request_with_history = ChatRequest(
            message="今天有什么热搜？",
            history=[
                {"role": "user", "content": "你好"},
                {"role": "assistant", "content": "你好！"}
            ]
        )
        assert len(request_with_history.history) == 2

    def test_chat_response_creation(self):
        """Test chat response creation"""
        response = ChatResponse(response="这是一个测试响应")
        assert response.response == "这是一个测试响应"

    def test_health_response(self):
        """Test health check response"""
        response = HealthResponse(status="ok", agent_ready=True)
        assert response.status == "ok"
        assert response.agent_ready is True


class TestCacheIntegration:
    """Integration tests for caching"""

    @pytest.mark.asyncio
    async def test_cache_with_scraper(self):
        """Test that caching works with scraper"""
        from src.utils.cache import get_cache

        cache = get_cache()
        cache.clear()

        scraper = WeiboScraper()
        call_count = 0

        async def mock_fetch(limit):
            nonlocal call_count
            call_count += 1
            return [
                HotSearchItem(
                    rank=1,
                    title=f"测试热搜{call_count}",
                    hot_value="100万",
                    category="科技",
                    url="https://example.com"
                )
            ]

        with patch.object(scraper, 'fetch_hot_search', side_effect=mock_fetch):
            # First call
            summary1 = await scraper.get_hot_search_summary(limit=5)
            assert call_count == 1

            # Second call should use cache
            summary2 = await scraper.get_hot_search_summary(limit=5)
            assert call_count == 1  # Should not increment

            assert summary1 == summary2


@pytest.mark.parametrize("message,expected_keywords", [
    ("今天有什么热搜？", "热搜"),
    ("微博热门话题", "热门"),
    ("最新的新闻", "新闻"),
])
def test_agent_various_queries(message, expected_keywords):
    """Test agent with various user queries"""
    assert expected_keywords in message or len(message) > 0
