from pydantic import BaseModel
from typing import Optional, Any

class CrawlRequest(BaseModel):
    url: str
    geo_location: Optional[str] = "N/A"

class CrawlResponse(BaseModel):
    job_id: str
    status: str
    url: str
    geo: str
