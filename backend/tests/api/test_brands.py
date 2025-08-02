import pytest
from httpx import AsyncClient
from sqlalchemy.orm import Session
from unittest.mock import Mock

from app.models.user import User
from app.models.brand import Brand
from app.models.job import Job
from tests.factories import UserFactory, BrandFactory


@pytest.mark.unit
class TestBrandsEndpoints:
    """Test brand-related API endpoints."""

    @pytest.mark.asyncio
    async def test_assimilate_brand_success(
        self, 
        async_client: AsyncClient, 
        sample_user: User,
        auth_headers: dict,
        db_session: Session,
        mock_celery
    ):
        """Test successful brand assimilation."""
        brand_data = {
            "url": "https://example.com"
        }
        
        response = await async_client.post(
            "/api/v1/brands/assimilate",
            json=brand_data,
            headers=auth_headers
        )
        
        assert response.status_code == 202
        data = response.json()
        assert "jobId" in data
        assert data["message"] == "Brand assimilation has started."
        
        # Verify job was created in database
        job = db_session.query(Job).filter(Job.job_id == data["jobId"]).first()
        assert job is not None
        assert job.job_type == "assimilate"
        assert job.status == "processing"

    @pytest.mark.asyncio
    async def test_assimilate_brand_unauthorized(self, async_client: AsyncClient):
        """Test brand assimilation without authentication."""
        brand_data = {
            "url": "https://example.com"
        }
        
        response = await async_client.post(
            "/api/v1/brands/assimilate",
            json=brand_data
        )
        
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_assimilate_brand_invalid_url(
        self,
        async_client: AsyncClient,
        auth_headers: dict
    ):
        """Test brand assimilation with invalid URL."""
        brand_data = {
            "url": "not-a-valid-url"
        }
        
        response = await async_client.post(
            "/api/v1/brands/assimilate",
            json=brand_data,
            headers=auth_headers
        )
        
        assert response.status_code == 422  # Validation error

    @pytest.mark.asyncio
    async def test_get_brands_success(
        self,
        async_client: AsyncClient,
        sample_user: User,
        auth_headers: dict,
        db_session: Session
    ):
        """Test successful retrieval of user brands."""
        # Create some brands for the user
        brand1 = BrandFactory.create(user_id=sample_user.id)
        brand2 = BrandFactory.create(user_id=sample_user.id)
        
        db_session.add_all([brand1, brand2])
        db_session.commit()
        
        response = await async_client.get(
            "/api/v1/brands",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "data" in data
        assert len(data["data"]) == 2
        
        # Verify brand data structure
        brand_data = data["data"][0]
        assert "brandId" in brand_data
        assert "name" in brand_data
        assert "url" in brand_data

    @pytest.mark.asyncio
    async def test_get_brands_unauthorized(self, async_client: AsyncClient):
        """Test brands retrieval without authentication."""
        response = await async_client.get("/api/v1/brands")
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_get_brands_empty_list(
        self,
        async_client: AsyncClient,
        sample_user: User,
        auth_headers: dict
    ):
        """Test brands retrieval with no brands."""
        response = await async_client.get(
            "/api/v1/brands",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["data"] == []

    @pytest.mark.asyncio
    async def test_get_brand_kit_success(
        self,
        async_client: AsyncClient,
        sample_brand: Brand,
        auth_headers: dict
    ):
        """Test successful brand kit retrieval."""
        response = await async_client.get(
            f"/api/v1/brands/{sample_brand.id}/kit",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "data" in data
        
        brand_kit = data["data"]
        assert "brandName" in brand_kit
        assert "logoUrl" in brand_kit
        assert "colors" in brand_kit
        assert "voice" in brand_kit
        assert "pillars" in brand_kit
        assert "assets" in brand_kit

    @pytest.mark.asyncio
    async def test_get_brand_kit_not_found(
        self,
        async_client: AsyncClient,
        auth_headers: dict
    ):
        """Test brand kit retrieval for non-existent brand."""
        response = await async_client.get(
            "/api/v1/brands/99999/kit",
            headers=auth_headers
        )
        
        assert response.status_code == 404
        data = response.json()
        assert data["detail"] == "Brand not found"

    @pytest.mark.asyncio
    async def test_get_brand_kit_unauthorized(
        self,
        async_client: AsyncClient,
        sample_brand: Brand
    ):
        """Test brand kit retrieval without authentication."""
        response = await async_client.get(
            f"/api/v1/brands/{sample_brand.id}/kit"
        )
        
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_update_brand_kit_success(
        self,
        async_client: AsyncClient,
        sample_brand: Brand,
        auth_headers: dict,
        db_session: Session
    ):
        """Test successful brand kit update."""
        update_data = {
            "colors": ["#FF0000", "#00FF00", "#0000FF"],
            "voice": "Updated brand voice",
            "pillars": ["Quality", "Innovation", "Customer Focus"]
        }
        
        response = await async_client.put(
            f"/api/v1/brands/{sample_brand.id}/kit",
            json=update_data,
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["message"] == "Brand kit updated successfully."
        
        # Verify database was updated
        db_session.refresh(sample_brand)
        assert sample_brand.colors == update_data["colors"]
        assert sample_brand.voice == update_data["voice"]
        assert sample_brand.pillars == update_data["pillars"]

    @pytest.mark.asyncio
    async def test_update_brand_kit_not_found(
        self,
        async_client: AsyncClient,
        auth_headers: dict
    ):
        """Test brand kit update for non-existent brand."""
        update_data = {
            "colors": ["#FF0000"],
            "voice": "New voice"
        }
        
        response = await async_client.put(
            "/api/v1/brands/99999/kit",
            json=update_data,
            headers=auth_headers
        )
        
        assert response.status_code == 404
        data = response.json()
        assert data["detail"] == "Brand not found"

    @pytest.mark.asyncio
    async def test_update_brand_kit_unauthorized(
        self,
        async_client: AsyncClient,
        sample_brand: Brand
    ):
        """Test brand kit update without authentication."""
        update_data = {
            "colors": ["#FF0000"],
            "voice": "New voice"
        }
        
        response = await async_client.put(
            f"/api/v1/brands/{sample_brand.id}/kit",
            json=update_data
        )
        
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_update_brand_kit_validation_error(
        self,
        async_client: AsyncClient,
        sample_brand: Brand,
        auth_headers: dict
    ):
        """Test brand kit update with invalid data."""
        update_data = {
            "colors": "not-a-list",  # Should be a list
            "voice": ""  # Empty string might not be valid
        }
        
        response = await async_client.put(
            f"/api/v1/brands/{sample_brand.id}/kit",
            json=update_data,
            headers=auth_headers
        )
        
        assert response.status_code == 422  # Validation error


@pytest.mark.integration
class TestBrandsIntegration:
    """Integration tests for brands endpoints."""

    @pytest.mark.asyncio
    async def test_brand_workflow_integration(
        self,
        async_client: AsyncClient,
        sample_user: User,
        auth_headers: dict,
        db_session: Session,
        mock_celery
    ):
        """Test complete brand workflow: assimilate -> get -> update."""
        # Step 1: Assimilate brand
        brand_data = {"url": "https://example.com"}
        response = await async_client.post(
            "/api/v1/brands/assimilate",
            json=brand_data,
            headers=auth_headers
        )
        assert response.status_code == 202
        job_id = response.json()["jobId"]
        
        # Step 2: Simulate job completion and create brand
        brand = BrandFactory.create(user_id=sample_user.id)
        db_session.add(brand)
        db_session.commit()
        
        # Step 3: Get brands list
        response = await async_client.get(
            "/api/v1/brands",
            headers=auth_headers
        )
        assert response.status_code == 200
        brands = response.json()["data"]
        assert len(brands) == 1
        
        # Step 4: Get brand kit
        brand_id = brand.id
        response = await async_client.get(
            f"/api/v1/brands/{brand_id}/kit",
            headers=auth_headers
        )
        assert response.status_code == 200
        brand_kit = response.json()["data"]
        
        # Step 5: Update brand kit
        update_data = {
            "colors": ["#NEW001", "#NEW002"],
            "voice": "Updated voice"
        }
        response = await async_client.put(
            f"/api/v1/brands/{brand_id}/kit",
            json=update_data,
            headers=auth_headers
        )
        assert response.status_code == 200
        
        # Step 6: Verify update
        response = await async_client.get(
            f"/api/v1/brands/{brand_id}/kit",
            headers=auth_headers
        )
        assert response.status_code == 200
        updated_kit = response.json()["data"]
        assert updated_kit["colors"] == update_data["colors"]
        assert updated_kit["voice"] == update_data["voice"]

    @pytest.mark.asyncio
    async def test_multi_user_brand_isolation(
        self,
        async_client: AsyncClient,
        db_session: Session
    ):
        """Test that users can only access their own brands."""
        # Create two users with brands
        user1 = UserFactory.create()
        user2 = UserFactory.create()
        
        brand1 = BrandFactory.create(user_id=user1.id)
        brand2 = BrandFactory.create(user_id=user2.id)
        
        db_session.add_all([user1, user2, brand1, brand2])
        db_session.commit()
        
        # User1 should only see their brand
        auth_headers_1 = {"Authorization": f"Bearer mock-jwt-token-{user1.id}"}
        response = await async_client.get(
            "/api/v1/brands",
            headers=auth_headers_1
        )
        assert response.status_code == 200
        brands = response.json()["data"]
        assert len(brands) == 1
        assert brands[0]["brandId"] == brand1.id
        
        # User2 should only see their brand
        auth_headers_2 = {"Authorization": f"Bearer mock-jwt-token-{user2.id}"}
        response = await async_client.get(
            "/api/v1/brands",
            headers=auth_headers_2
        )
        assert response.status_code == 200
        brands = response.json()["data"]
        assert len(brands) == 1
        assert brands[0]["brandId"] == brand2.id
        
        # User1 should not be able to access User2's brand kit
        response = await async_client.get(
            f"/api/v1/brands/{brand2.id}/kit",
            headers=auth_headers_1
        )
        assert response.status_code == 404  # Should not find brand for this user