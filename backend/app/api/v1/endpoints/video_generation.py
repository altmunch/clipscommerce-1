"""
API endpoints for video generation workflows
"""

import logging
from typing import Dict, Any, List, Optional
from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks, Query
from pydantic import BaseModel, Field
from enum import Enum

from app.models.product import Product
from app.models.brand import Brand
from app.services.video_generation.orchestrator import (
    VideoGenerationOrchestrator, VideoGenerationRequest, WorkflowType,
    get_video_generation_orchestrator
)
from app.services.video_generation.script_generation import ScriptType, ToneStyle
from app.services.video_generation.ugc_generation import TestimonialType, AuthenticityLevel
from app.models.video_project import VideoQualityEnum, VideoStyleEnum

logger = logging.getLogger(__name__)

router = APIRouter()


# Request/Response Models

class VideoGenerationRequestModel(BaseModel):
    """API model for video generation request"""
    workflow_type: str = Field(..., description="Type of video workflow")
    product_id: str = Field(..., description="Product ID to create video for")
    brand_id: Optional[str] = Field(None, description="Brand ID (optional)")
    
    # Video configuration
    target_platform: str = Field("tiktok", description="Target platform (tiktok, instagram, youtube_shorts)")
    target_duration: float = Field(30.0, ge=5.0, le=300.0, description="Target duration in seconds")
    video_style: str = Field("professional", description="Video style")
    video_quality: str = Field("high", description="Video quality")
    aspect_ratio: str = Field("9:16", description="Video aspect ratio")
    
    # Content configuration
    script_type: str = Field("product_showcase", description="Type of script to generate")
    tone_style: str = Field("energetic", description="Tone and style of content")
    target_audience: str = Field("general", description="Target audience")
    key_messages: List[str] = Field(default_factory=list, description="Key messages to include")
    
    # UGC specific
    reviews: List[Dict[str, Any]] = Field(default_factory=list, description="Review data for UGC")
    testimonial_type: str = Field("product_review", description="Type of testimonial")
    authenticity_level: str = Field("moderately_authentic", description="Authenticity level")
    
    # Technical preferences
    preferred_providers: Dict[str, str] = Field(default_factory=dict, description="Preferred AI providers")
    voice_id: Optional[str] = Field(None, description="Voice ID for TTS")
    language: str = Field("en", description="Content language")
    
    # Advanced options
    include_broll: bool = Field(True, description="Include B-roll footage")
    include_music: bool = Field(True, description="Include background music")
    include_captions: bool = Field(True, description="Include captions")


class VideoGenerationResponseModel(BaseModel):
    """API model for video generation response"""
    project_id: str
    status: str
    final_video_url: Optional[str]
    preview_url: Optional[str]
    thumbnail_url: Optional[str]
    total_duration: float
    actual_cost: float
    generation_time: float
    estimated_engagement_score: float
    viral_potential_score: float
    conversion_likelihood: float
    generation_metadata: Dict[str, Any]


class ProjectStatusResponseModel(BaseModel):
    """API model for project status response"""
    project_id: str
    status: str
    progress_percentage: float
    total_segments: int
    completed_segments: int
    estimated_completion: Optional[float]
    cost_so_far: float


class UGCBatchRequestModel(BaseModel):
    """API model for batch UGC generation"""
    product_id: str
    brand_id: Optional[str] = None
    reviews: List[Dict[str, Any]] = Field(..., min_items=1, max_items=10)
    testimonial_type: str = Field("product_review")
    authenticity_level: str = Field("moderately_authentic")
    target_duration: float = Field(30.0, ge=10.0, le=60.0)
    target_audience: str = Field("general")
    avatar_preferences: Dict[str, Any] = Field(default_factory=dict)


class ScriptGenerationRequestModel(BaseModel):
    """API model for standalone script generation"""
    product_id: str
    brand_id: Optional[str] = None
    script_type: str = Field("product_showcase")
    tone_style: str = Field("energetic")
    platform: str = Field("tiktok")
    target_duration: float = Field(30.0, ge=5.0, le=300.0)
    target_audience: str = Field("general")
    key_messages: List[str] = Field(default_factory=list)


class ScriptGenerationResponseModel(BaseModel):
    """API model for script generation response"""
    title: str
    description: str
    script_type: str
    tone_style: str
    platform: str
    target_duration: float
    hook: str
    segments: List[Dict[str, Any]]
    closing_cta: str
    hashtags: List[str]
    music_suggestions: List[str]
    estimated_engagement_score: float
    viral_potential_score: float
    conversion_likelihood: float
    total_word_count: int
    actual_duration: float


