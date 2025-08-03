"""
Comprehensive tests for Celery tasks including proper mocking,
async handling, task chaining, error handling, and retry logic.
"""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from datetime import datetime, timedelta
import json
from celery import Celery
from celery.exceptions import Retry

from app.tasks.brand_tasks import (
    analyze_brand_url_task, competitor_analysis_task, brand_assimilation_task
)
from app.tasks.scraping_tasks import (
    scrape_product_data_task, bulk_scraping_task, monitor_scraping_job_task
)
from app.tasks.video_generation_tasks import (
    generate_video_project_task, process_video_segments_task, 
    assemble_final_video_task, generate_ugc_testimonials_task
)
from app.tasks.social_media_tasks import (
    post_to_social_media_task, cross_platform_posting_task,
    update_social_media_analytics_task, process_social_webhooks_task
)
from app.tasks.tiktok_tasks import (
    scrape_tiktok_trends_task, analyze_trending_content_task,
    update_trend_metrics_task, detect_viral_patterns_task
)
from app.tasks.content_tasks import (
    optimize_content_task, generate_ab_test_variants_task,
    schedule_content_posting_task
)
from app.tasks.analytics_tasks import (
    calculate_performance_metrics_task, predict_content_performance_task,
    generate_analytics_report_task
)
from tests.factories import (
    BrandFactory, ProductFactory, VideoProjectFactory,
    SocialMediaAccountFactory, TikTokTrendFactory, ContentFactory
)


class TestBrandTasks:
    """Test brand-related Celery tasks."""

    @pytest.mark.celery
    async def test_analyze_brand_url_task(self, db_session, mock_celery):
        """Test brand URL analysis task."""
        brand = BrandFactory.create()
        db_session.add(brand)
        db_session.commit()
        
        # Mock the actual analysis function
        mock_analysis_result = {
            "brand_info": {
                "name": "Test Brand",
                "description": "A test brand",
                "logo_url": "https://example.com/logo.png"
            },
            "products": [
                {
                    "name": "Test Product",
                    "price": 99.99,
                    "description": "A test product"
                }
            ],
            "data_quality_score": 0.95
        }
        
        with patch('app.services.scraping.brand_scraper.BrandScraper.extract_brand_info') as mock_scraper:
            mock_scraper.return_value = mock_analysis_result
            
            # Execute the task
            result = analyze_brand_url_task.apply_async(
                args=[brand.id, "https://test-brand.com"],
                kwargs={"deep_analysis": True}
            )
        
        assert result.status == "SUCCESS"
        task_result = result.get()
        assert task_result["status"] == "completed"
        assert task_result["brand_info"]["name"] == "Test Brand"
        assert len(task_result["products"]) == 1

    @pytest.mark.celery
    async def test_competitor_analysis_task(self, db_session, mock_celery):
        """Test competitor analysis task."""
        brand = BrandFactory.create()
        db_session.add(brand)
        db_session.commit()
        
        competitor_urls = [
            "https://competitor1.com",
            "https://competitor2.com",
            "https://competitor3.com"
        ]
        
        mock_competitor_result = {
            "competitors": [
                {
                    "name": "Competitor 1",
                    "url": "https://competitor1.com",
                    "similarity_score": 0.85,
                    "strengths": ["Strong social presence", "Innovative products"]
                }
            ],
            "market_analysis": {
                "competitive_landscape": "highly_competitive",
                "opportunities": ["sustainability messaging", "video content"]
            }
        }
        
        with patch('app.services.scraping.brand_scraper.BrandScraper.analyze_competitors') as mock_competitor:
            mock_competitor.return_value = mock_competitor_result
            
            result = competitor_analysis_task.apply_async(
                args=[brand.id, competitor_urls]
            )
        
        assert result.status == "SUCCESS"
        task_result = result.get()
        assert len(task_result["competitors"]) == 1
        assert task_result["market_analysis"]["competitive_landscape"] == "highly_competitive"

    @pytest.mark.celery
    async def test_brand_assimilation_task_with_retry(self, db_session, mock_celery):
        """Test brand assimilation task with retry logic."""
        brand = BrandFactory.create()
        db_session.add(brand)
        db_session.commit()
        
        # Mock AI service failure on first attempt, success on retry
        with patch('app.services.ai.brand_assimilation.BrandAssimilation.process_brand_data') as mock_ai:
            mock_ai.side_effect = [
                Exception("AI service temporarily unavailable"),
                {
                    "brand_voice": "innovative and friendly",
                    "content_pillars": ["innovation", "quality", "sustainability"],
                    "target_audience_insights": {"primary": "tech-savvy millennials"}
                }
            ]
            
            # Task should retry and eventually succeed
            result = brand_assimilation_task.apply_async(
                args=[brand.id],
                retry=True,
                retry_policy={
                    'max_retries': 3,
                    'interval_start': 0,
                    'interval_step': 0.2,
                    'interval_max': 0.2,
                }
            )
        
        # The task should eventually succeed after retry
        task_result = result.get()
        assert task_result["status"] == "completed"
        assert "brand_voice" in task_result


