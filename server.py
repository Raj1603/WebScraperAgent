

import subprocess, os, sys

def ensure_playwright_installed():
    chromium_path = "/opt/render/.cache/ms-playwright/chromium-1187/chrome-linux/chrome"
    if not os.path.exists(chromium_path):
        print("⚙️ Playwright Chromium not found, installing...")
        try:
            subprocess.run([sys.executable, "-m", "playwright", "install", "chromium"], check=True)
            print("✅ Chromium installed successfully.")
        except subprocess.CalledProcessError as e:
            print(f"❌ Failed to install Chromium: {e}")
            raise

ensure_playwright_installed()


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

