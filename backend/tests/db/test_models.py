import pytest
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from datetime import datetime, timedelta

from app.models.user import User
from app.models.brand import Brand
from app.models.campaign import Campaign
from app.models.content import Content
from app.models.job import Job
from tests.factories import (
    UserFactory, BrandFactory, CampaignFactory, 
    ContentFactory, JobFactory, create_complete_brand_setup
)


@pytest.mark.db
class TestUserModel:
    """Test User model functionality."""

    def test_create_user(self, db_session: Session):
        """Test creating a user."""
        user_data = {
            'email': 'test@example.com',
            'full_name': 'Test User',
            'hashed_password': 'hashed_password_123'
        }
        user = User(**user_data)
        
        db_session.add(user)
        db_session.commit()
        db_session.refresh(user)
        
        assert user.id is not None
        assert user.email == user_data['email']
        assert user.full_name == user_data['full_name']
        assert user.is_active is True
        assert user.is_superuser is False
        assert user.created_at is not None
        assert user.updated_at is not None

    def test_user_email_unique_constraint(self, db_session: Session):
        """Test that user email must be unique."""
        # Create first user
        user1 = UserFactory.create(email='test@example.com')
        db_session.add(user1)
        db_session.commit()
        
        # Try to create second user with same email
        user2 = UserFactory.create(email='test@example.com')
        db_session.add(user2)
        
        with pytest.raises(IntegrityError):
            db_session.commit()

    def test_user_relationships(self, db_session: Session):
        """Test user relationships with brands."""
        user = UserFactory.create()
        brand1 = BrandFactory.create(user_id=user.id)
        brand2 = BrandFactory.create(user_id=user.id)
        
        db_session.add_all([user, brand1, brand2])
        db_session.commit()
        
        # Test relationship
        db_session.refresh(user)
        assert len(user.brands) == 2
        assert brand1 in user.brands
        assert brand2 in user.brands

    def test_user_factory(self, db_session: Session):
        """Test UserFactory creates valid users."""
        user = UserFactory.create()
        
        db_session.add(user)
        db_session.commit()
        db_session.refresh(user)
        
        assert user.id is not None
        assert '@' in user.email
        assert user.full_name is not None
        assert user.hashed_password is not None


@pytest.mark.db
class TestBrandModel:
    """Test Brand model functionality."""

    def test_create_brand(self, db_session: Session):
        """Test creating a brand."""
        user = UserFactory.create()
        db_session.add(user)
        db_session.commit()
        
        brand_data = {
            'name': 'Test Brand',
            'url': 'https://testbrand.com',
            'description': 'A test brand',
            'colors': ['#FF0000', '#00FF00'],
            'fonts': ['Arial', 'Helvetica'],
            'voice': 'Professional and friendly',
            'user_id': user.id
        }
        brand = Brand(**brand_data)
        
        db_session.add(brand)
        db_session.commit()
        db_session.refresh(brand)
        
        assert brand.id is not None
        assert brand.name == brand_data['name']
        assert brand.url == brand_data['url']
        assert brand.colors == brand_data['colors']
        assert brand.fonts == brand_data['fonts']
        assert brand.voice == brand_data['voice']
        assert brand.user_id == user.id
        assert brand.status == 'active'  # Default status

    def test_brand_user_relationship(self, db_session: Session):
        """Test brand-user relationship."""
        user = UserFactory.create()
        brand = BrandFactory.create(user_id=user.id)
        
        db_session.add_all([user, brand])
        db_session.commit()
        
        # Test forward relationship
        db_session.refresh(brand)
        assert brand.user.id == user.id
        
        # Test reverse relationship
        db_session.refresh(user)
        assert brand in user.brands

    def test_brand_cascade_delete(self, db_session: Session):
        """Test that deleting a user cascades to brands."""
        user = UserFactory.create()
        brand = BrandFactory.create(user_id=user.id)
        
        db_session.add_all([user, brand])
        db_session.commit()
        
        brand_id = brand.id
        
        # Delete user
        db_session.delete(user)
        db_session.commit()
        
        # Brand should be deleted too (if configured)
        remaining_brand = db_session.query(Brand).filter(Brand.id == brand_id).first()
        # Depending on cascade configuration, this might be None
        # Adjust assertion based on your cascade setup

    def test_brand_factory(self, db_session: Session):
        """Test BrandFactory creates valid brands."""
        user = UserFactory.create()
        db_session.add(user)
        db_session.commit()
        
        brand = BrandFactory.create(user_id=user.id)
        
        db_session.add(brand)
        db_session.commit()
        db_session.refresh(brand)
        
        assert brand.id is not None
        assert brand.name is not None
        assert brand.url is not None
        assert isinstance(brand.colors, list)
        assert isinstance(brand.fonts, list)
        assert brand.user_id == user.id


