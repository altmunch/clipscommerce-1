import factory
from faker import Faker
from datetime import datetime, timedelta
import uuid
import random

from app.models.user import User
from app.models.brand import Brand
from app.models.campaign import Campaign
from app.models.content import Idea, Blueprint, Video
from app.models.job import Job
from app.models.product import Product, ProductPriceHistory, ProductCompetitor, ScrapingJob, CompetitorBrand
from app.models.video_project import (
    VideoProject, VideoSegment, BRollClip, VideoAsset, UGCTestimonial, VideoGenerationJob,
    VideoProviderEnum, VideoQualityEnum, VideoStyleEnum, GenerationStatusEnum, VideoProjectTypeEnum
)
from app.models.tiktok_trend import (
    TikTokTrend, TikTokVideo, TikTokHashtag, TikTokSound, TikTokScrapingJob, TikTokAnalytics,
    TrendStatus, TrendType, ContentCategory
)
from app.models.social_media import (
    SocialMediaAccount, SocialMediaPost, SocialMediaAnalytics, PostingSchedule, 
    SocialMediaWebhook, CrossPlatformCampaign, PlatformType, AccountStatus, PostStatus, ContentType
)
from app.models.analytics import VideoPerformancePrediction, ModelPerformanceMetrics

fake = Faker()


class UserFactory(factory.Factory):
    """Factory for creating User instances."""
    
    class Meta:
        model = User
    
    id = factory.LazyFunction(lambda: fake.random_int(min=1, max=999999))
    email = factory.LazyAttribute(lambda obj: fake.email())
    hashed_password = factory.LazyAttribute(lambda obj: fake.password())
    is_active = True
    is_superuser = False
    created_at = factory.LazyFunction(datetime.utcnow)
    updated_at = factory.LazyFunction(datetime.utcnow)


class BrandFactory(factory.Factory):
    """Factory for creating Brand instances."""
    
    class Meta:
        model = Brand
    
    id = factory.LazyFunction(lambda: fake.random_int(min=1, max=999999))
    name = factory.LazyAttribute(lambda obj: fake.company())
    url = factory.LazyAttribute(lambda obj: fake.url())
    logo_url = factory.LazyAttribute(lambda obj: fake.image_url())
    
    # JSON fields that match the Brand model
    colors = factory.LazyAttribute(lambda obj: {"primary": fake.hex_color(), "secondary": fake.hex_color()})
    voice = factory.LazyAttribute(lambda obj: {"tone": "professional", "dos": "Be authentic", "donts": "Don't be pushy"})
    pillars = factory.LazyAttribute(lambda obj: ["Education", "Entertainment", "Inspiration"])
    
    # Extended fields for competitor analysis and product management
    industry = factory.LazyAttribute(lambda obj: fake.word())
    target_audience = factory.LazyAttribute(lambda obj: {"age": "25-35", "interests": [fake.word() for _ in range(3)]})
    unique_value_proposition = factory.LazyAttribute(lambda obj: fake.text(max_nb_chars=200))
    
    # Competitor data
    competitors = factory.LazyAttribute(lambda obj: [{"name": fake.company(), "url": fake.url(), "similarity": 0.8}])
    market_position = factory.LazyAttribute(lambda obj: {"segment": "premium", "share": 15.2})
    
    # Product catalog summary
    product_count = factory.LazyAttribute(lambda obj: fake.random_int(0, 100))
    avg_price_range = factory.LazyAttribute(lambda obj: {"min": 10, "max": 100, "avg": 45})
    main_categories = factory.LazyAttribute(lambda obj: ["Electronics", "Accessories"])
    
    # Scraping configuration
    scraping_config = factory.LazyAttribute(lambda obj: {"timeout": 30, "max_pages": 10})
    
    user_id = factory.SubFactory(UserFactory)
    created_at = factory.LazyFunction(datetime.utcnow)
    updated_at = factory.LazyFunction(datetime.utcnow)


class CampaignFactory(factory.Factory):
    """Factory for creating Campaign instances."""
    
    class Meta:
        model = Campaign
    
    id = factory.LazyFunction(lambda: fake.random_int(min=1, max=999999))
    name = factory.LazyAttribute(lambda obj: f"{fake.word().title()} Campaign")
    goal = factory.LazyAttribute(lambda obj: fake.sentence(nb_words=6))
    
    # Dates
    start_date = factory.LazyAttribute(lambda obj: fake.date_this_month())
    end_date = factory.LazyAttribute(lambda obj: fake.date_between(
        start_date=datetime.now().date(),
        end_date=datetime.now().date() + timedelta(days=90)
    ))
    
    brand_id = factory.SubFactory(BrandFactory)
    created_at = factory.LazyFunction(datetime.utcnow)
    updated_at = factory.LazyFunction(datetime.utcnow)


