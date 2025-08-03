"""
Product and competitor data models for scraped e-commerce data.
"""

from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, JSON, Text, Float, Boolean, Index
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.db.session import Base


class Product(Base):
    """Product information scraped from e-commerce sites"""
    __tablename__ = "products"

    id = Column(Integer, primary_key=True, index=True)
    brand_id = Column(Integer, ForeignKey("brands.id"), nullable=False)
    
    # Basic product information
    name = Column(String, nullable=False)
    description = Column(Text)
    short_description = Column(Text)
    sku = Column(String, index=True)
    brand_name = Column(String, index=True)
    category = Column(String, index=True)
    
    # Pricing information
    price = Column(Float)
    original_price = Column(Float)
    currency = Column(String(3), default="USD")
    sale_price = Column(Float)
    discount_percentage = Column(Float)
    price_range = Column(JSON)  # {"min": 10.99, "max": 99.99}
    
    # Product status
    availability = Column(String, index=True)  # in_stock, out_of_stock, pre_order, etc.
    is_active = Column(Boolean, default=True)
    
    # Source information
    source_url = Column(String, nullable=False, index=True)
    source_domain = Column(String, index=True)
    platform_type = Column(String, index=True)  # shopify, woocommerce, etc.
    
    # Product data (JSON fields)
    images = Column(JSON)  # [{"url": "...", "alt": "...", "type": "main"}]
    variants = Column(JSON)  # [{"name": "color", "options": [...]}]
    attributes = Column(JSON)  # {"material": "cotton", "size": "large"}
    features = Column(JSON)  # ["Feature 1", "Feature 2"]
    tags = Column(JSON)  # ["tag1", "tag2"]
    
    # Reviews and ratings
    reviews_data = Column(JSON)  # {"count": 10, "average_rating": 4.5, "ratings": [...]}
    
    # Shipping and seller info
    shipping_info = Column(JSON)  # {"free_shipping": true, "delivery_time": "2-3 days"}
    seller_info = Column(JSON)  # {"name": "Seller Inc", "rating": 4.8}
    
    # Social proof and trust signals
    social_proof = Column(JSON)  # [{"type": "trust_badge", "text": "SSL Secure"}]
    
    # Scraping metadata
    scraping_metadata = Column(JSON)  # {"scraper_type": "playwright", "confidence": 0.9}
    data_quality_score = Column(Float, default=0.0)
    
    # Timestamps
    first_seen_at = Column(DateTime(timezone=True), server_default=func.now())
    last_updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    last_scraped_at = Column(DateTime(timezone=True))
    
    # Relationships
    brand = relationship("Brand", back_populates="products")
    price_history = relationship("ProductPriceHistory", back_populates="product")
    competitors = relationship("ProductCompetitor", foreign_keys="ProductCompetitor.product_id", back_populates="product")
    
    # Indexes for common queries
    __table_args__ = (
        Index('idx_product_brand_category', 'brand_id', 'category'),
        Index('idx_product_price_range', 'price', 'currency'),
        Index('idx_product_availability', 'availability', 'is_active'),
        Index('idx_product_source', 'source_domain', 'platform_type'),
        Index('idx_product_updated', 'last_updated_at'),
    )


class ProductPriceHistory(Base):
    """Price history tracking for products"""
    __tablename__ = "product_price_history"

    id = Column(Integer, primary_key=True, index=True)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=False)
    
    # Price information
    price = Column(Float, nullable=False)
    original_price = Column(Float)
    currency = Column(String(3), nullable=False)
    discount_percentage = Column(Float)
    
    # Availability at time of capture
    availability = Column(String)
    in_stock = Column(Boolean)
    
    # Source and context
    source_url = Column(String)
    promotion_info = Column(JSON)  # Sale details, coupon codes, etc.
    
    # Timestamp
    recorded_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)
    
    # Relationships
    product = relationship("Product", back_populates="price_history")
    
    # Indexes
    __table_args__ = (
        Index('idx_price_history_product_date', 'product_id', 'recorded_at'),
        Index('idx_price_history_price', 'price', 'currency'),
    )


class ProductCompetitor(Base):
    """Competitor products for comparison"""
    __tablename__ = "product_competitors"

    id = Column(Integer, primary_key=True, index=True)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=False)
    competitor_product_id = Column(Integer, ForeignKey("products.id"), nullable=False)
    
    # Competition metrics
    similarity_score = Column(Float)  # 0-1 similarity score
    price_difference = Column(Float)  # Percentage difference
    feature_comparison = Column(JSON)  # Detailed feature comparison
    
    # Competition type
    competition_type = Column(String)  # direct, indirect, substitute
    match_criteria = Column(JSON)  # What criteria matched (category, keywords, etc.)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    last_compared_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    product = relationship("Product", foreign_keys=[product_id], back_populates="competitors")
    competitor_product = relationship("Product", foreign_keys=[competitor_product_id])
    
    # Unique constraint to prevent duplicates
    __table_args__ = (
        Index('idx_unique_competition', 'product_id', 'competitor_product_id', unique=True),
        Index('idx_competitor_similarity', 'similarity_score'),
    )


