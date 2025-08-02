from pydantic import BaseModel
from datetime import date
from typing import List, Optional

class KPIData(BaseModel):
    attributedRevenue: float
    totalViews: int
    clicksDriven: int
    avgConversionRate: float

class KPIResponse(BaseModel):
    data: KPIData

class ChartDataPoint(BaseModel):
    date: str
    value: float

class ChartResponse(BaseModel):
    data: List[ChartDataPoint]

class ContentPerformance(BaseModel):
    videoId: int
    thumbnailUrl: Optional[str] = None
    views: int
    clicks: int
    revenue: float

class Pagination(BaseModel):
    currentPage: int
    totalPages: int

class ContentResponse(BaseModel):
    data: List[ContentPerformance]
    pagination: Pagination

class Insight(BaseModel):
    title: str
    insight: str

class InsightsResponse(BaseModel):
    data: List[Insight]