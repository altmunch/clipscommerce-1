"""
Concrete implementations of video generation providers
"""

import json
import logging
import time
import uuid
from typing import Dict, Any, List, Optional
import asyncio
from urllib.parse import urljoin

from app.core.config import settings
from app.models.video_project import VideoQualityEnum, VideoStyleEnum, GenerationStatusEnum
from .base_provider import (
    BaseVideoProvider, 
    GenerationRequest, 
    GenerationResult, 
    ProviderCapability,
    register_provider
)

logger = logging.getLogger(__name__)


class RunwayMLProvider(BaseVideoProvider):
    """Runway ML video generation provider"""
    
    def __init__(self, api_key: Optional[str] = None):
        api_key = api_key or getattr(settings, 'RUNWAYML_API_KEY', '')
        super().__init__(api_key, "https://api.runwayml.com/v1")
        self.capabilities = [
            ProviderCapability.TEXT_TO_VIDEO,
            ProviderCapability.IMAGE_TO_VIDEO
        ]
        self.cost_per_second = 0.25  # Runway ML pricing
    
    async def generate_video(self, request: GenerationRequest) -> GenerationResult:
        """Generate video using Runway ML Gen-2"""
        if not self.api_key:
            raise ValueError("Runway ML API key not configured")
        
        # Map our quality enum to Runway's resolution options
        resolution_map = {
            VideoQualityEnum.LOW: "512x512",
            VideoQualityEnum.MEDIUM: "1024x768", 
            VideoQualityEnum.HIGH: "1920x1080",
            VideoQualityEnum.ULTRA: "2048x1536"
        }
        
        payload = {
            "text_prompt": request.prompt,
            "duration": request.duration,
            "resolution": resolution_map.get(request.quality, "1024x768"),
            "guidance_scale": 17.5,
            "watermark": False,
            **request.additional_params
        }
        
        try:
            # Submit generation request
            response = await self._make_request("POST", "/generate", payload)
            job_id = response.get("id", str(uuid.uuid4()))
            
            logger.info(f"Runway ML generation started: {job_id}")
            
            return GenerationResult(
                job_id=job_id,
                status=GenerationStatusEnum.IN_PROGRESS,
                cost=self.estimate_cost(request.duration, request.quality),
                metadata={
                    "provider": "runway_ml",
                    "model": "gen2",
                    "resolution": resolution_map.get(request.quality)
                }
            )
            
        except Exception as e:
            logger.error(f"Runway ML generation failed: {e}")
            return GenerationResult(
                job_id=str(uuid.uuid4()),
                status=GenerationStatusEnum.FAILED,
                error_message=str(e)
            )
    
    async def check_status(self, job_id: str) -> GenerationResult:
        """Check Runway ML generation status"""
        try:
            response = await self._make_request("GET", f"/tasks/{job_id}")
            
            status_map = {
                "PENDING": GenerationStatusEnum.PENDING,
                "RUNNING": GenerationStatusEnum.IN_PROGRESS,
                "SUCCEEDED": GenerationStatusEnum.COMPLETED,
                "FAILED": GenerationStatusEnum.FAILED
            }
            
            runway_status = response.get("status", "PENDING")
            status = status_map.get(runway_status, GenerationStatusEnum.PENDING)
            
            result = GenerationResult(
                job_id=job_id,
                status=status,
                metadata=response
            )
            
            if status == GenerationStatusEnum.COMPLETED:
                # Extract video URLs from response
                outputs = response.get("output", [])
                if outputs:
                    result.video_url = outputs[0]
                    result.duration = response.get("duration")
                    result.generation_time = response.get("generation_time")
            
            elif status == GenerationStatusEnum.FAILED:
                result.error_message = response.get("failure_reason", "Generation failed")
            
            return result
            
        except Exception as e:
            logger.error(f"Runway ML status check failed: {e}")
            return GenerationResult(
                job_id=job_id,
                status=GenerationStatusEnum.FAILED,
                error_message=str(e)
            )
    
    def estimate_cost(self, duration: float, quality: VideoQualityEnum) -> float:
        """Estimate Runway ML cost"""
        quality_multipliers = {
            VideoQualityEnum.LOW: 0.7,
            VideoQualityEnum.MEDIUM: 1.0,
            VideoQualityEnum.HIGH: 1.5,
            VideoQualityEnum.ULTRA: 2.5
        }
        return duration * self.cost_per_second * quality_multipliers.get(quality, 1.0)
    
    def get_supported_capabilities(self) -> List[ProviderCapability]:
        return self.capabilities


