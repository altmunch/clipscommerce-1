from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.api.deps import get_current_user
from app.models.user import User
from app.models.brand import Brand, Asset
from app.models.job import Job
from app.schemas.brand import (
    BrandCreate, BrandAssimilateResponse, BrandsResponse, BrandList,
    BrandKitResponse, BrandKit, BrandKitUpdate, Asset as AssetSchema
)
from app.services.brand_service import BrandService
from app.tasks.brand_tasks import assimilate_brand
import uuid
from typing import List

router = APIRouter()

@router.post("/assimilate", status_code=202, response_model=BrandAssimilateResponse)
async def assimilate_brand_endpoint(
    brand_data: BrandCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Start brand assimilation process from URL
    """
    # Create job record
    job_id = str(uuid.uuid4())
    job = Job(
        job_id=job_id,
        job_type="assimilate",
        status="processing",
        progress=0
    )
    db.add(job)
    db.commit()
    
    # Start background task
    assimilate_brand.delay(current_user.id, str(brand_data.url), job_id)
    
    return BrandAssimilateResponse(
        jobId=job_id,
        message="Brand assimilation has started."
    )

@router.get("", response_model=BrandsResponse)
def get_brands(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get all brands for the authenticated user
    """
    brands = BrandService.get_brands_by_user(db, current_user.id)
    
    brand_list = [
        BrandList(
            brandId=brand.id,
            name=brand.name,
            url=brand.url
        )
        for brand in brands
    ]
    
    return BrandsResponse(data=brand_list)

@router.get("/{brand_id}/kit", response_model=BrandKitResponse)
def get_brand_kit(
    brand_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get complete brand kit for a specific brand
    """
    brand = BrandService.get_brand_kit(db, brand_id, current_user.id)
    
    if not brand:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Brand not found"
        )
    
    # Get brand assets
    assets = BrandService.get_brand_assets(db, brand_id)
    asset_schemas = [
        AssetSchema(
            assetId=asset.id,
            assetType=asset.asset_type,
            name=asset.name,
            url=asset.url,
            createdAt=asset.created_at
        )
        for asset in assets
    ]
    
    brand_kit = BrandKit(
        brandName=brand.name,
        logoUrl=brand.logo_url,
        colors=brand.colors,
        voice=brand.voice,
        pillars=brand.pillars,
        assets=asset_schemas
    )
    
    return BrandKitResponse(data=brand_kit)

@router.put("/{brand_id}/kit")
def update_brand_kit(
    brand_id: int,
    kit_update: BrandKitUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Update brand kit information
    """
    updated_brand = BrandService.update_brand_kit(
        db, brand_id, current_user.id, kit_update
    )
    
    if not updated_brand:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Brand not found"
        )
    
    return {"message": "Brand kit updated successfully."}