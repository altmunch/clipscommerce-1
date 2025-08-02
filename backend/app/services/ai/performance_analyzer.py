"""
Performance Analysis AI Service

Analyzes content performance, predicts engagement, provides ROI optimization
recommendations, and generates competitor analysis insights.
"""

import asyncio
import json
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple
import logging
from collections import defaultdict
import statistics

import numpy as np
from diskcache import Cache

from app.core.config import settings
from app.services.ai.providers import get_text_service
from app.services.ai.vector_db import get_vector_service
from app.services.ai.prompts import get_prompt_template
from app.services.ai.viral_content import Platform

logger = logging.getLogger(__name__)

# Cache for performance data and predictions
performance_cache = Cache("/tmp/viralos_performance_cache", size_limit=200000000)  # 200MB cache


class MetricType(str, Enum):
    """Performance metric types"""
    ENGAGEMENT_RATE = "engagement_rate"
    REACH = "reach"
    IMPRESSIONS = "impressions"
    CLICKS = "clicks"
    CONVERSIONS = "conversions"
    SHARES = "shares"
    COMMENTS = "comments"
    LIKES = "likes"
    SAVES = "saves"
    FOLLOWERS_GAINED = "followers_gained"
    VIEW_DURATION = "view_duration"
    CPM = "cpm"
    CPC = "cpc"
    CPA = "cpa"
    ROI = "roi"


class TimeRange(str, Enum):
    """Time range for analysis"""
    LAST_24H = "24h"
    LAST_7D = "7d"
    LAST_30D = "30d"
    LAST_90D = "90d"
    LAST_YEAR = "1y"
    ALL_TIME = "all"


@dataclass
class PerformanceMetric:
    """Individual performance metric"""
    metric_type: MetricType
    value: float
    timestamp: float
    platform: Platform
    content_id: str
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "metric_type": self.metric_type,
            "value": self.value,
            "timestamp": self.timestamp,
            "platform": self.platform,
            "content_id": self.content_id,
            "metadata": self.metadata
        }


@dataclass
class ContentPerformance:
    """Comprehensive content performance data"""
    content_id: str
    title: str
    platform: Platform
    published_at: float
    metrics: List[PerformanceMetric]
    content_type: str  # video, image, carousel, etc.
    hashtags: List[str]
    audience_demographics: Dict[str, Any]
    engagement_timeline: List[Tuple[float, float]]  # (timestamp, engagement_rate)
    cost_data: Dict[str, float]
    
    def get_metric_value(self, metric_type: MetricType) -> Optional[float]:
        """Get latest value for specific metric"""
        relevant_metrics = [m for m in self.metrics if m.metric_type == metric_type]
        if not relevant_metrics:
            return None
        return max(relevant_metrics, key=lambda m: m.timestamp).value
    
    def get_engagement_rate(self) -> float:
        """Calculate overall engagement rate"""
        likes = self.get_metric_value(MetricType.LIKES) or 0
        comments = self.get_metric_value(MetricType.COMMENTS) or 0
        shares = self.get_metric_value(MetricType.SHARES) or 0
        impressions = self.get_metric_value(MetricType.IMPRESSIONS) or 1
        
        return (likes + comments + shares) / impressions if impressions > 0 else 0.0
    
    def get_roi(self) -> float:
        """Calculate return on investment"""
        revenue = self.cost_data.get("revenue_generated", 0)
        cost = self.cost_data.get("total_cost", 1)
        return (revenue - cost) / cost if cost > 0 else 0.0
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "content_id": self.content_id,
            "title": self.title,
            "platform": self.platform,
            "published_at": self.published_at,
            "metrics": [m.to_dict() for m in self.metrics],
            "content_type": self.content_type,
            "hashtags": self.hashtags,
            "audience_demographics": self.audience_demographics,
            "engagement_timeline": self.engagement_timeline,
            "cost_data": self.cost_data,
            "engagement_rate": self.get_engagement_rate(),
            "roi": self.get_roi()
        }


@dataclass
class PerformancePrediction:
    """AI-generated performance prediction"""
    content_id: str
    predicted_metrics: Dict[MetricType, float]
    confidence_score: float  # 0-1
    prediction_factors: List[str]
    similar_content_ids: List[str]
    optimization_recommendations: List[str]
    predicted_timeline: List[Tuple[float, Dict[str, float]]]  # (hours_after_post, metrics)
    created_at: float = field(default_factory=time.time)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "content_id": self.content_id,
            "predicted_metrics": {k.value: v for k, v in self.predicted_metrics.items()},
            "confidence_score": self.confidence_score,
            "prediction_factors": self.prediction_factors,
            "similar_content_ids": self.similar_content_ids,
            "optimization_recommendations": self.optimization_recommendations,
            "predicted_timeline": self.predicted_timeline,
            "created_at": self.created_at
        }


@dataclass
class CompetitorInsight:
    """Competitor analysis insight"""
    competitor_name: str
    platform: Platform
    content_analysis: Dict[str, Any]
    performance_benchmarks: Dict[str, float]
    successful_strategies: List[str]
    content_gaps: List[str]
    trending_topics: List[str]
    posting_patterns: Dict[str, Any]
    audience_overlap: float
    threat_level: str  # low, medium, high
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "competitor_name": self.competitor_name,
            "platform": self.platform,
            "content_analysis": self.content_analysis,
            "performance_benchmarks": self.performance_benchmarks,
            "successful_strategies": self.successful_strategies,
            "content_gaps": self.content_gaps,
            "trending_topics": self.trending_topics,
            "posting_patterns": self.posting_patterns,
            "audience_overlap": self.audience_overlap,
            "threat_level": self.threat_level
        }


