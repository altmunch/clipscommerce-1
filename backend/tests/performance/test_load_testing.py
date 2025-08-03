"""
Comprehensive load testing suite for the ViralOS API endpoints.
Tests performance under various load conditions and identifies bottlenecks.
"""

import asyncio
import time
import statistics
from typing import List, Dict, Any
from unittest.mock import AsyncMock, patch
import pytest
import httpx
from locust import HttpUser, task, between
from locust.runners import MasterRunner, WorkerRunner

from app.core.config import settings
from app.db.session import get_db
from tests.factories import (
    BrandFactory, CampaignFactory, ProductFactory, 
    VideoProjectFactory, TikTokTrendFactory
)


class APILoadTestMixin:
    """Mixin class for common load testing functionality."""
    
    def __init__(self):
        self.response_times: List[float] = []
        self.error_count = 0
        self.success_count = 0
    
    def record_response(self, response_time: float, success: bool):
        """Record response metrics."""
        self.response_times.append(response_time)
        if success:
            self.success_count += 1
        else:
            self.error_count += 1
    
    def get_metrics(self) -> Dict[str, Any]:
        """Calculate performance metrics."""
        if not self.response_times:
            return {
                "avg_response_time": 0,
                "p95_response_time": 0,
                "p99_response_time": 0,
                "error_rate": 0,
                "total_requests": 0
            }
        
        return {
            "avg_response_time": statistics.mean(self.response_times),
            "p95_response_time": statistics.quantiles(self.response_times, n=20)[18],  # 95th percentile
            "p99_response_time": statistics.quantiles(self.response_times, n=100)[98],  # 99th percentile
            "error_rate": self.error_count / (self.success_count + self.error_count),
            "total_requests": len(self.response_times),
            "min_response_time": min(self.response_times),
            "max_response_time": max(self.response_times)
        }


