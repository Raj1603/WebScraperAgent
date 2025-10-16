# import asyncio
# from fastapi import FastAPI, Request
# from fastapi.responses import JSONResponse
# from jobs.store import create_job, get_job
# from jobs.worker import run_job
# from config.settings import PORT

# app = FastAPI(title="Crawl4AI Smart Scraper API")

# @app.post("/crawl/start")
# async def start_crawl(request: Request):
#     data = await request.json()
#     url = data.get("url")
#     geo = data.get("geo_location", "N/A")
#     if not url:
#         return JSONResponse({"error": "Missing 'url'"}, status_code=400)
#     job_id = create_job(url, geo)
#     asyncio.create_task(run_job(job_id, url, geo))
#     return {"job_id": job_id, "status": "processing", "url": url, "geo": geo}

# @app.get("/crawl/result/{job_id}")
# def get_result(job_id: str):
#     job = get_job(job_id)
#     if not job:
#         return JSONResponse({"error": "Invalid job_id"}, status_code=404)
#     return job

# @app.get("/")
# def health():
#     return {"status": "ok", "jobs_in_memory": len(getattr(get_job, '__annotations__', {}))}

# if __name__ == "__main__":
#     import uvicorn
#     uvicorn.run("server:app", host="0.0.0.0", port=PORT)

#---------------------------------  2nd version ----------------

from fastapi import FastAPI
from fastapi.responses import JSONResponse
from crawler.models import CrawlRequest, CrawlResponse
from jobs.store import create_job, get_job
from jobs.worker import run_job
import asyncio

app = FastAPI(title="Crawl4AI Smart Scraper API", version="1.0")

@app.post("/crawl/start", response_model=CrawlResponse)
async def start_crawl(req: CrawlRequest):
    url = req.url
    geo = req.geo_location or "N/A"
    job_id = create_job(url, geo)
    asyncio.create_task(run_job(job_id, url, geo))
    return {"job_id": job_id, "status": "processing", "url": url, "geo": geo}

@app.get("/crawl/result/{job_id}")
def get_result(job_id: str):
    job = get_job(job_id)
    if not job:
        return JSONResponse({"error": "Invalid job_id"}, status_code=404)
    return job

@app.get("/")
def health():
    return {"status": "ok"}

