"""
Monitoring, logging, and error recovery system for scraping operations.
"""

import time
import json
import asyncio
from typing import Any, Dict, List, Optional, Callable
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from collections import defaultdict, deque
import logging

from sqlalchemy.orm import Session
from app.db.session import SessionLocal
from app.models.product import ScrapingJob, ScrapingSession
from app.core.config import settings

logger = logging.getLogger(__name__)


@dataclass
class ScrapingMetrics:
    """Scraping performance metrics"""
    total_requests: int = 0
    successful_requests: int = 0
    failed_requests: int = 0
    avg_response_time: float = 0.0
    total_data_extracted: int = 0
    proxy_failures: int = 0
    bot_detections: int = 0
    rate_limit_hits: int = 0
    
    @property
    def success_rate(self) -> float:
        if self.total_requests == 0:
            return 0.0
        return self.successful_requests / self.total_requests
    
    @property
    def failure_rate(self) -> float:
        return 1.0 - self.success_rate


@dataclass
class AlertRule:
    """Alert rule configuration"""
    name: str
    condition: Callable[[ScrapingMetrics], bool]
    message: str
    cooldown_minutes: int = 30
    last_triggered: Optional[datetime] = None
    
    def should_trigger(self, metrics: ScrapingMetrics) -> bool:
        """Check if alert should be triggered"""
        if not self.condition(metrics):
            return False
        
        # Check cooldown
        if self.last_triggered:
            cooldown_end = self.last_triggered + timedelta(minutes=self.cooldown_minutes)
            if datetime.now() < cooldown_end:
                return False
        
        return True
    
    def trigger(self):
        """Mark alert as triggered"""
        self.last_triggered = datetime.now()