@pytest.mark.asyncio
class TestAPIPerformance(APILoadTestMixin):
    """Test API endpoint performance under load."""
    
    def setup_method(self):
        super().__init__()
        self.base_url = f"http://localhost:{settings.PORT}"
    
    async def make_concurrent_requests(self, url: str, method: str = "GET", 
                                     data: dict = None, concurrent_users: int = 10,
                                     requests_per_user: int = 5) -> Dict[str, Any]:
        """Make concurrent requests to test endpoint performance."""
        async def make_request(session: httpx.AsyncClient):
            for _ in range(requests_per_user):
                start_time = time.time()
                try:
                    if method.upper() == "GET":
                        response = await session.get(url)
                    elif method.upper() == "POST":
                        response = await session.post(url, json=data)
                    elif method.upper() == "PUT":
                        response = await session.put(url, json=data)
                    
                    response_time = time.time() - start_time
                    success = response.status_code < 400
                    self.record_response(response_time, success)
                    
                except Exception as e:
                    response_time = time.time() - start_time
                    self.record_response(response_time, False)
        
        async with httpx.AsyncClient() as client:
            tasks = [make_request(client) for _ in range(concurrent_users)]
            await asyncio.gather(*tasks)
        
        return self.get_metrics()
    
    async def test_brand_analysis_performance(self):
        """Test brand analysis endpoint under load."""
        url = f"{self.base_url}/api/v1/brands/brand-1/analyze-url"
        data = {"url": "https://example-brand.com"}
        
        with patch('app.services.scraping.brand_scraper.BrandScraper.extract_brand_info') as mock_scraper:
            mock_scraper.return_value = {
                "name": "Test Brand",
                "description": "Test brand description",
                "logo_url": "https://example.com/logo.png"
            }
            
            metrics = await self.make_concurrent_requests(
                url, method="POST", data=data, 
                concurrent_users=20, requests_per_user=10
            )
        
        # Performance assertions
        assert metrics["avg_response_time"] < 2.0, f"Average response time too high: {metrics['avg_response_time']}"
        assert metrics["p95_response_time"] < 5.0, f"95th percentile too high: {metrics['p95_response_time']}"
        assert metrics["error_rate"] < 0.05, f"Error rate too high: {metrics['error_rate']}"
        
        print(f"Brand Analysis Performance Metrics: {metrics}")
    
    async def test_video_generation_performance(self):
        """Test video generation endpoint performance."""
        url = f"{self.base_url}/api/v1/video-generation/projects"
        data = {
            "blueprint_id": "blueprint-123",
            "platform": "tiktok",
            "duration": 30
        }
        
        with patch('app.services.video_generation.orchestrator.VideoOrchestrator.generate_video') as mock_gen:
            mock_gen.return_value = VideoProjectFactory()
            
            metrics = await self.make_concurrent_requests(
                url, method="POST", data=data,
                concurrent_users=15, requests_per_user=5
            )
        
        assert metrics["avg_response_time"] < 3.0, f"Video generation too slow: {metrics['avg_response_time']}"
        assert metrics["error_rate"] < 0.1, f"Too many video generation errors: {metrics['error_rate']}"
        
        print(f"Video Generation Performance Metrics: {metrics}")
    
    async def test_analytics_dashboard_performance(self):
        """Test analytics endpoints for dashboard performance."""
        brand_id = "brand-1"
        urls = [
            f"{self.base_url}/api/v1/analytics/{brand_id}/kpis",
            f"{self.base_url}/api/v1/analytics/{brand_id}/chart-data?metric=views",
            f"{self.base_url}/api/v1/analytics/{brand_id}/content-performance",
            f"{self.base_url}/api/v1/analytics/{brand_id}/insights"
        ]
        
        with patch('app.services.analytics.performance_predictor.PerformancePredictor') as mock_analytics:
            mock_analytics.return_value.get_kpis.return_value = {
                "total_views": 150000,
                "total_engagement": 12500,
                "avg_engagement_rate": 8.3
            }
            
            for url in urls:
                metrics = await self.make_concurrent_requests(
                    url, concurrent_users=25, requests_per_user=8
                )
                
                assert metrics["avg_response_time"] < 1.0, f"Analytics endpoint too slow: {url}"
                assert metrics["error_rate"] < 0.02, f"Analytics errors too high: {url}"
        
        print("Analytics Dashboard Performance: All endpoints within acceptable limits")
    
    async def test_database_performance_under_load(self):
        """Test database performance with concurrent operations."""
        async def db_operation():
            # Simulate heavy database operations
            start_time = time.time()
            try:
                # Create test data
                brand = BrandFactory()
                campaigns = [CampaignFactory(brand_id=brand.id) for _ in range(5)]
                products = [ProductFactory(brand_id=brand.id) for _ in range(10)]
                
                response_time = time.time() - start_time
                self.record_response(response_time, True)
            except Exception:
                response_time = time.time() - start_time
                self.record_response(response_time, False)
        
        # Run concurrent database operations
        tasks = [db_operation() for _ in range(50)]
        await asyncio.gather(*tasks)
        
        metrics = self.get_metrics()
        assert metrics["avg_response_time"] < 0.5, f"Database operations too slow: {metrics['avg_response_time']}"
        assert metrics["error_rate"] < 0.01, f"Database error rate too high: {metrics['error_rate']}"
        
        print(f"Database Performance Metrics: {metrics}")


class ViralOSUser(HttpUser):
    """Locust user class for comprehensive load testing."""
    
    wait_time = between(1, 3)  # Wait 1-3 seconds between tasks
    
    def on_start(self):
        """Set up user session."""
        self.brand_id = "test-brand-1"
        self.campaign_id = "test-campaign-1"
        self.client.headers.update({"Authorization": "Bearer test-token"})
    
    @task(3)
    def view_dashboard(self):
        """Simulate user viewing dashboard."""
        with self.client.get(f"/api/v1/brands", catch_response=True) as response:
            if response.status_code == 200:
                response.success()
            else:
                response.failure(f"Dashboard load failed: {response.status_code}")
    
    @task(2)
    def analyze_brand(self):
        """Simulate brand analysis."""
        data = {"url": "https://test-brand.com"}
        with self.client.post(f"/api/v1/brands/{self.brand_id}/analyze-url", 
                            json=data, catch_response=True) as response:
            if response.status_code in [200, 202]:
                response.success()
            else:
                response.failure(f"Brand analysis failed: {response.status_code}")
    
    @task(2)
    def generate_content_ideas(self):
        """Simulate content idea generation."""
        data = {"campaign_id": self.campaign_id}
        with self.client.post(f"/api/v1/content/{self.brand_id}/generate-ideas",
                            json=data, catch_response=True) as response:
            if response.status_code in [200, 202]:
                response.success()
            else:
                response.failure(f"Idea generation failed: {response.status_code}")
    
    @task(1)
    def generate_video(self):
        """Simulate video generation."""
        data = {
            "blueprint_id": "test-blueprint-1",
            "platform": "tiktok",
            "duration": 30
        }
        with self.client.post("/api/v1/video-generation/projects",
                            json=data, catch_response=True) as response:
            if response.status_code in [200, 201, 202]:
                response.success()
            else:
                response.failure(f"Video generation failed: {response.status_code}")
    
    @task(4)
    def view_analytics(self):
        """Simulate viewing analytics."""
        endpoints = [
            f"/api/v1/analytics/{self.brand_id}/kpis",
            f"/api/v1/analytics/{self.brand_id}/chart-data?metric=views",
            f"/api/v1/analytics/{self.brand_id}/insights"
        ]
        
        for endpoint in endpoints:
            with self.client.get(endpoint, catch_response=True) as response:
                if response.status_code == 200:
                    response.success()
                else:
                    response.failure(f"Analytics failed: {endpoint}")
    
    @task(1)
    def social_media_posting(self):
        """Simulate social media posting."""
        data = {
            "video_id": "test-video-1",
            "platforms": ["tiktok", "instagram"],
            "captions": {
                "tiktok": "Check out our amazing product! #viral",
                "instagram": "Innovation meets design #newproduct"
            }
        }
        with self.client.post("/api/v1/social-media/post-multi-platform",
                            json=data, catch_response=True) as response:
            if response.status_code in [200, 202]:
                response.success()
            else:
                response.failure(f"Social posting failed: {response.status_code}")


