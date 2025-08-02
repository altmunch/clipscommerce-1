"""
Trend Analysis AI Service

Real-time trend detection, analysis, and integration for viral content creation.
Monitors trending topics, hashtags, sounds, and content patterns across platforms.
"""

import asyncio
import json
import re
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Set, Tuple
import logging
from collections import defaultdict, Counter
import statistics

import aiohttp
import numpy as np
from diskcache import Cache

from app.core.config import settings
from app.services.ai.providers import get_text_service
from app.services.ai.vector_db import get_vector_service
from app.services.ai.viral_content import Platform

logger = logging.getLogger(__name__)

# Cache for trend data
trend_cache = Cache("/tmp/viralos_trend_cache", size_limit=500000000)  # 500MB cache


class TrendType(str, Enum):
    """Types of trends"""
    HASHTAG = "hashtag"
    TOPIC = "topic"
    SOUND = "sound"
    CHALLENGE = "challenge"
    MEME = "meme"
    NEWS_EVENT = "news_event"
    SEASONAL = "seasonal"
    VIRAL_FORMAT = "viral_format"


class TrendStatus(str, Enum):
    """Trend lifecycle status"""
    EMERGING = "emerging"
    RISING = "rising"
    PEAK = "peak"
    DECLINING = "declining"
    FADING = "fading"
    REVIVED = "revived"


class TrendSource(str, Enum):
    """Sources for trend data"""
    GOOGLE_TRENDS = "google_trends"
    SOCIAL_PLATFORMS = "social_platforms"
    NEWS_API = "news_api"
    INFLUENCER_MONITORING = "influencer_monitoring"
    HASHTAG_TRACKING = "hashtag_tracking"
    AI_DETECTION = "ai_detection"


@dataclass
class TrendSignal:
    """Individual trend signal/indicator"""
    signal_id: str
    content: str
    signal_strength: float  # 0-1
    platform: Platform
    source: TrendSource
    detected_at: float
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "signal_id": self.signal_id,
            "content": self.content,
            "signal_strength": self.signal_strength,
            "platform": self.platform,
            "source": self.source,
            "detected_at": self.detected_at,
            "metadata": self.metadata
        }


@dataclass
class TrendData:
    """Comprehensive trend information"""
    trend_id: str
    name: str
    trend_type: TrendType
    platform: Platform
    status: TrendStatus
    viral_score: float  # 0-100
    growth_rate: float  # percentage change
    volume: int  # number of mentions/uses
    engagement_rate: float
    demographic_data: Dict[str, Any]
    geographic_data: Dict[str, Any]
    signals: List[TrendSignal]
    related_trends: List[str]
    keywords: List[str]
    first_detected: float
    peak_time: Optional[float]
    predicted_lifespan: float  # hours
    content_examples: List[Dict[str, Any]]
    influencer_adoption: List[str]
    brand_opportunities: List[str]
    risk_factors: List[str]
    last_updated: float = field(default_factory=time.time)
    
    def is_fresh(self, max_age_hours: int = 2) -> bool:
        """Check if trend data is still fresh"""
        age_hours = (time.time() - self.last_updated) / 3600
        return age_hours < max_age_hours
    
    def get_trend_velocity(self) -> float:
        """Calculate trend velocity (growth rate / time)"""
        age_hours = (time.time() - self.first_detected) / 3600
        return self.growth_rate / max(age_hours, 1)
    
    def get_adoption_stage(self) -> str:
        """Determine adoption stage based on volume and signals"""
        if self.volume < 1000:
            return "innovators"
        elif self.volume < 10000:
            return "early_adopters"
        elif self.volume < 100000:
            return "early_majority"
        elif self.volume < 1000000:
            return "late_majority"
        else:
            return "laggards"
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "trend_id": self.trend_id,
            "name": self.name,
            "trend_type": self.trend_type,
            "platform": self.platform,
            "status": self.status,
            "viral_score": self.viral_score,
            "growth_rate": self.growth_rate,
            "volume": self.volume,
            "engagement_rate": self.engagement_rate,
            "demographic_data": self.demographic_data,
            "geographic_data": self.geographic_data,
            "signals": [s.to_dict() for s in self.signals],
            "related_trends": self.related_trends,
            "keywords": self.keywords,
            "first_detected": self.first_detected,
            "peak_time": self.peak_time,
            "predicted_lifespan": self.predicted_lifespan,
            "content_examples": self.content_examples,
            "influencer_adoption": self.influencer_adoption,
            "brand_opportunities": self.brand_opportunities,
            "risk_factors": self.risk_factors,
            "last_updated": self.last_updated,
            "trend_velocity": self.get_trend_velocity(),
            "adoption_stage": self.get_adoption_stage()
        }


@dataclass
class TrendOpportunity:
    """Identified trend opportunity for brand"""
    opportunity_id: str
    trend_id: str
    trend_name: str
    opportunity_type: str  # "early_entry", "trend_hijack", "counter_trend", etc.
    relevance_score: float  # 0-1
    effort_level: str  # "low", "medium", "high"
    potential_impact: str  # "low", "medium", "high"
    time_sensitivity: str  # "urgent", "moderate", "flexible"
    recommended_actions: List[str]
    content_suggestions: List[str]
    hashtag_recommendations: List[str]
    target_audience: str
    platform_strategy: Dict[Platform, List[str]]
    success_metrics: List[str]
    risk_assessment: Dict[str, str]
    competitive_analysis: Dict[str, Any]
    created_at: float = field(default_factory=time.time)
    expires_at: Optional[float] = None
    
    def is_still_relevant(self) -> bool:
        """Check if opportunity is still relevant"""
        if self.expires_at and time.time() > self.expires_at:
            return False
        
        # Check time sensitivity
        age_hours = (time.time() - self.created_at) / 3600
        
        if self.time_sensitivity == "urgent" and age_hours > 6:
            return False
        elif self.time_sensitivity == "moderate" and age_hours > 24:
            return False
        elif self.time_sensitivity == "flexible" and age_hours > 168:  # 1 week
            return False
        
        return True
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "opportunity_id": self.opportunity_id,
            "trend_id": self.trend_id,
            "trend_name": self.trend_name,
            "opportunity_type": self.opportunity_type,
            "relevance_score": self.relevance_score,
            "effort_level": self.effort_level,
            "potential_impact": self.potential_impact,
            "time_sensitivity": self.time_sensitivity,
            "recommended_actions": self.recommended_actions,
            "content_suggestions": self.content_suggestions,
            "hashtag_recommendations": self.hashtag_recommendations,
            "target_audience": self.target_audience,
            "platform_strategy": {k.value: v for k, v in self.platform_strategy.items()},
            "success_metrics": self.success_metrics,
            "risk_assessment": self.risk_assessment,
            "competitive_analysis": self.competitive_analysis,
            "created_at": self.created_at,
            "expires_at": self.expires_at,
            "is_still_relevant": self.is_still_relevant()
        }


