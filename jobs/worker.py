import asyncio
from crawler.engine import crawl_ai_collect
from .store import update_job

async def run_job(job_id, url, geo):
    try:
        result = await crawl_ai_collect(url, geo)
        update_job(job_id, "done", result=result)
    except Exception as e:
        update_job(job_id, "failed", error=str(e))
