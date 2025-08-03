import asyncio
import logging
from typing import Dict, List, Optional, Tuple, Any
from datetime import datetime, timedelta
import json
import numpy as np
import requests
from dataclasses import dataclass
from sqlalchemy.orm import Session
from sqlalchemy import and_, desc

from app.models.analytics import TrendRecommendation, PlatformType
from app.models.tiktok_trend import TikTokTrend, TikTokSound, TikTokVideo, TikTokHashtag
from app.models.brand import Brand
from app.core.config import settings
from app.db.session import SessionLocal

logger = logging.getLogger(__name__)

@dataclass
class TrendData:
    """Container for trend analysis data"""
    trend_id: str
    name: str
    description: str
    trend_type: str  # audio, hashtag, format, effect
    volume: int
    growth_rate: float
    virality_score: float
    relevance_score: float
    platform: PlatformType
    audio_url: Optional[str] = None
    audio_duration: Optional[float] = None
    audio_mood: Optional[str] = None
    audio_bpm: Optional[int] = None
    copyright_status: Optional[str] = None
    peak_usage_time: Optional[datetime] = None
    estimated_decay_date: Optional[datetime] = None
    metadata: Optional[Dict] = None

@dataclass
class RecommendationFilter:
    """Filter criteria for trend recommendations"""
    brand_id: int
    platform: PlatformType
    industry: Optional[str] = None
    target_audience: Optional[str] = None
    content_style: Optional[str] = None
    min_virality_score: float = 50.0
    max_age_days: int = 7
    include_audio: bool = True
    include_hashtags: bool = True
    include_formats: bool = True