class TrendDetector:
    """AI-powered trend detection engine"""
    
    def __init__(self):
        self.text_service = None
        self.vector_service = None
        self.detection_thresholds = {
            "hashtag_volume_spike": 2.0,  # 2x increase in volume
            "engagement_spike": 1.5,  # 1.5x increase in engagement
            "influencer_adoption": 0.1,  # 10% of tracked influencers
            "cross_platform_emergence": 3,  # Appears on 3+ platforms
            "velocity_threshold": 0.5  # Growth rate threshold
        }
    
    async def _get_services(self):
        """Initialize AI services"""
        if self.text_service is None:
            self.text_service = await get_text_service()
        if self.vector_service is None:
            self.vector_service = await get_vector_service()
    
    async def detect_trending_topics(
        self,
        platforms: List[Platform],
        industry_keywords: List[str],
        time_window_hours: int = 24
    ) -> List[TrendData]:
        """Detect trending topics across platforms"""
        
        await self._get_services()
        
        logger.info(f"Detecting trends across {len(platforms)} platforms")
        
        all_trends = []
        
        for platform in platforms:
            # Get platform-specific trends
            platform_trends = await self._detect_platform_trends(
                platform, industry_keywords, time_window_hours
            )
            all_trends.extend(platform_trends)
        
        # Consolidate cross-platform trends
        consolidated_trends = self._consolidate_trends(all_trends)
        
        # Analyze trend signals
        analyzed_trends = await self._analyze_trend_signals(consolidated_trends)
        
        # Score and rank trends
        scored_trends = self._score_trends(analyzed_trends)
        
        # Sort by viral score
        scored_trends.sort(key=lambda t: t.viral_score, reverse=True)
        
        return scored_trends
    
    async def _detect_platform_trends(
        self,
        platform: Platform,
        industry_keywords: List[str],
        time_window_hours: int
    ) -> List[TrendData]:
        """Detect trends for specific platform"""
        
        # Check cache first
        cache_key = f"platform_trends_{platform}_{time_window_hours}_{hash(tuple(industry_keywords))}"
        
        if cache_key in trend_cache:
            cached_data = trend_cache[cache_key]
            # Validate cache freshness
            if all(TrendData(**trend).is_fresh() for trend in cached_data):
                return [TrendData(**trend) for trend in cached_data]
        
        # In production, this would connect to platform APIs
        # For now, generate mock trending data with realistic patterns
        mock_trends = await self._generate_mock_platform_trends(platform, industry_keywords)
        
        # Cache the results
        trend_cache.set(
            cache_key, 
            [trend.to_dict() for trend in mock_trends],
            expire=3600  # 1 hour cache
        )
        
        return mock_trends
    
    async def _generate_mock_platform_trends(
        self,
        platform: Platform,
        industry_keywords: List[str]
    ) -> List[TrendData]:
        """Generate realistic mock trending data"""
        
        # Platform-specific trending patterns
        platform_trends = {
            Platform.TIKTOK: [
                "AI productivity hack", "Remote work setup", "Quick breakfast recipe",
                "30-second workout", "Book recommendation", "Life hack", "Study method",
                "Phone photography tip", "Budget meal prep", "Minimalist morning routine"
            ],
            Platform.INSTAGRAM: [
                "Aesthetic workspace", "Golden hour photo", "Sustainable fashion",
                "Plant care tips", "Self-care Sunday", "Home decor inspo",
                "Fitness motivation", "Travel photography", "Food styling", "Outfit inspiration"
            ],
            Platform.YOUTUBE_SHORTS: [
                "Tutorial in 60 seconds", "Before and after", "Day in my life",
                "Product review", "Life lesson", "Quick recipe", "Tech tip",
                "Productivity method", "Money saving tip", "Learning hack"
            ],
            Platform.LINKEDIN: [
                "Career advice", "Leadership insight", "Industry trend",
                "Professional growth", "Networking tip", "Remote work strategy",
                "Business lesson", "Skill development", "Market analysis", "Innovation update"
            ],
            Platform.TWITTER: [
                "Breaking news reaction", "Thread about topic", "Hot take",
                "Industry insight", "Personal story", "Viral meme", "Social commentary",
                "Quick tip", "Resource share", "Debate topic"
            ]
        }
        
        base_topics = platform_trends.get(platform, platform_trends[Platform.TIKTOK])
        
        # Combine with industry keywords
        if industry_keywords:
            enhanced_topics = []
            for topic in base_topics:
                for keyword in industry_keywords[:2]:  # Use first 2 keywords
                    enhanced_topics.append(f"{keyword} {topic}")
            base_topics.extend(enhanced_topics[:5])  # Add 5 industry-specific trends
        
        trends = []
        
        for i, topic in enumerate(base_topics[:15]):  # Limit to 15 trends
            trend_id = f"{platform}_{hash(topic)}_{int(time.time())}"
            
            # Generate realistic trend metrics
            base_volume = 1000 + (i * 500)
            volume_multiplier = np.random.lognormal(0, 1)  # Log-normal distribution for realistic spikes
            volume = int(base_volume * volume_multiplier)
            
            # Generate trend lifecycle
            trend_age_hours = np.random.uniform(1, 48)  # 1-48 hours old
            growth_rate = max(0, np.random.normal(50, 30))  # Average 50% growth with variation
            
            # Determine trend status based on age and growth
            if trend_age_hours < 6 and growth_rate > 100:
                status = TrendStatus.EMERGING
            elif trend_age_hours < 12 and growth_rate > 50:
                status = TrendStatus.RISING
            elif trend_age_hours < 24 and growth_rate > 20:
                status = TrendStatus.PEAK
            elif growth_rate > 0:
                status = TrendStatus.DECLINING
            else:
                status = TrendStatus.FADING
            
            # Generate signals
            signals = await self._generate_trend_signals(topic, platform, volume)
            
            # Create trend data
            trend = TrendData(
                trend_id=trend_id,
                name=topic,
                trend_type=self._classify_trend_type(topic),
                platform=platform,
                status=status,
                viral_score=min(100, volume / 1000 + growth_rate / 2),  # Score 0-100
                growth_rate=growth_rate,
                volume=volume,
                engagement_rate=np.random.uniform(0.02, 0.15),  # 2-15% engagement
                demographic_data=self._generate_demographic_data(),
                geographic_data=self._generate_geographic_data(),
                signals=signals,
                related_trends=self._generate_related_trends(topic),
                keywords=self._extract_keywords(topic),
                first_detected=time.time() - (trend_age_hours * 3600),
                peak_time=time.time() - (trend_age_hours * 3600 / 2) if status in [TrendStatus.PEAK, TrendStatus.DECLINING] else None,
                predicted_lifespan=np.random.uniform(24, 168),  # 1-7 days
                content_examples=self._generate_content_examples(topic, platform),
                influencer_adoption=self._generate_influencer_list(),
                brand_opportunities=self._generate_brand_opportunities(topic),
                risk_factors=self._generate_risk_factors(topic)
            )
            
            trends.append(trend)
        
        return trends
    
    def _classify_trend_type(self, topic: str) -> TrendType:
        """Classify trend type based on content"""
        topic_lower = topic.lower()
        
        if topic_lower.startswith('#'):
            return TrendType.HASHTAG
        elif any(word in topic_lower for word in ['challenge', 'dare', 'try']):
            return TrendType.CHALLENGE
        elif any(word in topic_lower for word in ['meme', 'viral', 'funny']):
            return TrendType.MEME
        elif any(word in topic_lower for word in ['news', 'breaking', 'update']):
            return TrendType.NEWS_EVENT
        elif any(word in topic_lower for word in ['sound', 'music', 'audio']):
            return TrendType.SOUND
        elif any(word in topic_lower for word in ['christmas', 'halloween', 'summer', 'winter']):
            return TrendType.SEASONAL
        else:
            return TrendType.TOPIC
    
    async def _generate_trend_signals(
        self,
        topic: str,
        platform: Platform,
        volume: int
    ) -> List[TrendSignal]:
        """Generate trend signals for mock data"""
        
        signals = []
        
        # Volume signal
        signals.append(TrendSignal(
            signal_id=f"volume_{hash(topic)}",
            content=f"Volume spike detected: {volume} mentions",
            signal_strength=min(1.0, volume / 10000),
            platform=platform,
            source=TrendSource.HASHTAG_TRACKING,
            detected_at=time.time(),
            metadata={"volume": volume}
        ))
        
        # Engagement signal
        engagement_strength = np.random.uniform(0.3, 0.9)
        signals.append(TrendSignal(
            signal_id=f"engagement_{hash(topic)}",
            content=f"High engagement detected on topic: {topic}",
            signal_strength=engagement_strength,
            platform=platform,
            source=TrendSource.SOCIAL_PLATFORMS,
            detected_at=time.time(),
            metadata={"engagement_rate": engagement_strength}
        ))
        
        # Influencer signal (sometimes)
        if np.random.random() > 0.7:  # 30% chance
            signals.append(TrendSignal(
                signal_id=f"influencer_{hash(topic)}",
                content=f"Influencer adoption detected for: {topic}",
                signal_strength=np.random.uniform(0.5, 1.0),
                platform=platform,
                source=TrendSource.INFLUENCER_MONITORING,
                detected_at=time.time(),
                metadata={"influencer_count": np.random.randint(5, 50)}
            ))
        
        return signals
    
    def _generate_demographic_data(self) -> Dict[str, Any]:
        """Generate mock demographic data"""
        return {
            "age_groups": {
                "13-17": np.random.uniform(10, 30),
                "18-24": np.random.uniform(20, 40),
                "25-34": np.random.uniform(15, 35),
                "35-44": np.random.uniform(10, 25),
                "45+": np.random.uniform(5, 20)
            },
            "gender": {
                "female": np.random.uniform(40, 60),
                "male": np.random.uniform(40, 60),
                "other": np.random.uniform(0, 5)
            },
            "interests": ["lifestyle", "entertainment", "education", "technology"]
        }
    
    def _generate_geographic_data(self) -> Dict[str, Any]:
        """Generate mock geographic data"""
        countries = ["US", "UK", "Canada", "Australia", "Germany", "France", "Brazil", "India"]
        return {
            "top_countries": {
                country: np.random.uniform(5, 25) 
                for country in np.random.choice(countries, 5, replace=False)
            },
            "concentration": "global" if np.random.random() > 0.3 else "regional"
        }
    
    def _generate_related_trends(self, topic: str) -> List[str]:
        """Generate related trends"""
        base_words = topic.lower().split()
        related = []
        
        for word in base_words:
            if len(word) > 3:  # Skip short words
                related.extend([
                    f"{word} tips",
                    f"best {word}",
                    f"{word} hack",
                    f"{word} trend"
                ])
        
        return related[:5]  # Return top 5
    
    def _extract_keywords(self, topic: str) -> List[str]:
        """Extract keywords from topic"""
        # Simple keyword extraction
        words = re.findall(r'\b\w+\b', topic.lower())
        # Filter out common words
        stop_words = {'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with', 'by'}
        keywords = [word for word in words if word not in stop_words and len(word) > 2]
        return keywords[:10]
    
    def _generate_content_examples(self, topic: str, platform: Platform) -> List[Dict[str, Any]]:
        """Generate example content for trend"""
        examples = []
        
        for i in range(3):
            examples.append({
                "title": f"Example {i+1}: {topic}",
                "engagement": np.random.randint(100, 10000),
                "author": f"@user{i+1}",
                "url": f"https://{platform.value}.com/example{i+1}",
                "posted_at": time.time() - (i * 3600)  # Staggered times
            })
        
        return examples
    
    def _generate_influencer_list(self) -> List[str]:
        """Generate mock influencer adoption list"""
        influencers = ["@influencer1", "@creator2", "@viral_maker", "@trend_setter", "@content_king"]
        return np.random.choice(influencers, np.random.randint(1, 4), replace=False).tolist()
    
    def _generate_brand_opportunities(self, topic: str) -> List[str]:
        """Generate brand opportunity suggestions"""
        return [
            f"Create educational content about {topic}",
            f"Partner with influencers discussing {topic}",
            f"Launch branded {topic} challenge",
            f"Develop {topic}-related product placement",
            f"Host live session about {topic}"
        ][:3]
    
    def _generate_risk_factors(self, topic: str) -> List[str]:
        """Generate potential risk factors"""
        generic_risks = [
            "Trend may be short-lived",
            "High competition from other brands",
            "Potential for negative associations",
            "Resource intensive to execute",
            "May not align with brand values"
        ]
        
        return np.random.choice(generic_risks, np.random.randint(1, 3), replace=False).tolist()
    
    def _consolidate_trends(self, all_trends: List[TrendData]) -> List[TrendData]:
        """Consolidate similar trends across platforms"""
        
        if not all_trends:
            return []
        
        # Group similar trends by name similarity
        consolidated = {}
        
        for trend in all_trends:
            # Find similar existing trends
            similar_key = None
            for existing_key in consolidated.keys():
                if self._calculate_name_similarity(trend.name, existing_key) > 0.7:
                    similar_key = existing_key
                    break
            
            if similar_key:
                # Merge with existing trend
                existing_trend = consolidated[similar_key]
                existing_trend.volume += trend.volume
                existing_trend.signals.extend(trend.signals)
                existing_trend.viral_score = max(existing_trend.viral_score, trend.viral_score)
                existing_trend.growth_rate = max(existing_trend.growth_rate, trend.growth_rate)
                existing_trend.related_trends.extend(trend.related_trends)
                existing_trend.related_trends = list(set(existing_trend.related_trends))  # Remove duplicates
            else:
                # Add as new trend
                consolidated[trend.name] = trend
        
        return list(consolidated.values())
    
    def _calculate_name_similarity(self, name1: str, name2: str) -> float:
        """Calculate similarity between trend names"""
        words1 = set(name1.lower().split())
        words2 = set(name2.lower().split())
        
        if not words1 or not words2:
            return 0.0
        
        intersection = len(words1.intersection(words2))
        union = len(words1.union(words2))
        
        return intersection / union if union > 0 else 0.0
    
    async def _analyze_trend_signals(self, trends: List[TrendData]) -> List[TrendData]:
        """Analyze and enhance trend signals with AI"""
        
        for trend in trends:
            # Calculate signal strength
            if trend.signals:
                avg_signal_strength = statistics.mean([s.signal_strength for s in trend.signals])
                # Boost viral score based on signal strength
                trend.viral_score = min(100, trend.viral_score * (1 + avg_signal_strength))
            
            # Predict trend lifecycle
            trend.status = await self._predict_trend_status(trend)
            
            # Update predicted lifespan based on signals
            if trend.signals:
                strong_signals = [s for s in trend.signals if s.signal_strength > 0.7]
                if len(strong_signals) > 2:
                    trend.predicted_lifespan *= 1.5  # Extend lifespan for strong trends
        
        return trends
    
    async def _predict_trend_status(self, trend: TrendData) -> TrendStatus:
        """Predict trend status using AI and signals"""
        
        # Simple rule-based prediction (in production, use ML model)
        age_hours = (time.time() - trend.first_detected) / 3600
        
        if trend.growth_rate > 100 and age_hours < 6:
            return TrendStatus.EMERGING
        elif trend.growth_rate > 50 and age_hours < 12:
            return TrendStatus.RISING
        elif trend.growth_rate > 20 and age_hours < 24:
            return TrendStatus.PEAK
        elif trend.growth_rate > 0 and age_hours < 48:
            return TrendStatus.DECLINING
        else:
            return TrendStatus.FADING
    
    def _score_trends(self, trends: List[TrendData]) -> List[TrendData]:
        """Score trends based on multiple factors"""
        
        for trend in trends:
            score_factors = []
            
            # Volume factor (normalized)
            max_volume = max([t.volume for t in trends]) if trends else 1
            volume_score = (trend.volume / max_volume) * 30
            score_factors.append(volume_score)
            
            # Growth rate factor
            growth_score = min(30, trend.growth_rate / 10)  # Cap at 30
            score_factors.append(growth_score)
            
            # Signal strength factor
            if trend.signals:
                signal_score = statistics.mean([s.signal_strength for s in trend.signals]) * 20
                score_factors.append(signal_score)
            
            # Engagement factor
            engagement_score = trend.engagement_rate * 200  # Scale to 0-20
            score_factors.append(min(20, engagement_score))
            
            # Update viral score
            trend.viral_score = sum(score_factors)
        
        return trends


