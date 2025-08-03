from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, JSON, Text
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.db.session import Base

class Brand(Base):
    __tablename__ = "brands"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    name = Column(String, nullable=False)
    url = Column(String, nullable=False)
    logo_url = Column(String)
    colors = Column(JSON)  # {"primary": "#FFFFFF", "secondary": "#000000"}
    voice = Column(JSON)   # {"tone": "Witty", "dos": "...", "donts": "..."}
    pillars = Column(JSON) # ["Education", "Testimonials"]
    
    # Extended fields for competitor analysis and product management
    industry = Column(String, index=True)
    target_audience = Column(JSON)
    unique_value_proposition = Column(Text)
    
    # Competitor data
    competitors = Column(JSON)  # [{"name": "Competitor", "url": "...", "similarity": 0.8}]
    market_position = Column(JSON)  # {"segment": "premium", "share": 15.2}
    
    # Product catalog summary
    product_count = Column(Integer, default=0)
    avg_price_range = Column(JSON)  # {"min": 10, "max": 100, "avg": 45}
    main_categories = Column(JSON)  # ["Electronics", "Accessories"]
    
    # Scraping configuration
    scraping_config = Column(JSON)  # Platform-specific scraping settings
    last_full_scrape = Column(DateTime(timezone=True))
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    user = relationship("User")
    campaigns = relationship("Campaign", back_populates="brand")
    assets = relationship("Asset", back_populates="brand")
    products = relationship("Product", back_populates="brand")
    scraping_jobs = relationship("ScrapingJob", back_populates="brand")
    trend_recommendations = relationship("TrendRecommendation", back_populates="brand")
    ab_experiments = relationship("ABTestExperiment", back_populates="brand")

class Asset(Base):
    __tablename__ = "assets"

    id = Column(Integer, primary_key=True, index=True)
    brand_id = Column(Integer, ForeignKey("brands.id"), nullable=False)
    asset_type = Column(String, nullable=False)  # logo, product, video, etc.
    name = Column(String, nullable=False)
    url = Column(String, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    brand = relationship("Brand", back_populates="assets")