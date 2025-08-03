"""
Core pipeline API endpoint for brand analysis and viral content generation.
"""

import asyncio
from typing import Any, Dict, List
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session

from app.api import deps
from app.core.config import settings
from app.services.scraping.core_brand_scraper import CoreBrandScraper
from app.services.ai.viral_content import ViralContentGenerator
from app.services.ai.simple_video_generator import VideoGenerator
from app.services.ai.seo_optimizer import SEOOptimizer

router = APIRouter()


@router.post("/analyze-brand")
async def analyze_brand(
    *,
    db: Session = Depends(deps.get_db),
    brand_url: str,
    background_tasks: BackgroundTasks,
) -> Dict[str, Any]:
    """
    Step 1: Analyze brand from URL and extract products
    """
    
    if not brand_url:
        raise HTTPException(status_code=400, detail="Brand URL is required")
    
    try:
        # Scrape brand information and products
        async with CoreBrandScraper() as scraper:
            result = await scraper.scrape(brand_url)
            
            if not result.success:
                raise HTTPException(status_code=400, detail=f"Failed to scrape brand: {result.error}")
            
            brand_data = result.data
            
            return {
                "success": True,
                "brand": brand_data.get("brand", {}),
                "products": brand_data.get("products", []),
                "total_products": len(brand_data.get("products", [])),
                "message": "Brand analysis completed successfully"
            }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error analyzing brand: {str(e)}")


