"""
AI Monitoring and Cost Optimization Service

Monitors AI service usage, costs, performance, and provides optimization
recommendations to reduce costs while maintaining quality.
"""

import asyncio
import json
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple
import logging
from collections import defaultdict, deque
import statistics

from diskcache import Cache

from app.core.config import settings

logger = logging.getLogger(__name__)

# Cache for monitoring data
monitoring_cache = Cache("/tmp/viralos_monitoring_cache", size_limit=100000000)  # 100MB cache


class AlertLevel(str, Enum):
    """Alert severity levels"""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class MetricType(str, Enum):
    """Types of metrics to track"""
    COST = "cost"
    LATENCY = "latency"
    ERROR_RATE = "error_rate"
    TOKEN_USAGE = "token_usage"
    REQUEST_COUNT = "request_count"
    SUCCESS_RATE = "success_rate"
    CACHE_HIT_RATE = "cache_hit_rate"


@dataclass
class AIServiceCall:
    """Individual AI service call record"""
    call_id: str
    service_name: str  # "openai", "anthropic", etc.
    model_name: str
    operation: str  # "text_generation", "embedding", etc.
    prompt_template: Optional[str]
    input_tokens: int
    output_tokens: int
    total_tokens: int
    cost: float
    latency: float  # seconds
    success: bool
    error_message: Optional[str] = None
    timestamp: float = field(default_factory=time.time)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "call_id": self.call_id,
            "service_name": self.service_name,
            "model_name": self.model_name,
            "operation": self.operation,
            "prompt_template": self.prompt_template,
            "input_tokens": self.input_tokens,
            "output_tokens": self.output_tokens,
            "total_tokens": self.total_tokens,
            "cost": self.cost,
            "latency": self.latency,
            "success": self.success,
            "error_message": self.error_message,
            "timestamp": self.timestamp,
            "metadata": self.metadata
        }


@dataclass
class PerformanceMetrics:
    """Performance metrics for a time window"""
    total_requests: int = 0
    successful_requests: int = 0
    failed_requests: int = 0
    total_cost: float = 0.0
    total_tokens: int = 0
    total_latency: float = 0.0
    cache_hits: int = 0
    cache_misses: int = 0
    
    @property
    def success_rate(self) -> float:
        return self.successful_requests / max(self.total_requests, 1)
    
    @property
    def error_rate(self) -> float:
        return self.failed_requests / max(self.total_requests, 1)
    
    @property
    def average_latency(self) -> float:
        return self.total_latency / max(self.successful_requests, 1)
    
    @property
    def average_cost_per_request(self) -> float:
        return self.total_cost / max(self.total_requests, 1)
    
    @property
    def cache_hit_rate(self) -> float:
        total_cache_operations = self.cache_hits + self.cache_misses
        return self.cache_hits / max(total_cache_operations, 1)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "total_requests": self.total_requests,
            "successful_requests": self.successful_requests,
            "failed_requests": self.failed_requests,
            "total_cost": self.total_cost,
            "total_tokens": self.total_tokens,
            "total_latency": self.total_latency,
            "cache_hits": self.cache_hits,
            "cache_misses": self.cache_misses,
            "success_rate": self.success_rate,
            "error_rate": self.error_rate,
            "average_latency": self.average_latency,
            "average_cost_per_request": self.average_cost_per_request,
            "cache_hit_rate": self.cache_hit_rate
        }


@dataclass
class Alert:
    """System alert"""
    alert_id: str
    level: AlertLevel
    title: str
    message: str
    metric_type: MetricType
    current_value: float
    threshold_value: float
    service_name: Optional[str] = None
    recommendations: List[str] = field(default_factory=list)
    timestamp: float = field(default_factory=time.time)
    resolved: bool = False
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "alert_id": self.alert_id,
            "level": self.level,
            "title": self.title,
            "message": self.message,
            "metric_type": self.metric_type,
            "current_value": self.current_value,
            "threshold_value": self.threshold_value,
            "service_name": self.service_name,
            "recommendations": self.recommendations,
            "timestamp": self.timestamp,
            "resolved": self.resolved
        }