class DIDProvider(BaseVideoProvider):
    """D-ID avatar video generation provider"""
    
    def __init__(self, api_key: Optional[str] = None):
        api_key = api_key or getattr(settings, 'DID_API_KEY', '')
        super().__init__(api_key, "https://api.d-id.com")
        self.capabilities = [
            ProviderCapability.AVATAR_GENERATION,
            ProviderCapability.TEXT_TO_VIDEO
        ]
        self.cost_per_second = 0.30  # D-ID pricing
    
    async def generate_video(self, request: GenerationRequest) -> GenerationResult:
        """Generate avatar video using D-ID"""
        if not self.api_key:
            raise ValueError("D-ID API key not configured")
        
        # Extract avatar parameters
        avatar_url = request.additional_params.get("avatar_url")
        audio_url = request.additional_params.get("audio_url") 
        script_text = request.additional_params.get("script_text", request.prompt)
        
        if not avatar_url and not script_text:
            raise ValueError("D-ID requires either avatar_url or script_text")
        
        payload = {
            "script": {
                "type": "text",
                "input": script_text,
                "provider": {
                    "type": "elevenlabs",
                    "voice_id": request.additional_params.get("voice_id", "21m00Tcm4TlvDq8ikWAM")
                }
            },
            "config": {
                "fluent": True,
                "pad_audio": 0.0,
                "driver_expressions": {
                    "expressions": [
                        {"start_frame": 0, "expression": "happy", "intensity": 0.7}
                    ]
                }
            },
            "source_url": avatar_url or "https://create-images-results.d-id.com/DefaultPresenters/Noelle_f/image.jpeg"
        }
        
        try:
            response = await self._make_request("POST", "/talks", payload)
            job_id = response.get("id", str(uuid.uuid4()))
            
            logger.info(f"D-ID generation started: {job_id}")
            
            return GenerationResult(
                job_id=job_id,
                status=GenerationStatusEnum.IN_PROGRESS,
                cost=self.estimate_cost(request.duration, request.quality),
                metadata={
                    "provider": "did",
                    "avatar_url": avatar_url,
                    "created_by": response.get("created_by")
                }
            )
            
        except Exception as e:
            logger.error(f"D-ID generation failed: {e}")
            return GenerationResult(
                job_id=str(uuid.uuid4()),
                status=GenerationStatusEnum.FAILED,
                error_message=str(e)
            )
    
    async def check_status(self, job_id: str) -> GenerationResult:
        """Check D-ID generation status"""
        try:
            response = await self._make_request("GET", f"/talks/{job_id}")
            
            status_map = {
                "created": GenerationStatusEnum.PENDING,
                "started": GenerationStatusEnum.IN_PROGRESS,
                "done": GenerationStatusEnum.COMPLETED,
                "error": GenerationStatusEnum.FAILED,
                "rejected": GenerationStatusEnum.FAILED
            }
            
            did_status = response.get("status", "created")
            status = status_map.get(did_status, GenerationStatusEnum.PENDING)
            
            result = GenerationResult(
                job_id=job_id,
                status=status,
                metadata=response
            )
            
            if status == GenerationStatusEnum.COMPLETED:
                result.video_url = response.get("result_url")
                result.duration = response.get("duration")
                result.generation_time = self._calculate_generation_time(response)
            
            elif status == GenerationStatusEnum.FAILED:
                result.error_message = response.get("error", {}).get("description", "Generation failed")
            
            return result
            
        except Exception as e:
            logger.error(f"D-ID status check failed: {e}")
            return GenerationResult(
                job_id=job_id,
                status=GenerationStatusEnum.FAILED,
                error_message=str(e)
            )
    
    def _calculate_generation_time(self, response: Dict[str, Any]) -> float:
        """Calculate generation time from D-ID response"""
        created_at = response.get("created_at")
        updated_at = response.get("updated_at")
        
        if created_at and updated_at:
            # Parse timestamps and calculate difference
            # This is a simplified calculation
            return 60.0  # Default to 1 minute
        
        return 0.0
    
    def estimate_cost(self, duration: float, quality: VideoQualityEnum) -> float:
        """Estimate D-ID cost"""
        # D-ID pricing is typically per minute
        minutes = max(1, duration / 60)  # Minimum 1 minute billing
        return minutes * 3.0  # $3 per minute estimate
    
    def get_supported_capabilities(self) -> List[ProviderCapability]:
        return self.capabilities


