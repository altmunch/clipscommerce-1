from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Text, Float, JSON
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.db.session import Base

class Idea(Base):
    __tablename__ = "ideas"

    id = Column(Integer, primary_key=True, index=True)
    brand_id = Column(Integer, ForeignKey("brands.id"), nullable=False)
    campaign_id = Column(Integer, ForeignKey("campaigns.id"), nullable=True)
    hook = Column(String, nullable=False)
    viral_score = Column(Float)
    status = Column(String, default="pending")  # pending, approved, rejected
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    brand = relationship("Brand")
    campaign = relationship("Campaign", back_populates="ideas")
    blueprints = relationship("Blueprint", back_populates="idea")

class Blueprint(Base):
    __tablename__ = "blueprints"

    id = Column(Integer, primary_key=True, index=True)
    idea_id = Column(Integer, ForeignKey("ideas.id"), nullable=False)
    script = Column(Text)
    shot_list = Column(JSON)
    status = Column(String, default="pending")  # pending, script_ready, complete
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    idea = relationship("Idea", back_populates="blueprints")
    videos = relationship("Video", back_populates="blueprint")

class Video(Base):
    __tablename__ = "videos"

    id = Column(Integer, primary_key=True, index=True)
    blueprint_id = Column(Integer, ForeignKey("blueprints.id"), nullable=False)
    video_url = Column(String)
    thumbnail_url = Column(String)
    caption = Column(Text)
    hashtags = Column(JSON)
    cta = Column(String)
    status = Column(String, default="draft")  # draft, optimized, scheduled, published
    scheduled_at = Column(DateTime)
    platforms = Column(JSON)  # ["tiktok", "instagram"]
    
    # Performance metrics
    views = Column(Integer, default=0)
    clicks = Column(Integer, default=0)
    revenue = Column(Float, default=0.0)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    blueprint = relationship("Blueprint", back_populates="videos")
    performance_predictions = relationship("VideoPerformancePrediction", back_populates="video")
    ab_variants = relationship("ABTestVariant", back_populates="video")
    analytics = relationship("VideoAnalytics", back_populates="video")