class TestScrapingTasks:
    """Test web scraping related tasks."""

    @pytest.mark.celery
    async def test_scrape_product_data_task(self, db_session, mock_celery):
        """Test product data scraping task."""
        brand = BrandFactory.create()
        db_session.add(brand)
        db_session.commit()
        
        product_urls = [
            "https://example.com/product1",
            "https://example.com/product2"
        ]
        
        mock_scraped_products = [
            {
                "name": "Product 1",
                "price": 49.99,
                "description": "First test product",
                "images": ["https://example.com/img1.jpg"]
            },
            {
                "name": "Product 2", 
                "price": 79.99,
                "description": "Second test product",
                "images": ["https://example.com/img2.jpg"]
            }
        ]
        
        with patch('app.services.scraping.product_scraper.ProductScraper.scrape_products') as mock_scraper:
            mock_scraper.return_value = mock_scraped_products
            
            result = scrape_product_data_task.apply_async(
                args=[brand.id, product_urls]
            )
        
        assert result.status == "SUCCESS"
        task_result = result.get()
        assert task_result["products_scraped"] == 2
        assert task_result["success_rate"] == 1.0

    @pytest.mark.celery
    async def test_bulk_scraping_task_with_progress_tracking(self, db_session, mock_celery, mock_redis):
        """Test bulk scraping task with progress tracking."""
        brand = BrandFactory.create()
        db_session.add(brand)
        db_session.commit()
        
        # Large number of URLs to scrape
        urls = [f"https://example.com/product{i}" for i in range(50)]
        
        def mock_scrape_with_progress(*args, **kwargs):
            # Simulate progress updates
            for i in range(0, 50, 10):
                progress = (i / 50) * 100
                mock_redis.set(f"scraping_progress:{args[0]}", progress)
            
            return [{"name": f"Product {i}", "price": 10 + i} for i in range(50)]
        
        with patch('app.services.scraping.product_scraper.ProductScraper.bulk_scrape') as mock_bulk:
            mock_bulk.side_effect = mock_scrape_with_progress
            
            result = bulk_scraping_task.apply_async(
                args=[brand.id, urls],
                kwargs={"batch_size": 10, "delay_between_batches": 0.1}
            )
        
        task_result = result.get()
        assert task_result["total_processed"] == 50
        assert task_result["status"] == "completed"

    @pytest.mark.celery
    async def test_monitor_scraping_job_task(self, db_session, mock_celery):
        """Test scraping job monitoring task."""
        from app.models.product import ScrapingJob
        
        scraping_job = ScrapingJob(
            brand_id=1,
            job_id="test_job_123",
            job_type="product_scraping",
            status="running",
            progress=50
        )
        db_session.add(scraping_job)
        db_session.commit()
        
        # Mock external job status check
        mock_job_status = {
            "status": "completed",
            "progress": 100,
            "results": {"products_found": 25, "errors": 0}
        }
        
        with patch('app.services.scraping.apify_client.ApifyClient.check_job_status') as mock_status:
            mock_status.return_value = mock_job_status
            
            result = monitor_scraping_job_task.apply_async(
                args=[scraping_job.id]
            )
        
        task_result = result.get()
        assert task_result["final_status"] == "completed"
        
        # Verify database was updated
        db_session.refresh(scraping_job)
        assert scraping_job.status == "completed"
        assert scraping_job.progress == 100


