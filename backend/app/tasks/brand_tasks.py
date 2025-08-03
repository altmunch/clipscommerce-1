import uuid
import httpx
import asyncio
from celery import current_task
from sqlalchemy.orm import Session
from app.core.celery_app import celery_app
from app.db.session import SessionLocal
from app.models import Brand, Asset, Job
from app.services.brand_service import BrandService
from app.services.ai.brand_assimilation import get_brand_assimilation_service
from app.tasks.scraping_tasks import enhanced_brand_scraping
import logging

logger = logging.getLogger(__name__)

@celery_app.task(name="assimilate_brand")
def assimilate_brand(user_id: int, url: str, job_id: str, use_enhanced_scraping: bool = True):
    """
    Background task to assimilate a brand from URL
    Uses enhanced scraping system if available, falls back to original implementation
    """
    db = SessionLocal()
    try:
        # Update job status to processing
        job = db.query(Job).filter(Job.job_id == job_id).first()
        if job:
            job.status = "processing"
            job.progress = 10
            db.commit()
        
        if use_enhanced_scraping:
            # Use the new enhanced scraping system
            try:
                result = enhanced_brand_scraping.apply_async(
                    args=[user_id, url, job_id, {"use_playwright": False}]
                )
                return result.get()  # Wait for completion
            except Exception as e:
                logger.warning(f"Enhanced scraping failed, falling back to original: {e}")
                # Fall through to original implementation
        
        # Original implementation as fallback
        current_task.update_state(state="PROGRESS", meta={"progress": 25})
        
        # Try to use AI brand assimilation service
        try:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
            brand_service = loop.run_until_complete(get_brand_assimilation_service())
            brand_kit = loop.run_until_complete(brand_service.assimilate_brand(url))
            
            current_task.update_state(state="PROGRESS", meta={"progress": 60})
            
            # Create brand record from AI analysis
            brand = Brand(
                user_id=user_id,
                name=brand_kit.brand_name,
                url=url,
                logo_url=brand_kit.logo_url,
                colors=brand_kit.colors.to_dict(),
                voice=brand_kit.voice.to_dict(),
                pillars=[p.to_dict() for p in brand_kit.pillars],
                industry=brand_kit.industry,
                target_audience={"description": brand_kit.target_audience},
                unique_value_proposition=brand_kit.unique_value_proposition,
                competitors=brand_kit.competitors
            )
            
            loop.close()
            
        except Exception as e:
            logger.warning(f"AI brand assimilation failed, using simple extraction: {e}")
            
            # Fallback to simple extraction
            brand_name = url.replace("https://", "").replace("www.", "").split(".")[0].title()
            brand = Brand(
                user_id=user_id,
                name=brand_name,
                url=url,
                colors={"primary": "#007bff", "secondary": "#6c757d"},
                voice={"tone": "Professional", "dos": "Be clear and direct", "donts": "Avoid jargon"},
                pillars=["Quality", "Innovation", "Customer Service"]
            )
        
        db.add(brand)
        db.flush()
        
        current_task.update_state(state="PROGRESS", meta={"progress": 75})
        
        # Create assets
        if brand.logo_url:
            logo_asset = Asset(
                brand_id=brand.id,
                asset_type="logo",
                name="Brand Logo",
                url=brand.logo_url
            )
        else:
            logo_asset = Asset(
                brand_id=brand.id,
                asset_type="logo",
                name="Brand Logo",
                url=f"https://via.placeholder.com/200x100?text={brand.name}"
            )
        db.add(logo_asset)
        
        current_task.update_state(state="PROGRESS", meta={"progress": 90})
        
        db.commit()
        
        # Update job as complete
        if job:
            job.status = "complete"
            job.progress = 100
            job.result = {
                "message": "Brand assimilation complete.",
                "resourceId": str(brand.id),
                "brandId": brand.id,
                "brandName": brand.name
            }
            db.commit()
        
        return {
            "message": "Brand assimilation complete.",
            "brandId": brand.id,
            "brandName": brand.name
        }
        
    except Exception as e:
        logger.error(f"Brand assimilation failed: {str(e)}")
        
        # Update job as failed
        if job:
            job.status = "failed"
            job.error = str(e)
            db.commit()
            
        raise e
    finally:
        db.close()