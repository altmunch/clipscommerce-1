from pydantic import BaseModel
from datetime import datetime
from typing import Optional, List, Dict, Any

# Idea Schemas
class IdeaGenerateRequest(BaseModel):
    brandId: int
    campaignId: Optional[int] = None

class IdeaGenerateResponse(BaseModel):
    jobId: str
    message: str

class Idea(BaseModel):
    ideaId: int
    hook: str
    status: str
    viralScore: Optional[float] = None

    class Config:
        from_attributes = True

class IdeasResponse(BaseModel):
    data: List[Idea]

# Blueprint Schemas
class BlueprintGenerateRequest(BaseModel):
    ideaId: int

class BlueprintGenerateResponse(BaseModel):
    jobId: str
    message: str

class Blueprint(BaseModel):
    blueprintId: int
    ideaId: int
    script: Optional[str] = None
    shotList: Optional[List[Dict[str, Any]]] = None
    status: str
    createdAt: datetime

    class Config:
        from_attributes = True

# Video Schemas
class VideoGenerateRequest(BaseModel):
    blueprintId: int

class VideoGenerateResponse(BaseModel):
    jobId: str
    message: str

class VideoOptimizeRequest(BaseModel):
    caption: str
    hashtags: List[str]
    cta: str

class VideoScheduleRequest(BaseModel):
    publishAt: datetime
    platforms: List[str]

class Video(BaseModel):
    videoId: int
    blueprintId: int  
    videoUrl: Optional[str] = None
    thumbnailUrl: Optional[str] = None
    caption: Optional[str] = None
    hashtags: Optional[List[str]] = None
    cta: Optional[str] = None
    status: str
    scheduledAt: Optional[datetime] = None
    platforms: Optional[List[str]] = None
    views: int = 0
    clicks: int = 0
    revenue: float = 0.0
    createdAt: datetime
    updatedAt: Optional[datetime] = None

    class Config:
        from_attributes = True

class VideoOptimizeResponse(BaseModel):
    message: str

class VideoScheduleResponse(BaseModel):
    message: str