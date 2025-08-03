from sqlalchemy import Column, Integer, String, Float, Text, DateTime, Boolean, ForeignKey, JSON, Enum
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import enum
from app.db.session import Base

class PlatformType(str, enum.Enum):
    TIKTOK = "tiktok"
    INSTAGRAM = "instagram"
    YOUTUBE = "youtube"
    FACEBOOK = "facebook"

class PerformanceCategory(str, enum.Enum):
    HOOK = "hook"
    CONTENT = "content"
    CTA = "cta"
    OVERALL = "overall"

class ExperimentStatus(str, enum.Enum):
    DRAFT = "draft"
    RUNNING = "running"
    COMPLETED = "completed"
    PAUSED = "paused"
    CANCELLED = "cancelled"

class VideoPerformancePrediction(Base):
    """Store predictive performance scores for videos"""
    __tablename__ = "video_performance_predictions"
    
    id = Column(Integer, primary_key=True, index=True)
    video_id = Column(Integer, ForeignKey("videos.id"), nullable=False)
    platform = Column(Enum(PlatformType), nullable=False)
    
    # Overall scores
    overall_score = Column(Float, nullable=False)  # 1-100
    confidence_interval = Column(Float, nullable=False)  # 0-1
    predicted_views = Column(Integer, nullable=True)
    predicted_engagement_rate = Column(Float, nullable=True)
    
    # Category breakdowns
    hook_score = Column(Float, nullable=False)
    content_score = Column(Float, nullable=False)
    cta_score = Column(Float, nullable=False)
    
    # Visual analysis metrics
    visual_analysis = Column(JSON, nullable=True)  # Detailed CV analysis
    audio_analysis = Column(JSON, nullable=True)   # Audio features
    
    # Recommendations
    recommendations = Column(JSON, nullable=True)  # Actionable suggestions
    
    # Metadata
    model_version = Column(String(50), nullable=False)
    processing_time = Column(Float, nullable=True)  # seconds
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    video = relationship("Video", back_populates="performance_predictions")

class TrendRecommendation(Base):
    """Store trending content and audio recommendations"""
    __tablename__ = "trend_recommendations"
    
    id = Column(Integer, primary_key=True, index=True)
    brand_id = Column(Integer, ForeignKey("brands.id"), nullable=False)
    platform = Column(Enum(PlatformType), nullable=False)
    
    # Trend data
    trend_type = Column(String(50), nullable=False)  # audio, hashtag, format, effect
    trend_id = Column(String(255), nullable=False)   # External trend identifier
    trend_name = Column(String(500), nullable=False)
    trend_description = Column(Text, nullable=True)
    
    # Performance metrics
    trend_volume = Column(Integer, nullable=False)   # Number of uses
    growth_rate = Column(Float, nullable=False)      # Daily growth %
    virality_score = Column(Float, nullable=False)   # 1-100
    relevance_score = Column(Float, nullable=False)  # Brand relevance 1-100
    
    # Audio specific
    audio_url = Column(String(1000), nullable=True)
    audio_duration = Column(Float, nullable=True)
    audio_mood = Column(String(100), nullable=True)
    audio_bpm = Column(Integer, nullable=True)
    copyright_status = Column(String(50), nullable=True)
    
    # Timing and engagement
    peak_usage_time = Column(DateTime(timezone=True), nullable=True)
    estimated_decay_date = Column(DateTime(timezone=True), nullable=True)
    recommended_usage_window = Column(JSON, nullable=True)
    
    # Metadata
    discovered_at = Column(DateTime(timezone=True), server_default=func.now())
    last_updated = Column(DateTime(timezone=True), onupdate=func.now())
    is_active = Column(Boolean, default=True)
    
    # Relationships
    brand = relationship("Brand", back_populates="trend_recommendations")

class ABTestExperiment(Base):
    """Manage A/B testing experiments"""
    __tablename__ = "ab_test_experiments"
    
    id = Column(Integer, primary_key=True, index=True)
    campaign_id = Column(Integer, ForeignKey("campaigns.id"), nullable=False)
    brand_id = Column(Integer, ForeignKey("brands.id"), nullable=False)
    
    # Experiment details
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    hypothesis = Column(Text, nullable=False)
    status = Column(Enum(ExperimentStatus), default=ExperimentStatus.DRAFT)
    
    # Test configuration
    traffic_split = Column(JSON, nullable=False)  # {"control": 50, "variant_1": 25, "variant_2": 25}
    success_metrics = Column(JSON, nullable=False)  # ["ctr", "conversion_rate", "engagement"]
    minimum_sample_size = Column(Integer, nullable=False)
    confidence_level = Column(Float, default=0.95)
    statistical_power = Column(Float, default=0.8)
    
    # Timing
    start_date = Column(DateTime(timezone=True), nullable=True)
    end_date = Column(DateTime(timezone=True), nullable=True)
    planned_duration_days = Column(Integer, nullable=False)
    
    # Results
    current_sample_size = Column(Integer, default=0)
    statistical_significance = Column(Float, nullable=True)
    winner_variant = Column(String(100), nullable=True)
    confidence_interval = Column(JSON, nullable=True)
    results_summary = Column(JSON, nullable=True)
    
    # Metadata
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    campaign = relationship("Campaign", back_populates="ab_experiments")
    brand = relationship("Brand", back_populates="ab_experiments")
    variants = relationship("ABTestVariant", back_populates="experiment", cascade="all, delete-orphan")