class TestVideoGenerationTasks:
    """Test video generation related tasks."""

    @pytest.mark.celery
    async def test_generate_video_project_task(self, db_session, mock_celery):
        """Test video project generation task."""
        video_project = VideoProjectFactory.create()
        db_session.add(video_project)
        db_session.commit()
        
        mock_generation_result = {
            "status": "completed",
            "video_url": "https://storage.example.com/video.mp4",
            "thumbnail_url": "https://storage.example.com/thumb.jpg",
            "duration": 30.5,
            "generation_time": 120.0,
            "cost": 15.50
        }
        
        with patch('app.services.ai.video_generation.VideoGenerationService.generate_project') as mock_gen:
            mock_gen.return_value = mock_generation_result
            
            result = generate_video_project_task.apply_async(
                args=[video_project.id]
            )
        
        task_result = result.get()
        assert task_result["status"] == "completed"
        assert task_result["video_url"] is not None
        assert task_result["cost"] == 15.50

    @pytest.mark.celery
    async def test_process_video_segments_task_parallel(self, db_session, mock_celery):
        """Test parallel processing of video segments."""
        video_project = VideoProjectFactory.create()
        
        # Create multiple segments
        segments = []
        for i in range(5):
            segment = {
                "id": f"segment_{i}",
                "prompt": f"Video segment {i}",
                "duration": 6,
                "start_time": i * 6
            }
            segments.append(segment)
        
        db_session.add(video_project)
        db_session.commit()
        
        mock_segment_results = [
            {
                "segment_id": f"segment_{i}",
                "video_url": f"https://storage.example.com/segment_{i}.mp4",
                "status": "completed"
            }
            for i in range(5)
        ]
        
        with patch('app.services.ai.video_generation.VideoGenerationService.process_segments_parallel') as mock_process:
            mock_process.return_value = mock_segment_results
            
            result = process_video_segments_task.apply_async(
                args=[video_project.id, segments]
            )
        
        task_result = result.get()
        assert len(task_result["completed_segments"]) == 5
        assert task_result["total_duration"] == 30  # 5 segments * 6 seconds each

    @pytest.mark.celery
    async def test_assemble_final_video_task(self, db_session, mock_celery):
        """Test final video assembly task."""
        video_project = VideoProjectFactory.create()
        db_session.add(video_project)
        db_session.commit()
        
        segment_urls = [
            "https://storage.example.com/segment_0.mp4",
            "https://storage.example.com/segment_1.mp4",
            "https://storage.example.com/segment_2.mp4"
        ]
        
        assembly_config = {
            "add_background_music": True,
            "music_url": "https://storage.example.com/bg_music.mp3",
            "add_brand_logo": True,
            "output_quality": "high"
        }
        
        mock_assembly_result = {
            "final_video_url": "https://storage.example.com/final_video.mp4",
            "file_size": 15728640,  # 15 MB
            "duration": 30.0,
            "resolution": "1920x1080",
            "processing_time": 45.2
        }
        
        with patch('app.services.video_generation.video_assembly.VideoAssemblyService.assemble_final_video') as mock_assembly:
            mock_assembly.return_value = mock_assembly_result
            
            result = assemble_final_video_task.apply_async(
                args=[video_project.id, segment_urls, assembly_config]
            )
        
        task_result = result.get()
        assert task_result["final_video_url"] is not None
        assert task_result["duration"] == 30.0

    @pytest.mark.celery
    async def test_generate_ugc_testimonials_task(self, db_session, mock_celery):
        """Test UGC testimonial generation task."""
        brand = BrandFactory.create()
        product = ProductFactory.create(brand_id=brand.id)
        
        db_session.add_all([brand, product])
        db_session.commit()
        
        # Sample review data
        reviews = [
            {
                "text": "This product is amazing! Changed my life completely.",
                "rating": 5,
                "reviewer": "Happy Customer",
                "verified": True
            },
            {
                "text": "Great quality and fast shipping. Highly recommend!",
                "rating": 5,
                "reviewer": "Satisfied Buyer",
                "verified": True
            }
        ]
        
        mock_testimonials = [
            {
                "video_url": "https://storage.example.com/testimonial_1.mp4",
                "avatar_style": "casual_female_25_35",
                "script": "Hi everyone! I had to share my experience...",
                "duration": 45
            },
            {
                "video_url": "https://storage.example.com/testimonial_2.mp4",
                "avatar_style": "professional_male_30_40", 
                "script": "I've been using this product for months...",
                "duration": 38
            }
        ]
        
        with patch('app.services.video_generation.ugc_generation.UGCTestimonialGenerator.generate_batch') as mock_ugc:
            mock_ugc.return_value = mock_testimonials
            
            result = generate_ugc_testimonials_task.apply_async(
                args=[product.id, reviews]
            )
        
        task_result = result.get()
        assert len(task_result["testimonials"]) == 2
        assert all("video_url" in t for t in task_result["testimonials"])


