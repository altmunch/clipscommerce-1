"""
Comprehensive unit tests for TikTok trend analysis and Apify integration
including trend detection, viral pattern recognition, and data processing.
"""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from datetime import datetime, timedelta
import json

from app.services.scraping.apify_client import ApifyClient
from app.services.scraping.tiktok_processor import TikTokDataProcessor
from app.services.ai.tiktok_trend_integration import TikTokTrendIntegration
from app.services.ai.trend_analyzer import TrendAnalyzer
from app.models.tiktok_trend import (
    TikTokTrend, TikTokVideo, TikTokHashtag, TikTokSound, TikTokScrapingJob,
    TrendStatus, TrendType, ContentCategory
)
from tests.factories import (
    TikTokTrendFactory, TikTokVideoFactory, TikTokHashtagFactory,
    TikTokScrapingJobFactory, BrandFactory
)


class TestApifyClient:
    """Test Apify client integration for TikTok data scraping."""

    @pytest.fixture
    def apify_client(self):
        return ApifyClient(api_token="test-token")

    @pytest.fixture
    def sample_apify_response(self):
        """Sample Apify API response for TikTok scraping."""
        return {
            "data": {
                "actId": "test-actor-123",
                "id": "run-456",
                "status": "SUCCEEDED",
                "startedAt": "2024-01-01T10:00:00.000Z",
                "finishedAt": "2024-01-01T10:05:00.000Z",
                "stats": {
                    "inputBodyLen": 1234,
                    "outputBodyLen": 56789
                },
                "defaultDatasetId": "dataset-789"
            }
        }

    @pytest.fixture
    def sample_tiktok_data(self):
        """Sample TikTok video data from Apify."""
        return [
            {
                "id": "7234567890123456789",
                "text": "Amazing product showcase! #viral #trending #foryou",
                "createTime": 1704067200,
                "authorMeta": {
                    "id": "user123",
                    "name": "TestUser",
                    "nickName": "Test User",
                    "verified": False,
                    "signature": "Content creator",
                    "followerCount": 50000,
                    "followingCount": 1000,
                    "videoCount": 200
                },
                "musicMeta": {
                    "musicId": "music123",
                    "musicName": "Trending Audio",
                    "musicAuthor": "Artist Name",
                    "musicDuration": 30
                },
                "covers": {
                    "default": "https://example.com/cover.jpg",
                    "dynamic": "https://example.com/cover_dynamic.jpg"
                },
                "webVideoUrl": "https://tiktok.com/@testuser/video/7234567890123456789",
                "videoUrl": "https://example.com/video.mp4",
                "diggCount": 5000,
                "shareCount": 500,
                "playCount": 100000,
                "commentCount": 250,
                "hashtags": [
                    {"id": "viral", "name": "viral", "title": "viral", "cover": ""},
                    {"id": "trending", "name": "trending", "title": "trending", "cover": ""}
                ],
                "mentions": ["@brand"],
                "videoMeta": {
                    "height": 1920,
                    "width": 1080,
                    "duration": 30
                }
            }
        ]

    @pytest.mark.unit
    async def test_start_scraping_job(self, apify_client, sample_apify_response):
        """Test starting a TikTok scraping job via Apify."""
        scraping_config = {
            "hashtags": ["#viral", "#trending"],
            "count": 100,
            "language": "en"
        }
        
        with patch('httpx.AsyncClient.post') as mock_post:
            mock_post.return_value = Mock(
                status_code=201,
                json=Mock(return_value=sample_apify_response)
            )
            
            result = await apify_client.start_tiktok_scraping(scraping_config)
        
        assert result["run_id"] == "run-456"
        assert result["status"] == "started"
        assert result["actor_id"] == "test-actor-123"

    @pytest.mark.unit
    async def test_check_job_status(self, apify_client, sample_apify_response):
        """Test checking the status of a running scraping job."""
        run_id = "run-456"
        
        with patch('httpx.AsyncClient.get') as mock_get:
            mock_get.return_value = Mock(
                status_code=200,
                json=Mock(return_value=sample_apify_response)
            )
            
            status = await apify_client.check_job_status(run_id)
        
        assert status["status"] == "SUCCEEDED"
        assert status["dataset_id"] == "dataset-789"
        assert "started_at" in status
        assert "finished_at" in status

    @pytest.mark.unit
    async def test_fetch_scraped_data(self, apify_client, sample_tiktok_data):
        """Test fetching scraped TikTok data from Apify dataset."""
        dataset_id = "dataset-789"
        
        with patch('httpx.AsyncClient.get') as mock_get:
            mock_get.return_value = Mock(
                status_code=200,
                json=Mock(return_value=sample_tiktok_data)
            )
            
            data = await apify_client.fetch_dataset_data(dataset_id)
        
        assert len(data) == 1
        assert data[0]["id"] == "7234567890123456789"
        assert "#viral" in data[0]["text"]
        assert data[0]["diggCount"] == 5000

    @pytest.mark.unit
    async def test_error_handling_failed_job(self, apify_client):
        """Test error handling for failed scraping jobs."""
        error_response = {
            "data": {
                "id": "run-456",
                "status": "FAILED",
                "error": {
                    "type": "ACTOR_INPUT_ERROR",
                    "message": "Invalid input parameters"
                }
            }
        }
        
        with patch('httpx.AsyncClient.get') as mock_get:
            mock_get.return_value = Mock(
                status_code=200,
                json=Mock(return_value=error_response)
            )
            
            status = await apify_client.check_job_status("run-456")
        
        assert status["status"] == "FAILED"
        assert "error" in status

    @pytest.mark.unit
    async def test_rate_limiting_handling(self, apify_client):
        """Test handling of Apify API rate limiting."""
        with patch('httpx.AsyncClient.post') as mock_post:
            mock_post.return_value = Mock(
                status_code=429,
                headers={"Retry-After": "60"},
                json=Mock(return_value={"error": "Rate limit exceeded"})
            )
            
            with pytest.raises(Exception, match="Rate limit"):
                await apify_client.start_tiktok_scraping({"hashtags": ["#test"]})

    @pytest.mark.unit
    async def test_batch_hashtag_scraping(self, apify_client):
        """Test scraping multiple hashtags in batch."""
        hashtags = ["#viral", "#trending", "#fyp", "#dance", "#comedy"]
        
        with patch('httpx.AsyncClient.post') as mock_post:
            mock_post.return_value = Mock(
                status_code=201,
                json=Mock(return_value={"data": {"id": "run-123", "status": "RUNNING"}})
            )
            
            results = await apify_client.batch_hashtag_scraping(hashtags, videos_per_hashtag=50)
        
        assert len(results) == len(hashtags)
        assert all(r["status"] == "started" for r in results)

    @pytest.mark.unit
    async def test_user_profile_scraping(self, apify_client):
        """Test scraping specific TikTok user profiles."""
        usernames = ["@user1", "@user2", "@user3"]
        
        user_config = {
            "usernames": usernames,
            "videosPerUser": 20,
            "includeProfile": True
        }
        
        with patch('httpx.AsyncClient.post') as mock_post:
            mock_post.return_value = Mock(
                status_code=201,
                json=Mock(return_value={"data": {"id": "run-user-123"}})
            )
            
            result = await apify_client.scrape_user_profiles(user_config)
        
        assert result["run_id"] == "run-user-123"

    @pytest.mark.unit
    async def test_trending_sounds_scraping(self, apify_client):
        """Test scraping trending sounds and music."""
        sound_config = {
            "category": "trending",
            "region": "US",
            "count": 100
        }
        
        with patch('httpx.AsyncClient.post') as mock_post:
            mock_post.return_value = Mock(
                status_code=201,
                json=Mock(return_value={"data": {"id": "run-sounds-123"}})
            )
            
            result = await apify_client.scrape_trending_sounds(sound_config)
        
        assert result["run_id"] == "run-sounds-123"