class ABTestVariant(Base):
    """Individual variants in A/B tests"""
    __tablename__ = "ab_test_variants"
    
    id = Column(Integer, primary_key=True, index=True)
    experiment_id = Column(Integer, ForeignKey("ab_test_experiments.id"), nullable=False)
    video_id = Column(Integer, ForeignKey("videos.id"), nullable=False)
    
    # Variant details
    variant_name = Column(String(100), nullable=False)  # control, variant_1, etc.
    variant_type = Column(String(50), nullable=False)   # hook, cta, audio, etc.
    description = Column(Text, nullable=True)
    
    # Changes made
    modifications = Column(JSON, nullable=False)  # Detailed change log
    generation_prompt = Column(Text, nullable=True)
    
    # Performance tracking
    impressions = Column(Integer, default=0)
    clicks = Column(Integer, default=0)
    conversions = Column(Integer, default=0)
    engagement_rate = Column(Float, default=0.0)
    cost_per_result = Column(Float, nullable=True)
    
    # Statistical metrics
    conversion_rate = Column(Float, default=0.0)
    confidence_interval_lower = Column(Float, nullable=True)
    confidence_interval_upper = Column(Float, nullable=True)
    
    # Metadata
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    is_active = Column(Boolean, default=True)
    
    # Relationships
    experiment = relationship("ABTestExperiment", back_populates="variants")
    video = relationship("Video", back_populates="ab_variants")

class VideoAnalytics(Base):
    """Detailed analytics for video performance"""
    __tablename__ = "video_analytics"
    
    id = Column(Integer, primary_key=True, index=True)
    video_id = Column(Integer, ForeignKey("videos.id"), nullable=False)
    platform = Column(Enum(PlatformType), nullable=False)
    
    # Performance metrics
    views = Column(Integer, default=0)
    likes = Column(Integer, default=0)
    shares = Column(Integer, default=0)
    comments = Column(Integer, default=0)
    saves = Column(Integer, default=0)
    
    # Engagement metrics
    avg_watch_time = Column(Float, nullable=True)  # seconds
    completion_rate = Column(Float, nullable=True)  # 0-1
    engagement_rate = Column(Float, nullable=True)  # 0-1
    click_through_rate = Column(Float, nullable=True)  # 0-1
    
    # Audience insights
    audience_demographics = Column(JSON, nullable=True)
    geographic_data = Column(JSON, nullable=True)
    device_breakdown = Column(JSON, nullable=True)
    traffic_sources = Column(JSON, nullable=True)
    
    # Time-based metrics
    hourly_performance = Column(JSON, nullable=True)
    daily_performance = Column(JSON, nullable=True)
    
    # Metadata
    recorded_at = Column(DateTime(timezone=True), server_default=func.now())
    data_source = Column(String(100), nullable=False)  # api, scraping, manual
    
    # Relationships
    video = relationship("Video", back_populates="analytics")

class ModelPerformanceMetrics(Base):
    """Track ML model performance over time"""
    __tablename__ = "model_performance_metrics"
    
    id = Column(Integer, primary_key=True, index=True)
    model_name = Column(String(100), nullable=False)
    model_version = Column(String(50), nullable=False)
    
    # Performance metrics
    accuracy = Column(Float, nullable=False)
    precision = Column(Float, nullable=False)
    recall = Column(Float, nullable=False)
    f1_score = Column(Float, nullable=False)
    mae = Column(Float, nullable=True)  # Mean Absolute Error
    rmse = Column(Float, nullable=True)  # Root Mean Square Error
    
    # Test dataset info
    test_size = Column(Integer, nullable=False)
    test_period_start = Column(DateTime(timezone=True), nullable=False)
    test_period_end = Column(DateTime(timezone=True), nullable=False)
    
    # Model details
    feature_importance = Column(JSON, nullable=True)
    hyperparameters = Column(JSON, nullable=True)
    training_duration = Column(Float, nullable=True)  # minutes
    
    # Metadata
    evaluated_at = Column(DateTime(timezone=True), server_default=func.now())
    notes = Column(Text, nullable=True)