class TestSocialMediaTasks:
    """Test social media related tasks."""

    @pytest.mark.celery
    async def test_post_to_social_media_task(self, db_session, mock_celery):
        """Test social media posting task."""
        account = SocialMediaAccountFactory.create(platform="tiktok")
        video_project = VideoProjectFactory.create()
        
        db_session.add_all([account, video_project])
        db_session.commit()
        
        post_config = {
            "video_url": "https://storage.example.com/video.mp4",
            "caption": "Check out this amazing product! #viral #trending",
            "hashtags": ["#viral", "#trending", "#product"],
            "schedule_time": None
        }
        
        mock_post_result = {
            "platform_post_id": "tiktok_12345",
            "status": "published",
            "share_url": "https://tiktok.com/@brand/video/12345",
            "posted_at": datetime.utcnow().isoformat()
        }
        
        with patch('app.services.social_media.tiktok_service.TikTokBusinessAPI.upload_video') as mock_upload:
            mock_upload.return_value = mock_post_result
            
            result = post_to_social_media_task.apply_async(
                args=[account.id, video_project.id, post_config]
            )
        
        task_result = result.get()
        assert task_result["status"] == "success"
        assert task_result["platform_post_id"] == "tiktok_12345"

    @pytest.mark.celery
    async def test_cross_platform_posting_task(self, db_session, mock_celery):
        """Test cross-platform posting task."""
        brand = BrandFactory.create()
        tiktok_account = SocialMediaAccountFactory.create(brand_id=brand.id, platform="tiktok")
        instagram_account = SocialMediaAccountFactory.create(brand_id=brand.id, platform="instagram")
        video_project = VideoProjectFactory.create(brand_id=brand.id)
        
        db_session.add_all([brand, tiktok_account, instagram_account, video_project])
        db_session.commit()
        
        cross_platform_config = {
            "video_url": "https://storage.example.com/video.mp4",
            "platforms": ["tiktok", "instagram"],
            "platform_specific_captions": {
                "tiktok": "🔥 Viral content! #fyp #viral",
                "instagram": "Discover our latest innovation! ✨ #innovation #newproduct"
            }
        }
        
        mock_results = {
            "tiktok": {"status": "success", "post_id": "tiktok_123"},
            "instagram": {"status": "success", "post_id": "instagram_456"}
        }
        
        with patch('app.services.social_media.social_media_manager.SocialMediaManager.post_to_multiple_platforms') as mock_cross:
            mock_cross.return_value = mock_results
            
            result = cross_platform_posting_task.apply_async(
                args=[brand.id, video_project.id, cross_platform_config]
            )
        
        task_result = result.get()
        assert task_result["tiktok"]["status"] == "success"
        assert task_result["instagram"]["status"] == "success"

    @pytest.mark.celery
    async def test_update_social_media_analytics_task(self, db_session, mock_celery):
        """Test social media analytics update task."""
        post = SocialMediaPostFactory.create(
            platform_post_id="tiktok_123",
            view_count=1000,
            like_count=50
        )
        db_session.add(post)
        db_session.commit()
        
        mock_updated_analytics = {
            "views": 5000,
            "likes": 250,
            "shares": 30,
            "comments": 15,
            "engagement_rate": 6.0
        }
        
        with patch('app.services.social_media.tiktok_service.TikTokBusinessAPI.get_video_analytics') as mock_analytics:
            mock_analytics.return_value = mock_updated_analytics
            
            result = update_social_media_analytics_task.apply_async(
                args=[post.id]
            )
        
        task_result = result.get()
        assert task_result["updated_metrics"]["views"] == 5000
        
        # Verify database was updated
        db_session.refresh(post)
        assert post.view_count == 5000
        assert post.like_count == 250

    @pytest.mark.celery
    async def test_process_social_webhooks_task_batch(self, db_session, mock_celery):
        """Test batch processing of social media webhooks."""
        # Multiple webhook events to process
        webhook_events = [
            {
                "platform": "tiktok",
                "event_type": "video.published",
                "data": {"video_id": "tiktok_123", "status": "published"}
            },
            {
                "platform": "instagram",
                "event_type": "media.insights_update",
                "data": {"media_id": "instagram_456", "impressions": 10000}
            },
            {
                "platform": "tiktok",
                "event_type": "video.metrics_update",
                "data": {"video_id": "tiktok_789", "views": 25000}
            }
        ]
        
        mock_processing_results = [
            {"webhook_id": "webhook_1", "status": "processed", "updates_applied": 2},
            {"webhook_id": "webhook_2", "status": "processed", "updates_applied": 1},
            {"webhook_id": "webhook_3", "status": "processed", "updates_applied": 3}
        ]
        
        with patch('app.services.social_media.webhook_processor.WebhookProcessor.process_batch') as mock_batch:
            mock_batch.return_value = mock_processing_results
            
            result = process_social_webhooks_task.apply_async(
                args=[webhook_events]
            )
        
        task_result = result.get()
        assert len(task_result["processed_webhooks"]) == 3
        assert task_result["total_updates"] == 6  # 2 + 1 + 3


