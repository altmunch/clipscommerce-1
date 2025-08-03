"""
TikTok Trend Models

Database models for storing TikTok trend data, hashtags, sounds, video analytics,
and viral pattern recognition data extracted via Apify scraping.
"""

import json
from datetime import datetime
from enum import Enum
from typing import Dict, Any, List, Optional

from sqlalchemy import (
    Column, Integer, String, Text, DateTime, Float, Boolean, 
    JSON, ForeignKey, Index, UniqueConstraint, BigInteger
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import UUID

from app.db.session import Base


class TrendStatus(str, Enum):
    """Trend lifecycle status"""
    EMERGING = "emerging"
    RISING = "rising" 
    PEAK = "peak"
    DECLINING = "declining"
    FADING = "fading"
    REVIVED = "revived"


class TrendType(str, Enum):
    """Types of TikTok trends"""
    HASHTAG = "hashtag"
    SOUND = "sound"
    EFFECT = "effect"
    CHALLENGE = "challenge"
    DANCE = "dance"
    MEME = "meme"
    TREND_FORMAT = "trend_format"
    VIRAL_VIDEO = "viral_video"


class ContentCategory(str, Enum):
    """Content categories for trends"""
    ENTERTAINMENT = "entertainment"
    EDUCATION = "education"
    LIFESTYLE = "lifestyle"
    FASHION = "fashion"
    FOOD = "food"
    FITNESS = "fitness"
    TECHNOLOGY = "technology"
    BUSINESS = "business"
    NEWS = "news"
    OTHER = "other"


class TikTokTrend(Base):
    """Main TikTok trend entity"""
    __tablename__ = "tiktok_trends"

    id = Column(Integer, primary_key=True, index=True)
    trend_id = Column(String(100), unique=True, index=True, nullable=False)  # External trend ID
    name = Column(String(500), nullable=False, index=True)
    normalized_name = Column(String(500), index=True)  # For similarity matching
    
    # Trend classification
    trend_type = Column(String(50), nullable=False, index=True)
    trend_status = Column(String(50), nullable=False, index=True)
    content_category = Column(String(50), index=True)
    
    # Metrics
    total_videos = Column(BigInteger, default=0)
    total_views = Column(BigInteger, default=0)
    total_likes = Column(BigInteger, default=0)
    total_shares = Column(BigInteger, default=0)
    total_comments = Column(BigInteger, default=0)
    
    # Analytics
    viral_score = Column(Float, default=0.0, index=True)
    growth_rate = Column(Float, default=0.0)  # Percentage growth
    engagement_rate = Column(Float, default=0.0)
    velocity = Column(Float, default=0.0)  # Growth rate / time
    
    # Trend lifecycle
    first_detected = Column(DateTime, nullable=False, default=datetime.utcnow)
    peak_time = Column(DateTime, nullable=True)
    predicted_end = Column(DateTime, nullable=True)
    last_scraped = Column(DateTime, default=datetime.utcnow)
    
    # Metadata
    description = Column(Text, nullable=True)
    keywords = Column(JSON, default=list)  # List of keywords
    hashtags = Column(JSON, default=list)  # Associated hashtags
    
    # Geographic and demographic data
    geographic_data = Column(JSON, default=dict)
    demographic_data = Column(JSON, default=dict)
    
    # Platform specific data
    tiktok_metadata = Column(JSON, default=dict)
    
    # Relationships
    videos = relationship("TikTokVideo", back_populates="trend")
    hashtag_associations = relationship("TikTokHashtag", back_populates="trend")
    sound_associations = relationship("TikTokSound", back_populates="trend")
    
    # Audit fields
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    is_active = Column(Boolean, default=True)

    # Indexes
    __table_args__ = (
        Index('idx_tiktok_trend_status_score', 'trend_status', 'viral_score'),
        Index('idx_tiktok_trend_type_category', 'trend_type', 'content_category'),
        Index('idx_tiktok_trend_detected_score', 'first_detected', 'viral_score'),
        Index('idx_tiktok_trend_active', 'is_active', 'viral_score'),
    )

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for API responses"""
        return {
            "id": self.id,
            "trend_id": self.trend_id,
            "name": self.name,
            "trend_type": self.trend_type,
            "trend_status": self.trend_status,
            "content_category": self.content_category,
            "total_videos": self.total_videos,
            "total_views": self.total_views,
            "total_likes": self.total_likes,
            "total_shares": self.total_shares,
            "total_comments": self.total_comments,
            "viral_score": self.viral_score,
            "growth_rate": self.growth_rate,
            "engagement_rate": self.engagement_rate,
            "velocity": self.velocity,
            "first_detected": self.first_detected.isoformat() if self.first_detected else None,
            "peak_time": self.peak_time.isoformat() if self.peak_time else None,
            "predicted_end": self.predicted_end.isoformat() if self.predicted_end else None,
            "last_scraped": self.last_scraped.isoformat() if self.last_scraped else None,
            "description": self.description,
            "keywords": self.keywords,
            "hashtags": self.hashtags,
            "geographic_data": self.geographic_data,
            "demographic_data": self.demographic_data,
            "tiktok_metadata": self.tiktok_metadata,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "is_active": self.is_active
        }


class TikTokVideo(Base):
    """Individual TikTok video data"""
    __tablename__ = "tiktok_videos"

    id = Column(Integer, primary_key=True, index=True)
    video_id = Column(String(100), unique=True, index=True, nullable=False)
    trend_id = Column(Integer, ForeignKey("tiktok_trends.id"), nullable=True, index=True)
    
    # Video metadata
    title = Column(Text, nullable=True)
    description = Column(Text, nullable=True)
    duration = Column(Integer, nullable=True)  # Duration in seconds
    
    # Creator information
    creator_username = Column(String(100), index=True)
    creator_display_name = Column(String(200))
    creator_follower_count = Column(Integer, default=0)
    creator_verified = Column(Boolean, default=False)
    
    # Engagement metrics
    view_count = Column(BigInteger, default=0)
    like_count = Column(Integer, default=0)
    share_count = Column(Integer, default=0)
    comment_count = Column(Integer, default=0)
    engagement_rate = Column(Float, default=0.0)
    
    # Video characteristics
    hashtags = Column(JSON, default=list)
    mentions = Column(JSON, default=list)
    sounds_used = Column(JSON, default=list)
    effects_used = Column(JSON, default=list)
    
    # Content analysis
    transcript = Column(Text, nullable=True)
    visual_elements = Column(JSON, default=list)
    content_hooks = Column(JSON, default=list)  # Identified hooks
    video_structure = Column(JSON, default=dict)  # Structure analysis
    
    # TikTok specific data
    tiktok_url = Column(String(500), nullable=True)
    posted_at = Column(DateTime, nullable=True)
    video_quality = Column(String(20), nullable=True)  # HD, FHD, etc.
    
    # Scraping metadata
    scraped_at = Column(DateTime, default=datetime.utcnow)
    scraping_source = Column(String(100), default="apify")
    raw_data = Column(JSON, default=dict)  # Raw scraped data
    
    # Relationships
    trend = relationship("TikTokTrend", back_populates="videos")
    
    # Audit fields
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    is_active = Column(Boolean, default=True)

    # Indexes
    __table_args__ = (
        Index('idx_tiktok_video_creator', 'creator_username'),
        Index('idx_tiktok_video_engagement', 'view_count', 'like_count'),
        Index('idx_tiktok_video_posted', 'posted_at'),
        Index('idx_tiktok_video_scraped', 'scraped_at'),
    )

    def calculate_engagement_rate(self) -> float:
        """Calculate engagement rate for the video"""
        if self.view_count and self.view_count > 0:
            total_engagement = (self.like_count + self.share_count + self.comment_count)
            return (total_engagement / self.view_count) * 100
        return 0.0

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for API responses"""
        return {
            "id": self.id,
            "video_id": self.video_id,
            "trend_id": self.trend_id,
            "title": self.title,
            "description": self.description,
            "duration": self.duration,
            "creator_username": self.creator_username,
            "creator_display_name": self.creator_display_name,
            "creator_follower_count": self.creator_follower_count,
            "creator_verified": self.creator_verified,
            "view_count": self.view_count,
            "like_count": self.like_count,
            "share_count": self.share_count,
            "comment_count": self.comment_count,
            "engagement_rate": self.engagement_rate,
            "hashtags": self.hashtags,
            "mentions": self.mentions,
            "sounds_used": self.sounds_used,
            "effects_used": self.effects_used,
            "transcript": self.transcript,
            "visual_elements": self.visual_elements,
            "content_hooks": self.content_hooks,
            "video_structure": self.video_structure,
            "tiktok_url": self.tiktok_url,
            "posted_at": self.posted_at.isoformat() if self.posted_at else None,
            "video_quality": self.video_quality,
            "scraped_at": self.scraped_at.isoformat() if self.scraped_at else None,
            "scraping_source": self.scraping_source,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "is_active": self.is_active
        }


class TikTokHashtag(Base):
    """TikTok hashtag tracking"""
    __tablename__ = "tiktok_hashtags"

    id = Column(Integer, primary_key=True, index=True)
    hashtag = Column(String(200), unique=True, index=True, nullable=False)
    normalized_hashtag = Column(String(200), index=True)  # Lowercase, cleaned
    trend_id = Column(Integer, ForeignKey("tiktok_trends.id"), nullable=True, index=True)
    
    # Usage metrics
    total_videos = Column(BigInteger, default=0)
    total_views = Column(BigInteger, default=0)
    usage_velocity = Column(Float, default=0.0)  # Videos per hour
    
    # Trend analysis
    is_trending = Column(Boolean, default=False, index=True)
    trend_score = Column(Float, default=0.0)
    first_seen = Column(DateTime, default=datetime.utcnow)
    peak_usage = Column(DateTime, nullable=True)
    
    # Associated data
    related_hashtags = Column(JSON, default=list)
    top_creators = Column(JSON, default=list)
    geographic_distribution = Column(JSON, default=dict)
    
    # Relationships
    trend = relationship("TikTokTrend", back_populates="hashtag_associations")
    
    # Audit fields
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    last_analyzed = Column(DateTime, default=datetime.utcnow)

    # Indexes
    __table_args__ = (
        Index('idx_tiktok_hashtag_trending', 'is_trending', 'trend_score'),
        Index('idx_tiktok_hashtag_usage', 'total_videos', 'usage_velocity'),
        Index('idx_tiktok_hashtag_seen', 'first_seen'),
    )

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for API responses"""
        return {
            "id": self.id,
            "hashtag": self.hashtag,
            "trend_id": self.trend_id,
            "total_videos": self.total_videos,
            "total_views": self.total_views,
            "usage_velocity": self.usage_velocity,
            "is_trending": self.is_trending,
            "trend_score": self.trend_score,
            "first_seen": self.first_seen.isoformat() if self.first_seen else None,
            "peak_usage": self.peak_usage.isoformat() if self.peak_usage else None,
            "related_hashtags": self.related_hashtags,
            "top_creators": self.top_creators,
            "geographic_distribution": self.geographic_distribution,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "last_analyzed": self.last_analyzed.isoformat() if self.last_analyzed else None
        }


class TikTokSound(Base):
    """TikTok sound/music tracking"""
    __tablename__ = "tiktok_sounds"

    id = Column(Integer, primary_key=True, index=True)
    sound_id = Column(String(100), unique=True, index=True, nullable=False)
    trend_id = Column(Integer, ForeignKey("tiktok_trends.id"), nullable=True, index=True)
    
    # Sound metadata
    title = Column(String(500), nullable=True)
    artist = Column(String(200), nullable=True, index=True)
    duration = Column(Integer, nullable=True)  # Duration in seconds
    sound_url = Column(String(500), nullable=True)
    
    # Usage metrics
    total_videos = Column(BigInteger, default=0)
    total_views = Column(BigInteger, default=0)
    usage_velocity = Column(Float, default=0.0)  # Videos per hour
    
    # Trend analysis
    is_trending = Column(Boolean, default=False, index=True)
    trend_score = Column(Float, default=0.0)
    first_detected = Column(DateTime, default=datetime.utcnow)
    peak_usage = Column(DateTime, nullable=True)
    
    # Sound characteristics
    genre = Column(String(100), nullable=True, index=True)
    mood = Column(String(100), nullable=True)
    tempo = Column(String(50), nullable=True)  # slow, medium, fast
    is_original = Column(Boolean, default=False)
    is_licensed = Column(Boolean, default=True)
    
    # Associated data
    top_creators = Column(JSON, default=list)
    usage_patterns = Column(JSON, default=dict)  # Time-based usage patterns
    geographic_distribution = Column(JSON, default=dict)
    
    # Relationships
    trend = relationship("TikTokTrend", back_populates="sound_associations")
    
    # Audit fields
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    last_analyzed = Column(DateTime, default=datetime.utcnow)

    # Indexes
    __table_args__ = (
        Index('idx_tiktok_sound_trending', 'is_trending', 'trend_score'),
        Index('idx_tiktok_sound_artist', 'artist'),
        Index('idx_tiktok_sound_genre', 'genre'),
        Index('idx_tiktok_sound_usage', 'total_videos', 'usage_velocity'),
    )

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for API responses"""
        return {
            "id": self.id,
            "sound_id": self.sound_id,
            "trend_id": self.trend_id,
            "title": self.title,
            "artist": self.artist,
            "duration": self.duration,
            "sound_url": self.sound_url,
            "total_videos": self.total_videos,
            "total_views": self.total_views,
            "usage_velocity": self.usage_velocity,
            "is_trending": self.is_trending,
            "trend_score": self.trend_score,
            "first_detected": self.first_detected.isoformat() if self.first_detected else None,
            "peak_usage": self.peak_usage.isoformat() if self.peak_usage else None,
            "genre": self.genre,
            "mood": self.mood,
            "tempo": self.tempo,
            "is_original": self.is_original,
            "is_licensed": self.is_licensed,
            "top_creators": self.top_creators,
            "usage_patterns": self.usage_patterns,
            "geographic_distribution": self.geographic_distribution,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "last_analyzed": self.last_analyzed.isoformat() if self.last_analyzed else None
        }


class TikTokScrapingJob(Base):
    """Track TikTok scraping jobs and their status"""
    __tablename__ = "tiktok_scraping_jobs"

    id = Column(Integer, primary_key=True, index=True)
    job_id = Column(String(100), unique=True, index=True, nullable=False)
    apify_run_id = Column(String(100), unique=True, index=True, nullable=True)
    
    # Job configuration
    job_type = Column(String(50), nullable=False, index=True)  # trending, hashtag, user, sound
    target = Column(String(500), nullable=True)  # Target hashtag, user, etc.
    parameters = Column(JSON, default=dict)  # Scraping parameters
    
    # Job status
    status = Column(String(50), default="pending", index=True)  # pending, running, completed, failed
    progress = Column(Float, default=0.0)  # 0-100
    
    # Results
    videos_scraped = Column(Integer, default=0)
    trends_identified = Column(Integer, default=0)
    hashtags_discovered = Column(Integer, default=0)
    sounds_tracked = Column(Integer, default=0)
    
    # Timing
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    estimated_duration = Column(Integer, nullable=True)  # Estimated duration in seconds
    
    # Error handling
    error_count = Column(Integer, default=0)
    last_error = Column(Text, nullable=True)
    retry_count = Column(Integer, default=0)
    max_retries = Column(Integer, default=3)
    
    # Data quality
    data_quality_score = Column(Float, default=0.0)
    validation_errors = Column(JSON, default=list)
    
    # Audit fields
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Indexes
    __table_args__ = (
        Index('idx_tiktok_job_status_type', 'status', 'job_type'),
        Index('idx_tiktok_job_created', 'created_at'),
        Index('idx_tiktok_job_completed', 'completed_at'),
    )

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for API responses"""
        return {
            "id": self.id,
            "job_id": self.job_id,
            "apify_run_id": self.apify_run_id,
            "job_type": self.job_type,
            "target": self.target,
            "parameters": self.parameters,
            "status": self.status,
            "progress": self.progress,
            "videos_scraped": self.videos_scraped,
            "trends_identified": self.trends_identified,
            "hashtags_discovered": self.hashtags_discovered,
            "sounds_tracked": self.sounds_tracked,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "estimated_duration": self.estimated_duration,
            "error_count": self.error_count,
            "last_error": self.last_error,
            "retry_count": self.retry_count,
            "max_retries": self.max_retries,
            "data_quality_score": self.data_quality_score,
            "validation_errors": self.validation_errors,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None
        }


class TikTokAnalytics(Base):
    """Aggregated analytics for TikTok trends"""
    __tablename__ = "tiktok_analytics"

    id = Column(Integer, primary_key=True, index=True)
    
    # Time period
    date = Column(DateTime, nullable=False, index=True)
    period_type = Column(String(20), default="daily", index=True)  # hourly, daily, weekly
    
    # Trend analytics
    total_trends = Column(Integer, default=0)
    emerging_trends = Column(Integer, default=0)
    declining_trends = Column(Integer, default=0)
    peak_trends = Column(Integer, default=0)
    
    # Content analytics
    total_videos_analyzed = Column(BigInteger, default=0)
    avg_engagement_rate = Column(Float, default=0.0)
    top_content_categories = Column(JSON, default=list)
    
    # Hashtag analytics
    total_hashtags = Column(Integer, default=0)
    trending_hashtags = Column(Integer, default=0)
    top_hashtags = Column(JSON, default=list)
    
    # Sound analytics
    total_sounds = Column(Integer, default=0)
    trending_sounds = Column(Integer, default=0)
    top_sounds = Column(JSON, default=list)
    
    # Performance metrics
    avg_viral_score = Column(Float, default=0.0)
    detection_accuracy = Column(Float, default=0.0)
    processing_time = Column(Float, default=0.0)  # Average processing time in seconds
    
    # Geographic insights
    top_regions = Column(JSON, default=list)
    regional_trends = Column(JSON, default=dict)
    
    # Audit fields
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Indexes
    __table_args__ = (
        Index('idx_tiktok_analytics_date_period', 'date', 'period_type'),
        UniqueConstraint('date', 'period_type', name='uq_tiktok_analytics_date_period'),
    )

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for API responses"""
        return {
            "id": self.id,
            "date": self.date.isoformat() if self.date else None,
            "period_type": self.period_type,
            "total_trends": self.total_trends,
            "emerging_trends": self.emerging_trends,
            "declining_trends": self.declining_trends,
            "peak_trends": self.peak_trends,
            "total_videos_analyzed": self.total_videos_analyzed,
            "avg_engagement_rate": self.avg_engagement_rate,
            "top_content_categories": self.top_content_categories,
            "total_hashtags": self.total_hashtags,
            "trending_hashtags": self.trending_hashtags,
            "top_hashtags": self.top_hashtags,
            "total_sounds": self.total_sounds,
            "trending_sounds": self.trending_sounds,
            "top_sounds": self.top_sounds,
            "avg_viral_score": self.avg_viral_score,
            "detection_accuracy": self.detection_accuracy,
            "processing_time": self.processing_time,
            "top_regions": self.top_regions,
            "regional_trends": self.regional_trends,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None
        }