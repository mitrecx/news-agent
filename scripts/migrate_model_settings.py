"""创建按用户隔离的模型设置表；可重复执行，不修改现有数据。"""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.auth.database import db
from src.settings.service import ModelSettingsService


async def migrate():
    await db.connect()
    try:
        async with db.pool.acquire() as conn:
            await ModelSettingsService.ensure_schema(conn)
        print("用户模型设置表已就绪")
    finally:
        await db.disconnect()


if __name__ == "__main__":
    asyncio.run(migrate())