class PerformanceAnalyzer:
    """Core performance analysis engine"""
    
    def __init__(self):
        self.text_service = None
        self.vector_service = None
    
    async def _get_services(self):
        """Initialize AI services"""
        if self.text_service is None:
            self.text_service = await get_text_service()
        if self.vector_service is None:
            self.vector_service = await get_vector_service()
    
    async def analyze_content_performance(
        self,
        performance_data: List[ContentPerformance],
        time_range: TimeRange = TimeRange.LAST_30D
    ) -> Dict[str, Any]:
        """Analyze content performance patterns and insights"""
        
        await self._get_services()
        
        if not performance_data:
            return {"error": "No performance data provided"}
        
        logger.info(f"Analyzing performance for {len(performance_data)} content pieces")
        
        # Filter data by time range
        cutoff_time = self._get_time_cutoff(time_range)
        recent_data = [p for p in performance_data if p.published_at >= cutoff_time]
        
        if not recent_data:
            return {"error": f"No data available for time range: {time_range}"}
        
        # Calculate aggregate metrics
        aggregate_metrics = self._calculate_aggregate_metrics(recent_data)
        
        # Identify top performers
        top_performers = self._identify_top_performers(recent_data)
        
        # Analyze performance patterns
        patterns = await self._analyze_performance_patterns(recent_data)
        
        # Generate insights using AI
        insights = await self._generate_performance_insights(recent_data, patterns)
        
        # Platform comparison
        platform_comparison = self._analyze_platform_performance(recent_data)
        
        # Content type analysis
        content_type_analysis = self._analyze_content_type_performance(recent_data)
        
        # Hashtag effectiveness  
        hashtag_analysis = self._analyze_hashtag_effectiveness(recent_data)
        
        # Audience insights
        audience_insights = self._analyze_audience_patterns(recent_data)
        
        return {
            "summary": {
                "total_content": len(recent_data),
                "time_range": time_range,
                "analysis_date": time.time()
            },
            "aggregate_metrics": aggregate_metrics,
            "top_performers": [p.to_dict() for p in top_performers],
            "performance_patterns": patterns,
            "ai_insights": insights,
            "platform_comparison": platform_comparison,
            "content_type_analysis": content_type_analysis,
            "hashtag_analysis": hashtag_analysis,
            "audience_insights": audience_insights
        }
    
    def _get_time_cutoff(self, time_range: TimeRange) -> float:
        """Get timestamp cutoff for time range"""
        now = time.time()
        
        cutoffs = {
            TimeRange.LAST_24H: now - (24 * 3600),
            TimeRange.LAST_7D: now - (7 * 24 * 3600),
            TimeRange.LAST_30D: now - (30 * 24 * 3600),
            TimeRange.LAST_90D: now - (90 * 24 * 3600),
            TimeRange.LAST_YEAR: now - (365 * 24 * 3600),
            TimeRange.ALL_TIME: 0
        }
        
        return cutoffs.get(time_range, now - (30 * 24 * 3600))
    
    def _calculate_aggregate_metrics(self, data: List[ContentPerformance]) -> Dict[str, float]:
        """Calculate aggregate performance metrics"""
        
        if not data:
            return {}
        
        # Collect all metric values
        metric_values = defaultdict(list)
        
        for content in data:
            for metric in content.metrics:
                metric_values[metric.metric_type].append(metric.value)
        
        # Calculate statistics for each metric
        aggregates = {}
        
        for metric_type, values in metric_values.items():
            if values:
                aggregates[f"{metric_type}_avg"] = statistics.mean(values)
                aggregates[f"{metric_type}_median"] = statistics.median(values)
                aggregates[f"{metric_type}_max"] = max(values)
                aggregates[f"{metric_type}_min"] = min(values)
                aggregates[f"{metric_type}_total"] = sum(values)
        
        # Calculate derived metrics
        total_engagement_rate = statistics.mean([c.get_engagement_rate() for c in data])
        total_roi = statistics.mean([c.get_roi() for c in data if c.get_roi() is not None])
        
        aggregates["avg_engagement_rate"] = total_engagement_rate
        aggregates["avg_roi"] = total_roi
        aggregates["content_count"] = len(data)
        
        return aggregates
    
    def _identify_top_performers(self, data: List[ContentPerformance], limit: int = 10) -> List[ContentPerformance]:
        """Identify top performing content"""
        
        # Sort by engagement rate, then by reach
        sorted_data = sorted(
            data,
            key=lambda c: (c.get_engagement_rate(), c.get_metric_value(MetricType.REACH) or 0),
            reverse=True
        )
        
        return sorted_data[:limit]
    
    async def _analyze_performance_patterns(self, data: List[ContentPerformance]) -> Dict[str, Any]:
        """Analyze patterns in performance data"""
        
        patterns = {}
        
        # Time-based patterns
        posting_times = []
        for content in data:
            post_time = time.localtime(content.published_at)
            posting_times.append({
                "hour": post_time.tm_hour,
                "day_of_week": post_time.tm_wday,
                "engagement_rate": content.get_engagement_rate()
            })
        
        # Best posting times
        hourly_performance = defaultdict(list)
        daily_performance = defaultdict(list)
        
        for post in posting_times:
            hourly_performance[post["hour"]].append(post["engagement_rate"])
            daily_performance[post["day_of_week"]].append(post["engagement_rate"])
        
        best_hours = sorted(
            [(hour, statistics.mean(rates)) for hour, rates in hourly_performance.items()],
            key=lambda x: x[1], reverse=True
        )[:3]
        
        best_days = sorted(
            [(day, statistics.mean(rates)) for day, rates in daily_performance.items()],
            key=lambda x: x[1], reverse=True
        )[:3]
        
        patterns["best_posting_hours"] = [{"hour": h, "avg_engagement": r} for h, r in best_hours]
        patterns["best_posting_days"] = [{"day": d, "avg_engagement": r} for d, r in best_days]
        
        # Content length patterns
        if data:
            # Assuming title length as proxy for content length
            length_performance = [(len(c.title), c.get_engagement_rate()) for c in data]
            
            # Group by length ranges
            short_content = [er for length, er in length_performance if length < 50]
            medium_content = [er for length, er in length_performance if 50 <= length < 100]
            long_content = [er for length, er in length_performance if length >= 100]
            
            patterns["content_length_analysis"] = {
                "short_content_avg_engagement": statistics.mean(short_content) if short_content else 0,
                "medium_content_avg_engagement": statistics.mean(medium_content) if medium_content else 0,
                "long_content_avg_engagement": statistics.mean(long_content) if long_content else 0
            }
        
        return patterns
    
    async def _generate_performance_insights(
        self,
        data: List[ContentPerformance],
        patterns: Dict[str, Any]
    ) -> List[str]:
        """Generate AI-powered performance insights"""
        
        # Prepare data summary for AI analysis
        summary = {
            "total_content": len(data),
            "avg_engagement_rate": statistics.mean([c.get_engagement_rate() for c in data]),
            "top_performing_titles": [c.title for c in sorted(data, key=lambda x: x.get_engagement_rate(), reverse=True)[:5]],
            "patterns": patterns
        }
        
        performance_prompt = await get_prompt_template("performance_analysis")
        
        # Generate insights with AI
        response = await self.text_service.generate(
            performance_prompt.format(
                performance_data=json.dumps(summary, indent=2),
                brand_name="Brand",  # Would be passed in real implementation
                time_period="30 days",
                platform="Multi-platform"
            ),
            max_tokens=800,
            temperature=0.3
        )
        
        if response.success:
            # Parse insights from AI response
            insights = []
            for line in response.content.strip().split('\n'):
                line = line.strip()
                if line and (line.startswith('-') or line.startswith('•') or line[0].isdigit()):
                    insight = line.lstrip('-•0123456789. ')
                    if len(insight) > 10:  # Valid insight
                        insights.append(insight)
            
            return insights[:10]  # Return top 10 insights
        
        # Fallback insights
        return [
            f"Analyzed {len(data)} content pieces with average engagement rate of {statistics.mean([c.get_engagement_rate() for c in data]):.2%}",
            "Top performers show consistent posting times and engaging titles",
            "Consider analyzing successful content patterns for future campaigns"
        ]
    
    def _analyze_platform_performance(self, data: List[ContentPerformance]) -> Dict[str, Any]:
        """Analyze performance across different platforms"""
        
        platform_data = defaultdict(list)
        
        for content in data:
            platform_data[content.platform].append(content)
        
        platform_analysis = {}
        
        for platform, contents in platform_data.items():
            if contents:
                avg_engagement = statistics.mean([c.get_engagement_rate() for c in contents])
                avg_reach = statistics.mean([c.get_metric_value(MetricType.REACH) or 0 for c in contents])
                total_content = len(contents)
                
                platform_analysis[platform] = {
                    "content_count": total_content,
                    "avg_engagement_rate": avg_engagement,
                    "avg_reach": avg_reach,
                    "top_performer": max(contents, key=lambda c: c.get_engagement_rate()).title
                }
        
        return platform_analysis
    
    def _analyze_content_type_performance(self, data: List[ContentPerformance]) -> Dict[str, Any]:
        """Analyze performance by content type"""
        
        type_data = defaultdict(list)
        
        for content in data:
            type_data[content.content_type].append(content)
        
        type_analysis = {}
        
        for content_type, contents in type_data.items():
            if contents:
                avg_engagement = statistics.mean([c.get_engagement_rate() for c in contents])
                total_content = len(contents)
                
                type_analysis[content_type] = {
                    "content_count": total_content,
                    "avg_engagement_rate": avg_engagement,
                    "performance_rank": 0  # Will be set after sorting
                }
        
        # Rank content types by performance
        sorted_types = sorted(type_analysis.items(), key=lambda x: x[1]["avg_engagement_rate"], reverse=True)
        
        for i, (content_type, data) in enumerate(sorted_types):
            type_analysis[content_type]["performance_rank"] = i + 1
        
        return type_analysis
    
    def _analyze_hashtag_effectiveness(self, data: List[ContentPerformance]) -> Dict[str, Any]:
        """Analyze hashtag effectiveness"""
        
        hashtag_performance = defaultdict(list)
        
        for content in data:
            engagement = content.get_engagement_rate()
            for hashtag in content.hashtags:
                hashtag_performance[hashtag].append(engagement)
        
        # Calculate average performance for each hashtag
        hashtag_analysis = {}
        
        for hashtag, engagements in hashtag_performance.items():
            if len(engagements) >= 2:  # Only include hashtags used multiple times
                hashtag_analysis[hashtag] = {
                    "usage_count": len(engagements),
                    "avg_engagement": statistics.mean(engagements),
                    "performance_consistency": 1 - (statistics.stdev(engagements) / statistics.mean(engagements)) if statistics.mean(engagements) > 0 else 0
                }
        
        # Sort by average engagement
        top_hashtags = sorted(
            hashtag_analysis.items(),
            key=lambda x: x[1]["avg_engagement"],
            reverse=True
        )[:10]
        
        return {
            "top_performing_hashtags": dict(top_hashtags),
            "total_unique_hashtags": len(hashtag_performance),
            "avg_hashtags_per_post": statistics.mean([len(c.hashtags) for c in data]) if data else 0
        }
    
    def _analyze_audience_patterns(self, data: List[ContentPerformance]) -> Dict[str, Any]:
        """Analyze audience engagement patterns"""
        
        if not data:
            return {}
        
        # Aggregate audience demographics
        total_demographics = defaultdict(int)
        total_engagement_by_demo = defaultdict(list)
        
        for content in data:
            engagement = content.get_engagement_rate()
            
            for demo_key, demo_value in content.audience_demographics.items():
                if isinstance(demo_value, dict):
                    for sub_key, count in demo_value.items():
                        key = f"{demo_key}_{sub_key}"
                        total_demographics[key] += count
                        total_engagement_by_demo[key].append(engagement)
        
        # Calculate engagement by demographic
        demo_engagement = {}
        for demo, engagements in total_engagement_by_demo.items():
            if engagements:
                demo_engagement[demo] = statistics.mean(engagements)
        
        # Find most engaging demographics
        top_demographics = sorted(
            demo_engagement.items(),
            key=lambda x: x[1],
            reverse=True
        )[:5]
        
        return {
            "top_engaging_demographics": dict(top_demographics),
            "total_audience_segments": len(total_demographics),
            "audience_diversity_score": len(total_demographics) / max(total_demographics.values()) if total_demographics else 0
        }


