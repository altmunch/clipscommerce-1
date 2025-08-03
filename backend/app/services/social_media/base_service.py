"""
Base Social Media Service Classes

Provides abstract base classes and utilities for social media platform integrations
with standardized OAuth handling, rate limiting, and error management.
"""

import asyncio
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, List, Optional, Union, Callable
import logging
from contextlib import asynccontextmanager
import json
import aiohttp
from datetime import datetime, timedelta

from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
    before_sleep_log
)

from app.core.config import settings
from app.models.social_media import PlatformType, PostStatus, ContentType

logger = logging.getLogger(__name__)


class SocialMediaProvider(str, Enum):
    """Supported social media providers"""
    TIKTOK = "tiktok"
    INSTAGRAM = "instagram"
    FACEBOOK = "facebook"


class APIEndpointType(str, Enum):
    """Types of API operations"""
    AUTHENTICATION = "authentication"
    CONTENT_UPLOAD = "content_upload"
    CONTENT_PUBLISH = "content_publish"
    ANALYTICS = "analytics"
    ACCOUNT_INFO = "account_info"
    WEBHOOK = "webhook"


@dataclass
class APIUsageMetrics:
    """Tracks API usage for rate limiting and cost optimization"""
    provider: str
    endpoint_type: str
    requests_count: int = 0
    success_count: int = 0
    error_count: int = 0
    total_latency_ms: int = 0
    rate_limit_hits: int = 0
    timestamp: float = 0.0
    
    def __post_init__(self):
        if self.timestamp == 0.0:
            self.timestamp = time.time()
    
    @property
    def success_rate(self) -> float:
        """Calculate success rate percentage"""
        if self.requests_count == 0:
            return 0.0
        return (self.success_count / self.requests_count) * 100
    
    @property
    def average_latency_ms(self) -> float:
        """Calculate average latency in milliseconds"""
        if self.success_count == 0:
            return 0.0
        return self.total_latency_ms / self.success_count


@dataclass
class SocialMediaResponse:
    """Standardized social media API response format"""
    data: Dict[str, Any]
    success: bool = True
    error: Optional[str] = None
    error_code: Optional[str] = None
    rate_limit_remaining: Optional[int] = None
    rate_limit_reset: Optional[datetime] = None
    usage: Optional[APIUsageMetrics] = None
    metadata: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}


@dataclass
class PostingRequest:
    """Standardized posting request format"""
    content_type: ContentType
    media_urls: List[str]
    caption: Optional[str] = None
    hashtags: Optional[List[str]] = None
    mentions: Optional[List[str]] = None
    location_tag: Optional[str] = None
    scheduled_at: Optional[datetime] = None
    privacy_settings: Optional[Dict[str, Any]] = None
    audience_targeting: Optional[Dict[str, Any]] = None
    platform_settings: Optional[Dict[str, Any]] = None


@dataclass
class AnalyticsRequest:
    """Standardized analytics request format"""
    post_ids: Optional[List[str]] = None
    account_id: Optional[str] = None
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    metrics: Optional[List[str]] = None
    breakdown: Optional[str] = None  # daily, weekly, monthly


class SocialMediaServiceError(Exception):
    """Base exception for social media service errors"""
    def __init__(self, message: str, provider: str = "", error_code: str = "", original_error: Exception = None):
        self.message = message
        self.provider = provider
        self.error_code = error_code
        self.original_error = original_error
        super().__init__(self.message)


class AuthenticationError(SocialMediaServiceError):
    """Authentication/authorization error"""
    pass


class RateLimitError(SocialMediaServiceError):
    """Rate limit exceeded error"""
    def __init__(self, message: str, reset_time: Optional[datetime] = None, **kwargs):
        super().__init__(message, **kwargs)
        self.reset_time = reset_time


class ContentUploadError(SocialMediaServiceError):
    """Content upload error"""
    pass


class PublishingError(SocialMediaServiceError):
    """Content publishing error"""
    pass


class AnalyticsError(SocialMediaServiceError):
    """Analytics retrieval error"""
    pass


class WebhookError(SocialMediaServiceError):
    """Webhook processing error"""
    pass