class IdeaFactory(factory.Factory):
    """Factory for creating Idea instances."""
    
    class Meta:
        model = Idea
    
    id = factory.LazyFunction(lambda: fake.random_int(min=1, max=999999))
    hook = factory.LazyAttribute(lambda obj: fake.sentence(nb_words=10))
    viral_score = factory.LazyAttribute(lambda obj: round(fake.pyfloat(left_digits=1, right_digits=1, positive=True, min_value=1.0, max_value=10.0), 1))
    status = factory.LazyAttribute(lambda obj: fake.random_element(["pending", "approved", "rejected"]))
    
    brand_id = factory.SubFactory(BrandFactory)
    campaign_id = factory.SubFactory(CampaignFactory)
    created_at = factory.LazyFunction(datetime.utcnow)


class JobFactory(factory.Factory):
    """Factory for creating Job instances."""
    
    class Meta:
        model = Job
    
    id = factory.LazyFunction(lambda: str(uuid.uuid4()))
    task_name = factory.LazyAttribute(lambda obj: fake.random_element([
        "brand_assimilation", "idea_generation", "blueprint_creation", 
        "video_generation", "content_optimization"
    ]))
    status = "pending"
    progress = 0
    
    # Job details
    parameters = factory.LazyAttribute(lambda obj: {
        "brand_id": str(uuid.uuid4()),
        "campaign_id": str(uuid.uuid4()),
        "content_type": fake.random_element(["video", "image", "text"])
    })
    
    result = None
    error_message = None
    
    # Timing
    started_at = None
    completed_at = None
    expires_at = factory.LazyAttribute(lambda obj: fake.date_time_between(
        start_date=datetime.now(),
        end_date=datetime.now() + timedelta(hours=24)
    ))
    
    user_id = factory.SubFactory(UserFactory)
    created_at = factory.LazyFunction(datetime.utcnow)
    updated_at = factory.LazyFunction(datetime.utcnow)


# Factory traits for different scenarios
class ActiveBrandFactory(BrandFactory):
    """Factory for active brands."""
    status = "active"


class PendingBrandFactory(BrandFactory):
    """Factory for pending brands."""
    status = "pending"


class CompletedJobFactory(JobFactory):
    """Factory for completed jobs."""
    status = "completed"
    progress = 100
    started_at = factory.LazyAttribute(lambda obj: fake.date_time_between(
        start_date=datetime.now() - timedelta(hours=2),
        end_date=datetime.now() - timedelta(hours=1)
    ))
    completed_at = factory.LazyAttribute(lambda obj: fake.date_time_between(
        start_date=datetime.now() - timedelta(hours=1),
        end_date=datetime.now()
    ))
    result = factory.LazyAttribute(lambda obj: {
        "message": "Job completed successfully",
        "data": {"result": fake.sentence()}
    })


class FailedJobFactory(JobFactory):
    """Factory for failed jobs."""
    status = "failed"
    progress = 0
    error_message = factory.LazyAttribute(lambda obj: fake.sentence())
    started_at = factory.LazyAttribute(lambda obj: fake.date_time_between(
        start_date=datetime.now() - timedelta(hours=1),
        end_date=datetime.now()
    ))
    completed_at = factory.LazyAttribute(lambda obj: fake.date_time_between(
        start_date=datetime.now() - timedelta(minutes=30),
        end_date=datetime.now()
    ))


class ApprovedIdeaFactory(IdeaFactory):
    """Factory for approved ideas."""
    status = "approved"
    viral_score = factory.LazyAttribute(lambda obj: round(fake.random_uniform(7.0, 10.0), 1))


# Utility functions for creating related objects
def create_brand_with_campaigns(user_id: str, num_campaigns: int = 3):
    """Create a brand with associated campaigns."""
    brand = BrandFactory.create(user_id=user_id)
    campaigns = [CampaignFactory.create(brand_id=brand.id) for _ in range(num_campaigns)]
    return brand, campaigns


def create_campaign_with_ideas(brand_id: str, num_ideas: int = 5):
    """Create a campaign with associated ideas."""
    campaign = CampaignFactory.create(brand_id=brand_id)
    idea_items = [IdeaFactory.create(
        brand_id=brand_id, 
        campaign_id=campaign.id
    ) for _ in range(num_ideas)]
    return campaign, idea_items


