"""
Video Generation Orchestrator - Main service that coordinates all video generation workflows
"""

import asyncio
import logging
import time
import uuid
from typing import Dict, Any, List, Optional
from dataclasses import dataclass
from enum import Enum

from app.models.product import Product
from app.models.brand import Brand
from app.models.video_project import (
    VideoProject, VideoProjectTypeEnum, VideoQualityEnum, 
    VideoStyleEnum, GenerationStatusEnum
)

from .script_generation import (
    ScriptGenerationService, ScriptGenerationRequest, 
    ScriptType, ToneStyle, PlatformOptimization
)
from .asset_management import AssetManagementService, StockAssetSearch, AssetType
from .video_assembly import VideoAssemblyService
from .ugc_generation import (
    UGCGenerationService, UGCGenerationRequest, TestimonialType,
    AuthenticityLevel, ReviewData
)
from .providers import get_provider
from .text_to_speech import get_tts_service

logger = logging.getLogger(__name__)


class WorkflowType(Enum):
    """Types of video generation workflows"""
    PRODUCT_TO_VIDEO = "product_to_video"
    UGC_TESTIMONIAL = "ugc_testimonial"
    BRAND_STORY = "brand_story"
    COMPARISON_VIDEO = "comparison_video"
    TUTORIAL_VIDEO = "tutorial_video"


@dataclass
class VideoGenerationRequest:
    """Main request for video generation"""
    workflow_type: WorkflowType
    product: Product
    brand: Optional[Brand] = None
    
    # Video configuration
    target_platform: str = "tiktok"
    target_duration: float = 30.0
    video_style: VideoStyleEnum = VideoStyleEnum.PROFESSIONAL
    video_quality: VideoQualityEnum = VideoQualityEnum.HIGH
    aspect_ratio: str = "9:16"
    
    # Content configuration
    script_type: ScriptType = ScriptType.PRODUCT_SHOWCASE
    tone_style: ToneStyle = ToneStyle.ENERGETIC
    target_audience: str = "general"
    key_messages: List[str] = None
    
    # UGC specific
    reviews: List[Dict[str, Any]] = None
    testimonial_type: TestimonialType = TestimonialType.PRODUCT_REVIEW
    authenticity_level: AuthenticityLevel = AuthenticityLevel.MODERATELY_AUTHENTIC
    
    # Technical preferences
    preferred_providers: Dict[str, str] = None
    voice_id: Optional[str] = None
    language: str = "en"
    
    # Advanced options
    include_broll: bool = True
    include_music: bool = True
    include_captions: bool = True
    
    def __post_init__(self):
        if self.key_messages is None:
            self.key_messages = []
        if self.reviews is None:
            self.reviews = []
        if self.preferred_providers is None:
            self.preferred_providers = {}


@dataclass
class VideoGenerationResult:
    """Result of video generation process"""
    project_id: str
    status: GenerationStatusEnum
    final_video_url: Optional[str]
    preview_url: Optional[str]
    thumbnail_url: Optional[str]
    
    # Generation details
    total_duration: float
    actual_cost: float
    generation_time: float
    
    # Content details
    script_segments: List[Dict[str, Any]]
    assets_used: List[Dict[str, Any]]
    generation_metadata: Dict[str, Any]
    
    # Quality metrics
    estimated_engagement_score: float
    viral_potential_score: float
    conversion_likelihood: float
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "project_id": self.project_id,
            "status": self.status.value,
            "final_video_url": self.final_video_url,
            "preview_url": self.preview_url,
            "thumbnail_url": self.thumbnail_url,
            "total_duration": self.total_duration,
            "actual_cost": self.actual_cost,
            "generation_time": self.generation_time,
            "script_segments": self.script_segments,
            "assets_used": self.assets_used,
            "generation_metadata": self.generation_metadata,
            "estimated_engagement_score": self.estimated_engagement_score,
            "viral_potential_score": self.viral_potential_score,
            "conversion_likelihood": self.conversion_likelihood
        }


