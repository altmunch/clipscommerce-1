"""
AI Provider Implementations

Concrete implementations for different AI providers (OpenAI, Anthropic)
with standardized interfaces and error handling.
"""

import asyncio
import json
import time
from typing import Any, Dict, List, Optional

import openai
import anthropic
from openai import AsyncOpenAI
from anthropic import AsyncAnthropic

from app.core.config import settings
from app.services.ai.base import (
    BaseAIService,
    AIProvider,
    AIResponse,
    AIUsageMetrics,
    AIServiceError,
    RateLimitError,
    ProviderError,
    CostOptimizer
)

import logging

logger = logging.getLogger(__name__)


class OpenAIService(BaseAIService):
    """OpenAI GPT service implementation"""
    
    def __init__(self, model: str = None):
        model = model or settings.DEFAULT_TEXT_MODEL
        super().__init__(AIProvider.OPENAI, model)
        
        if not settings.OPENAI_API_KEY:
            raise AIServiceError("OpenAI API key not configured")
        
        self.client = AsyncOpenAI(
            api_key=settings.OPENAI_API_KEY,
            timeout=settings.AI_REQUEST_TIMEOUT
        )
    
    async def _make_request(self, prompt: str, **kwargs) -> AIResponse:
        """Make request to OpenAI API"""
        try:
            # Prepare request parameters
            max_tokens = kwargs.get('max_tokens', 1000)
            temperature = kwargs.get('temperature', 0.7)
            system_prompt = kwargs.get('system_prompt', '')
            
            messages = []
            if system_prompt:
                messages.append({"role": "system", "content": system_prompt})
            messages.append({"role": "user", "content": prompt})
            
            # Make the API call
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                max_tokens=max_tokens,
                temperature=temperature,
                **{k: v for k, v in kwargs.items() 
                   if k not in ['max_tokens', 'temperature', 'system_prompt']}
            )
            
            # Extract response data
            content = response.choices[0].message.content
            usage = response.usage
            
            # Calculate cost
            input_tokens = usage.prompt_tokens
            output_tokens = usage.completion_tokens
            cost = CostOptimizer.estimate_cost("openai", self.model, input_tokens, output_tokens)
            
            # Create usage metrics
            usage_metrics = AIUsageMetrics(
                provider=self.provider,
                model=self.model,
                tokens_input=input_tokens,
                tokens_output=output_tokens,
                requests_count=1,
                total_cost=cost
            )
            
            return AIResponse(
                content=content,
                usage=usage_metrics,
                metadata={
                    "finish_reason": response.choices[0].finish_reason,
                    "model": response.model
                }
            )
            
        except openai.RateLimitError as e:
            raise RateLimitError(f"OpenAI rate limit exceeded: {e}", "openai", self.model)
        except openai.APIError as e:
            raise ProviderError(f"OpenAI API error: {e}", "openai", self.model, e)
        except Exception as e:
            raise AIServiceError(f"Unexpected OpenAI error: {e}", "openai", self.model, e)
    
    async def generate_embeddings(self, texts: List[str], model: str = None) -> List[List[float]]:
        """Generate embeddings for text inputs"""
        embedding_model = model or settings.DEFAULT_EMBEDDING_MODEL
        
        try:
            response = await self.client.embeddings.create(
                model=embedding_model,
                input=texts
            )
            
            embeddings = [item.embedding for item in response.data]
            
            # Track usage
            usage_metrics = AIUsageMetrics(
                provider=self.provider,
                model=embedding_model,
                tokens_input=response.usage.prompt_tokens,
                tokens_output=0,
                requests_count=1,
                total_cost=CostOptimizer.estimate_cost("openai", embedding_model, response.usage.prompt_tokens)
            )
            self.usage_metrics.append(usage_metrics)
            
            return embeddings
            
        except Exception as e:
            logger.error(f"Failed to generate embeddings: {e}")
            raise AIServiceError(f"Embedding generation failed: {e}", "openai", embedding_model, e)