class TestTikTokDataProcessor:
    """Test TikTok data processing and normalization."""

    @pytest.fixture
    def data_processor(self, mock_redis):
        with patch('app.services.scraping.tiktok_processor.redis', mock_redis):
            return TikTokDataProcessor()

    @pytest.fixture
    def raw_tiktok_video(self):
        """Raw TikTok video data as received from Apify."""
        return {
            "id": "7234567890123456789",
            "text": "Amazing product showcase! #viral #trending #foryou @brand",
            "createTime": 1704067200,
            "authorMeta": {
                "id": "user123",
                "name": "TestUser",
                "nickName": "Test User",
                "verified": False,
                "followerCount": 50000
            },
            "musicMeta": {
                "musicId": "music123",
                "musicName": "Trending Audio"
            },
            "diggCount": 5000,
            "shareCount": 500,
            "playCount": 100000,
            "commentCount": 250,
            "hashtags": [
                {"name": "viral"},
                {"name": "trending"},
                {"name": "foryou"}
            ]
        }

    @pytest.mark.unit
    async def test_process_video_data(self, data_processor, raw_tiktok_video, db_session):
        """Test processing raw TikTok video data."""
        processed = await data_processor.process_video_data(raw_tiktok_video, db_session)
        
        assert processed.video_id == "7234567890123456789"
        assert processed.view_count == 100000
        assert processed.like_count == 5000
        assert processed.creator_username == "TestUser"
        assert len(processed.hashtags) == 3
        assert "#viral" in processed.hashtags

    @pytest.mark.unit
    async def test_extract_hashtags(self, data_processor):
        """Test hashtag extraction and normalization."""
        text = "Amazing video! #ViralContent #TrendingNow #ForYouPage #Brand2024"
        video_hashtags = [{"name": "viral"}, {"name": "trending"}]
        
        hashtags = await data_processor.extract_hashtags(text, video_hashtags)
        
        assert "#viralcontent" in [h.lower() for h in hashtags]
        assert "#trendingnow" in [h.lower() for h in hashtags]
        assert "#viral" in [h.lower() for h in hashtags]
        assert len(hashtags) >= 5

    @pytest.mark.unit
    async def test_extract_mentions(self, data_processor):
        """Test mention extraction from video text."""
        text = "Shoutout to @brand @influencer and @creator for this collab!"
        
        mentions = await data_processor.extract_mentions(text)
        
        assert "@brand" in mentions
        assert "@influencer" in mentions
        assert "@creator" in mentions
        assert len(mentions) == 3

    @pytest.mark.unit
    async def test_calculate_engagement_metrics(self, data_processor, raw_tiktok_video):
        """Test engagement metrics calculation."""
        metrics = await data_processor.calculate_engagement_metrics(raw_tiktok_video)
        
        assert metrics["engagement_rate"] > 0
        assert metrics["like_rate"] > 0
        assert metrics["share_rate"] > 0
        assert metrics["comment_rate"] > 0

    @pytest.mark.unit
    async def test_detect_content_hooks(self, data_processor):
        """Test detection of content hooks and viral elements."""
        video_data = {
            "text": "Wait for it... 🔥 This will blow your mind! WATCH TILL THE END",
            "transcript": "Hey everyone, you won't believe what happened..."
        }
        
        hooks = await data_processor.detect_content_hooks(video_data)
        
        assert len(hooks) > 0
        hook_types = [h["type"] for h in hooks]
        assert "suspense" in hook_types or "anticipation" in hook_types

    @pytest.mark.unit
    async def test_analyze_posting_patterns(self, data_processor):
        """Test analysis of optimal posting patterns."""
        video_timestamps = [
            1704067200,  # 2024-01-01 10:00:00 UTC
            1704070800,  # 2024-01-01 11:00:00 UTC
            1704153600,  # 2024-01-02 10:00:00 UTC
        ]
        
        patterns = await data_processor.analyze_posting_patterns(video_timestamps)
        
        assert "optimal_hours" in patterns
        assert "optimal_days" in patterns
        assert "timezone_analysis" in patterns

    @pytest.mark.unit
    async def test_duplicate_detection(self, data_processor, db_session):
        """Test detection of duplicate videos."""
        # Create existing video
        existing_video = TikTokVideoFactory.create(video_id="existing123")
        db_session.add(existing_video)
        db_session.commit()
        
        # Test duplicate detection
        duplicate_data = {"id": "existing123", "text": "Test video"}
        is_duplicate = await data_processor.is_duplicate_video(duplicate_data, db_session)
        assert is_duplicate is True
        
        # Test new video
        new_data = {"id": "new456", "text": "New video"}
        is_duplicate = await data_processor.is_duplicate_video(new_data, db_session)
        assert is_duplicate is False

    @pytest.mark.unit
    async def test_batch_processing(self, data_processor, db_session):
        """Test batch processing of multiple videos."""
        raw_videos = [
            {"id": f"video{i}", "text": f"Video {i}", "diggCount": i * 100}
            for i in range(10)
        ]
        
        results = await data_processor.batch_process_videos(raw_videos, db_session)
        
        assert len(results["processed"]) == 10
        assert results["total_processed"] == 10
        assert results["duplicates_skipped"] == 0

    @pytest.mark.unit
    async def test_data_quality_validation(self, data_processor):
        """Test data quality validation and scoring."""
        high_quality_video = {
            "id": "12345",
            "text": "Detailed description with hashtags #test",
            "authorMeta": {"name": "RealUser", "verified": True},
            "diggCount": 1000,
            "playCount": 50000
        }
        
        low_quality_video = {
            "id": "",  # Missing ID
            "text": "",  # No description
            "authorMeta": {},  # Missing author info
            "diggCount": 0
        }
        
        high_score = await data_processor.validate_data_quality(high_quality_video)
        low_score = await data_processor.validate_data_quality(low_quality_video)
        
        assert high_score > 0.8
        assert low_score < 0.5