class TokenManager:
    """Manages OAuth tokens with automatic refresh"""
    
    def __init__(self, provider: str):
        self.provider = provider
        self._tokens_cache: Dict[str, Dict] = {}
    
    async def get_valid_token(self, account_id: str, token_data: Dict[str, Any]) -> str:
        """Get a valid access token, refreshing if necessary"""
        access_token = token_data.get("access_token")
        refresh_token = token_data.get("refresh_token")
        expires_at = token_data.get("expires_at")
        
        if not access_token:
            raise AuthenticationError("No access token available", provider=self.provider)
        
        # Check if token is expired or about to expire (within 5 minutes)
        if expires_at:
            expires_datetime = datetime.fromisoformat(expires_at) if isinstance(expires_at, str) else expires_at
            if expires_datetime <= datetime.utcnow() + timedelta(minutes=5):
                if refresh_token:
                    return await self._refresh_token(account_id, refresh_token)
                else:
                    raise AuthenticationError("Token expired and no refresh token available", provider=self.provider)
        
        return access_token
    
    @abstractmethod
    async def _refresh_token(self, account_id: str, refresh_token: str) -> str:
        """Refresh the access token using the refresh token"""
        pass


class RateLimiter:
    """Advanced rate limiter for social media APIs"""
    
    def __init__(self, provider: str, requests_per_hour: int = 100, burst_limit: int = 10):
        self.provider = provider
        self.requests_per_hour = requests_per_hour
        self.burst_limit = burst_limit
        self.requests_log: List[float] = []
        self.burst_requests: List[float] = []
    
    async def acquire(self, endpoint_type: APIEndpointType = APIEndpointType.CONTENT_PUBLISH) -> bool:
        """Acquire permission to make a request with burst protection"""
        current_time = time.time()
        
        # Clean old requests (older than 1 hour)
        hour_ago = current_time - 3600
        self.requests_log = [req_time for req_time in self.requests_log if req_time > hour_ago]
        
        # Clean burst requests (older than 1 minute)
        minute_ago = current_time - 60
        self.burst_requests = [req_time for req_time in self.burst_requests if req_time > minute_ago]
        
        # Check hourly rate limit
        if len(self.requests_log) >= self.requests_per_hour:
            oldest_request = min(self.requests_log)
            wait_time = 3600 - (current_time - oldest_request)
            if wait_time > 0:
                logger.warning(f"Hourly rate limit reached for {self.provider}, waiting {wait_time:.2f} seconds")
                await asyncio.sleep(wait_time)
        
        # Check burst limit
        if len(self.burst_requests) >= self.burst_limit:
            oldest_burst = min(self.burst_requests)
            wait_time = 60 - (current_time - oldest_burst)
            if wait_time > 0:
                logger.info(f"Burst limit reached for {self.provider}, waiting {wait_time:.2f} seconds")
                await asyncio.sleep(wait_time)
        
        # Record the request
        self.requests_log.append(current_time)
        self.burst_requests.append(current_time)
        return True