def create_complete_brand_setup(user_id: str):
    """Create a complete brand setup with campaigns and ideas."""
    brand = BrandFactory.create(user_id=user_id)
    
    campaigns = []
    all_ideas = []
    
    for _ in range(2):  # 2 campaigns per brand
        campaign = CampaignFactory.create(brand_id=brand.id)
        campaigns.append(campaign)
        
        # 3-5 idea items per campaign
        num_ideas = fake.random_int(min=3, max=5)
        idea_items = [IdeaFactory.create(
            brand_id=brand.id,
            campaign_id=campaign.id
        ) for _ in range(num_ideas)]
        all_ideas.extend(idea_items)
    
    return brand, campaigns, all_ideas


# Product and Scraping Factories

class ProductFactory(factory.Factory):
    """Factory for creating Product instances."""
    
    class Meta:
        model = Product
    
    id = factory.LazyFunction(lambda: fake.random_int(min=1, max=999999))
    brand_id = factory.SubFactory(BrandFactory)
    name = factory.LazyAttribute(lambda obj: fake.word().title() + " " + fake.word().title())
    description = factory.LazyAttribute(lambda obj: fake.text(max_nb_chars=500))
    short_description = factory.LazyAttribute(lambda obj: fake.sentence())
    sku = factory.LazyAttribute(lambda obj: fake.bothify(text='???-####'))
    brand_name = factory.LazyAttribute(lambda obj: fake.company())
    category = factory.LazyAttribute(lambda obj: fake.random_element([
        "Electronics", "Clothing", "Home & Garden", "Beauty", "Sports", "Books"
    ]))
    
    price = factory.LazyAttribute(lambda obj: round(fake.random_uniform(10, 500), 2))
    original_price = factory.LazyAttribute(lambda obj: round(obj.price * fake.random_uniform(1.1, 1.5), 2))
    currency = "USD"
    sale_price = factory.LazyAttribute(lambda obj: round(obj.price * fake.random_uniform(0.7, 0.9), 2))
    discount_percentage = factory.LazyAttribute(lambda obj: round((obj.original_price - obj.price) / obj.original_price * 100, 2))
    
    availability = factory.LazyAttribute(lambda obj: fake.random_element([
        "in_stock", "out_of_stock", "pre_order", "limited"
    ]))
    is_active = True
    
    source_url = factory.LazyAttribute(lambda obj: fake.url())
    source_domain = factory.LazyAttribute(lambda obj: fake.domain_name())
    platform_type = factory.LazyAttribute(lambda obj: fake.random_element([
        "shopify", "woocommerce", "magento", "bigcommerce"
    ]))
    
    images = factory.LazyAttribute(lambda obj: [
        {"url": fake.image_url(), "alt": fake.sentence(), "type": "main"},
        {"url": fake.image_url(), "alt": fake.sentence(), "type": "gallery"}
    ])
    variants = factory.LazyAttribute(lambda obj: [
        {"name": "color", "options": ["red", "blue", "green"]},
        {"name": "size", "options": ["S", "M", "L", "XL"]}
    ])
    attributes = factory.LazyAttribute(lambda obj: {
        "material": fake.word(),
        "weight": f"{fake.random_int(1, 50)}kg",
        "dimensions": f"{fake.random_int(10, 100)}x{fake.random_int(10, 100)}x{fake.random_int(10, 100)}cm"
    })
    features = factory.LazyAttribute(lambda obj: [fake.sentence() for _ in range(3)])
    tags = factory.LazyAttribute(lambda obj: [fake.word() for _ in range(5)])
    
    reviews_data = factory.LazyAttribute(lambda obj: {
        "count": fake.random_int(1, 100),
        "average_rating": round(fake.random_uniform(3.0, 5.0), 1),
        "ratings": [fake.random_int(1, 5) for _ in range(10)]
    })
    
    shipping_info = factory.LazyAttribute(lambda obj: {
        "free_shipping": fake.boolean(),
        "delivery_time": f"{fake.random_int(1, 14)} days"
    })
    seller_info = factory.LazyAttribute(lambda obj: {
        "name": fake.company(),
        "rating": round(fake.random_uniform(3.0, 5.0), 1)
    })
    
    data_quality_score = factory.LazyAttribute(lambda obj: round(fake.random_uniform(0.5, 1.0), 2))
    
    first_seen_at = factory.LazyFunction(datetime.utcnow)
    last_updated_at = factory.LazyFunction(datetime.utcnow)