class TrendRecommendationEngine:
    """Real-time trend monitoring and recommendation system"""
    
    def __init__(self):
        self.cache_duration = timedelta(hours=1)
        self.trend_cache = {}
        self.audio_analyzer = AudioAnalyzer()
        self.relevance_calculator = RelevanceCalculator()
        
        # Industry keywords for relevance matching
        self.industry_keywords = {
            'fashion': ['style', 'outfit', 'fashion', 'clothing', 'accessories', 'trend', 'wear'],
            'beauty': ['makeup', 'skincare', 'beauty', 'cosmetics', 'hair', 'nails', 'glow'],
            'fitness': ['workout', 'fitness', 'gym', 'exercise', 'health', 'strength', 'cardio'],
            'food': ['recipe', 'cooking', 'food', 'kitchen', 'chef', 'meal', 'ingredients'],
            'tech': ['technology', 'gadget', 'app', 'software', 'digital', 'innovation', 'tech'],
            'gaming': ['game', 'gaming', 'player', 'stream', 'esports', 'console', 'pc'],
            'lifestyle': ['life', 'daily', 'routine', 'home', 'family', 'travel', 'vlog']
        }
    
    async def get_trend_recommendations(
        self, 
        brand_id: int, 
        platform: PlatformType,
        filters: Optional[RecommendationFilter] = None
    ) -> List[TrendRecommendation]:
        """
        Get personalized trend recommendations for a brand
        
        Args:
            brand_id: Brand identifier
            platform: Target platform
            filters: Additional filtering criteria
            
        Returns:
            List of relevant trend recommendations
        """
        try:
            # Use default filters if none provided
            if filters is None:
                filters = RecommendationFilter(brand_id=brand_id, platform=platform)
            
            # Get fresh trend data
            trend_data = await self._fetch_trend_data(platform, filters.max_age_days)
            
            # Filter and score trends for relevance
            relevant_trends = await self._filter_and_score_trends(trend_data, filters)
            
            # Convert to recommendation objects
            recommendations = await self._create_recommendations(relevant_trends, brand_id, platform)
            
            # Save to database
            await self._save_recommendations(recommendations)
            
            return recommendations
            
        except Exception as e:
            logger.error(f"Error getting trend recommendations: {e}")
            return []
    
    async def _fetch_trend_data(self, platform: PlatformType, max_age_days: int) -> List[TrendData]:
        """Fetch trending data from various sources"""
        trend_data = []
        
        # Fetch from TikTok data if available
        if platform in [PlatformType.TIKTOK, PlatformType.INSTAGRAM]:
            tiktok_trends = await self._fetch_tiktok_trends(max_age_days)
            trend_data.extend(tiktok_trends)
        
        # Fetch from external APIs (placeholder for real implementations)
        external_trends = await self._fetch_external_trends(platform, max_age_days)
        trend_data.extend(external_trends)
        
        return trend_data
    
    async def _fetch_tiktok_trends(self, max_age_days: int) -> List[TrendData]:
        """Fetch trends from TikTok scraping data"""
        trends = []
        
        try:
            db = SessionLocal()
            
            # Get recent TikTok trends
            cutoff_date = datetime.now() - timedelta(days=max_age_days)
            
            # Fetch trending sounds
            trending_sounds = db.query(TikTokSound).filter(
                TikTokSound.discovered_at >= cutoff_date
            ).order_by(desc(TikTokSound.usage_count)).limit(50).all()
            
            for sound in trending_sounds:
                trend = TrendData(
                    trend_id=f"tiktok_sound_{sound.id}",
                    name=sound.title or "Unknown Sound",
                    description=f"Trending audio with {sound.usage_count} uses",
                    trend_type="audio",
                    volume=sound.usage_count or 0,
                    growth_rate=self._calculate_growth_rate(sound),
                    virality_score=self._calculate_virality_score(sound.usage_count, sound.discovered_at),
                    relevance_score=0.0,  # Will be calculated later
                    platform=PlatformType.TIKTOK,
                    audio_url=sound.audio_url,
                    audio_duration=sound.duration,
                    audio_mood=None,  # Will be analyzed
                    audio_bpm=None,   # Will be analyzed
                    copyright_status="unknown",
                    metadata={'sound_id': sound.sound_id, 'author': sound.author}
                )
                trends.append(trend)
            
            # Fetch trending hashtags
            trending_hashtags = db.query(TikTokHashtag).filter(
                TikTokHashtag.discovered_at >= cutoff_date
            ).order_by(desc(TikTokHashtag.view_count)).limit(30).all()
            
            for hashtag in trending_hashtags:
                trend = TrendData(
                    trend_id=f"tiktok_hashtag_{hashtag.id}",
                    name=hashtag.name,
                    description=f"Trending hashtag with {hashtag.view_count} views",
                    trend_type="hashtag",
                    volume=hashtag.view_count or 0,
                    growth_rate=self._calculate_hashtag_growth_rate(hashtag),
                    virality_score=self._calculate_virality_score(hashtag.view_count, hashtag.discovered_at),
                    relevance_score=0.0,
                    platform=PlatformType.TIKTOK,
                    metadata={'hashtag_id': hashtag.hashtag_id}
                )
                trends.append(trend)
                
        except Exception as e:
            logger.error(f"Error fetching TikTok trends: {e}")
        finally:
            db.close()
        
        return trends
    
    async def _fetch_external_trends(self, platform: PlatformType, max_age_days: int) -> List[TrendData]:
        """Fetch trends from external APIs"""
        trends = []
        
        # Placeholder for external API integrations
        # In production, this would integrate with:
        # - Instagram Basic Display API
        # - YouTube Data API
        # - Third-party trend monitoring services
        
        # Mock data for demonstration
        mock_trends = [
            TrendData(
                trend_id="ext_audio_001",
                name="Upbeat Electronic Beat",
                description="Trending electronic music for lifestyle content",
                trend_type="audio",
                volume=15000,
                growth_rate=45.2,
                virality_score=78.5,
                relevance_score=0.0,
                platform=platform,
                audio_duration=30.0,
                audio_mood="energetic",
                audio_bpm=128,
                copyright_status="royalty_free"
            ),
            TrendData(
                trend_id="ext_format_001",
                name="Before/After Transformation",
                description="Popular format showing transformations",
                trend_type="format",
                volume=8500,
                growth_rate=32.1,
                virality_score=85.2,
                relevance_score=0.0,
                platform=platform
            )
        ]
        
        trends.extend(mock_trends)
        return trends
    
    async def _filter_and_score_trends(
        self, 
        trend_data: List[TrendData], 
        filters: RecommendationFilter
    ) -> List[TrendData]:
        """Filter trends and calculate relevance scores"""
        filtered_trends = []
        
        # Get brand information for relevance scoring
        brand_info = await self._get_brand_info(filters.brand_id)
        
        for trend in trend_data:
            # Apply basic filters
            if trend.virality_score < filters.min_virality_score:
                continue
            
            # Calculate relevance score
            relevance_score = await self._calculate_relevance_score(trend, brand_info, filters)
            trend.relevance_score = relevance_score
            
            # Apply relevance threshold
            if relevance_score < 30.0:  # Minimum relevance threshold
                continue
            
            # Analyze audio if it's an audio trend
            if trend.trend_type == "audio" and trend.audio_url:
                audio_analysis = await self.audio_analyzer.analyze_audio_url(trend.audio_url)
                if audio_analysis:
                    trend.audio_mood = audio_analysis.get('mood')
                    trend.audio_bpm = audio_analysis.get('bpm')
            
            # Estimate decay date
            trend.estimated_decay_date = self._estimate_decay_date(trend)
            
            filtered_trends.append(trend)
        
        # Sort by combined virality and relevance score
        filtered_trends.sort(
            key=lambda t: (t.virality_score * 0.6 + t.relevance_score * 0.4), 
            reverse=True
        )
        
        return filtered_trends[:20]  # Return top 20 trends
    
    async def _calculate_relevance_score(
        self, 
        trend: TrendData, 
        brand_info: Dict, 
        filters: RecommendationFilter
    ) -> float:
        """Calculate how relevant a trend is to a specific brand"""
        score = 0.0
        
        # Industry relevance (40% weight)
        industry_score = self._calculate_industry_relevance(trend, brand_info.get('industry'))
        score += industry_score * 0.4
        
        # Audience relevance (30% weight)
        audience_score = self._calculate_audience_relevance(trend, brand_info.get('target_audience'))
        score += audience_score * 0.3
        
        # Brand voice alignment (20% weight)
        voice_score = self._calculate_voice_alignment(trend, brand_info.get('brand_voice'))
        score += voice_score * 0.2
        
        # Timing relevance (10% weight)
        timing_score = self._calculate_timing_relevance(trend)
        score += timing_score * 0.1
        
        return min(100.0, score)
    
    def _calculate_industry_relevance(self, trend: TrendData, industry: Optional[str]) -> float:
        """Calculate industry-specific relevance"""
        if not industry or industry not in self.industry_keywords:
            return 50.0  # Neutral score
        
        keywords = self.industry_keywords[industry]
        trend_text = f"{trend.name} {trend.description}".lower()
        
        # Count keyword matches
        matches = sum(1 for keyword in keywords if keyword in trend_text)
        relevance = min(100.0, (matches / len(keywords)) * 100)
        
        return relevance
    
    def _calculate_audience_relevance(self, trend: TrendData, target_audience: Optional[str]) -> float:
        """Calculate audience-specific relevance"""
        # Simplified audience matching
        # In production, this would use more sophisticated NLP
        
        if not target_audience:
            return 50.0
        
        # Age-based relevance
        age_keywords = {
            'gen_z': ['young', 'teen', 'student', 'college', 'viral', 'meme'],
            'millennial': ['adult', 'work', 'professional', 'lifestyle', 'career'],
            'gen_x': ['family', 'parent', 'home', 'mature', 'established']
        }
        
        audience_lower = target_audience.lower()
        trend_text = f"{trend.name} {trend.description}".lower()
        
        score = 50.0  # Base score
        
        for audience_type, keywords in age_keywords.items():
            if audience_type in audience_lower:
                matches = sum(1 for keyword in keywords if keyword in trend_text)
                score += matches * 10
        
        return min(100.0, score)
    
    def _calculate_voice_alignment(self, trend: TrendData, brand_voice: Optional[str]) -> float:
        """Calculate brand voice alignment"""
        if not brand_voice:
            return 50.0
        
        # Voice characteristic mapping
        voice_characteristics = {
            'professional': ['business', 'corporate', 'formal', 'expert'],
            'casual': ['fun', 'relaxed', 'informal', 'friendly'],
            'energetic': ['exciting', 'dynamic', 'active', 'vibrant'],
            'sophisticated': ['elegant', 'refined', 'luxury', 'premium'],
            'playful': ['fun', 'creative', 'quirky', 'entertaining']
        }
        
        voice_lower = brand_voice.lower()
        trend_text = f"{trend.name} {trend.description}".lower()
        
        score = 50.0
        
        for voice_type, characteristics in voice_characteristics.items():
            if voice_type in voice_lower:
                matches = sum(1 for char in characteristics if char in trend_text)
                score += matches * 15
        
        return min(100.0, score)
    
    def _calculate_timing_relevance(self, trend: TrendData) -> float:
        """Calculate timing-based relevance"""
        # Trends are more relevant when they're growing vs declining
        if trend.growth_rate > 20:
            return 100.0
        elif trend.growth_rate > 0:
            return 70.0
        elif trend.growth_rate > -10:
            return 50.0
        else:
            return 20.0
    
    async def _create_recommendations(
        self, 
        trends: List[TrendData], 
        brand_id: int, 
        platform: PlatformType
    ) -> List[TrendRecommendation]:
        """Convert trend data to recommendation objects"""
        recommendations = []
        
        for trend in trends:
            recommendation = TrendRecommendation(
                brand_id=brand_id,
                platform=platform,
                trend_type=trend.trend_type,
                trend_id=trend.trend_id,
                trend_name=trend.name,
                trend_description=trend.description,
                trend_volume=trend.volume,
                growth_rate=trend.growth_rate,
                virality_score=trend.virality_score,
                relevance_score=trend.relevance_score,
                audio_url=trend.audio_url,
                audio_duration=trend.audio_duration,
                audio_mood=trend.audio_mood,
                audio_bpm=trend.audio_bpm,
                copyright_status=trend.copyright_status,
                peak_usage_time=trend.peak_usage_time,
                estimated_decay_date=trend.estimated_decay_date,
                recommended_usage_window=self._calculate_usage_window(trend),
                is_active=True
            )
            recommendations.append(recommendation)
        
        return recommendations
    
    def _calculate_usage_window(self, trend: TrendData) -> Dict[str, Any]:
        """Calculate optimal usage window for trend"""
        now = datetime.now()
        
        # Base window on growth rate and current volume
        if trend.growth_rate > 50:
            # High growth - act quickly
            optimal_start = now
            optimal_end = now + timedelta(days=3)
        elif trend.growth_rate > 20:
            # Moderate growth - good window
            optimal_start = now
            optimal_end = now + timedelta(days=7)
        elif trend.growth_rate > 0:
            # Slow growth - longer window
            optimal_start = now
            optimal_end = now + timedelta(days=14)
        else:
            # Declining - use cautiously
            optimal_start = now
            optimal_end = now + timedelta(days=2)
        
        return {
            'optimal_start': optimal_start.isoformat(),
            'optimal_end': optimal_end.isoformat(),
            'urgency': 'high' if trend.growth_rate > 50 else 'medium' if trend.growth_rate > 20 else 'low',
            'confidence': min(100, trend.virality_score + trend.relevance_score) / 2
        }
    
    async def _save_recommendations(self, recommendations: List[TrendRecommendation]):
        """Save recommendations to database"""
        try:
            db = SessionLocal()
            
            for recommendation in recommendations:
                # Check if recommendation already exists
                existing = db.query(TrendRecommendation).filter(
                    and_(
                        TrendRecommendation.brand_id == recommendation.brand_id,
                        TrendRecommendation.trend_id == recommendation.trend_id,
                        TrendRecommendation.platform == recommendation.platform
                    )
                ).first()
                
                if existing:
                    # Update existing recommendation
                    for attr, value in recommendation.__dict__.items():
                        if not attr.startswith('_') and attr != 'id':
                            setattr(existing, attr, value)
                else:
                    # Add new recommendation
                    db.add(recommendation)
            
            db.commit()
            
        except Exception as e:
            logger.error(f"Error saving recommendations: {e}")
            db.rollback()
        finally:
            db.close()
    
    async def _get_brand_info(self, brand_id: int) -> Dict[str, Any]:
        """Get brand information for relevance calculation"""
        try:
            db = SessionLocal()
            brand = db.query(Brand).filter(Brand.id == brand_id).first()
            
            if not brand:
                return {}
            
            return {
                'industry': getattr(brand, 'industry', None),
                'target_audience': getattr(brand, 'target_audience', None),
                'brand_voice': getattr(brand, 'brand_voice', None),
                'keywords': getattr(brand, 'keywords', [])
            }
            
        except Exception as e:
            logger.error(f"Error getting brand info: {e}")
            return {}
        finally:
            db.close()
    
    def _calculate_growth_rate(self, sound) -> float:
        """Calculate growth rate for TikTok sound"""
        # Simplified calculation - in production would use historical data
        days_since_discovery = (datetime.now() - sound.discovered_at).days
        if days_since_discovery <= 0:
            return 100.0  # New trend
        
        # Estimate daily growth based on usage and recency
        daily_usage = (sound.usage_count or 0) / max(days_since_discovery, 1)
        
        # Normalize to percentage
        return min(100.0, daily_usage / 100)
    
    def _calculate_hashtag_growth_rate(self, hashtag) -> float:
        """Calculate growth rate for TikTok hashtag"""
        days_since_discovery = (datetime.now() - hashtag.discovered_at).days
        if days_since_discovery <= 0:
            return 100.0
        
        daily_views = (hashtag.view_count or 0) / max(days_since_discovery, 1)
        return min(100.0, daily_views / 10000)  # Normalize by 10K views
    
    def _calculate_virality_score(self, volume: int, discovered_at: datetime) -> float:
        """Calculate virality score based on volume and recency"""
        # Recency factor (more recent = higher score)
        days_old = (datetime.now() - discovered_at).days
        recency_factor = max(0.1, 1.0 - (days_old / 30.0))  # Decays over 30 days
        
        # Volume factor (logarithmic scaling)
        volume_factor = min(1.0, np.log10(max(volume, 1)) / 6.0)  # Scales to 1M
        
        # Combine factors
        virality_score = (volume_factor * 0.7 + recency_factor * 0.3) * 100
        
        return min(100.0, virality_score)
    
    def _estimate_decay_date(self, trend: TrendData) -> datetime:
        """Estimate when trend will lose relevance"""
        base_days = 14  # Base lifecycle
        
        # Adjust based on growth rate
        if trend.growth_rate > 50:
            lifecycle_days = base_days * 0.5  # Fast trends decay quickly
        elif trend.growth_rate > 20:
            lifecycle_days = base_days
        else:
            lifecycle_days = base_days * 1.5  # Slow trends last longer
        
        # Adjust based on trend type
        if trend.trend_type == "audio":
            lifecycle_days *= 1.2  # Audio trends last longer
        elif trend.trend_type == "hashtag":
            lifecycle_days *= 0.8  # Hashtags decay faster
        
        return datetime.now() + timedelta(days=int(lifecycle_days))


class AudioAnalyzer:
    """Analyze audio trends for mood and characteristics"""
    
    async def analyze_audio_url(self, audio_url: str) -> Optional[Dict[str, Any]]:
        """Analyze audio file from URL"""
        try:
            # In production, this would download and analyze the audio
            # For now, return mock analysis
            return {
                'mood': 'energetic',
                'bpm': 128,
                'genre': 'electronic',
                'energy_level': 0.8,
                'danceability': 0.9
            }
        except Exception as e:
            logger.error(f"Error analyzing audio: {e}")
            return None


class RelevanceCalculator:
    """Calculate trend relevance to brands"""
    
    def __init__(self):
        # This could be extended with ML models for better relevance scoring
        pass
    
    def calculate_semantic_similarity(self, text1: str, text2: str) -> float:
        """Calculate semantic similarity between texts"""
        # Placeholder for semantic similarity calculation
        # In production, would use sentence transformers or similar
        
        # Simple keyword overlap for now
        words1 = set(text1.lower().split())
        words2 = set(text2.lower().split())
        
        if not words1 or not words2:
            return 0.0
        
        intersection = words1.intersection(words2)
        union = words1.union(words2)
        
        return len(intersection) / len(union)