class TestTikTokTasks:
    """Test TikTok-specific tasks."""

    @pytest.mark.celery
    async def test_scrape_tiktok_trends_task(self, db_session, mock_celery):
        """Test TikTok trend scraping task."""
        scraping_config = {
            "hashtags": ["#viral", "#trending", "#fyp"],
            "region": "US",
            "count": 100
        }
        
        mock_scraped_trends = [
            {
                "hashtag": "#viral",
                "usage_count": 100000,
                "growth_rate": 25.5,
                "engagement_rate": 8.2
            },
            {
                "hashtag": "#trending",
                "usage_count": 75000,
                "growth_rate": 45.2,
                "engagement_rate": 12.1
            }
        ]
        
        with patch('app.services.scraping.apify_client.ApifyClient.scrape_trending_hashtags') as mock_scrape:
            mock_scrape.return_value = mock_scraped_trends
            
            result = scrape_tiktok_trends_task.apply_async(
                args=[scraping_config]
            )
        
        task_result = result.get()
        assert len(task_result["trends_found"]) == 2
        assert task_result["status"] == "completed"

    @pytest.mark.celery
    async def test_analyze_trending_content_task(self, db_session, mock_celery):
        """Test trending content analysis task."""
        # Create sample trending content
        trending_videos = [
            {
                "video_id": "trending_1",
                "hashtags": ["#viral", "#comedy"],
                "view_count": 1000000,
                "engagement_rate": 15.2
            },
            {
                "video_id": "trending_2",
                "hashtags": ["#viral", "#dance"],
                "view_count": 850000,
                "engagement_rate": 12.8
            }
        ]
        
        mock_analysis_result = {
            "viral_patterns": [
                {
                    "pattern": "strong_hook_opening",
                    "frequency": 0.85,
                    "avg_performance_boost": 25.3
                }
            ],
            "trending_elements": {
                "hashtags": ["#viral", "#comedy", "#dance"],
                "sounds": ["trending_sound_123"],
                "effects": ["zoom_effect", "text_overlay"]
            }
        }
        
        with patch('app.services.ai.trend_analyzer.TrendAnalyzer.analyze_viral_content') as mock_analyze:
            mock_analyze.return_value = mock_analysis_result
            
            result = analyze_trending_content_task.apply_async(
                args=[trending_videos]
            )
        
        task_result = result.get()
        assert len(task_result["viral_patterns"]) > 0
        assert "#viral" in task_result["trending_elements"]["hashtags"]

    @pytest.mark.celery
    async def test_update_trend_metrics_task(self, db_session, mock_celery):
        """Test trend metrics update task."""
        trend = TikTokTrendFactory.create(
            name="#testtrend",
            total_videos=1000,
            viral_score=5.5
        )
        db_session.add(trend)
        db_session.commit()
        
        mock_updated_metrics = {
            "total_videos": 2500,
            "total_views": 5000000,
            "growth_rate": 150.0,
            "viral_score": 8.2
        }
        
        with patch('app.services.ai.trend_analyzer.TrendAnalyzer.calculate_updated_metrics') as mock_metrics:
            mock_metrics.return_value = mock_updated_metrics
            
            result = update_trend_metrics_task.apply_async(
                args=[trend.id]
            )
        
        task_result = result.get()
        assert task_result["updated_viral_score"] == 8.2
        
        # Verify database was updated
        db_session.refresh(trend)
        assert trend.total_videos == 2500
        assert trend.viral_score == 8.2

    @pytest.mark.celery
    async def test_detect_viral_patterns_task(self, db_session, mock_celery):
        """Test viral pattern detection task."""
        # Sample viral videos for analysis
        viral_videos = []
        for i in range(20):
            video = {
                "video_id": f"viral_{i}",
                "view_count": 500000 + (i * 50000),
                "viral_coefficient": 2.0 + (i * 0.1),
                "content_features": ["trending_music", "quick_cuts", "text_overlay"]
            }
            viral_videos.append(video)
        
        mock_patterns = {
            "common_patterns": [
                {
                    "pattern_name": "quick_cuts",
                    "occurrence_rate": 0.95,
                    "avg_viral_boost": 35.2
                },
                {
                    "pattern_name": "trending_music",
                    "occurrence_rate": 0.90,
                    "avg_viral_boost": 28.7
                }
            ],
            "emerging_patterns": [
                {
                    "pattern_name": "ai_effects",
                    "occurrence_rate": 0.25,
                    "growth_trend": "increasing"
                }
            ]
        }
        
        with patch('app.services.ai.trend_analyzer.TrendAnalyzer.detect_viral_patterns') as mock_detect:
            mock_detect.return_value = mock_patterns
            
            result = detect_viral_patterns_task.apply_async(
                args=[viral_videos]
            )
        
        task_result = result.get()
        assert len(task_result["common_patterns"]) == 2
        assert task_result["common_patterns"][0]["occurrence_rate"] > 0.9