class ScrapingJobFactory(factory.Factory):
    """Factory for creating ScrapingJob instances."""
    
    class Meta:
        model = ScrapingJob
    
    id = factory.LazyFunction(lambda: fake.random_int(min=1, max=999999))
    brand_id = factory.SubFactory(BrandFactory)
    job_id = factory.LazyFunction(lambda: str(uuid.uuid4()))
    
    job_type = factory.LazyAttribute(lambda obj: fake.random_element([
        "brand_discovery", "product_scraping", "competitor_analysis"
    ]))
    target_urls = factory.LazyAttribute(lambda obj: [fake.url() for _ in range(3)])
    scraping_config = factory.LazyAttribute(lambda obj: {
        "timeout": 30,
        "max_pages": 10,
        "use_proxy": fake.boolean()
    })
    
    status = factory.LazyAttribute(lambda obj: fake.random_element([
        "pending", "running", "completed", "failed"
    ]))
    progress = factory.LazyAttribute(lambda obj: fake.random_int(0, 100))
    
    products_found = factory.LazyAttribute(lambda obj: fake.random_int(0, 50))
    products_created = factory.LazyAttribute(lambda obj: fake.random_int(0, obj.products_found))
    products_updated = factory.LazyAttribute(lambda obj: fake.random_int(0, obj.products_found))
    
    pages_scraped = factory.LazyAttribute(lambda obj: fake.random_int(1, 20))
    total_processing_time = factory.LazyAttribute(lambda obj: fake.random_uniform(60, 3600))
    avg_page_load_time = factory.LazyAttribute(lambda obj: fake.random_uniform(1, 10))
    
    created_at = factory.LazyFunction(datetime.utcnow)


# Video Generation Factories

class VideoProjectFactory(factory.Factory):
    """Factory for creating VideoProject instances."""
    
    class Meta:
        model = VideoProject
    
    id = factory.LazyFunction(uuid.uuid4)
    title = factory.LazyAttribute(lambda obj: fake.sentence())
    description = factory.LazyAttribute(lambda obj: fake.text(max_nb_chars=200))
    project_type = factory.LazyAttribute(lambda obj: fake.random_element(VideoProjectTypeEnum))
    
    brand_id = factory.SubFactory(BrandFactory)
    target_platform = factory.LazyAttribute(lambda obj: fake.random_element([
        "tiktok", "instagram", "youtube_shorts"
    ]))
    target_duration = factory.LazyAttribute(lambda obj: fake.random_uniform(15, 60))
    aspect_ratio = "9:16"
    quality = VideoQualityEnum.MEDIUM
    style = VideoStyleEnum.PROFESSIONAL
    
    preferred_provider = factory.LazyAttribute(lambda obj: fake.random_element(VideoProviderEnum))
    voice_id = factory.LazyAttribute(lambda obj: fake.bothify(text='voice_???_####'))
    language = "en"
    
    status = GenerationStatusEnum.PENDING
    progress_percentage = 0.0
    
    estimated_cost = factory.LazyAttribute(lambda obj: round(fake.random_uniform(10, 100), 2))
    actual_cost = 0.0
    
    brand_guidelines = factory.LazyAttribute(lambda obj: {
        "colors": [fake.hex_color() for _ in range(3)],
        "fonts": [fake.word() for _ in range(2)],
        "logo_url": fake.image_url()
    })
    
    generation_config = factory.LazyAttribute(lambda obj: {
        "temperature": fake.random_uniform(0.5, 1.0),
        "max_tokens": fake.random_int(100, 500)
    })
    
    created_at = factory.LazyFunction(datetime.utcnow)
    created_by = factory.LazyFunction(uuid.uuid4)


class VideoSegmentFactory(factory.Factory):
    """Factory for creating VideoSegment instances."""
    
    class Meta:
        model = VideoSegment
    
    id = factory.LazyFunction(uuid.uuid4)
    project_id = factory.SubFactory(VideoProjectFactory)
    segment_number = factory.LazyAttribute(lambda obj: fake.random_int(1, 10))
    title = factory.LazyAttribute(lambda obj: fake.sentence())
    
    start_time = factory.LazyAttribute(lambda obj: fake.random_uniform(0, 30))
    end_time = factory.LazyAttribute(lambda obj: obj.start_time + fake.random_uniform(5, 15))
    duration = factory.LazyAttribute(lambda obj: obj.end_time - obj.start_time)
    
    prompt = factory.LazyAttribute(lambda obj: fake.text(max_nb_chars=200))
    enhanced_prompt = factory.LazyAttribute(lambda obj: fake.text(max_nb_chars=300))
    style = VideoStyleEnum.PROFESSIONAL
    quality = VideoQualityEnum.MEDIUM
    provider = factory.LazyAttribute(lambda obj: fake.random_element(VideoProviderEnum))
    
    provider_job_id = factory.LazyAttribute(lambda obj: fake.bothify(text='job_???_####'))
    status = GenerationStatusEnum.PENDING
    
    generation_time = factory.LazyAttribute(lambda obj: fake.random_uniform(30, 300))
    cost = factory.LazyAttribute(lambda obj: round(fake.random_uniform(5, 50), 2))
    
    has_speech = factory.LazyAttribute(lambda obj: fake.boolean())
    speech_text = factory.LazyAttribute(lambda obj: fake.sentence() if obj.has_speech else None)
    
    resolution = "1920x1080"
    fps = 30
    format = "mp4"
    
    created_at = factory.LazyFunction(datetime.utcnow)