class TestTikTokTrendIntegration:
    """Test TikTok trend integration with AI services."""

    @pytest.fixture
    def trend_integration(self, mock_openai_client, mock_anthropic_client):
        with patch('app.services.ai.tiktok_trend_integration.openai_client', mock_openai_client):
            with patch('app.services.ai.tiktok_trend_integration.anthropic_client', mock_anthropic_client):
                return TikTokTrendIntegration()

    @pytest.mark.unit
    @pytest.mark.ai
    async def test_generate_trend_insights(self, trend_integration, db_session):
        """Test generating AI-powered trend insights."""
        # Create sample trends
        trends = [
            TikTokTrendFactory.create(
                name="#viral",
                total_videos=100000,
                growth_rate=25.5,
                trend_status=TrendStatus.RISING
            ),
            TikTokTrendFactory.create(
                name="#trending",
                total_videos=75000,
                growth_rate=45.2,
                trend_status=TrendStatus.EMERGING
            )
        ]
        
        for trend in trends:
            db_session.add(trend)
        db_session.commit()
        
        trend_integration.openai_client.chat.completions.create.return_value = Mock(
            choices=[Mock(message=Mock(content=json.dumps({
                "insights": [
                    {
                        "trend": "#viral",
                        "insight": "Consistently high engagement across demographics",
                        "recommendation": "Leverage for brand awareness campaigns"
                    }
                ],
                "overall_analysis": "Strong growth in entertainment-focused content",
                "opportunities": ["Brand collaboration potential", "User-generated content"]
            })))]
        )
        
        insights = await trend_integration.generate_trend_insights(trends)
        
        assert len(insights["insights"]) > 0
        assert "overall_analysis" in insights
        assert "opportunities" in insights

    @pytest.mark.unit
    @pytest.mark.ai
    async def test_predict_viral_potential(self, trend_integration):
        """Test predicting viral potential of content."""
        content_data = {
            "hashtags": ["#viral", "#trending", "#fyp"],
            "description": "Amazing product showcase with trending music",
            "creator_followers": 100000,
            "posting_time": "evening",
            "content_features": ["trending_music", "product_demo", "call_to_action"]
        }
        
        trend_integration.openai_client.chat.completions.create.return_value = Mock(
            choices=[Mock(message=Mock(content=json.dumps({
                "viral_score": 8.5,
                "confidence": 0.85,
                "factors": {
                    "hashtag_strength": 9.0,
                    "content_quality": 8.0,
                    "timing_optimization": 7.5
                },
                "recommendations": [
                    "Add more trending hashtags",
                    "Optimize posting time to peak hours"
                ]
            })))]
        )
        
        prediction = await trend_integration.predict_viral_potential(content_data)
        
        assert prediction["viral_score"] == 8.5
        assert prediction["confidence"] == 0.85
        assert len(prediction["recommendations"]) > 0

    @pytest.mark.unit
    @pytest.mark.ai
    async def test_brand_trend_alignment(self, trend_integration, db_session):
        """Test analyzing brand-trend alignment."""
        brand = BrandFactory.create(
            industry="beauty",
            target_audience={"age": "18-34", "gender": "female"},
            brand_voice="fun and trendy"
        )
        db_session.add(brand)
        db_session.commit()
        
        trending_hashtags = ["#skincare", "#makeup", "#selfcare", "#beauty", "#viral"]
        
        trend_integration.openai_client.chat.completions.create.return_value = Mock(
            choices=[Mock(message=Mock(content=json.dumps({
                "alignment_scores": {
                    "#skincare": 9.5,
                    "#makeup": 9.0,
                    "#selfcare": 8.5,
                    "#beauty": 10.0,
                    "#viral": 6.0
                },
                "recommended_trends": ["#skincare", "#makeup", "#beauty"],
                "brand_fit_analysis": "Strong alignment with beauty and wellness trends"
            })))]
        )
        
        alignment = await trend_integration.analyze_brand_trend_alignment(brand.id, trending_hashtags, db_session)
        
        assert "#beauty" in alignment["recommended_trends"]
        assert alignment["alignment_scores"]["#beauty"] > 9.0

    @pytest.mark.unit
    @pytest.mark.ai
    async def test_content_optimization_suggestions(self, trend_integration):
        """Test AI-powered content optimization suggestions."""
        content_draft = {
            "script": "Check out this amazing product!",
            "hashtags": ["#product", "#amazing"],
            "target_platform": "tiktok",
            "brand_guidelines": {
                "voice": "energetic and youthful",
                "colors": ["#FF6B6B", "#4ECDC4"]
            }
        }
        
        current_trends = [
            {"hashtag": "#viral", "growth_rate": 25.0},
            {"hashtag": "#trending", "growth_rate": 45.0}
        ]
        
        trend_integration.openai_client.chat.completions.create.return_value = Mock(
            choices=[Mock(message=Mock(content=json.dumps({
                "optimized_script": "OMG you NEED to see this life-changing product! 🔥",
                "suggested_hashtags": ["#viral", "#trending", "#musthave", "#lifehack"],
                "content_hooks": ["OMG you NEED to see this", "life-changing"],
                "visual_suggestions": ["Quick product demo", "Before/after shots"],
                "optimization_score": 8.7
            })))]
        )
        
        suggestions = await trend_integration.optimize_content_for_trends(content_draft, current_trends)
        
        assert suggestions["optimization_score"] > 8.0
        assert len(suggestions["suggested_hashtags"]) > 2
        assert "life-changing" in suggestions["content_hooks"]


