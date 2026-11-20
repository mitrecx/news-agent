"""单条摘要只更新所选资讯；数据库与上游均使用隔离的测试环境。"""

import asyncio
import json
import unittest
from datetime import datetime, timedelta
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from threading import Thread
from unittest.mock import patch
from uuid import uuid4

import asyncpg
from httpx import ASGITransport, AsyncClient

from src.agent.config import get_settings
from src.api import server
from src.auth.models import User
from src.auth.router import get_current_user
from src.settings.models import ModelSettingsInput
from src.settings.service import ModelSettingsService
from src.tools.weibo_cache import WeiboHotSearchCache


class HotSearchSummaryTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        settings = get_settings()
        database = {
            "host": settings.db_host,
            "port": settings.db_port,
            "user": settings.db_user,
            "password": settings.db_password,
            "database": settings.db_name,
        }
        self.schema = f"hotsearch_summary_test_{uuid4().hex}"
        self.admin = await asyncpg.connect(**database)
        await self.admin.execute(f'CREATE SCHEMA "{self.schema}"')
        self.pool = await asyncpg.create_pool(
            **database,
            min_size=1,
            max_size=3,
            server_settings={"search_path": self.schema},
        )
        async with self.pool.acquire() as conn:
            await conn.execute("CREATE TABLE users (id INTEGER PRIMARY KEY)")
            await conn.execute("INSERT INTO users VALUES (101), (202)")
            await ModelSettingsService.ensure_schema(conn)
            await conn.execute("""CREATE TABLE weibo_hot_search_cache (
                title_hash VARCHAR(64) PRIMARY KEY, title TEXT NOT NULL, url TEXT,
                description TEXT, description_source TEXT,
                created_at TIMESTAMP NOT NULL, updated_at TIMESTAMP NOT NULL,
                expires_at TIMESTAMP NOT NULL
            )""")

        self.requests = []
        self.model_requests = []
        requests = self.requests
        model_requests = self.model_requests

        class Provider(BaseHTTPRequestHandler):
            def log_message(self, *args):
                pass

            def do_GET(self):
                requests.append(("GET", self.path))
                body = (
                    b"<html><body>no accessible content</body></html>"
                    if self.path == "/blocked"
                    else "<html><p>这是所选话题对应的微博正文，包含时间、人物和事件经过，供摘要整理。</p></html>".encode()
                )
                self.reply(body, "text/html; charset=utf-8")

            def do_POST(self):
                requests.append(("POST", self.path))
                body = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
                model_requests.append((body, self.headers.get("Authorization")))
                self.reply(
                    json.dumps(
                        {
                            "id": "single-story-test",
                            "object": "chat.completion",
                            "created": 0,
                            "model": body["model"],
                            "choices": [
                                {
                                    "index": 0,
                                    "finish_reason": "stop",
                                    "message": {
                                        "role": "assistant",
                                        "content": "已根据当前话题生成的内容摘要。",
                                    },
                                }
                            ],
                        }
                    ).encode(),
                    "application/json",
                )

            def reply(self, body, content_type):
                self.send_response(200)
                self.send_header("Content-Type", content_type)
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)

        self.provider = ThreadingHTTPServer(("127.0.0.1", 0), Provider)
        self.provider_thread = Thread(target=self.provider.serve_forever, daemon=True)
        self.provider_thread.start()
        self.origin = f"http://127.0.0.1:{self.provider.server_port}"
        async with self.pool.acquire() as conn:
            await ModelSettingsService.create(
                conn,
                101,
                ModelSettingsInput(
                    name="测试用户所选模型",
                    base_url=self.origin + "/v1",
                    model="selected-story-model",
                    api_key="test-only-model-key",
                ),
            )
        self.old_hash = await self.add_story("最早待处理的其他资讯", "/older", age=3)
        self.selected_hash = await self.add_story(
            "用户当前选中的资讯", "/selected", age=2
        )
        self.next_hash = await self.add_story("另一条待处理资讯", "/next", age=1)
        self.settings_patch = patch(
            "src.agent.config.get_settings",
            return_value=settings.model_copy(
                update={
                    "weibo_cookie": "SUB=local-test",
                    "use_selenium_for_descriptions": False,
                }
            ),
        )
        self.settings_patch.start()
        self.pool_patch = patch.object(server.db, "pool", self.pool)
        self.pool_patch.start()
        self.original_overrides = server.app.dependency_overrides.copy()
        server.app.dependency_overrides[get_current_user] = lambda: User(
            id=101, username="owner"
        )
        self.client = AsyncClient(
            transport=ASGITransport(app=server.app), base_url="http://test"
        )

    async def asyncTearDown(self):
        await self.client.aclose()
        server.app.dependency_overrides = self.original_overrides
        self.pool_patch.stop()
        self.settings_patch.stop()
        await asyncio.to_thread(self.provider.shutdown)
        self.provider.server_close()
        self.provider_thread.join()
        await self.pool.close()
        await self.admin.execute(f'DROP SCHEMA "{self.schema}" CASCADE')
        await self.admin.close()

    async def add_story(self, title, path, age=0):
        title_hash = WeiboHotSearchCache.hash_title(title)
        created_at = datetime.now() - timedelta(minutes=age)
        async with self.pool.acquire() as conn:
            await conn.execute(
                """INSERT INTO weibo_hot_search_cache
                (title_hash,title,url,created_at,updated_at,expires_at)
                VALUES($1,$2,$3,$4,$4,$5)""",
                title_hash,
                title,
                self.origin + path if path else None,
                created_at,
                datetime.now() + timedelta(days=1),
            )
        return title_hash

    async def generate_selected(self):
        return await self.client.post(f"/api/weibo/cache/{self.selected_hash}/summary")

    async def descriptions(self):
        async with self.pool.acquire() as conn:
            return dict(
                await conn.fetch(
                    "SELECT title_hash,description FROM weibo_hot_search_cache"
                )
            )

    async def test_single_summary_fetches_and_updates_only_selected_story(self):
        response = await self.generate_selected()
        self.assertEqual(response.status_code, 200, response.text)
        payload = response.json()
        self.assertEqual(payload["status"], "generated")
        self.assertEqual(payload["item"]["title_hash"], self.selected_hash)
        self.assertEqual(payload["item"]["title"], "用户当前选中的资讯")
        self.assertEqual(
            payload["item"]["description"], "Agent总结: 已根据当前话题生成的内容摘要。"
        )
        self.assertEqual(
            self.requests, [("GET", "/selected"), ("POST", "/v1/chat/completions")]
        )
        body, authorization = self.model_requests[0]
        self.assertEqual(body["model"], "selected-story-model")
        self.assertEqual(authorization, "Bearer test-only-model-key")
        self.assertIn("用户当前选中的资讯", body["messages"][-1]["content"])
        descriptions = await self.descriptions()
        self.assertIsNone(descriptions[self.old_hash])
        self.assertIsNone(descriptions[self.next_hash])
        self.assertEqual(
            descriptions[self.selected_hash], payload["item"]["description"]
        )

    async def test_retry_reuses_existing_summary_without_another_fetch(self):
        first = await self.generate_selected()
        self.assertEqual(first.status_code, 200)
        second = await self.generate_selected()
        self.assertEqual(second.status_code, 200)
        self.assertEqual(second.json()["status"], "cached")
        self.assertEqual(second.json()["item"], first.json()["item"])
        self.assertEqual(len(self.requests), 2)

    async def test_unknown_or_expired_story_is_not_fetched(self):
        response = await self.client.post(f"/api/weibo/cache/{'0' * 64}/summary")
        self.assertEqual(response.status_code, 404)
        async with self.pool.acquire() as conn:
            await conn.execute(
                "UPDATE weibo_hot_search_cache SET expires_at=NOW()-INTERVAL '1 day' WHERE title_hash=$1",
                self.selected_hash,
            )
        response = await self.generate_selected()
        self.assertEqual(response.status_code, 404)
        self.assertEqual(self.requests, [])

    async def test_missing_url_does_not_fetch_a_different_story(self):
        missing_hash = await self.add_story("缺少链接的资讯", None)
        response = await self.client.post(f"/api/weibo/cache/{missing_hash}/summary")
        self.assertEqual(response.status_code, 400)
        self.assertEqual(self.requests, [])
        self.assertTrue(
            all(value is None for value in (await self.descriptions()).values())
        )

    async def test_fetch_failure_preserves_all_other_stories(self):
        async with self.pool.acquire() as conn:
            await conn.execute(
                "UPDATE weibo_hot_search_cache SET url=$1 WHERE title_hash=$2",
                self.origin + "/blocked",
                self.selected_hash,
            )
        response = await self.generate_selected()
        self.assertEqual(response.status_code, 502)
        self.assertNotIn("test-only-model-key", response.text)
        self.assertEqual(self.requests, [("GET", "/blocked")])
        self.assertTrue(
            all(value is None for value in (await self.descriptions()).values())
        )

    async def test_unconfigured_account_must_choose_a_model(self):
        server.app.dependency_overrides[get_current_user] = lambda: User(
            id=202, username="empty"
        )
        response = await self.generate_selected()
        self.assertEqual(response.status_code, 400)
        self.assertIn("添加并启用", response.json()["detail"])
        self.assertEqual(self.requests, [])

    async def test_single_summary_requires_login(self):
        server.app.dependency_overrides.pop(get_current_user)
        response = await self.generate_selected()
        self.assertEqual(response.status_code, 401)
        self.assertEqual(self.requests, [])

    async def test_batch_generation_still_processes_oldest_missing_story(self):
        response = await self.client.post(
            "/api/weibo/cache/fetch-missing", params={"limit": 1}
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["success_count"], 1)
        self.assertEqual(response.json()["items"][0]["title"], "最早待处理的其他资讯")
        descriptions = await self.descriptions()
        self.assertTrue(descriptions[self.old_hash])
        self.assertIsNone(descriptions[self.selected_hash])
        self.assertIsNone(descriptions[self.next_hash])
