"""Test configuration and fixtures"""

import pytest
import asyncio
import sys
import os

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))


@pytest.fixture
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def mock_settings():
    """Mock settings for testing"""
    from unittest.mock import Mock
    settings = Mock()
    settings.deepseek_api_key = "test_api_key"
    settings.deepseek_base_url = "https://api.test.com/v1"
    settings.host = "localhost"
    settings.port = 8000
    settings.agent_temperature = 0.7
    settings.agent_max_tokens = 2000
    settings.agent_model = "test-model"
    settings.weibo_use_selenium = False
    settings.weibo_scraper_timeout = 10
    return settings
