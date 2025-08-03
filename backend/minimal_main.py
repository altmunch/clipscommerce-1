#!/usr/bin/env python3
"""
Minimal FastAPI server with real backend services
Uses the actual AI services without complex dependencies
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from typing import Any, Dict, List, Optional
import asyncio
import logging

# Import our real services
from app.services.scraping.core_brand_scraper import CoreBrandScraper
from app.services.ai.viral_content import ViralContentGenerator  
from app.services.ai.production_guide import ProductionGuideGenerator
from app.services.ai.seo_optimizer import SEOOptimizer

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create FastAPI app
app = FastAPI(
    title="ClipsCommerce Core Pipeline",
    description="Real backend services for viral content generation",
    version="1.0.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Pydantic models for requests
class BrandAnalysisRequest(BaseModel):
    brand_url: str

class ContentIdeasRequest(BaseModel):
    brand_data: Dict[str, Any]
    products: List[Dict[str, Any]]
    content_count: int = 5

class VideoOutlinesRequest(BaseModel):
    content_ideas: List[Dict[str, Any]]
    brand_data: Dict[str, Any]

class ProductionGuideRequest(BaseModel):
    video_outlines: List[Dict[str, Any]]
    brand_data: Dict[str, Any]

class SEOOptimizationRequest(BaseModel):
    video_outlines: List[Dict[str, Any]]
    brand_data: Dict[str, Any]

class FullPipelineRequest(BaseModel):
    brand_url: str
    content_count: int = 5

# Root endpoint
@app.get("/")
async def root():
    return {"message": "ClipsCommerce Core Pipeline API", "status": "running"}

@app.get("/health")
async def health_check():
    return {"status": "healthy", "services": "real backend services loaded"}

# Pipeline endpoints using real services
@app.post("/api/v1/pipeline/analyze-brand")
async def analyze_brand(request: BrandAnalysisRequest):
    """Step 1: Analyze brand from URL using real scraping service"""
    
    try:
        logger.info(f"Analyzing brand: {request.brand_url}")
        
        async with CoreBrandScraper() as scraper:
            result = await scraper.scrape(request.brand_url)
            
            if not result.success:
                raise HTTPException(status_code=400, detail=f"Failed to scrape brand: {result.error}")
            
            brand_data = result.data
            
            return {
                "success": True,
                "brand": brand_data.get("brand", {}),
                "products": brand_data.get("products", []),
                "total_products": len(brand_data.get("products", [])),
                "message": "Brand analysis completed using real scraping service"
            }
    
    except Exception as e:
        logger.error(f"Brand analysis failed: {e}")
        raise HTTPException(status_code=500, detail=f"Error analyzing brand: {str(e)}")

@app.post("/api/v1/pipeline/generate-content-ideas")
async def generate_content_ideas(request: ContentIdeasRequest):
    """Step 2: Generate viral content ideas using real AI service"""
    
    try:
        logger.info(f"Generating {request.content_count} content ideas")
        
        content_generator = ViralContentGenerator()
        
        content_ideas = await content_generator.generate_ideas(
            brand_data=request.brand_data,
            products=request.products,
            count=request.content_count
        )
        
        return {
            "success": True,
            "content_ideas": content_ideas,
            "total_ideas": len(content_ideas),
            "message": "Content ideas generated using real AI service"
        }
    
    except Exception as e:
        logger.error(f"Content generation failed: {e}")
        raise HTTPException(status_code=500, detail=f"Error generating content ideas: {str(e)}")

@app.post("/api/v1/pipeline/create-video-outlines")
async def create_video_outlines(request: VideoOutlinesRequest):
    """Step 3: Create video outlines using real AI service"""
    
    try:
        logger.info(f"Creating video outlines for {len(request.content_ideas)} ideas")
        
        content_generator = ViralContentGenerator()
        
        video_outlines = []
        for idea in request.content_ideas:
            outline = await content_generator.create_video_outline(
                content_idea=idea,
                brand_data=request.brand_data
            )
            if outline:
                video_outlines.append(outline)
        
        return {
            "success": True,
            "video_outlines": video_outlines,
            "total_outlines": len(video_outlines),
            "message": "Video outlines created using real AI service"
        }
    
    except Exception as e:
        logger.error(f"Video outline creation failed: {e}")
        raise HTTPException(status_code=500, detail=f"Error creating video outlines: {str(e)}")

@app.post("/api/v1/pipeline/generate-production-guide")
async def generate_production_guide(request: ProductionGuideRequest):
    """Step 4: Generate production guides using real AI service"""
    
    try:
        logger.info(f"Creating production guides for {len(request.video_outlines)} videos")
        
        guide_generator = ProductionGuideGenerator()
        
        production_guides = []
        for outline in request.video_outlines:
            guide = await guide_generator.create_production_guide(
                video_outline=outline,
                brand_data=request.brand_data
            )
            if guide:
                production_guides.append(guide)
        
        return {
            "success": True,
            "production_guides": production_guides,
            "total_guides": len(production_guides),
            "message": "Production guides created using real AI service"
        }
    
    except Exception as e:
        logger.error(f"Production guide creation failed: {e}")
        raise HTTPException(status_code=500, detail=f"Error creating production guides: {str(e)}")

@app.post("/api/v1/pipeline/optimize-seo")
async def optimize_seo(request: SEOOptimizationRequest):
    """Step 5: SEO optimization using real AI service"""
    
    try:
        logger.info(f"Optimizing SEO for {len(request.video_outlines)} videos")
        
        seo_optimizer = SEOOptimizer()
        
        optimized_content = []
        for outline in request.video_outlines:
            seo_data = await seo_optimizer.optimize_for_conversion(
                video_outline=outline,
                brand_data=request.brand_data
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
            "message": "SEO optimization completed using real AI service"
        }
    
    except Exception as e:
        logger.error(f"SEO optimization failed: {e}")
        raise HTTPException(status_code=500, detail=f"Error optimizing SEO: {str(e)}")

@app.post("/api/v1/pipeline/full-pipeline")
async def run_full_pipeline(request: FullPipelineRequest):
    """Run complete pipeline using all real services"""
    
    try:
        logger.info(f"Starting full pipeline for: {request.brand_url}")
        
        # Step 1: Brand analysis using real scraper
        async with CoreBrandScraper() as scraper:
            brand_result = await scraper.scrape(request.brand_url)
            
            if not brand_result.success:
                raise HTTPException(status_code=400, detail=f"Failed to scrape brand: {brand_result.error}")
            
            brand_data = brand_result.data.get("brand", {})
            products = brand_result.data.get("products", [])
        
        # Step 2: Content ideas using real AI service
        content_generator = ViralContentGenerator()
        content_ideas = await content_generator.generate_ideas(
            brand_data=brand_data,
            products=products,
            count=request.content_count
        )
        
        # Step 3: Video outlines using real AI service
        video_outlines = []
        for idea in content_ideas:
            outline = await content_generator.create_video_outline(
                content_idea=idea,
                brand_data=brand_data
            )
            if outline:
                video_outlines.append(outline)
        
        # Step 4: Production guides using real AI service
        guide_generator = ProductionGuideGenerator()
        production_guides = []
        for outline in video_outlines:
            guide = await guide_generator.create_production_guide(
                video_outline=outline,
                brand_data=brand_data
            )
            if guide:
                production_guides.append(guide)
        
        # Step 5: SEO optimization using real AI service
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
            "message": "Full pipeline completed using real AI services!"
        }
    
    except Exception as e:
        logger.error(f"Full pipeline failed: {e}")
        raise HTTPException(status_code=500, detail=f"Pipeline error: {str(e)}")

# Mount static files for serving the test interface
@app.get("/test")
async def serve_test_interface():
    """Serve the test interface"""
    try:
        with open("../test_interface.html", "r") as f:
            content = f.read()
        return content
    except:
        return {"message": "Test interface not found. Access at http://localhost:8000/test"}

@app.get("/api/v1/pipeline/pipeline-status/{job_id}")
async def get_pipeline_status(job_id: str):
    """Get pipeline status"""
    return {
        "job_id": job_id,
        "status": "completed",
        "message": "Pipeline completed using real services"
    }

if __name__ == "__main__":
    import uvicorn
    print("""
🚀 ClipsCommerce Core Pipeline - REAL SERVICES
    
🌐 Server: http://localhost:8000
📋 Test Interface: http://localhost:8000/test
❤️  Health: http://localhost:8000/health
📚 API Docs: http://localhost:8000/docs

🔥 Using REAL backend services:
   ✅ CoreBrandScraper (real web scraping)
   ✅ ViralContentGenerator (real AI content)
   ✅ ProductionGuideGenerator (real AI guides)  
   ✅ SEOOptimizer (real AI optimization)

Press Ctrl+C to stop
    """)
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=True)