class ScrapingMonitor:
    """Monitor scraping operations and provide alerts"""
    
    def __init__(self, db_session_factory: Callable = SessionLocal):
        self.db_session_factory = db_session_factory
        self.metrics_history = deque(maxlen=1000)  # Keep last 1000 metrics
        self.domain_metrics = defaultdict(lambda: ScrapingMetrics())
        self.job_metrics = defaultdict(lambda: ScrapingMetrics())
        
        # Setup alert rules
        self.alert_rules = [
            AlertRule(
                name="high_failure_rate",
                condition=lambda m: m.total_requests >= 10 and m.failure_rate > 0.5,
                message="High failure rate detected: {failure_rate:.1%}",
                cooldown_minutes=15
            ),
            AlertRule(
                name="slow_response_time",
                condition=lambda m: m.avg_response_time > 30.0,
                message="Slow response times detected: {avg_response_time:.1f}s average",
                cooldown_minutes=20
            ),
            AlertRule(
                name="high_bot_detection",
                condition=lambda m: m.total_requests >= 5 and m.bot_detections / m.total_requests > 0.3,
                message="High bot detection rate: {bot_detection_rate:.1%}",
                cooldown_minutes=10
            ),
            AlertRule(
                name="proxy_failures",
                condition=lambda m: m.proxy_failures > 10,
                message="Multiple proxy failures detected: {proxy_failures} failures",
                cooldown_minutes=25
            )
        ]
        
        self.error_recovery_strategies = {
            "rate_limit": self._handle_rate_limit,
            "bot_detection": self._handle_bot_detection,
            "proxy_failure": self._handle_proxy_failure,
            "network_error": self._handle_network_error,
            "parsing_error": self._handle_parsing_error
        }
    
    def record_scraping_session(self, session_data: Dict[str, Any]):
        """Record metrics from a scraping session"""
        
        # Update total metrics
        metrics = ScrapingMetrics()
        metrics.total_requests = 1
        
        if session_data.get("success"):
            metrics.successful_requests = 1
            metrics.total_data_extracted = session_data.get("products_found", 0)
        else:
            metrics.failed_requests = 1
            
            # Categorize errors
            error_type = session_data.get("error_type", "unknown")
            if "rate" in error_type.lower():
                metrics.rate_limit_hits = 1
            elif "bot" in error_type.lower() or "blocked" in error_type.lower():
                metrics.bot_detections = 1
            elif "proxy" in error_type.lower():
                metrics.proxy_failures = 1
        
        metrics.avg_response_time = session_data.get("response_time", 0.0)
        
        # Update domain-specific metrics
        domain = session_data.get("target_domain", "unknown")
        self._update_metrics(self.domain_metrics[domain], metrics)
        
        # Update job-specific metrics
        job_id = session_data.get("job_id")
        if job_id:
            self._update_metrics(self.job_metrics[job_id], metrics)
        
        # Store in history
        self.metrics_history.append({
            "timestamp": datetime.now(),
            "metrics": metrics,
            "domain": domain,
            "job_id": job_id
        })
        
        # Check for alerts
        self._check_alerts(metrics, domain)
    
    def _update_metrics(self, target_metrics: ScrapingMetrics, new_metrics: ScrapingMetrics):
        """Update target metrics with new data"""
        
        # Update counters
        target_metrics.total_requests += new_metrics.total_requests
        target_metrics.successful_requests += new_metrics.successful_requests
        target_metrics.failed_requests += new_metrics.failed_requests
        target_metrics.total_data_extracted += new_metrics.total_data_extracted
        target_metrics.proxy_failures += new_metrics.proxy_failures
        target_metrics.bot_detections += new_metrics.bot_detections
        target_metrics.rate_limit_hits += new_metrics.rate_limit_hits
        
        # Update average response time
        if new_metrics.avg_response_time > 0:
            if target_metrics.avg_response_time == 0:
                target_metrics.avg_response_time = new_metrics.avg_response_time
            else:
                # Running average
                total_time = target_metrics.avg_response_time * (target_metrics.total_requests - 1)
                total_time += new_metrics.avg_response_time
                target_metrics.avg_response_time = total_time / target_metrics.total_requests
    
    def _check_alerts(self, metrics: ScrapingMetrics, domain: str):
        """Check if any alerts should be triggered"""
        
        domain_metrics = self.domain_metrics[domain]
        
        for rule in self.alert_rules:
            if rule.should_trigger(domain_metrics):
                self._send_alert(rule, domain_metrics, domain)
                rule.trigger()
    
    def _send_alert(self, rule: AlertRule, metrics: ScrapingMetrics, domain: str):
        """Send alert notification"""
        
        message = rule.message.format(
            failure_rate=metrics.failure_rate,
            avg_response_time=metrics.avg_response_time,
            bot_detection_rate=metrics.bot_detections / max(metrics.total_requests, 1),
            proxy_failures=metrics.proxy_failures
        )
        
        alert_data = {
            "rule": rule.name,
            "domain": domain,
            "message": message,
            "metrics": {
                "total_requests": metrics.total_requests,
                "success_rate": metrics.success_rate,
                "avg_response_time": metrics.avg_response_time,
                "bot_detections": metrics.bot_detections,
                "proxy_failures": metrics.proxy_failures
            },
            "timestamp": datetime.now().isoformat()
        }
        
        logger.warning(f"SCRAPING ALERT [{rule.name}] {domain}: {message}")
        
        # In production, send to monitoring service (Slack, email, etc.)
        self._send_notification(alert_data)
    
    def _send_notification(self, alert_data: Dict[str, Any]):
        """Send notification to external service"""
        # Placeholder for external notification service
        # Could integrate with Slack, email, PagerDuty, etc.
        pass
    
    def get_domain_metrics(self, domain: str) -> ScrapingMetrics:
        """Get metrics for specific domain"""
        return self.domain_metrics[domain]
    
    def get_job_metrics(self, job_id: int) -> ScrapingMetrics:
        """Get metrics for specific job"""
        return self.job_metrics[job_id]
    
    def get_overall_metrics(self, time_window_minutes: int = 60) -> ScrapingMetrics:
        """Get overall metrics for specified time window"""
        
        cutoff_time = datetime.now() - timedelta(minutes=time_window_minutes)
        recent_metrics = [
            entry for entry in self.metrics_history
            if entry["timestamp"] > cutoff_time
        ]
        
        overall = ScrapingMetrics()
        for entry in recent_metrics:
            self._update_metrics(overall, entry["metrics"])
        
        return overall
    
    def get_health_status(self) -> Dict[str, Any]:
        """Get overall health status of scraping system"""
        
        overall_metrics = self.get_overall_metrics(60)  # Last hour
        
        # Determine health status
        health_score = 1.0
        issues = []
        
        if overall_metrics.total_requests > 0:
            if overall_metrics.failure_rate > 0.3:
                health_score -= 0.4
                issues.append("High failure rate")
            
            if overall_metrics.avg_response_time > 20:
                health_score -= 0.2
                issues.append("Slow response times")
            
            bot_detection_rate = overall_metrics.bot_detections / overall_metrics.total_requests
            if bot_detection_rate > 0.2:
                health_score -= 0.3
                issues.append("Bot detection issues")
        
        if health_score >= 0.8:
            status = "healthy"
        elif health_score >= 0.6:
            status = "degraded"
        else:
            status = "unhealthy"
        
        return {
            "status": status,
            "health_score": max(health_score, 0.0),
            "issues": issues,
            "metrics": {
                "total_requests": overall_metrics.total_requests,
                "success_rate": overall_metrics.success_rate,
                "avg_response_time": overall_metrics.avg_response_time,
                "data_extracted": overall_metrics.total_data_extracted
            }
        }
    
    async def analyze_job_performance(self, job_id: int) -> Dict[str, Any]:
        """Analyze performance of a specific scraping job"""
        
        db = self.db_session_factory()
        try:
            # Get job details
            job = db.query(ScrapingJob).filter(ScrapingJob.id == job_id).first()
            if not job:
                return {"error": "Job not found"}
            
            # Get all sessions for this job
            sessions = db.query(ScrapingSession).filter(
                ScrapingSession.job_id == job_id
            ).all()
            
            if not sessions:
                return {"error": "No sessions found for job"}
            
            # Analyze session data
            total_sessions = len(sessions)
            successful_sessions = sum(1 for s in sessions if s.success)
            failed_sessions = total_sessions - successful_sessions
            
            response_times = [s.response_time for s in sessions if s.response_time]
            avg_response_time = sum(response_times) / len(response_times) if response_times else 0
            
            # Error analysis
            error_types = defaultdict(int)
            bot_detections = 0
            
            for session in sessions:
                if not session.success and session.error_type:
                    error_types[session.error_type] += 1
                
                if session.bot_detection:
                    bot_detections += 1
            
            # Domain analysis
            domain_performance = defaultdict(lambda: {"total": 0, "successful": 0})
            for session in sessions:
                domain = session.target_domain or "unknown"
                domain_performance[domain]["total"] += 1
                if session.success:
                    domain_performance[domain]["successful"] += 1
            
            # Performance insights
            insights = []
            
            success_rate = successful_sessions / total_sessions
            if success_rate < 0.7:
                insights.append("Low success rate indicates potential issues with target sites or scraping configuration")
            
            if avg_response_time > 15:
                insights.append("High response times may indicate network issues or need for optimization")
            
            if bot_detections > total_sessions * 0.2:
                insights.append("High bot detection rate - consider using different user agents or proxies")
            
            return {
                "job_id": job_id,
                "job_type": job.job_type,
                "total_sessions": total_sessions,
                "successful_sessions": successful_sessions,
                "failed_sessions": failed_sessions,
                "success_rate": success_rate,
                "avg_response_time": avg_response_time,
                "bot_detections": bot_detections,
                "error_types": dict(error_types),
                "domain_performance": {
                    domain: {
                        "total": stats["total"],
                        "successful": stats["successful"],
                        "success_rate": stats["successful"] / stats["total"]
                    }
                    for domain, stats in domain_performance.items()
                },
                "insights": insights,
                "recommendations": self._generate_recommendations(
                    success_rate, avg_response_time, bot_detections, total_sessions
                )
            }
            
        finally:
            db.close()
    
    def _generate_recommendations(self, success_rate: float, avg_response_time: float,
                                bot_detections: int, total_sessions: int) -> List[str]:
        """Generate recommendations based on performance analysis"""
        
        recommendations = []
        
        if success_rate < 0.5:
            recommendations.append("Consider implementing retry logic with exponential backoff")
            recommendations.append("Review target site structures - they may have changed")
        
        if success_rate < 0.8 and bot_detections > total_sessions * 0.1:
            recommendations.append("Implement proxy rotation to avoid bot detection")
            recommendations.append("Add random delays between requests")
            recommendations.append("Use more realistic user agents")
        
        if avg_response_time > 20:
            recommendations.append("Consider using faster proxies or direct connections")
            recommendations.append("Optimize scraping selectors to reduce page processing time")
        
        if bot_detections > total_sessions * 0.3:
            recommendations.append("Switch to Playwright for JavaScript-heavy sites")
            recommendations.append("Implement CAPTCHA solving service")
        
        return recommendations
    
    # Error Recovery Strategies
    
    async def _handle_rate_limit(self, error_data: Dict[str, Any]) -> Dict[str, Any]:
        """Handle rate limiting errors"""
        
        domain = error_data.get("domain")
        
        # Increase delay for this domain
        delay_multiplier = 2.0
        recommended_delay = error_data.get("current_delay", 1.0) * delay_multiplier
        
        return {
            "strategy": "increase_delay",
            "domain": domain,
            "recommended_delay": min(recommended_delay, 60.0),  # Cap at 60 seconds
            "use_proxy": True,
            "wait_time": 300  # Wait 5 minutes before retrying
        }
    
    async def _handle_bot_detection(self, error_data: Dict[str, Any]) -> Dict[str, Any]:
        """Handle bot detection errors"""
        
        return {
            "strategy": "anti_bot_measures",
            "use_proxy": True,
            "change_user_agent": True,
            "use_playwright": True,
            "random_delay": (5.0, 15.0),
            "wait_time": 600  # Wait 10 minutes
        }
    
    async def _handle_proxy_failure(self, error_data: Dict[str, Any]) -> Dict[str, Any]:
        """Handle proxy failure errors"""
        
        return {
            "strategy": "proxy_rotation",
            "rotate_proxy": True,
            "test_proxy_health": True,
            "fallback_to_direct": True
        }
    
    async def _handle_network_error(self, error_data: Dict[str, Any]) -> Dict[str, Any]:
        """Handle network errors"""
        
        return {
            "strategy": "retry_with_backoff",
            "max_retries": 3,
            "backoff_multiplier": 2.0,
            "use_different_proxy": True
        }
    
    async def _handle_parsing_error(self, error_data: Dict[str, Any]) -> Dict[str, Any]:
        """Handle parsing errors"""
        
        return {
            "strategy": "update_selectors",
            "use_fallback_selectors": True,
            "try_different_parser": True,
            "log_page_content": True  # For debugging
        }
    
    async def get_recovery_strategy(self, error_type: str, error_data: Dict[str, Any]) -> Dict[str, Any]:
        """Get recovery strategy for specific error type"""
        
        handler = self.error_recovery_strategies.get(error_type)
        if handler:
            return await handler(error_data)
        
        # Default recovery strategy
        return {
            "strategy": "default_retry",
            "increase_delay": True,
            "use_proxy": True,
            "max_retries": 2
        }