# Dependencies

async def get_product(product_id: str) -> Product:
    """Get product by ID"""
    # Mock implementation - in production would query database
    return Product(
        id=product_id,
        name="Sample Product",
        description="High-quality product description",
        price=99.99,
        category="electronics",
        images=["https://example.com/product1.jpg"],
        discount=10.0
    )


async def get_brand(brand_id: str) -> Brand:
    """Get brand by ID"""
    # Mock implementation - in production would query database
    return Brand(
        id=brand_id,
        name="Sample Brand",
        brand_guidelines={
            "colors": {"primary": "#FF6B35", "secondary": "#F7931E"},
            "fonts": {"primary": "Arial", "secondary": "Helvetica"},
            "voice": "friendly",
            "tone": "professional"
        }
    )


def validate_workflow_type(workflow_type: str) -> WorkflowType:
    """Validate and convert workflow type"""
    try:
        return WorkflowType(workflow_type)
    except ValueError:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid workflow type. Must be one of: {[wt.value for wt in WorkflowType]}"
        )


def validate_enum_field(value: str, enum_class, field_name: str):
    """Validate enum field"""
    try:
        return enum_class(value)
    except ValueError:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid {field_name}. Must be one of: {[e.value for e in enum_class]}"
        )


# API Endpoints

@router.post("/generate", response_model=VideoGenerationResponseModel)
async def generate_video(
    request: VideoGenerationRequestModel,
    background_tasks: BackgroundTasks,
    orchestrator: VideoGenerationOrchestrator = Depends(get_video_generation_orchestrator)
):
    """
    Generate a video using the specified workflow
    
    Supported workflow types:
    - product_to_video: Generate product showcase videos
    - ugc_testimonial: Generate user testimonial videos from reviews
    - brand_story: Generate brand story videos
    - comparison_video: Generate product comparison videos
    - tutorial_video: Generate tutorial/how-to videos
    """
    
    try:
        # Validate workflow type
        workflow_type = validate_workflow_type(request.workflow_type)
        
        # Validate enum fields
        video_style = validate_enum_field(request.video_style, VideoStyleEnum, "video_style")
        video_quality = validate_enum_field(request.video_quality, VideoQualityEnum, "video_quality")
        script_type = validate_enum_field(request.script_type, ScriptType, "script_type")
        tone_style = validate_enum_field(request.tone_style, ToneStyle, "tone_style")
        
        # Get product and brand
        product = await get_product(request.product_id)
        brand = None
        if request.brand_id:
            brand = await get_brand(request.brand_id)
        
        # Validate UGC specific fields if needed
        testimonial_type = None
        authenticity_level = None
        if workflow_type == WorkflowType.UGC_TESTIMONIAL:
            if not request.reviews:
                raise HTTPException(
                    status_code=400,
                    detail="Reviews are required for UGC testimonial workflow"
                )
            testimonial_type = validate_enum_field(request.testimonial_type, TestimonialType, "testimonial_type")
            authenticity_level = validate_enum_field(request.authenticity_level, AuthenticityLevel, "authenticity_level")
        
        # Create orchestrator request
        orchestrator_request = VideoGenerationRequest(
            workflow_type=workflow_type,
            product=product,
            brand=brand,
            target_platform=request.target_platform,
            target_duration=request.target_duration,
            video_style=video_style,
            video_quality=video_quality,
            aspect_ratio=request.aspect_ratio,
            script_type=script_type,
            tone_style=tone_style,
            target_audience=request.target_audience,
            key_messages=request.key_messages,
            reviews=request.reviews,
            testimonial_type=testimonial_type,
            authenticity_level=authenticity_level,
            preferred_providers=request.preferred_providers,
            voice_id=request.voice_id,
            language=request.language,
            include_broll=request.include_broll,
            include_music=request.include_music,
            include_captions=request.include_captions
        )
        
        # Generate video
        result = await orchestrator.generate_video(orchestrator_request)
        
        return VideoGenerationResponseModel(
            project_id=result.project_id,
            status=result.status.value,
            final_video_url=result.final_video_url,
            preview_url=result.preview_url,
            thumbnail_url=result.thumbnail_url,
            total_duration=result.total_duration,
            actual_cost=result.actual_cost,
            generation_time=result.generation_time,
            estimated_engagement_score=result.estimated_engagement_score,
            viral_potential_score=result.viral_potential_score,
            conversion_likelihood=result.conversion_likelihood,
            generation_metadata=result.generation_metadata
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Video generation failed: {e}")
        raise HTTPException(status_code=500, detail=f"Video generation failed: {str(e)}")


@router.get("/project/{project_id}/status", response_model=ProjectStatusResponseModel)
async def get_project_status(
    project_id: str,
    orchestrator: VideoGenerationOrchestrator = Depends(get_video_generation_orchestrator)
):
    """Get the status of a video generation project"""
    
    try:
        status = await orchestrator.get_project_status(project_id)
        
        if "error" in status:
            raise HTTPException(status_code=404, detail=status["error"])
        
        return ProjectStatusResponseModel(**status)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get project status: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get project status: {str(e)}")


@router.post("/project/{project_id}/cancel")
async def cancel_project(
    project_id: str,
    orchestrator: VideoGenerationOrchestrator = Depends(get_video_generation_orchestrator)
):
    """Cancel a video generation project"""
    
    try:
        success = await orchestrator.cancel_project(project_id)
        
        if not success:
            raise HTTPException(status_code=404, detail="Project not found or cannot be cancelled")
        
        return {"message": "Project cancelled successfully", "project_id": project_id}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to cancel project: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to cancel project: {str(e)}")


@router.post("/ugc/batch")
async def generate_batch_ugc(
    request: UGCBatchRequestModel,
    background_tasks: BackgroundTasks
):
    """Generate multiple UGC testimonials from a batch of reviews"""
    
    try:
        from app.services.video_generation.ugc_generation import (
            get_ugc_generation_service, ReviewData
        )
        
        # Get product and brand
        product = await get_product(request.product_id)
        brand = None
        if request.brand_id:
            brand = await get_brand(request.brand_id)
        
        # Convert reviews to ReviewData objects
        review_data_list = []
        for review_dict in request.reviews:
            review_data = ReviewData(
                original_text=review_dict.get("text", ""),
                rating=review_dict.get("rating", 5.0),
                reviewer_name=review_dict.get("reviewer_name"),
                review_source=review_dict.get("source", "manual"),
                sentiment=review_dict.get("sentiment", "positive"),
                key_points=review_dict.get("key_points", []),
                emotions=review_dict.get("emotions", []),
                product_benefits_mentioned=review_dict.get("benefits", []),
                pain_points_addressed=review_dict.get("pain_points", []),
                credibility_score=review_dict.get("credibility_score", 0.0)
            )
            review_data_list.append(review_data)
        
        # Generate batch testimonials
        ugc_service = get_ugc_generation_service()
        
        batch_config = {
            "testimonial_type": validate_enum_field(request.testimonial_type, TestimonialType, "testimonial_type"),
            "authenticity_level": validate_enum_field(request.authenticity_level, AuthenticityLevel, "authenticity_level"),
            "target_duration": request.target_duration,
            "target_audience": request.target_audience,
            "avatar_preferences": request.avatar_preferences,
            "brand_guidelines": brand.brand_guidelines if brand else {}
        }
        
        results = await ugc_service.generate_batch_testimonials(
            product=product,
            reviews=review_data_list,
            batch_config=batch_config
        )
        
        # Convert results to API response format
        testimonials = []
        for result in results:
            testimonials.append({
                "testimonial_id": result.testimonial_id,
                "video_url": result.video_url,
                "audio_url": result.audio_url,
                "duration": result.testimonial_script.estimated_duration,
                "quality_score": result.quality_score,
                "cost": result.cost,
                "avatar_profile": result.avatar_profile.to_dict(),
                "script": result.testimonial_script.script_text
            })
        
        return {
            "batch_id": f"batch_{len(results)}_{int(time.time())}",
            "total_generated": len(results),
            "total_cost": sum(r.cost for r in results),
            "testimonials": testimonials
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Batch UGC generation failed: {e}")
        raise HTTPException(status_code=500, detail=f"Batch UGC generation failed: {str(e)}")


@router.post("/script/generate", response_model=ScriptGenerationResponseModel)
async def generate_script(
    request: ScriptGenerationRequestModel
):
    """Generate a video script without creating the actual video"""
    
    try:
        from app.services.video_generation.script_generation import (
            get_script_generation_service, ScriptGenerationRequest, PlatformOptimization
        )
        
        # Get product and brand
        product = await get_product(request.product_id)
        brand = None
        if request.brand_id:
            brand = await get_brand(request.brand_id)
        
        # Validate enum fields
        script_type = validate_enum_field(request.script_type, ScriptType, "script_type")
        tone_style = validate_enum_field(request.tone_style, ToneStyle, "tone_style")
        platform = validate_enum_field(request.platform, PlatformOptimization, "platform")
        
        # Create script generation request
        script_request = ScriptGenerationRequest(
            product=product,
            brand=brand,
            script_type=script_type,
            tone_style=tone_style,
            platform=platform,
            target_duration=request.target_duration,
            target_audience=request.target_audience,
            key_messages=request.key_messages
        )
        
        # Generate script
        script_service = get_script_generation_service()
        video_script = await script_service.generate_script(script_request)
        
        return ScriptGenerationResponseModel(
            title=video_script.title,
            description=video_script.description,
            script_type=video_script.script_type.value,
            tone_style=video_script.tone_style.value,
            platform=video_script.platform.value,
            target_duration=video_script.target_duration,
            hook=video_script.hook,
            segments=[segment.to_dict() for segment in video_script.segments],
            closing_cta=video_script.closing_cta,
            hashtags=video_script.hashtags,
            music_suggestions=video_script.music_suggestions,
            estimated_engagement_score=video_script.estimated_engagement_score,
            viral_potential_score=video_script.viral_potential_score,
            conversion_likelihood=video_script.conversion_likelihood,
            total_word_count=video_script.total_word_count,
            actual_duration=video_script.actual_duration
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Script generation failed: {e}")
        raise HTTPException(status_code=500, detail=f"Script generation failed: {str(e)}")


@router.get("/providers/status")
async def get_provider_status():
    """Get status of all AI providers"""
    
    try:
        from app.services.video_generation.base_provider import PROVIDER_REGISTRY
        
        provider_status = {}
        
        for provider_name in PROVIDER_REGISTRY.keys():
            try:
                provider = get_provider(provider_name)
                provider_status[provider_name] = {
                    "available": provider.is_healthy(),
                    "capabilities": [cap.value for cap in provider.get_supported_capabilities()],
                    "queue_status": provider.get_queue_status()
                }
            except Exception as e:
                provider_status[provider_name] = {
                    "available": False,
                    "error": str(e),
                    "capabilities": [],
                    "queue_status": {}
                }
        
        return {
            "providers": provider_status,
            "total_providers": len(PROVIDER_REGISTRY),
            "available_providers": len([p for p in provider_status.values() if p.get("available", False)])
        }
        
    except Exception as e:
        logger.error(f"Failed to get provider status: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get provider status: {str(e)}")


@router.get("/templates")
async def get_script_templates():
    """Get available script templates and configurations"""
    
    return {
        "workflow_types": [wt.value for wt in WorkflowType],
        "script_types": [st.value for st in ScriptType],
        "tone_styles": [ts.value for ts in ToneStyle],
        "video_styles": [vs.value for vs in VideoStyleEnum],
        "video_qualities": [vq.value for vq in VideoQualityEnum],
        "testimonial_types": [tt.value for tt in TestimonialType],
        "authenticity_levels": [al.value for al in AuthenticityLevel],
        "supported_platforms": ["tiktok", "instagram", "youtube_shorts", "youtube", "facebook"],
        "aspect_ratios": ["9:16", "16:9", "1:1", "4:5"],
        "languages": ["en", "es", "fr", "de", "it", "pt", "zh", "ja", "ko"]
    }


@router.post("/assets/search")
async def search_stock_assets(
    query: str = Query(..., description="Search query for stock assets"),
    asset_type: str = Query("stock_photo", description="Type of asset to search for"),
    max_results: int = Query(20, ge=1, le=50, description="Maximum number of results"),
    orientation: str = Query("any", description="Image orientation preference")
):
    """Search for stock assets (photos/videos) to use in video generation"""
    
    try:
        from app.services.video_generation.asset_management import (
            get_asset_management_service, StockAssetSearch, AssetType
        )
        
        # Validate asset type
        try:
            asset_type_enum = AssetType(asset_type)
        except ValueError:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid asset type. Must be one of: {[at.value for at in AssetType]}"
            )
        
        # Create search request
        search_request = StockAssetSearch(
            query=query,
            asset_type=asset_type_enum,
            orientation=orientation,
            max_results=max_results
        )
        
        # Search for assets
        asset_service = get_asset_management_service()
        assets = await asset_service.search_stock_assets(search_request)
        
        # Convert to API response format
        results = []
        for asset in assets:
            results.append({
                "asset_id": asset.asset_id,
                "asset_type": asset.asset_type.value,
                "url": asset.original_url,
                "dimensions": asset.dimensions,
                "quality_score": asset.quality_score.value,
                "color_palette": asset.color_palette
            })
        
        return {
            "query": query,
            "total_results": len(results),
            "assets": results
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Asset search failed: {e}")
        raise HTTPException(status_code=500, detail=f"Asset search failed: {str(e)}")


# Add time import for batch endpoint
import time