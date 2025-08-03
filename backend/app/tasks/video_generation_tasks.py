"""
Celery tasks for video generation workflows
"""

import asyncio
import logging
import time
from typing import Dict, Any, List, Optional
from celery import Task, group, chain, chord

from app.core.celery_app import celery_app
from app.services.video_generation.orchestrator import (
    VideoGenerationOrchestrator, VideoGenerationRequest, WorkflowType,
    get_video_generation_orchestrator
)
from app.services.video_generation.ugc_generation import (
    UGCGenerationService, UGCGenerationRequest, ReviewData, TestimonialType,
    AuthenticityLevel, get_ugc_generation_service
)
from app.services.video_generation.script_generation import (
    ScriptGenerationService, ScriptGenerationRequest, ScriptType, ToneStyle,
    PlatformOptimization, get_script_generation_service
)
from app.services.video_generation.asset_management import (
    AssetManagementService, get_asset_management_service
)
from app.services.video_generation.video_assembly import (
    VideoAssemblyService, get_video_assembly_service
)

logger = logging.getLogger(__name__)


class CallbackTask(Task):
    """Base task with callback support"""
    
    def on_success(self, retval, task_id, args, kwargs):
        """Called on task success"""
        logger.info(f"Task {task_id} completed successfully")
        
        # Send progress update
        progress_data = {
            "task_id": task_id,
            "status": "completed",
            "result": retval,
            "completed_at": time.time()
        }
        
        # In production, you'd send this to a websocket or notification system
        self.send_progress_update(progress_data)
    
    def on_failure(self, exc, task_id, args, kwargs, einfo):
        """Called on task failure"""
        logger.error(f"Task {task_id} failed: {exc}")
        
        # Send failure notification
        failure_data = {
            "task_id": task_id,
            "status": "failed",
            "error": str(exc),
            "failed_at": time.time()
        }
        
        self.send_progress_update(failure_data)
    
    def send_progress_update(self, data: Dict[str, Any]):
        """Send progress update (implement based on your notification system)"""
        # This could send to WebSocket, Redis pub/sub, database, etc.
        logger.info(f"Progress update: {data}")


