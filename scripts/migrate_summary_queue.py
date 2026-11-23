"""创建摘要队列并补入尚未生成摘要的资讯；可重复执行。"""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0,str(Path(__file__).resolve().parent.parent))

from src.auth.database import db
from src.tasks.summary_queue import enqueue_missing,ensure_schema


async def migrate():
    await db.connect()
    try:
        async with db.pool.acquire() as conn:
            await ensure_schema(conn)
            queued=await enqueue_missing(conn)
        print(f"摘要队列已就绪，补入 {len(queued)} 条待处理资讯")
    finally:
        await db.disconnect()


if __name__=="__main__":
    asyncio.run(migrate())
