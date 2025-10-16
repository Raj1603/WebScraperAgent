import uuid

jobs = {}

def create_job(url, geo):
    job_id = str(uuid.uuid4())
    jobs[job_id] = {"status": "processing", "url": url, "geo": geo}
    return job_id

def update_job(job_id, status, result=None, error=None):
    if job_id in jobs:
        jobs[job_id].update({"status": status, "result": result, "error": error})

def get_job(job_id):
    return jobs.get(job_id)