# Brand model is imported from brand.py to avoid duplication


class ScrapingJob(Base):
    """Track scraping jobs and their status"""
    __tablename__ = "scraping_jobs"

    id = Column(Integer, primary_key=True, index=True)
    brand_id = Column(Integer, ForeignKey("brands.id"), nullable=True)
    job_id = Column(String, unique=True, index=True)  # Celery task ID
    
    # Job configuration
    job_type = Column(String, nullable=False)  # brand_discovery, product_scraping, competitor_analysis
    target_urls = Column(JSON)  # URLs to scrape
    scraping_config = Column(JSON)  # Scraper configuration
    
    # Job status
    status = Column(String, default="pending", index=True)  # pending, running, completed, failed
    progress = Column(Integer, default=0)  # 0-100
    
    # Results
    products_found = Column(Integer, default=0)
    products_created = Column(Integer, default=0)
    products_updated = Column(Integer, default=0)
    
    # Error handling
    error_message = Column(Text)
    retry_count = Column(Integer, default=0)
    max_retries = Column(Integer, default=3)
    
    # Performance metrics
    pages_scraped = Column(Integer, default=0)
    total_processing_time = Column(Float)  # seconds
    avg_page_load_time = Column(Float)  # seconds
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    started_at = Column(DateTime(timezone=True))
    completed_at = Column(DateTime(timezone=True))
    
    # Relationships
    brand = relationship("Brand", back_populates="scraping_jobs")
    
    # Indexes
    __table_args__ = (
        Index('idx_scraping_job_status', 'status', 'created_at'),
        Index('idx_scraping_job_brand', 'brand_id', 'job_type'),
    )


class CompetitorBrand(Base):
    """Competitor brand information"""
    __tablename__ = "competitor_brands"

    id = Column(Integer, primary_key=True, index=True)
    brand_id = Column(Integer, ForeignKey("brands.id"), nullable=False)
    
    # Competitor information
    name = Column(String, nullable=False)
    url = Column(String, nullable=False)
    logo_url = Column(String)
    
    # Competition analysis
    similarity_score = Column(Float)  # 0-1 how similar to our brand
    threat_level = Column(String)  # low, medium, high
    competition_type = Column(String)  # direct, indirect
    
    # Market data
    estimated_size = Column(String)  # small, medium, large, enterprise
    market_share = Column(Float)  # If available
    pricing_strategy = Column(String)  # premium, competitive, budget
    
    # Brand characteristics
    brand_colors = Column(JSON)
    brand_voice = Column(JSON)
    target_audience = Column(JSON)
    unique_selling_points = Column(JSON)
    
    # Social presence
    social_followers = Column(JSON)  # {"instagram": 10000, "facebook": 5000}
    social_engagement = Column(JSON)  # Engagement metrics
    
    # Performance tracking
    products_tracked = Column(Integer, default=0)
    avg_product_price = Column(Float)
    price_positioning = Column(String)  # relative to our brand
    
    # Monitoring
    monitoring_enabled = Column(Boolean, default=True)
    last_analyzed_at = Column(DateTime(timezone=True))
    next_analysis_at = Column(DateTime(timezone=True))
    
    # Timestamps
    discovered_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Indexes
    __table_args__ = (
        Index('idx_competitor_brand', 'brand_id', 'similarity_score'),
        Index('idx_competitor_threat', 'threat_level', 'competition_type'),
        Index('idx_competitor_monitoring', 'monitoring_enabled', 'next_analysis_at'),
    )


class ScrapingSession(Base):
    """Track individual scraping sessions with detailed metrics"""
    __tablename__ = "scraping_sessions"

    id = Column(Integer, primary_key=True, index=True)
    job_id = Column(Integer, ForeignKey("scraping_jobs.id"), nullable=False)
    session_id = Column(String, unique=True, index=True)
    
    # Session configuration
    scraper_type = Column(String)  # playwright, requests, scrapy
    use_proxy = Column(Boolean, default=False)
    proxy_info = Column(JSON)  # Proxy details if used
    user_agent = Column(String)
    
    # Target information
    target_url = Column(String, nullable=False)
    target_domain = Column(String, index=True)
    platform_detected = Column(String)  # shopify, woocommerce, etc.
    
    # Results
    success = Column(Boolean, default=False)
    data_extracted = Column(JSON)  # Raw extracted data
    products_found = Column(Integer, default=0)
    
    # Performance metrics
    response_time = Column(Float)  # seconds
    page_load_time = Column(Float)  # seconds
    data_quality_score = Column(Float)  # 0-1
    
    # Error handling
    error_type = Column(String)  # network, parsing, anti-bot, etc.
    error_message = Column(Text)
    bot_detection = Column(JSON)  # Bot protection detected
    
    # Timestamps
    started_at = Column(DateTime(timezone=True), server_default=func.now())
    completed_at = Column(DateTime(timezone=True))
    
    # Indexes
    __table_args__ = (
        Index('idx_session_job', 'job_id', 'success'),
        Index('idx_session_domain', 'target_domain', 'started_at'),
        Index('idx_session_performance', 'response_time', 'data_quality_score'),
    )