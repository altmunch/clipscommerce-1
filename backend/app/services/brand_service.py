from sqlalchemy.orm import Session
from app.models import Brand, Asset
from app.schemas.brand import BrandCreate, BrandKitUpdate
from typing import List, Optional
import httpx
import logging

logger = logging.getLogger(__name__)

class BrandService:
    @staticmethod
    def get_brands_by_user(db: Session, user_id: int) -> List[Brand]:
        """Get all brands for a user"""
        return db.query(Brand).filter(Brand.user_id == user_id).all()
    
    @staticmethod
    def get_brand_by_id(db: Session, brand_id: int, user_id: int) -> Optional[Brand]:
        """Get a specific brand by ID for a user"""
        return db.query(Brand).filter(
            Brand.id == brand_id, 
            Brand.user_id == user_id
        ).first()
    
    @staticmethod
    def get_brand_kit(db: Session, brand_id: int, user_id: int) -> Optional[Brand]:
        """Get brand kit with assets"""
        brand = db.query(Brand).filter(
            Brand.id == brand_id,
            Brand.user_id == user_id
        ).first()
        return brand
    
    @staticmethod
    def update_brand_kit(db: Session, brand_id: int, user_id: int, update_data: BrandKitUpdate) -> Optional[Brand]:
        """Update brand kit information"""
        brand = db.query(Brand).filter(
            Brand.id == brand_id,
            Brand.user_id == user_id
        ).first()
        
        if not brand:
            return None
        
        update_dict = update_data.dict(exclude_unset=True)
        
        # Handle nested objects
        if "colors" in update_dict:
            brand.colors = update_dict["colors"]
        if "voice" in update_dict:
            brand.voice = update_dict["voice"]
        if "pillars" in update_dict:
            brand.pillars = update_dict["pillars"]
        if "brandName" in update_dict:
            brand.name = update_dict["brandName"]
        if "logoUrl" in update_dict:
            brand.logo_url = update_dict["logoUrl"]
        
        db.commit()
        db.refresh(brand)
        return brand
    
    @staticmethod
    def get_brand_assets(db: Session, brand_id: int) -> List[Asset]:
        """Get all assets for a brand"""
        return db.query(Asset).filter(Asset.brand_id == brand_id).all()
    
    @staticmethod
    async def scrape_brand_info(url: str) -> dict:
        """
        Scrape brand information from URL
        In production, this would use web scraping libraries
        """
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(url, timeout=10.0)
                response.raise_for_status()
                
                # Mock extraction - in production would parse HTML
                domain = url.replace("https://", "").replace("www.", "").split("/")[0]
                brand_name = domain.split(".")[0].title()
                
                return {
                    "name": brand_name,
                    "url": url,
                    "colors": {"primary": "#007bff", "secondary": "#6c757d"},
                    "voice": {"tone": "Professional", "dos": "Be clear", "donts": "Avoid jargon"},
                    "pillars": ["Quality", "Innovation"]
                }
        except Exception as e:
            logger.error(f"Failed to scrape brand info: {str(e)}")
            raise