@router.post("/generate-content-ideas")
async def generate_content_ideas(
    *,
    db: Session = Depends(deps.get_db),
    brand_data: Dict[str, Any],
    products: List[Dict[str, Any]],
    content_count: int = 10
) -> Dict[str, Any]:
    """
    Step 2: Generate high-value viral content ideas
    """
    
    try:
        content_generator = ViralContentGenerator()
        
        # Generate viral content ideas
        content_ideas = await content_generator.generate_ideas(
            brand_data=brand_data,
            products=products,
            count=content_count
        )
        
        return {
            "success": True,
            "content_ideas": content_ideas,
            "total_ideas": len(content_ideas),
            "message": "Content ideas generated successfully"
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generating content ideas: {str(e)}")


@router.post("/create-video-outlines")
async def create_video_outlines(
    *,
    db: Session = Depends(deps.get_db),
    content_ideas: List[Dict[str, Any]],
    brand_data: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Step 3: Create exact video outlines for each content idea
    """
    
    try:
        content_generator = ViralContentGenerator()
        
        video_outlines = []
        
        for idea in content_ideas:
            outline = await content_generator.create_video_outline(
                content_idea=idea,
                brand_data=brand_data
            )
            if outline:
                video_outlines.append(outline)
        
        return {
            "success": True,
            "video_outlines": video_outlines,
            "total_outlines": len(video_outlines),
            "message": "Video outlines created successfully"
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error creating video outlines: {str(e)}")


@router.post("/generate-production-guide")
async def generate_production_guide(
    *,
    db: Session = Depends(deps.get_db),
    video_outlines: List[Dict[str, Any]],
    brand_data: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Step 4: Generate detailed production guide for user to create videos
    """
    
    try:
        from app.services.ai.production_guide import ProductionGuideGenerator
        
        guide_generator = ProductionGuideGenerator()
        
        production_guides = []
        for outline in video_outlines:
            guide = await guide_generator.create_production_guide(
                video_outline=outline,
                brand_data=brand_data
            )
            if guide:
                production_guides.append(guide)
        
        return {
            "success": True,
            "production_guides": production_guides,
            "total_guides": len(production_guides),
            "message": "Production guides created - ready for user video creation!"
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error creating production guides: {str(e)}")


@router.post("/optimize-seo")
async def optimize_seo(
    *,
    db: Session = Depends(deps.get_db),
    video_outlines: List[Dict[str, Any]],
    brand_data: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Step 5: SEO optimization for conversion
    """
    
    try:
        seo_optimizer = SEOOptimizer()
        
        optimized_content = []
        
        for outline in video_outlines:
            seo_data = await seo_optimizer.optimize_for_conversion(
                video_outline=outline,
                brand_data=brand_data
            )
            if seo_data:
                optimized_content.append({
                    "video_outline": outline,
                    "seo_optimization": seo_data
                })
        
        return {
            "success": True,
            "optimized_content": optimized_content,
            "total_optimized": len(optimized_content),
            "message": "SEO optimization completed"
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error optimizing SEO: {str(e)}")


@router.post("/full-pipeline")
async def run_full_pipeline(
    *,
    db: Session = Depends(deps.get_db),
    brand_url: str,
    content_count: int = 5,
    background_tasks: BackgroundTasks
) -> Dict[str, Any]:
    """
    Run the complete pipeline: Brand analysis → Content ideas → Video outlines → Video generation → SEO
    """
    
    try:
        # Step 1: Brand analysis
        async with CoreBrandScraper() as scraper:
            brand_result = await scraper.scrape(brand_url)
            
            if not brand_result.success:
                raise HTTPException(status_code=400, detail=f"Failed to scrape brand: {brand_result.error}")
            
            brand_data = brand_result.data.get("brand", {})
            products = brand_result.data.get("products", [])
        
        # Step 2: Content ideas
        content_generator = ViralContentGenerator()
        content_ideas = await content_generator.generate_ideas(
            brand_data=brand_data,
            products=products,
            count=content_count
        )
        
        # Step 3: Video outlines
        video_outlines = []
        for idea in content_ideas:
            outline = await content_generator.create_video_outline(
                content_idea=idea,
                brand_data=brand_data
            )
            if outline:
                video_outlines.append(outline)
        
        # Step 4: SEO optimization
        seo_optimizer = SEOOptimizer()
        optimized_content = []
        
        for outline in video_outlines:
            seo_data = await seo_optimizer.optimize_for_conversion(
                video_outline=outline,
                brand_data=brand_data
            )
            if seo_data:
                optimized_content.append({
                    "video_outline": outline,
                    "seo_optimization": seo_data
                })
        
        # Step 5: Generate production guides for user video creation
        from app.services.ai.production_guide import ProductionGuideGenerator
        guide_generator = ProductionGuideGenerator()
        
        production_guides = []
        for outline in video_outlines:
            guide = await guide_generator.create_production_guide(
                video_outline=outline,
                brand_data=brand_data
            )
            if guide:
                production_guides.append(guide)
        
        return {
            "success": True,
            "pipeline_results": {
                "brand_analysis": {
                    "brand": brand_data,
                    "products_count": len(products)
                },
                "content_ideas": content_ideas,
                "video_outlines": video_outlines,
                "production_guides": production_guides,
                "seo_optimized_content": optimized_content
            },
            "message": "Full pipeline completed successfully - ready for video production!"
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Pipeline error: {str(e)}")


async def generate_videos_background(video_outlines: List[Dict[str, Any]], brand_data: Dict[str, Any]):
    """Background task for video generation"""
    
    try:
        video_generator = VideoGenerator()
        
        for outline in video_outlines:
            # Generate main video
            video_result = await video_generator.generate_video(
                outline=outline,
                brand_data=brand_data
            )
            
            # Generate short version
            if video_result:
                short_result = await video_generator.generate_short(
                    outline=outline,
                    brand_data=brand_data,
                    original_video=video_result
                )
        
    except Exception as e:
        # Log error but don't fail the background task
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"Background video generation failed: {e}")


@router.get("/pipeline-status/{job_id}")
async def get_pipeline_status(
    job_id: str,
    db: Session = Depends(deps.get_db)
) -> Dict[str, Any]:
    """
    Get status of pipeline execution
    """
    
    # This would check the status of background tasks
    # For now, return a placeholder
    return {
        "job_id": job_id,
        "status": "completed",
        "message": "Pipeline completed successfully"
    }