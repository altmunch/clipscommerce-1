from pydantic import BaseModel, HttpUrl
from datetime import datetime
from typing import Optional, List, Dict, Any

class AssetBase(BaseModel):
    assetType: str
    name: str
    url: str

class AssetCreate(AssetBase):
    brandId: int

class Asset(AssetBase):
    assetId: int
    createdAt: datetime

    class Config:
        from_attributes = True

class BrandColors(BaseModel):
    primary: str
    secondary: str

class BrandVoice(BaseModel):
    tone: str
    dos: str
    donts: str

class BrandBase(BaseModel):
    name: str
    url: HttpUrl

class BrandCreate(BaseModel):
    name: str
    url: HttpUrl

class BrandAssimilateResponse(BaseModel):
    jobId: str
    message: str

class BrandList(BaseModel):
    brandId: int
    name: str
    url: str

class BrandsResponse(BaseModel):
    data: List[BrandList]

class BrandKit(BaseModel):
    brandName: str
    logoUrl: Optional[str] = None
    colors: Optional[BrandColors] = None
    voice: Optional[BrandVoice] = None
    pillars: Optional[List[str]] = None
    assets: List[Asset] = []

class BrandKitResponse(BaseModel):
    data: BrandKit

class BrandKitUpdate(BaseModel):
    brandName: Optional[str] = None
    logoUrl: Optional[str] = None
    colors: Optional[BrandColors] = None
    voice: Optional[BrandVoice] = None
    pillars: Optional[List[str]] = None

class Brand(BrandBase):
    brandId: int
    userId: int
    logoUrl: Optional[str] = None
    colors: Optional[Dict[str, Any]] = None
    voice: Optional[Dict[str, Any]] = None
    pillars: Optional[List[str]] = None
    createdAt: datetime
    updatedAt: Optional[datetime] = None

    class Config:
        from_attributes = True