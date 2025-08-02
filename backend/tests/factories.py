import factory
from faker import Faker
from datetime import datetime, timedelta
import uuid

from app.models.user import User
from app.models.brand import Brand
from app.models.campaign import Campaign
from app.models.content import Content
from app.models.job import Job

fake = Faker()


class UserFactory(factory.Factory):
    """Factory for creating User instances."""
    
    class Meta:
        model = User
    
    id = factory.LazyFunction(lambda: str(uuid.uuid4()))
    email = factory.LazyAttribute(lambda obj: fake.email())
    full_name = factory.LazyAttribute(lambda obj: fake.name())
    hashed_password = factory.LazyAttribute(lambda obj: fake.password())
    is_active = True
    is_superuser = False
    created_at = factory.LazyFunction(datetime.utcnow)
    updated_at = factory.LazyFunction(datetime.utcnow)


class BrandFactory(factory.Factory):
    """Factory for creating Brand instances."""
    
    class Meta:
        model = Brand
    
    id = factory.LazyFunction(lambda: str(uuid.uuid4()))
    name = factory.LazyAttribute(lambda obj: fake.company())
    url = factory.LazyAttribute(lambda obj: fake.url())
    description = factory.LazyAttribute(lambda obj: fake.text(max_nb_chars=200))
    status = "active"
    
    # Brand kit data
    colors = factory.LazyAttribute(lambda obj: [fake.hex_color() for _ in range(3)])
    fonts = factory.LazyAttribute(lambda obj: [fake.word() for _ in range(2)])
    voice = factory.LazyAttribute(lambda obj: fake.sentence(nb_words=6))
    values = factory.LazyAttribute(lambda obj: [fake.word() for _ in range(3)])
    target_audience = factory.LazyAttribute(lambda obj: fake.text(max_nb_chars=100))
    content_pillars = factory.LazyAttribute(lambda obj: [fake.word() for _ in range(3)])
    
    # Metadata
    industry = factory.LazyAttribute(lambda obj: fake.word())
    competitors = factory.LazyAttribute(lambda obj: [fake.company() for _ in range(2)])
    
    user_id = factory.SubFactory(UserFactory)
    created_at = factory.LazyFunction(datetime.utcnow)
    updated_at = factory.LazyFunction(datetime.utcnow)


class CampaignFactory(factory.Factory):
    """Factory for creating Campaign instances."""
    
    class Meta:
        model = Campaign
    
    id = factory.LazyFunction(lambda: str(uuid.uuid4()))
    name = factory.LazyAttribute(lambda obj: f"{fake.word()} Campaign")
    description = factory.LazyAttribute(lambda obj: fake.text(max_nb_chars=300))
    status = "active"
    
    # Campaign details
    objectives = factory.LazyAttribute(lambda obj: [fake.sentence() for _ in range(2)])
    target_metrics = factory.LazyAttribute(lambda obj: {
        "views": fake.random_int(min=1000, max=100000),
        "engagement_rate": fake.random_int(min=5, max=15),
        "conversions": fake.random_int(min=10, max=1000)
    })
    budget = factory.LazyAttribute(lambda obj: fake.random_int(min=1000, max=100000))
    
    # Dates
    start_date = factory.LazyAttribute(lambda obj: fake.date_this_month())
    end_date = factory.LazyAttribute(lambda obj: fake.date_between(
        start_date=datetime.now().date(),
        end_date=datetime.now().date() + timedelta(days=90)
    ))
    
    brand_id = factory.SubFactory(BrandFactory)
    created_at = factory.LazyFunction(datetime.utcnow)
    updated_at = factory.LazyFunction(datetime.utcnow)


class ContentFactory(factory.Factory):
    """Factory for creating Content instances."""
    
    class Meta:
        model = Content
    
    id = factory.LazyFunction(lambda: str(uuid.uuid4()))
    title = factory.LazyAttribute(lambda obj: fake.sentence(nb_words=6))
    description = factory.LazyAttribute(lambda obj: fake.text(max_nb_chars=300))
    content_type = factory.LazyAttribute(lambda obj: fake.random_element([
        "video", "image", "text", "carousel"
    ]))
    platform = factory.LazyAttribute(lambda obj: fake.random_element([
        "youtube", "tiktok", "instagram", "facebook", "twitter"
    ]))
    status = "draft"
    
    # Content details
    script = factory.LazyAttribute(lambda obj: fake.text(max_nb_chars=500))
    visual_elements = factory.LazyAttribute(lambda obj: [
        {"type": "image", "url": fake.image_url()},
        {"type": "text", "content": fake.sentence()}
    ])
    audio_elements = factory.LazyAttribute(lambda obj: [
        {"type": "voiceover", "script": fake.sentence()},
        {"type": "music", "style": fake.word()}
    ])
    
    # Performance data
    estimated_performance = factory.LazyAttribute(lambda obj: {
        "views": fake.random_int(min=1000, max=50000),
        "engagement_rate": fake.random_int(min=3, max=12),
        "virality_score": fake.random_int(min=1, max=10)
    })
    
    actual_performance = factory.LazyAttribute(lambda obj: {
        "views": fake.random_int(min=500, max=75000),
        "likes": fake.random_int(min=50, max=5000),
        "shares": fake.random_int(min=10, max=1000),
        "comments": fake.random_int(min=5, max=500),
        "engagement_rate": fake.random_int(min=2, max=15)
    })
    
    # File URLs
    thumbnail_url = factory.LazyAttribute(lambda obj: fake.image_url())
    video_url = factory.LazyAttribute(lambda obj: fake.url())
    
    # Publishing details
    scheduled_at = factory.LazyAttribute(lambda obj: fake.date_time_between(
        start_date=datetime.now(),
        end_date=datetime.now() + timedelta(days=30)
    ))
    published_at = None
    
    brand_id = factory.SubFactory(BrandFactory)
    campaign_id = factory.SubFactory(CampaignFactory)
    created_at = factory.LazyFunction(datetime.utcnow)
    updated_at = factory.LazyFunction(datetime.utcnow)


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


class PublishedContentFactory(ContentFactory):
    """Factory for published content."""
    status = "published"
    published_at = factory.LazyAttribute(lambda obj: fake.date_time_between(
        start_date=datetime.now() - timedelta(days=30),
        end_date=datetime.now()
    ))


# Utility functions for creating related objects
def create_brand_with_campaigns(user_id: str, num_campaigns: int = 3):
    """Create a brand with associated campaigns."""
    brand = BrandFactory.create(user_id=user_id)
    campaigns = [CampaignFactory.create(brand_id=brand.id) for _ in range(num_campaigns)]
    return brand, campaigns


def create_campaign_with_content(brand_id: str, num_content: int = 5):
    """Create a campaign with associated content."""
    campaign = CampaignFactory.create(brand_id=brand_id)
    content_items = [ContentFactory.create(
        brand_id=brand_id, 
        campaign_id=campaign.id
    ) for _ in range(num_content)]
    return campaign, content_items


def create_complete_brand_setup(user_id: str):
    """Create a complete brand setup with campaigns and content."""
    brand = BrandFactory.create(user_id=user_id)
    
    campaigns = []
    all_content = []
    
    for _ in range(2):  # 2 campaigns per brand
        campaign = CampaignFactory.create(brand_id=brand.id)
        campaigns.append(campaign)
        
        # 3-5 content items per campaign
        num_content = fake.random_int(min=3, max=5)
        content_items = [ContentFactory.create(
            brand_id=brand.id,
            campaign_id=campaign.id
        ) for _ in range(num_content)]
        all_content.extend(content_items)
    
    return brand, campaigns, all_content