from pydantic import BaseModel
from typing import Optional, Dict, Any

class JobStatus(BaseModel):
    jobId: str
    status: str  # processing, complete, failed
    progress: Optional[int] = None
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None

class JobResponse(BaseModel):
    jobId: str
    status: str
    progress: Optional[int] = None
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None