"""持久化摘要队列；同一工作台每次只处理一条资讯。"""

import asyncio
import logging

from ..agent.config import get_settings
from ..settings.service import ModelSettingsService

logger = logging.getLogger(__name__)
LOCK_KEY = 748210636
SUMMARY_STATUS_SQL = """CASE
    WHEN description IS NOT NULL AND description != '' THEN 'ready'
    WHEN summary_job.state='processing' THEN 'processing'
    WHEN summary_job.state='retry' THEN 'retrying'
    ELSE 'queued' END"""


async def ensure_schema(conn):
    async with conn.transaction():
        await conn.execute("SELECT pg_advisory_xact_lock(748210637)")
        await conn.execute("""CREATE TABLE IF NOT EXISTS weibo_summary_jobs (
            id BIGSERIAL UNIQUE NOT NULL,
            title_hash VARCHAR(64) PRIMARY KEY REFERENCES weibo_hot_search_cache(title_hash) ON DELETE CASCADE,
            user_id INTEGER REFERENCES users(id) ON DELETE SET NULL,
            state VARCHAR(16) NOT NULL DEFAULT 'pending' CHECK(state IN ('pending','processing','retry')),
            attempts INTEGER NOT NULL DEFAULT 0,
            queued_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            attempted_at TIMESTAMPTZ,
            available_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            last_error TEXT
        )""")
        await conn.execute("""CREATE INDEX IF NOT EXISTS weibo_summary_jobs_available
            ON weibo_summary_jobs(available_at,queued_at)""")


async def enqueue_missing(conn, user_id=None, limit=None, title_hash=None, retry=False):
    conditions = ["expires_at > NOW()", "(description IS NULL OR description='')"]
    params = [user_id]
    if title_hash is not None:
        params.append(title_hash)
        conditions.append(f"title_hash=${len(params)}")
    limit_sql = ""
    if limit is not None:
        params.append(limit)
        limit_sql = f"LIMIT ${len(params)}"
    conflict = """DO UPDATE SET user_id=EXCLUDED.user_id
        WHERE weibo_summary_jobs.user_id IS NULL AND EXCLUDED.user_id IS NOT NULL"""
    if retry:
        conflict = """DO UPDATE SET
            user_id=COALESCE(weibo_summary_jobs.user_id,EXCLUDED.user_id),
            state='pending',available_at=NOW(),last_error=NULL
            WHERE weibo_summary_jobs.state != 'processing'"""
    rows = await conn.fetch(
        f"""INSERT INTO weibo_summary_jobs(title_hash,user_id)
            SELECT title_hash,$1::integer FROM weibo_hot_search_cache
            WHERE {' AND '.join(conditions)}
            ORDER BY created_at ASC,title_hash ASC {limit_sql}
            ON CONFLICT(title_hash) {conflict} RETURNING title_hash""",
        *params,
    )
    return [row["title_hash"] for row in rows]


async def read_item(conn, title_hash):
    return await conn.fetchrow(
        f"""SELECT title_hash,title,url,description,description_source,
            created_at,updated_at,expires_at,
            {SUMMARY_STATUS_SQL} AS summary_status,
            summary_job.last_error AS summary_error
            FROM weibo_hot_search_cache
            LEFT JOIN weibo_summary_jobs summary_job USING(title_hash)
            WHERE title_hash=$1 AND expires_at > NOW()""",
        title_hash,
    )


async def process_next(pool, username=None):
    from .weibo_tasks import _fetch_and_update_description_async

    async with pool.acquire() as conn:
        locked = await conn.fetchval(
            "SELECT pg_try_advisory_lock(hashtext(current_schema()),$1)", LOCK_KEY
        )
        if not locked:
            return {"status": "busy"}
        try:
            await ensure_schema(conn)
            await conn.execute("""DELETE FROM weibo_summary_jobs job
                USING weibo_hot_search_cache item
                WHERE item.title_hash=job.title_hash AND
                (item.expires_at <= NOW() OR (item.description IS NOT NULL AND item.description != ''))""")
            await enqueue_missing(conn)
            item = await conn.fetchrow("""SELECT job.title_hash,job.user_id,job.attempts,
                    item.title,item.url
                FROM weibo_summary_jobs job
                JOIN weibo_hot_search_cache item USING(title_hash)
                WHERE (job.available_at <= NOW() OR job.state='processing')
                  AND item.expires_at > NOW() AND (item.description IS NULL OR item.description='')
                ORDER BY job.queued_at,job.id LIMIT 1""")
            if item is None:
                return {"status": "idle"}
            user_id = item["user_id"]
            if user_id is None:
                owner = username if username is not None else get_settings().weibo_summary_username
                user_id = await conn.fetchval("SELECT id FROM users WHERE username=$1", owner) if owner else None
            try:
                if user_id is None:
                    raise ValueError("请配置自动摘要账号并启用模型")
                model_config = await ModelSettingsService.resolve(conn, user_id)
            except ValueError as error:
                await conn.execute(
                    """UPDATE weibo_summary_jobs SET state='retry',
                        available_at=NOW()+INTERVAL '1 minute',last_error=$2 WHERE title_hash=$1""",
                    item["title_hash"],str(error),
                )
                return {"status": "waiting_model", "title_hash": item["title_hash"]}
            await conn.execute(
                """UPDATE weibo_summary_jobs SET state='processing',
                    attempts=attempts+1,attempted_at=NOW() WHERE title_hash=$1""",
                item["title_hash"],
            )
            try:
                result = await asyncio.wait_for(
                    _fetch_and_update_description_async(
                        item["title"],item["url"] or "",1,model_config=model_config,pool=pool
                    ),timeout=180,
                )
                complete = await conn.fetchval(
                    "SELECT description IS NOT NULL AND description != '' FROM weibo_hot_search_cache WHERE title_hash=$1",
                    item["title_hash"],
                )
                if not result.get("success") or not complete:
                    raise RuntimeError("摘要尚未生成")
            except Exception as error:
                logger.warning("摘要队列处理失败 (%s)",type(error).__name__)
                delay = min(3600,60 * 2 ** min(item["attempts"],6))
                await conn.execute(
                    """UPDATE weibo_summary_jobs SET state='retry',
                        available_at=NOW()+make_interval(secs => $2),last_error=$3 WHERE title_hash=$1""",
                    item["title_hash"],delay,"生成失败，将自动重试；请检查微博连接和模型服务",
                )
                return {"status": "retry", "title_hash": item["title_hash"]}
            await conn.execute("DELETE FROM weibo_summary_jobs WHERE title_hash=$1",item["title_hash"])
            return {"status": "completed", "title_hash": item["title_hash"]}
        finally:
            await conn.execute("SELECT pg_advisory_unlock(hashtext(current_schema()),$1)",LOCK_KEY)
