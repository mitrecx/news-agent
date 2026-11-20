"""按用户保存多个模型，运行时只使用明确启用的配置。"""

import base64
import hashlib
from uuid import uuid4

from cryptography.fernet import Fernet, InvalidToken

from ..agent.config import get_settings
from .models import (
    ModelRuntime,
    ModelSettingsCollection,
    ModelSettingsPublic,
)


class ModelSettingsService:
    @classmethod
    async def ensure_schema(cls, conn):
        async with conn.transaction():
            await conn.execute("SELECT pg_advisory_xact_lock(748210635)")
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS user_model_profiles (
                    id UUID PRIMARY KEY,
                    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                    name VARCHAR(80) NOT NULL,
                    base_url TEXT NOT NULL,
                    model VARCHAR(200) NOT NULL,
                    api_key_encrypted TEXT NOT NULL,
                    temperature DOUBLE PRECISION NOT NULL DEFAULT 0.7,
                    max_tokens INTEGER NOT NULL DEFAULT 2000,
                    is_active BOOLEAN NOT NULL DEFAULT FALSE,
                    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
                )
            """)
            await conn.execute("""CREATE UNIQUE INDEX IF NOT EXISTS user_model_profiles_one_active
                ON user_model_profiles(user_id) WHERE is_active""")
            await conn.execute("""CREATE INDEX IF NOT EXISTS user_model_profiles_owner
                ON user_model_profiles(user_id, created_at)""")
            # 旧单配置只迁移一次。保留原表备查，删除新配置后也不会复活旧值。
            if await conn.fetchval("SELECT to_regclass('user_model_settings')"):
                await conn.execute(
                    "ALTER TABLE user_model_settings ADD COLUMN IF NOT EXISTS migrated_at TIMESTAMPTZ"
                )
                rows = await conn.fetch(
                    "SELECT * FROM user_model_settings WHERE migrated_at IS NULL"
                )
                for row in rows:
                    has_profiles = await conn.fetchval(
                        "SELECT EXISTS(SELECT 1 FROM user_model_profiles WHERE user_id=$1)",
                        row["user_id"],
                    )
                    if not has_profiles:
                        await conn.execute(
                            """INSERT INTO user_model_profiles
                            (id,user_id,name,base_url,model,api_key_encrypted,temperature,max_tokens,is_active)
                            VALUES($1,$2,$3,$4,$5,$6,$7,$8,TRUE)""",
                            uuid4(),
                            row["user_id"],
                            row["model"][:80],
                            row["base_url"],
                            row["model"],
                            row["api_key_encrypted"],
                            row["temperature"],
                            row["max_tokens"],
                        )
                    await conn.execute(
                        "UPDATE user_model_settings SET migrated_at=NOW() WHERE user_id=$1",
                        row["user_id"],
                    )

    @staticmethod
    def _cipher():
        material = f"news-agent:model-settings:{get_settings().jwt_secret}".encode()
        return Fernet(base64.urlsafe_b64encode(hashlib.sha256(material).digest()))

    @staticmethod
    def _public(row):
        return ModelSettingsPublic(
            id=row["id"],
            name=row["name"],
            base_url=row["base_url"],
            model=row["model"],
            has_api_key=bool(row["api_key_encrypted"]),
            temperature=row["temperature"],
            max_tokens=row["max_tokens"],
            is_active=row["is_active"],
        )

    @classmethod
    def _runtime_from_row(cls, row):
        try:
            key = cls._cipher().decrypt(row["api_key_encrypted"].encode()).decode()
        except InvalidToken:
            raise ValueError("密钥无法解密，请编辑此模型并重新填写 API Key") from None
        return ModelRuntime(
            base_url=row["base_url"],
            model=row["model"],
            api_key=key,
            temperature=row["temperature"],
            max_tokens=row["max_tokens"],
        )

    @staticmethod
    async def _owned(conn, user_id, profile_id):
        row = await conn.fetchrow(
            "SELECT * FROM user_model_profiles WHERE id=$1 AND user_id=$2",
            profile_id,
            user_id,
        )
        if row is None:
            raise LookupError("模型配置不存在")
        return row

    @classmethod
    async def read(cls, conn, user_id):
        rows = await conn.fetch(
            "SELECT * FROM user_model_profiles WHERE user_id=$1 ORDER BY created_at,id",
            user_id,
        )
        items = [cls._public(row) for row in rows]
        return ModelSettingsCollection(
            items=items,
            active_id=next((item.id for item in items if item.is_active), None),
        )

    @classmethod
    async def resolve(cls, conn, user_id):
        row = await conn.fetchrow(
            "SELECT * FROM user_model_profiles WHERE user_id=$1 AND is_active", user_id
        )
        if row is None:
            raise ValueError("请先在设置中添加并启用一个模型")
        return cls._runtime_from_row(row)

    @classmethod
    async def resolve_profile(cls, conn, user_id, profile_id):
        return cls._runtime_from_row(await cls._owned(conn, user_id, profile_id))

    @classmethod
    async def prepare(cls, conn, user_id, data, profile_id=None):
        row = await cls._owned(conn, user_id, profile_id) if profile_id else None
        key = data.api_key.get_secret_value().strip() if data.api_key else ""
        if not key:
            if row is None:
                raise ValueError("添加模型时，请填写 API Key")
            if row["base_url"] != data.base_url:
                raise ValueError("修改 API 地址时，请同时填写该地址对应的 API Key")
            key = cls._runtime_from_row(row).api_key.get_secret_value()
        return ModelRuntime(
            base_url=data.base_url,
            model=data.model,
            api_key=key,
            temperature=data.temperature,
            max_tokens=data.max_tokens,
        )

    @classmethod
    async def create(cls, conn, user_id, data):
        runtime = await cls.prepare(conn, user_id, data)
        encrypted = (
            cls._cipher().encrypt(runtime.api_key.get_secret_value().encode()).decode()
        )
        async with conn.transaction():
            await conn.fetchval("SELECT id FROM users WHERE id=$1 FOR UPDATE", user_id)
            has_profiles = await conn.fetchval(
                "SELECT EXISTS(SELECT 1 FROM user_model_profiles WHERE user_id=$1)",
                user_id,
            )
            row = await conn.fetchrow(
                """INSERT INTO user_model_profiles
                (id,user_id,name,base_url,model,api_key_encrypted,temperature,max_tokens,is_active)
                VALUES($1,$2,$3,$4,$5,$6,$7,$8,$9) RETURNING *""",
                uuid4(),
                user_id,
                data.name,
                runtime.base_url,
                runtime.model,
                encrypted,
                runtime.temperature,
                runtime.max_tokens,
                not has_profiles,
            )
        return cls._public(row)

    @classmethod
    async def update(cls, conn, user_id, profile_id, data):
        async with conn.transaction():
            await conn.fetchval("SELECT id FROM users WHERE id=$1 FOR UPDATE", user_id)
            runtime = await cls.prepare(conn, user_id, data, profile_id)
            encrypted = (
                cls._cipher()
                .encrypt(runtime.api_key.get_secret_value().encode())
                .decode()
            )
            row = await conn.fetchrow(
                """UPDATE user_model_profiles SET name=$3,base_url=$4,model=$5,
                api_key_encrypted=$6,temperature=$7,max_tokens=$8,updated_at=NOW()
                WHERE id=$1 AND user_id=$2 RETURNING *""",
                profile_id,
                user_id,
                data.name,
                runtime.base_url,
                runtime.model,
                encrypted,
                runtime.temperature,
                runtime.max_tokens,
            )
        return cls._public(row)

    @classmethod
    async def activate(cls, conn, user_id, profile_id):
        async with conn.transaction():
            await conn.fetchval("SELECT id FROM users WHERE id=$1 FOR UPDATE", user_id)
            await cls._owned(conn, user_id, profile_id)
            await conn.execute(
                "UPDATE user_model_profiles SET is_active=FALSE WHERE user_id=$1 AND is_active",
                user_id,
            )
            await conn.execute(
                "UPDATE user_model_profiles SET is_active=TRUE,updated_at=NOW() WHERE id=$1 AND user_id=$2",
                profile_id,
                user_id,
            )
        return await cls.read(conn, user_id)

    @classmethod
    async def delete(cls, conn, user_id, profile_id):
        async with conn.transaction():
            await conn.fetchval("SELECT id FROM users WHERE id=$1 FOR UPDATE", user_id)
            row = await cls._owned(conn, user_id, profile_id)
            count = await conn.fetchval(
                "SELECT COUNT(*) FROM user_model_profiles WHERE user_id=$1", user_id
            )
            if row["is_active"] and count > 1:
                raise ValueError("请先启用另一个模型，再删除当前使用的模型")
            await conn.execute(
                "DELETE FROM user_model_profiles WHERE id=$1 AND user_id=$2",
                profile_id,
                user_id,
            )
        return await cls.read(conn, user_id)
