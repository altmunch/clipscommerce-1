from pydantic import BaseModel
from datetime import datetime
from typing import Optional, List

class CampaignBase(BaseModel):
    name: str
    goal: Optional[str] = None
    startDate: Optional[datetime] = None
    endDate: Optional[datetime] = None

class CampaignCreate(CampaignBase):
    brandId: int

class Campaign(CampaignBase):
    campaignId: int
    brandId: int
    createdAt: datetime
    updatedAt: Optional[datetime] = None

    class Config:
        from_attributes = True

class CampaignResponse(BaseModel):
    data: Campaign

class CampaignsResponse(BaseModel):
    data: List[Campaign]