class AnthropicService(BaseAIService):
    """Anthropic Claude service implementation"""
    
    def __init__(self, model: str = "claude-3-sonnet-20240229"):
        super().__init__(AIProvider.ANTHROPIC, model)
        
        if not settings.ANTHROPIC_API_KEY:
            raise AIServiceError("Anthropic API key not configured")
        
        self.client = AsyncAnthropic(
            api_key=settings.ANTHROPIC_API_KEY,
            timeout=settings.AI_REQUEST_TIMEOUT
        )
    
    async def _make_request(self, prompt: str, **kwargs) -> AIResponse:
        """Make request to Anthropic API"""
        try:
            max_tokens = kwargs.get('max_tokens', 1000)
            temperature = kwargs.get('temperature', 0.7)
            system_prompt = kwargs.get('system_prompt', '')
            
            # Anthropic uses a different message format
            response = await self.client.messages.create(
                model=self.model,
                max_tokens=max_tokens,
                temperature=temperature,
                system=system_prompt,
                messages=[{"role": "user", "content": prompt}]
            )
            
            content = response.content[0].text
            
            # Calculate approximate token usage (Anthropic doesn't always provide exact counts)
            input_tokens = self.token_counter.count_tokens(prompt + system_prompt, self.model)
            output_tokens = self.token_counter.count_tokens(content, self.model)
            cost = CostOptimizer.estimate_cost("anthropic", self.model, input_tokens, output_tokens)
            
            usage_metrics = AIUsageMetrics(
                provider=self.provider,
                model=self.model,
                tokens_input=input_tokens,
                tokens_output=output_tokens,
                requests_count=1,
                total_cost=cost
            )
            
            return AIResponse(
                content=content,
                usage=usage_metrics,
                metadata={
                    "stop_reason": response.stop_reason,
                    "model": response.model
                }
            )
            
        except anthropic.RateLimitError as e:
            raise RateLimitError(f"Anthropic rate limit exceeded: {e}", "anthropic", self.model)
        except anthropic.APIError as e:
            raise ProviderError(f"Anthropic API error: {e}", "anthropic", self.model, e)
        except Exception as e:
            raise AIServiceError(f"Unexpected Anthropic error: {e}", "anthropic", self.model, e)


class AIServiceFactory:
    """Factory for creating AI service instances"""
    
    @staticmethod
    def create_text_service(provider: str = None, model: str = None) -> BaseAIService:
        """Create a text generation service"""
        provider = provider or settings.DEFAULT_MODEL_PROVIDER
        
        if provider == "openai":
            return OpenAIService(model)
        elif provider == "anthropic":
            return AnthropicService(model)
        else:
            raise AIServiceError(f"Unsupported provider: {provider}")
    
    @staticmethod
    def create_embedding_service(provider: str = "openai", model: str = None) -> OpenAIService:
        """Create an embedding service (currently only OpenAI supported)"""
        if provider != "openai":
            raise AIServiceError("Only OpenAI embeddings are currently supported")
        
        model = model or settings.DEFAULT_EMBEDDING_MODEL
        return OpenAIService(model)
    
    @staticmethod
    async def create_best_available_service() -> BaseAIService:
        """Create the best available service based on health checks"""
        providers = ["openai", "anthropic"]
        
        for provider in providers:
            try:
                service = AIServiceFactory.create_text_service(provider)
                if await service.health_check():
                    logger.info(f"Using {provider} as AI service provider")
                    return service
            except Exception as e:
                logger.warning(f"Failed to create {provider} service: {e}")
        
        raise AIServiceError("No AI services are available")


class MultiProviderService:
    """Service that can failover between multiple AI providers"""
    
    def __init__(self, primary_provider: str = None, fallback_providers: List[str] = None):
        self.primary_provider = primary_provider or settings.DEFAULT_MODEL_PROVIDER
        self.fallback_providers = fallback_providers or ["openai", "anthropic"]
        self.current_service: Optional[BaseAIService] = None
    
    async def _get_service(self) -> BaseAIService:
        """Get an available AI service with fallback"""
        if self.current_service and await self.current_service.health_check():
            return self.current_service
        
        # Try primary provider first
        try:
            service = AIServiceFactory.create_text_service(self.primary_provider)
            if await service.health_check():
                self.current_service = service
                return service
        except Exception as e:
            logger.warning(f"Primary provider {self.primary_provider} failed: {e}")
        
        # Try fallback providers
        for provider in self.fallback_providers:
            if provider == self.primary_provider:
                continue
            
            try:
                service = AIServiceFactory.create_text_service(provider)
                if await service.health_check():
                    logger.info(f"Using fallback provider: {provider}")
                    self.current_service = service
                    return service
            except Exception as e:
                logger.warning(f"Fallback provider {provider} failed: {e}")
        
        raise AIServiceError("No AI providers are available")
    
    async def generate(self, prompt: str, **kwargs) -> AIResponse:
        """Generate content with automatic provider failover"""
        service = await self._get_service()
        return await service.generate(prompt, **kwargs)
    
    async def generate_embeddings(self, texts: List[str], **kwargs) -> List[List[float]]:
        """Generate embeddings (OpenAI only for now)"""
        embedding_service = AIServiceFactory.create_embedding_service()
        return await embedding_service.generate_embeddings(texts, **kwargs)
    
    def get_usage_stats(self) -> Dict[str, Any]:
        """Get usage statistics from current service"""
        if self.current_service:
            return self.current_service.get_usage_stats()
        return {}


# Global service instances
_text_service: Optional[MultiProviderService] = None
_embedding_service: Optional[OpenAIService] = None


async def get_text_service() -> MultiProviderService:
    """Get global text generation service instance"""
    global _text_service
    if _text_service is None:
        _text_service = MultiProviderService()
    return _text_service


async def get_embedding_service() -> OpenAIService:
    """Get global embedding service instance"""
    global _embedding_service
    if _embedding_service is None:
        _embedding_service = AIServiceFactory.create_embedding_service()
    return _embedding_service