class UGCTestimonialFactory(factory.Factory):
    """Factory for creating UGCTestimonial instances."""
    
    class Meta:
        model = UGCTestimonial
    
    id = factory.LazyFunction(uuid.uuid4)
    project_id = factory.SubFactory(VideoProjectFactory)
    
    original_review_text = factory.LazyAttribute(lambda obj: fake.text(max_nb_chars=300))
    review_source = factory.LazyAttribute(lambda obj: fake.random_element([
        "amazon", "google", "yelp", "facebook", "manual"
    ]))
    review_rating = factory.LazyAttribute(lambda obj: fake.random_int(3, 5))
    review_author = factory.LazyAttribute(lambda obj: fake.name())
    
    avatar_provider = factory.LazyAttribute(lambda obj: fake.random_element([
        "did", "heygen", "synthesia"
    ]))
    avatar_id = factory.LazyAttribute(lambda obj: fake.bothify(text='avatar_???_####'))
    avatar_gender = factory.LazyAttribute(lambda obj: fake.random_element(["male", "female"]))
    avatar_ethnicity = factory.LazyAttribute(lambda obj: fake.random_element([
        "caucasian", "asian", "african", "hispanic", "middle_eastern"
    ]))
    avatar_age_range = factory.LazyAttribute(lambda obj: fake.random_element([
        "20-30", "30-40", "40-50", "50-60"
    ]))
    
    generated_script = factory.LazyAttribute(lambda obj: fake.text(max_nb_chars=200))
    script_emotion = factory.LazyAttribute(lambda obj: fake.random_element([
        "enthusiastic", "calm", "excited", "professional"
    ]))
    script_language = "en"
    
    voice_provider = factory.LazyAttribute(lambda obj: fake.random_element([
        "elevenlabs", "built_in"
    ]))
    voice_id = factory.LazyAttribute(lambda obj: fake.bothify(text='voice_???_####'))
    
    status = GenerationStatusEnum.PENDING
    duration = factory.LazyAttribute(lambda obj: fake.random_uniform(30, 120))
    generation_cost = factory.LazyAttribute(lambda obj: round(fake.random_uniform(10, 50), 2))
    
    created_at = factory.LazyFunction(datetime.utcnow)


# TikTok Trend Factories

class TikTokTrendFactory(factory.Factory):
    """Factory for creating TikTokTrend instances."""
    
    class Meta:
        model = TikTokTrend
    
    id = factory.LazyFunction(lambda: fake.random_int(min=1, max=999999))
    trend_id = factory.LazyFunction(lambda: fake.bothify(text='trend_???_####'))
    name = factory.LazyAttribute(lambda obj: f"#{fake.word()}{fake.word()}")
    normalized_name = factory.LazyAttribute(lambda obj: obj.name.lower())
    
    trend_type = factory.LazyAttribute(lambda obj: fake.random_element(TrendType))
    trend_status = factory.LazyAttribute(lambda obj: fake.random_element(TrendStatus))
    content_category = factory.LazyAttribute(lambda obj: fake.random_element(ContentCategory))
    
    total_videos = factory.LazyAttribute(lambda obj: fake.random_int(1000, 1000000))
    total_views = factory.LazyAttribute(lambda obj: fake.random_int(100000, 100000000))
    total_likes = factory.LazyAttribute(lambda obj: fake.random_int(10000, 10000000))
    total_shares = factory.LazyAttribute(lambda obj: fake.random_int(1000, 1000000))
    total_comments = factory.LazyAttribute(lambda obj: fake.random_int(5000, 5000000))
    
    viral_score = factory.LazyAttribute(lambda obj: round(fake.random_uniform(0.1, 10.0), 2))
    growth_rate = factory.LazyAttribute(lambda obj: round(fake.random_uniform(-50, 200), 2))
    engagement_rate = factory.LazyAttribute(lambda obj: round(fake.random_uniform(2, 15), 2))
    velocity = factory.LazyAttribute(lambda obj: round(fake.random_uniform(0.1, 5.0), 2))
    
    first_detected = factory.LazyFunction(datetime.utcnow)
    description = factory.LazyAttribute(lambda obj: fake.text(max_nb_chars=200))
    keywords = factory.LazyAttribute(lambda obj: [fake.word() for _ in range(5)])
    hashtags = factory.LazyAttribute(lambda obj: [f"#{fake.word()}" for _ in range(3)])
    
    geographic_data = factory.LazyAttribute(lambda obj: {
        "US": fake.random_int(20, 40),
        "UK": fake.random_int(10, 20),
        "CA": fake.random_int(5, 15)
    })
    demographic_data = factory.LazyAttribute(lambda obj: {
        "age_groups": {
            "18-24": fake.random_int(30, 50),
            "25-34": fake.random_int(20, 35),
            "35-44": fake.random_int(10, 25)
        },
        "gender": {
            "female": fake.random_int(40, 70),
            "male": fake.random_int(30, 60)
        }
    })
    
    created_at = factory.LazyFunction(datetime.utcnow)
    is_active = True


