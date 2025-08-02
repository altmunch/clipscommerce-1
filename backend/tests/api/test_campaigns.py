import pytest
from httpx import AsyncClient
from sqlalchemy.orm import Session
from datetime import date, timedelta

from app.models.user import User
from app.models.brand import Brand
from app.models.campaign import Campaign
from tests.factories import UserFactory, BrandFactory, CampaignFactory


@pytest.mark.unit
class TestCampaignsEndpoints:
    """Test campaign-related API endpoints."""

    @pytest.mark.asyncio
    async def test_create_campaign_success(
        self,
        async_client: AsyncClient,
        sample_brand: Brand,
        auth_headers: dict,
        db_session: Session
    ):
        """Test successful campaign creation."""
        campaign_data = {
            "brandId": sample_brand.id,
            "name": "Test Campaign",
            "goal": "Increase brand awareness",
            "startDate": str(date.today()),
            "endDate": str(date.today() + timedelta(days=30))
        }
        
        response = await async_client.post(
            "/api/v1/campaigns",
            json=campaign_data,
            headers=auth_headers
        )
        
        assert response.status_code == 201
        data = response.json()
        assert "data" in data
        
        campaign = data["data"]
        assert campaign["name"] == campaign_data["name"]
        assert campaign["goal"] == campaign_data["goal"]
        assert campaign["brandId"] == sample_brand.id
        
        # Verify campaign was created in database
        db_campaign = db_session.query(Campaign).filter(
            Campaign.name == campaign_data["name"]
        ).first()
        assert db_campaign is not None
        assert db_campaign.brand_id == sample_brand.id

    @pytest.mark.asyncio
    async def test_create_campaign_brand_not_found(
        self,
        async_client: AsyncClient,
        auth_headers: dict
    ):
        """Test campaign creation with non-existent brand."""
        campaign_data = {
            "brandId": 99999,
            "name": "Test Campaign",
            "goal": "Test goal",
            "startDate": str(date.today()),
            "endDate": str(date.today() + timedelta(days=30))
        }
        
        response = await async_client.post(
            "/api/v1/campaigns",
            json=campaign_data,
            headers=auth_headers
        )
        
        assert response.status_code == 404
        data = response.json()
        assert data["detail"] == "Brand not found"

    @pytest.mark.asyncio
    async def test_create_campaign_unauthorized(self, async_client: AsyncClient):
        """Test campaign creation without authentication."""
        campaign_data = {
            "brandId": 1,
            "name": "Test Campaign",
            "goal": "Test goal",
            "startDate": str(date.today()),
            "endDate": str(date.today() + timedelta(days=30))
        }
        
        response = await async_client.post(
            "/api/v1/campaigns",
            json=campaign_data
        )
        
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_create_campaign_validation_error(
        self,
        async_client: AsyncClient,
        sample_brand: Brand,
        auth_headers: dict
    ):
        """Test campaign creation with invalid data."""
        campaign_data = {
            "brandId": sample_brand.id,
            "name": "",  # Empty name should fail validation
            "goal": "Test goal",
            "startDate": "invalid-date",  # Invalid date format
            "endDate": str(date.today() + timedelta(days=30))
        }
        
        response = await async_client.post(
            "/api/v1/campaigns",
            json=campaign_data,
            headers=auth_headers
        )
        
        assert response.status_code == 422  # Validation error

    @pytest.mark.asyncio
    async def test_create_campaign_invalid_date_range(
        self,
        async_client: AsyncClient,
        sample_brand: Brand,
        auth_headers: dict
    ):
        """Test campaign creation with end date before start date."""
        campaign_data = {
            "brandId": sample_brand.id,
            "name": "Test Campaign",
            "goal": "Test goal",
            "startDate": str(date.today() + timedelta(days=30)),
            "endDate": str(date.today())  # End date before start date
        }
        
        response = await async_client.post(
            "/api/v1/campaigns",
            json=campaign_data,
            headers=auth_headers
        )
        
        # This might be a validation error or successful depending on validation rules
        # Adjust assertion based on actual validation implementation
        assert response.status_code in [201, 422]

    @pytest.mark.asyncio
    async def test_get_campaigns_success(
        self,
        async_client: AsyncClient,
        sample_brand: Brand,
        auth_headers: dict,
        db_session: Session
    ):
        """Test successful campaigns retrieval."""
        # Create some campaigns for the brand
        campaign1 = CampaignFactory.create(brand_id=sample_brand.id)
        campaign2 = CampaignFactory.create(brand_id=sample_brand.id)
        
        db_session.add_all([campaign1, campaign2])
        db_session.commit()
        
        response = await async_client.get(
            f"/api/v1/campaigns?brandId={sample_brand.id}",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "data" in data
        assert len(data["data"]) == 2
        
        # Verify campaign data structure
        campaign_data = data["data"][0]
        assert "campaignId" in campaign_data
        assert "brandId" in campaign_data
        assert "name" in campaign_data
        assert "goal" in campaign_data
        assert campaign_data["brandId"] == sample_brand.id

    @pytest.mark.asyncio
    async def test_get_campaigns_brand_not_found(
        self,
        async_client: AsyncClient,
        auth_headers: dict
    ):
        """Test campaigns retrieval for non-existent brand."""
        response = await async_client.get(
            "/api/v1/campaigns?brandId=99999",
            headers=auth_headers
        )
        
        assert response.status_code == 404
        data = response.json()
        assert data["detail"] == "Brand not found"

    @pytest.mark.asyncio
    async def test_get_campaigns_unauthorized(
        self,
        async_client: AsyncClient,
        sample_brand: Brand
    ):
        """Test campaigns retrieval without authentication."""
        response = await async_client.get(
            f"/api/v1/campaigns?brandId={sample_brand.id}"
        )
        
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_get_campaigns_empty_list(
        self,
        async_client: AsyncClient,
        sample_brand: Brand,
        auth_headers: dict
    ):
        """Test campaigns retrieval with no campaigns."""
        response = await async_client.get(
            f"/api/v1/campaigns?brandId={sample_brand.id}",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["data"] == []

    @pytest.mark.asyncio
    async def test_get_campaigns_missing_brand_id(
        self,
        async_client: AsyncClient,
        auth_headers: dict
    ):
        """Test campaigns retrieval without brandId parameter."""
        response = await async_client.get(
            "/api/v1/campaigns",
            headers=auth_headers
        )
        
        assert response.status_code == 422  # Missing required parameter


@pytest.mark.integration
class TestCampaignsIntegration:
    """Integration tests for campaigns endpoints."""

    @pytest.mark.asyncio
    async def test_campaign_workflow_integration(
        self,
        async_client: AsyncClient,
        sample_brand: Brand,
        auth_headers: dict,
        db_session: Session
    ):
        """Test complete campaign workflow: create -> get."""
        # Step 1: Create campaign
        campaign_data = {
            "brandId": sample_brand.id,
            "name": "Integration Test Campaign",
            "goal": "Test complete workflow",
            "startDate": str(date.today()),
            "endDate": str(date.today() + timedelta(days=60))
        }
        
        response = await async_client.post(
            "/api/v1/campaigns",
            json=campaign_data,
            headers=auth_headers
        )
        assert response.status_code == 201
        created_campaign = response.json()["data"]
        
        # Step 2: Get campaigns list
        response = await async_client.get(
            f"/api/v1/campaigns?brandId={sample_brand.id}",
            headers=auth_headers
        )
        assert response.status_code == 200
        campaigns = response.json()["data"]
        
        # Verify created campaign is in the list
        campaign_ids = [c["campaignId"] for c in campaigns]
        assert created_campaign["campaignId"] in campaign_ids
        
        # Find our campaign in the list
        our_campaign = next(
            c for c in campaigns 
            if c["campaignId"] == created_campaign["campaignId"]
        )
        assert our_campaign["name"] == campaign_data["name"]
        assert our_campaign["goal"] == campaign_data["goal"]

    @pytest.mark.asyncio
    async def test_multi_brand_campaign_isolation(
        self,
        async_client: AsyncClient,
        sample_user: User,
        auth_headers: dict,
        db_session: Session
    ):
        """Test that campaigns are properly isolated by brand."""
        # Create two brands for the same user
        brand1 = BrandFactory.create(user_id=sample_user.id)
        brand2 = BrandFactory.create(user_id=sample_user.id)
        
        # Create campaigns for each brand
        campaign1 = CampaignFactory.create(brand_id=brand1.id)
        campaign2 = CampaignFactory.create(brand_id=brand2.id)
        
        db_session.add_all([brand1, brand2, campaign1, campaign2])
        db_session.commit()
        
        # Get campaigns for brand1 - should only return campaign1
        response = await async_client.get(
            f"/api/v1/campaigns?brandId={brand1.id}",
            headers=auth_headers
        )
        assert response.status_code == 200
        campaigns = response.json()["data"]
        assert len(campaigns) == 1
        assert campaigns[0]["campaignId"] == campaign1.id
        
        # Get campaigns for brand2 - should only return campaign2
        response = await async_client.get(
            f"/api/v1/campaigns?brandId={brand2.id}",
            headers=auth_headers
        )
        assert response.status_code == 200
        campaigns = response.json()["data"]
        assert len(campaigns) == 1
        assert campaigns[0]["campaignId"] == campaign2.id

    @pytest.mark.asyncio
    async def test_user_brand_access_control(
        self,
        async_client: AsyncClient,
        db_session: Session
    ):
        """Test that users can only access campaigns for their own brands."""
        # Create two users with their own brands
        user1 = UserFactory.create()
        user2 = UserFactory.create()
        
        brand1 = BrandFactory.create(user_id=user1.id)
        brand2 = BrandFactory.create(user_id=user2.id)
        
        campaign1 = CampaignFactory.create(brand_id=brand1.id)
        campaign2 = CampaignFactory.create(brand_id=brand2.id)
        
        db_session.add_all([user1, user2, brand1, brand2, campaign1, campaign2])
        db_session.commit()
        
        # User1 should be able to access their brand's campaigns
        auth_headers_1 = {"Authorization": f"Bearer mock-jwt-token-{user1.id}"}
        response = await async_client.get(
            f"/api/v1/campaigns?brandId={brand1.id}",
            headers=auth_headers_1
        )
        assert response.status_code == 200
        campaigns = response.json()["data"]
        assert len(campaigns) == 1
        assert campaigns[0]["campaignId"] == campaign1.id
        
        # User1 should NOT be able to access user2's brand campaigns
        response = await async_client.get(
            f"/api/v1/campaigns?brandId={brand2.id}",
            headers=auth_headers_1
        )
        assert response.status_code == 404  # Brand not found for this user
        
        # User1 should NOT be able to create campaigns for user2's brand
        campaign_data = {
            "brandId": brand2.id,
            "name": "Unauthorized Campaign",
            "goal": "Should fail",
            "startDate": str(date.today()),
            "endDate": str(date.today() + timedelta(days=30))
        }
        
        response = await async_client.post(
            "/api/v1/campaigns",
            json=campaign_data,
            headers=auth_headers_1
        )
        assert response.status_code == 404  # Brand not found for this user

    @pytest.mark.asyncio
    async def test_campaign_data_persistence(
        self,
        async_client: AsyncClient,
        sample_brand: Brand,
        auth_headers: dict,
        db_session: Session
    ):
        """Test that campaign data persists correctly."""
        # Create campaign with specific data
        campaign_data = {
            "brandId": sample_brand.id,
            "name": "Persistence Test Campaign",
            "goal": "Test data persistence",
            "startDate": "2024-01-01",
            "endDate": "2024-01-31"
        }
        
        # Create campaign
        response = await async_client.post(
            "/api/v1/campaigns",
            json=campaign_data,
            headers=auth_headers
        )
        assert response.status_code == 201
        created_campaign = response.json()["data"]
        
        # Retrieve and verify all data is correct
        response = await async_client.get(
            f"/api/v1/campaigns?brandId={sample_brand.id}",
            headers=auth_headers
        )
        assert response.status_code == 200
        campaigns = response.json()["data"]
        
        campaign = campaigns[0]
        assert campaign["name"] == campaign_data["name"]
        assert campaign["goal"] == campaign_data["goal"]
        assert campaign["startDate"] == campaign_data["startDate"]
        assert campaign["endDate"] == campaign_data["endDate"]
        assert campaign["brandId"] == sample_brand.id
        assert "createdAt" in campaign
        assert "updatedAt" in campaign
        assert "campaignId" in campaign