class TrendOpportunityEngine:
    """AI engine for identifying trend opportunities"""
    
    def __init__(self):
        self.text_service = None
    
    async def _get_text_service(self):
        """Get text service instance"""
        if self.text_service is None:
            self.text_service = await get_text_service()
    
    async def identify_opportunities(
        self,
        trends: List[TrendData],
        brand_name: str,
        industry: str,
        target_audience: str,
        brand_voice: Dict[str, Any],
        platforms: List[Platform]
    ) -> List[TrendOpportunity]:
        """Identify trend opportunities for brand"""
        
        await self._get_text_service()
        
        logger.info(f"Identifying trend opportunities for {brand_name}")
        
        opportunities = []
        
        for trend in trends:
            # Calculate relevance to brand
            relevance_score = await self._calculate_trend_relevance(
                trend, brand_name, industry, target_audience
            )
            
            if relevance_score > 0.3:  # Only consider relevant trends
                opportunity = await self._create_trend_opportunity(
                    trend, brand_name, industry, target_audience, 
                    brand_voice, platforms, relevance_score
                )
                opportunities.append(opportunity)
        
        # Sort by relevance and potential impact
        opportunities.sort(
            key=lambda o: (o.relevance_score, self._impact_to_score(o.potential_impact)),
            reverse=True
        )
        
        return opportunities[:10]  # Return top 10 opportunities
    
    async def _calculate_trend_relevance(
        self,
        trend: TrendData,
        brand_name: str,
        industry: str,
        target_audience: str
    ) -> float:
        """Calculate how relevant a trend is to the brand"""
        
        relevance_factors = []
        
        # Industry relevance
        industry_keywords = industry.lower().split()
        trend_keywords = [kw.lower() for kw in trend.keywords]
        
        industry_overlap = len(set(industry_keywords).intersection(set(trend_keywords)))
        industry_relevance = industry_overlap / max(len(industry_keywords), 1)
        relevance_factors.append(industry_relevance * 0.3)
        
        # Audience demographic match
        audience_relevance = self._calculate_audience_match(trend, target_audience)
        relevance_factors.append(audience_relevance * 0.25)
        
        # Platform presence
        platform_relevance = 0.2  # Base relevance for any platform presence
        relevance_factors.append(platform_relevance)
        
        # Trend stage (early trends are more valuable)
        stage_relevance = {
            TrendStatus.EMERGING: 1.0,
            TrendStatus.RISING: 0.8,
            TrendStatus.PEAK: 0.6,
            TrendStatus.DECLINING: 0.3,
            TrendStatus.FADING: 0.1
        }.get(trend.status, 0.5)
        relevance_factors.append(stage_relevance * 0.25)
        
        return sum(relevance_factors)
    
    def _calculate_audience_match(self, trend: TrendData, target_audience: str) -> float:
        """Calculate audience demographic match"""
        
        # Simple keyword matching (in production, use more sophisticated analysis)
        target_keywords = target_audience.lower().split()
        
        # Check age group alignment
        demographic_data = trend.demographic_data
        if "age_groups" in demographic_data:
            # Simplistic matching based on keywords
            if any(kw in target_audience.lower() for kw in ["young", "teen", "gen z"]):
                return (demographic_data["age_groups"].get("13-17", 0) + 
                       demographic_data["age_groups"].get("18-24", 0)) / 100
            elif any(kw in target_audience.lower() for kw in ["millennial", "adult"]):
                return (demographic_data["age_groups"].get("25-34", 0) + 
                       demographic_data["age_groups"].get("35-44", 0)) / 100
        
        return 0.5  # Default moderate match
    
    async def _create_trend_opportunity(
        self,
        trend: TrendData,
        brand_name: str,
        industry: str,
        target_audience: str,
        brand_voice: Dict[str, Any],
        platforms: List[Platform],
        relevance_score: float
    ) -> TrendOpportunity:
        """Create detailed trend opportunity"""
        
        opportunity_type = self._determine_opportunity_type(trend)
        
        # Generate AI-powered recommendations
        recommendations = await self._generate_ai_recommendations(
            trend, brand_name, industry, opportunity_type
        )
        
        # Create platform-specific strategies
        platform_strategy = self._create_platform_strategy(trend, platforms)
        
        # Assess effort and impact
        effort_level = self._assess_effort_level(trend, opportunity_type)
        potential_impact = self._assess_potential_impact(trend, relevance_score)
        time_sensitivity = self._assess_time_sensitivity(trend)
        
        # Generate content suggestions
        content_suggestions = await self._generate_content_suggestions(
            trend, brand_name, brand_voice
        )
        
        # Risk assessment
        risk_assessment = self._assess_risks(trend, brand_name)
        
        # Success metrics
        success_metrics = self._define_success_metrics(trend, opportunity_type)
        
        # Set expiration based on trend lifecycle
        expires_at = self._calculate_expiration(trend)
        
        return TrendOpportunity(
            opportunity_id=f"opp_{trend.trend_id}_{int(time.time())}",
            trend_id=trend.trend_id,
            trend_name=trend.name,
            opportunity_type=opportunity_type,
            relevance_score=relevance_score,
            effort_level=effort_level,
            potential_impact=potential_impact,
            time_sensitivity=time_sensitivity,
            recommended_actions=recommendations,
            content_suggestions=content_suggestions,
            hashtag_recommendations=self._recommend_hashtags(trend),
            target_audience=target_audience,
            platform_strategy=platform_strategy,
            success_metrics=success_metrics,
            risk_assessment=risk_assessment,
            competitive_analysis=self._analyze_competition(trend),
            expires_at=expires_at
        )
    
    def _determine_opportunity_type(self, trend: TrendData) -> str:
        """Determine the type of opportunity"""
        
        if trend.status == TrendStatus.EMERGING:
            return "early_entry"
        elif trend.status == TrendStatus.RISING:
            return "trend_jump"
        elif trend.status == TrendStatus.PEAK:
            return "trend_hijack"
        elif trend.trend_type == TrendType.CHALLENGE:
            return "challenge_participation"
        elif trend.trend_type == TrendType.HASHTAG:
            return "hashtag_adoption"
        else:
            return "content_creation"
    
    async def _generate_ai_recommendations(
        self,
        trend: TrendData,
        brand_name: str,
        industry: str,
        opportunity_type: str
    ) -> List[str]:
        """Generate AI-powered recommendations"""
        
        # Use AI to generate contextual recommendations
        prompt = f"""Generate 5 specific action recommendations for {brand_name} in the {industry} industry to capitalize on the trending topic: "{trend.name}".

Trend details:
- Type: {trend.trend_type}
- Status: {trend.status}
- Volume: {trend.volume} mentions
- Growth rate: {trend.growth_rate}%
- Platform: {trend.platform}

Opportunity type: {opportunity_type}

Provide actionable, specific recommendations that align with the trend momentum and brand positioning."""
        
        try:
            response = await self.text_service.generate(
                prompt,
                max_tokens=400,
                temperature=0.6
            )
            
            if response.success:
                recommendations = []
                for line in response.content.strip().split('\n'):
                    line = line.strip()
                    if line and (line.startswith('-') or line.startswith('•') or line[0].isdigit()):
                        rec = line.lstrip('-•0123456789. ')
                        if len(rec) > 10:  # Valid recommendation
                            recommendations.append(rec)
                
                return recommendations[:5]
        
        except Exception as e:
            logger.error(f"Failed to generate AI recommendations: {e}")
        
        # Fallback recommendations
        return [
            f"Create content around {trend.name} within 24 hours",
            f"Engage with existing {trend.name} content",
            f"Use trending hashtags related to {trend.name}",
            f"Partner with influencers discussing {trend.name}",
            f"Monitor {trend.name} for brand mention opportunities"
        ]
    
    def _create_platform_strategy(
        self,
        trend: TrendData,
        platforms: List[Platform]
    ) -> Dict[Platform, List[str]]:
        """Create platform-specific strategies"""
        
        strategy = {}
        
        for platform in platforms:
            platform_strategy = []
            
            if platform == Platform.TIKTOK:
                platform_strategy.extend([
                    f"Create short-form video about {trend.name}",
                    "Use trending sounds and effects",
                    "Participate in related challenges",
                    "Post during peak hours (6-10pm)"
                ])
            
            elif platform == Platform.INSTAGRAM:
                platform_strategy.extend([
                    f"Create Instagram Reels about {trend.name}",
                    "Share to Stories with polls/questions",
                    "Use trending hashtags in post",
                    "Create carousel post with tips"
                ])
            
            elif platform == Platform.YOUTUBE_SHORTS:
                platform_strategy.extend([
                    f"Create educational Shorts about {trend.name}",
                    "Use eye-catching thumbnails",
                    "Include clear call-to-action",
                    "Cross-promote on community tab"
                ])
            
            elif platform == Platform.LINKEDIN:
                platform_strategy.extend([
                    f"Share professional perspective on {trend.name}",
                    "Create thought leadership post",
                    "Engage in relevant discussions",
                    "Share industry insights"
                ])
            
            elif platform == Platform.TWITTER:
                platform_strategy.extend([
                    f"Tweet real-time commentary on {trend.name}",
                    "Create Twitter thread",
                    "Engage with trending hashtags",
                    "Retweet with added value"
                ])
            
            strategy[platform] = platform_strategy[:3]  # Top 3 strategies per platform
        
        return strategy
    
    def _assess_effort_level(self, trend: TrendData, opportunity_type: str) -> str:
        """Assess effort level required"""
        
        effort_map = {
            "early_entry": "high",  # Requires original content creation
            "trend_jump": "medium",  # Requires quick adaptation
            "trend_hijack": "low",  # Can use existing content
            "challenge_participation": "medium",  # Moderate content creation
            "hashtag_adoption": "low",  # Just add hashtags
            "content_creation": "medium"  # Default
        }
        
        base_effort = effort_map.get(opportunity_type, "medium")
        
        # Adjust based on trend complexity
        if trend.trend_type in [TrendType.CHALLENGE, TrendType.VIRAL_FORMAT]:
            # These require more creative effort
            if base_effort == "low":
                base_effort = "medium"
            elif base_effort == "medium":
                base_effort = "high"
        
        return base_effort
    
    def _assess_potential_impact(self, trend: TrendData, relevance_score: float) -> str:
        """Assess potential impact of the opportunity"""
        
        impact_score = 0
        
        # Viral score factor
        if trend.viral_score > 80:
            impact_score += 3
        elif trend.viral_score > 60:
            impact_score += 2
        elif trend.viral_score > 40:
            impact_score += 1
        
        # Relevance factor
        if relevance_score > 0.7:
            impact_score += 2
        elif relevance_score > 0.5:
            impact_score += 1
        
        # Volume factor
        if trend.volume > 100000:
            impact_score += 2
        elif trend.volume > 10000:
            impact_score += 1
        
        # Growth rate factor
        if trend.growth_rate > 100:
            impact_score += 2
        elif trend.growth_rate > 50:
            impact_score += 1
        
        # Convert to categorical
        if impact_score >= 6:
            return "high"
        elif impact_score >= 3:
            return "medium"
        else:
            return "low"
    
    def _assess_time_sensitivity(self, trend: TrendData) -> str:
        """Assess time sensitivity of the opportunity"""
        
        if trend.status == TrendStatus.EMERGING:
            return "urgent"  # Need to act quickly
        elif trend.status == TrendStatus.RISING:
            return "moderate"  # Some time but not much
        elif trend.status == TrendStatus.PEAK:
            return "urgent"  # Peak moment to capitalize
        elif trend.status == TrendStatus.DECLINING:
            return "flexible"  # Less urgent
        else:
            return "moderate"
    
    async def _generate_content_suggestions(
        self,
        trend: TrendData,
        brand_name: str,
        brand_voice: Dict[str, Any]
    ) -> List[str]:
        """Generate content suggestions"""
        
        suggestions = []
        
        # Format brand voice for context
        voice_context = ""
        if brand_voice:
            tone = brand_voice.get("tone", "professional")
            voice_context = f"Brand voice is {tone}."
        
        # Generate suggestions based on trend type
        if trend.trend_type == TrendType.CHALLENGE:
            suggestions.extend([
                f"Participate in {trend.name} challenge with brand twist",
                f"Create tutorial on how to do {trend.name}",
                f"Share behind-the-scenes of team doing {trend.name}"
            ])
        
        elif trend.trend_type == TrendType.TOPIC:
            suggestions.extend([
                f"Share expert opinion on {trend.name}",
                f"Create educational content about {trend.name}",
                f"Show how {trend.name} relates to your industry"
            ])
        
        elif trend.trend_type == TrendType.HASHTAG:
            suggestions.extend([
                f"Create original content using {trend.name}",
                f"Share user-generated content with {trend.name}",
                f"Start conversation around {trend.name}"
            ])
        
        else:
            # Generic suggestions
            suggestions.extend([
                f"Create timely content about {trend.name}",
                f"Share your perspective on {trend.name}",
                f"Connect {trend.name} to your brand story"
            ])
        
        return suggestions[:5]
    
    def _recommend_hashtags(self, trend: TrendData) -> List[str]:
        """Recommend hashtags for the trend"""
        
        hashtags = []
        
        # Primary trend hashtag
        if not trend.name.startswith('#'):
            hashtags.append(f"#{trend.name.replace(' ', '').lower()}")
        else:
            hashtags.append(trend.name)
        
        # Related hashtags from trend data
        hashtags.extend(trend.related_trends[:3])
        
        # Keyword-based hashtags
        for keyword in trend.keywords[:3]:
            hashtags.append(f"#{keyword}")
        
        # Platform-specific hashtags
        platform_hashtags = {
            Platform.TIKTOK: ["#fyp", "#viral", "#trending"],
            Platform.INSTAGRAM: ["#instagood", "#trending", "#viral"],
            Platform.YOUTUBE_SHORTS: ["#shorts", "#viral", "#trending"],
            Platform.LINKEDIN: ["#professional", "#industry", "#insights"],
            Platform.TWITTER: ["#breaking", "#news", "#trending"]
        }
        
        if trend.platform in platform_hashtags:
            hashtags.extend(platform_hashtags[trend.platform][:2])
        
        # Remove duplicates and limit
        unique_hashtags = list(dict.fromkeys(hashtags))
        return unique_hashtags[:10]
    
    def _define_success_metrics(self, trend: TrendData, opportunity_type: str) -> List[str]:
        """Define success metrics for the opportunity"""
        
        base_metrics = [
            "Engagement rate increase",
            "Reach expansion",
            "Hashtag performance",
            "Content shares",
            "Comment engagement"
        ]
        
        # Add opportunity-specific metrics
        if opportunity_type == "early_entry":
            base_metrics.extend([
                "First-mover advantage captured",
                "Thought leadership establishment"
            ])
        elif opportunity_type == "challenge_participation":
            base_metrics.extend([
                "Challenge completion rate",
                "User-generated content creation"
            ])
        elif opportunity_type == "hashtag_adoption":
            base_metrics.extend([
                "Hashtag reach",
                "Hashtag engagement rate"
            ])
        
        return base_metrics[:6]
    
    def _assess_risks(self, trend: TrendData, brand_name: str) -> Dict[str, str]:
        """Assess risks associated with the opportunity"""
        
        risks = {}
        
        # Trend lifecycle risk
        if trend.status in [TrendStatus.PEAK, TrendStatus.DECLINING]:
            risks["trend_lifecycle"] = "high"
        elif trend.status == TrendStatus.RISING:
            risks["trend_lifecycle"] = "medium"
        else:
            risks["trend_lifecycle"] = "low"
        
        # Competition risk
        if trend.volume > 100000:
            risks["competition"] = "high"
        elif trend.volume > 10000:
            risks["competition"] = "medium"
        else:
            risks["competition"] = "low"
        
        # Brand alignment risk
        if trend.trend_type in [TrendType.MEME, TrendType.CHALLENGE]:
            risks["brand_alignment"] = "medium"
        else:
            risks["brand_alignment"] = "low"
        
        # Content quality risk
        if trend.growth_rate > 200:  # Very fast trends
            risks["content_quality"] = "high"  # Less time to create quality
        else:
            risks["content_quality"] = "low"
        
        return risks
    
    def _analyze_competition(self, trend: TrendData) -> Dict[str, Any]:
        """Analyze competitive landscape for trend"""
        
        return {
            "competition_level": "high" if trend.volume > 50000 else "medium" if trend.volume > 5000 else "low",
            "estimated_competitors": min(trend.volume // 1000, 100),  # Rough estimate
            "competitive_advantage": "early_entry" if trend.status == TrendStatus.EMERGING else "differentiation",
            "market_saturation": trend.volume / 100000,  # Rough saturation metric
        }
    
    def _calculate_expiration(self, trend: TrendData) -> float:
        """Calculate when opportunity expires"""
        
        # Base expiration on predicted lifespan
        base_expiration = time.time() + (trend.predicted_lifespan * 3600)
        
        # Adjust based on trend status
        if trend.status == TrendStatus.EMERGING:
            # Short window for emerging trends
            return time.time() + (12 * 3600)  # 12 hours
        elif trend.status == TrendStatus.RISING:
            # Moderate window
            return time.time() + (24 * 3600)  # 24 hours
        elif trend.status == TrendStatus.PEAK:
            # Very short window
            return time.time() + (6 * 3600)  # 6 hours
        else:
            return base_expiration
    
    def _impact_to_score(self, impact: str) -> int:
        """Convert impact level to numeric score"""
        return {"high": 3, "medium": 2, "low": 1}.get(impact, 1)


class TrendAnalysisService:
    """Main service for comprehensive trend analysis"""
    
    def __init__(self):
        self.detector = TrendDetector()
        self.opportunity_engine = TrendOpportunityEngine()
    
    async def comprehensive_trend_analysis(
        self,
        brand_name: str,
        industry: str,
        target_audience: str,
        platforms: List[Platform],
        brand_voice: Dict[str, Any] = None,
        industry_keywords: List[str] = None
    ) -> Dict[str, Any]:
        """Run comprehensive trend analysis"""
        
        logger.info(f"Running comprehensive trend analysis for {brand_name}")
        
        # Detect current trends
        trends = await self.detector.detect_trending_topics(
            platforms=platforms,
            industry_keywords=industry_keywords or [],
            time_window_hours=24
        )
        
        # Identify opportunities
        opportunities = await self.opportunity_engine.identify_opportunities(
            trends=trends,
            brand_name=brand_name,
            industry=industry,
            target_audience=target_audience,
            brand_voice=brand_voice or {},
            platforms=platforms
        )
        
        # Filter for still relevant opportunities
        active_opportunities = [opp for opp in opportunities if opp.is_still_relevant()]
        
        # Categorize trends by status
        trend_categories = self._categorize_trends(trends)
        
        # Generate trend insights
        insights = await self._generate_trend_insights(trends, opportunities)
        
        # Create trend summary
        summary = self._create_trend_summary(trends, active_opportunities)
        
        return {
            "analysis_timestamp": time.time(),
            "brand_name": brand_name,
            "industry": industry,
            "platforms_analyzed": [p.value for p in platforms],
            "summary": summary,
            "trends": [t.to_dict() for t in trends],
            "trend_categories": trend_categories,
            "opportunities": [o.to_dict() for o in active_opportunities],
            "insights": insights,
            "recommendations": {
                "immediate_actions": [o.recommended_actions[0] for o in active_opportunities[:3] if o.recommended_actions],
                "trending_hashtags": list(set([tag for o in active_opportunities for tag in o.hashtag_recommendations[:3]])),
                "content_focus": self._identify_content_focus(trends),
                "platform_priorities": self._prioritize_platforms(trends, platforms)
            }
        }
    
    def _categorize_trends(self, trends: List[TrendData]) -> Dict[str, List[Dict[str, Any]]]:
        """Categorize trends by status and type"""
        
        categories = {
            "emerging": [],
            "rising": [],
            "peak": [],
            "declining": [],
            "by_type": defaultdict(list),
            "by_platform": defaultdict(list)
        }
        
        for trend in trends:
            # By status
            status_key = trend.status.value
            if status_key in categories:
                categories[status_key].append(trend.to_dict())
            
            # By type
            categories["by_type"][trend.trend_type.value].append(trend.to_dict())
            
            # By platform
            categories["by_platform"][trend.platform.value].append(trend.to_dict())
        
        # Convert defaultdicts to regular dicts
        categories["by_type"] = dict(categories["by_type"])
        categories["by_platform"] = dict(categories["by_platform"])
        
        return categories
    
    async def _generate_trend_insights(
        self,
        trends: List[TrendData],
        opportunities: List[TrendOpportunity]
    ) -> List[str]:
        """Generate AI-powered trend insights"""
        
        insights = []
        
        if not trends:
            return ["No significant trends detected in the current analysis period."]
        
        # Volume insights
        total_volume = sum(t.volume for t in trends)
        avg_volume = total_volume / len(trends)
        high_volume_trends = [t for t in trends if t.volume > avg_volume * 2]
        
        if high_volume_trends:
            insights.append(f"{len(high_volume_trends)} high-volume trends detected with significant engagement potential")
        
        # Growth rate insights
        high_growth_trends = [t for t in trends if t.growth_rate > 100]
        if high_growth_trends:
            insights.append(f"{len(high_growth_trends)} rapidly growing trends identified - immediate action recommended")
        
        # Platform insights
        platform_distribution = Counter([t.platform for t in trends])
        dominant_platform = platform_distribution.most_common(1)[0] if platform_distribution else None
        
        if dominant_platform:
            insights.append(f"{dominant_platform[0].value} shows highest trend activity with {dominant_platform[1]} active trends")
        
        # Opportunity insights
        urgent_opportunities = [o for o in opportunities if o.time_sensitivity == "urgent"]
        if urgent_opportunities:
            insights.append(f"{len(urgent_opportunities)} urgent opportunities require immediate attention")
        
        high_impact_opportunities = [o for o in opportunities if o.potential_impact == "high"]
        if high_impact_opportunities:
            insights.append(f"{len(high_impact_opportunities)} high-impact opportunities identified for maximum ROI")
        
        # Trend type insights
        type_distribution = Counter([t.trend_type for t in trends])
        if type_distribution:
            top_type = type_distribution.most_common(1)[0]
            insights.append(f"{top_type[0].value} trends are dominating current landscape")
        
        # Status insights
        emerging_trends = [t for t in trends if t.status == TrendStatus.EMERGING]
        if emerging_trends:
            insights.append(f"{len(emerging_trends)} emerging trends offer early-mover advantages")
        
        return insights[:8]  # Return top 8 insights
    
    def _create_trend_summary(
        self,
        trends: List[TrendData],
        opportunities: List[TrendOpportunity]
    ) -> Dict[str, Any]:
        """Create summary of trend analysis"""
        
        if not trends:
            return {
                "total_trends": 0,
                "total_opportunities": 0,
                "avg_viral_score": 0,
                "trend_velocity": 0
            }
        
        return {
            "total_trends": len(trends),
            "total_opportunities": len(opportunities),
            "urgent_opportunities": len([o for o in opportunities if o.time_sensitivity == "urgent"]),
            "high_impact_opportunities": len([o for o in opportunities if o.potential_impact == "high"]),
            "avg_viral_score": statistics.mean([t.viral_score for t in trends]),
            "avg_growth_rate": statistics.mean([t.growth_rate for t in trends]),
            "trend_velocity": statistics.mean([t.get_trend_velocity() for t in trends]),
            "platforms_with_trends": len(set([t.platform for t in trends])),
            "emerging_trends": len([t for t in trends if t.status == TrendStatus.EMERGING]),
            "peak_trends": len([t for t in trends if t.status == TrendStatus.PEAK])
        }
    
    def _identify_content_focus(self, trends: List[TrendData]) -> List[str]:
        """Identify content focus areas based on trends"""
        
        # Analyze trending keywords
        all_keywords = []
        for trend in trends:
            all_keywords.extend(trend.keywords)
        
        keyword_counts = Counter(all_keywords)
        top_keywords = keyword_counts.most_common(5)
        
        focus_areas = [keyword for keyword, count in top_keywords]
        
        # Add trend type recommendations
        type_counts = Counter([t.trend_type for t in trends])
        top_types = type_counts.most_common(2)
        
        for trend_type, count in top_types:
            if trend_type == TrendType.CHALLENGE:
                focus_areas.append("Interactive challenges")
            elif trend_type == TrendType.TOPIC:
                focus_areas.append("Educational content")
            elif trend_type == TrendType.MEME:
                focus_areas.append("Entertainment content")
        
        return focus_areas[:5]
    
    def _prioritize_platforms(
        self,
        trends: List[TrendData],
        platforms: List[Platform]
    ) -> List[Dict[str, Any]]:
        """Prioritize platforms based on trend activity"""
        
        platform_scores = {}
        
        for platform in platforms:
            platform_trends = [t for t in trends if t.platform == platform]
            
            if platform_trends:
                avg_viral_score = statistics.mean([t.viral_score for t in platform_trends])
                total_volume = sum([t.volume for t in platform_trends])
                emerging_count = len([t for t in platform_trends if t.status == TrendStatus.EMERGING])
                
                # Calculate priority score
                priority_score = (
                    avg_viral_score * 0.4 +
                    (total_volume / 10000) * 0.3 +  # Normalize volume
                    emerging_count * 10 * 0.3  # Bonus for emerging trends
                )
                
                platform_scores[platform] = {
                    "platform": platform.value,
                    "priority_score": priority_score,
                    "trend_count": len(platform_trends),
                    "avg_viral_score": avg_viral_score,
                    "emerging_trends": emerging_count
                }
        
        # Sort by priority score
        prioritized = sorted(platform_scores.values(), key=lambda x: x["priority_score"], reverse=True)
        
        return prioritized


# Global service instance
_trend_analysis_service: Optional[TrendAnalysisService] = None


async def get_trend_analysis_service() -> TrendAnalysisService:
    """Get global trend analysis service instance"""
    global _trend_analysis_service
    if _trend_analysis_service is None:
        _trend_analysis_service = TrendAnalysisService()
    return _trend_analysis_service