class TestTrendAnalyzer:
    """Test trend analysis algorithms and pattern recognition."""

    @pytest.fixture
    def trend_analyzer(self, mock_redis, mock_vector_db):
        with patch('app.services.ai.trend_analyzer.redis', mock_redis):
            with patch('app.services.ai.trend_analyzer.vector_db', mock_vector_db):
                return TrendAnalyzer()

    @pytest.mark.unit
    async def test_detect_emerging_trends(self, trend_analyzer, db_session):
        """Test detection of emerging trends from data."""
        # Create hashtags with different growth patterns
        hashtags = [
            TikTokHashtagFactory.create(
                hashtag="#emergingtag",
                total_videos=1000,
                usage_velocity=50.0,  # High velocity
                first_seen=datetime.utcnow() - timedelta(days=1)  # Very recent
            ),
            TikTokHashtagFactory.create(
                hashtag="#stabletag",
                total_videos=10000,
                usage_velocity=5.0,  # Low velocity
                first_seen=datetime.utcnow() - timedelta(days=30)  # Older
            )
        ]
        
        for hashtag in hashtags:
            db_session.add(hashtag)
        db_session.commit()
        
        emerging = await trend_analyzer.detect_emerging_trends(db_session)
        
        assert len(emerging) > 0
        emerging_tags = [t.hashtag for t in emerging]
        assert "#emergingtag" in emerging_tags

    @pytest.mark.unit
    async def test_calculate_viral_coefficient(self, trend_analyzer):
        """Test viral coefficient calculation."""
        video_metrics = {
            "view_count": 1000000,
            "like_count": 50000,
            "share_count": 10000,
            "comment_count": 5000,
            "creator_followers": 100000
        }
        
        coefficient = await trend_analyzer.calculate_viral_coefficient(video_metrics)
        
        assert coefficient > 0
        assert isinstance(coefficient, (int, float))

    @pytest.mark.unit
    async def test_trend_lifecycle_analysis(self, trend_analyzer, db_session):
        """Test trend lifecycle stage detection."""
        # Create trend with historical data
        trend = TikTokTrendFactory.create(
            name="#lifecycletest",
            total_videos=50000,
            growth_rate=15.0,
            first_detected=datetime.utcnow() - timedelta(days=14)
        )
        db_session.add(trend)
        db_session.commit()
        
        lifecycle = await trend_analyzer.analyze_trend_lifecycle(trend)
        
        assert lifecycle["current_phase"] in ["emerging", "growing", "peak", "declining", "fading"]
        assert "estimated_peak" in lifecycle
        assert "time_to_peak" in lifecycle

    @pytest.mark.unit
    async def test_cross_platform_trend_correlation(self, trend_analyzer):
        """Test correlation analysis across platforms."""
        platform_data = {
            "tiktok": [
                {"hashtag": "#viral", "usage": 100000, "growth": 25.0},
                {"hashtag": "#trending", "usage": 75000, "growth": 30.0}
            ],
            "instagram": [
                {"hashtag": "#viral", "usage": 50000, "growth": 15.0},
                {"hashtag": "#instatrend", "usage": 30000, "growth": 40.0}
            ]
        }
        
        correlation = await trend_analyzer.analyze_cross_platform_correlation(platform_data)
        
        assert "shared_trends" in correlation
        assert "platform_specific" in correlation
        assert "#viral" in [t["hashtag"] for t in correlation["shared_trends"]]

    @pytest.mark.unit
    async def test_geographic_trend_analysis(self, trend_analyzer):
        """Test geographic distribution analysis of trends."""
        geographic_data = {
            "US": {"usage": 50000, "engagement": 8.5},
            "UK": {"usage": 20000, "engagement": 7.2},
            "CA": {"usage": 15000, "engagement": 9.1},
            "AU": {"usage": 10000, "engagement": 8.8}
        }
        
        analysis = await trend_analyzer.analyze_geographic_trends(geographic_data)
        
        assert "top_regions" in analysis
        assert "engagement_leaders" in analysis
        assert "growth_opportunities" in analysis

    @pytest.mark.unit
    async def test_seasonal_trend_patterns(self, trend_analyzer, db_session):
        """Test seasonal trend pattern detection."""
        # Create trends with timestamps across different seasons
        seasonal_trends = []
        for i, month in enumerate([1, 4, 7, 10]):  # Jan, Apr, Jul, Oct
            trend = TikTokTrendFactory.create(
                name=f"#season{month}",
                first_detected=datetime(2024, month, 1),
                total_videos=10000 + i * 5000
            )
            seasonal_trends.append(trend)
            db_session.add(trend)
        
        db_session.commit()
        
        patterns = await trend_analyzer.detect_seasonal_patterns(seasonal_trends)
        
        assert "seasonal_peaks" in patterns
        assert "recurring_themes" in patterns

    @pytest.mark.unit
    async def test_trend_clustering(self, trend_analyzer, mock_vector_db):
        """Test clustering of similar trends."""
        trends_data = [
            {"hashtag": "#dance1", "category": "dance", "features": [0.8, 0.2, 0.9]},
            {"hashtag": "#dance2", "category": "dance", "features": [0.9, 0.1, 0.8]},
            {"hashtag": "#food1", "category": "food", "features": [0.1, 0.9, 0.2]},
            {"hashtag": "#food2", "category": "food", "features": [0.2, 0.8, 0.3]}
        ]
        
        # Mock vector similarity
        mock_vector_db.query.return_value = {
            "matches": [
                {"id": "dance1", "score": 0.95, "metadata": {"category": "dance"}},
                {"id": "dance2", "score": 0.93, "metadata": {"category": "dance"}}
            ]
        }
        
        clusters = await trend_analyzer.cluster_similar_trends(trends_data)
        
        assert len(clusters) > 0
        assert any(cluster["category"] == "dance" for cluster in clusters)

    @pytest.mark.unit
    async def test_trend_prediction_model(self, trend_analyzer):
        """Test trend prediction using ML models."""
        historical_data = [
            {
                "hashtag": "#predicttest",
                "day": i,
                "usage": 1000 + i * 100,
                "growth_rate": 10.0 + i * 2,
                "engagement": 5.0 + i * 0.5
            }
            for i in range(14)  # 14 days of data
        ]
        
        prediction = await trend_analyzer.predict_trend_future(historical_data, days_ahead=7)
        
        assert "predicted_usage" in prediction
        assert "confidence_interval" in prediction
        assert "growth_trajectory" in prediction

    @pytest.mark.unit
    async def test_competitor_trend_monitoring(self, trend_analyzer, db_session):
        """Test monitoring competitor trend adoption."""
        brand = BrandFactory.create(
            competitors=["competitor1", "competitor2", "competitor3"]
        )
        db_session.add(brand)
        db_session.commit()
        
        competitor_trends = {
            "competitor1": ["#trend1", "#trend2"],
            "competitor2": ["#trend2", "#trend3"],
            "competitor3": ["#trend1", "#trend3"]
        }
        
        analysis = await trend_analyzer.analyze_competitor_trends(brand.id, competitor_trends, db_session)
        
        assert "popular_among_competitors" in analysis
        assert "opportunity_trends" in analysis
        assert "competitive_gaps" in analysis

    @pytest.mark.unit
    async def test_trend_saturation_analysis(self, trend_analyzer):
        """Test analysis of trend saturation levels."""
        trend_metrics = {
            "hashtag": "#saturatedtrend",
            "total_videos": 500000,
            "daily_new_videos": 1000,  # Slowing growth
            "engagement_rate": 3.2,  # Lower engagement
            "creator_diversity": 0.3,  # Low diversity
            "age_days": 45
        }
        
        saturation = await trend_analyzer.analyze_trend_saturation(trend_metrics)
        
        assert "saturation_level" in saturation
        assert "market_fatigue_indicators" in saturation
        assert "recommendation" in saturation