class BaseSocialMediaService(ABC):
    """Abstract base class for all social media platform services"""
    
    def __init__(self, provider: SocialMediaProvider):
        self.provider = provider
        self.rate_limiter = RateLimiter(provider.value)
        self.token_manager = self._create_token_manager()
        self.usage_metrics: Dict[str, APIUsageMetrics] = {}
        self.session: Optional[aiohttp.ClientSession] = None
    
    @abstractmethod
    def _create_token_manager(self) -> TokenManager:
        """Create provider-specific token manager"""
        pass
    
    @abstractmethod
    async def authenticate(self, auth_code: str, redirect_uri: str) -> Dict[str, Any]:
        """Complete OAuth authentication flow"""
        pass
    
    @abstractmethod
    async def refresh_token(self, refresh_token: str) -> Dict[str, Any]:
        """Refresh access token"""
        pass
    
    @abstractmethod
    async def get_account_info(self, access_token: str) -> Dict[str, Any]:
        """Get account information"""
        pass
    
    @abstractmethod
    async def upload_media(self, access_token: str, media_file: bytes, content_type: str) -> Dict[str, Any]:
        """Upload media to the platform"""
        pass
    
    @abstractmethod
    async def publish_post(self, access_token: str, request: PostingRequest) -> Dict[str, Any]:
        """Publish content to the platform"""
        pass
    
    @abstractmethod
    async def get_analytics(self, access_token: str, request: AnalyticsRequest) -> Dict[str, Any]:
        """Get analytics data from the platform"""
        pass
    
    @abstractmethod
    async def process_webhook(self, payload: Dict[str, Any], headers: Dict[str, str]) -> Dict[str, Any]:
        """Process webhook payload from the platform"""
        pass
    
    async def _get_session(self) -> aiohttp.ClientSession:
        """Get or create HTTP session"""
        if self.session is None:
            timeout = aiohttp.ClientTimeout(total=30)
            self.session = aiohttp.ClientSession(timeout=timeout)
        return self.session
    
    async def _track_usage(self, endpoint_type: APIEndpointType, success: bool, latency_ms: int):
        """Track API usage metrics"""
        key = f"{self.provider}_{endpoint_type}"
        
        if key not in self.usage_metrics:
            self.usage_metrics[key] = APIUsageMetrics(
                provider=self.provider,
                endpoint_type=endpoint_type
            )
        
        metrics = self.usage_metrics[key]
        metrics.requests_count += 1
        
        if success:
            metrics.success_count += 1
            metrics.total_latency_ms += latency_ms
        else:
            metrics.error_count += 1
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=4, max=10),
        retry=retry_if_exception_type((RateLimitError, ConnectionError)),
        before_sleep=before_sleep_log(logger, logging.INFO)
    )
    async def _make_request(
        self,
        method: str,
        url: str,
        headers: Optional[Dict[str, str]] = None,
        data: Optional[Union[Dict, str, bytes]] = None,
        params: Optional[Dict[str, str]] = None,
        endpoint_type: APIEndpointType = APIEndpointType.CONTENT_PUBLISH
    ) -> SocialMediaResponse:
        """Make HTTP request with retry logic and error handling"""
        
        await self.rate_limiter.acquire(endpoint_type)
        
        start_time = time.time()
        success = False
        error_msg = None
        error_code = None
        
        try:
            session = await self._get_session()
            
            async with session.request(
                method=method,
                url=url,
                headers=headers,
                data=data,
                params=params
            ) as response:
                latency_ms = int((time.time() - start_time) * 1000)
                
                # Parse response
                if response.content_type == 'application/json':
                    response_data = await response.json()
                else:
                    response_data = {"content": await response.text()}
                
                # Check for rate limiting
                if response.status == 429:
                    reset_time = None
                    if 'X-RateLimit-Reset' in response.headers:
                        reset_time = datetime.fromtimestamp(int(response.headers['X-RateLimit-Reset']))
                    
                    await self._track_usage(endpoint_type, False, latency_ms)
                    raise RateLimitError(
                        f"Rate limit exceeded for {self.provider}",
                        reset_time=reset_time,
                        provider=self.provider
                    )
                
                # Check for success
                if 200 <= response.status < 300:
                    success = True
                    await self._track_usage(endpoint_type, True, latency_ms)
                    
                    return SocialMediaResponse(
                        data=response_data,
                        success=True,
                        rate_limit_remaining=response.headers.get('X-RateLimit-Remaining'),
                        rate_limit_reset=response.headers.get('X-RateLimit-Reset')
                    )
                else:
                    error_msg = f"API request failed with status {response.status}"
                    error_code = str(response.status)
                    
                    if isinstance(response_data, dict):
                        error_msg = response_data.get('error', {}).get('message', error_msg)
                        error_code = response_data.get('error', {}).get('code', error_code)
        
        except aiohttp.ClientError as e:
            error_msg = f"Network error: {str(e)}"
            error_code = "NETWORK_ERROR"
        
        except Exception as e:
            error_msg = f"Unexpected error: {str(e)}"
            error_code = "UNKNOWN_ERROR"
        
        finally:
            if not success:
                latency_ms = int((time.time() - start_time) * 1000)
                await self._track_usage(endpoint_type, False, latency_ms)
        
        return SocialMediaResponse(
            data={},
            success=False,
            error=error_msg,
            error_code=error_code
        )
    
    async def health_check(self) -> bool:
        """Check if the service is healthy and accessible"""
        try:
            # Implement a simple ping or lightweight request
            return True
        except Exception as e:
            logger.error(f"Health check failed for {self.provider}: {e}")
            return False
    
    def get_usage_stats(self) -> Dict[str, Any]:
        """Get usage statistics for monitoring and optimization"""
        stats = {}
        
        for key, metrics in self.usage_metrics.items():
            stats[key] = {
                "requests_count": metrics.requests_count,
                "success_rate": metrics.success_rate,
                "average_latency_ms": metrics.average_latency_ms,
                "rate_limit_hits": metrics.rate_limit_hits,
                "error_count": metrics.error_count
            }
        
        return stats
    
    async def close(self):
        """Clean up resources"""
        if self.session:
            await self.session.close()
            self.session = None


@asynccontextmanager
async def social_media_service_context(service: BaseSocialMediaService):
    """Context manager for social media service operations with cleanup"""
    try:
        yield service
    finally:
        await service.close()
        
        # Log usage stats on exit
        stats = service.get_usage_stats()
        if stats:
            logger.info(f"Social media service usage for {service.provider}: {stats}")