class HeyGenProvider(BaseVideoProvider):
    """HeyGen avatar video generation provider"""
    
    def __init__(self, api_key: Optional[str] = None):
        api_key = api_key or getattr(settings, 'HEYGEN_API_KEY', '')
        super().__init__(api_key, "https://api.heygen.com/v2")
        self.capabilities = [
            ProviderCapability.AVATAR_GENERATION,
            ProviderCapability.TEXT_TO_VIDEO
        ]
        self.cost_per_second = 0.20  # HeyGen pricing
    
    async def generate_video(self, request: GenerationRequest) -> GenerationResult:
        """Generate avatar video using HeyGen"""
        if not self.api_key:
            raise ValueError("HeyGen API key not configured")
        
        avatar_id = request.additional_params.get("avatar_id", "default")
        voice_id = request.additional_params.get("voice_id", "default")
        
        payload = {
            "video_inputs": [
                {
                    "character": {
                        "type": "avatar",
                        "avatar_id": avatar_id,
                        "avatar_style": request.style.value if request.style else "normal"
                    },
                    "voice": {
                        "type": "text",
                        "input_text": request.prompt,
                        "voice_id": voice_id
                    },
                    "background": request.additional_params.get("background", {
                        "type": "color",
                        "value": "#FFFFFF"
                    })
                }
            ],
            "dimension": {
                "width": 1920 if request.quality != VideoQualityEnum.LOW else 1280,
                "height": 1080 if request.quality != VideoQualityEnum.LOW else 720
            },
            "aspect_ratio": request.additional_params.get("aspect_ratio", "16:9")
        }
        
        try:
            response = await self._make_request("POST", "/video/generate", payload)
            job_id = response.get("video_id", str(uuid.uuid4()))
            
            logger.info(f"HeyGen generation started: {job_id}")
            
            return GenerationResult(
                job_id=job_id,
                status=GenerationStatusEnum.IN_PROGRESS,
                cost=self.estimate_cost(request.duration, request.quality),
                metadata={
                    "provider": "heygen",
                    "avatar_id": avatar_id,
                    "voice_id": voice_id
                }
            )
            
        except Exception as e:
            logger.error(f"HeyGen generation failed: {e}")
            return GenerationResult(
                job_id=str(uuid.uuid4()),
                status=GenerationStatusEnum.FAILED,
                error_message=str(e)
            )
    
    async def check_status(self, job_id: str) -> GenerationResult:
        """Check HeyGen generation status"""
        try:
            response = await self._make_request("GET", f"/video/{job_id}")
            
            status_map = {
                "pending": GenerationStatusEnum.PENDING,
                "processing": GenerationStatusEnum.IN_PROGRESS,
                "completed": GenerationStatusEnum.COMPLETED,
                "failed": GenerationStatusEnum.FAILED
            }
            
            heygen_status = response.get("status", "pending")
            status = status_map.get(heygen_status, GenerationStatusEnum.PENDING)
            
            result = GenerationResult(
                job_id=job_id,
                status=status,
                metadata=response
            )
            
            if status == GenerationStatusEnum.COMPLETED:
                result.video_url = response.get("video_url")
                result.thumbnail_url = response.get("thumbnail_url")
                result.duration = response.get("duration")
            
            elif status == GenerationStatusEnum.FAILED:
                result.error_message = response.get("error_message", "Generation failed")
            
            return result
            
        except Exception as e:
            logger.error(f"HeyGen status check failed: {e}")
            return GenerationResult(
                job_id=job_id,
                status=GenerationStatusEnum.FAILED,
                error_message=str(e)
            )
    
    def estimate_cost(self, duration: float, quality: VideoQualityEnum) -> float:
        """Estimate HeyGen cost"""
        # HeyGen typically charges per credit minute
        minutes = max(1, duration / 60)
        quality_multipliers = {
            VideoQualityEnum.LOW: 1.0,
            VideoQualityEnum.MEDIUM: 1.5,
            VideoQualityEnum.HIGH: 2.0,
            VideoQualityEnum.ULTRA: 3.0
        }
        return minutes * 2.0 * quality_multipliers.get(quality, 1.5)  # $2 per minute base
    
    def get_supported_capabilities(self) -> List[ProviderCapability]:
        return self.capabilities


