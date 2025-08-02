from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.api.deps import get_current_user
from app.models.user import User
from app.models.campaign import Campaign
from app.models.brand import Brand
from app.schemas.campaign import CampaignCreate, CampaignResponse, CampaignsResponse, Campaign as CampaignSchema
from typing import Optional

router = APIRouter()

@router.post("", status_code=201, response_model=CampaignResponse)
def create_campaign(
    campaign_data: CampaignCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Create a new strategic campaign
    """
    # Verify brand belongs to user
    brand = db.query(Brand).filter(
        Brand.id == campaign_data.brandId,
        Brand.user_id == current_user.id
    ).first()
    
    if not brand:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Brand not found"
        )
    
    # Create campaign
    campaign = Campaign(
        brand_id=campaign_data.brandId,
        name=campaign_data.name,
        goal=campaign_data.goal,
        start_date=campaign_data.startDate,
        end_date=campaign_data.endDate
    )
    db.add(campaign)
    db.commit()
    db.refresh(campaign)
    
    campaign_schema = CampaignSchema(
        campaignId=campaign.id,
        brandId=campaign.brand_id,
        name=campaign.name,
        goal=campaign.goal,
        startDate=campaign.start_date,
        endDate=campaign.end_date,
        createdAt=campaign.created_at,
        updatedAt=campaign.updated_at
    )
    
    return CampaignResponse(data=campaign_schema)

@router.get("", response_model=CampaignsResponse)
def get_campaigns(
    brand_id: int = Query(..., alias="brandId"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get all campaigns for a specific brand
    """
    # Verify brand belongs to user
    brand = db.query(Brand).filter(
        Brand.id == brand_id,
        Brand.user_id == current_user.id
    ).first()
    
    if not brand:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Brand not found"
        )
    
    # Get campaigns for the brand
    campaigns = db.query(Campaign).filter(Campaign.brand_id == brand_id).all()
    
    campaign_schemas = [
        CampaignSchema(
            campaignId=campaign.id,
            brandId=campaign.brand_id,
            name=campaign.name,
            goal=campaign.goal,
            startDate=campaign.start_date,
            endDate=campaign.end_date,
            createdAt=campaign.created_at,
            updatedAt=campaign.updated_at
        )
        for campaign in campaigns
    ]
    
    return CampaignsResponse(data=campaign_schemas)