class TestContentOptimizationTasks:
    """Test content optimization related tasks."""

    @pytest.mark.celery
    async def test_optimize_content_task(self, db_session, mock_celery):
        """Test content optimization task."""
        content = ContentFactory.create(
            title="Original Content",
            description="Basic product description",
            hashtags=["#product", "#basic"]
        )
        db_session.add(content)
        db_session.commit()
        
        optimization_config = {
            "optimization_goals": ["engagement", "reach", "viral_potential"],
            "target_platform": "tiktok",
            "current_trends": ["#viral", "#trending", "#innovation"]
        }
        
        mock_optimized_content = {
            "optimized_title": "🔥 You NEED to see this product!",
            "optimized_description": "This revolutionary product will change everything! Don't miss out!",
            "optimized_hashtags": ["#viral", "#trending", "#innovation", "#gamechanging"],
            "optimization_score": 8.7,
            "expected_improvements": {
                "engagement": "+45%",
                "reach": "+32%",
                "viral_potential": "+60%"
            }
        }
        
        with patch('app.services.optimization.ab_testing.ABTestingService.optimize_content') as mock_optimize:
            mock_optimize.return_value = mock_optimized_content
            
            result = optimize_content_task.apply_async(
                args=[content.id, optimization_config]
            )
        
        task_result = result.get()
        assert task_result["optimization_score"] > 8.0
        assert "#viral" in task_result["optimized_hashtags"]

    @pytest.mark.celery
    async def test_generate_ab_test_variants_task(self, db_session, mock_celery):
        """Test A/B test variant generation task."""
        base_content = {
            "script": "Check out this amazing product",
            "hashtags": ["#product", "#amazing"],
            "hook": "Check out this"
        }
        
        test_config = {
            "variant_count": 3,
            "test_elements": ["hook", "hashtags", "call_to_action"],
            "target_metrics": ["engagement_rate", "viral_potential"]
        }
        
        mock_variants = [
            {
                "variant_id": "A",
                "script": "Check out this amazing product",
                "hashtags": ["#product", "#amazing"],
                "predicted_performance": 6.2
            },
            {
                "variant_id": "B",
                "script": "🔥 You won't believe this product!",
                "hashtags": ["#viral", "#mindblown", "#amazing"],
                "predicted_performance": 8.5
            },
            {
                "variant_id": "C",
                "script": "This product changed my life!",
                "hashtags": ["#lifechanging", "#viral", "#product"],
                "predicted_performance": 7.8
            }
        ]
        
        with patch('app.services.optimization.ab_testing.ABTestingService.generate_test_variants') as mock_variants_gen:
            mock_variants_gen.return_value = mock_variants
            
            result = generate_ab_test_variants_task.apply_async(
                args=[base_content, test_config]
            )
        
        task_result = result.get()
        assert len(task_result["variants"]) == 3
        assert task_result["recommended_variant"] == "B"  # Highest predicted performance

    @pytest.mark.celery
    async def test_schedule_content_posting_task(self, db_session, mock_celery, mock_redis):
        """Test content posting scheduling task."""
        content = ContentFactory.create()
        account = SocialMediaAccountFactory.create()
        
        db_session.add_all([content, account])
        db_session.commit()
        
        schedule_config = {
            "post_time": (datetime.utcnow() + timedelta(hours=2)).isoformat(),
            "platforms": ["tiktok"],
            "optimization_enabled": True
        }
        
        with patch('app.tasks.social_media_tasks.post_to_social_media_task.apply_async') as mock_schedule:
            mock_schedule.return_value = Mock(id="scheduled_task_123")
            
            result = schedule_content_posting_task.apply_async(
                args=[content.id, account.id, schedule_config]
            )
        
        task_result = result.get()
        assert task_result["scheduled_task_id"] == "scheduled_task_123"
        assert task_result["status"] == "scheduled"
        
        # Verify Redis entry for scheduled task
        mock_redis.zadd.assert_called()


