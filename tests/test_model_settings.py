"""模型配置数据库集成测试；仅使用独立 schema 与临时模型接口。"""

import json
import os
import tempfile
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from threading import Thread
from unittest.mock import patch
from uuid import uuid4

import asyncpg
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from src.agent.config import get_settings


class ModelSettingsTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        from src.settings.service import ModelSettingsService

        settings = get_settings()
        self.conn = await asyncpg.connect(
            host=settings.db_host,
            port=settings.db_port,
            user=settings.db_user,
            password=settings.db_password,
            database=settings.db_name,
        )
        self.schema = f"model_settings_test_{uuid4().hex}"
        await self.conn.execute(f'CREATE SCHEMA "{self.schema}"')
        await self.conn.execute(f'SET search_path TO "{self.schema}"')
        await self.conn.execute("CREATE TABLE users (id INTEGER PRIMARY KEY)")
        await self.conn.execute("INSERT INTO users VALUES (101), (202)")
        await ModelSettingsService.ensure_schema(self.conn)
        self.service = ModelSettingsService

    async def asyncTearDown(self):
        if hasattr(self, "conn"):
            await self.conn.execute("SET search_path TO public")
            await self.conn.execute(f'DROP SCHEMA "{self.schema}" CASCADE')
            await self.conn.close()

    def settings_input(self, **overrides):
        from src.settings.models import ModelSettingsInput

        return ModelSettingsInput(
            **{
                "name": "工作模型",
                "base_url": "https://model.example/v1/",
                "model": "test-chat",
                "api_key": "private-test-key",
                "temperature": 0.4,
                "max_tokens": 2048,
                **overrides,
            }
        )

    async def test_empty_account_has_no_system_fallback(self):
        state = await self.service.read(self.conn, 202)
        self.assertEqual(state.items, [])
        self.assertIsNone(state.active_id)
        with self.assertRaises(ValueError):
            await self.service.resolve(self.conn, 202)

    async def test_first_profile_activates_and_second_profile_does_not_replace_it(self):
        first = await self.service.create(self.conn, 101, self.settings_input())
        second = await self.service.create(
            self.conn, 101, self.settings_input(name="备用模型", model="second-chat")
        )
        state = await self.service.read(self.conn, 101)
        self.assertEqual(len(state.items), 2)
        self.assertEqual(state.active_id, first.id)
        self.assertTrue(first.is_active)
        self.assertFalse(second.is_active)
        self.assertEqual(
            (await self.service.resolve(self.conn, 101)).model, "test-chat"
        )

    async def test_activation_switches_only_the_owners_profile(self):
        first = await self.service.create(self.conn, 101, self.settings_input())
        second = await self.service.create(
            self.conn,
            101,
            self.settings_input(
                name="备用模型", model="second-chat", api_key="second-key"
            ),
        )
        other = await self.service.create(
            self.conn, 202, self.settings_input(model="other-chat")
        )
        await self.service.activate(self.conn, 101, second.id)
        state = await self.service.read(self.conn, 101)
        self.assertEqual(state.active_id, second.id)
        self.assertEqual(sum(item.is_active for item in state.items), 1)
        runtime = await self.service.resolve(self.conn, 101)
        self.assertEqual(runtime.model, "second-chat")
        self.assertEqual(runtime.api_key.get_secret_value(), "second-key")
        self.assertEqual((await self.service.read(self.conn, 202)).active_id, other.id)
        self.assertNotEqual(state.active_id, first.id)

    async def test_profiles_and_secrets_are_isolated_by_user(self):
        profile = await self.service.create(self.conn, 101, self.settings_input())
        self.assertEqual((await self.service.read(self.conn, 202)).items, [])
        for operation in [
            lambda: self.service.activate(self.conn, 202, profile.id),
            lambda: self.service.update(
                self.conn, 202, profile.id, self.settings_input()
            ),
            lambda: self.service.delete(self.conn, 202, profile.id),
            lambda: self.service.prepare(
                self.conn, 202, self.settings_input(api_key=""), profile.id
            ),
        ]:
            with self.assertRaises(LookupError):
                await operation()
        self.assertEqual(
            (await self.service.resolve(self.conn, 101)).model, "test-chat"
        )

    async def test_key_is_encrypted_and_never_in_public_response(self):
        profile = await self.service.create(self.conn, 101, self.settings_input())
        encrypted = await self.conn.fetchval(
            "SELECT api_key_encrypted FROM user_model_profiles WHERE id=$1", profile.id
        )
        self.assertNotIn("private-test-key", encrypted)
        self.assertNotIn(
            "private-test-key",
            (await self.service.read(self.conn, 101)).model_dump_json(),
        )
        self.assertEqual(
            (await self.service.resolve(self.conn, 101)).api_key.get_secret_value(),
            "private-test-key",
        )

    async def test_blank_key_retains_only_the_edited_profiles_key(self):
        first = await self.service.create(self.conn, 101, self.settings_input())
        second = await self.service.create(
            self.conn, 101, self.settings_input(name="备用", api_key="second-key")
        )
        await self.service.update(
            self.conn,
            101,
            second.id,
            self.settings_input(name="已改名", api_key="", model="updated-chat"),
        )
        runtime = await self.service.prepare(
            self.conn,
            101,
            self.settings_input(api_key="", model="updated-chat"),
            second.id,
        )
        self.assertEqual(runtime.api_key.get_secret_value(), "second-key")
        self.assertEqual((await self.service.read(self.conn, 101)).active_id, first.id)

    async def test_new_profile_requires_its_own_key(self):
        await self.service.create(self.conn, 101, self.settings_input())
        with self.assertRaises(ValueError):
            await self.service.create(
                self.conn, 101, self.settings_input(name="新模型", api_key="")
            )

    async def test_endpoint_change_requires_reentering_key(self):
        profile = await self.service.create(self.conn, 101, self.settings_input())
        with self.assertRaises(ValueError):
            await self.service.update(
                self.conn,
                101,
                profile.id,
                self.settings_input(api_key="", base_url="https://other.example/v1"),
            )
        self.assertEqual(
            (await self.service.resolve(self.conn, 101)).base_url,
            "https://model.example/v1",
        )

    async def test_editing_inactive_profile_preserves_activation(self):
        first = await self.service.create(self.conn, 101, self.settings_input())
        second = await self.service.create(
            self.conn, 101, self.settings_input(name="备用", model="second-chat")
        )
        await self.service.update(
            self.conn,
            101,
            second.id,
            self.settings_input(name="改名后的备用", api_key="", model="third-chat"),
        )
        state = await self.service.read(self.conn, 101)
        self.assertEqual(state.active_id, first.id)
        self.assertEqual(
            next(item.name for item in state.items if item.id == second.id),
            "改名后的备用",
        )

    async def test_deleting_active_profile_requires_explicit_switch(self):
        first = await self.service.create(self.conn, 101, self.settings_input())
        second = await self.service.create(
            self.conn, 101, self.settings_input(name="备用")
        )
        with self.assertRaises(ValueError):
            await self.service.delete(self.conn, 101, first.id)
        await self.service.activate(self.conn, 101, second.id)
        await self.service.delete(self.conn, 101, first.id)
        self.assertEqual((await self.service.read(self.conn, 101)).active_id, second.id)

    async def test_deleting_last_profile_leaves_no_hidden_default(self):
        profile = await self.service.create(self.conn, 101, self.settings_input())
        await self.service.delete(self.conn, 101, profile.id)
        await self.service.ensure_schema(self.conn)
        self.assertEqual((await self.service.read(self.conn, 101)).items, [])
        with self.assertRaises(ValueError):
            await self.service.resolve(self.conn, 101)

    async def test_probe_does_not_save_or_activate_draft(self):
        profile = await self.service.create(self.conn, 101, self.settings_input())
        draft = await self.service.prepare(
            self.conn, 101, self.settings_input(model="draft-chat", api_key="draft-key")
        )
        self.assertEqual(draft.model, "draft-chat")
        self.assertEqual(
            (await self.service.read(self.conn, 101)).active_id, profile.id
        )
        self.assertEqual(
            (await self.service.resolve(self.conn, 101)).model, "test-chat"
        )

    async def test_legacy_single_profile_migrates_once_without_resurrection(self):
        await self.conn.execute(
            """CREATE TABLE user_model_settings(user_id INTEGER PRIMARY KEY REFERENCES users(id),base_url TEXT,model TEXT,api_key_encrypted TEXT,temperature DOUBLE PRECISION,max_tokens INTEGER)"""
        )
        encrypted = self.service._cipher().encrypt(b"legacy-key").decode()
        await self.conn.execute(
            "INSERT INTO user_model_settings VALUES(101,'https://legacy.example/v1','legacy-chat',$1,0.5,2048)",
            encrypted,
        )
        await self.service.ensure_schema(self.conn)
        state = await self.service.read(self.conn, 101)
        self.assertEqual(len(state.items), 1)
        self.assertEqual(
            (await self.service.resolve(self.conn, 101)).api_key.get_secret_value(),
            "legacy-key",
        )
        await self.service.ensure_schema(self.conn)
        self.assertEqual(len((await self.service.read(self.conn, 101)).items), 1)
        await self.service.delete(self.conn, 101, state.active_id)
        await self.service.ensure_schema(self.conn)
        self.assertEqual((await self.service.read(self.conn, 101)).items, [])

    async def test_invalid_profile_values_are_rejected(self):
        from pydantic import ValidationError

        for values in [
            {"name": "  "},
            {"base_url": "file:///etc/passwd"},
            {"base_url": "https://user:pass@example.com/v1"},
            {"base_url": "https://example.com/v1?token=x"},
            {"model": " "},
            {"temperature": 3},
            {"max_tokens": 0},
        ]:
            with self.subTest(values=values), self.assertRaises(ValidationError):
                self.settings_input(**values)

    async def test_profile_routes_require_login(self):
        from src.auth.database import get_db
        from src.settings.router import router

        app = FastAPI()
        app.include_router(router)

        async def connection():
            yield self.conn

        app.dependency_overrides[get_db] = connection
        profile_id = str(uuid4())
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            for method, path in [
                ("GET", "/api/settings/models"),
                ("POST", "/api/settings/models"),
                ("PUT", f"/api/settings/models/{profile_id}"),
                ("DELETE", f"/api/settings/models/{profile_id}"),
                ("POST", f"/api/settings/models/{profile_id}/activate"),
                ("POST", f"/api/settings/models/{profile_id}/test"),
                ("POST", "/api/settings/models/test"),
                ("POST", "/api/settings/models/available"),
            ]:
                response = await client.request(method, path, json={})
                self.assertEqual(response.status_code, 401, path)

    async def test_public_profile_api_never_echoes_keys(self):
        from src.auth.database import get_db
        from src.auth.models import User
        from src.auth.router import get_current_user
        from src.settings.router import router

        app = FastAPI()
        app.include_router(router)

        async def connection():
            yield self.conn

        app.dependency_overrides[get_db] = connection
        app.dependency_overrides[get_current_user] = lambda: User(
            id=101, username="owner"
        )
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            saved = await client.post(
                "/api/settings/models",
                json={
                    "name": "工作模型",
                    "base_url": "https://model.example/v1",
                    "model": "test-chat",
                    "api_key": "never-echo-this",
                },
            )
            self.assertEqual(saved.status_code, 201)
            self.assertTrue(saved.json()["has_api_key"])
            self.assertNotIn("never-echo-this", saved.text)
            listing = await client.get("/api/settings/models")
            self.assertEqual(len(listing.json()["items"]), 1)
            self.assertNotIn("api_key", listing.json()["items"][0])
            self.assertNotIn("api_key_encrypted", listing.text)

    async def test_ai_endpoints_reject_accounts_without_enabled_model(self):
        from contextlib import asynccontextmanager

        from src.api import server
        from src.auth.models import User
        from src.auth.router import get_current_user

        connection = self.conn

        class Pool:
            @asynccontextmanager
            async def acquire(self):
                yield connection

        original_overrides = server.app.dependency_overrides.copy()
        server.app.dependency_overrides[get_current_user] = lambda: User(
            id=202, username="unconfigured"
        )
        try:
            with (
                patch.object(server.db, "pool", Pool()),
                patch.object(server, "NewsAgent") as agent,
            ):
                async with AsyncClient(
                    transport=ASGITransport(app=server.app), base_url="http://test"
                ) as client:
                    for path, payload in [
                        ("/api/chat", {"message": "hello"}),
                        ("/api/chat/stream", {"message": "hello"}),
                        ("/api/weibo/cache/fetch-missing", {"limit": 1}),
                    ]:
                        response = await client.post(path, json=payload)
                        self.assertEqual(response.status_code, 400, path)
                        self.assertIn("添加并启用", response.json()["detail"])
                agent.assert_not_called()
        finally:
            server.app.dependency_overrides = original_overrides

    async def test_create_llm_requires_explicit_runtime(self):
        from src.agent.base import create_llm

        with self.assertRaises(ValueError):
            create_llm()

    async def test_chat_and_summary_follow_active_model_switch(self):
        from src.agent.base import NewsAgent
        from src.tools.llm_summary import summarize_weibo_content

        received = []

        class Provider(BaseHTTPRequestHandler):
            def log_message(self, *args):
                pass

            def do_POST(self):
                body = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
                received.append((body["model"], self.headers.get("Authorization")))
                content = "已使用个人模型生成结果。"
                response = json.dumps(
                    {
                        "id": "test-completion",
                        "object": "chat.completion",
                        "created": 0,
                        "model": body["model"],
                        "choices": [
                            {
                                "index": 0,
                                "message": {"role": "assistant", "content": content},
                                "finish_reason": "stop",
                            }
                        ],
                    }
                ).encode()
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(response)))
                self.end_headers()
                self.wfile.write(response)

        server = ThreadingHTTPServer(("127.0.0.1", 0), Provider)
        thread = Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            await self.service.create(
                self.conn,
                101,
                self.settings_input(
                    base_url=f"http://127.0.0.1:{server.server_port}/v1"
                ),
            )
            runtime = await self.service.resolve(self.conn, 101)
            reply = await NewsAgent(model_config=runtime).chat("你好")
            summary = await summarize_weibo_content(
                "测试热点",
                "用于测试的真实格式正文，包含足够内容供模型生成摘要。",
                runtime,
            )
            self.assertEqual(reply, "已使用个人模型生成结果。")
            self.assertEqual(summary, "Agent总结: 已使用个人模型生成结果。")
            second = await self.service.create(
                self.conn,
                101,
                self.settings_input(
                    name="备用",
                    model="second-chat",
                    api_key="second-key",
                    base_url=runtime.base_url,
                ),
            )
            await self.service.activate(self.conn, 101, second.id)
            switched = await self.service.resolve(self.conn, 101)
            await NewsAgent(model_config=switched).chat("切换后对话")
            await summarize_weibo_content(
                "切换后热点", "用于验证切换后摘要调用的微博正文。", switched
            )
            self.assertEqual(
                received,
                [
                    ("test-chat", "Bearer private-test-key"),
                    ("test-chat", "Bearer private-test-key"),
                    ("second-chat", "Bearer second-key"),
                    ("second-chat", "Bearer second-key"),
                ],
            )
        finally:
            server.shutdown()
            server.server_close()
            thread.join()

    async def test_chat_failure_never_returns_credentials(self):
        from langchain_core.runnables import RunnableLambda
        from langchain_core.tools import tool

        from src.agent.base import NewsAgent

        @tool
        def harmless_lookup(query: str) -> str:
            """Return a local test value."""
            return "test"

        async def rejected(messages):
            raise RuntimeError(
                "upstream rejected private-test-key at https://private.example"
            )

        await self.service.create(self.conn, 101, self.settings_input())
        agent = NewsAgent(
            tools=[harmless_lookup],
            model_config=await self.service.resolve(self.conn, 101),
        )
        agent.llm_with_tools = RunnableLambda(rejected)
        reply = "".join([part async for part in agent.chat_stream("hello")])
        self.assertNotIn("private-test-key", reply)
        self.assertNotIn("private.example", reply)
        self.assertIn("模型", reply)


class LiveCookieTests(unittest.TestCase):
    def test_saved_cookie_overrides_process_startup_value_immediately(self):
        from src.agent.config import get_settings

        get_settings()
        original = Path.cwd()
        with (
            tempfile.TemporaryDirectory() as directory,
            patch.dict(os.environ, {"WEIBO_COOKIE": "SUB=startup"}),
        ):
            try:
                os.chdir(directory)
                Path(".env").write_text('WEIBO_COOKIE="SUB=first; SUBP=one"\n')
                self.assertEqual(get_settings().weibo_cookie, "SUB=first; SUBP=one")
                Path(".env").write_text('WEIBO_COOKIE="SUB=changed; SUBP=two"\n')
                self.assertEqual(get_settings().weibo_cookie, "SUB=changed; SUBP=two")
            finally:
                os.chdir(original)
