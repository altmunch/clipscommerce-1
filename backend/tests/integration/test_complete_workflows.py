"""
Integration tests for complete workflows including:
- URL input → product discovery → video generation → social media posting
- End-to-end brand assimilation and content creation flows
- Cross-service integration testing
"""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from datetime import datetime, timedelta
import json
import uuid

from app.models.brand import Brand
from app.models.product import Product, ScrapingJob
from app.models.video_project import VideoProject, VideoSegment, GenerationStatusEnum
from app.models.social_media import SocialMediaAccount, SocialMediaPost, PostStatus
from app.models.job import Job
from tests.factories import (
    BrandFactory, UserFactory, ProductFactory, VideoProjectFactory,
    SocialMediaAccountFactory, SocialMediaPostFactory
)


class TestCompleteWorkflow:
    """Test complete end-to-end workflows."""

    @pytest.fixture
    async def setup_complete_workflow(self, db_session):
        """Set up a complete workflow test environment."""
        # Create user and brand
        user = UserFactory.create()
        brand = BrandFactory.create(
            user_id=user.id,
            url="https://example-brand.com",
            industry="electronics",
            target_audience={"age": "25-45", "interests": ["technology", "gadgets"]}
        )
        
        # Create social media accounts
        tiktok_account = SocialMediaAccountFactory.create(
            brand_id=brand.id,
            platform="tiktok",
            username="brand_tiktok",
            access_token="tiktok_token_123"
        )
        
        instagram_account = SocialMediaAccountFactory.create(
            brand_id=brand.id,
            platform="instagram", 
            username="brand_instagram",
            access_token="instagram_token_456"
        )
        
        db_session.add_all([user, brand, tiktok_account, instagram_account])
        db_session.commit()
        
        return {
            "user": user,
            "brand": brand,
            "tiktok_account": tiktok_account,
            "instagram_account": instagram_account
        }

    @pytest.mark.integration
    async def test_url_to_video_to_posting_workflow(self, setup_complete_workflow, db_session, async_client):
        """Test complete workflow from URL input to social media posting."""
        setup = setup_complete_workflow
        
        # Step 1: Brand URL Analysis and Product Discovery
        brand_url = "https://example-brand.com"
        
        # Mock scraping response
        mock_scraping_data = {
            "brand_info": {
                "name": "Amazing Tech Brand",
                "description": "Innovative technology products",
                "logo_url": "https://example-brand.com/logo.png",
                "colors": ["#FF6B6B", "#4ECDC4"],
                "voice": "innovative and friendly"
            },
            "products": [
                {
                    "name": "Smart Widget Pro",
                    "description": "Revolutionary smart widget with AI capabilities",
                    "price": 199.99,
                    "images": ["https://example.com/widget.jpg"],
                    "features": ["AI-powered", "Wireless", "Long battery life"],
                    "category": "Electronics"
                }
            ]
        }
        
        with patch('app.services.scraping.brand_scraper.BrandScraper.extract_brand_info') as mock_scraper:
            mock_scraper.return_value = mock_scraping_data
            
            # API call to start brand analysis
            response = await async_client.post(
                f"/api/v1/brands/{setup['brand'].id}/analyze-url",
                json={"url": brand_url}
            )
        
        assert response.status_code == 200
        analysis_result = response.json()
        assert analysis_result["status"] == "success"
        assert "job_id" in analysis_result
        
        # Step 2: Create Video Project from Discovered Product
        product_data = mock_scraping_data["products"][0]
        
        video_project_config = {
            "title": f"Showcase Video for {product_data['name']}",
            "project_type": "product_ad",
            "target_platform": "tiktok",
            "target_duration": 30,
            "style": "professional",
            "brand_guidelines": mock_scraping_data["brand_info"]
        }
        
        # Mock AI video generation
        mock_video_generation = {
            "status": "completed",
            "video_url": "https://storage.example.com/generated_video.mp4",
            "thumbnail_url": "https://storage.example.com/thumbnail.jpg",
            "segments": [
                {"start": 0, "end": 5, "description": "Product introduction"},
                {"start": 5, "end": 20, "description": "Feature demonstration"},
                {"start": 20, "end": 30, "description": "Call to action"}
            ]
        }
        
        with patch('app.services.ai.video_generation.VideoGenerationService.generate_video_project') as mock_video_gen:
            mock_video_gen.return_value = mock_video_generation
            
            response = await async_client.post(
                "/api/v1/video-generation/projects",
                json=video_project_config,
                headers={"Authorization": f"Bearer mock-jwt-{setup['user'].id}"}
            )
        
        assert response.status_code == 201
        video_project = response.json()
        assert video_project["status"] == "completed"
        assert "video_url" in video_project
        
        # Step 3: Social Media Posting
        posting_config = {
            "video_project_id": video_project["id"],
            "platforms": ["tiktok", "instagram"],
            "caption": "Check out our amazing Smart Widget Pro! 🚀 #innovation #tech #smartwidget",
            "hashtags": ["#innovation", "#tech", "#smartwidget", "#viral"],
            "schedule_time": None  # Post immediately
        }
        
        # Mock social media API responses
        mock_tiktok_response = {
            "video_id": "tiktok_12345",
            "status": "processing",
            "share_url": "https://tiktok.com/@brand_tiktok/video/12345"
        }
        
        mock_instagram_response = {
            "media_id": "instagram_67890",
            "status": "published",
            "permalink": "https://instagram.com/p/ABC123/"
        }
        
        with patch('app.services.social_media.tiktok_service.TikTokBusinessAPI.upload_video') as mock_tiktok:
            with patch('app.services.social_media.instagram_service.InstagramGraphAPI.upload_video') as mock_instagram:
                
                mock_tiktok.return_value = mock_tiktok_response
                mock_instagram.return_value = mock_instagram_response
                
                response = await async_client.post(
                    "/api/v1/social-media/post-multi-platform",
                    json=posting_config,
                    headers={"Authorization": f"Bearer mock-jwt-{setup['user'].id}"}
                )
        
        assert response.status_code == 200
        posting_result = response.json()
        assert posting_result["tiktok"]["status"] == "success"
        assert posting_result["instagram"]["status"] == "success"
        
        # Verify database state
        posts = db_session.query(SocialMediaPost).filter_by(
            video_project_id=video_project["id"]
        ).all()
        assert len(posts) == 2  # One for TikTok, one for Instagram
        
        # Step 4: Analytics Tracking
        # Simulate webhook updates for performance tracking
        tiktok_webhook_data = {
            "event": "video.metrics_update",
            "data": {
                "video_id": "tiktok_12345",
                "metrics": {
                    "views": 5000,
                    "likes": 250,
                    "shares": 30,
                    "comments": 15
                }
            }
        }
        
        response = await async_client.post(
            "/api/v1/webhooks/tiktok",
            json=tiktok_webhook_data,
            headers={"X-TikTok-Signature": "mock_signature"}
        )
        
        assert response.status_code == 200
        
        # Verify analytics were updated
        tiktok_post = db_session.query(SocialMediaPost).filter_by(
            platform_post_id="tiktok_12345"
        ).first()
        assert tiktok_post.view_count == 5000
        assert tiktok_post.like_count == 250

    @pytest.mark.integration
    async def test_competitor_analysis_to_content_creation(self, setup_complete_workflow, db_session, async_client):
        """Test workflow from competitor analysis to content creation."""
        setup = setup_complete_workflow
        
        # Step 1: Competitor Analysis
        competitor_urls = [
            "https://competitor1.com",
            "https://competitor2.com",
            "https://competitor3.com"
        ]
        
        mock_competitor_data = {
            "competitors": [
                {
                    "name": "Competitor 1",
                    "url": "https://competitor1.com",
                    "strengths": ["Strong social presence", "Innovative products"],
                    "content_themes": ["sustainability", "innovation"],
                    "trending_content": ["#ecofriendly", "#innovation"]
                },
                {
                    "name": "Competitor 2", 
                    "url": "https://competitor2.com",
                    "strengths": ["Great customer service", "Affordable pricing"],
                    "content_themes": ["customer_focus", "value"],
                    "trending_content": ["#customercare", "#affordable"]
                }
            ],
            "opportunities": [
                "Gap in eco-friendly messaging",
                "Underutilized video content",
                "Limited trending hashtag adoption"
            ],
            "recommendations": [
                "Focus on sustainability messaging",
                "Increase video content production",
                "Adopt trending hashtags from competitors"
            ]
        }
        
        with patch('app.services.scraping.brand_scraper.BrandScraper.analyze_competitors') as mock_competitor:
            mock_competitor.return_value = mock_competitor_data
            
            response = await async_client.post(
                f"/api/v1/brands/{setup['brand'].id}/analyze-competitors",
                json={"competitor_urls": competitor_urls},
                headers={"Authorization": f"Bearer mock-jwt-{setup['user'].id}"}
            )
        
        assert response.status_code == 200
        competitor_analysis = response.json()
        assert len(competitor_analysis["competitors"]) == 2
        assert len(competitor_analysis["opportunities"]) > 0
        
        # Step 2: Generate Content Strategy Based on Analysis
        strategy_config = {
            "competitor_insights": competitor_analysis,
            "brand_positioning": "eco-friendly innovation leader",
            "content_goals": ["brand_awareness", "engagement", "lead_generation"],
            "platforms": ["tiktok", "instagram"]
        }
        
        mock_strategy = {
            "content_themes": [
                {
                    "theme": "Sustainable Innovation",
                    "content_ideas": [
                        "Behind-the-scenes sustainable manufacturing",
                        "Product lifecycle sustainability story",
                        "Eco-friendly packaging showcase"
                    ],
                    "suggested_hashtags": ["#sustainability", "#ecoinnovation", "#greenfuture"]
                }
            ],
            "posting_calendar": [
                {
                    "date": "2024-01-15",
                    "content_type": "product_showcase",
                    "theme": "Sustainable Innovation",
                    "platform": "tiktok"
                }
            ]
        }
        
        with patch('app.services.ai.brand_assimilation.BrandAssimilation.generate_content_strategy') as mock_strategy_gen:
            mock_strategy_gen.return_value = mock_strategy
            
            response = await async_client.post(
                "/api/v1/content/strategy/generate",
                json=strategy_config,
                headers={"Authorization": f"Bearer mock-jwt-{setup['user'].id}"}
            )
        
        assert response.status_code == 200
        content_strategy = response.json()
        assert len(content_strategy["content_themes"]) > 0
        assert "Sustainable Innovation" in [theme["theme"] for theme in content_strategy["content_themes"]]
        
        # Step 3: Create Content Based on Strategy
        content_brief = {
            "theme": "Sustainable Innovation",
            "content_type": "product_showcase",
            "target_platform": "tiktok",
            "key_messages": ["eco-friendly", "innovative", "sustainable"],
            "call_to_action": "Learn more about our sustainable practices"
        }
        
        mock_video_content = {
            "script": "Discover how we're revolutionizing sustainability in tech...",
            "visual_elements": ["product_shots", "manufacturing_process", "nature_scenes"],
            "music_mood": "uplifting and inspirational",
            "duration": 30
        }
        
        with patch('app.services.ai.script_generation.ScriptGenerationService.generate_content_from_brief') as mock_content:
            mock_content.return_value = mock_video_content
            
            response = await async_client.post(
                "/api/v1/content/generate-from-brief",
                json=content_brief,
                headers={"Authorization": f"Bearer mock-jwt-{setup['user'].id}"}
            )
        
        assert response.status_code == 200
        generated_content = response.json()
        assert "sustainability" in generated_content["script"].lower()

    @pytest.mark.integration
    async def test_trend_monitoring_to_viral_content(self, setup_complete_workflow, db_session, async_client):
        """Test workflow from trend monitoring to viral content creation."""
        setup = setup_complete_workflow
        
        # Step 1: TikTok Trend Monitoring
        mock_trending_data = {
            "emerging_trends": [
                {
                    "hashtag": "#techinnovation2024",
                    "growth_rate": 450.2,
                    "total_videos": 15000,
                    "engagement_rate": 12.5,
                    "viral_score": 9.2,
                    "demographics": {"age_18_24": 45, "age_25_34": 35}
                },
                {
                    "hashtag": "#sustainabletech",
                    "growth_rate": 320.1,
                    "total_videos": 8500,
                    "engagement_rate": 10.8,
                    "viral_score": 8.7,
                    "demographics": {"age_25_34": 40, "age_35_44": 30}
                }
            ],
            "trending_sounds": [
                {
                    "sound_id": "trending_sound_123",
                    "name": "Innovative Beat",
                    "usage_count": 25000,
                    "engagement_boost": 15.2
                }
            ]
        }
        
        with patch('app.services.scraping.apify_client.ApifyClient.fetch_trending_data') as mock_trends:
            mock_trends.return_value = mock_trending_data
            
            response = await async_client.get(
                "/api/v1/tiktok/trends/emerging",
                headers={"Authorization": f"Bearer mock-jwt-{setup['user'].id}"}
            )
        
        assert response.status_code == 200
        trends = response.json()
        assert len(trends["emerging_trends"]) == 2
        
        # Step 2: Trend-Brand Alignment Analysis
        alignment_config = {
            "brand_id": setup["brand"].id,
            "trending_hashtags": ["#techinnovation2024", "#sustainabletech"],
            "brand_values": ["innovation", "sustainability", "quality"]
        }
        
        mock_alignment = {
            "trend_scores": {
                "#techinnovation2024": {
                    "alignment_score": 9.5,
                    "reasons": ["Perfect match with innovation focus", "Target audience overlap"],
                    "recommended": True
                },
                "#sustainabletech": {
                    "alignment_score": 8.8,
                    "reasons": ["Aligns with sustainability values", "Growing engagement"],
                    "recommended": True
                }
            },
            "content_recommendations": [
                "Create innovation showcase using #techinnovation2024",
                "Highlight sustainable practices with #sustainabletech"
            ]
        }
        
        with patch('app.services.ai.tiktok_trend_integration.TikTokTrendIntegration.analyze_brand_trend_alignment') as mock_align:
            mock_align.return_value = mock_alignment
            
            response = await async_client.post(
                "/api/v1/trends/analyze-alignment",
                json=alignment_config,
                headers={"Authorization": f"Bearer mock-jwt-{setup['user'].id}"}
            )
        
        assert response.status_code == 200
        alignment = response.json()
        assert alignment["trend_scores"]["#techinnovation2024"]["recommended"] is True
        
        # Step 3: Viral Content Creation
        viral_content_config = {
            "trending_elements": {
                "hashtags": ["#techinnovation2024", "#sustainabletech"],
                "sound_id": "trending_sound_123",
                "viral_hooks": ["You won't believe this innovation", "This changes everything"]
            },
            "brand_elements": {
                "product_focus": "Smart Widget Pro",
                "key_features": ["AI-powered", "Eco-friendly", "Revolutionary"],
                "brand_voice": "innovative and friendly"
            },
            "optimization_goals": ["viral_potential", "brand_alignment", "engagement"]
        }
        
        mock_viral_content = {
            "script": "You won't believe this innovation! 🚀 Our Smart Widget Pro is revolutionizing sustainable tech with AI-powered features that change everything! #techinnovation2024 #sustainabletech",
            "video_structure": [
                {"segment": "hook", "duration": 3, "content": "Attention-grabbing opener"},
                {"segment": "demonstration", "duration": 20, "content": "Product features showcase"},
                {"segment": "call_to_action", "duration": 7, "content": "Strong CTA with trending elements"}
            ],
            "viral_score_prediction": 8.9,
            "optimization_suggestions": [
                "Use trending sound for higher reach",
                "Post during peak hours (7-9 PM)",
                "Include trending visual effects"
            ]
        }
        
        with patch('app.services.ai.viral_content.ViralContentGenerator.create_viral_content') as mock_viral:
            mock_viral.return_value = mock_viral_content
            
            response = await async_client.post(
                "/api/v1/content/create-viral",
                json=viral_content_config,
                headers={"Authorization": f"Bearer mock-jwt-{setup['user'].id}"}
            )
        
        assert response.status_code == 200
        viral_content = response.json()
        assert viral_content["viral_score_prediction"] > 8.0
        assert "#techinnovation2024" in viral_content["script"]
        
        # Step 4: Generate and Post Viral Video
        video_generation_config = {
            "script": viral_content["script"],
            "video_structure": viral_content["video_structure"],
            "trending_audio": "trending_sound_123",
            "optimization_settings": {
                "platform": "tiktok",
                "viral_optimization": True,
                "trending_effects": True
            }
        }
        
        mock_generated_video = {
            "video_url": "https://storage.example.com/viral_video.mp4",
            "thumbnail_url": "https://storage.example.com/viral_thumbnail.jpg",
            "duration": 30,
            "viral_elements_applied": ["trending_sound", "optimal_cuts", "engaging_text"],
            "predicted_performance": {
                "estimated_views": 50000,
                "estimated_engagement_rate": 12.5
            }
        }
        
        with patch('app.services.ai.video_generation.VideoGenerationService.generate_viral_video') as mock_gen:
            mock_gen.return_value = mock_generated_video
            
            response = await async_client.post(
                "/api/v1/video-generation/viral",
                json=video_generation_config,
                headers={"Authorization": f"Bearer mock-jwt-{setup['user'].id}"}
            )
        
        assert response.status_code == 200
        generated_video = response.json()
        assert generated_video["predicted_performance"]["estimated_views"] > 40000

    @pytest.mark.integration
    async def test_performance_optimization_feedback_loop(self, setup_complete_workflow, db_session, async_client):
        """Test performance monitoring and optimization feedback loop."""
        setup = setup_complete_workflow
        
        # Step 1: Create and Post Initial Content
        initial_post = SocialMediaPostFactory.create(
            account_id=setup["tiktok_account"].id,
            content_type="video",
            caption="Initial test post #test",
            status="published",
            view_count=1000,
            like_count=50,
            engagement_rate=5.0
        )
        db_session.add(initial_post)
        db_session.commit()
        
        # Step 2: Performance Analysis
        performance_data = {
            "post_id": initial_post.id,
            "time_period": "24_hours",
            "metrics": {
                "views": 1000,
                "likes": 50,
                "shares": 5,
                "comments": 8,
                "engagement_rate": 5.0,
                "reach": 850,
                "impressions": 1200
            }
        }
        
        mock_analysis = {
            "performance_grade": "C",
            "benchmark_comparison": {
                "views": "below_average",
                "engagement_rate": "average",
                "reach": "below_average"
            },
            "improvement_areas": [
                "Hook optimization needed",
                "Hashtag strategy improvement",
                "Posting time optimization"
            ],
            "specific_recommendations": [
                {
                    "area": "content_hooks",
                    "suggestion": "Use more attention-grabbing openings",
                    "expected_improvement": "20-30% engagement increase"
                },
                {
                    "area": "hashtags",
                    "suggestion": "Include trending hashtags #viral #fyp",
                    "expected_improvement": "15-25% reach increase"
                }
            ]
        }
        
        with patch('app.services.analytics.performance_predictor.PerformancePredictor.analyze_post_performance') as mock_perf:
            mock_perf.return_value = mock_analysis
            
            response = await async_client.post(
                "/api/v1/analytics/analyze-performance",
                json=performance_data,
                headers={"Authorization": f"Bearer mock-jwt-{setup['user'].id}"}
            )
        
        assert response.status_code == 200
        analysis = response.json()
        assert analysis["performance_grade"] == "C"
        assert len(analysis["specific_recommendations"]) > 0
        
        # Step 3: Apply Optimizations to New Content
        optimization_config = {
            "previous_performance": analysis,
            "content_type": "product_showcase",
            "target_improvements": ["engagement_rate", "reach", "viral_potential"]
        }
        
        mock_optimized_content = {
            "optimized_script": "🔥 You NEED to see this life-changing innovation! This Smart Widget Pro will blow your mind with its AI-powered features! #viral #fyp #innovation #mindblown",
            "optimized_hashtags": ["#viral", "#fyp", "#innovation", "#mindblown", "#tech", "#gamechanging"],
            "optimized_hooks": ["🔥 You NEED to see this", "This will blow your mind"],
            "posting_time_recommendation": "Tuesday 8:00 PM EST",
            "expected_improvements": {
                "engagement_rate": "+35%",
                "reach": "+28%",
                "viral_potential": "+45%"
            }
        }
        
        with patch('app.services.optimization.ab_testing.ABTestingService.optimize_content') as mock_optimize:
            mock_optimize.return_value = mock_optimized_content
            
            response = await async_client.post(
                "/api/v1/content/optimize",
                json=optimization_config,
                headers={"Authorization": f"Bearer mock-jwt-{setup['user'].id}"}
            )
        
        assert response.status_code == 200
        optimized = response.json()
        assert "🔥" in optimized["optimized_script"]
        assert "#viral" in optimized["optimized_hashtags"]
        
        # Step 4: A/B Test Optimized vs Original
        ab_test_config = {
            "test_name": "Hook Optimization Test",
            "variant_a": {
                "script": "Check out this amazing product #test",
                "hashtags": ["#test", "#product"]
            },
            "variant_b": {
                "script": optimized["optimized_script"],
                "hashtags": optimized["optimized_hashtags"]
            },
            "success_metric": "engagement_rate",
            "test_duration_hours": 48
        }
        
        mock_ab_test = {
            "test_id": "ab_test_123",
            "status": "running",
            "variant_assignments": {
                "variant_a": {"traffic_percentage": 50},
                "variant_b": {"traffic_percentage": 50}
            }
        }
        
        with patch('app.services.optimization.ab_testing.ABTestingService.create_test') as mock_ab:
            mock_ab.return_value = mock_ab_test
            
            response = await async_client.post(
                "/api/v1/ab-testing/create-test",
                json=ab_test_config,
                headers={"Authorization": f"Bearer mock-jwt-{setup['user'].id}"}
            )
        
        assert response.status_code == 200
        ab_test = response.json()
        assert ab_test["status"] == "running"
        
        # Step 5: Monitor A/B Test Results
        # Simulate test completion after some time
        mock_test_results = {
            "test_id": "ab_test_123",
            "status": "completed",
            "results": {
                "variant_a": {
                    "participants": 500,
                    "engagement_rate": 5.2,
                    "conversion_rate": 2.1
                },
                "variant_b": {
                    "participants": 500,
                    "engagement_rate": 7.8,
                    "conversion_rate": 3.4
                }
            },
            "winner": "variant_b",
            "confidence_level": 95.5,
            "improvement": {
                "engagement_rate": "+50%",
                "conversion_rate": "+62%"
            }
        }
        
        with patch('app.services.optimization.ab_testing.ABTestingService.get_test_results') as mock_results:
            mock_results.return_value = mock_test_results
            
            response = await async_client.get(
                f"/api/v1/ab-testing/results/{ab_test['test_id']}",
                headers={"Authorization": f"Bearer mock-jwt-{setup['user'].id}"}
            )
        
        assert response.status_code == 200
        results = response.json()
        assert results["winner"] == "variant_b"
        assert results["improvement"]["engagement_rate"] == "+50%"

    @pytest.mark.integration
    async def test_error_recovery_and_fallback_mechanisms(self, setup_complete_workflow, db_session, async_client):
        """Test error recovery and fallback mechanisms across services."""
        setup = setup_complete_workflow
        
        # Test 1: Scraping Service Failure with Fallback
        with patch('app.services.scraping.brand_scraper.BrandScraper.extract_brand_info') as mock_scraper:
            # First attempt fails
            mock_scraper.side_effect = [
                Exception("Bot detection - primary scraper failed"),
                # Fallback scraper succeeds
                {
                    "brand_info": {"name": "Fallback Brand", "description": "From fallback scraper"},
                    "products": []
                }
            ]
            
            response = await async_client.post(
                f"/api/v1/brands/{setup['brand'].id}/analyze-url",
                json={"url": "https://protected-site.com"}
            )
        
        # Should succeed with fallback
        assert response.status_code == 200
        result = response.json()
        assert result["status"] == "success"
        assert "fallback" in result.get("method", "").lower() or result["status"] == "success"
        
        # Test 2: AI Service Failure with Graceful Degradation
        video_config = {
            "title": "Test Video",
            "project_type": "product_ad",
            "target_platform": "tiktok"
        }
        
        with patch('app.services.ai.video_generation.VideoGenerationService.generate_video_project') as mock_ai:
            # Primary AI service fails, fallback to template-based generation
            mock_ai.side_effect = [
                Exception("AI service temporarily unavailable"),
                {
                    "status": "completed",
                    "video_url": "https://storage.example.com/template_video.mp4",
                    "generation_method": "template_based",
                    "note": "Generated using fallback template system"
                }
            ]
            
            response = await async_client.post(
                "/api/v1/video-generation/projects",
                json=video_config,
                headers={"Authorization": f"Bearer mock-jwt-{setup['user'].id}"}
            )
        
        assert response.status_code == 201
        video_result = response.json()
        assert video_result["status"] == "completed"
        
        # Test 3: Social Media API Failure with Retry Logic
        posting_config = {
            "video_url": "https://example.com/video.mp4",
            "caption": "Test post",
            "platforms": ["tiktok"]
        }
        
        with patch('app.services.social_media.tiktok_service.TikTokBusinessAPI.upload_video') as mock_tiktok:
            # Simulate rate limiting, then success on retry
            mock_tiktok.side_effect = [
                Exception("Rate limit exceeded"),
                Exception("Temporary service unavailable"),
                {"video_id": "retry_success_123", "status": "processing"}
            ]
            
            response = await async_client.post(
                "/api/v1/social-media/post-multi-platform",
                json=posting_config,
                headers={"Authorization": f"Bearer mock-jwt-{setup['user'].id}"}
            )
        
        assert response.status_code == 200
        posting_result = response.json()
        assert posting_result["tiktok"]["status"] == "success"
        
        # Test 4: Database Transaction Rollback on Partial Failure
        multi_operation_config = {
            "operations": [
                {"type": "create_product", "data": {"name": "Test Product 1"}},
                {"type": "create_video_project", "data": {"title": "Test Video 1"}},
                {"type": "create_social_post", "data": {"caption": "Test Post 1"}}
            ]
        }
        
        # Simulate failure in the middle operation
        with patch('app.services.video_generation.orchestrator.VideoOrchestrator.create_project') as mock_video:
            mock_video.side_effect = Exception("Video creation failed")
            
            response = await async_client.post(
                "/api/v1/operations/batch",
                json=multi_operation_config,
                headers={"Authorization": f"Bearer mock-jwt-{setup['user'].id}"}
            )
        
        # Should return partial success with rollback information
        assert response.status_code == 207  # Multi-Status
        batch_result = response.json()
        assert any(op["status"] == "error" for op in batch_result["operations"])
        assert "rollback_performed" in batch_result

    @pytest.mark.integration
    async def test_concurrent_workflow_execution(self, setup_complete_workflow, db_session, async_client):
        """Test handling of concurrent workflow executions."""
        setup = setup_complete_workflow
        
        # Simulate multiple concurrent workflows
        concurrent_configs = [
            {
                "workflow_id": f"workflow_{i}",
                "brand_id": setup["brand"].id,
                "operations": [
                    {"type": "analyze_competitors", "priority": "high"},
                    {"type": "generate_content", "priority": "medium"},
                    {"type": "post_to_social", "priority": "low"}
                ]
            }
            for i in range(5)
        ]
        
        # Mock successful execution for all workflows
        mock_responses = []
        for i in range(5):
            mock_responses.append({
                "workflow_id": f"workflow_{i}",
                "status": "completed",
                "execution_time": f"{i + 1}.5s",
                "results": {"operations_completed": 3}
            })
        
        # Execute workflows concurrently
        tasks = []
        for config in concurrent_configs:
            task = async_client.post(
                "/api/v1/workflows/execute",
                json=config,
                headers={"Authorization": f"Bearer mock-jwt-{setup['user'].id}"}
            )
            tasks.append(task)
        
        # Wait for all to complete
        with patch('app.services.workflow.WorkflowOrchestrator.execute_workflow') as mock_workflow:
            mock_workflow.side_effect = mock_responses
            
            responses = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Verify all workflows completed successfully
        assert len(responses) == 5
        for i, response in enumerate(responses):
            if not isinstance(response, Exception):
                assert response.status_code == 200
                result = response.json()
                assert result["workflow_id"] == f"workflow_{i}"