class PerformancePredictor:
    """AI-powered performance prediction engine"""
    
    def __init__(self):
        self.text_service = None
        self.vector_service = None
    
    async def _get_services(self):
        """Initialize AI services"""
        if self.text_service is None:
            self.text_service = await get_text_service()
        if self.vector_service is None:
            self.vector_service = await get_vector_service()
    
    async def predict_content_performance(
        self,
        content_title: str,
        content_description: str,
        platform: Platform,
        hashtags: List[str],
        posting_time: float,
        historical_data: List[ContentPerformance]
    ) -> PerformancePrediction:
        """Predict performance for new content"""
        
        await self._get_services()
        
        logger.info(f"Predicting performance for: {content_title}")
        
        # Find similar historical content
        similar_content = await self._find_similar_content(
            content_title, content_description, historical_data
        )
        
        # Analyze historical patterns
        patterns = await self._analyze_historical_patterns(historical_data, platform)
        
        # Generate predictions using AI
        ai_predictions = await self._generate_ai_predictions(
            content_title, content_description, platform, hashtags, similar_content, patterns
        )
        
        # Calculate confidence score
        confidence = self._calculate_prediction_confidence(similar_content, patterns)
        
        # Generate optimization recommendations
        recommendations = await self._generate_optimization_recommendations(
            content_title, content_description, similar_content, patterns
        )
        
        # Create prediction timeline
        timeline = self._create_prediction_timeline(ai_predictions)
        
        return PerformancePrediction(
            content_id=f"pred_{int(time.time())}",
            predicted_metrics=ai_predictions,
            confidence_score=confidence,
            prediction_factors=[
                f"Based on {len(similar_content)} similar content pieces",
                f"Platform: {platform} historical performance",
                f"Posting time analysis",
                f"Hashtag effectiveness data"
            ],
            similar_content_ids=[c.content_id for c in similar_content],
            optimization_recommendations=recommendations,
            predicted_timeline=timeline
        )
    
    async def _find_similar_content(
        self,
        title: str,
        description: str,
        historical_data: List[ContentPerformance]
    ) -> List[ContentPerformance]:
        """Find similar content from historical data"""
        
        try:
            # Use vector similarity to find similar content
            query_text = f"{title} {description}"
            
            # Create embeddings for all historical content (in production, these would be pre-computed)
            historical_texts = [f"{c.title} {' '.join(c.hashtags)}" for c in historical_data]
            
            if not historical_texts:
                return []
            
            # For now, use simple text similarity (in production, use vector embeddings)
            similar_content = []
            query_words = set(query_text.lower().split())
            
            for content in historical_data:
                content_words = set(f"{content.title} {' '.join(content.hashtags)}".lower().split())
                similarity = len(query_words.intersection(content_words)) / len(query_words.union(content_words))
                
                if similarity > 0.1:  # Threshold for similarity
                    similar_content.append((content, similarity))
            
            # Sort by similarity and return top matches
            similar_content.sort(key=lambda x: x[1], reverse=True)
            return [content for content, _ in similar_content[:10]]
            
        except Exception as e:
            logger.error(f"Error finding similar content: {e}")
            return historical_data[:5]  # Fallback to recent content
    
    async def _analyze_historical_patterns(
        self,
        historical_data: List[ContentPerformance],
        platform: Platform
    ) -> Dict[str, Any]:
        """Analyze patterns in historical data"""
        
        if not historical_data:
            return {}
        
        # Filter by platform
        platform_data = [c for c in historical_data if c.platform == platform]
        
        if not platform_data:
            platform_data = historical_data  # Use all data if no platform-specific data
        
        patterns = {}
        
        # Average metrics for platform
        avg_metrics = {}
        for metric_type in MetricType:
            values = [c.get_metric_value(metric_type) for c in platform_data]
            valid_values = [v for v in values if v is not None]
            if valid_values:
                avg_metrics[metric_type] = statistics.mean(valid_values)
        
        patterns["platform_averages"] = avg_metrics
        
        # Engagement rate distribution
        engagement_rates = [c.get_engagement_rate() for c in platform_data]
        if engagement_rates:
            patterns["engagement_stats"] = {
                "mean": statistics.mean(engagement_rates),
                "median": statistics.median(engagement_rates),
                "p75": np.percentile(engagement_rates, 75),
                "p90": np.percentile(engagement_rates, 90)
            }
        
        # Best performing characteristics
        top_performers = sorted(platform_data, key=lambda x: x.get_engagement_rate(), reverse=True)[:5]
        
        if top_performers:
            patterns["top_performer_characteristics"] = {
                "avg_title_length": statistics.mean([len(c.title) for c in top_performers]),
                "common_hashtags": self._find_common_hashtags([c.hashtags for c in top_performers]),
                "avg_hashtag_count": statistics.mean([len(c.hashtags) for c in top_performers])
            }
        
        return patterns
    
    def _find_common_hashtags(self, hashtag_lists: List[List[str]]) -> List[str]:
        """Find commonly used hashtags"""
        hashtag_counts = defaultdict(int)
        
        for hashtags in hashtag_lists:
            for hashtag in hashtags:
                hashtag_counts[hashtag] += 1
        
        # Return hashtags used in at least 40% of top performers
        threshold = len(hashtag_lists) * 0.4
        common_hashtags = [tag for tag, count in hashtag_counts.items() if count >= threshold]
        
        return sorted(common_hashtags, key=lambda x: hashtag_counts[x], reverse=True)[:10]
    
    async def _generate_ai_predictions(
        self,
        title: str,
        description: str,
        platform: Platform,
        hashtags: List[str],
        similar_content: List[ContentPerformance],
        patterns: Dict[str, Any]
    ) -> Dict[MetricType, float]:
        """Generate AI-powered performance predictions"""
        
        # Base predictions on similar content and patterns
        predictions = {}
        
        if similar_content:
            # Average metrics from similar content
            for metric_type in MetricType:
                values = [c.get_metric_value(metric_type) for c in similar_content]
                valid_values = [v for v in values if v is not None and v > 0]
                
                if valid_values:
                    base_prediction = statistics.mean(valid_values)
                    
                    # Apply adjustments based on patterns and content characteristics
                    adjustment = 1.0
                    
                    # Title length adjustment
                    if patterns.get("top_performer_characteristics"):
                        optimal_length = patterns["top_performer_characteristics"].get("avg_title_length", 50)
                        length_diff = abs(len(title) - optimal_length) / optimal_length
                        adjustment *= (1 - length_diff * 0.1)  # Up to 10% adjustment
                    
                    # Hashtag count adjustment
                    if patterns.get("top_performer_characteristics"):
                        optimal_hashtag_count = patterns["top_performer_characteristics"].get("avg_hashtag_count", 5)
                        hashtag_diff = abs(len(hashtags) - optimal_hashtag_count) / optimal_hashtag_count
                        adjustment *= (1 - hashtag_diff * 0.05)  # Up to 5% adjustment
                    
                    # Platform-specific adjustments
                    platform_multipliers = {
                        Platform.TIKTOK: {"engagement_rate": 1.2, "reach": 1.5},
                        Platform.INSTAGRAM: {"engagement_rate": 1.0, "reach": 1.0},
                        Platform.YOUTUBE_SHORTS: {"engagement_rate": 1.1, "reach": 1.3}
                    }
                    
                    if platform in platform_multipliers:
                        if metric_type.value in platform_multipliers[platform]:
                            adjustment *= platform_multipliers[platform][metric_type.value]
                    
                    predictions[metric_type] = base_prediction * adjustment
        
        else:
            # Fallback to platform averages if no similar content
            platform_averages = patterns.get("platform_averages", {})
            for metric_type in MetricType:
                if metric_type in platform_averages:
                    predictions[metric_type] = platform_averages[metric_type]
        
        # Ensure reasonable predictions
        predictions = self._validate_predictions(predictions, platform)
        
        return predictions
    
    def _validate_predictions(self, predictions: Dict[MetricType, float], platform: Platform) -> Dict[MetricType, float]:
        """Validate and adjust predictions to reasonable ranges"""
        
        # Platform-specific reasonable ranges
        reasonable_ranges = {
            Platform.TIKTOK: {
                MetricType.ENGAGEMENT_RATE: (0.01, 0.20),
                MetricType.REACH: (1000, 1000000),
                MetricType.LIKES: (10, 100000),
                MetricType.COMMENTS: (1, 5000),
                MetricType.SHARES: (1, 10000)
            },
            Platform.INSTAGRAM: {
                MetricType.ENGAGEMENT_RATE: (0.005, 0.10),
                MetricType.REACH: (500, 500000),
                MetricType.LIKES: (5, 50000),
                MetricType.COMMENTS: (1, 2000),
                MetricType.SHARES: (1, 5000)
            },
            Platform.YOUTUBE_SHORTS: {
                MetricType.ENGAGEMENT_RATE: (0.01, 0.15),
                MetricType.REACH: (1000, 2000000),
                MetricType.LIKES: (10, 200000),
                MetricType.COMMENTS: (1, 10000),
                MetricType.VIEW_DURATION: (0.1, 1.0)
            }
        }
        
        ranges = reasonable_ranges.get(platform, reasonable_ranges[Platform.INSTAGRAM])
        
        validated_predictions = {}
        for metric_type, value in predictions.items():
            if metric_type in ranges:
                min_val, max_val = ranges[metric_type]
                validated_predictions[metric_type] = max(min_val, min(max_val, value))
            else:
                validated_predictions[metric_type] = value
        
        return validated_predictions
    
    def _calculate_prediction_confidence(
        self,
        similar_content: List[ContentPerformance],
        patterns: Dict[str, Any]
    ) -> float:
        """Calculate confidence score for predictions"""
        
        confidence = 0.5  # Base confidence
        
        # More similar content = higher confidence
        if similar_content:
            confidence += min(len(similar_content) * 0.05, 0.3)  # Up to 30% boost
        
        # Strong patterns = higher confidence
        if patterns.get("engagement_stats"):
            # Lower variance in historical data = higher confidence
            engagement_stats = patterns["engagement_stats"]
            variance = (engagement_stats.get("p90", 0) - engagement_stats.get("median", 0)) / engagement_stats.get("median", 1)
            confidence += max(0, (1 - variance) * 0.2)  # Up to 20% boost for low variance
        
        # Ensure confidence is between 0 and 1
        return max(0.1, min(0.95, confidence))
    
    async def _generate_optimization_recommendations(
        self,
        title: str,
        description: str,
        similar_content: List[ContentPerformance],
        patterns: Dict[str, Any]
    ) -> List[str]:
        """Generate optimization recommendations"""
        
        recommendations = []
        
        # Title optimization
        if patterns.get("top_performer_characteristics"):
            optimal_length = patterns["top_performer_characteristics"].get("avg_title_length", 50)
            if len(title) > optimal_length * 1.2:
                recommendations.append(f"Consider shortening title to around {int(optimal_length)} characters for better performance")
            elif len(title) < optimal_length * 0.8:
                recommendations.append(f"Consider expanding title to around {int(optimal_length)} characters")
        
        # Hashtag recommendations
        if patterns.get("top_performer_characteristics", {}).get("common_hashtags"):
            common_tags = patterns["top_performer_characteristics"]["common_hashtags"]
            recommendations.append(f"Consider using these high-performing hashtags: {', '.join(common_tags[:3])}")
        
        # Timing recommendations
        if similar_content:
            successful_times = []
            for content in similar_content[:3]:  # Top 3 similar content
                post_time = time.localtime(content.published_at)
                successful_times.append(post_time.tm_hour)
            
            if successful_times:
                avg_hour = int(statistics.mean(successful_times))
                recommendations.append(f"Optimal posting time appears to be around {avg_hour}:00 based on similar content")
        
        # Content-specific recommendations
        if len(recommendations) < 3:
            recommendations.extend([
                "Include a strong call-to-action to boost engagement",
                "Use high-quality visuals to increase reach",
                "Engage with comments quickly to boost algorithm favorability"
            ])
        
        return recommendations[:5]  # Return top 5 recommendations
    
    def _create_prediction_timeline(self, predictions: Dict[MetricType, float]) -> List[Tuple[float, Dict[str, float]]]:
        """Create predicted performance timeline"""
        
        timeline = []
        
        # Typical engagement curve over 24 hours
        time_points = [0.5, 1, 2, 4, 8, 12, 24]  # Hours after posting
        engagement_curve = [0.1, 0.3, 0.5, 0.7, 0.9, 0.95, 1.0]  # Cumulative engagement
        
        for hours, engagement_percent in zip(time_points, engagement_curve):
            timeline_metrics = {}
            
            for metric_type, final_value in predictions.items():
                if metric_type in [MetricType.LIKES, MetricType.COMMENTS, MetricType.SHARES, MetricType.REACH]:
                    timeline_metrics[metric_type.value] = final_value * engagement_percent
                elif metric_type == MetricType.ENGAGEMENT_RATE:
                    # Engagement rate stabilizes over time
                    timeline_metrics[metric_type.value] = final_value * min(1.0, engagement_percent + 0.2)
            
            timeline.append((hours, timeline_metrics))
        
        return timeline


