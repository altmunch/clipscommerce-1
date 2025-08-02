"""
Base AI Service Classes

Provides abstract base classes and utilities for AI service implementations
with standardized error handling, rate limiting, and provider abstraction.
"""

import asyncio
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, List, Optional, Union, Callable
import logging
from contextlib import asynccontextmanager

import tiktoken
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
    before_sleep_log
)

from app.core.config import settings

logger = logging.getLogger(__name__)


class AIProvider(str, Enum):
    """Supported AI providers"""
    OPENAI = "openai"
    ANTHROPIC = "anthropic"


class AIModelType(str, Enum):
    """Types of AI models"""
    TEXT_GENERATION = "text_generation"
    EMBEDDING = "embedding"
    IMAGE_GENERATION = "image_generation"
    VIDEO_GENERATION = "video_generation"


@dataclass
class AIUsageMetrics:
    """Tracks AI service usage for cost optimization"""
    provider: str
    model: str
    tokens_input: int = 0
    tokens_output: int = 0
    requests_count: int = 0
    total_cost: float = 0.0
    latency_ms: int = 0
    timestamp: float = 0.0
    
    def __post_init__(self):
        if self.timestamp == 0.0:
            self.timestamp = time.time()


@dataclass
class AIResponse:
    """Standardized AI response format"""
    content: str
    usage: AIUsageMetrics
    metadata: Dict[str, Any]
    success: bool = True
    error: Optional[str] = None


class AIServiceError(Exception):
    """Base exception for AI service errors"""
    def __init__(self, message: str, provider: str = "", model: str = "", original_error: Exception = None):
        self.message = message
        self.provider = provider
        self.model = model
        self.original_error = original_error
        super().__init__(self.message)


class RateLimitError(AIServiceError):
    """Rate limit exceeded error"""
    pass


class TokenLimitError(AIServiceError):
    """Token limit exceeded error"""
    pass


class ProviderError(AIServiceError):
    """Provider-specific error"""
    pass


class TokenCounter:
    """Utility class for counting tokens across different models"""
    
    def __init__(self):
        self._encoders = {}
    
    def count_tokens(self, text: str, model: str = "gpt-4-turbo") -> int:
        """Count tokens for given text and model"""
        try:
            # Map model names to tiktoken encodings
            encoding_map = {
                "gpt-4-turbo": "cl100k_base",
                "gpt-3.5-turbo": "cl100k_base",
                "text-embedding-3-small": "cl100k_base",
                "text-embedding-3-large": "cl100k_base",
            }
            
            encoding_name = encoding_map.get(model, "cl100k_base")
            
            if encoding_name not in self._encoders:
                self._encoders[encoding_name] = tiktoken.get_encoding(encoding_name)
            
            return len(self._encoders[encoding_name].encode(text))
        
        except Exception as e:
            logger.warning(f"Failed to count tokens for model {model}: {e}")
            # Fallback: rough estimation (4 chars per token)
            return len(text) // 4


class RateLimiter:
    """Simple rate limiter for AI API calls"""
    
    def __init__(self, max_requests: int = 60, time_window: int = 60):
        self.max_requests = max_requests
        self.time_window = time_window
        self.requests = []
    
    async def acquire(self) -> bool:
        """Acquire permission to make a request"""
        current_time = time.time()
        
        # Remove old requests outside the time window
        self.requests = [req_time for req_time in self.requests 
                        if current_time - req_time < self.time_window]
        
        if len(self.requests) >= self.max_requests:
            # Calculate wait time
            oldest_request = min(self.requests)
            wait_time = self.time_window - (current_time - oldest_request)
            
            if wait_time > 0:
                logger.info(f"Rate limit reached, waiting {wait_time:.2f} seconds")
                await asyncio.sleep(wait_time)
        
        self.requests.append(current_time)
        return True


