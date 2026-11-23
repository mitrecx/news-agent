"""摘要队列使用隔离数据库与本地内容服务，验证持久化、顺序和恢复。"""

import asyncio
from unittest.mock import patch

from src.tasks import summary_queue
from src.tasks.weibo_tasks import _fetch_and_save_hot_search_titles_async
from src.tools.weibo import HotSearchItem
from tests.test_hotsearch_summary import HotSearchFixture


class SummaryQueueTests(HotSearchFixture):
    async def queued(self):
        async with self.pool.acquire() as conn:
            return [dict(row) for row in await conn.fetch(
                "SELECT * FROM weibo_summary_jobs ORDER BY queued_at,title_hash"
            )]

    async def test_scheduled_collection_persists_jobs_without_calling_model(self):
        story = HotSearchItem(rank=1,title="定时采集的新话题",url=self.origin+"/scheduled",hot_value="",category="")
        with patch("src.tools.weibo.WeiboScraper._fetch_hot_search_items",return_value=[story]):
            first = await _fetch_and_save_hot_search_titles_async(10,pool=self.pool)
            second = await _fetch_and_save_hot_search_titles_async(10,pool=self.pool)
        self.assertEqual(first["new_items"],1)
        self.assertEqual(second["new_items"],0)
        jobs = await self.queued()
        self.assertEqual(len(jobs),1)
        self.assertIsNone(jobs[0]["user_id"])
        self.assertEqual(self.requests,[])

    async def test_job_and_collected_title_are_saved_in_one_transaction(self):
        story = HotSearchItem(rank=1,title="事务回滚的话题",url=self.origin+"/scheduled",hot_value="",category="")
        with patch("src.tools.weibo.WeiboScraper._fetch_hot_search_items",return_value=[story]), patch(
            "src.tasks.summary_queue.enqueue_missing",side_effect=RuntimeError("queue insert failure")
        ):
            with self.assertRaises(RuntimeError):
                await _fetch_and_save_hot_search_titles_async(10,pool=self.pool)
        async with self.pool.acquire() as conn:
            self.assertFalse(await conn.fetchval(
                "SELECT EXISTS(SELECT 1 FROM weibo_hot_search_cache WHERE title=$1)",story.title
            ))

    async def test_one_job_is_processed_at_a_time_and_completed_jobs_are_not_repeated(self):
        async with self.pool.acquire() as conn:
            await summary_queue.enqueue_missing(conn,user_id=101)
            await summary_queue.enqueue_missing(conn,user_id=101)
        first = await summary_queue.process_next(self.pool)
        second = await summary_queue.process_next(self.pool)
        self.assertEqual(first["title_hash"],self.old_hash)
        self.assertEqual(second["title_hash"],self.selected_hash)
        self.assertEqual([path for method,path in self.requests if method=="GET"],["/older","/selected"])
        jobs=await self.queued()
        self.assertEqual([job["title_hash"] for job in jobs],[self.next_hash])

    async def test_two_workers_cannot_generate_summaries_concurrently(self):
        async with self.pool.acquire() as conn:
            await summary_queue.enqueue_missing(conn,user_id=101)
        started,finish=asyncio.Event(),asyncio.Event()
        async def slow_model(*args,**kwargs):
            started.set()
            await finish.wait()
            return "Agent总结: 排队生成的摘要"
        with patch("src.tools.llm_summary.summarize_weibo_content",side_effect=slow_model):
            task=asyncio.create_task(summary_queue.process_next(self.pool))
            await asyncio.wait_for(started.wait(),timeout=5)
            try:
                concurrent=await summary_queue.process_next(self.pool)
                self.assertEqual(concurrent["status"],"busy")
            finally:
                finish.set()
                await task
        self.assertEqual([path for method,path in self.requests if method=="GET"],["/older"])

    async def test_failure_retries_later_without_blocking_the_next_story(self):
        async with self.pool.acquire() as conn:
            await conn.execute("UPDATE weibo_hot_search_cache SET url=$1 WHERE title_hash=$2",self.origin+"/blocked",self.old_hash)
            await summary_queue.enqueue_missing(conn,user_id=101)
        failed=await summary_queue.process_next(self.pool)
        following=await summary_queue.process_next(self.pool)
        self.assertEqual(failed["status"],"retry")
        self.assertEqual(following["title_hash"],self.selected_hash)
        async with self.pool.acquire() as conn:
            job=await conn.fetchrow("SELECT *,available_at>NOW() delayed FROM weibo_summary_jobs WHERE title_hash=$1",self.old_hash)
            self.assertTrue(job["delayed"])
            self.assertEqual(job["attempts"],1)
            self.assertIsNone((await self.descriptions())[self.old_hash])
            await conn.execute("UPDATE weibo_hot_search_cache SET url=$1 WHERE title_hash=$2",self.origin+"/recovered",self.old_hash)
            await conn.execute("UPDATE weibo_summary_jobs SET available_at=NOW() WHERE title_hash=$1",self.old_hash)
        retried=await summary_queue.process_next(self.pool)
        self.assertEqual(retried["status"],"completed")
        self.assertTrue((await self.descriptions())[self.old_hash])

    async def test_interrupted_processing_is_recovered_after_worker_restart(self):
        async with self.pool.acquire() as conn:
            await summary_queue.enqueue_missing(conn,user_id=101,title_hash=self.old_hash)
            await conn.execute("UPDATE weibo_summary_jobs SET state='processing',available_at=NOW()+INTERVAL '1 hour'")
        result=await summary_queue.process_next(self.pool)
        self.assertEqual(result["status"],"completed")
        self.assertEqual(result["title_hash"],self.old_hash)

    async def test_default_account_supplies_the_model_without_borrowing_other_users(self):
        async with self.pool.acquire() as conn:
            await conn.execute("ALTER TABLE users ADD COLUMN username TEXT")
            await conn.execute("UPDATE users SET username='queue-owner' WHERE id=101")
            await summary_queue.enqueue_missing(conn,title_hash=self.old_hash)
        missing=await summary_queue.process_next(self.pool,username="not-configured")
        self.assertEqual(missing["status"],"waiting_model")
        self.assertEqual(self.requests,[])
        async with self.pool.acquire() as conn:
            await conn.execute("UPDATE weibo_summary_jobs SET available_at=NOW()")
        result=await summary_queue.process_next(self.pool,username="queue-owner")
        self.assertEqual(result["status"],"completed")
        self.assertEqual(self.model_requests[0][0]["model"],"selected-story-model")

    async def test_job_with_unconfigured_owner_does_not_use_default_account(self):
        async with self.pool.acquire() as conn:
            await conn.execute("ALTER TABLE users ADD COLUMN username TEXT")
            await conn.execute("UPDATE users SET username='queue-owner' WHERE id=101")
            await summary_queue.enqueue_missing(conn,user_id=202,title_hash=self.old_hash)
        result=await summary_queue.process_next(self.pool,username="queue-owner")
        self.assertEqual(result["status"],"waiting_model")
        self.assertEqual(self.requests,[])
        self.assertIsNone((await self.descriptions())[self.old_hash])

    async def test_completed_summary_is_not_generated_again_after_interruption(self):
        async with self.pool.acquire() as conn:
            await summary_queue.enqueue_missing(conn,user_id=101,title_hash=self.old_hash)
            await conn.execute("UPDATE weibo_summary_jobs SET state='processing'")
            await conn.execute("UPDATE weibo_hot_search_cache SET description='已保存的摘要' WHERE title_hash=$1",self.old_hash)
            await conn.execute("UPDATE weibo_hot_search_cache SET expires_at=NOW()-INTERVAL '1 day' WHERE title_hash!=$1",self.old_hash)
        result=await summary_queue.process_next(self.pool)
        self.assertEqual(result["status"],"idle")
        self.assertEqual(self.requests,[])
        self.assertEqual(await self.queued(),[])

    async def test_list_and_detail_show_retry_state_without_private_error_details(self):
        async with self.pool.acquire() as conn:
            await summary_queue.enqueue_missing(conn,user_id=101,title_hash=self.selected_hash)
            await conn.execute("UPDATE weibo_hot_search_cache SET url=$1 WHERE title_hash=$2",self.origin+"/blocked",self.selected_hash)
        await summary_queue.process_next(self.pool)
        detail=await self.client.get(f"/api/weibo/cache/{self.selected_hash}")
        listing=await self.client.get("/api/weibo/cache",params={"search":"当前选中"})
        self.assertEqual(detail.json()["summary_status"],"retrying")
        self.assertEqual(listing.json()["items"][0]["summary_status"],"retrying")
        self.assertIn("自动重试",detail.json()["summary_error"])
        self.assertNotIn("test-only-model-key",detail.text)
