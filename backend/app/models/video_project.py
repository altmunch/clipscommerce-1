"""
Database models for video generation projects
"""

import uuid
from datetime import datetime
from typing import Dict, List, Optional, Any
from sqlalchemy import Column, String, Text, Float, Integer, DateTime, Boolean, JSON, ForeignKey, Enum as SQLEnum
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import UUID, JSONB
import enum

from app.db.session import Base


class VideoProviderEnum(enum.Enum):
    """Video generation providers"""
    RUNWAYML = "runwayml"
    DID = "did"
    HEYGEN = "heygen"
    SYNTHESIA = "synthesia"
    REPLICATE = "replicate"
    INVIDEO = "invideo"
    STABLE_VIDEO = "stable_video"


class VideoQualityEnum(enum.Enum):
    """Video quality options"""
    LOW = "480p"
    MEDIUM = "720p"
    HIGH = "1080p"
    ULTRA = "4k"


class VideoStyleEnum(enum.Enum):
    """Video generation styles"""
    REALISTIC = "realistic"
    ANIMATED = "animated"
    CARTOON = "cartoon"
    CINEMATIC = "cinematic"
    PROFESSIONAL = "professional"
    CASUAL = "casual"
    TESTIMONIAL = "testimonial"


class GenerationStatusEnum(enum.Enum):
    """Video generation status"""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class VideoProjectTypeEnum(enum.Enum):
    """Types of video projects"""
    PRODUCT_AD = "product_ad"
    UGC_TESTIMONIAL = "ugc_testimonial"
    BRAND_STORY = "brand_story"
    TUTORIAL = "tutorial"
    SOCIAL_POST = "social_post"