class BaseAIService(ABC):
    """Abstract base class for all AI services"""
    
    def __init__(self, provider: AIProvider, model: str):
        self.provider = provider
        self.model = model
        self.token_counter = TokenCounter()
        self.rate_limiter = RateLimiter()
        self.usage_metrics: List[AIUsageMetrics] = []
    
    @abstractmethod
    async def _make_request(self, **kwargs) -> AIResponse:
        """Make the actual API request to the AI provider"""
        pass
    
    async def validate_input(self, text: str, max_tokens: Optional[int] = None) -> bool:
        """Validate input before making AI request"""
        if not text or not text.strip():
            raise AIServiceError("Input text cannot be empty")
        
        token_count = self.token_counter.count_tokens(text, self.model)
        max_allowed = max_tokens or settings.MAX_TOKENS_PER_REQUEST
        
        if token_count > max_allowed:
            raise TokenLimitError(
                f"Input token count ({token_count}) exceeds maximum ({max_allowed})",
                provider=self.provider,
                model=self.model
            )
        
        return True
    
    @retry(
        stop=stop_after_attempt(settings.AI_MAX_RETRIES),
        wait=wait_exponential(multiplier=1, min=4, max=10),
        retry=retry_if_exception_type((RateLimitError, ProviderError)),
        before_sleep=before_sleep_log(logger, logging.INFO)
    )
    async def generate(self, prompt: str, **kwargs) -> AIResponse:
        """Generate content using the AI service with retry logic"""
        await self.validate_input(prompt)
        await self.rate_limiter.acquire()
        
        start_time = time.time()
        
        try:
            response = await self._make_request(prompt=prompt, **kwargs)
            response.usage.latency_ms = int((time.time() - start_time) * 1000)
            
            # Track usage metrics
            self.usage_metrics.append(response.usage)
            
            return response
            
        except Exception as e:
            error_msg = f"AI generation failed: {str(e)}"
            logger.error(error_msg, exc_info=True)
            
            return AIResponse(
                content="",
                usage=AIUsageMetrics(
                    provider=self.provider,
                    model=self.model,
                    latency_ms=int((time.time() - start_time) * 1000)
                ),
                metadata={},
                success=False,
                error=error_msg
            )
    
    def get_usage_stats(self) -> Dict[str, Any]:
        """Get usage statistics for cost optimization"""
        if not self.usage_metrics:
            return {}
        
        total_tokens_input = sum(m.tokens_input for m in self.usage_metrics)
        total_tokens_output = sum(m.tokens_output for m in self.usage_metrics)
        total_requests = len(self.usage_metrics)
        total_cost = sum(m.total_cost for m in self.usage_metrics)
        avg_latency = sum(m.latency_ms for m in self.usage_metrics) / total_requests
        
        return {
            "provider": self.provider,
            "model": self.model,
            "total_tokens_input": total_tokens_input,
            "total_tokens_output": total_tokens_output,
            "total_requests": total_requests,
            "total_cost": total_cost,
            "average_latency_ms": avg_latency,
            "cost_per_request": total_cost / total_requests if total_requests > 0 else 0
        }
    
    async def health_check(self) -> bool:
        """Check if the AI service is healthy and accessible"""
        try:
            test_response = await self.generate(
                "Test prompt for health check",
                max_tokens=10
            )
            return test_response.success
        except Exception as e:
            logger.error(f"Health check failed for {self.provider}: {e}")
            return False


class CostOptimizer:
    """Utilities for optimizing AI service costs"""
    
    @staticmethod
    def estimate_cost(provider: str, model: str, input_tokens: int, output_tokens: int = 0) -> float:
        """Estimate cost based on token usage"""
        # Pricing as of January 2024 (per 1K tokens)
        pricing = {
            "openai": {
                "gpt-4-turbo": {"input": 0.01, "output": 0.03},
                "gpt-3.5-turbo": {"input": 0.0015, "output": 0.002},
                "text-embedding-3-small": {"input": 0.00002, "output": 0},
                "text-embedding-3-large": {"input": 0.00013, "output": 0},
            },
            "anthropic": {
                "claude-3-sonnet": {"input": 0.003, "output": 0.015},
                "claude-3-haiku": {"input": 0.00025, "output": 0.00125},
            }
        }
        
        if provider not in pricing or model not in pricing[provider]:
            return 0.0
        
        model_pricing = pricing[provider][model]
        cost = (input_tokens / 1000) * model_pricing["input"]
        
        if output_tokens > 0 and "output" in model_pricing:
            cost += (output_tokens / 1000) * model_pricing["output"]
        
        return cost
    
    @staticmethod
    def suggest_optimization(usage_stats: Dict[str, Any]) -> List[str]:
        """Suggest cost optimization strategies"""
        suggestions = []
        
        if usage_stats.get("cost_per_request", 0) > 0.1:
            suggestions.append("Consider using a smaller model for simple tasks")
        
        if usage_stats.get("average_latency_ms", 0) > 5000:
            suggestions.append("High latency detected - consider caching frequent requests")
        
        if usage_stats.get("total_requests", 0) > 1000:
            suggestions.append("High request volume - implement request batching")
        
        return suggestions


@asynccontextmanager
async def ai_service_context(service: BaseAIService):
    """Context manager for AI service operations with cleanup"""
    try:
        yield service
    finally:
        # Log usage stats on exit
        stats = service.get_usage_stats()
        if stats:
            logger.info(f"AI service usage: {stats}")