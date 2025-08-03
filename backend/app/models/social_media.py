from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, JSON, Text, Boolean, Float, Enum
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.db.session import Base
import enum


class PlatformType(enum.Enum):
    TIKTOK = "tiktok"
    INSTAGRAM = "instagram"
    FACEBOOK = "facebook"


class AccountStatus(enum.Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"
    SUSPENDED = "suspended"
    PENDING_VERIFICATION = "pending_verification"
    ERROR = "error"


class PostStatus(enum.Enum):
    DRAFT = "draft"
    SCHEDULED = "scheduled"
    PUBLISHING = "publishing"
    PUBLISHED = "published"
    FAILED = "failed"
    DELETED = "deleted"


class ContentType(enum.Enum):
    VIDEO = "video"
    IMAGE = "image"
    REEL = "reel"
    STORY = "story"
    CAROUSEL = "carousel"


class SocialMediaAccount(Base):
    """Social media accounts connected to brands for automated posting"""
    __tablename__ = "social_media_accounts"

    id = Column(Integer, primary_key=True, index=True)
    brand_id = Column(Integer, ForeignKey("brands.id"), nullable=False)
    platform = Column(Enum(PlatformType), nullable=False)
    username = Column(String, nullable=False)
    display_name = Column(String)
    profile_picture_url = Column(String)
    
    # Platform-specific IDs
    platform_account_id = Column(String, nullable=False, unique=True)
    business_account_id = Column(String)  # For Instagram Business accounts
    
    # Authentication tokens (encrypted)
    access_token = Column(Text)
    refresh_token = Column(Text)
    token_expires_at = Column(DateTime(timezone=True))
    
    # Account status and metadata
    status = Column(Enum(AccountStatus), default=AccountStatus.ACTIVE)
    is_business_account = Column(Boolean, default=False)
    is_verified = Column(Boolean, default=False)
    follower_count = Column(Integer, default=0)
    following_count = Column(Integer, default=0)
    
    # Platform-specific settings
    posting_settings = Column(JSON)  # Platform-specific posting preferences
    analytics_settings = Column(JSON)  # Analytics configuration
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    last_sync_at = Column(DateTime(timezone=True))
    
    # Relationships
    brand = relationship("Brand")
    posts = relationship("SocialMediaPost", back_populates="account")
    analytics = relationship("SocialMediaAnalytics", back_populates="account")
    posting_schedule = relationship("PostingSchedule", back_populates="account")


class SocialMediaPost(Base):
    """Posts published or scheduled across social media platforms"""
    __tablename__ = "social_media_posts"

    id = Column(Integer, primary_key=True, index=True)
    account_id = Column(Integer, ForeignKey("social_media_accounts.id"), nullable=False)
    video_project_id = Column(Integer, ForeignKey("video_projects.id"))
    campaign_id = Column(Integer, ForeignKey("campaigns.id"))
    
    # Post identification
    platform_post_id = Column(String)  # Platform's unique ID for the post
    post_url = Column(String)
    
    # Content details
    content_type = Column(Enum(ContentType), nullable=False)
    caption = Column(Text)
    hashtags = Column(JSON)  # List of hashtags
    mentions = Column(JSON)  # List of mentioned accounts
    location_tag = Column(String)
    
    # Media content
    media_urls = Column(JSON)  # List of media file URLs
    thumbnail_url = Column(String)
    duration = Column(Integer)  # For videos, in seconds
    
    # Publishing details
    status = Column(Enum(PostStatus), default=PostStatus.DRAFT)
    scheduled_at = Column(DateTime(timezone=True))
    published_at = Column(DateTime(timezone=True))
    
    # Platform-specific settings
    privacy_settings = Column(JSON)
    audience_targeting = Column(JSON)
    post_settings = Column(JSON)  # Platform-specific post configuration
    
    # Performance metrics (updated via webhooks/API)
    view_count = Column(Integer, default=0)
    like_count = Column(Integer, default=0)
    comment_count = Column(Integer, default=0)
    share_count = Column(Integer, default=0)
    save_count = Column(Integer, default=0)
    
    # Analytics metadata
    engagement_rate = Column(Float, default=0.0)
    reach = Column(Integer, default=0)
    impressions = Column(Integer, default=0)
    
    # Error handling
    error_message = Column(Text)
    retry_count = Column(Integer, default=0)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    account = relationship("SocialMediaAccount", back_populates="posts")
    video_project = relationship("VideoProject")
    campaign = relationship("Campaign")
    analytics = relationship("SocialMediaAnalytics", back_populates="post")


class SocialMediaAnalytics(Base):
    """Detailed analytics and insights for social media posts and accounts"""
    __tablename__ = "social_media_analytics"

    id = Column(Integer, primary_key=True, index=True)
    account_id = Column(Integer, ForeignKey("social_media_accounts.id"), nullable=False)
    post_id = Column(Integer, ForeignKey("social_media_posts.id"))
    
    # Time period for analytics
    date = Column(DateTime(timezone=True), nullable=False)
    period_type = Column(String, default="daily")  # daily, weekly, monthly
    
    # Engagement metrics
    views = Column(Integer, default=0)
    likes = Column(Integer, default=0)
    comments = Column(Integer, default=0)
    shares = Column(Integer, default=0)
    saves = Column(Integer, default=0)
    
    # Reach and impressions
    reach = Column(Integer, default=0)
    impressions = Column(Integer, default=0)
    unique_viewers = Column(Integer, default=0)
    
    # Engagement rates
    engagement_rate = Column(Float, default=0.0)
    like_rate = Column(Float, default=0.0)
    comment_rate = Column(Float, default=0.0)
    share_rate = Column(Float, default=0.0)
    
    # Audience insights
    audience_demographics = Column(JSON)  # Age, gender, location breakdown
    audience_interests = Column(JSON)  # Interest categories
    top_territories = Column(JSON)  # Geographic performance
    
    # Performance metrics
    watch_time_total = Column(Integer, default=0)  # Total watch time in seconds
    average_watch_time = Column(Float, default=0.0)  # Average watch time percentage
    completion_rate = Column(Float, default=0.0)  # Video completion rate
    
    # Traffic and conversion
    profile_visits = Column(Integer, default=0)
    website_clicks = Column(Integer, default=0)
    follows_gained = Column(Integer, default=0)
    
    # Platform-specific metrics
    platform_metrics = Column(JSON)  # Additional platform-specific data
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    account = relationship("SocialMediaAccount", back_populates="analytics")
    post = relationship("SocialMediaPost", back_populates="analytics")


class PostingSchedule(Base):
    """Automated posting schedules for social media accounts"""
    __tablename__ = "posting_schedules"

    id = Column(Integer, primary_key=True, index=True)
    account_id = Column(Integer, ForeignKey("social_media_accounts.id"), nullable=False)
    brand_id = Column(Integer, ForeignKey("brands.id"), nullable=False)
    
    # Schedule configuration
    name = Column(String, nullable=False)
    description = Column(Text)
    is_active = Column(Boolean, default=True)
    
    # Timing settings
    timezone = Column(String, default="UTC")
    posting_times = Column(JSON)  # List of optimal posting times
    posting_frequency = Column(JSON)  # Frequency configuration
    
    # Content settings
    content_types = Column(JSON)  # Allowed content types for this schedule
    hashtag_strategy = Column(JSON)  # Hashtag generation rules
    caption_templates = Column(JSON)  # Caption templates
    
    # Optimization settings
    auto_optimize_timing = Column(Boolean, default=True)
    auto_optimize_hashtags = Column(Boolean, default=True)
    auto_optimize_captions = Column(Boolean, default=False)
    
    # Performance tracking
    posts_scheduled = Column(Integer, default=0)
    posts_published = Column(Integer, default=0)
    average_engagement = Column(Float, default=0.0)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    last_posting_at = Column(DateTime(timezone=True))
    
    # Relationships
    account = relationship("SocialMediaAccount", back_populates="posting_schedule")
    brand = relationship("Brand")


class SocialMediaWebhook(Base):
    """Webhook events from social media platforms for real-time updates"""
    __tablename__ = "social_media_webhooks"

    id = Column(Integer, primary_key=True, index=True)
    account_id = Column(Integer, ForeignKey("social_media_accounts.id"))
    post_id = Column(Integer, ForeignKey("social_media_posts.id"))
    
    # Webhook details
    platform = Column(Enum(PlatformType), nullable=False)
    event_type = Column(String, nullable=False)  # post_published, engagement_update, etc.
    webhook_id = Column(String)  # Platform's webhook ID
    
    # Event data
    event_data = Column(JSON, nullable=False)  # Raw webhook payload
    processed = Column(Boolean, default=False)
    processing_error = Column(Text)
    
    # Timestamps
    received_at = Column(DateTime(timezone=True), server_default=func.now())
    processed_at = Column(DateTime(timezone=True))
    
    # Relationships
    account = relationship("SocialMediaAccount")
    post = relationship("SocialMediaPost")


class CrossPlatformCampaign(Base):
    """Campaigns that span multiple social media platforms"""
    __tablename__ = "cross_platform_campaigns"

    id = Column(Integer, primary_key=True, index=True)
    brand_id = Column(Integer, ForeignKey("brands.id"), nullable=False)
    campaign_id = Column(Integer, ForeignKey("campaigns.id"))
    
    # Campaign details
    name = Column(String, nullable=False)
    description = Column(Text)
    status = Column(String, default="active")  # active, paused, completed
    
    # Platform configuration
    platforms = Column(JSON, nullable=False)  # List of platforms to post to
    platform_settings = Column(JSON)  # Platform-specific settings
    
    # Content strategy
    content_strategy = Column(JSON)  # Content adaptation rules per platform
    hashtag_strategy = Column(JSON)  # Hashtag strategy per platform
    posting_strategy = Column(JSON)  # Timing and frequency per platform
    
    # Performance tracking
    total_posts = Column(Integer, default=0)
    total_engagement = Column(Integer, default=0)
    total_reach = Column(Integer, default=0)
    
    # Budget and ROI
    budget = Column(Float, default=0.0)
    spent = Column(Float, default=0.0)
    revenue_attributed = Column(Float, default=0.0)
    roi = Column(Float, default=0.0)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    start_date = Column(DateTime(timezone=True))
    end_date = Column(DateTime(timezone=True))
    
    # Relationships
    brand = relationship("Brand")
    campaign = relationship("Campaign")