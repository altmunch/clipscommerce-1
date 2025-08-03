"""
TikTok Trend Integration with Existing Trend Analyzer

Integrates real-time TikTok trend data with the existing ViralOS trend analysis system.
Enhances content generation with platform-specific trend insights and viral patterns.
"""

import asyncio
import json
import logging
import statistics
from collections import Counter, defaultdict
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Tuple

from sqlalchemy.orm import Session
from sqlalchemy import desc, func, and_, or_

from app.core.config import settings
from app.db.session import get_db
from app.models.tiktok_trend import (
    TikTokTrend, TikTokVideo, TikTokHashtag, TikTokSound,
    TrendStatus, TrendType, ContentCategory
)
from app.services.ai.trend_analyzer import (
    TrendData, TrendSignal, TrendOpportunity, TrendSource, 
    TrendAnalysisService, Platform, get_trend_analysis_service
)
from app.services.ai.viral_content import Platform as ViralPlatform

logger = logging.getLogger(__name__)


class TikTokTrendEnhancer:
    """Enhances existing trend analysis with TikTok-specific data"""
    
    def __init__(self, db: Session):
        self.db = db
        
    async def enhance_trending_topics(
        self,
        existing_trends: List[TrendData],
        brand_industry: str = None,
        target_audience: str = None
    ) -> List[TrendData]:
        """
        Enhance existing trend detection with TikTok data
        
        Args:
            existing_trends: Trends from existing analyzer
            brand_industry: Brand industry for relevance filtering
            target_audience: Target audience for demographic matching
            
        Returns:
            Enhanced trend data with TikTok insights
        """
        
        logger.info(f"Enhancing {len(existing_trends)} trends with TikTok data")
        
        # Get active TikTok trends
        tiktok_trends = self.db.query(TikTokTrend).filter(
            and_(
                TikTokTrend.is_active == True,
                TikTokTrend.viral_score > 30,
                TikTokTrend.last_scraped > datetime.utcnow() - timedelta(hours=24)
            )
        ).order_by(desc(TikTokTrend.viral_score)).all()
        
        enhanced_trends = []
        
        # Enhance existing trends with TikTok data
        for trend in existing_trends:
            enhanced_trend = await self._enhance_single_trend(trend, tiktok_trends)
            enhanced_trends.append(enhanced_trend)
        
        # Add TikTok-only trends
        tiktok_only_trends = await self._create_tiktok_trends(
            existing_trends, tiktok_trends, brand_industry, target_audience
        )
        enhanced_trends.extend(tiktok_only_trends)
        
        # Sort by viral score
        enhanced_trends.sort(key=lambda t: t.viral_score, reverse=True)
        
        logger.info(f"Enhanced analysis complete: {len(enhanced_trends)} total trends")
        
        return enhanced_trends
    
    async def _enhance_single_trend(
        self,
        trend: TrendData,
        tiktok_trends: List[TikTokTrend]
    ) -> TrendData:
        """Enhance a single trend with TikTok data"""
        
        # Find matching TikTok trends
        matching_trends = []
        
        for tiktok_trend in tiktok_trends:
            similarity_score = self._calculate_trend_similarity(trend, tiktok_trend)
            if similarity_score > 0.3:  # 30% similarity threshold
                matching_trends.append((tiktok_trend, similarity_score))
        
        if not matching_trends:
            return trend
        
        # Sort by similarity
        matching_trends.sort(key=lambda x: x[1], reverse=True)
        best_match = matching_trends[0][0]
        
        # Enhance trend with TikTok data
        enhanced_trend = TrendData(
            trend_id=trend.trend_id,
            name=trend.name,
            trend_type=trend.trend_type,
            platform=Platform.TIKTOK,  # Update platform
            status=self._map_tiktok_status(best_match.trend_status),
            viral_score=max(trend.viral_score, best_match.viral_score),
            growth_rate=max(trend.growth_rate, best_match.growth_rate),
            volume=trend.volume + best_match.total_videos,
            engagement_rate=max(trend.engagement_rate, best_match.engagement_rate),
            demographic_data=self._merge_demographics(
                trend.demographic_data, best_match.demographic_data
            ),
            geographic_data=self._merge_geography(
                trend.geographic_data, best_match.geographic_data
            ),
            signals=trend.signals + await self._create_tiktok_signals(best_match),
            related_trends=list(set(trend.related_trends + (best_match.hashtags or []))),
            keywords=list(set(trend.keywords + (best_match.keywords or []))),
            first_detected=min(trend.first_detected, best_match.first_detected.timestamp()),
            peak_time=trend.peak_time,
            predicted_lifespan=trend.predicted_lifespan,
            content_examples=trend.content_examples + await self._get_tiktok_examples(best_match),
            influencer_adoption=trend.influencer_adoption,
            brand_opportunities=trend.brand_opportunities + await self._get_tiktok_opportunities(best_match),
            risk_factors=trend.risk_factors,
            last_updated=datetime.utcnow().timestamp()
        )
        
        return enhanced_trend
    
    def _calculate_trend_similarity(
        self,
        existing_trend: TrendData,
        tiktok_trend: TikTokTrend
    ) -> float:
        """Calculate similarity between existing trend and TikTok trend"""
        
        similarity_factors = []
        
        # Name similarity
        name_words = set(existing_trend.name.lower().split())
        tiktok_words = set(tiktok_trend.normalized_name.split())
        
        if name_words and tiktok_words:
            name_similarity = len(name_words.intersection(tiktok_words)) / len(name_words.union(tiktok_words))
            similarity_factors.append(name_similarity * 0.4)
        
        # Keyword similarity
        existing_keywords = set([kw.lower() for kw in existing_trend.keywords])
        tiktok_keywords = set([kw.lower() for kw in (tiktok_trend.keywords or [])])
        
        if existing_keywords and tiktok_keywords:
            keyword_similarity = len(existing_keywords.intersection(tiktok_keywords)) / len(existing_keywords.union(tiktok_keywords))
            similarity_factors.append(keyword_similarity * 0.3)
        
        # Hashtag overlap
        existing_hashtags = set([tag.lower() for tag in existing_trend.related_trends if tag.startswith('#')])
        tiktok_hashtags = set([tag.lower() for tag in (tiktok_trend.hashtags or [])])
        
        if existing_hashtags and tiktok_hashtags:
            hashtag_similarity = len(existing_hashtags.intersection(tiktok_hashtags)) / len(existing_hashtags.union(tiktok_hashtags))
            similarity_factors.append(hashtag_similarity * 0.3)
        
        return sum(similarity_factors) if similarity_factors else 0.0
    
    def _map_tiktok_status(self, tiktok_status: str) -> str:
        """Map TikTok trend status to general trend status"""
        
        status_mapping = {
            TrendStatus.EMERGING.value: "emerging",
            TrendStatus.RISING.value: "rising", 
            TrendStatus.PEAK.value: "peak",
            TrendStatus.DECLINING.value: "declining",
            TrendStatus.FADING.value: "fading"
        }
        
        return status_mapping.get(tiktok_status, "rising")
    
    def _merge_demographics(
        self,
        existing_demo: Dict[str, Any],
        tiktok_demo: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Merge demographic data from both sources"""
        
        if not tiktok_demo:
            return existing_demo
        
        if not existing_demo:
            return tiktok_demo
        
        # Weighted average of age groups
        merged_demo = existing_demo.copy()
        
        if "age_groups" in tiktok_demo and "age_groups" in existing_demo:
            merged_age_groups = {}
            all_age_groups = set(existing_demo["age_groups"].keys()) | set(tiktok_demo["age_groups"].keys())
            
            for age_group in all_age_groups:
                existing_val = existing_demo["age_groups"].get(age_group, 0)
                tiktok_val = tiktok_demo["age_groups"].get(age_group, 0)
                merged_age_groups[age_group] = (existing_val + tiktok_val) / 2
            
            merged_demo["age_groups"] = merged_age_groups
        
        return merged_demo
    
    def _merge_geography(
        self,
        existing_geo: Dict[str, Any],
        tiktok_geo: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Merge geographic data from both sources"""
        
        if not tiktok_geo:
            return existing_geo
        
        if not existing_geo:
            return tiktok_geo
        
        merged_geo = existing_geo.copy()
        
        # Merge top countries if available
        if "top_countries" in tiktok_geo and "top_countries" in existing_geo:
            all_countries = set(existing_geo["top_countries"].keys()) | set(tiktok_geo["top_countries"].keys())
            merged_countries = {}
            
            for country in all_countries:
                existing_val = existing_geo["top_countries"].get(country, 0)
                tiktok_val = tiktok_geo["top_countries"].get(country, 0)
                merged_countries[country] = max(existing_val, tiktok_val)
            
            merged_geo["top_countries"] = merged_countries
        
        return merged_geo
    
    async def _create_tiktok_signals(self, tiktok_trend: TikTokTrend) -> List[TrendSignal]:
        """Create trend signals from TikTok data"""
        
        signals = []
        
        # Volume signal
        signals.append(TrendSignal(
            signal_id=f"tiktok_volume_{tiktok_trend.trend_id}",
            content=f"TikTok trend volume: {tiktok_trend.total_videos} videos",
            signal_strength=min(tiktok_trend.total_videos / 10000, 1.0),
            platform=Platform.TIKTOK,
            source=TrendSource.SOCIAL_PLATFORMS,
            detected_at=datetime.utcnow().timestamp(),
            metadata={
                "total_videos": tiktok_trend.total_videos,
                "total_views": tiktok_trend.total_views,
                "viral_score": tiktok_trend.viral_score
            }
        ))
        
        # Engagement signal
        signals.append(TrendSignal(
            signal_id=f"tiktok_engagement_{tiktok_trend.trend_id}",
            content=f"TikTok engagement rate: {tiktok_trend.engagement_rate:.2f}%",
            signal_strength=min(tiktok_trend.engagement_rate / 10, 1.0),
            platform=Platform.TIKTOK,
            source=TrendSource.SOCIAL_PLATFORMS,
            detected_at=datetime.utcnow().timestamp(),
            metadata={
                "engagement_rate": tiktok_trend.engagement_rate,
                "growth_rate": tiktok_trend.growth_rate
            }
        ))
        
        # Viral score signal
        if tiktok_trend.viral_score > 70:
            signals.append(TrendSignal(
                signal_id=f"tiktok_viral_{tiktok_trend.trend_id}",
                content=f"High viral score detected: {tiktok_trend.viral_score}",
                signal_strength=tiktok_trend.viral_score / 100,
                platform=Platform.TIKTOK,
                source=TrendSource.AI_DETECTION,
                detected_at=datetime.utcnow().timestamp(),
                metadata={
                    "viral_score": tiktok_trend.viral_score,
                    "trend_type": tiktok_trend.trend_type,
                    "status": tiktok_trend.trend_status
                }
            ))
        
        return signals
    
    async def _get_tiktok_examples(self, tiktok_trend: TikTokTrend) -> List[Dict[str, Any]]:
        """Get example content from TikTok trend"""
        
        # Get top videos for this trend
        videos = self.db.query(TikTokVideo).filter(
            TikTokVideo.trend_id == tiktok_trend.id
        ).order_by(desc(TikTokVideo.view_count)).limit(3).all()
        
        examples = []
        for video in videos:
            examples.append({
                "title": video.description[:100] if video.description else f"TikTok Video {video.video_id}",
                "engagement": video.view_count,
                "author": video.creator_username,
                "url": video.tiktok_url,
                "platform": "tiktok",
                "posted_at": video.posted_at.timestamp() if video.posted_at else video.created_at.timestamp(),
                "viral_score": getattr(video, 'viral_score', 0),
                "content_hooks": video.content_hooks if hasattr(video, 'content_hooks') else []
            })
        
        return examples
    
    async def _get_tiktok_opportunities(self, tiktok_trend: TikTokTrend) -> List[str]:
        """Get brand opportunities from TikTok trend"""
        
        opportunities = []
        
        # Hashtag opportunities
        if tiktok_trend.hashtags:
            top_hashtags = tiktok_trend.hashtags[:3]
            opportunities.append(f"Use trending hashtags: {', '.join(top_hashtags)}")
        
        # Content format opportunities
        if tiktok_trend.trend_type == TrendType.CHALLENGE.value:
            opportunities.append(f"Participate in {tiktok_trend.name} challenge")
        elif tiktok_trend.trend_type == TrendType.DANCE.value:
            opportunities.append(f"Create dance content inspired by {tiktok_trend.name}")
        elif tiktok_trend.trend_type == TrendType.SOUND.value:
            opportunities.append(f"Use trending sound in original content")
        elif tiktok_trend.trend_type == TrendType.TREND_FORMAT.value:
            opportunities.append(f"Adapt {tiktok_trend.name} format for brand content")
        
        # Timing opportunities
        if tiktok_trend.trend_status == TrendStatus.EMERGING.value:
            opportunities.append("Early entry opportunity - low competition")
        elif tiktok_trend.trend_status == TrendStatus.RISING.value:
            opportunities.append("Join rising trend for maximum visibility")
        
        return opportunities
    
    async def _create_tiktok_trends(
        self,
        existing_trends: List[TrendData],
        tiktok_trends: List[TikTokTrend],
        brand_industry: str = None,
        target_audience: str = None
    ) -> List[TrendData]:
        """Create TrendData objects from TikTok-only trends"""
        
        # Find TikTok trends not covered by existing trends
        existing_keywords = set()
        for trend in existing_trends:
            existing_keywords.update([kw.lower() for kw in trend.keywords])
            existing_keywords.update([name.lower() for name in trend.related_trends])
        
        tiktok_only = []
        
        for tiktok_trend in tiktok_trends:
            # Check if this TikTok trend is already covered
            tiktok_keywords = set([kw.lower() for kw in (tiktok_trend.keywords or [])])
            tiktok_hashtags = set([tag.lower() for tag in (tiktok_trend.hashtags or [])])
            
            overlap = len(existing_keywords.intersection(tiktok_keywords | tiktok_hashtags))
            
            if overlap < 2:  # Minimal overlap, this is a TikTok-specific trend
                trend_data = await self._convert_tiktok_to_trend_data(tiktok_trend)
                
                # Apply relevance filtering
                if brand_industry or target_audience:
                    relevance_score = self._calculate_brand_relevance(
                        trend_data, brand_industry, target_audience
                    )
                    if relevance_score > 0.3:  # 30% relevance threshold
                        tiktok_only.append(trend_data)
                else:
                    tiktok_only.append(trend_data)
        
        return tiktok_only
    
    async def _convert_tiktok_to_trend_data(self, tiktok_trend: TikTokTrend) -> TrendData:
        """Convert TikTokTrend to TrendData format"""
        
        # Get associated videos for examples
        videos = self.db.query(TikTokVideo).filter(
            TikTokVideo.trend_id == tiktok_trend.id
        ).order_by(desc(TikTokVideo.view_count)).limit(5).all()
        
        content_examples = []
        for video in videos:
            content_examples.append({
                "title": video.description[:100] if video.description else f"TikTok Video",
                "engagement": video.view_count,
                "author": video.creator_username,
                "url": video.tiktok_url,
                "posted_at": video.posted_at.timestamp() if video.posted_at else video.created_at.timestamp()
            })
        
        # Create trend signals
        signals = await self._create_tiktok_signals(tiktok_trend)
        
        # Generate brand opportunities
        brand_opportunities = await self._get_tiktok_opportunities(tiktok_trend)
        
        return TrendData(
            trend_id=f"tiktok_{tiktok_trend.trend_id}",
            name=tiktok_trend.name,
            trend_type=self._map_trend_type(tiktok_trend.trend_type),
            platform=Platform.TIKTOK,
            status=self._map_tiktok_status(tiktok_trend.trend_status),
            viral_score=tiktok_trend.viral_score,
            growth_rate=tiktok_trend.growth_rate,
            volume=tiktok_trend.total_videos,
            engagement_rate=tiktok_trend.engagement_rate,
            demographic_data=tiktok_trend.demographic_data or {},
            geographic_data=tiktok_trend.geographic_data or {},
            signals=signals,
            related_trends=tiktok_trend.hashtags or [],
            keywords=tiktok_trend.keywords or [],
            first_detected=tiktok_trend.first_detected.timestamp(),
            peak_time=tiktok_trend.peak_time.timestamp() if tiktok_trend.peak_time else None,
            predicted_lifespan=72,  # Default 3 days for TikTok trends
            content_examples=content_examples,
            influencer_adoption=[],  # Would need to extract from video data
            brand_opportunities=brand_opportunities,
            risk_factors=self._assess_tiktok_risks(tiktok_trend),
            last_updated=datetime.utcnow().timestamp()
        )
    
    def _map_trend_type(self, tiktok_type: str) -> str:
        """Map TikTok trend type to general trend type"""
        
        type_mapping = {
            TrendType.HASHTAG.value: "hashtag",
            TrendType.SOUND.value: "sound",
            TrendType.CHALLENGE.value: "challenge",
            TrendType.DANCE.value: "challenge",
            TrendType.MEME.value: "meme",
            TrendType.TREND_FORMAT.value: "viral_format",
            TrendType.VIRAL_VIDEO.value: "topic"
        }
        
        return type_mapping.get(tiktok_type, "topic")
    
    def _assess_tiktok_risks(self, tiktok_trend: TikTokTrend) -> List[str]:
        """Assess risks for TikTok trend participation"""
        
        risks = []
        
        # High competition risk
        if tiktok_trend.total_videos > 100000:
            risks.append("High competition - trend already saturated")
        
        # Declining trend risk
        if tiktok_trend.trend_status in [TrendStatus.DECLINING.value, TrendStatus.FADING.value]:
            risks.append("Trend momentum declining")
        
        # Platform-specific risks
        if tiktok_trend.trend_type == TrendType.CHALLENGE.value:
            risks.append("Challenge format may not align with all brand types")
        
        if tiktok_trend.trend_type == TrendType.DANCE.value:
            risks.append("Dance content requires specific creative skills")
        
        # Fast-moving trend risk
        if tiktok_trend.growth_rate > 500:
            risks.append("Very fast-moving trend - limited time window")
        
        return risks
    
    def _calculate_brand_relevance(
        self,
        trend: TrendData,
        brand_industry: str,
        target_audience: str
    ) -> float:
        """Calculate how relevant a trend is to a specific brand"""
        
        relevance_score = 0.0
        
        # Industry keyword matching
        if brand_industry:
            industry_keywords = brand_industry.lower().split()
            trend_keywords = [kw.lower() for kw in trend.keywords]
            
            keyword_matches = len(set(industry_keywords).intersection(set(trend_keywords)))
            if keyword_matches > 0:
                relevance_score += 0.4 * (keyword_matches / len(industry_keywords))
        
        # Demographic matching
        if target_audience and trend.demographic_data:
            # Simple demographic matching based on age groups
            if "young" in target_audience.lower() or "teen" in target_audience.lower():
                young_percentage = (
                    trend.demographic_data.get("age_groups", {}).get("13-17", 0) +
                    trend.demographic_data.get("age_groups", {}).get("18-24", 0)
                )
                relevance_score += 0.3 * (young_percentage / 100)
            
            elif "adult" in target_audience.lower():
                adult_percentage = (
                    trend.demographic_data.get("age_groups", {}).get("25-34", 0) +
                    trend.demographic_data.get("age_groups", {}).get("35-44", 0)
                )
                relevance_score += 0.3 * (adult_percentage / 100)
        
        # Platform appropriateness
        relevance_score += 0.3  # Base relevance for TikTok trends
        
        return min(relevance_score, 1.0)


class TikTokTrendProvider:
    """Provider for TikTok trend data to existing systems"""
    
    def __init__(self, db: Session):
        self.db = db
        self.enhancer = TikTokTrendEnhancer(db)
    
    async def get_enhanced_trends(
        self,
        platforms: List[Platform],
        industry_keywords: List[str] = None,
        brand_industry: str = None,
        target_audience: str = None
    ) -> List[TrendData]:
        """
        Get trends enhanced with TikTok data
        
        Args:
            platforms: Platforms to analyze (must include TIKTOK)
            industry_keywords: Keywords for industry filtering
            brand_industry: Brand industry context
            target_audience: Target audience context
            
        Returns:
            List of enhanced trends
        """
        
        # Get base trends from existing service
        trend_service = await get_trend_analysis_service()
        
        # If TikTok not in platforms, add TikTok-specific trends anyway
        if Platform.TIKTOK not in platforms:
            platforms = list(platforms) + [Platform.TIKTOK]
        
        # Get existing trends
        existing_trends = await trend_service.detector.detect_trending_topics(
            platforms=platforms,
            industry_keywords=industry_keywords or [],
            time_window_hours=24
        )
        
        # Enhance with TikTok data
        enhanced_trends = await self.enhancer.enhance_trending_topics(
            existing_trends=existing_trends,
            brand_industry=brand_industry,
            target_audience=target_audience
        )
        
        return enhanced_trends
    
    async def get_tiktok_opportunities(
        self,
        brand_name: str,
        industry: str,
        target_audience: str,
        brand_voice: Dict[str, Any] = None
    ) -> List[TrendOpportunity]:
        """
        Get TikTok-specific content opportunities
        
        Args:
            brand_name: Brand name
            industry: Brand industry
            target_audience: Target audience description
            brand_voice: Brand voice characteristics
            
        Returns:
            List of TikTok trend opportunities
        """
        
        # Get TikTok trends
        tiktok_trends = self.db.query(TikTokTrend).filter(
            and_(
                TikTokTrend.is_active == True,
                TikTokTrend.viral_score > 40,
                TikTokTrend.trend_status.in_([
                    TrendStatus.EMERGING.value,
                    TrendStatus.RISING.value,
                    TrendStatus.PEAK.value
                ])
            )
        ).order_by(desc(TikTokTrend.viral_score)).limit(20).all()
        
        # Convert to TrendData format
        trend_data_list = []
        for tiktok_trend in tiktok_trends:
            trend_data = await self.enhancer._convert_tiktok_to_trend_data(tiktok_trend)
            trend_data_list.append(trend_data)
        
        # Use existing opportunity engine
        trend_service = await get_trend_analysis_service()
        opportunities = await trend_service.opportunity_engine.identify_opportunities(
            trends=trend_data_list,
            brand_name=brand_name,
            industry=industry,
            target_audience=target_audience,
            brand_voice=brand_voice or {},
            platforms=[Platform.TIKTOK]
        )
        
        return opportunities
    
    async def get_platform_insights(self) -> Dict[str, Any]:
        """Get TikTok platform-specific insights"""
        
        # Get recent trends summary
        recent_trends = self.db.query(TikTokTrend).filter(
            and_(
                TikTokTrend.is_active == True,
                TikTokTrend.first_detected > datetime.utcnow() - timedelta(days=7)
            )
        ).count()
        
        # Get top content categories
        category_counts = self.db.query(
            TikTokTrend.content_category,
            func.count(TikTokTrend.id).label('count')
        ).filter(
            and_(
                TikTokTrend.is_active == True,
                TikTokTrend.viral_score > 50
            )
        ).group_by(TikTokTrend.content_category).all()
        
        # Get trending hashtags
        trending_hashtags = self.db.query(TikTokHashtag).filter(
            TikTokHashtag.is_trending == True
        ).order_by(desc(TikTokHashtag.trend_score)).limit(10).all()
        
        # Get trending sounds
        trending_sounds = self.db.query(TikTokSound).filter(
            TikTokSound.is_trending == True
        ).order_by(desc(TikTokSound.trend_score)).limit(5).all()
        
        return {
            "platform": "TikTok",
            "data_freshness": "Real-time",
            "recent_trends_count": recent_trends,
            "top_categories": [
                {"category": cat, "count": count} 
                for cat, count in category_counts
            ],
            "trending_hashtags": [
                {"hashtag": h.hashtag, "score": h.trend_score} 
                for h in trending_hashtags
            ],
            "trending_sounds": [
                {"title": s.title or s.sound_id, "score": s.trend_score} 
                for s in trending_sounds
            ],
            "last_updated": datetime.utcnow().isoformat()
        }


# Global provider instance
_tiktok_provider: Optional[TikTokTrendProvider] = None


async def get_tiktok_trend_provider() -> TikTokTrendProvider:
    """Get global TikTok trend provider instance"""
    global _tiktok_provider
    
    if _tiktok_provider is None:
        db = next(get_db())
        _tiktok_provider = TikTokTrendProvider(db)
    
    return _tiktok_provider


# Integration functions for existing services
async def enhance_trends_with_tiktok(
    existing_trends: List[TrendData],
    brand_context: Dict[str, Any] = None
) -> List[TrendData]:
    """Enhance existing trends with TikTok data"""
    
    provider = await get_tiktok_trend_provider()
    
    enhanced_trends = await provider.enhancer.enhance_trending_topics(
        existing_trends=existing_trends,
        brand_industry=brand_context.get('industry') if brand_context else None,
        target_audience=brand_context.get('target_audience') if brand_context else None
    )
    
    return enhanced_trends


async def get_tiktok_trend_opportunities(
    brand_info: Dict[str, Any]
) -> List[TrendOpportunity]:
    """Get TikTok-specific opportunities for a brand"""
    
    provider = await get_tiktok_trend_provider()
    
    opportunities = await provider.get_tiktok_opportunities(
        brand_name=brand_info.get('name', ''),
        industry=brand_info.get('industry', ''),
        target_audience=brand_info.get('target_audience', ''),
        brand_voice=brand_info.get('brand_voice', {})
    )
    
    return opportunities


async def get_tiktok_platform_insights() -> Dict[str, Any]:
    """Get TikTok platform insights"""
    
    provider = await get_tiktok_trend_provider()
    return await provider.get_platform_insights()