@pytest.mark.db
class TestCampaignModel:
    """Test Campaign model functionality."""

    def test_create_campaign(self, db_session: Session):
        """Test creating a campaign."""
        user = UserFactory.create()
        brand = BrandFactory.create(user_id=user.id)
        db_session.add_all([user, brand])
        db_session.commit()
        
        campaign_data = {
            'name': 'Test Campaign',
            'description': 'A test campaign',
            'status': 'active',
            'start_date': datetime.now().date(),
            'end_date': (datetime.now() + timedelta(days=30)).date(),
            'budget': 10000,
            'brand_id': brand.id
        }
        campaign = Campaign(**campaign_data)
        
        db_session.add(campaign)
        db_session.commit()
        db_session.refresh(campaign)
        
        assert campaign.id is not None
        assert campaign.name == campaign_data['name']
        assert campaign.brand_id == brand.id
        assert campaign.status == campaign_data['status']

    def test_campaign_brand_relationship(self, db_session: Session):
        """Test campaign-brand relationship."""
        user = UserFactory.create()
        brand = BrandFactory.create(user_id=user.id)
        campaign = CampaignFactory.create(brand_id=brand.id)
        
        db_session.add_all([user, brand, campaign])
        db_session.commit()
        
        # Test forward relationship
        db_session.refresh(campaign)
        assert campaign.brand.id == brand.id
        
        # Test reverse relationship
        db_session.refresh(brand)
        assert campaign in brand.campaigns

    def test_campaign_date_validation(self, db_session: Session):
        """Test campaign date constraints."""
        user = UserFactory.create()
        brand = BrandFactory.create(user_id=user.id)
        db_session.add_all([user, brand])
        db_session.commit()
        
        # Test valid date range
        campaign = CampaignFactory.create(
            brand_id=brand.id,
            start_date=datetime.now().date(),
            end_date=(datetime.now() + timedelta(days=30)).date()
        )
        
        db_session.add(campaign)
        db_session.commit()  # Should succeed
        
        assert campaign.id is not None

    def test_campaign_factory(self, db_session: Session):
        """Test CampaignFactory creates valid campaigns."""
        user = UserFactory.create()
        brand = BrandFactory.create(user_id=user.id)
        db_session.add_all([user, brand])
        db_session.commit()
        
        campaign = CampaignFactory.create(brand_id=brand.id)
        
        db_session.add(campaign)
        db_session.commit()
        db_session.refresh(campaign)
        
        assert campaign.id is not None
        assert campaign.name is not None
        assert campaign.brand_id == brand.id
        assert campaign.start_date is not None
        assert campaign.end_date is not None


