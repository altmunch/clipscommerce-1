"""
Base provider class for video generation services
"""

import abc
import asyncio
import logging
from typing import Dict, Any, Optional, List
from dataclasses import dataclass
from enum import Enum
import aiohttp
from tenacity import retry, stop_after_attempt, wait_exponential

from app.models.video_project import VideoQualityEnum, VideoStyleEnum, GenerationStatusEnum

logger = logging.getLogger(__name__)


class ProviderCapability(Enum):
    """Capabilities that providers can support"""
    TEXT_TO_VIDEO = "text_to_video"
    IMAGE_TO_VIDEO = "image_to_video"
    AVATAR_GENERATION = "avatar_generation"
    VOICE_CLONING = "voice_cloning"
    SCRIPT_GENERATION = "script_generation"
    BACKGROUND_REMOVAL = "background_removal"
    VIDEO_EDITING = "video_editing"


@dataclass
class GenerationRequest:
    """Standard request format for video generation"""
    prompt: str
    duration: float
    style: VideoStyleEnum
    quality: VideoQualityEnum
    additional_params: Dict[str, Any]


@dataclass 
class GenerationResult:
    """Standard result format from video generation"""
    job_id: str
    status: GenerationStatusEnum
    video_url: Optional[str] = None
    preview_url: Optional[str] = None
    thumbnail_url: Optional[str] = None
    duration: Optional[float] = None
    cost: float = 0.0
    generation_time: Optional[float] = None
    error_message: Optional[str] = None
    metadata: Dict[str, Any] = None

    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}


class BaseVideoProvider(abc.ABC):
    """Base class for all video generation providers"""
    
    def __init__(self, api_key: str, base_url: str):
        self.api_key = api_key
        self.base_url = base_url
        self.session: Optional[aiohttp.ClientSession] = None
        self.capabilities: List[ProviderCapability] = []
        self.rate_limit = 10  # requests per minute
        self.cost_per_second = 0.10  # base cost per second
        
    async def __aenter__(self):
        timeout = aiohttp.ClientTimeout(total=600)  # 10 minute timeout
        connector = aiohttp.TCPConnector(limit=10, limit_per_host=5)
        self.session = aiohttp.ClientSession(
            timeout=timeout,
            connector=connector,
            headers=self._get_default_headers()
        )
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()
    
    def _get_default_headers(self) -> Dict[str, str]:
        """Get default headers for API requests"""
        return {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "User-Agent": "ViralOS-VideoGeneration/1.0"
        }
    
    @abc.abstractmethod
    async def generate_video(self, request: GenerationRequest) -> GenerationResult:
        """Generate a video from the request"""
        pass
    
    @abc.abstractmethod
    async def check_status(self, job_id: str) -> GenerationResult:
        """Check the status of a generation job"""
        pass
    
    @abc.abstractmethod
    def estimate_cost(self, duration: float, quality: VideoQualityEnum) -> float:
        """Estimate the cost for generating a video"""
        pass
    
    @abc.abstractmethod
    def get_supported_capabilities(self) -> List[ProviderCapability]:
        """Get list of capabilities this provider supports"""
        pass
    
    async def cancel_generation(self, job_id: str) -> bool:
        """Cancel a generation job if supported"""
        logger.warning(f"Cancel not supported by {self.__class__.__name__}")
        return False
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=4, max=10)
    )
    async def _make_request(
        self, 
        method: str, 
        endpoint: str, 
        data: Optional[Dict[str, Any]] = None,
        params: Optional[Dict[str, str]] = None
    ) -> Dict[str, Any]:
        """Make HTTP request with retry logic"""
        if not self.session:
            raise RuntimeError("Session not initialized. Use async context manager.")
        
        url = f"{self.base_url.rstrip('/')}/{endpoint.lstrip('/')}"
        
        try:
            async with self.session.request(
                method=method,
                url=url,
                json=data,
                params=params
            ) as response:
                
                if response.status == 429:
                    retry_after = int(response.headers.get('Retry-After', 60))
                    logger.warning(f"Rate limited by {self.__class__.__name__}, waiting {retry_after}s")
                    await asyncio.sleep(retry_after)
                    raise aiohttp.ClientResponseError(
                        request_info=response.request_info,
                        history=response.history,
                        status=response.status,
                        message="Rate limited"
                    )
                
                response.raise_for_status()
                
                content_type = response.headers.get('Content-Type', '')
                if 'application/json' in content_type:
                    return await response.json()
                else:
                    text = await response.text()
                    return {"response": text}
                    
        except aiohttp.ClientError as e:
            logger.error(f"Request failed for {self.__class__.__name__}: {e}")
            raise
    
    def is_healthy(self) -> bool:
        """Check if the provider is healthy and available"""
        # Basic implementation - subclasses can override for health checks
        return bool(self.api_key)
    
    def get_queue_status(self) -> Dict[str, Any]:
        """Get current queue status from provider"""
        # Default implementation - providers can override
        return {
            "queue_length": 0,
            "estimated_wait_time": 0,
            "processing_capacity": 100
        }