class SynthesiaProvider(BaseVideoProvider):
    """Synthesia AI video generation provider"""
    
    def __init__(self, api_key: Optional[str] = None):
        api_key = api_key or getattr(settings, 'SYNTHESIA_API_KEY', '')
        super().__init__(api_key, "https://api.synthesia.io/v2")
        self.capabilities = [
            ProviderCapability.AVATAR_GENERATION,
            ProviderCapability.TEXT_TO_VIDEO,
            ProviderCapability.SCRIPT_GENERATION
        ]
        self.cost_per_second = 0.35  # Synthesia pricing
    
    async def generate_video(self, request: GenerationRequest) -> GenerationResult:
        """Generate video using Synthesia"""
        if not self.api_key:
            raise ValueError("Synthesia API key not configured")
        
        avatar_id = request.additional_params.get("avatar_id", "anna_costume1_cameraA")
        
        payload = {
            "input": [
                {
                    "avatar": avatar_id,
                    "script": request.prompt,
                    "background": request.additional_params.get("background", "green_screen"),
                    "scriptText": request.prompt
                }
            ],
            "voice": request.additional_params.get("voice", "en-US-1"),
            "title": request.additional_params.get("title", "Generated Video"),
            "description": request.additional_params.get("description", "AI generated video")
        }
        
        try:
            response = await self._make_request("POST", "/videos", payload)
            job_id = response.get("id", str(uuid.uuid4()))
            
            logger.info(f"Synthesia generation started: {job_id}")
            
            return GenerationResult(
                job_id=job_id,
                status=GenerationStatusEnum.IN_PROGRESS,
                cost=self.estimate_cost(request.duration, request.quality),
                metadata={
                    "provider": "synthesia",
                    "avatar_id": avatar_id,
                    "title": payload["title"]
                }
            )
            
        except Exception as e:
            logger.error(f"Synthesia generation failed: {e}")
            return GenerationResult(
                job_id=str(uuid.uuid4()),
                status=GenerationStatusEnum.FAILED,
                error_message=str(e)
            )
    
    async def check_status(self, job_id: str) -> GenerationResult:
        """Check Synthesia generation status"""
        try:
            response = await self._make_request("GET", f"/videos/{job_id}")
            
            status_map = {
                "pending": GenerationStatusEnum.PENDING,
                "in_progress": GenerationStatusEnum.IN_PROGRESS,
                "complete": GenerationStatusEnum.COMPLETED,
                "failed": GenerationStatusEnum.FAILED
            }
            
            synthesia_status = response.get("status", "pending")
            status = status_map.get(synthesia_status, GenerationStatusEnum.PENDING)
            
            result = GenerationResult(
                job_id=job_id,
                status=status,
                metadata=response
            )
            
            if status == GenerationStatusEnum.COMPLETED:
                result.video_url = response.get("url")
                result.thumbnail_url = response.get("thumbnail")
                result.duration = response.get("duration")
            
            elif status == GenerationStatusEnum.FAILED:
                result.error_message = response.get("message", "Generation failed")
            
            return result
            
        except Exception as e:
            logger.error(f"Synthesia status check failed: {e}")
            return GenerationResult(
                job_id=job_id,
                status=GenerationStatusEnum.FAILED,
                error_message=str(e)
            )
    
    def estimate_cost(self, duration: float, quality: VideoQualityEnum) -> float:
        """Estimate Synthesia cost"""
        # Synthesia charges per minute
        minutes = max(1, duration / 60)
        return minutes * 5.0  # $5 per minute estimate
    
    def get_supported_capabilities(self) -> List[ProviderCapability]:
        return self.capabilities