class VideoProject(Base):
    """Main video generation project"""
    __tablename__ = "video_projects"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    title = Column(String(255), nullable=False)
    description = Column(Text)
    project_type = Column(SQLEnum(VideoProjectTypeEnum), nullable=False)
    
    # Associated entities
    brand_id = Column(UUID(as_uuid=True), ForeignKey("brands.id"), nullable=True)
    product_id = Column(UUID(as_uuid=True), ForeignKey("products.id"), nullable=True)
    campaign_id = Column(UUID(as_uuid=True), ForeignKey("campaigns.id"), nullable=True)
    
    # Project configuration
    target_platform = Column(String(50))  # tiktok, instagram, youtube_shorts
    target_duration = Column(Float)  # Duration in seconds
    aspect_ratio = Column(String(20), default="9:16")  # For vertical videos
    quality = Column(SQLEnum(VideoQualityEnum), default=VideoQualityEnum.MEDIUM)
    style = Column(SQLEnum(VideoStyleEnum), default=VideoStyleEnum.PROFESSIONAL)
    
    # Generation settings
    preferred_provider = Column(SQLEnum(VideoProviderEnum))
    voice_id = Column(String(100))  # ElevenLabs voice ID
    language = Column(String(10), default="en")
    
    # Status and progress
    status = Column(SQLEnum(GenerationStatusEnum), default=GenerationStatusEnum.PENDING)
    progress_percentage = Column(Float, default=0.0)
    
    # Costs and timing
    estimated_cost = Column(Float, default=0.0)
    actual_cost = Column(Float, default=0.0)
    estimated_completion_time = Column(DateTime)
    generation_started_at = Column(DateTime)
    generation_completed_at = Column(DateTime)
    
    # Results
    final_video_url = Column(String(500))
    preview_video_url = Column(String(500))
    thumbnail_url = Column(String(500))
    
    # Brand guidelines and customization
    brand_guidelines = Column(JSONB)  # Colors, fonts, logo, etc.
    
    # Metadata and configuration
    generation_config = Column(JSONB)  # AI generation parameters
    editing_timeline = Column(JSONB)  # Video editing instructions
    metrics = Column(JSONB)  # Performance metrics after generation
    
    # Audit fields
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    created_by = Column(UUID(as_uuid=True))  # User who created the project
    
    # Relationships
    video_segments = relationship("VideoSegment", back_populates="project", cascade="all, delete-orphan")
    broll_clips = relationship("BRollClip", back_populates="project", cascade="all, delete-orphan")
    assets = relationship("VideoAsset", back_populates="project", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<VideoProject(id={self.id}, title='{self.title}', status='{self.status}')>"


class VideoSegment(Base):
    """Individual video segment within a project"""
    __tablename__ = "video_segments"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    project_id = Column(UUID(as_uuid=True), ForeignKey("video_projects.id"), nullable=False)
    
    # Segment metadata
    segment_number = Column(Integer, nullable=False)  # Order within project
    title = Column(String(255))
    
    # Timing
    start_time = Column(Float, nullable=False)  # Start time in seconds
    end_time = Column(Float, nullable=False)    # End time in seconds
    duration = Column(Float, nullable=False)    # Duration in seconds
    
    # Generation parameters
    prompt = Column(Text, nullable=False)
    enhanced_prompt = Column(Text)  # AI-enhanced version
    style = Column(SQLEnum(VideoStyleEnum))
    quality = Column(SQLEnum(VideoQualityEnum))
    provider = Column(SQLEnum(VideoProviderEnum))
    
    # Provider-specific data
    provider_job_id = Column(String(200))  # External provider's job ID
    provider_response = Column(JSONB)      # Full provider response
    
    # Status and results
    status = Column(SQLEnum(GenerationStatusEnum), default=GenerationStatusEnum.PENDING)
    video_url = Column(String(500))
    preview_url = Column(String(500))
    thumbnail_url = Column(String(500))
    
    # Generation metadata
    generation_time = Column(Float)  # Time taken to generate in seconds
    cost = Column(Float, default=0.0)
    retry_count = Column(Integer, default=0)
    error_message = Column(Text)
    
    # Audio/speech
    has_speech = Column(Boolean, default=False)
    speech_text = Column(Text)
    speech_url = Column(String(500))
    
    # Technical metadata
    resolution = Column(String(20))  # e.g., "1920x1080"
    fps = Column(Integer)
    file_size = Column(Integer)      # File size in bytes
    format = Column(String(10))      # Video format (mp4, mov, etc.)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    generated_at = Column(DateTime)
    
    # Relationships
    project = relationship("VideoProject", back_populates="video_segments")
    
    def __repr__(self):
        return f"<VideoSegment(id={self.id}, segment_number={self.segment_number}, status='{self.status}')>"


class BRollClip(Base):
    """B-roll video clips for projects"""
    __tablename__ = "broll_clips"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    project_id = Column(UUID(as_uuid=True), ForeignKey("video_projects.id"), nullable=False)
    
    # Clip metadata
    title = Column(String(255))
    description = Column(Text)
    duration = Column(Float, nullable=False)
    tags = Column(JSONB)  # Array of tags
    
    # Source information
    source = Column(String(50))  # "generated", "stock", "uploaded", "extracted"
    source_provider = Column(String(50))  # "pexels", "unsplash", "user_upload"
    source_id = Column(String(200))  # ID from the source provider
    license_type = Column(String(50))  # "royalty_free", "licensed", "custom"
    
    # URLs and files
    video_url = Column(String(500), nullable=False)
    thumbnail_url = Column(String(500))
    local_path = Column(String(500))
    
    # Usage in project
    used_in_timeline = Column(Boolean, default=False)
    timeline_start_time = Column(Float)
    timeline_end_time = Column(Float)
    overlay_position = Column(String(50))  # "bottom_right", "top_left", etc.
    opacity = Column(Float, default=1.0)
    
    # Technical specs
    resolution = Column(String(20))
    fps = Column(Integer)
    file_size = Column(Integer)
    format = Column(String(10))
    
    # Cost and licensing
    cost = Column(Float, default=0.0)
    license_expires_at = Column(DateTime)
    attribution_required = Column(Boolean, default=False)
    attribution_text = Column(Text)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    project = relationship("VideoProject", back_populates="broll_clips")
    
    def __repr__(self):
        return f"<BRollClip(id={self.id}, title='{self.title}', source='{self.source}')>"


class VideoAsset(Base):
    """Assets used in video generation (images, logos, fonts, etc.)"""
    __tablename__ = "video_assets"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    project_id = Column(UUID(as_uuid=True), ForeignKey("video_projects.id"), nullable=False)
    
    # Asset metadata
    name = Column(String(255), nullable=False)
    description = Column(Text)
    asset_type = Column(String(50))  # "logo", "background", "overlay", "font", "image", "audio"
    category = Column(String(50))    # "brand", "product", "decoration", "effect"
    
    # File information
    file_url = Column(String(500), nullable=False)
    local_path = Column(String(500))
    file_size = Column(Integer)
    mime_type = Column(String(100))
    
    # Usage in project
    usage_context = Column(String(100))  # "background", "overlay", "watermark", "intro", "outro"
    position = Column(String(50))         # "center", "top_left", etc.
    scale = Column(Float, default=1.0)
    opacity = Column(Float, default=1.0)
    start_time = Column(Float)           # When to show in video
    end_time = Column(Float)             # When to hide in video
    
    # Processing settings
    processed = Column(Boolean, default=False)
    processed_url = Column(String(500))
    processing_settings = Column(JSONB)  # Crop, resize, filters, etc.
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    project = relationship("VideoProject", back_populates="assets")
    
    def __repr__(self):
        return f"<VideoAsset(id={self.id}, name='{self.name}', type='{self.asset_type}')>"


class UGCTestimonial(Base):
    """User-generated content testimonials with AI avatars"""
    __tablename__ = "ugc_testimonials"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    project_id = Column(UUID(as_uuid=True), ForeignKey("video_projects.id"), nullable=False)
    
    # Source review/testimonial
    original_review_text = Column(Text, nullable=False)
    review_source = Column(String(100))  # "amazon", "google", "manual", etc.
    review_rating = Column(Float)
    review_author = Column(String(200))
    
    # Avatar configuration
    avatar_provider = Column(String(50))  # "did", "heygen", "synthesia"
    avatar_id = Column(String(200))       # Provider's avatar ID
    avatar_gender = Column(String(20))
    avatar_ethnicity = Column(String(50))
    avatar_age_range = Column(String(20)) # "20-30", "30-40", etc.
    
    # Generated script
    generated_script = Column(Text)
    script_emotion = Column(String(50))   # "enthusiastic", "calm", "excited"
    script_language = Column(String(10), default="en")
    
    # Voice settings
    voice_provider = Column(String(50))   # "elevenlabs", "built_in"
    voice_id = Column(String(200))
    voice_settings = Column(JSONB)        # Speed, pitch, emotion settings
    
    # Generation results
    status = Column(SQLEnum(GenerationStatusEnum), default=GenerationStatusEnum.PENDING)
    video_url = Column(String(500))
    audio_url = Column(String(500))
    duration = Column(Float)
    
    # Cost and metadata
    generation_cost = Column(Float, default=0.0)
    generation_time = Column(Float)
    provider_job_id = Column(String(200))
    error_message = Column(Text)
    
    # Usage tracking
    used_in_campaigns = Column(JSONB)     # Track which campaigns use this testimonial
    performance_metrics = Column(JSONB)   # Engagement metrics if available
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    generated_at = Column(DateTime)
    
    def __repr__(self):
        return f"<UGCTestimonial(id={self.id}, avatar_provider='{self.avatar_provider}', status='{self.status}')>"


class VideoGenerationJob(Base):
    """Track long-running video generation jobs"""
    __tablename__ = "video_generation_jobs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    project_id = Column(UUID(as_uuid=True), ForeignKey("video_projects.id"), nullable=False)
    
    # Job metadata
    job_type = Column(String(50))  # "full_project", "single_segment", "ugc_testimonial"
    celery_task_id = Column(String(200))  # Celery task ID for tracking
    
    # Job parameters
    job_config = Column(JSONB)     # Parameters passed to the job
    priority = Column(Integer, default=0)  # Job priority
    
    # Status and progress
    status = Column(SQLEnum(GenerationStatusEnum), default=GenerationStatusEnum.PENDING)
    progress_percentage = Column(Float, default=0.0)
    current_step = Column(String(200))
    
    # Results and errors
    result = Column(JSONB)         # Job result data
    error_message = Column(Text)
    retry_count = Column(Integer, default=0)
    max_retries = Column(Integer, default=3)
    
    # Timing
    started_at = Column(DateTime)
    completed_at = Column(DateTime)
    estimated_completion = Column(DateTime)
    
    # Resource usage
    processing_time = Column(Float)  # Total processing time in seconds
    cost = Column(Float, default=0.0)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def __repr__(self):
        return f"<VideoGenerationJob(id={self.id}, job_type='{self.job_type}', status='{self.status}')>"