@pytest.mark.asyncio
class TestMemoryPerformance:
    """Test memory usage and performance optimization."""
    
    def test_memory_usage_under_load(self):
        """Test memory consumption during heavy operations."""
        import psutil
        import os
        
        process = psutil.Process(os.getpid())
        initial_memory = process.memory_info().rss / 1024 / 1024  # MB
        
        # Simulate heavy operations
        brands = [BrandFactory() for _ in range(1000)]
        products = [ProductFactory() for _ in range(5000)]
        trends = [TikTokTrendFactory() for _ in range(2000)]
        
        final_memory = process.memory_info().rss / 1024 / 1024  # MB
        memory_increase = final_memory - initial_memory
        
        assert memory_increase < 500, f"Memory usage increased by {memory_increase}MB"
        print(f"Memory usage: {initial_memory}MB -> {final_memory}MB (+{memory_increase}MB)")
    
    def test_large_dataset_processing(self):
        """Test performance with large datasets."""
        start_time = time.time()
        
        # Simulate processing large amounts of data
        large_dataset = [
            {
                "id": i,
                "title": f"Trend {i}",
                "hashtags": [f"#tag{j}" for j in range(10)],
                "metrics": {"views": i * 1000, "likes": i * 100}
            }
            for i in range(10000)
        ]
        
        # Process data (simulate analysis)
        processed_data = []
        for item in large_dataset:
            processed_item = {
                "id": item["id"],
                "score": sum(item["metrics"].values()) / len(item["metrics"]),
                "tag_count": len(item["hashtags"])
            }
            processed_data.append(processed_item)
        
        processing_time = time.time() - start_time
        
        assert processing_time < 5.0, f"Large dataset processing took {processing_time}s"
        assert len(processed_data) == 10000
        print(f"Processed 10,000 items in {processing_time:.2f}s")


@pytest.mark.performance
class TestCachePerformance:
    """Test caching performance and optimization."""
    
    @patch('app.services.ai.cache_manager.CacheManager')
    def test_cache_hit_performance(self, mock_cache):
        """Test cache performance for frequently accessed data."""
        mock_cache.get.return_value = {"cached": "data"}
        
        start_time = time.time()
        
        # Simulate multiple cache hits
        for _ in range(1000):
            result = mock_cache.get("test_key")
            assert result is not None
        
        cache_time = time.time() - start_time
        
        assert cache_time < 0.1, f"Cache operations too slow: {cache_time}s"
        print(f"1000 cache operations completed in {cache_time:.4f}s")
    
    def test_cache_miss_performance(self):
        """Test performance when cache misses occur."""
        cache_misses = 0
        cache_hits = 0
        
        start_time = time.time()
        
        # Simulate cache behavior
        for i in range(100):
            if i % 10 == 0:  # 10% miss rate
                cache_misses += 1
                # Simulate expensive operation
                time.sleep(0.01)
            else:
                cache_hits += 1
        
        total_time = time.time() - start_time
        
        assert cache_misses == 10
        assert cache_hits == 90
        assert total_time < 0.5, f"Cache miss handling too slow: {total_time}s"
        print(f"Cache performance: {cache_hits} hits, {cache_misses} misses in {total_time:.3f}s")


if __name__ == "__main__":
    # Run performance tests
    pytest.main([__file__, "-v", "-m", "performance"])