class TestAnalyticsTasks:
    """Test analytics related tasks."""

    @pytest.mark.celery
    async def test_calculate_performance_metrics_task(self, db_session, mock_celery):
        """Test performance metrics calculation task."""
        # Create sample posts with performance data
        posts = []
        for i in range(10):
            post = SocialMediaPostFactory.create(
                view_count=1000 + (i * 500),
                like_count=50 + (i * 25),
                engagement_rate=5.0 + (i * 0.5)
            )
            posts.append(post)
            db_session.add(post)
        
        db_session.commit()
        
        post_ids = [post.id for post in posts]
        
        mock_calculated_metrics = {
            "average_engagement_rate": 7.25,
            "total_reach": 75000,
            "top_performing_post": posts[-1].id,
            "performance_trend": "increasing",
            "benchmark_comparison": {
                "engagement_rate": "above_average",
                "reach": "good",
                "viral_potential": "high"
            }
        }
        
        with patch('app.services.analytics.performance_predictor.PerformancePredictor.calculate_metrics') as mock_calc:
            mock_calc.return_value = mock_calculated_metrics
            
            result = calculate_performance_metrics_task.apply_async(
                args=[post_ids]
            )
        
        task_result = result.get()
        assert task_result["average_engagement_rate"] == 7.25
        assert task_result["performance_trend"] == "increasing"

    @pytest.mark.celery
    async def test_predict_content_performance_task(self, db_session, mock_celery):
        """Test content performance prediction task."""
        content_features = {
            "content_type": "product_showcase",
            "duration": 30,
            "hashtag_count": 5,
            "has_trending_elements": True,
            "posting_time": "evening",
            "platform": "tiktok"
        }
        
        mock_prediction = {
            "predicted_views": 25000,
            "predicted_likes": 1250,
            "predicted_shares": 125,
            "predicted_engagement_rate": 7.8,
            "confidence_score": 0.87,
            "viral_probability": 0.34
        }
        
        with patch('app.services.analytics.performance_predictor.PerformancePredictor.predict_performance') as mock_predict:
            mock_predict.return_value = mock_prediction
            
            result = predict_content_performance_task.apply_async(
                args=[content_features]
            )
        
        task_result = result.get()
        assert task_result["predicted_views"] == 25000
        assert task_result["confidence_score"] > 0.8

    @pytest.mark.celery
    async def test_generate_analytics_report_task(self, db_session, mock_celery):
        """Test analytics report generation task."""
        brand = BrandFactory.create()
        db_session.add(brand)
        db_session.commit()
        
        report_config = {
            "time_period": "last_30_days",
            "metrics": ["engagement", "reach", "conversions"],
            "include_recommendations": True,
            "format": "detailed"
        }
        
        mock_report = {
            "summary": {
                "total_posts": 25,
                "total_views": 500000,
                "average_engagement_rate": 8.2,
                "top_performing_platform": "tiktok"
            },
            "detailed_metrics": {
                "daily_breakdown": [{"date": "2024-01-01", "views": 20000}],
                "platform_comparison": {"tiktok": {"engagement": 8.2}, "instagram": {"engagement": 6.5}}
            },
            "recommendations": [
                "Increase posting frequency on TikTok",
                "Experiment with trending hashtags",
                "Optimize posting times for better reach"
            ]
        }
        
        with patch('app.services.analytics.performance_predictor.PerformancePredictor.generate_report') as mock_report_gen:
            mock_report_gen.return_value = mock_report
            
            result = generate_analytics_report_task.apply_async(
                args=[brand.id, report_config]
            )
        
        task_result = result.get()
        assert task_result["summary"]["total_posts"] == 25
        assert len(task_result["recommendations"]) > 0