class ReplicateProvider(BaseVideoProvider):
    """Replicate multi-model video generation provider"""
    
    def __init__(self, api_key: Optional[str] = None):
        api_key = api_key or getattr(settings, 'REPLICATE_API_TOKEN', '')
        super().__init__(api_key, "https://api.replicate.com/v1")
        self.capabilities = [
            ProviderCapability.TEXT_TO_VIDEO,
            ProviderCapability.IMAGE_TO_VIDEO
        ]
        self.cost_per_second = 0.15  # Replicate pricing
    
    async def generate_video(self, request: GenerationRequest) -> GenerationResult:
        """Generate video using Replicate models"""
        if not self.api_key:
            raise ValueError("Replicate API key not configured")
        
        # Select model based on request type
        model_version = request.additional_params.get(
            "model_version", 
            "zeroscope/zeroscope-v2-xl:9f747673945c62801b13b84701c783929c0ee784e4748ec062204894dda1a351"
        )
        
        payload = {
            "version": model_version,
            "input": {
                "prompt": request.prompt,
                "num_frames": int(request.duration * 24),  # Assuming 24fps
                "width": 1024 if request.quality != VideoQualityEnum.LOW else 512,
                "height": 576 if request.quality != VideoQualityEnum.LOW else 320,
                **request.additional_params.get("model_inputs", {})
            }
        }
        
        try:
            response = await self._make_request("POST", "/predictions", payload)
            job_id = response.get("id", str(uuid.uuid4()))
            
            logger.info(f"Replicate generation started: {job_id}")
            
            return GenerationResult(
                job_id=job_id,
                status=GenerationStatusEnum.IN_PROGRESS,
                cost=self.estimate_cost(request.duration, request.quality),
                metadata={
                    "provider": "replicate",
                    "model_version": model_version,
                    "num_frames": payload["input"]["num_frames"]
                }
            )
            
        except Exception as e:
            logger.error(f"Replicate generation failed: {e}")
            return GenerationResult(
                job_id=str(uuid.uuid4()),
                status=GenerationStatusEnum.FAILED,
                error_message=str(e)
            )
    
    async def check_status(self, job_id: str) -> GenerationResult:
        """Check Replicate generation status"""
        try:
            response = await self._make_request("GET", f"/predictions/{job_id}")
            
            status_map = {
                "starting": GenerationStatusEnum.PENDING,
                "processing": GenerationStatusEnum.IN_PROGRESS,
                "succeeded": GenerationStatusEnum.COMPLETED,
                "failed": GenerationStatusEnum.FAILED,
                "canceled": GenerationStatusEnum.CANCELLED
            }
            
            replicate_status = response.get("status", "starting")
            status = status_map.get(replicate_status, GenerationStatusEnum.PENDING)
            
            result = GenerationResult(
                job_id=job_id,
                status=status,
                metadata=response
            )
            
            if status == GenerationStatusEnum.COMPLETED:
                output = response.get("output")
                if isinstance(output, list) and output:
                    result.video_url = output[0]
                elif isinstance(output, str):
                    result.video_url = output
                
                # Calculate actual duration from metadata
                if "logs" in response:
                    result.generation_time = self._parse_generation_time(response["logs"])
            
            elif status == GenerationStatusEnum.FAILED:
                error = response.get("error", "Generation failed")
                result.error_message = str(error)
            
            return result
            
        except Exception as e:
            logger.error(f"Replicate status check failed: {e}")
            return GenerationResult(
                job_id=job_id,
                status=GenerationStatusEnum.FAILED,
                error_message=str(e)
            )
    
    def _parse_generation_time(self, logs: str) -> float:
        """Parse generation time from Replicate logs"""
        # This is a simplified parser - in practice you'd parse the actual log timestamps
        return 180.0  # Default 3 minutes
    
    async def cancel_generation(self, job_id: str) -> bool:
        """Cancel Replicate generation"""
        try:
            await self._make_request("POST", f"/predictions/{job_id}/cancel")
            return True
        except Exception as e:
            logger.error(f"Failed to cancel Replicate job {job_id}: {e}")
            return False
    
    def estimate_cost(self, duration: float, quality: VideoQualityEnum) -> float:
        """Estimate Replicate cost"""
        # Replicate charges per compute second
        quality_multipliers = {
            VideoQualityEnum.LOW: 0.8,
            VideoQualityEnum.MEDIUM: 1.0,
            VideoQualityEnum.HIGH: 1.8,
            VideoQualityEnum.ULTRA: 3.0
        }
        compute_time = duration * 10  # Rough estimate: 10x real-time
        return compute_time * 0.02 * quality_multipliers.get(quality, 1.0)  # $0.02 per compute second
    
    def get_supported_capabilities(self) -> List[ProviderCapability]:
        return self.capabilities