class MockVideoProvider(BaseVideoProvider):
    """Mock provider for testing and development"""
    
    def __init__(self):
        super().__init__("mock-api-key", "https://mock-provider.com")
        self.capabilities = [
            ProviderCapability.TEXT_TO_VIDEO,
            ProviderCapability.IMAGE_TO_VIDEO
        ]
    
    async def generate_video(self, request: GenerationRequest) -> GenerationResult:
        """Mock video generation"""
        await asyncio.sleep(2)  # Simulate processing time
        
        job_id = f"mock_{hash(request.prompt + str(request.duration))}"
        
        return GenerationResult(
            job_id=job_id,
            status=GenerationStatusEnum.COMPLETED,
            video_url=f"https://mock-videos.com/{job_id}.mp4",
            preview_url=f"https://mock-videos.com/{job_id}_preview.jpg",
            thumbnail_url=f"https://mock-videos.com/{job_id}_thumb.jpg",
            duration=request.duration,
            cost=self.estimate_cost(request.duration, request.quality),
            generation_time=120.0,
            metadata={
                "provider": "mock",
                "model_version": "1.0",
                "resolution": "1920x1080" if request.quality != VideoQualityEnum.LOW else "720x480"
            }
        )
    
    async def check_status(self, job_id: str) -> GenerationResult:
        """Mock status check"""
        return GenerationResult(
            job_id=job_id,
            status=GenerationStatusEnum.COMPLETED,
            video_url=f"https://mock-videos.com/{job_id}.mp4"
        )
    
    def estimate_cost(self, duration: float, quality: VideoQualityEnum) -> float:
        """Mock cost estimation"""
        quality_multipliers = {
            VideoQualityEnum.LOW: 0.5,
            VideoQualityEnum.MEDIUM: 1.0,
            VideoQualityEnum.HIGH: 2.0,
            VideoQualityEnum.ULTRA: 4.0
        }
        return duration * self.cost_per_second * quality_multipliers.get(quality, 1.0)
    
    def get_supported_capabilities(self) -> List[ProviderCapability]:
        """Get mock capabilities"""
        return self.capabilities


# Provider registry for dynamic loading
PROVIDER_REGISTRY: Dict[str, type] = {
    "mock": MockVideoProvider
}


def register_provider(name: str, provider_class: type):
    """Register a new provider in the registry"""
    PROVIDER_REGISTRY[name] = provider_class


def get_provider(name: str, **kwargs) -> BaseVideoProvider:
    """Get a provider instance by name"""
    if name not in PROVIDER_REGISTRY:
        raise ValueError(f"Unknown provider: {name}")
    
    provider_class = PROVIDER_REGISTRY[name]
    return provider_class(**kwargs)