@dataclass
class CostOptimization:
    """Cost optimization recommendation"""
    optimization_id: str
    title: str
    description: str
    potential_savings: float  # USD per month
    implementation_effort: str  # "low", "medium", "high"
    impact_on_quality: str  # "none", "minimal", "moderate", "significant"
    affected_services: List[str]
    implementation_steps: List[str]
    estimated_savings_percentage: float
    priority_score: float  # 0-100
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "optimization_id": self.optimization_id,
            "title": self.title,
            "description": self.description,
            "potential_savings": self.potential_savings,
            "implementation_effort": self.implementation_effort,
            "impact_on_quality": self.impact_on_quality,
            "affected_services": self.affected_services,
            "implementation_steps": self.implementation_steps,
            "estimated_savings_percentage": self.estimated_savings_percentage,
            "priority_score": self.priority_score
        }


class AIMonitor:
    """Core monitoring system for AI services"""
    
    def __init__(self, retention_days: int = 30):
        self.retention_days = retention_days
        self.call_history: deque = deque(maxlen=10000)  # Keep last 10k calls in memory
        self.metrics_cache: Dict[str, PerformanceMetrics] = {}
        self.alerts: List[Alert] = []
        self.thresholds = self._load_default_thresholds()
    
    def _load_default_thresholds(self) -> Dict[str, Dict[str, float]]:
        """Load default monitoring thresholds"""
        return {
            "cost": {
                "daily_limit": 100.0,  # $100 per day
                "hourly_spike": 20.0,  # $20 per hour spike
                "per_request_high": 1.0  # $1 per request
            },
            "latency": {
                "average_high": 10.0,  # 10 seconds average
                "p95_high": 30.0,  # 30 seconds 95th percentile
                "individual_high": 60.0  # 60 seconds individual request
            },
            "error_rate": {
                "high": 0.1,  # 10% error rate
                "critical": 0.25  # 25% error rate
            },
            "token_usage": {
                "daily_limit": 1000000,  # 1M tokens per day
                "hourly_spike": 100000  # 100k tokens per hour
            }
        }
    
    def record_call(self, call: AIServiceCall):
        """Record an AI service call"""
        self.call_history.append(call)
        
        # Update real-time metrics
        self._update_metrics(call)
        
        # Check for alerts
        self._check_alerts(call)
        
        # Store in cache for persistence
        cache_key = f"ai_call_{call.call_id}"
        monitoring_cache.set(cache_key, call.to_dict(), expire=self.retention_days * 24 * 3600)
    
    def _update_metrics(self, call: AIServiceCall):
        """Update performance metrics"""
        # Update overall metrics
        overall_key = "overall"
        if overall_key not in self.metrics_cache:
            self.metrics_cache[overall_key] = PerformanceMetrics()
        
        metrics = self.metrics_cache[overall_key]
        self._update_metrics_object(metrics, call)
        
        # Update service-specific metrics
        service_key = f"service_{call.service_name}"
        if service_key not in self.metrics_cache:
            self.metrics_cache[service_key] = PerformanceMetrics()
        
        service_metrics = self.metrics_cache[service_key]
        self._update_metrics_object(service_metrics, call)
        
        # Update model-specific metrics
        model_key = f"model_{call.model_name}"
        if model_key not in self.metrics_cache:
            self.metrics_cache[model_key] = PerformanceMetrics()
        
        model_metrics = self.metrics_cache[model_key]
        self._update_metrics_object(model_metrics, call)
    
    def _update_metrics_object(self, metrics: PerformanceMetrics, call: AIServiceCall):
        """Update a metrics object with call data"""
        metrics.total_requests += 1
        
        if call.success:
            metrics.successful_requests += 1
            metrics.total_latency += call.latency
        else:
            metrics.failed_requests += 1
        
        metrics.total_cost += call.cost
        metrics.total_tokens += call.total_tokens
        
        # Cache metrics are updated separately
    
    def record_cache_hit(self, service_name: str):
        """Record a cache hit"""
        key = f"service_{service_name}"
        if key not in self.metrics_cache:
            self.metrics_cache[key] = PerformanceMetrics()
        
        self.metrics_cache[key].cache_hits += 1
        self.metrics_cache["overall"].cache_hits += 1
    
    def record_cache_miss(self, service_name: str):
        """Record a cache miss"""
        key = f"service_{service_name}"
        if key not in self.metrics_cache:
            self.metrics_cache[key] = PerformanceMetrics()
        
        self.metrics_cache[key].cache_misses += 1
        self.metrics_cache["overall"].cache_misses += 1
    
    def _check_alerts(self, call: AIServiceCall):
        """Check if call triggers any alerts"""
        
        # High cost per request
        if call.cost > self.thresholds["cost"]["per_request_high"]:
            self._create_alert(
                AlertLevel.WARNING,
                "High Cost Per Request",
                f"Request {call.call_id} cost ${call.cost:.2f}, exceeding threshold of ${self.thresholds['cost']['per_request_high']:.2f}",
                MetricType.COST,
                call.cost,
                self.thresholds["cost"]["per_request_high"],
                call.service_name,
                [
                    "Consider using a smaller model",
                    "Optimize prompt length",
                    "Implement better caching",
                    "Review token usage patterns"
                ]
            )
        
        # High latency
        if call.latency > self.thresholds["latency"]["individual_high"]:
            self._create_alert(
                AlertLevel.WARNING,
                "High Request Latency",
                f"Request {call.call_id} took {call.latency:.1f}s, exceeding threshold of {self.thresholds['latency']['individual_high']:.1f}s",
                MetricType.LATENCY,
                call.latency,
                self.thresholds["latency"]["individual_high"],
                call.service_name,
                [
                    "Check network connectivity",
                    "Consider request batching",
                    "Implement timeout handling",
                    "Monitor service status"
                ]
            )
        
        # Service error
        if not call.success:
            self._create_alert(
                AlertLevel.ERROR,
                "AI Service Error",
                f"Request {call.call_id} failed: {call.error_message}",
                MetricType.ERROR_RATE,
                1.0,
                0.0,
                call.service_name,
                [
                    "Check API key validity",
                    "Verify service status",
                    "Implement retry logic",
                    "Add fallback mechanisms"
                ]
            )
    
    def _create_alert(
        self,
        level: AlertLevel,
        title: str,
        message: str,
        metric_type: MetricType,
        current_value: float,
        threshold_value: float,
        service_name: Optional[str] = None,
        recommendations: List[str] = None
    ):
        """Create a new alert"""
        
        alert_id = f"alert_{int(time.time())}_{len(self.alerts)}"
        
        alert = Alert(
            alert_id=alert_id,
            level=level,
            title=title,
            message=message,
            metric_type=metric_type,
            current_value=current_value,
            threshold_value=threshold_value,
            service_name=service_name,
            recommendations=recommendations or []
        )
        
        self.alerts.append(alert)
        logger.warning(f"Alert created: {title}")
        
        # Store in cache
        cache_key = f"alert_{alert_id}"
        monitoring_cache.set(cache_key, alert.to_dict(), expire=7 * 24 * 3600)  # 7 days
    
    def get_metrics(self, time_window_hours: int = 24) -> Dict[str, Any]:
        """Get performance metrics for time window"""
        
        cutoff_time = time.time() - (time_window_hours * 3600)
        
        # Filter calls within time window
        recent_calls = [call for call in self.call_history if call.timestamp >= cutoff_time]
        
        if not recent_calls:
            return {"error": "No data available for specified time window"}
        
        # Calculate metrics
        total_requests = len(recent_calls)
        successful_requests = sum(1 for call in recent_calls if call.success)
        failed_requests = total_requests - successful_requests
        
        total_cost = sum(call.cost for call in recent_calls)
        total_tokens = sum(call.total_tokens for call in recent_calls)
        total_latency = sum(call.latency for call in recent_calls if call.success)
        
        # Service breakdown
        service_breakdown = defaultdict(lambda: {"requests": 0, "cost": 0, "tokens": 0})
        model_breakdown = defaultdict(lambda: {"requests": 0, "cost": 0, "tokens": 0})
        
        for call in recent_calls:
            service_breakdown[call.service_name]["requests"] += 1
            service_breakdown[call.service_name]["cost"] += call.cost
            service_breakdown[call.service_name]["tokens"] += call.total_tokens
            
            model_breakdown[call.model_name]["requests"] += 1
            model_breakdown[call.model_name]["cost"] += call.cost
            model_breakdown[call.model_name]["tokens"] += call.total_tokens
        
        # Cost trends (hourly breakdown)
        hourly_costs = defaultdict(float)
        for call in recent_calls:
            hour = int(call.timestamp // 3600)
            hourly_costs[hour] += call.cost
        
        return {
            "time_window_hours": time_window_hours,
            "summary": {
                "total_requests": total_requests,
                "successful_requests": successful_requests,
                "failed_requests": failed_requests,
                "success_rate": successful_requests / total_requests if total_requests > 0 else 0,
                "total_cost": total_cost,
                "total_tokens": total_tokens,
                "average_latency": total_latency / successful_requests if successful_requests > 0 else 0,
                "average_cost_per_request": total_cost / total_requests if total_requests > 0 else 0
            },
            "service_breakdown": dict(service_breakdown),
            "model_breakdown": dict(model_breakdown),
            "hourly_costs": dict(hourly_costs),
            "cache_performance": {
                "overall_hit_rate": self.metrics_cache.get("overall", PerformanceMetrics()).cache_hit_rate
            }
        }
    
    def get_active_alerts(self) -> List[Alert]:
        """Get active (unresolved) alerts"""
        return [alert for alert in self.alerts if not alert.resolved]
    
    def resolve_alert(self, alert_id: str):
        """Mark an alert as resolved"""
        for alert in self.alerts:
            if alert.alert_id == alert_id:
                alert.resolved = True
                # Update cache
                cache_key = f"alert_{alert_id}"
                monitoring_cache.set(cache_key, alert.to_dict(), expire=7 * 24 * 3600)
                logger.info(f"Alert resolved: {alert_id}")
                break


class CostOptimizer:
    """AI cost optimization engine"""
    
    def __init__(self, monitor: AIMonitor):
        self.monitor = monitor
        self.optimization_history: List[CostOptimization] = []
    
    def analyze_costs(self, time_window_hours: int = 168) -> Dict[str, Any]:  # 1 week default
        """Analyze costs and identify optimization opportunities"""
        
        metrics = self.monitor.get_metrics(time_window_hours)
        
        if "error" in metrics:
            return metrics
        
        # Generate optimization recommendations
        optimizations = []
        
        # High-cost models optimization
        model_breakdown = metrics["model_breakdown"]
        total_cost = metrics["summary"]["total_cost"]
        
        for model, stats in model_breakdown.items():
            model_cost_percentage = (stats["cost"] / total_cost) * 100 if total_cost > 0 else 0
            
            if model_cost_percentage > 30 and "gpt-4" in model.lower():
                optimizations.append(self._create_model_optimization(model, stats, model_cost_percentage))
        
        # Token usage optimization
        high_token_calls = [
            call for call in self.monitor.call_history 
            if call.total_tokens > 4000 and call.timestamp >= time.time() - (time_window_hours * 3600)
        ]
        
        if len(high_token_calls) > 10:
            optimizations.append(self._create_token_optimization(high_token_calls))
        
        # Cache optimization
        cache_hit_rate = metrics.get("cache_performance", {}).get("overall_hit_rate", 0)
        if cache_hit_rate < 0.3:  # Less than 30% cache hit rate
            optimizations.append(self._create_cache_optimization(cache_hit_rate))
        
        # Prompt optimization
        prompt_inefficiencies = self._analyze_prompt_efficiency()
        if prompt_inefficiencies:
            optimizations.extend(prompt_inefficiencies)
        
        # Error rate optimization
        error_rate = metrics["summary"]["failed_requests"] / max(metrics["summary"]["total_requests"], 1)
        if error_rate > 0.05:  # More than 5% error rate
            optimizations.append(self._create_error_rate_optimization(error_rate))
        
        # Sort by priority score
        optimizations.sort(key=lambda x: x.priority_score, reverse=True)
        
        # Calculate total potential savings
        total_potential_savings = sum(opt.potential_savings for opt in optimizations)
        
        return {
            "analysis_period_hours": time_window_hours,
            "current_costs": metrics["summary"],
            "optimization_opportunities": [opt.to_dict() for opt in optimizations],
            "total_potential_monthly_savings": total_potential_savings,
            "estimated_cost_reduction_percentage": min(
                (total_potential_savings / (metrics["summary"]["total_cost"] * 30 / (time_window_hours / 24))) * 100,
                50  # Cap at 50% reduction
            ) if metrics["summary"]["total_cost"] > 0 else 0,
            "recommendations_summary": {
                "high_priority": len([opt for opt in optimizations if opt.priority_score >= 80]),
                "medium_priority": len([opt for opt in optimizations if 60 <= opt.priority_score < 80]),
                "low_priority": len([opt for opt in optimizations if opt.priority_score < 60])
            }
        }
    
    def _create_model_optimization(self, model: str, stats: Dict, cost_percentage: float) -> CostOptimization:
        """Create model optimization recommendation"""
        
        potential_savings = stats["cost"] * 0.3  # Assume 30% savings with smaller model
        
        return CostOptimization(
            optimization_id=f"model_opt_{int(time.time())}",
            title=f"Optimize {model} Usage",
            description=f"{model} accounts for {cost_percentage:.1f}% of total costs. Consider using smaller models for simpler tasks.",
            potential_savings=potential_savings * 30,  # Monthly estimate
            implementation_effort="medium",
            impact_on_quality="minimal",
            affected_services=[model],
            implementation_steps=[
                f"Identify simple tasks currently using {model}",
                "Test smaller models (GPT-3.5-turbo) for these tasks",
                "Implement model selection logic based on task complexity",
                "Monitor quality metrics after switching",
                "Gradually expand usage of smaller models"
            ],
            estimated_savings_percentage=30.0,
            priority_score=85.0
        )
    
    def _create_token_optimization(self, high_token_calls: List[AIServiceCall]) -> CostOptimization:
        """Create token usage optimization recommendation"""
        
        avg_tokens = statistics.mean([call.total_tokens for call in high_token_calls])
        potential_reduction = avg_tokens * 0.25  # 25% token reduction
        
        potential_cost_savings = len(high_token_calls) * (potential_reduction * 0.002) * 30  # Rough estimate
        
        return CostOptimization(
            optimization_id=f"token_opt_{int(time.time())}",
            title="Optimize Token Usage",
            description=f"Found {len(high_token_calls)} high-token requests (avg: {avg_tokens:.0f} tokens). Prompt optimization can reduce token usage.",
            potential_savings=potential_cost_savings,
            implementation_effort="low",
            impact_on_quality="none",
            affected_services=list(set([call.service_name for call in high_token_calls])),
            implementation_steps=[
                "Analyze prompts with highest token usage",
                "Remove unnecessary context and examples",
                "Use more concise instructions",
                "Implement prompt compression techniques",
                "Test optimized prompts for quality"
            ],
            estimated_savings_percentage=25.0,
            priority_score=75.0
        )
    
    def _create_cache_optimization(self, current_hit_rate: float) -> CostOptimization:
        """Create cache optimization recommendation"""
        
        # Estimate potential savings from improved caching
        target_hit_rate = 0.7  # 70% target
        improvement = target_hit_rate - current_hit_rate
        
        # Rough estimate: each cache hit saves average request cost
        recent_calls = list(self.monitor.call_history)[-1000:]  # Last 1000 calls
        if recent_calls:
            avg_cost_per_request = statistics.mean([call.cost for call in recent_calls])
            monthly_requests = len(recent_calls) * 30  # Rough monthly estimate
            potential_savings = monthly_requests * improvement * avg_cost_per_request
        else:
            potential_savings = 50.0  # Default estimate
        
        return CostOptimization(
            optimization_id=f"cache_opt_{int(time.time())}",
            title="Improve Caching Strategy",
            description=f"Current cache hit rate is {current_hit_rate:.1%}. Improving caching can significantly reduce costs.",
            potential_savings=potential_savings,
            implementation_effort="medium",
            impact_on_quality="none",
            affected_services=["all"],
            implementation_steps=[
                "Analyze cache miss patterns",
                "Increase cache TTL for stable content",
                "Implement semantic caching for similar requests",
                "Add cache warming for common queries",
                "Monitor cache performance metrics"
            ],
            estimated_savings_percentage=improvement * 100,
            priority_score=80.0
        )
    
    def _analyze_prompt_efficiency(self) -> List[CostOptimization]:
        """Analyze prompt efficiency and suggest improvements"""
        
        optimizations = []
        
        # Analyze recent calls for prompt inefficiencies
        recent_calls = [
            call for call in self.monitor.call_history 
            if call.timestamp >= time.time() - (24 * 3600)  # Last 24 hours
        ]
        
        if not recent_calls:
            return optimizations
        
        # Group by prompt template
        template_stats = defaultdict(list)
        for call in recent_calls:
            if call.prompt_template:
                template_stats[call.prompt_template].append(call)
        
        for template, calls in template_stats.items():
            if len(calls) < 10:  # Skip templates with few calls
                continue
            
            avg_tokens = statistics.mean([call.total_tokens for call in calls])
            avg_cost = statistics.mean([call.cost for call in calls])
            
            # Check if this template is expensive
            if avg_cost > 0.1:  # $0.10 per request
                potential_savings = len(calls) * avg_cost * 0.2 * 30  # 20% savings, monthly
                
                optimizations.append(CostOptimization(
                    optimization_id=f"prompt_opt_{template}_{int(time.time())}",
                    title=f"Optimize '{template}' Prompt",
                    description=f"Template '{template}' has high average cost (${avg_cost:.3f}) and token usage ({avg_tokens:.0f} tokens).",
                    potential_savings=potential_savings,
                    implementation_effort="low",
                    impact_on_quality="minimal",
                    affected_services=[template],
                    implementation_steps=[
                        f"Review '{template}' prompt structure",
                        "Remove redundant instructions",
                        "Simplify language and examples",
                        "Test shortened version for quality",
                        "A/B test optimized prompt"
                    ],
                    estimated_savings_percentage=20.0,
                    priority_score=70.0
                ))
        
        return optimizations
    
    def _create_error_rate_optimization(self, error_rate: float) -> CostOptimization:
        """Create error rate optimization recommendation"""
        
        # Estimate cost of errors (retries, manual intervention, etc.)
        recent_calls = list(self.monitor.call_history)[-1000:]
        if recent_calls:
            avg_cost_per_request = statistics.mean([call.cost for call in recent_calls])
            failed_requests = [call for call in recent_calls if not call.success]
            
            # Assume each error leads to 2 retries on average
            error_cost = len(failed_requests) * avg_cost_per_request * 2
            potential_savings = error_cost * 30  # Monthly estimate
        else:
            potential_savings = 100.0  # Default estimate
        
        return CostOptimization(
            optimization_id=f"error_opt_{int(time.time())}",
            title="Reduce Error Rate",
            description=f"Current error rate is {error_rate:.1%}. Reducing errors saves on retry costs and improves reliability.",
            potential_savings=potential_savings,
            implementation_effort="medium",
            impact_on_quality="positive",
            affected_services=["all"],
            implementation_steps=[
                "Analyze common error patterns",
                "Improve input validation",
                "Add better error handling and retries",
                "Monitor API rate limits",
                "Implement circuit breakers"
            ],
            estimated_savings_percentage=error_rate * 100,
            priority_score=90.0
        )


class AIMonitoringService:
    """Main service for AI monitoring and optimization"""
    
    def __init__(self):
        self.monitor = AIMonitor()
        self.optimizer = CostOptimizer(self.monitor)
        self.alert_callbacks = []
    
    def record_ai_call(
        self,
        service_name: str,
        model_name: str,
        operation: str,
        input_tokens: int,
        output_tokens: int,
        cost: float,
        latency: float,
        success: bool,
        prompt_template: Optional[str] = None,
        error_message: Optional[str] = None,
        metadata: Dict[str, Any] = None
    ):
        """Record an AI service call"""
        
        call = AIServiceCall(
            call_id=f"{service_name}_{int(time.time())}_{hash(str(time.time()))}",
            service_name=service_name,
            model_name=model_name,
            operation=operation,
            prompt_template=prompt_template,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            total_tokens=input_tokens + output_tokens,
            cost=cost,
            latency=latency,
            success=success,
            error_message=error_message,
            metadata=metadata or {}
        )
        
        self.monitor.record_call(call)
        
        # Trigger alert callbacks if needed
        active_alerts = self.monitor.get_active_alerts()
        for alert in active_alerts[-1:]:  # Only check latest alert
            for callback in self.alert_callbacks:
                try:
                    callback(alert)
                except Exception as e:
                    logger.error(f"Alert callback failed: {e}")
    
    def record_cache_hit(self, service_name: str):
        """Record a cache hit"""
        self.monitor.record_cache_hit(service_name)
    
    def record_cache_miss(self, service_name: str):
        """Record a cache miss"""
        self.monitor.record_cache_miss(service_name)
    
    def get_dashboard_data(self) -> Dict[str, Any]:
        """Get comprehensive dashboard data"""
        
        # Get metrics for different time windows
        metrics_24h = self.monitor.get_metrics(24)
        metrics_7d = self.monitor.get_metrics(168)
        
        # Get optimization analysis
        cost_analysis = self.optimizer.analyze_costs()
        
        # Get active alerts
        active_alerts = [alert.to_dict() for alert in self.monitor.get_active_alerts()]
        
        return {
            "overview": {
                "last_24h": metrics_24h.get("summary", {}),
                "last_7d": metrics_7d.get("summary", {}),
                "active_alerts_count": len(active_alerts),
                "high_priority_optimizations": len([
                    opt for opt in cost_analysis.get("optimization_opportunities", [])
                    if opt["priority_score"] >= 80
                ])
            },
            "current_metrics": metrics_24h,
            "weekly_trends": metrics_7d,
            "cost_optimization": cost_analysis,
            "active_alerts": active_alerts,
            "system_health": {
                "monitoring_status": "healthy",
                "last_updated": time.time(),
                "data_retention_days": self.monitor.retention_days
            }
        }
    
    def add_alert_callback(self, callback):
        """Add callback function for alerts"""
        self.alert_callbacks.append(callback)
    
    def get_cost_trends(self, days: int = 30) -> Dict[str, Any]:
        """Get cost trends over time"""
        
        # Get historical data from cache
        daily_costs = defaultdict(float)
        daily_requests = defaultdict(int)
        
        cutoff_time = time.time() - (days * 24 * 3600)
        
        for call in self.monitor.call_history:
            if call.timestamp >= cutoff_time:
                day = int(call.timestamp // (24 * 3600))
                daily_costs[day] += call.cost
                daily_requests[day] += 1
        
        # Convert to time series
        cost_trend = []
        request_trend = []
        
        for i in range(days):
            day = int((time.time() - ((days - i) * 24 * 3600)) // (24 * 3600))
            cost_trend.append({
                "date": day * 24 * 3600,
                "cost": daily_costs.get(day, 0.0)
            })
            request_trend.append({
                "date": day * 24 * 3600,
                "requests": daily_requests.get(day, 0)
            })
        
        return {
            "period_days": days,
            "cost_trend": cost_trend,
            "request_trend": request_trend,
            "total_cost": sum(daily_costs.values()),
            "total_requests": sum(daily_requests.values()),
            "average_daily_cost": statistics.mean(daily_costs.values()) if daily_costs else 0,
            "cost_growth_rate": self._calculate_growth_rate(cost_trend)
        }
    
    def _calculate_growth_rate(self, trend_data: List[Dict]) -> float:
        """Calculate growth rate from trend data"""
        if len(trend_data) < 7:  # Need at least a week of data
            return 0.0
        
        # Compare last 7 days with previous 7 days
        recent_week = sum(d["cost"] for d in trend_data[-7:])
        previous_week = sum(d["cost"] for d in trend_data[-14:-7]) if len(trend_data) >= 14 else recent_week
        
        if previous_week == 0:
            return 0.0
        
        return ((recent_week - previous_week) / previous_week) * 100


# Global service instance
_monitoring_service: Optional[AIMonitoringService] = None


def get_monitoring_service() -> AIMonitoringService:
    """Get global monitoring service instance"""
    global _monitoring_service
    if _monitoring_service is None:
        _monitoring_service = AIMonitoringService()
    return _monitoring_service