@celery_app.task(bind=True, base=CallbackTask, name="video_generation.generate_video")
def generate_video_task(self, request_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Background task for complete video generation
    """
    
    task_id = self.request.id
    logger.info(f"Starting video generation task {task_id}")
    
    try:
        # Update progress
        self.update_state(
            state="PROGRESS",
            meta={"step": "initialization", "progress": 0}
        )
        
        # Convert request data to VideoGenerationRequest
        # This is a simplified conversion - in production you'd have proper serialization
        orchestrator = get_video_generation_orchestrator()
        
        # Run async orchestrator in sync context
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        try:
            # Create request object from data
            request = create_video_generation_request_from_dict(request_data)
            
            # Update progress
            self.update_state(
                state="PROGRESS", 
                meta={"step": "script_generation", "progress": 20}
            )
            
            # Generate video
            result = loop.run_until_complete(orchestrator.generate_video(request))
            
            # Update progress
            self.update_state(
                state="PROGRESS",
                meta={"step": "completed", "progress": 100}
            )
            
            return result.to_dict()
            
        finally:
            loop.close()
    
    except Exception as e:
        logger.error(f"Video generation task {task_id} failed: {e}")
        self.update_state(
            state="FAILURE",
            meta={"error": str(e), "step": "failed"}
        )
        raise


@celery_app.task(bind=True, base=CallbackTask, name="video_generation.generate_script")
def generate_script_task(self, request_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Background task for script generation only
    """
    
    task_id = self.request.id
    logger.info(f"Starting script generation task {task_id}")
    
    try:
        self.update_state(
            state="PROGRESS",
            meta={"step": "script_analysis", "progress": 10}
        )
        
        script_service = get_script_generation_service()
        
        # Run async script generation
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        try:
            request = create_script_generation_request_from_dict(request_data)
            
            self.update_state(
                state="PROGRESS",
                meta={"step": "generating_script", "progress": 50}
            )
            
            script_result = loop.run_until_complete(
                script_service.generate_script(request)
            )
            
            self.update_state(
                state="PROGRESS",
                meta={"step": "completed", "progress": 100}
            )
            
            return script_result.to_dict()
            
        finally:
            loop.close()
    
    except Exception as e:
        logger.error(f"Script generation task {task_id} failed: {e}")
        self.update_state(
            state="FAILURE",
            meta={"error": str(e), "step": "failed"}
        )
        raise


@celery_app.task(bind=True, base=CallbackTask, name="video_generation.generate_ugc_batch")
def generate_ugc_batch_task(self, request_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Background task for batch UGC generation
    """
    
    task_id = self.request.id
    logger.info(f"Starting UGC batch generation task {task_id}")
    
    try:
        self.update_state(
            state="PROGRESS",
            meta={"step": "processing_reviews", "progress": 10}
        )
        
        ugc_service = get_ugc_generation_service()
        
        # Run async UGC generation
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        try:
            # Parse request data
            product_data = request_data["product"]
            reviews_data = request_data["reviews"]
            batch_config = request_data["batch_config"]
            
            # Create review objects
            review_objects = []
            for review_dict in reviews_data:
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
                review_objects.append(review_data)
            
            self.update_state(
                state="PROGRESS",
                meta={"step": "generating_testimonials", "progress": 30}
            )
            
            # Generate testimonials
            from app.models.product import Product
            product = Product(**product_data)
            
            results = loop.run_until_complete(
                ugc_service.generate_batch_testimonials(
                    product=product,
                    reviews=review_objects,
                    batch_config=batch_config
                )
            )
            
            self.update_state(
                state="PROGRESS",
                meta={"step": "completed", "progress": 100}
            )
            
            # Convert results to serializable format
            testimonials = []
            for result in results:
                testimonials.append(result.to_dict())
            
            return {
                "total_generated": len(testimonials),
                "total_cost": sum(r["cost"] for r in testimonials),
                "testimonials": testimonials
            }
            
        finally:
            loop.close()
    
    except Exception as e:
        logger.error(f"UGC batch generation task {task_id} failed: {e}")
        self.update_state(
            state="FAILURE",
            meta={"error": str(e), "step": "failed"}
        )
        raise


@celery_app.task(bind=True, base=CallbackTask, name="video_generation.process_product_assets")
def process_product_assets_task(self, product_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Background task for processing product assets
    """
    
    task_id = self.request.id
    logger.info(f"Starting product asset processing task {task_id}")
    
    try:
        self.update_state(
            state="PROGRESS",
            meta={"step": "downloading_assets", "progress": 20}
        )
        
        asset_service = get_asset_management_service()
        
        # Run async asset processing
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        try:
            from app.models.product import Product
            product = Product(**product_data)
            
            self.update_state(
                state="PROGRESS",
                meta={"step": "analyzing_quality", "progress": 50}
            )
            
            assets = loop.run_until_complete(
                asset_service.extract_product_assets(product)
            )
            
            self.update_state(
                state="PROGRESS",
                meta={"step": "completed", "progress": 100}
            )
            
            # Convert assets to serializable format
            asset_dicts = [asset.to_dict() for asset in assets]
            
            return {
                "product_id": str(product.id),
                "total_assets": len(asset_dicts),
                "assets": asset_dicts
            }
            
        finally:
            loop.close()
    
    except Exception as e:
        logger.error(f"Product asset processing task {task_id} failed: {e}")
        self.update_state(
            state="FAILURE",
            meta={"error": str(e), "step": "failed"}
        )
        raise


@celery_app.task(bind=True, base=CallbackTask, name="video_generation.assemble_video")
def assemble_video_task(self, project_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Background task for video assembly
    """
    
    task_id = self.request.id
    logger.info(f"Starting video assembly task {task_id}")
    
    try:
        self.update_state(
            state="PROGRESS",
            meta={"step": "preparing_timeline", "progress": 10}
        )
        
        assembly_service = get_video_assembly_service()
        
        # Run async video assembly
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        try:
            # Create project object from data
            from app.models.video_project import VideoProject
            project = VideoProject(**project_data)
            
            self.update_state(
                state="PROGRESS",
                meta={"step": "downloading_assets", "progress": 30}
            )
            
            result = loop.run_until_complete(
                assembly_service.assemble_video_project(project)
            )
            
            self.update_state(
                state="PROGRESS",
                meta={"step": "ffmpeg_processing", "progress": 80}
            )
            
            return result
            
        finally:
            loop.close()
    
    except Exception as e:
        logger.error(f"Video assembly task {task_id} failed: {e}")
        self.update_state(
            state="FAILURE",
            meta={"error": str(e), "step": "failed"}
        )
        raise


@celery_app.task(bind=True, name="video_generation.cleanup_old_projects")
def cleanup_old_projects_task(self, max_age_hours: int = 24):
    """
    Periodic task to clean up old projects and temporary files
    """
    
    task_id = self.request.id
    logger.info(f"Starting cleanup task {task_id}")
    
    try:
        # Clean up orchestrator projects
        orchestrator = get_video_generation_orchestrator()
        
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        try:
            loop.run_until_complete(
                orchestrator.cleanup_completed_projects(max_age_hours)
            )
            
            # Clean up temporary asset files
            asset_service = get_asset_management_service()
            loop.run_until_complete(
                asset_service.cleanup_temp_assets(max_age_hours)
            )
            
        finally:
            loop.close()
        
        logger.info(f"Cleanup task {task_id} completed")
        return {"status": "completed", "cleaned_hours": max_age_hours}
        
    except Exception as e:
        logger.error(f"Cleanup task {task_id} failed: {e}")
        raise


# Workflow composition tasks

@celery_app.task(name="video_generation.product_to_video_workflow")
def product_to_video_workflow(request_data: Dict[str, Any]) -> str:
    """
    Compose a complete product-to-video workflow using task chains
    """
    
    # Create a workflow chain
    workflow = chain(
        # Step 1: Process product assets
        process_product_assets_task.s(request_data["product"]),
        
        # Step 2: Generate script
        generate_script_task.s(request_data),
        
        # Step 3: Generate video segments
        generate_video_task.s(request_data),
    )
    
    # Execute workflow
    result = workflow.apply_async()
    
    return result.id


@celery_app.task(name="video_generation.multi_variant_generation")
def multi_variant_generation(base_request: Dict[str, Any], variants: List[Dict[str, Any]]) -> List[str]:
    """
    Generate multiple video variants in parallel
    """
    
    # Create parallel generation tasks
    variant_tasks = []
    
    for variant_config in variants:
        # Merge base request with variant config
        variant_request = {**base_request, **variant_config}
        
        # Create task
        task = generate_video_task.s(variant_request)
        variant_tasks.append(task)
    
    # Execute all variants in parallel
    job = group(variant_tasks)
    result = job.apply_async()
    
    return result.id


# Utility functions

def create_video_generation_request_from_dict(data: Dict[str, Any]) -> VideoGenerationRequest:
    """Create VideoGenerationRequest from dictionary data"""
    
    from app.models.product import Product
    from app.models.brand import Brand
    from app.models.video_project import VideoQualityEnum, VideoStyleEnum
    from app.services.video_generation.script_generation import ScriptType, ToneStyle
    
    # Create product object
    product = Product(**data["product"])
    
    # Create brand object if provided
    brand = None
    if data.get("brand"):
        brand = Brand(**data["brand"])
    
    # Map enum values
    workflow_type = WorkflowType(data["workflow_type"])
    video_style = VideoStyleEnum(data.get("video_style", "professional"))
    video_quality = VideoQualityEnum(data.get("video_quality", "high"))
    script_type = ScriptType(data.get("script_type", "product_showcase"))
    tone_style = ToneStyle(data.get("tone_style", "energetic"))
    
    return VideoGenerationRequest(
        workflow_type=workflow_type,
        product=product,
        brand=brand,
        target_platform=data.get("target_platform", "tiktok"),
        target_duration=data.get("target_duration", 30.0),
        video_style=video_style,
        video_quality=video_quality,
        aspect_ratio=data.get("aspect_ratio", "9:16"),
        script_type=script_type,
        tone_style=tone_style,
        target_audience=data.get("target_audience", "general"),
        key_messages=data.get("key_messages", []),
        reviews=data.get("reviews", []),
        preferred_providers=data.get("preferred_providers", {}),
        voice_id=data.get("voice_id"),
        language=data.get("language", "en"),
        include_broll=data.get("include_broll", True),
        include_music=data.get("include_music", True),
        include_captions=data.get("include_captions", True)
    )


def create_script_generation_request_from_dict(data: Dict[str, Any]) -> ScriptGenerationRequest:
    """Create ScriptGenerationRequest from dictionary data"""
    
    from app.models.product import Product
    from app.models.brand import Brand
    from app.services.video_generation.script_generation import ScriptType, ToneStyle, PlatformOptimization
    
    # Create product object
    product = Product(**data["product"])
    
    # Create brand object if provided
    brand = None
    if data.get("brand"):
        brand = Brand(**data["brand"])
    
    # Map enum values
    script_type = ScriptType(data.get("script_type", "product_showcase"))
    tone_style = ToneStyle(data.get("tone_style", "energetic"))
    platform = PlatformOptimization(data.get("platform", "tiktok"))
    
    return ScriptGenerationRequest(
        product=product,
        brand=brand,
        script_type=script_type,
        tone_style=tone_style,
        platform=platform,
        target_duration=data.get("target_duration", 30.0),
        target_audience=data.get("target_audience", "general"),
        key_messages=data.get("key_messages", [])
    )


# Periodic tasks setup

@celery_app.on_after_configure.connect
def setup_periodic_tasks(sender, **kwargs):
    """Setup periodic tasks"""
    
    # Run cleanup every 6 hours
    sender.add_periodic_task(
        21600.0,  # 6 hours in seconds
        cleanup_old_projects_task.s(),
        name="cleanup old video projects"
    )
    
    # Monitor provider health every hour
    sender.add_periodic_task(
        3600.0,  # 1 hour in seconds
        monitor_provider_health.s(),
        name="monitor AI provider health"
    )


@celery_app.task(name="video_generation.monitor_provider_health")
def monitor_provider_health():
    """Monitor AI provider health and log status"""
    
    try:
        from app.services.video_generation.base_provider import PROVIDER_REGISTRY, get_provider
        
        health_report = {}
        
        for provider_name in PROVIDER_REGISTRY.keys():
            try:
                provider = get_provider(provider_name)
                is_healthy = provider.is_healthy()
                queue_status = provider.get_queue_status()
                
                health_report[provider_name] = {
                    "healthy": is_healthy,
                    "queue_length": queue_status.get("queue_length", 0),
                    "estimated_wait_time": queue_status.get("estimated_wait_time", 0)
                }
                
                if not is_healthy:
                    logger.warning(f"Provider {provider_name} is unhealthy")
                
            except Exception as e:
                logger.error(f"Health check failed for {provider_name}: {e}")
                health_report[provider_name] = {
                    "healthy": False,
                    "error": str(e)
                }
        
        logger.info(f"Provider health report: {health_report}")
        return health_report
        
    except Exception as e:
        logger.error(f"Provider health monitoring failed: {e}")
        raise