@pytest.mark.db
class TestContentModel:
    """Test Content model functionality."""

    def test_create_content(self, db_session: Session):
        """Test creating content."""
        user = UserFactory.create()
        brand = BrandFactory.create(user_id=user.id)
        campaign = CampaignFactory.create(brand_id=brand.id)
        db_session.add_all([user, brand, campaign])
        db_session.commit()
        
        content_data = {
            'title': 'Test Content',
            'description': 'A test content piece',
            'content_type': 'video',
            'platform': 'youtube',
            'status': 'draft',
            'script': 'This is a test script',
            'brand_id': brand.id,
            'campaign_id': campaign.id
        }
        content = Content(**content_data)
        
        db_session.add(content)
        db_session.commit()
        db_session.refresh(content)
        
        assert content.id is not None
        assert content.title == content_data['title']
        assert content.content_type == content_data['content_type']
        assert content.platform == content_data['platform']
        assert content.brand_id == brand.id
        assert content.campaign_id == campaign.id

    def test_content_relationships(self, db_session: Session):
        """Test content relationships with brand and campaign."""
        user = UserFactory.create()
        brand = BrandFactory.create(user_id=user.id)
        campaign = CampaignFactory.create(brand_id=brand.id)
        content = ContentFactory.create(brand_id=brand.id, campaign_id=campaign.id)
        
        db_session.add_all([user, brand, campaign, content])
        db_session.commit()
        
        # Test brand relationship
        db_session.refresh(content)
        assert content.brand.id == brand.id
        
        # Test campaign relationship
        assert content.campaign.id == campaign.id
        
        # Test reverse relationships
        db_session.refresh(brand)
        assert content in brand.content_items
        
        db_session.refresh(campaign)
        assert content in campaign.content_items

    def test_content_json_fields(self, db_session: Session):
        """Test content JSON fields."""
        user = UserFactory.create()
        brand = BrandFactory.create(user_id=user.id)
        campaign = CampaignFactory.create(brand_id=brand.id)
        db_session.add_all([user, brand, campaign])
        db_session.commit()
        
        visual_elements = [
            {"type": "image", "url": "https://example.com/image.jpg"},
            {"type": "text", "content": "Sample text"}
        ]
        
        performance_data = {
            "views": 1000,
            "likes": 50,
            "shares": 10
        }
        
        content = ContentFactory.create(
            brand_id=brand.id,
            campaign_id=campaign.id,
            visual_elements=visual_elements,
            actual_performance=performance_data
        )
        
        db_session.add(content)
        db_session.commit()
        db_session.refresh(content)
        
        assert content.visual_elements == visual_elements
        assert content.actual_performance == performance_data

    def test_content_factory(self, db_session: Session):
        """Test ContentFactory creates valid content."""
        user = UserFactory.create()
        brand = BrandFactory.create(user_id=user.id)
        campaign = CampaignFactory.create(brand_id=brand.id)
        db_session.add_all([user, brand, campaign])
        db_session.commit()
        
        content = ContentFactory.create(brand_id=brand.id, campaign_id=campaign.id)
        
        db_session.add(content)
        db_session.commit()
        db_session.refresh(content)
        
        assert content.id is not None
        assert content.title is not None
        assert content.content_type in ['video', 'image', 'text', 'carousel']
        assert content.platform in ['youtube', 'tiktok', 'instagram', 'facebook', 'twitter']
        assert content.brand_id == brand.id
        assert content.campaign_id == campaign.id


@pytest.mark.db
class TestJobModel:
    """Test Job model functionality."""

    def test_create_job(self, db_session: Session):
        """Test creating a job."""
        user = UserFactory.create()
        db_session.add(user)
        db_session.commit()
        
        job_data = {
            'task_name': 'brand_assimilation',
            'status': 'pending',
            'progress': 0,
            'parameters': {'brand_id': 'test-brand-id'},
            'user_id': user.id
        }
        job = Job(**job_data)
        
        db_session.add(job)
        db_session.commit()
        db_session.refresh(job)
        
        assert job.id is not None
        assert job.task_name == job_data['task_name']
        assert job.status == job_data['status']
        assert job.progress == job_data['progress']
        assert job.parameters == job_data['parameters']
        assert job.user_id == user.id

    def test_job_user_relationship(self, db_session: Session):
        """Test job-user relationship."""
        user = UserFactory.create()
        job = JobFactory.create(user_id=user.id)
        
        db_session.add_all([user, job])
        db_session.commit()
        
        # Test forward relationship
        db_session.refresh(job)
        assert job.user.id == user.id
        
        # Test reverse relationship
        db_session.refresh(user)
        assert job in user.jobs

    def test_job_status_progression(self, db_session: Session):
        """Test job status updates."""
        user = UserFactory.create()
        job = JobFactory.create(user_id=user.id, status='pending', progress=0)
        
        db_session.add_all([user, job])
        db_session.commit()
        
        # Update job to processing
        job.status = 'processing'
        job.progress = 50
        job.started_at = datetime.utcnow()
        
        db_session.commit()
        db_session.refresh(job)
        
        assert job.status == 'processing'
        assert job.progress == 50
        assert job.started_at is not None
        
        # Complete job
        job.status = 'completed'
        job.progress = 100
        job.completed_at = datetime.utcnow()
        job.result = {'message': 'Job completed successfully'}
        
        db_session.commit()
        db_session.refresh(job)
        
        assert job.status == 'completed'
        assert job.progress == 100
        assert job.completed_at is not None
        assert job.result['message'] == 'Job completed successfully'

    def test_job_factory(self, db_session: Session):
        """Test JobFactory creates valid jobs."""
        user = UserFactory.create()
        db_session.add(user)
        db_session.commit()
        
        job = JobFactory.create(user_id=user.id)
        
        db_session.add(job)
        db_session.commit()
        db_session.refresh(job)
        
        assert job.id is not None
        assert job.task_name is not None
        assert job.status in ['pending', 'processing', 'completed', 'failed']
        assert job.user_id == user.id


