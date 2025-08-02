"""
AI Error Handling and Fallback Mechanisms

Provides comprehensive error handling, retry logic, circuit breakers,
and fallback mechanisms for all AI services to ensure reliability.
"""

import asyncio
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Type, Union
import logging
from functools import wraps
import traceback
from collections import defaultdict, deque

logger = logging.getLogger(__name__)


class ErrorType(str, Enum):
    """Types of errors in AI services"""
    API_ERROR = "api_error"
    TIMEOUT_ERROR = "timeout_error"
    RATE_LIMIT_ERROR = "rate_limit_error"
    AUTHENTICATION_ERROR = "authentication_error"
    VALIDATION_ERROR = "validation_error"
    NETWORK_ERROR = "network_error"
    SERVICE_UNAVAILABLE = "service_unavailable"
    QUOTA_EXCEEDED = "quota_exceeded"
    PROCESSING_ERROR = "processing_error"
    UNKNOWN_ERROR = "unknown_error"


class ErrorSeverity(str, Enum):
    """Error severity levels"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class FallbackStrategy(str, Enum):
    """Fallback strategies"""
    RETRY = "retry"
    ALTERNATIVE_SERVICE = "alternative_service"
    CACHED_RESPONSE = "cached_response"
    SIMPLIFIED_RESPONSE = "simplified_response"
    DEFAULT_RESPONSE = "default_response"
    MANUAL_INTERVENTION = "manual_intervention"


@dataclass
class ErrorRecord:
    """Record of an error occurrence"""
    error_id: str
    error_type: ErrorType
    severity: ErrorSeverity
    service_name: str
    operation: str
    error_message: str
    stack_trace: str
    timestamp: float = field(default_factory=time.time)
    resolved: bool = False
    fallback_used: Optional[FallbackStrategy] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "error_id": self.error_id,
            "error_type": self.error_type,
            "severity": self.severity,
            "service_name": self.service_name,
            "operation": self.operation,
            "error_message": self.error_message,
            "stack_trace": self.stack_trace,
            "timestamp": self.timestamp,
            "resolved": self.resolved,
            "fallback_used": self.fallback_used,
            "metadata": self.metadata
        }


@dataclass
class RetryConfig:
    """Configuration for retry logic"""
    max_attempts: int = 3
    base_delay: float = 1.0  # seconds
    max_delay: float = 60.0  # seconds
    exponential_base: float = 2.0
    jitter: bool = True
    retryable_errors: List[ErrorType] = field(default_factory=lambda: [
        ErrorType.NETWORK_ERROR,
        ErrorType.TIMEOUT_ERROR,
        ErrorType.SERVICE_UNAVAILABLE,
        ErrorType.RATE_LIMIT_ERROR
    ])


@dataclass
class CircuitBreakerConfig:
    """Configuration for circuit breaker"""
    failure_threshold: int = 5  # failures before opening
    recovery_timeout: float = 60.0  # seconds
    success_threshold: int = 3  # successes to close circuit
    window_size: int = 100  # sliding window size


class CircuitBreakerState(str, Enum):
    """Circuit breaker states"""
    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"


class CircuitBreaker:
    """Circuit breaker implementation"""
    
    def __init__(self, config: CircuitBreakerConfig):
        self.config = config
        self.state = CircuitBreakerState.CLOSED
        self.failure_count = 0
        self.success_count = 0
        self.last_failure_time = 0
        self.recent_calls = deque(maxlen=config.window_size)
    
    def can_execute(self) -> bool:
        """Check if operation can be executed"""
        if self.state == CircuitBreakerState.CLOSED:
            return True
        elif self.state == CircuitBreakerState.OPEN:
            # Check if recovery timeout has passed
            if time.time() - self.last_failure_time > self.config.recovery_timeout:
                self.state = CircuitBreakerState.HALF_OPEN
                self.success_count = 0
                return True
            return False
        elif self.state == CircuitBreakerState.HALF_OPEN:
            return True
        
        return False
    
    def record_success(self):
        """Record successful operation"""
        self.recent_calls.append(True)
        
        if self.state == CircuitBreakerState.HALF_OPEN:
            self.success_count += 1
            if self.success_count >= self.config.success_threshold:
                self.state = CircuitBreakerState.CLOSED
                self.failure_count = 0
    
    def record_failure(self):
        """Record failed operation"""
        self.recent_calls.append(False)
        self.failure_count += 1
        self.last_failure_time = time.time()
        
        if self.state == CircuitBreakerState.CLOSED:
            # Check failure rate in recent window
            recent_failures = sum(1 for call in self.recent_calls if not call)
            if recent_failures >= self.config.failure_threshold:
                self.state = CircuitBreakerState.OPEN
        elif self.state == CircuitBreakerState.HALF_OPEN:
            self.state = CircuitBreakerState.OPEN
    
    def get_status(self) -> Dict[str, Any]:
        """Get circuit breaker status"""
        return {
            "state": self.state,
            "failure_count": self.failure_count,
            "success_count": self.success_count,
            "last_failure_time": self.last_failure_time,
            "recent_success_rate": sum(self.recent_calls) / max(len(self.recent_calls), 1)
        }


class AIErrorHandler:
    """Main error handling service"""
    
    def __init__(self):
        self.error_history: List[ErrorRecord] = []
        self.circuit_breakers: Dict[str, CircuitBreaker] = {}
        self.fallback_handlers: Dict[str, Callable] = {}
        self.error_patterns: Dict[str, int] = defaultdict(int)
        
        # Default configurations
        self.retry_configs: Dict[str, RetryConfig] = {
            "default": RetryConfig(),
            "embedding": RetryConfig(max_attempts=2, base_delay=0.5),
            "text_generation": RetryConfig(max_attempts=3, base_delay=2.0),
            "image_generation": RetryConfig(max_attempts=2, base_delay=5.0)
        }
        
        self.circuit_breaker_configs: Dict[str, CircuitBreakerConfig] = {
            "default": CircuitBreakerConfig(),
            "critical": CircuitBreakerConfig(failure_threshold=3, recovery_timeout=30.0)
        }
    
    def classify_error(self, error: Exception, service_name: str = "") -> Tuple[ErrorType, ErrorSeverity]:
        """Classify error type and severity"""
        
        error_str = str(error).lower()
        error_type_name = type(error).__name__.lower()
        
        # API-specific errors
        if "rate limit" in error_str or "429" in error_str:
            return ErrorType.RATE_LIMIT_ERROR, ErrorSeverity.MEDIUM
        elif "unauthorized" in error_str or "401" in error_str or "api key" in error_str:
            return ErrorType.AUTHENTICATION_ERROR, ErrorSeverity.HIGH
        elif "timeout" in error_str or "timeouterror" in error_type_name:
            return ErrorType.TIMEOUT_ERROR, ErrorSeverity.MEDIUM
        elif "connection" in error_str or "network" in error_str:
            return ErrorType.NETWORK_ERROR, ErrorSeverity.MEDIUM
        elif "service unavailable" in error_str or "503" in error_str:
            return ErrorType.SERVICE_UNAVAILABLE, ErrorSeverity.HIGH
        elif "quota" in error_str or "limit exceeded" in error_str:
            return ErrorType.QUOTA_EXCEEDED, ErrorSeverity.HIGH
        elif "validation" in error_str or "invalid" in error_str:
            return ErrorType.VALIDATION_ERROR, ErrorSeverity.LOW
        elif any(code in error_str for code in ["400", "404", "422", "500", "502", "504"]):
            return ErrorType.API_ERROR, ErrorSeverity.MEDIUM
        else:
            return ErrorType.UNKNOWN_ERROR, ErrorSeverity.MEDIUM
    
    def record_error(
        self,
        error: Exception,
        service_name: str,
        operation: str,
        metadata: Dict[str, Any] = None
    ) -> ErrorRecord:
        """Record an error occurrence"""
        
        error_type, severity = self.classify_error(error, service_name)
        
        error_record = ErrorRecord(
            error_id=f"{service_name}_{operation}_{int(time.time())}_{len(self.error_history)}",
            error_type=error_type,
            severity=severity,
            service_name=service_name,
            operation=operation,
            error_message=str(error),
            stack_trace=traceback.format_exc(),
            metadata=metadata or {}
        )
        
        self.error_history.append(error_record)
        
        # Update error patterns
        pattern_key = f"{service_name}:{error_type}"
        self.error_patterns[pattern_key] += 1
        
        # Update circuit breaker
        cb_key = f"{service_name}:{operation}"
        if cb_key in self.circuit_breakers:
            self.circuit_breakers[cb_key].record_failure()
        
        logger.error(f"Error recorded: {error_record.error_id} - {error_record.error_message}")
        
        return error_record
    
    def record_success(self, service_name: str, operation: str):
        """Record successful operation"""
        cb_key = f"{service_name}:{operation}"
        if cb_key in self.circuit_breakers:
            self.circuit_breakers[cb_key].record_success()
    
    def get_circuit_breaker(self, service_name: str, operation: str, config_type: str = "default") -> CircuitBreaker:
        """Get or create circuit breaker for service operation"""
        cb_key = f"{service_name}:{operation}"
        
        if cb_key not in self.circuit_breakers:
            config = self.circuit_breaker_configs.get(config_type, self.circuit_breaker_configs["default"])
            self.circuit_breakers[cb_key] = CircuitBreaker(config)
        
        return self.circuit_breakers[cb_key]
    
    def can_execute(self, service_name: str, operation: str) -> bool:
        """Check if operation can be executed (circuit breaker check)"""
        circuit_breaker = self.get_circuit_breaker(service_name, operation)
        return circuit_breaker.can_execute()
    
    def register_fallback_handler(self, service_operation: str, handler: Callable):
        """Register fallback handler for service operation"""
        self.fallback_handlers[service_operation] = handler
    
    async def execute_with_fallback(
        self,
        operation: Callable,
        service_name: str,
        operation_name: str,
        *args,
        fallback_strategy: FallbackStrategy = FallbackStrategy.DEFAULT_RESPONSE,
        **kwargs
    ) -> Any:
        """Execute operation with fallback handling"""
        
        # Check circuit breaker
        if not self.can_execute(service_name, operation_name):
            logger.warning(f"Circuit breaker open for {service_name}:{operation_name}")
            return await self._execute_fallback(
                service_name, operation_name, FallbackStrategy.DEFAULT_RESPONSE, None, *args, **kwargs
            )
        
        try:
            # Execute operation
            if asyncio.iscoroutinefunction(operation):
                result = await operation(*args, **kwargs)
            else:
                result = operation(*args, **kwargs)
            
            # Record success
            self.record_success(service_name, operation_name)
            return result
            
        except Exception as e:
            # Record error
            error_record = self.record_error(e, service_name, operation_name)
            
            # Execute fallback
            return await self._execute_fallback(
                service_name, operation_name, fallback_strategy, error_record, *args, **kwargs
            )
    
    async def _execute_fallback(
        self,
        service_name: str,
        operation_name: str,
        strategy: FallbackStrategy,
        error_record: Optional[ErrorRecord],
        *args,
        **kwargs
    ) -> Any:
        """Execute fallback strategy"""
        
        fallback_key = f"{service_name}:{operation_name}"
        
        if strategy == FallbackStrategy.DEFAULT_RESPONSE:
            # Return service-specific default response
            defaults = self._get_default_responses()
            service_defaults = defaults.get(service_name, {})
            return service_defaults.get(operation_name, {"error": "Service temporarily unavailable", "fallback": True})
        
        elif strategy == FallbackStrategy.CACHED_RESPONSE:
            # Try to return cached response (would need cache implementation)
            logger.info(f"Attempting cached response for {fallback_key}")
            return {"error": "Cached response not implemented", "fallback": True}
        
        elif strategy == FallbackStrategy.SIMPLIFIED_RESPONSE:
            # Return simplified version of expected response
            return self._get_simplified_response(service_name, operation_name)
        
        elif fallback_key in self.fallback_handlers:
            # Use registered fallback handler
            try:
                handler = self.fallback_handlers[fallback_key]
                if asyncio.iscoroutinefunction(handler):
                    return await handler(*args, **kwargs)
                else:
                    return handler(*args, **kwargs)
            except Exception as e:
                logger.error(f"Fallback handler failed for {fallback_key}: {e}")
        
        # Update error record with fallback strategy used
        if error_record:
            error_record.fallback_used = strategy
        
        return {"error": "Service temporarily unavailable", "fallback": True, "strategy": strategy}
    
    def _get_default_responses(self) -> Dict[str, Dict[str, Any]]:
        """Get default responses for services"""
        return {
            "viral_content": {
                "generate_viral_hooks": {
                    "hooks": [
                        {"text": "You won't believe what happened next...", "viral_score": 65, "pattern": "curiosity"},
                        {"text": "This changed everything I knew about...", "viral_score": 60, "pattern": "transformation"},
                        {"text": "Everyone is doing this wrong", "viral_score": 58, "pattern": "contrarian"}
                    ],
                    "fallback": True
                }
            },
            "brand_assimilation": {
                "analyze_brand_identity": {
                    "brand_name": "Unknown Brand",
                    "industry": "General",
                    "target_audience": "General Audience",
                    "fallback": True
                }
            },
            "performance_analyzer": {
                "predict_content_performance": {
                    "predicted_engagement_rate": 0.05,
                    "predicted_reach": 10000,
                    "confidence_score": 0.3,
                    "fallback": True
                }
            }
        }
    
    def _get_simplified_response(self, service_name: str, operation_name: str) -> Dict[str, Any]:
        """Get simplified response for operation"""
        
        # Service-specific simplified responses
        simplified_responses = {
            "text_generation": {"text": "Content temporarily unavailable", "fallback": True},
            "image_generation": {"image_url": None, "error": "Image generation unavailable", "fallback": True},
            "analysis": {"analysis": "Analysis temporarily unavailable", "fallback": True}
        }
        
        # Try to match operation type
        for response_type, response in simplified_responses.items():
            if response_type in operation_name.lower():
                return response
        
        return {"result": "Simplified response", "fallback": True}
    
    def get_error_statistics(self, hours: int = 24) -> Dict[str, Any]:
        """Get error statistics for time period"""
        
        cutoff_time = time.time() - (hours * 3600)
        recent_errors = [e for e in self.error_history if e.timestamp >= cutoff_time]
        
        if not recent_errors:
            return {"total_errors": 0, "error_rate": 0.0}
        
        # Group by service
        service_errors = defaultdict(list)
        error_type_counts = defaultdict(int)
        severity_counts = defaultdict(int)
        
        for error in recent_errors:
            service_errors[error.service_name].append(error)
            error_type_counts[error.error_type] += 1
            severity_counts[error.severity] += 1
        
        # Most problematic services
        problematic_services = sorted(
            service_errors.items(),
            key=lambda x: len(x[1]),
            reverse=True
        )[:5]
        
        return {
            "time_period_hours": hours,
            "total_errors": len(recent_errors),
            "error_types": dict(error_type_counts),
            "severity_distribution": dict(severity_counts),
            "errors_by_service": {service: len(errors) for service, errors in service_errors.items()},
            "most_problematic_services": [
                {"service": service, "error_count": len(errors), "latest_error": errors[-1].to_dict()}
                for service, errors in problematic_services
            ],
            "circuit_breaker_status": {
                key: cb.get_status() for key, cb in self.circuit_breakers.items()
            }
        }
    
    def get_health_status(self) -> Dict[str, Any]:
        """Get overall system health status"""
        
        recent_errors = [e for e in self.error_history if e.timestamp >= time.time() - 3600]  # Last hour
        
        # Calculate health score
        error_count = len(recent_errors)
        critical_errors = len([e for e in recent_errors if e.severity == ErrorSeverity.CRITICAL])
        
        if critical_errors > 0:
            health_status = "critical"
            health_score = 0
        elif error_count > 10:
            health_status = "degraded"
            health_score = max(0, 100 - (error_count * 5))
        elif error_count > 5:
            health_status = "warning"
            health_score = max(50, 100 - (error_count * 10))
        else:
            health_status = "healthy"
            health_score = 100
        
        # Circuit breaker health
        open_circuits = sum(1 for cb in self.circuit_breakers.values() if cb.state == CircuitBreakerState.OPEN)
        
        return {
            "health_status": health_status,
            "health_score": health_score,
            "recent_errors_count": error_count,
            "critical_errors_count": critical_errors,
            "open_circuit_breakers": open_circuits,
            "total_circuit_breakers": len(self.circuit_breakers),
            "error_patterns": dict(self.error_patterns),
            "recommendations": self._generate_health_recommendations(recent_errors)
        }
    
    def _generate_health_recommendations(self, recent_errors: List[ErrorRecord]) -> List[str]:
        """Generate health improvement recommendations"""
        
        recommendations = []
        
        if not recent_errors:
            return ["System is healthy - no recent errors detected"]
        
        # Error type analysis
        error_types = defaultdict(int)
        for error in recent_errors:
            error_types[error.error_type] += 1
        
        # Generate recommendations based on error patterns
        if error_types[ErrorType.RATE_LIMIT_ERROR] > 3:
            recommendations.append("Consider implementing rate limiting and request queuing")
        
        if error_types[ErrorType.TIMEOUT_ERROR] > 3:
            recommendations.append("Review timeout configurations and consider increasing limits")
        
        if error_types[ErrorType.AUTHENTICATION_ERROR] > 1:
            recommendations.append("Check API key validity and authentication configuration")
        
        if error_types[ErrorType.NETWORK_ERROR] > 2:
            recommendations.append("Monitor network connectivity and consider implementing connection pooling")
        
        if len(error_types) > 5:
            recommendations.append("Multiple error types detected - comprehensive system review recommended")
        
        return recommendations or ["Monitor error patterns and implement specific fixes"]


def with_error_handling(
    service_name: str,
    operation_name: str,
    retry_config: str = "default",
    circuit_breaker_config: str = "default",
    fallback_strategy: FallbackStrategy = FallbackStrategy.DEFAULT_RESPONSE
):
    """Decorator for adding error handling to functions"""
    
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            error_handler = get_error_handler()
            
            # Get retry configuration
            retry_config_obj = error_handler.retry_configs.get(retry_config, error_handler.retry_configs["default"])
            
            # Implement retry logic
            last_exception = None
            
            for attempt in range(retry_config_obj.max_attempts):
                try:
                    # Check circuit breaker
                    if not error_handler.can_execute(service_name, operation_name):
                        raise Exception("Circuit breaker is open")
                    
                    # Execute function
                    if asyncio.iscoroutinefunction(func):
                        result = await func(*args, **kwargs)
                    else:
                        result = func(*args, **kwargs)
                    
                    # Record success
                    error_handler.record_success(service_name, operation_name)
                    return result
                    
                except Exception as e:
                    last_exception = e
                    error_record = error_handler.record_error(e, service_name, operation_name)
                    
                    # Check if error is retryable
                    if error_record.error_type not in retry_config_obj.retryable_errors:
                        break
                    
                    # Check if this is the last attempt
                    if attempt == retry_config_obj.max_attempts - 1:
                        break
                    
                    # Calculate delay
                    delay = min(
                        retry_config_obj.base_delay * (retry_config_obj.exponential_base ** attempt),
                        retry_config_obj.max_delay
                    )
                    
                    if retry_config_obj.jitter:
                        import random
                        delay *= (0.5 + random.random() * 0.5)  # Add jitter
                    
                    logger.warning(f"Retrying {service_name}:{operation_name} in {delay:.2f}s (attempt {attempt + 1}/{retry_config_obj.max_attempts})")
                    await asyncio.sleep(delay)
            
            # All retries failed, execute fallback
            return await error_handler._execute_fallback(
                service_name, operation_name, fallback_strategy, None, *args, **kwargs
            )
        
        return wrapper
    return decorator


# Global error handler instance
_error_handler: Optional[AIErrorHandler] = None


def get_error_handler() -> AIErrorHandler:
    """Get global error handler instance"""
    global _error_handler
    if _error_handler is None:
        _error_handler = AIErrorHandler()
    return _error_handler