class InVideoProvider(BaseVideoProvider):
    """InVideo template-based video generation provider"""
    
    def __init__(self, api_key: Optional[str] = None):
        api_key = api_key or getattr(settings, 'INVIDEO_API_KEY', '')
        super().__init__(api_key, "https://api.invideo.io/v2")
        self.capabilities = [
            ProviderCapability.TEXT_TO_VIDEO,
            ProviderCapability.VIDEO_EDITING
        ]
        self.cost_per_second = 0.08  # InVideo pricing
    
    async def generate_video(self, request: GenerationRequest) -> GenerationResult:
        """Generate video using InVideo templates"""
        if not self.api_key:
            raise ValueError("InVideo API key not configured")
        
        template_id = request.additional_params.get("template_id", "default")
        
        payload = {
            "template_id": template_id,
            "variables": {
                "main_text": request.prompt,
                "duration": request.duration,
                "style": request.style.value if request.style else "professional"
            },
            "settings": {
                "quality": request.quality.value,
                "format": "mp4",
                "resolution": "1920x1080" if request.quality != VideoQualityEnum.LOW else "1280x720"
            }
        }
        
        try:
            response = await self._make_request("POST", "/videos", payload)
            job_id = response.get("id", str(uuid.uuid4()))
            
            logger.info(f"InVideo generation started: {job_id}")
            
            return GenerationResult(
                job_id=job_id,
                status=GenerationStatusEnum.IN_PROGRESS,
                cost=self.estimate_cost(request.duration, request.quality),
                metadata={
                    "provider": "invideo",
                    "template_id": template_id
                }
            )
            
        except Exception as e:
            logger.error(f"InVideo generation failed: {e}")
            return GenerationResult(
                job_id=str(uuid.uuid4()),
                status=GenerationStatusEnum.FAILED,
                error_message=str(e)
            )
    
    async def check_status(self, job_id: str) -> GenerationResult:
        """Check InVideo generation status"""
        try:
            response = await self._make_request("GET", f"/videos/{job_id}")
            
            status_map = {
                "queued": GenerationStatusEnum.PENDING,
                "processing": GenerationStatusEnum.IN_PROGRESS,
                "completed": GenerationStatusEnum.COMPLETED,
                "failed": GenerationStatusEnum.FAILED
            }
            
            invideo_status = response.get("status", "queued")
            status = status_map.get(invideo_status, GenerationStatusEnum.PENDING)
            
            result = GenerationResult(
                job_id=job_id,
                status=status,
                metadata=response
            )
            
            if status == GenerationStatusEnum.COMPLETED:
                result.video_url = response.get("download_url")
                result.preview_url = response.get("preview_url")
                result.thumbnail_url = response.get("thumbnail_url")
                result.duration = response.get("duration")
            
            elif status == GenerationStatusEnum.FAILED:
                result.error_message = response.get("error_message", "Generation failed")
            
            return result
            
        except Exception as e:
            logger.error(f"InVideo status check failed: {e}")
            return GenerationResult(
                job_id=job_id,
                status=GenerationStatusEnum.FAILED,
                error_message=str(e)
            )
    
    def estimate_cost(self, duration: float, quality: VideoQualityEnum) -> float:
        """Estimate InVideo cost"""
        return duration * self.cost_per_second
    
    def get_supported_capabilities(self) -> List[ProviderCapability]:
        return self.capabilities


# Register all providers
register_provider("runway_ml", RunwayMLProvider)
register_provider("did", DIDProvider)
register_provider("heygen", HeyGenProvider)
register_provider("synthesia", SynthesiaProvider)
register_provider("replicate", ReplicateProvider)
register_provider("invideo", InVideoProvider)