class ScrapingLogger:
    """Enhanced logging for scraping operations"""
    
    def __init__(self, logger_name: str = "scraping"):
        self.logger = logging.getLogger(logger_name)
        self.session_logs = deque(maxlen=1000)
    
    def log_session_start(self, session_id: str, url: str, config: Dict[str, Any]):
        """Log scraping session start"""
        log_entry = {
            "session_id": session_id,
            "event": "session_start",
            "url": url,
            "config": config,
            "timestamp": datetime.now().isoformat()
        }
        
        self.session_logs.append(log_entry)
        self.logger.info(f"Starting scraping session {session_id} for {url}")
    
    def log_session_end(self, session_id: str, success: bool, 
                       metrics: Dict[str, Any], error: str = None):
        """Log scraping session end"""
        log_entry = {
            "session_id": session_id,
            "event": "session_end",
            "success": success,
            "metrics": metrics,
            "error": error,
            "timestamp": datetime.now().isoformat()
        }
        
        self.session_logs.append(log_entry)
        
        if success:
            self.logger.info(f"Scraping session {session_id} completed successfully")
        else:
            self.logger.error(f"Scraping session {session_id} failed: {error}")
    
    def log_bot_detection(self, session_id: str, url: str, detection_type: str):
        """Log bot detection event"""
        log_entry = {
            "session_id": session_id,
            "event": "bot_detection",
            "url": url,
            "detection_type": detection_type,
            "timestamp": datetime.now().isoformat()
        }
        
        self.session_logs.append(log_entry)
        self.logger.warning(f"Bot detection in session {session_id}: {detection_type}")
    
    def log_proxy_event(self, session_id: str, proxy_info: Dict[str, Any], 
                       event_type: str, details: str = None):
        """Log proxy-related events"""
        log_entry = {
            "session_id": session_id,
            "event": f"proxy_{event_type}",
            "proxy_info": proxy_info,
            "details": details,
            "timestamp": datetime.now().isoformat()
        }
        
        self.session_logs.append(log_entry)
        self.logger.debug(f"Proxy {event_type} in session {session_id}: {details}")
    
    def get_session_logs(self, session_id: str = None, 
                        last_n: int = 100) -> List[Dict[str, Any]]:
        """Get session logs"""
        logs = list(self.session_logs)
        
        if session_id:
            logs = [log for log in logs if log.get("session_id") == session_id]
        
        return logs[-last_n:] if last_n else logs


# Global instances
scraping_monitor = ScrapingMonitor()
scraping_logger = ScrapingLogger()