class TikTokVideoFactory(factory.Factory):
    """Factory for creating TikTokVideo instances."""
    
    class Meta:
        model = TikTokVideo
    
    id = factory.LazyFunction(lambda: fake.random_int(min=1, max=999999))
    video_id = factory.LazyFunction(lambda: fake.bothify(text='video_???_####'))
    trend_id = factory.SubFactory(TikTokTrendFactory)
    
    title = factory.LazyAttribute(lambda obj: fake.sentence())
    description = factory.LazyAttribute(lambda obj: fake.text(max_nb_chars=150))
    duration = factory.LazyAttribute(lambda obj: fake.random_int(15, 180))
    
    creator_username = factory.LazyAttribute(lambda obj: fake.user_name())
    creator_display_name = factory.LazyAttribute(lambda obj: fake.name())
    creator_follower_count = factory.LazyAttribute(lambda obj: fake.random_int(100, 1000000))
    creator_verified = factory.LazyAttribute(lambda obj: fake.boolean(chance_of_getting_true=20))
    
    view_count = factory.LazyAttribute(lambda obj: fake.random_int(1000, 10000000))
    like_count = factory.LazyAttribute(lambda obj: fake.random_int(50, obj.view_count // 10))
    share_count = factory.LazyAttribute(lambda obj: fake.random_int(10, obj.like_count // 5))
    comment_count = factory.LazyAttribute(lambda obj: fake.random_int(5, obj.like_count // 10))
    engagement_rate = factory.LazyAttribute(lambda obj: round(
        (obj.like_count + obj.share_count + obj.comment_count) / obj.view_count * 100, 2
    ))
    
    hashtags = factory.LazyAttribute(lambda obj: [f"#{fake.word()}" for _ in range(5)])
    mentions = factory.LazyAttribute(lambda obj: [f"@{fake.user_name()}" for _ in range(2)])
    sounds_used = factory.LazyAttribute(lambda obj: [fake.bothify(text='sound_???_####')])
    effects_used = factory.LazyAttribute(lambda obj: [fake.word() for _ in range(3)])
    
    transcript = factory.LazyAttribute(lambda obj: fake.text(max_nb_chars=300))
    visual_elements = factory.LazyAttribute(lambda obj: [
        {"type": "text_overlay", "content": fake.sentence()},
        {"type": "effect", "name": fake.word()}
    ])
    content_hooks = factory.LazyAttribute(lambda obj: [fake.sentence() for _ in range(2)])
    
    tiktok_url = factory.LazyAttribute(lambda obj: f"https://tiktok.com/@{obj.creator_username}/video/{obj.video_id}")
    posted_at = factory.LazyAttribute(lambda obj: fake.date_time_between(
        start_date=datetime.now() - timedelta(days=30),
        end_date=datetime.now()
    ))
    video_quality = factory.LazyAttribute(lambda obj: fake.random_element(["HD", "FHD", "4K"]))
    
    scraped_at = factory.LazyFunction(datetime.utcnow)
    scraping_source = "apify"
    
    created_at = factory.LazyFunction(datetime.utcnow)
    is_active = True


class TikTokHashtagFactory(factory.Factory):
    """Factory for creating TikTokHashtag instances."""
    
    class Meta:
        model = TikTokHashtag
    
    id = factory.LazyFunction(lambda: fake.random_int(min=1, max=999999))
    hashtag = factory.LazyAttribute(lambda obj: f"#{fake.word()}{fake.word()}")
    normalized_hashtag = factory.LazyAttribute(lambda obj: obj.hashtag.lower())
    trend_id = factory.SubFactory(TikTokTrendFactory)
    
    total_videos = factory.LazyAttribute(lambda obj: fake.random_int(100, 100000))
    total_views = factory.LazyAttribute(lambda obj: fake.random_int(10000, 10000000))
    usage_velocity = factory.LazyAttribute(lambda obj: round(fake.random_uniform(0.1, 50.0), 2))
    
    is_trending = factory.LazyAttribute(lambda obj: fake.boolean(chance_of_getting_true=30))
    trend_score = factory.LazyAttribute(lambda obj: round(fake.random_uniform(0.1, 10.0), 2))
    first_seen = factory.LazyFunction(datetime.utcnow)
    
    related_hashtags = factory.LazyAttribute(lambda obj: [f"#{fake.word()}" for _ in range(3)])
    top_creators = factory.LazyAttribute(lambda obj: [fake.user_name() for _ in range(5)])
    geographic_distribution = factory.LazyAttribute(lambda obj: {
        "US": fake.random_int(20, 50),
        "UK": fake.random_int(10, 30)
    })
    
    created_at = factory.LazyFunction(datetime.utcnow)


# Social Media Factories

class SocialMediaAccountFactory(factory.Factory):
    """Factory for creating SocialMediaAccount instances."""
    
    class Meta:
        model = SocialMediaAccount
    
    id = factory.LazyFunction(lambda: fake.random_int(min=1, max=999999))
    brand_id = factory.SubFactory(BrandFactory)
    platform = factory.LazyAttribute(lambda obj: fake.random_element(PlatformType))
    username = factory.LazyAttribute(lambda obj: fake.user_name())
    display_name = factory.LazyAttribute(lambda obj: fake.name())
    profile_picture_url = factory.LazyAttribute(lambda obj: fake.image_url())
    
    platform_account_id = factory.LazyFunction(lambda: fake.bothify(text='acc_???_####'))
    business_account_id = factory.LazyFunction(lambda: fake.bothify(text='biz_???_####'))
    
    access_token = factory.LazyFunction(lambda: fake.bothify(text='token_' + '?' * 32))
    token_expires_at = factory.LazyAttribute(lambda obj: fake.date_time_between(
        start_date=datetime.now(),
        end_date=datetime.now() + timedelta(days=60)
    ))
    
    status = AccountStatus.ACTIVE
    is_business_account = factory.LazyAttribute(lambda obj: fake.boolean(chance_of_getting_true=70))
    is_verified = factory.LazyAttribute(lambda obj: fake.boolean(chance_of_getting_true=20))
    follower_count = factory.LazyAttribute(lambda obj: fake.random_int(100, 100000))
    following_count = factory.LazyAttribute(lambda obj: fake.random_int(50, 5000))
    
    posting_settings = factory.LazyAttribute(lambda obj: {
        "auto_hashtags": fake.boolean(),
        "optimal_timing": fake.boolean(),
        "cross_post": fake.boolean()
    })
    analytics_settings = factory.LazyAttribute(lambda obj: {
        "track_engagement": True,
        "track_reach": True,
        "daily_reports": fake.boolean()
    })
    
    created_at = factory.LazyFunction(datetime.utcnow)


class SocialMediaPostFactory(factory.Factory):
    """Factory for creating SocialMediaPost instances."""
    
    class Meta:
        model = SocialMediaPost
    
    id = factory.LazyFunction(lambda: fake.random_int(min=1, max=999999))
    account_id = factory.SubFactory(SocialMediaAccountFactory)
    video_project_id = factory.SubFactory(VideoProjectFactory)
    
    platform_post_id = factory.LazyFunction(lambda: fake.bothify(text='post_???_####'))
    post_url = factory.LazyAttribute(lambda obj: fake.url())
    
    content_type = factory.LazyAttribute(lambda obj: fake.random_element(ContentType))
    caption = factory.LazyAttribute(lambda obj: fake.text(max_nb_chars=200))
    hashtags = factory.LazyAttribute(lambda obj: [f"#{fake.word()}" for _ in range(5)])
    mentions = factory.LazyAttribute(lambda obj: [f"@{fake.user_name()}" for _ in range(2)])
    location_tag = factory.LazyAttribute(lambda obj: fake.city())
    
    media_urls = factory.LazyAttribute(lambda obj: [fake.url() for _ in range(1, 4)])
    thumbnail_url = factory.LazyAttribute(lambda obj: fake.image_url())
    duration = factory.LazyAttribute(lambda obj: fake.random_int(15, 180))
    
    status = PostStatus.DRAFT
    scheduled_at = factory.LazyAttribute(lambda obj: fake.date_time_between(
        start_date=datetime.now(),
        end_date=datetime.now() + timedelta(days=7)
    ))
    
    view_count = factory.LazyAttribute(lambda obj: fake.random_int(100, 50000))
    like_count = factory.LazyAttribute(lambda obj: fake.random_int(10, obj.view_count // 10))
    comment_count = factory.LazyAttribute(lambda obj: fake.random_int(1, obj.like_count // 5))
    share_count = factory.LazyAttribute(lambda obj: fake.random_int(1, obj.like_count // 10))
    save_count = factory.LazyAttribute(lambda obj: fake.random_int(1, obj.like_count // 8))
    
    engagement_rate = factory.LazyAttribute(lambda obj: round(
        (obj.like_count + obj.comment_count + obj.share_count) / max(obj.view_count, 1) * 100, 2
    ))
    reach = factory.LazyAttribute(lambda obj: fake.random_int(obj.view_count // 2, obj.view_count))
    impressions = factory.LazyAttribute(lambda obj: fake.random_int(obj.view_count, obj.view_count * 2))
    
    created_at = factory.LazyFunction(datetime.utcnow)


class SocialMediaAnalyticsFactory(factory.Factory):
    """Factory for creating SocialMediaAnalytics instances."""
    
    class Meta:
        model = SocialMediaAnalytics
    
    id = factory.LazyFunction(lambda: fake.random_int(min=1, max=999999))
    account_id = factory.SubFactory(SocialMediaAccountFactory)
    post_id = factory.SubFactory(SocialMediaPostFactory)
    
    date = factory.LazyFunction(datetime.utcnow)
    period_type = factory.LazyAttribute(lambda obj: fake.random_element(["daily", "weekly", "monthly"]))
    
    views = factory.LazyAttribute(lambda obj: fake.random_int(100, 10000))
    likes = factory.LazyAttribute(lambda obj: fake.random_int(10, obj.views // 10))
    comments = factory.LazyAttribute(lambda obj: fake.random_int(1, obj.likes // 5))
    shares = factory.LazyAttribute(lambda obj: fake.random_int(1, obj.likes // 10))
    saves = factory.LazyAttribute(lambda obj: fake.random_int(1, obj.likes // 8))
    
    reach = factory.LazyAttribute(lambda obj: fake.random_int(obj.views // 2, obj.views))
    impressions = factory.LazyAttribute(lambda obj: fake.random_int(obj.views, obj.views * 2))
    unique_viewers = factory.LazyAttribute(lambda obj: fake.random_int(obj.reach // 2, obj.reach))
    
    engagement_rate = factory.LazyAttribute(lambda obj: round(
        (obj.likes + obj.comments + obj.shares) / max(obj.views, 1) * 100, 2
    ))
    like_rate = factory.LazyAttribute(lambda obj: round(obj.likes / max(obj.views, 1) * 100, 2))
    comment_rate = factory.LazyAttribute(lambda obj: round(obj.comments / max(obj.views, 1) * 100, 2))
    share_rate = factory.LazyAttribute(lambda obj: round(obj.shares / max(obj.views, 1) * 100, 2))
    
    audience_demographics = factory.LazyAttribute(lambda obj: {
        "age_groups": {
            "18-24": fake.random_int(20, 40),
            "25-34": fake.random_int(25, 45),
            "35-44": fake.random_int(15, 25)
        },
        "gender": {
            "female": fake.random_int(40, 70),
            "male": fake.random_int(30, 60)
        },
        "locations": {
            "US": fake.random_int(30, 60),
            "UK": fake.random_int(10, 25),
            "CA": fake.random_int(5, 15)
        }
    })
    
    watch_time_total = factory.LazyAttribute(lambda obj: fake.random_int(100, 5000))
    average_watch_time = factory.LazyAttribute(lambda obj: round(fake.random_uniform(0.3, 0.9), 2))
    completion_rate = factory.LazyAttribute(lambda obj: round(fake.random_uniform(0.2, 0.8), 2))
    
    profile_visits = factory.LazyAttribute(lambda obj: fake.random_int(5, 100))
    website_clicks = factory.LazyAttribute(lambda obj: fake.random_int(1, 50))
    follows_gained = factory.LazyAttribute(lambda obj: fake.random_int(0, 20))
    
    created_at = factory.LazyFunction(datetime.utcnow)