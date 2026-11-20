"""显式将 .env 模型导入指定用户，仅作为一次性迁移，不作为运行时默认值。"""

import argparse
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from dotenv import dotenv_values

from src.auth.database import db
from src.settings.models import ModelSettingsInput
from src.settings.service import ModelSettingsService


async def import_model(username: str, name: str | None):
    values = dotenv_values(Path(__file__).resolve().parent.parent / ".env")
    key = values.get("DEEPSEEK_API_KEY", "")
    base_url = values.get("DEEPSEEK_BASE_URL", "")
    model = values.get("AGENT_MODEL", "")
    if not key or not base_url or not model:
        raise ValueError("本地文件中的模型连接信息不完整")
    await db.connect()
    try:
        async with db.pool.acquire() as conn:
            await ModelSettingsService.ensure_schema(conn)
            user_id = await conn.fetchval(
                "SELECT id FROM users WHERE username=$1", username
            )
            if user_id is None:
                raise ValueError("指定账号不存在")
            async with conn.transaction():
                await conn.fetchval(
                    "SELECT id FROM users WHERE id=$1 FOR UPDATE", user_id
                )
                if (await ModelSettingsService.read(conn, user_id)).items:
                    print("该账号已有模型，保留现有配置，不重复导入。")
                    return
                data = ModelSettingsInput(
                    name=name or model,
                    base_url=base_url,
                    model=model,
                    api_key=key,
                    temperature=float(values.get("AGENT_TEMPERATURE") or 0.7),
                    max_tokens=int(values.get("AGENT_MAX_TOKENS") or 2000),
                )
                await ModelSettingsService.create(conn, user_id, data)
        print("已导入首个模型并启用；凭据已加密保存，未输出。")
    finally:
        await db.disconnect()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--username", required=True)
    parser.add_argument("--name")
    arguments = parser.parse_args()
    try:
        asyncio.run(import_model(arguments.username, arguments.name))
    except Exception:  # noqa: BLE001 -- 隐藏包含本地凭据的底层诊断
        print("导入失败，请检查账号和本地连接配置；敏感诊断已省略。", file=sys.stderr)
        raise SystemExit(1)