class CompetitorAnalyzer:
    """AI-powered competitor analysis"""
    
    def __init__(self):
        self.text_service = None
        self.vector_service = None
    
    async def _get_services(self):
        """Initialize AI services"""
        if self.text_service is None:
            self.text_service = await get_text_service()
        if self.vector_service is None:
            self.vector_service = await get_vector_service()
    
    async def analyze_competitors(
        self,
        brand_name: str,
        industry: str,
        platform: Platform,
        competitor_names: List[str],
        own_performance_data: List[ContentPerformance]
    ) -> List[CompetitorInsight]:
        """Analyze competitors and generate insights"""
        
        await self._get_services()
        
        logger.info(f"Analyzing {len(competitor_names)} competitors for {brand_name}")
        
        insights = []
        
        for competitor in competitor_names:
            # In production, this would fetch real competitor data
            # For now, generate mock insights
            insight = await self._analyze_single_competitor(
                competitor, brand_name, industry, platform, own_performance_data
            )
            insights.append(insight)
        
        return insights
    
    async def _analyze_single_competitor(
        self,
        competitor_name: str,
        brand_name: str,
        industry: str,
        platform: Platform,
        own_performance_data: List[ContentPerformance]
    ) -> CompetitorInsight:
        """Analyze a single competitor"""
        
        # Mock competitor data (in production, use real data sources)
        mock_competitor_data = self._generate_mock_competitor_data(competitor_name, platform)
        
        # Analyze content patterns
        content_analysis = await self._analyze_competitor_content(mock_competitor_data)
        
        # Benchmark performance
        performance_benchmarks = self._benchmark_competitor_performance(
            mock_competitor_data, own_performance_data
        )
        
        # Identify successful strategies
        successful_strategies = await self._identify_successful_strategies(mock_competitor_data)
        
        # Find content gaps
        content_gaps = await self._identify_content_gaps(
            mock_competitor_data, own_performance_data
        )
        
        # Analyze trending topics
        trending_topics = self._analyze_competitor_trends(mock_competitor_data)
        
        # Analyze posting patterns
        posting_patterns = self._analyze_posting_patterns(mock_competitor_data)
        
        # Calculate audience overlap (mock)
        audience_overlap = 0.3  # 30% overlap
        
        # Determine threat level
        threat_level = self._assess_threat_level(performance_benchmarks, audience_overlap)
        
        return CompetitorInsight(
            competitor_name=competitor_name,
            platform=platform,
            content_analysis=content_analysis,
            performance_benchmarks=performance_benchmarks,
            successful_strategies=successful_strategies,
            content_gaps=content_gaps,
            trending_topics=trending_topics,
            posting_patterns=posting_patterns,
            audience_overlap=audience_overlap,
            threat_level=threat_level
        )
    
    def _generate_mock_competitor_data(self, competitor_name: str, platform: Platform) -> List[Dict[str, Any]]:
        """Generate mock competitor data"""
        
        # Mock content data
        mock_content = []
        
        for i in range(20):  # 20 pieces of content
            mock_content.append({
                "title": f"{competitor_name} content piece {i+1}",
                "engagement_rate": 0.02 + (i % 5) * 0.01,  # Varying engagement
                "reach": 10000 + (i * 500),
                "likes": 200 + (i * 50),
                "comments": 20 + (i * 5),
                "shares": 10 + (i * 2),
                "hashtags": [f"#{competitor_name.lower()}", "#industry", f"#topic{i%3}"],
                "posted_at": time.time() - (i * 24 * 3600),  # Spread over time
                "content_type": ["video", "image", "carousel"][i % 3]
            })
        
        return mock_content
    
    async def _analyze_competitor_content(self, competitor_data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Analyze competitor content patterns"""
        
        if not competitor_data:
            return {}
        
        analysis = {}
        
        # Content type distribution
        content_types = [item["content_type"] for item in competitor_data]
        type_counts = {ct: content_types.count(ct) for ct in set(content_types)}
        analysis["content_type_distribution"] = type_counts
        
        # Average engagement by content type
        type_engagement = defaultdict(list)
        for item in competitor_data:
            type_engagement[item["content_type"]].append(item["engagement_rate"])
        
        analysis["engagement_by_content_type"] = {
            ct: statistics.mean(rates) for ct, rates in type_engagement.items()
        }
        
        # Title patterns
        titles = [item["title"] for item in competitor_data]
        avg_title_length = statistics.mean([len(title) for title in titles])
        analysis["avg_title_length"] = avg_title_length
        
        # Hashtag analysis
        all_hashtags = []
        for item in competitor_data:
            all_hashtags.extend(item["hashtags"])
        
        hashtag_counts = {tag: all_hashtags.count(tag) for tag in set(all_hashtags)}
        top_hashtags = sorted(hashtag_counts.items(), key=lambda x: x[1], reverse=True)[:10]
        analysis["top_hashtags"] = dict(top_hashtags)
        
        return analysis
    
    def _benchmark_competitor_performance(
        self,
        competitor_data: List[Dict[str, Any]],
        own_data: List[ContentPerformance]
    ) -> Dict[str, float]:
        """Benchmark competitor performance against own performance"""
        
        if not competitor_data or not own_data:
            return {}
        
        # Calculate competitor averages
        competitor_avg_engagement = statistics.mean([item["engagement_rate"] for item in competitor_data])
        competitor_avg_reach = statistics.mean([item["reach"] for item in competitor_data])
        competitor_avg_likes = statistics.mean([item["likes"] for item in competitor_data])
        
        # Calculate own averages
        own_avg_engagement = statistics.mean([c.get_engagement_rate() for c in own_data])
        own_avg_reach = statistics.mean([c.get_metric_value(MetricType.REACH) or 0 for c in own_data])
        own_avg_likes = statistics.mean([c.get_metric_value(MetricType.LIKES) or 0 for c in own_data])
        
        # Calculate ratios (competitor vs own performance)
        benchmarks = {
            "engagement_rate_ratio": competitor_avg_engagement / own_avg_engagement if own_avg_engagement > 0 else 1.0,
            "reach_ratio": competitor_avg_reach / own_avg_reach if own_avg_reach > 0 else 1.0,
            "likes_ratio": competitor_avg_likes / own_avg_likes if own_avg_likes > 0 else 1.0,
            "competitor_avg_engagement": competitor_avg_engagement,
            "competitor_avg_reach": competitor_avg_reach
        }
        
        return benchmarks
    
    async def _identify_successful_strategies(self, competitor_data: List[Dict[str, Any]]) -> List[str]:
        """Identify competitor's successful strategies"""
        
        if not competitor_data:
            return []
        
        # Find top performing content
        top_performers = sorted(competitor_data, key=lambda x: x["engagement_rate"], reverse=True)[:5]
        
        strategies = []
        
        # Analyze patterns in top performers
        top_content_types = [item["content_type"] for item in top_performers]
        most_common_type = max(set(top_content_types), key=top_content_types.count)
        strategies.append(f"Focuses heavily on {most_common_type} content")
        
        # Hashtag strategies
        top_hashtags = []
        for item in top_performers:
            top_hashtags.extend(item["hashtags"])
        
        common_hashtags = [tag for tag in set(top_hashtags) if top_hashtags.count(tag) >= 2]
        if common_hashtags:
            strategies.append(f"Consistently uses hashtags: {', '.join(common_hashtags[:3])}")
        
        # Engagement patterns
        high_engagement_items = [item for item in competitor_data if item["engagement_rate"] > 0.05]
        if len(high_engagement_items) > len(competitor_data) * 0.3:
            strategies.append("Maintains consistently high engagement rates")
        
        # Fallback strategies
        if len(strategies) < 3:
            strategies.extend([
                "Posts regularly with consistent branding",
                "Engages actively with audience comments",
                "Uses trending topics and hashtags effectively"
            ])
        
        return strategies[:5]
    
    async def _identify_content_gaps(
        self,
        competitor_data: List[Dict[str, Any]],
        own_data: List[ContentPerformance]
    ) -> List[str]:
        """Identify content gaps and opportunities"""
        
        gaps = []
        
        if not competitor_data or not own_data:
            return ["Insufficient data to identify content gaps"]
        
        # Compare content types
        competitor_types = [item["content_type"] for item in competitor_data]
        own_types = [c.content_type for c in own_data]
        
        competitor_type_counts = {ct: competitor_types.count(ct) for ct in set(competitor_types)}
        own_type_counts = {ct: own_types.count(ct) for ct in set(own_types)}
        
        # Find content types competitor uses more
        for content_type, comp_count in competitor_type_counts.items():
            own_count = own_type_counts.get(content_type, 0)
            comp_ratio = comp_count / len(competitor_data)
            own_ratio = own_count / len(own_data) if own_data else 0
            
            if comp_ratio > own_ratio + 0.2:  # Significant difference
                gaps.append(f"Underutilizing {content_type} content (competitor: {comp_ratio:.1%}, you: {own_ratio:.1%})")
        
        # Compare hashtag usage
        competitor_hashtags = set()
        for item in competitor_data:
            competitor_hashtags.update(item["hashtags"])
        
        own_hashtags = set()
        for content in own_data:
            own_hashtags.update(content.hashtags)
        
        unique_competitor_hashtags = competitor_hashtags - own_hashtags
        if unique_competitor_hashtags:
            gaps.append(f"Missing hashtag opportunities: {', '.join(list(unique_competitor_hashtags)[:3])}")
        
        # Generic gaps if none found
        if not gaps:
            gaps = [
                "Consider diversifying content types",
                "Explore trending topics in your industry",
                "Analyze competitor engagement strategies"
            ]
        
        return gaps[:5]
    
    def _analyze_competitor_trends(self, competitor_data: List[Dict[str, Any]]) -> List[str]:
        """Analyze trending topics from competitor data"""
        
        if not competitor_data:
            return []
        
        # Extract hashtags from recent content (last 7 days)
        recent_cutoff = time.time() - (7 * 24 * 3600)
        recent_content = [item for item in competitor_data if item["posted_at"] >= recent_cutoff]
        
        if not recent_content:
            recent_content = competitor_data[:5]  # Use most recent
        
        trending_hashtags = []
        for item in recent_content:
            trending_hashtags.extend(item["hashtags"])
        
        # Count hashtag frequency
        hashtag_counts = {tag: trending_hashtags.count(tag) for tag in set(trending_hashtags)}
        trending_topics = sorted(hashtag_counts.items(), key=lambda x: x[1], reverse=True)
        
        return [topic for topic, count in trending_topics[:10]]
    
    def _analyze_posting_patterns(self, competitor_data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Analyze competitor posting patterns"""
        
        if not competitor_data:
            return {}
        
        # Posting frequency
        posting_times = [item["posted_at"] for item in competitor_data]
        posting_times.sort()
        
        # Calculate intervals between posts
        intervals = []
        for i in range(1, len(posting_times)):
            interval = posting_times[i] - posting_times[i-1]
            intervals.append(interval)
        
        if intervals:
            avg_interval_hours = statistics.mean(intervals) / 3600
            posting_frequency = f"Every {avg_interval_hours:.1f} hours"
        else:
            posting_frequency = "Irregular"
        
        # Best performing days/times (mock analysis)
        patterns = {
            "posting_frequency": posting_frequency,
            "avg_posts_per_week": len(competitor_data) / 4,  # Assuming 4 weeks of data
            "most_active_time": "2-4 PM",  # Mock data
            "best_day": "Wednesday"  # Mock data
        }
        
        return patterns
    
    def _assess_threat_level(self, benchmarks: Dict[str, float], audience_overlap: float) -> str:
        """Assess competitor threat level"""
        
        # Calculate threat score
        threat_score = 0
        
        # Performance comparison
        engagement_ratio = benchmarks.get("engagement_rate_ratio", 1.0)
        reach_ratio = benchmarks.get("reach_ratio", 1.0)
        
        if engagement_ratio > 1.5:
            threat_score += 2
        elif engagement_ratio > 1.2:
            threat_score += 1
        
        if reach_ratio > 1.5:
            threat_score += 2
        elif reach_ratio > 1.2:
            threat_score += 1
        
        # Audience overlap
        if audience_overlap > 0.5:
            threat_score += 2
        elif audience_overlap > 0.3:
            threat_score += 1
        
        # Determine threat level
        if threat_score >= 4:
            return "high"
        elif threat_score >= 2:
            return "medium"
        else:
            return "low"


class PerformanceAnalysisService:
    """Main service for performance analysis and optimization"""
    
    def __init__(self):
        self.analyzer = PerformanceAnalyzer()
        self.predictor = PerformancePredictor()
        self.competitor_analyzer = CompetitorAnalyzer()
    
    async def comprehensive_analysis(
        self,
        brand_name: str,
        performance_data: List[ContentPerformance],
        time_range: TimeRange = TimeRange.LAST_30D,
        competitors: List[str] = None,
        platform: Platform = Platform.INSTAGRAM
    ) -> Dict[str, Any]:
        """Run comprehensive performance analysis"""
        
        logger.info(f"Running comprehensive analysis for {brand_name}")
        
        # Performance analysis
        performance_analysis = await self.analyzer.analyze_content_performance(
            performance_data, time_range
        )
        
        # Competitor analysis
        competitor_insights = []
        if competitors:
            competitor_insights = await self.competitor_analyzer.analyze_competitors(
                brand_name, "Technology", platform, competitors, performance_data
            )
        
        # ROI analysis
        roi_analysis = self._analyze_roi(performance_data)
        
        # Generate strategic recommendations
        strategic_recommendations = await self._generate_strategic_recommendations(
            performance_analysis, competitor_insights, roi_analysis
        )
        
        return {
            "brand_name": brand_name,
            "analysis_timestamp": time.time(),
            "time_range": time_range,
            "performance_analysis": performance_analysis,
            "competitor_insights": [c.to_dict() for c in competitor_insights],
            "roi_analysis": roi_analysis,
            "strategic_recommendations": strategic_recommendations,
            "summary": {
                "total_content_analyzed": len(performance_data),
                "competitors_analyzed": len(competitor_insights),
                "key_insights_count": len(strategic_recommendations)
            }
        }
    
    def _analyze_roi(self, performance_data: List[ContentPerformance]) -> Dict[str, Any]:
        """Analyze return on investment"""
        
        if not performance_data:
            return {}
        
        # Calculate ROI metrics
        total_cost = sum(c.cost_data.get("total_cost", 0) for c in performance_data)
        total_revenue = sum(c.cost_data.get("revenue_generated", 0) for c in performance_data)
        
        if total_cost > 0:
            overall_roi = (total_revenue - total_cost) / total_cost
        else:
            overall_roi = 0.0
        
        # ROI by content type
        roi_by_type = defaultdict(list)
        for content in performance_data:
            content_roi = content.get_roi()
            if content_roi is not None:
                roi_by_type[content.content_type].append(content_roi)
        
        avg_roi_by_type = {
            content_type: statistics.mean(rois) 
            for content_type, rois in roi_by_type.items()
        }
        
        # ROI by platform
        roi_by_platform = defaultdict(list)
        for content in performance_data:
            content_roi = content.get_roi()
            if content_roi is not None:
                roi_by_platform[content.platform].append(content_roi)
        
        avg_roi_by_platform = {
            platform: statistics.mean(rois) 
            for platform, rois in roi_by_platform.items()
        }
        
        # Cost efficiency
        cost_per_engagement = 0
        total_engagements = sum(
            (c.get_metric_value(MetricType.LIKES) or 0) +
            (c.get_metric_value(MetricType.COMMENTS) or 0) +
            (c.get_metric_value(MetricType.SHARES) or 0)
            for c in performance_data
        )
        
        if total_engagements > 0 and total_cost > 0:
            cost_per_engagement = total_cost / total_engagements
        
        return {
            "overall_roi": overall_roi,
            "total_cost": total_cost,
            "total_revenue": total_revenue,
            "roi_by_content_type": avg_roi_by_type,
            "roi_by_platform": avg_roi_by_platform,
            "cost_per_engagement": cost_per_engagement,
            "profitable_content_ratio": len([c for c in performance_data if c.get_roi() > 0]) / len(performance_data)
        }
    
    async def _generate_strategic_recommendations(
        self,
        performance_analysis: Dict[str, Any],
        competitor_insights: List[CompetitorInsight],
        roi_analysis: Dict[str, Any]
    ) -> List[str]:
        """Generate strategic recommendations"""
        
        recommendations = []
        
        # Performance-based recommendations
        if performance_analysis.get("platform_comparison"):
            platform_data = performance_analysis["platform_comparison"]
            best_platform = max(platform_data.items(), key=lambda x: x[1].get("avg_engagement_rate", 0))
            recommendations.append(f"Focus more resources on {best_platform[0]} (highest engagement: {best_platform[1].get('avg_engagement_rate', 0):.2%})")
        
        # Content type recommendations
        if performance_analysis.get("content_type_analysis"):
            type_analysis = performance_analysis["content_type_analysis"]
            best_type = min(type_analysis.items(), key=lambda x: x[1].get("performance_rank", 999))
            recommendations.append(f"Increase {best_type[0]} content production (top performing type)")
        
        # ROI-based recommendations
        if roi_analysis.get("roi_by_content_type"):
            best_roi_type = max(roi_analysis["roi_by_content_type"].items(), key=lambda x: x[1])
            if best_roi_type[1] > 0:
                recommendations.append(f"Scale {best_roi_type[0]} content (highest ROI: {best_roi_type[1]:.1%})")
        
        # Competitor-based recommendations
        for insight in competitor_insights[:2]:  # Top 2 competitors
            if insight.threat_level == "high":
                recommendations.append(f"Address competitive threat from {insight.competitor_name}: {insight.successful_strategies[0] if insight.successful_strategies else 'Monitor closely'}")
            
            if insight.content_gaps:
                recommendations.append(f"Content opportunity: {insight.content_gaps[0]}")
        
        # Cost optimization
        if roi_analysis.get("cost_per_engagement", 0) > 0.1:  # High cost per engagement
            recommendations.append("Optimize content costs - current cost per engagement is high")
        
        # Timing optimization
        if performance_analysis.get("performance_patterns", {}).get("best_posting_hours"):
            best_hours = performance_analysis["performance_patterns"]["best_posting_hours"]
            if best_hours:
                recommendations.append(f"Optimize posting schedule: best performance at {best_hours[0]['hour']}:00")
        
        return recommendations[:8]  # Return top 8 recommendations


# Global service instance
_performance_analysis_service: Optional[PerformanceAnalysisService] = None


async def get_performance_analysis_service() -> PerformanceAnalysisService:
    """Get global performance analysis service instance"""
    global _performance_analysis_service
    if _performance_analysis_service is None:
        _performance_analysis_service = PerformanceAnalysisService()
    return _performance_analysis_service