class VideoGenerationOrchestrator:
    """Main orchestrator for video generation workflows"""
    
    def __init__(self):
        self.script_service = ScriptGenerationService()
        self.asset_service = AssetManagementService()
        self.assembly_service = VideoAssemblyService()
        self.ugc_service = UGCGenerationService()
        self.tts_service = get_tts_service()
        
        # Active projects tracking
        self.active_projects: Dict[str, VideoProject] = {}
        
        # Workflow handlers
        self.workflow_handlers = {
            WorkflowType.PRODUCT_TO_VIDEO: self._handle_product_to_video,
            WorkflowType.UGC_TESTIMONIAL: self._handle_ugc_testimonial,
            WorkflowType.BRAND_STORY: self._handle_brand_story,
            WorkflowType.COMPARISON_VIDEO: self._handle_comparison_video,
            WorkflowType.TUTORIAL_VIDEO: self._handle_tutorial_video
        }
    
    async def generate_video(self, request: VideoGenerationRequest) -> VideoGenerationResult:
        """Main entry point for video generation"""
        
        logger.info(f"Starting {request.workflow_type.value} generation for product: {request.product.name}")
        
        start_time = time.time()
        
        try:
            # Create project
            project = await self._create_video_project(request)
            self.active_projects[project.id] = project
            
            # Execute workflow
            handler = self.workflow_handlers.get(request.workflow_type)
            if not handler:
                raise ValueError(f"Unsupported workflow type: {request.workflow_type}")
            
            result = await handler(request, project)
            
            # Update project status
            if result.status == GenerationStatusEnum.COMPLETED:
                project.status = GenerationStatusEnum.COMPLETED
                project.final_video_url = result.final_video_url
                project.actual_cost = result.actual_cost
                project.generation_completed_at = time.time()
            
            generation_time = time.time() - start_time
            result.generation_time = generation_time
            
            logger.info(f"Video generation completed in {generation_time:.1f}s for project {project.id}")
            
            return result
            
        except Exception as e:
            logger.error(f"Video generation failed: {e}")
            
            # Return error result
            return VideoGenerationResult(
                project_id=str(uuid.uuid4()),
                status=GenerationStatusEnum.FAILED,
                final_video_url=None,
                preview_url=None,
                thumbnail_url=None,
                total_duration=0.0,
                actual_cost=0.0,
                generation_time=time.time() - start_time,
                script_segments=[],
                assets_used=[],
                generation_metadata={"error": str(e)},
                estimated_engagement_score=0.0,
                viral_potential_score=0.0,
                conversion_likelihood=0.0
            )
    
    async def _create_video_project(self, request: VideoGenerationRequest) -> VideoProject:
        """Create video project from request"""
        
        # Map workflow to project type
        workflow_to_project_type = {
            WorkflowType.PRODUCT_TO_VIDEO: VideoProjectTypeEnum.PRODUCT_AD,
            WorkflowType.UGC_TESTIMONIAL: VideoProjectTypeEnum.UGC_TESTIMONIAL,
            WorkflowType.BRAND_STORY: VideoProjectTypeEnum.BRAND_STORY,
            WorkflowType.COMPARISON_VIDEO: VideoProjectTypeEnum.PRODUCT_AD,
            WorkflowType.TUTORIAL_VIDEO: VideoProjectTypeEnum.TUTORIAL
        }
        
        project = VideoProject(
            id=uuid.uuid4(),
            title=f"{request.workflow_type.value} - {request.product.name}",
            description=f"AI-generated {request.workflow_type.value} for {request.product.name}",
            project_type=workflow_to_project_type[request.workflow_type],
            brand_id=request.brand.id if request.brand else None,
            product_id=request.product.id,
            target_platform=request.target_platform,
            target_duration=request.target_duration,
            aspect_ratio=request.aspect_ratio,
            quality=request.video_quality,
            style=request.video_style,
            voice_id=request.voice_id,
            language=request.language,
            status=GenerationStatusEnum.PENDING,
            brand_guidelines=request.brand.brand_guidelines if request.brand else {},
            generation_config={
                "workflow_type": request.workflow_type.value,
                "script_type": request.script_type.value,
                "tone_style": request.tone_style.value,
                "target_audience": request.target_audience,
                "key_messages": request.key_messages,
                "preferred_providers": request.preferred_providers,
                "include_broll": request.include_broll,
                "include_music": request.include_music,
                "include_captions": request.include_captions
            }
        )
        
        return project
    
    async def _handle_product_to_video(
        self, 
        request: VideoGenerationRequest, 
        project: VideoProject
    ) -> VideoGenerationResult:
        """Handle product-to-video synthesis workflow"""
        
        logger.info(f"Processing product-to-video for {request.product.name}")
        
        # Step 1: Extract and process product assets
        logger.info("Step 1: Extracting product assets")
        product_assets = await self.asset_service.extract_product_assets(request.product)
        
        # Step 2: Process brand assets if available
        brand_assets = {}
        if request.brand:
            logger.info("Step 2: Processing brand assets")
            brand_assets = await self.asset_service.process_brand_assets(request.brand)
        
        # Step 3: Generate script
        logger.info("Step 3: Generating video script")
        platform_optimization = PlatformOptimization(request.target_platform)
        
        script_request = ScriptGenerationRequest(
            product=request.product,
            brand=request.brand,
            script_type=request.script_type,
            tone_style=request.tone_style,
            platform=platform_optimization,
            target_duration=request.target_duration,
            target_audience=request.target_audience,
            key_messages=request.key_messages
        )
        
        video_script = await self.script_service.generate_script(script_request)
        
        # Step 4: Search for B-roll if enabled
        broll_assets = []
        if request.include_broll:
            logger.info("Step 4: Searching for B-roll assets")
            broll_search = StockAssetSearch(
                query=f"{request.product.name} {request.product.category or ''}",
                asset_type=AssetType.STOCK_VIDEO,
                max_results=5
            )
            broll_assets = await self.asset_service.search_stock_assets(broll_search)
        
        # Step 5: Generate video segments using AI providers
        logger.info("Step 5: Generating video segments")
        video_segments = await self._generate_video_segments(
            video_script, request, project, product_assets
        )
        
        # Step 6: Generate TTS audio for segments
        logger.info("Step 6: Generating audio narration")
        await self._generate_audio_for_segments(video_segments, request)
        
        # Step 7: Assemble final video
        logger.info("Step 7: Assembling final video")
        
        # Update project with generated content
        project.video_segments = video_segments
        project.broll_clips = [self._convert_asset_to_broll(asset) for asset in broll_assets]
        project.assets = [self._convert_asset_to_video_asset(asset) for asset in product_assets + list(brand_assets.values())]
        
        assembly_result = await self.assembly_service.assemble_video_project(project)
        
        if assembly_result["status"] == "completed":
            return VideoGenerationResult(
                project_id=str(project.id),
                status=GenerationStatusEnum.COMPLETED,
                final_video_url=assembly_result["video_url"],
                preview_url=assembly_result.get("preview_url"),
                thumbnail_url=assembly_result.get("thumbnail_url"),
                total_duration=assembly_result["duration"],
                actual_cost=sum(seg.cost for seg in video_segments),
                generation_time=0.0,  # Will be set by caller
                script_segments=[seg.to_dict() for seg in video_script.segments],
                assets_used=[asset.to_dict() for asset in product_assets],
                generation_metadata={
                    "script_word_count": video_script.total_word_count,
                    "segments_generated": len(video_segments),
                    "broll_clips_used": len(broll_assets),
                    "timeline": assembly_result.get("timeline", {})
                },
                estimated_engagement_score=video_script.estimated_engagement_score,
                viral_potential_score=video_script.viral_potential_score,
                conversion_likelihood=video_script.conversion_likelihood
            )
        else:
            return VideoGenerationResult(
                project_id=str(project.id),
                status=GenerationStatusEnum.FAILED,
                final_video_url=None,
                preview_url=None,
                thumbnail_url=None,
                total_duration=0.0,
                actual_cost=0.0,
                generation_time=0.0,
                script_segments=[],
                assets_used=[],
                generation_metadata={"error": assembly_result.get("error", "Assembly failed")},
                estimated_engagement_score=0.0,
                viral_potential_score=0.0,
                conversion_likelihood=0.0
            )
    
    async def _handle_ugc_testimonial(
        self, 
        request: VideoGenerationRequest, 
        project: VideoProject
    ) -> VideoGenerationResult:
        """Handle UGC testimonial generation workflow"""
        
        logger.info(f"Processing UGC testimonial for {request.product.name}")
        
        if not request.reviews:
            raise ValueError("UGC testimonial workflow requires review data")
        
        # Convert review data
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
        
        # Generate testimonials
        testimonial_results = []
        
        for review_data in review_data_list[:3]:  # Limit to 3 testimonials
            ugc_request = UGCGenerationRequest(
                product=request.product,
                review_data=review_data,
                testimonial_type=request.testimonial_type,
                authenticity_level=request.authenticity_level,
                target_duration=request.target_duration / len(review_data_list),
                target_audience=request.target_audience,
                brand_guidelines=request.brand.brand_guidelines if request.brand else {}
            )
            
            testimonial_result = await self.ugc_service.generate_ugc_testimonial(ugc_request)
            testimonial_results.append(testimonial_result)
        
        # For simplicity, return the first testimonial result
        # In a full implementation, you might combine multiple testimonials
        if testimonial_results:
            best_testimonial = max(testimonial_results, key=lambda x: x.quality_score)
            
            return VideoGenerationResult(
                project_id=str(project.id),
                status=GenerationStatusEnum.COMPLETED,
                final_video_url=best_testimonial.video_url,
                preview_url=None,
                thumbnail_url=None,
                total_duration=best_testimonial.testimonial_script.estimated_duration,
                actual_cost=best_testimonial.cost,
                generation_time=best_testimonial.generation_time,
                script_segments=[best_testimonial.testimonial_script.to_dict()],
                assets_used=[],
                generation_metadata={
                    "testimonial_id": best_testimonial.testimonial_id,
                    "avatar_profile": best_testimonial.avatar_profile.to_dict(),
                    "authenticity_level": request.authenticity_level.value,
                    "credibility_score": best_testimonial.testimonial_script.credibility_score
                },
                estimated_engagement_score=0.8,  # UGC typically has high engagement
                viral_potential_score=0.7,
                conversion_likelihood=0.9  # Testimonials convert well
            )
        else:
            raise ValueError("Failed to generate any testimonials")
    
    async def _handle_brand_story(
        self, 
        request: VideoGenerationRequest, 
        project: VideoProject
    ) -> VideoGenerationResult:
        """Handle brand story video generation"""
        
        # For now, use the product-to-video workflow with brand story script type
        request.script_type = ScriptType.BRAND_STORY
        return await self._handle_product_to_video(request, project)
    
    async def _handle_comparison_video(
        self, 
        request: VideoGenerationRequest, 
        project: VideoProject
    ) -> VideoGenerationResult:
        """Handle product comparison video generation"""
        
        request.script_type = ScriptType.COMPARISON
        return await self._handle_product_to_video(request, project)
    
    async def _handle_tutorial_video(
        self, 
        request: VideoGenerationRequest, 
        project: VideoProject
    ) -> VideoGenerationResult:
        """Handle tutorial video generation"""
        
        request.script_type = ScriptType.TUTORIAL
        return await self._handle_product_to_video(request, project)
    
    async def _generate_video_segments(
        self,
        video_script,
        request: VideoGenerationRequest,
        project: VideoProject,
        product_assets: List
    ) -> List:
        """Generate video segments using AI providers"""
        
        from app.models.video_project import VideoSegment
        from .base_provider import GenerationRequest
        
        segments = []
        
        # Select video generation provider
        provider_name = request.preferred_providers.get("video", "runway_ml")
        provider = get_provider(provider_name)
        
        if not provider:
            logger.error(f"Video provider {provider_name} not available")
            return segments
        
        async with provider:
            for i, script_segment in enumerate(video_script.segments):
                try:
                    # Create enhanced prompt incorporating product images
                    enhanced_prompt = await self._create_enhanced_prompt(
                        script_segment, request.product, product_assets
                    )
                    
                    # Generate video segment
                    gen_request = GenerationRequest(
                        prompt=enhanced_prompt,
                        duration=script_segment.duration,
                        style=request.video_style,
                        quality=request.video_quality,
                        additional_params={
                            "product_focus": True,
                            "brand_colors": project.brand_guidelines.get("colors", {}),
                            "aspect_ratio": request.aspect_ratio
                        }
                    )
                    
                    result = await provider.generate_video(gen_request)
                    
                    # Convert to VideoSegment model
                    segment = VideoSegment(
                        id=uuid.uuid4(),
                        project_id=project.id,
                        segment_number=i + 1,
                        title=f"Segment {i + 1}",
                        start_time=script_segment.timestamp_start,
                        end_time=script_segment.timestamp_end,
                        duration=script_segment.duration,
                        prompt=enhanced_prompt,
                        style=request.video_style,
                        quality=request.video_quality,
                        provider=result.metadata.get("provider", provider_name),
                        provider_job_id=result.job_id,
                        provider_response=result.metadata,
                        status=result.status,
                        video_url=result.video_url,
                        preview_url=result.preview_url,
                        thumbnail_url=result.thumbnail_url,
                        generation_time=result.generation_time,
                        cost=result.cost,
                        has_speech=bool(script_segment.dialogue),
                        speech_text=script_segment.dialogue
                    )
                    
                    segments.append(segment)
                    
                except Exception as e:
                    logger.error(f"Failed to generate segment {i}: {e}")
                    # Continue with other segments
        
        return segments
    
    async def _create_enhanced_prompt(self, script_segment, product: Product, product_assets: List) -> str:
        """Create enhanced prompt with product and visual context"""
        
        base_prompt = script_segment.action_description
        
        # Add product context
        product_context = f"Product: {product.name}"
        if product.category:
            product_context += f", Category: {product.category}"
        
        # Add visual context from product assets
        visual_context = ""
        if product_assets:
            primary_asset = product_assets[0]  # Use highest quality asset
            colors = primary_asset.color_palette[:3] if primary_asset.color_palette else []
            if colors:
                visual_context += f"Colors: {', '.join(colors)}. "
        
        # Add brand context
        brand_context = ""
        if hasattr(script_segment, 'emotion') and script_segment.emotion:
            brand_context += f"Emotion: {script_segment.emotion}. "
        
        enhanced_prompt = f"{product_context}. {visual_context}{brand_context}{base_prompt}"
        
        return enhanced_prompt
    
    async def _generate_audio_for_segments(self, video_segments: List, request: VideoGenerationRequest):
        """Generate TTS audio for video segments"""
        
        for segment in video_segments:
            if segment.speech_text and not segment.speech_url:
                try:
                    # Generate TTS
                    voice_id = request.voice_id or "21m00Tcm4TlvDq8ikWAM"
                    
                    tts_result = await self.tts_service.generate_speech(
                        text=segment.speech_text,
                        voice_id=voice_id,
                        provider="elevenlabs"
                    )
                    
                    segment.speech_url = tts_result.audio_url
                    segment.has_speech = True
                    
                except Exception as e:
                    logger.error(f"Failed to generate TTS for segment {segment.id}: {e}")
    
    def _convert_asset_to_broll(self, asset) -> 'BRollClip':
        """Convert AssetMetadata to BRollClip model"""
        from app.models.video_project import BRollClip
        
        return BRollClip(
            id=uuid.uuid4(),
            title=asset.asset_id,
            description=f"Stock {asset.asset_type.value}",
            duration=10.0,  # Default duration for stock assets
            source="stock",
            source_provider="stock_api",
            license_type="royalty_free",
            video_url=asset.original_url,
            thumbnail_url=asset.processed_url,
            resolution=f"{asset.dimensions[0]}x{asset.dimensions[1]}",
            format=asset.format,
            cost=5.0  # Default stock asset cost
        )
    
    def _convert_asset_to_video_asset(self, asset) -> 'VideoAsset':
        """Convert AssetMetadata to VideoAsset model"""
        from app.models.video_project import VideoAsset
        
        return VideoAsset(
            id=uuid.uuid4(),
            name=asset.asset_id,
            asset_type=asset.asset_type.value,
            category="product" if asset.asset_type.value == "product_image" else "brand",
            file_url=asset.original_url,
            processed_url=asset.processed_url,
            file_size=asset.file_size,
            mime_type=f"image/{asset.format}",
            processed=bool(asset.processed_url),
            processing_settings={
                "applied_processing": [p.value for p in asset.processing_applied],
                "quality_score": asset.quality_score.value,
                "color_palette": asset.color_palette
            }
        )
    
    async def get_project_status(self, project_id: str) -> Dict[str, Any]:
        """Get status of active video generation project"""
        
        project = self.active_projects.get(project_id)
        if not project:
            return {"error": "Project not found"}
        
        # Calculate progress
        total_segments = len(project.video_segments) if project.video_segments else 0
        completed_segments = sum(
            1 for seg in project.video_segments 
            if seg.status == GenerationStatusEnum.COMPLETED
        ) if project.video_segments else 0
        
        progress_percentage = (completed_segments / total_segments * 100) if total_segments > 0 else 0
        
        return {
            "project_id": str(project.id),
            "status": project.status.value,
            "progress_percentage": progress_percentage,
            "total_segments": total_segments,
            "completed_segments": completed_segments,
            "estimated_completion": project.estimated_completion_time,
            "cost_so_far": project.actual_cost
        }
    
    async def cancel_project(self, project_id: str) -> bool:
        """Cancel active video generation project"""
        
        project = self.active_projects.get(project_id)
        if not project:
            return False
        
        # Update project status
        project.status = GenerationStatusEnum.CANCELLED
        
        # TODO: Cancel any ongoing AI provider jobs
        
        logger.info(f"Cancelled project {project_id}")
        return True
    
    async def cleanup_completed_projects(self, max_age_hours: int = 24):
        """Clean up completed projects older than specified hours"""
        
        current_time = time.time()
        max_age_seconds = max_age_hours * 3600
        
        projects_to_remove = []
        
        for project_id, project in self.active_projects.items():
            if project.status in [GenerationStatusEnum.COMPLETED, GenerationStatusEnum.FAILED]:
                if hasattr(project, 'generation_completed_at') and project.generation_completed_at:
                    age = current_time - project.generation_completed_at
                    if age > max_age_seconds:
                        projects_to_remove.append(project_id)
        
        for project_id in projects_to_remove:
            del self.active_projects[project_id]
        
        logger.info(f"Cleaned up {len(projects_to_remove)} completed projects")
    
    async def trigger_auto_posting(self, project_id: str, db_session, posting_config: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Trigger automatic social media posting for a completed video project"""
        
        try:
            from app.services.social_media.video_pipeline_integration import VideoPipelineIntegration
            
            # Initialize video pipeline integration
            integration = VideoPipelineIntegration(db_session)
            
            # Convert project_id to int (assuming it's stored as int in database)
            video_project_id = int(project_id)
            
            # Auto-post the completed video
            result = await integration.auto_post_completed_video(
                video_project_id=video_project_id,
                posting_config=posting_config
            )
            
            await integration.close()
            
            logger.info(f"Auto-posting triggered for project {project_id}: {result}")
            return result
            
        except Exception as e:
            logger.error(f"Failed to trigger auto-posting for project {project_id}: {e}")
            return {
                "project_id": project_id,
                "posted": False,
                "error": str(e)
            }
    
    async def schedule_auto_posting(self, project_id: str, db_session, delay_hours: Optional[int] = None) -> Dict[str, Any]:
        """Schedule automatic posting for when video generation is completed"""
        
        try:
            from app.services.social_media.video_pipeline_integration import VideoPipelineIntegration
            
            # Initialize video pipeline integration
            integration = VideoPipelineIntegration(db_session)
            
            # Convert project_id to int
            video_project_id = int(project_id)
            
            # Schedule auto-posting
            result = await integration.schedule_auto_posting(
                video_project_id=video_project_id,
                delay_hours=delay_hours
            )
            
            await integration.close()
            
            logger.info(f"Auto-posting scheduled for project {project_id}: {result}")
            return result
            
        except Exception as e:
            logger.error(f"Failed to schedule auto-posting for project {project_id}: {e}")
            return {
                "project_id": project_id,
                "scheduled": False,
                "error": str(e)
            }


# Global service instance
_video_generation_orchestrator: Optional[VideoGenerationOrchestrator] = None


def get_video_generation_orchestrator() -> VideoGenerationOrchestrator:
    """Get global video generation orchestrator instance"""
    global _video_generation_orchestrator
    if _video_generation_orchestrator is None:
        _video_generation_orchestrator = VideoGenerationOrchestrator()
    return _video_generation_orchestrator