@pytest.mark.db
class TestDatabaseIntegration:
    """Test complex database operations and relationships."""

    def test_complete_brand_setup(self, db_session: Session):
        """Test creating a complete brand setup with all relationships."""
        user = UserFactory.create()
        db_session.add(user)
        db_session.commit()
        
        brand, campaigns, content_items = create_complete_brand_setup(user.id)
        
        db_session.add(brand)
        db_session.add_all(campaigns)
        db_session.add_all(content_items)
        db_session.commit()
        
        # Refresh all objects
        db_session.refresh(user)
        db_session.refresh(brand)
        
        # Verify relationships
        assert brand in user.brands
        assert len(brand.campaigns) == 2
        assert len(brand.content_items) >= 6  # 3-5 content per campaign * 2 campaigns
        
        # Verify campaign relationships
        for campaign in campaigns:
            db_session.refresh(campaign)
            assert campaign.brand_id == brand.id
            assert len(campaign.content_items) >= 3

    def test_cascade_operations(self, db_session: Session):
        """Test cascade delete operations."""
        user = UserFactory.create()
        brand = BrandFactory.create(user_id=user.id)
        campaign = CampaignFactory.create(brand_id=brand.id)
        content = ContentFactory.create(brand_id=brand.id, campaign_id=campaign.id)
        
        db_session.add_all([user, brand, campaign, content])
        db_session.commit()
        
        content_id = content.id
        campaign_id = campaign.id
        brand_id = brand.id
        
        # Delete campaign - should cascade to content (if configured)
        db_session.delete(campaign)
        db_session.commit()
        
        # Check if content still exists (depends on cascade configuration)
        remaining_content = db_session.query(Content).filter(Content.id == content_id).first()
        # Adjust assertion based on your cascade setup

    def test_query_performance(self, db_session: Session):
        """Test query performance with relationships."""
        user = UserFactory.create()
        brands = [BrandFactory.create(user_id=user.id) for _ in range(3)]
        
        campaigns = []
        content_items = []
        
        for brand in brands:
            brand_campaigns = [CampaignFactory.create(brand_id=brand.id) for _ in range(2)]
            campaigns.extend(brand_campaigns)
            
            for campaign in brand_campaigns:
                campaign_content = [ContentFactory.create(
                    brand_id=brand.id, 
                    campaign_id=campaign.id
                ) for _ in range(3)]
                content_items.extend(campaign_content)
        
        db_session.add(user)
        db_session.add_all(brands)
        db_session.add_all(campaigns)
        db_session.add_all(content_items)
        db_session.commit()
        
        # Test efficient queries with joins
        user_with_brands = db_session.query(User).filter(User.id == user.id).first()
        
        # Should be able to access relationships without additional queries
        assert len(user_with_brands.brands) == 3
        
        for brand in user_with_brands.brands:
            assert len(brand.campaigns) == 2
            assert len(brand.content_items) == 6  # 2 campaigns * 3 content each

    def test_transaction_rollback(self, db_session: Session):
        """Test transaction rollback on error."""
        user = UserFactory.create()
        db_session.add(user)
        db_session.commit()
        
        try:
            # Start transaction
            brand1 = BrandFactory.create(user_id=user.id)
            db_session.add(brand1)
            
            # This should cause an error (duplicate email in same transaction)
            user2 = UserFactory.create(email=user.email)
            db_session.add(user2)
            
            db_session.commit()
        except IntegrityError:
            db_session.rollback()
        
        # Verify brand1 was not committed
        brands = db_session.query(Brand).filter(Brand.user_id == user.id).all()
        assert len(brands) == 0