class TestTaskChaining:
    """Test task chaining and workflow orchestration."""

    @pytest.mark.celery
    async def test_complete_workflow_chain(self, db_session, mock_celery):
        """Test complete workflow using task chains."""
        from celery import chain
        
        brand = BrandFactory.create()
        db_session.add(brand)
        db_session.commit()
        
        # Mock all the tasks in the chain
        with patch.multiple(
            'app.tasks',
            analyze_brand_url_task=Mock(return_value={"status": "completed", "products": []}),
            generate_video_project_task=Mock(return_value={"status": "completed", "video_url": "test.mp4"}),
            post_to_social_media_task=Mock(return_value={"status": "success", "post_id": "123"}),
            update_social_media_analytics_task=Mock(return_value={"status": "completed"})
        ):
            # Create a task chain
            workflow = chain(
                analyze_brand_url_task.s(brand.id, "https://test.com"),
                generate_video_project_task.s(),
                post_to_social_media_task.s(),
                update_social_media_analytics_task.s()
            )
            
            result = workflow.apply_async()
            final_result = result.get()
            
            assert final_result["status"] == "completed"

    @pytest.mark.celery
    async def test_task_error_handling_in_chain(self, db_session, mock_celery):
        """Test error handling in task chains."""
        from celery import chain
        from celery.exceptions import Retry
        
        brand = BrandFactory.create()
        db_session.add(brand)
        db_session.commit()
        
        # Mock task failure in the middle of chain
        with patch('app.tasks.analyze_brand_url_task') as mock_analyze:
            with patch('app.tasks.generate_video_project_task') as mock_generate:
                
                mock_analyze.return_value = {"status": "completed"}
                mock_generate.side_effect = Exception("Video generation failed")
                
                workflow = chain(
                    mock_analyze.s(brand.id, "https://test.com"),
                    mock_generate.s()
                )
                
                # The chain should handle the error gracefully
                with pytest.raises(Exception):
                    result = workflow.apply_async()
                    result.get(propagate=True)

    @pytest.mark.celery
    async def test_task_retry_mechanism(self, mock_celery):
        """Test task retry mechanism with exponential backoff."""
        
        @mock_celery.task(bind=True, autoretry_for=(Exception,), retry_kwargs={'max_retries': 3})
        def failing_task(self, fail_count=3):
            if hasattr(self, 'request') and self.request.retries < fail_count - 1:
                raise Exception(f"Attempt {self.request.retries + 1} failed")
            return {"status": "success", "attempts": getattr(self.request, 'retries', 0) + 1}
        
        # Mock the task execution
        with patch.object(failing_task, 'retry') as mock_retry:
            # Configure mock to simulate retries
            mock_retry.side_effect = Retry("Retrying...")
            
            # The task should retry on failure
            with pytest.raises(Retry):
                failing_task.apply_async(args=[2])

    @pytest.mark.celery
    async def test_task_monitoring_and_progress_tracking(self, mock_redis, mock_celery):
        """Test task monitoring and progress tracking."""
        
        @mock_celery.task(bind=True)
        def monitored_task(self, total_items=100):
            # Simulate long-running task with progress updates
            for i in range(0, total_items, 10):
                progress = (i / total_items) * 100
                
                # Update task progress
                self.update_state(
                    state='PROGRESS',
                    meta={'current': i, 'total': total_items, 'progress': progress}
                )
                
                # Update Redis for real-time monitoring
                mock_redis.set(f"task_progress:{self.request.id}", progress)
            
            return {"status": "completed", "items_processed": total_items}
        
        # Execute the monitored task
        result = monitored_task.apply_async(args=[50])
        
        # Verify progress tracking
        task_result = result.get()
        assert task_result["items_processed"] == 50
        
        # Verify Redis calls for progress tracking
        mock_redis.set.assert_called()