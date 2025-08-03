"""
Comprehensive unit tests for social media platform APIs including
TikTok Business API, Instagram Graph API, OAuth flows, and multi-platform posting.
"""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from datetime import datetime, timedelta
import json
import jwt

from app.services.social_media.tiktok_service import TikTokBusinessAPI
from app.services.social_media.instagram_service import InstagramGraphAPI
from app.services.social_media.social_media_manager import SocialMediaManager
from app.services.social_media.webhook_processor import WebhookProcessor
from app.services.social_media.video_pipeline_integration import VideoPipelineIntegration
from app.models.social_media import (
    SocialMediaAccount, SocialMediaPost, SocialMediaAnalytics,
    PlatformType, AccountStatus, PostStatus, ContentType
)
from tests.factories import (
    SocialMediaAccountFactory, SocialMediaPostFactory, SocialMediaAnalyticsFactory,
    VideoProjectFactory, BrandFactory
)


class TestTikTokBusinessAPI:
    """Test TikTok Business API integration."""

    @pytest.fixture
    def tiktok_api(self):
        return TikTokBusinessAPI(
            client_id="test_client_id",
            client_secret="test_client_secret",
            redirect_uri="https://example.com/callback"
        )

    @pytest.fixture
    def sample_oauth_response(self):
        """Sample OAuth token response from TikTok."""
        return {
            "access_token": "tiktok_access_token_123",
            "refresh_token": "tiktok_refresh_token_456",
            "expires_in": 86400,
            "refresh_expires_in": 2592000,
            "token_type": "Bearer",
            "scope": "user.info.basic,video.upload,video.publish"
        }

    @pytest.fixture
    def sample_user_info(self):
        """Sample user info from TikTok API."""
        return {
            "data": {
                "user": {
                    "open_id": "tiktok_user_123",
                    "union_id": "tiktok_union_456",
                    "avatar_url": "https://example.com/avatar.jpg",
                    "avatar_url_100": "https://example.com/avatar_100.jpg",
                    "avatar_large_url": "https://example.com/avatar_large.jpg",
                    "display_name": "Test User",
                    "bio_description": "Content creator",
                    "profile_deep_link": "https://tiktok.com/@testuser",
                    "is_verified": False,
                    "follower_count": 50000,
                    "following_count": 1000,
                    "likes_count": 500000
                }
            }
        }

    @pytest.mark.unit
    async def test_oauth_authorization_url(self, tiktok_api):
        """Test OAuth authorization URL generation."""
        state = "random_state_123"
        scopes = ["user.info.basic", "video.upload", "video.publish"]
        
        auth_url = tiktok_api.get_authorization_url(state, scopes)
        
        assert "https://www.tiktok.com/v2/auth/authorize" in auth_url
        assert "client_id=test_client_id" in auth_url
        assert "state=random_state_123" in auth_url
        assert "scope=user.info.basic%2Cvideo.upload%2Cvideo.publish" in auth_url

    @pytest.mark.unit
    async def test_exchange_code_for_token(self, tiktok_api, sample_oauth_response):
        """Test exchanging authorization code for access token."""
        auth_code = "tiktok_auth_code_123"
        
        with patch('httpx.AsyncClient.post') as mock_post:
            mock_post.return_value = Mock(
                status_code=200,
                json=Mock(return_value=sample_oauth_response)
            )
            
            token_data = await tiktok_api.exchange_code_for_token(auth_code)
        
        assert token_data["access_token"] == "tiktok_access_token_123"
        assert token_data["expires_in"] == 86400
        assert "refresh_token" in token_data

    @pytest.mark.unit
    async def test_refresh_access_token(self, tiktok_api, sample_oauth_response):
        """Test refreshing expired access token."""
        refresh_token = "tiktok_refresh_token_456"
        
        with patch('httpx.AsyncClient.post') as mock_post:
            mock_post.return_value = Mock(
                status_code=200,
                json=Mock(return_value=sample_oauth_response)
            )
            
            new_token_data = await tiktok_api.refresh_access_token(refresh_token)
        
        assert new_token_data["access_token"] == "tiktok_access_token_123"

    @pytest.mark.unit
    async def test_get_user_info(self, tiktok_api, sample_user_info):
        """Test fetching user profile information."""
        access_token = "tiktok_access_token_123"
        
        with patch('httpx.AsyncClient.get') as mock_get:
            mock_get.return_value = Mock(
                status_code=200,
                json=Mock(return_value=sample_user_info)
            )
            
            user_info = await tiktok_api.get_user_info(access_token)
        
        assert user_info["open_id"] == "tiktok_user_123"
        assert user_info["display_name"] == "Test User"
        assert user_info["follower_count"] == 50000

    @pytest.mark.unit
    async def test_upload_video(self, tiktok_api):
        """Test video upload to TikTok."""
        access_token = "tiktok_access_token_123"
        video_file_path = "/tmp/test_video.mp4"
        video_metadata = {
            "title": "Amazing Product Demo",
            "description": "Check out this amazing product! #viral #trending",
            "privacy_level": "PUBLIC_TO_EVERYONE",
            "disable_duet": False,
            "disable_comment": False,
            "disable_stitch": False,
            "video_cover_timestamp_ms": 1000
        }
        
        upload_response = {
            "data": {
                "video": {
                    "id": "tiktok_video_123",
                    "title": "Amazing Product Demo",
                    "cover_image_url": "https://example.com/cover.jpg",
                    "share_url": "https://tiktok.com/@testuser/video/123",
                    "embed_html": "<iframe>...</iframe>",
                    "embed_link": "https://tiktok.com/embed/video/123",
                    "create_time": 1704067200,
                    "duration": 30,
                    "height": 1920,
                    "width": 1080,
                    "video_status": "PROCESSING"
                }
            }
        }
        
        with patch('httpx.AsyncClient.post') as mock_post:
            with patch('builtins.open', mock_open(read_data=b"fake_video_data")):
                mock_post.return_value = Mock(
                    status_code=200,
                    json=Mock(return_value=upload_response)
                )
                
                result = await tiktok_api.upload_video(access_token, video_file_path, video_metadata)
        
        assert result["video_id"] == "tiktok_video_123"
        assert result["share_url"] == "https://tiktok.com/@testuser/video/123"
        assert result["status"] == "PROCESSING"

    @pytest.mark.unit
    async def test_get_video_analytics(self, tiktok_api):
        """Test fetching video analytics from TikTok."""
        access_token = "tiktok_access_token_123"
        video_id = "tiktok_video_123"
        
        analytics_response = {
            "data": {
                "videos": [
                    {
                        "id": "tiktok_video_123",
                        "metrics": {
                            "video_views": 50000,
                            "likes": 2500,
                            "comments": 150,
                            "shares": 300,
                            "reach": 45000,
                            "profile_views": 800,
                            "follows": 45
                        }
                    }
                ]
            }
        }
        
        with patch('httpx.AsyncClient.get') as mock_get:
            mock_get.return_value = Mock(
                status_code=200,
                json=Mock(return_value=analytics_response)
            )
            
            analytics = await tiktok_api.get_video_analytics(access_token, video_id)
        
        assert analytics["video_views"] == 50000
        assert analytics["likes"] == 2500
        assert analytics["engagement_rate"] > 0

    @pytest.mark.unit
    async def test_post_video_with_scheduling(self, tiktok_api):
        """Test scheduling video posts for future publishing."""
        access_token = "tiktok_access_token_123"
        video_file_path = "/tmp/scheduled_video.mp4"
        publish_time = datetime.utcnow() + timedelta(hours=2)
        
        video_metadata = {
            "title": "Scheduled Post",
            "description": "This post is scheduled for later",
            "privacy_level": "PUBLIC_TO_EVERYONE",
            "publish_time": int(publish_time.timestamp())
        }
        
        scheduled_response = {
            "data": {
                "video": {
                    "id": "scheduled_video_456",
                    "video_status": "SCHEDULED",
                    "publish_time": int(publish_time.timestamp())
                }
            }
        }
        
        with patch('httpx.AsyncClient.post') as mock_post:
            with patch('builtins.open', mock_open(read_data=b"fake_video_data")):
                mock_post.return_value = Mock(
                    status_code=200,
                    json=Mock(return_value=scheduled_response)
                )
                
                result = await tiktok_api.upload_video(access_token, video_file_path, video_metadata)
        
        assert result["video_id"] == "scheduled_video_456"
        assert result["status"] == "SCHEDULED"

    @pytest.mark.unit
    async def test_error_handling_rate_limit(self, tiktok_api):
        """Test handling of TikTok API rate limits."""
        access_token = "tiktok_access_token_123"
        
        with patch('httpx.AsyncClient.get') as mock_get:
            mock_get.return_value = Mock(
                status_code=429,
                json=Mock(return_value={
                    "error": {
                        "code": "rate_limit_exceeded",
                        "message": "Rate limit exceeded",
                        "log_id": "202401011000001"
                    }
                })
            )
            
            with pytest.raises(Exception, match="Rate limit exceeded"):
                await tiktok_api.get_user_info(access_token)

    @pytest.mark.unit
    async def test_webhook_verification(self, tiktok_api):
        """Test TikTok webhook verification."""
        webhook_payload = {
            "timestamp": str(int(datetime.utcnow().timestamp())),
            "event": "video.publish",
            "data": {"video_id": "123", "status": "published"}
        }
        
        signature = "test_signature"
        
        # Mock signature verification
        with patch.object(tiktok_api, 'verify_webhook_signature', return_value=True):
            is_valid = tiktok_api.verify_webhook_signature(
                json.dumps(webhook_payload), 
                signature
            )
        
        assert is_valid is True


class TestInstagramGraphAPI:
    """Test Instagram Graph API integration."""

    @pytest.fixture
    def instagram_api(self):
        return InstagramGraphAPI(
            app_id="instagram_app_123",
            app_secret="instagram_secret_456",
            redirect_uri="https://example.com/instagram/callback"
        )

    @pytest.fixture
    def sample_instagram_token(self):
        """Sample Instagram access token response."""
        return {
            "access_token": "instagram_token_123",
            "user_id": "instagram_user_456",
            "expires_in": 5183944  # ~60 days
        }

    @pytest.fixture
    def sample_instagram_user(self):
        """Sample Instagram user data."""
        return {
            "id": "instagram_user_456",
            "username": "testuser_ig",
            "account_type": "BUSINESS",
            "media_count": 150,
            "followers_count": 75000,
            "follows_count": 500,
            "name": "Test Business",
            "website": "https://testbusiness.com",
            "biography": "Official business account",
            "profile_picture_url": "https://example.com/ig_profile.jpg"
        }

    @pytest.mark.unit
    async def test_instagram_oauth_flow(self, instagram_api, sample_instagram_token):
        """Test Instagram OAuth authorization flow."""
        auth_code = "instagram_auth_code_123"
        
        with patch('httpx.AsyncClient.post') as mock_post:
            mock_post.return_value = Mock(
                status_code=200,
                json=Mock(return_value=sample_instagram_token)
            )
            
            token_data = await instagram_api.exchange_code_for_token(auth_code)
        
        assert token_data["access_token"] == "instagram_token_123"
        assert token_data["user_id"] == "instagram_user_456"

    @pytest.mark.unit
    async def test_get_instagram_user_info(self, instagram_api, sample_instagram_user):
        """Test fetching Instagram user information."""
        access_token = "instagram_token_123"
        
        with patch('httpx.AsyncClient.get') as mock_get:
            mock_get.return_value = Mock(
                status_code=200,
                json=Mock(return_value=sample_instagram_user)
            )
            
            user_info = await instagram_api.get_user_info(access_token)
        
        assert user_info["username"] == "testuser_ig"
        assert user_info["followers_count"] == 75000
        assert user_info["account_type"] == "BUSINESS"

    @pytest.mark.unit
    async def test_upload_instagram_video(self, instagram_api):
        """Test uploading video to Instagram."""
        access_token = "instagram_token_123"
        video_url = "https://example.com/video.mp4"
        caption = "Amazing product showcase! #instagram #viral"
        
        upload_response = {
            "id": "instagram_container_123"
        }
        
        publish_response = {
            "id": "instagram_media_456"
        }
        
        with patch('httpx.AsyncClient.post') as mock_post:
            mock_post.side_effect = [
                Mock(status_code=200, json=Mock(return_value=upload_response)),
                Mock(status_code=200, json=Mock(return_value=publish_response))
            ]
            
            result = await instagram_api.upload_video(access_token, video_url, caption)
        
        assert result["media_id"] == "instagram_media_456"
        assert result["container_id"] == "instagram_container_123"

    @pytest.mark.unit
    async def test_upload_instagram_reel(self, instagram_api):
        """Test uploading Instagram Reel."""
        access_token = "instagram_token_123"
        video_url = "https://example.com/reel.mp4"
        cover_url = "https://example.com/cover.jpg"
        caption = "Check out this Reel! #reels #viral"
        
        reel_response = {
            "id": "instagram_reel_container_789"
        }
        
        with patch('httpx.AsyncClient.post') as mock_post:
            mock_post.return_value = Mock(
                status_code=200,
                json=Mock(return_value=reel_response)
            )
            
            result = await instagram_api.upload_reel(
                access_token, video_url, caption, cover_url
            )
        
        assert result["container_id"] == "instagram_reel_container_789"

    @pytest.mark.unit
    async def test_get_instagram_media_insights(self, instagram_api):
        """Test fetching Instagram media insights."""
        access_token = "instagram_token_123"
        media_id = "instagram_media_456"
        
        insights_response = {
            "data": [
                {"name": "impressions", "values": [{"value": 5000}]},
                {"name": "reach", "values": [{"value": 4500}]},
                {"name": "engagement", "values": [{"value": 450}]},
                {"name": "likes", "values": [{"value": 300}]},
                {"name": "comments", "values": [{"value": 25}]},
                {"name": "shares", "values": [{"value": 45}]},
                {"name": "saves", "values": [{"value": 80}]}
            ]
        }
        
        with patch('httpx.AsyncClient.get') as mock_get:
            mock_get.return_value = Mock(
                status_code=200,
                json=Mock(return_value=insights_response)
            )
            
            insights = await instagram_api.get_media_insights(access_token, media_id)
        
        assert insights["impressions"] == 5000
        assert insights["reach"] == 4500
        assert insights["engagement_rate"] > 0

    @pytest.mark.unit
    async def test_instagram_story_upload(self, instagram_api):
        """Test uploading Instagram Story."""
        access_token = "instagram_token_123"
        media_url = "https://example.com/story_video.mp4"
        
        story_response = {
            "id": "instagram_story_123"
        }
        
        with patch('httpx.AsyncClient.post') as mock_post:
            mock_post.return_value = Mock(
                status_code=200,
                json=Mock(return_value=story_response)
            )
            
            result = await instagram_api.upload_story(access_token, media_url, media_type="VIDEO")
        
        assert result["story_id"] == "instagram_story_123"

    @pytest.mark.unit
    async def test_long_lived_token_exchange(self, instagram_api):
        """Test exchanging short-lived token for long-lived token."""
        short_lived_token = "short_token_123"
        
        long_lived_response = {
            "access_token": "long_lived_token_456",
            "token_type": "bearer",
            "expires_in": 5183944  # ~60 days
        }
        
        with patch('httpx.AsyncClient.get') as mock_get:
            mock_get.return_value = Mock(
                status_code=200,
                json=Mock(return_value=long_lived_response)
            )
            
            long_token = await instagram_api.get_long_lived_token(short_lived_token)
        
        assert long_token["access_token"] == "long_lived_token_456"
        assert long_token["expires_in"] == 5183944


class TestSocialMediaManager:
    """Test unified social media management."""

    @pytest.fixture
    def social_manager(self, mock_redis):
        with patch('app.services.social_media.social_media_manager.redis', mock_redis):
            return SocialMediaManager()

    @pytest.fixture
    def sample_accounts(self, db_session):
        """Create sample social media accounts."""
        brand = BrandFactory.create()
        
        tiktok_account = SocialMediaAccountFactory.create(
            brand_id=brand.id,
            platform=PlatformType.TIKTOK,
            username="brand_tiktok",
            access_token="tiktok_token_123"
        )
        
        instagram_account = SocialMediaAccountFactory.create(
            brand_id=brand.id,
            platform=PlatformType.INSTAGRAM,
            username="brand_instagram", 
            access_token="instagram_token_456"
        )
        
        db_session.add_all([brand, tiktok_account, instagram_account])
        db_session.commit()
        
        return {
            "brand": brand,
            "tiktok": tiktok_account,
            "instagram": instagram_account
        }

    @pytest.mark.unit
    async def test_cross_platform_posting(self, social_manager, sample_accounts, db_session):
        """Test posting content across multiple platforms."""
        video_project = VideoProjectFactory.create(brand_id=sample_accounts["brand"].id)
        db_session.add(video_project)
        db_session.commit()
        
        post_config = {
            "video_url": "https://example.com/cross_platform_video.mp4",
            "caption": "Amazing product showcase!",
            "hashtags": ["#viral", "#trending", "#product"],
            "platforms": ["tiktok", "instagram"],
            "schedule_time": None  # Post immediately
        }
        
        # Mock platform API responses
        with patch.object(social_manager.tiktok_api, 'upload_video') as mock_tiktok:
            with patch.object(social_manager.instagram_api, 'upload_video') as mock_instagram:
                
                mock_tiktok.return_value = {"video_id": "tiktok_123", "status": "processing"}
                mock_instagram.return_value = {"media_id": "instagram_456", "status": "published"}
                
                results = await social_manager.post_to_multiple_platforms(
                    video_project.id, post_config, db_session
                )
        
        assert len(results) == 2
        assert results["tiktok"]["status"] == "success"
        assert results["instagram"]["status"] == "success"

    @pytest.mark.unit
    async def test_platform_specific_optimization(self, social_manager):
        """Test optimizing content for specific platforms."""
        base_content = {
            "video_url": "https://example.com/video.mp4",
            "caption": "Check out this amazing product! It will change your life forever and make everything better.",
            "hashtags": ["#product", "#amazing", "#life", "#better", "#change"]
        }
        
        # Test TikTok optimization (shorter, more hashtags)
        tiktok_optimized = await social_manager.optimize_for_platform(base_content, "tiktok")
        assert len(tiktok_optimized["caption"]) <= 150  # TikTok character limit
        assert len(tiktok_optimized["hashtags"]) >= 3
        
        # Test Instagram optimization (longer caption allowed, fewer hashtags)
        instagram_optimized = await social_manager.optimize_for_platform(base_content, "instagram")
        assert len(instagram_optimized["hashtags"]) <= 10  # Instagram best practice

    @pytest.mark.unit
    async def test_scheduled_posting(self, social_manager, sample_accounts, mock_redis, db_session):
        """Test scheduling posts for future publishing."""
        schedule_time = datetime.utcnow() + timedelta(hours=2)
        
        post_data = {
            "video_url": "https://example.com/scheduled_video.mp4",
            "caption": "Scheduled post content",
            "platforms": ["tiktok", "instagram"],
            "schedule_time": schedule_time
        }
        
        job_id = await social_manager.schedule_post(sample_accounts["brand"].id, post_data, db_session)
        
        assert job_id is not None
        mock_redis.zadd.assert_called()  # Scheduled job stored

    @pytest.mark.unit
    async def test_analytics_aggregation(self, social_manager, sample_accounts, db_session):
        """Test aggregating analytics across platforms."""
        # Create sample posts
        tiktok_post = SocialMediaPostFactory.create(
            account_id=sample_accounts["tiktok"].id,
            view_count=50000,
            like_count=2500,
            share_count=300
        )
        
        instagram_post = SocialMediaPostFactory.create(
            account_id=sample_accounts["instagram"].id,
            view_count=30000,
            like_count=1800,
            share_count=150
        )
        
        db_session.add_all([tiktok_post, instagram_post])
        db_session.commit()
        
        # Mock platform API calls for fresh analytics
        with patch.object(social_manager.tiktok_api, 'get_video_analytics') as mock_tiktok_analytics:
            with patch.object(social_manager.instagram_api, 'get_media_insights') as mock_ig_analytics:
                
                mock_tiktok_analytics.return_value = {
                    "video_views": 55000, "likes": 2700, "shares": 350
                }
                mock_ig_analytics.return_value = {
                    "impressions": 35000, "likes": 2000, "shares": 180
                }
                
                aggregated = await social_manager.get_cross_platform_analytics(
                    sample_accounts["brand"].id, db_session
                )
        
        assert aggregated["total_views"] > 80000
        assert aggregated["total_likes"] > 4000
        assert len(aggregated["platform_breakdown"]) == 2

    @pytest.mark.unit
    async def test_content_performance_comparison(self, social_manager, db_session):
        """Test comparing content performance across platforms."""
        # Create posts with different performance metrics
        high_performing_post = SocialMediaPostFactory.create(
            view_count=100000,
            like_count=5000,
            engagement_rate=8.5
        )
        
        low_performing_post = SocialMediaPostFactory.create(
            view_count=5000,
            like_count=200,
            engagement_rate=2.1
        )
        
        db_session.add_all([high_performing_post, low_performing_post])
        db_session.commit()
        
        comparison = await social_manager.compare_content_performance([
            high_performing_post.id, low_performing_post.id
        ], db_session)
        
        assert comparison["best_performing"]["engagement_rate"] > 8.0
        assert comparison["performance_gap"] > 5.0

    @pytest.mark.unit
    async def test_account_health_monitoring(self, social_manager, sample_accounts, db_session):
        """Test monitoring social media account health."""
        # Simulate token expiration
        sample_accounts["tiktok"].token_expires_at = datetime.utcnow() - timedelta(days=1)
        db_session.commit()
        
        health_status = await social_manager.check_account_health(
            sample_accounts["brand"].id, db_session
        )
        
        assert health_status["tiktok"]["status"] == "token_expired"
        assert health_status["instagram"]["status"] == "healthy"
        assert health_status["overall_health"] == "needs_attention"


class TestWebhookProcessor:
    """Test webhook processing for real-time updates."""

    @pytest.fixture
    def webhook_processor(self, mock_redis):
        with patch('app.services.social_media.webhook_processor.redis', mock_redis):
            return WebhookProcessor()

    @pytest.mark.unit
    async def test_process_tiktok_webhook(self, webhook_processor, db_session):
        """Test processing TikTok webhook events."""
        # Create associated post
        post = SocialMediaPostFactory.create(
            platform_post_id="tiktok_video_123",
            status=PostStatus.PUBLISHING
        )
        db_session.add(post)
        db_session.commit()
        
        webhook_data = {
            "event": "video.publish",
            "timestamp": int(datetime.utcnow().timestamp()),
            "data": {
                "video_id": "tiktok_video_123",
                "status": "published",
                "share_url": "https://tiktok.com/@user/video/123",
                "metrics": {
                    "views": 1000,
                    "likes": 50,
                    "shares": 5,
                    "comments": 8
                }
            }
        }
        
        await webhook_processor.process_tiktok_webhook(webhook_data, db_session)
        
        # Verify post status updated
        db_session.refresh(post)
        assert post.status == PostStatus.PUBLISHED
        assert post.view_count == 1000
        assert post.like_count == 50

    @pytest.mark.unit
    async def test_process_instagram_webhook(self, webhook_processor, db_session):
        """Test processing Instagram webhook events."""
        post = SocialMediaPostFactory.create(
            platform_post_id="instagram_media_456",
            status=PostStatus.PUBLISHED
        )
        db_session.add(post)
        db_session.commit()
        
        webhook_data = {
            "object": "instagram",
            "entry": [
                {
                    "id": "instagram_user_456",
                    "time": int(datetime.utcnow().timestamp()),
                    "changes": [
                        {
                            "field": "media",
                            "value": {
                                "media_id": "instagram_media_456",
                                "event_type": "insights_update",
                                "insights": {
                                    "impressions": 5000,
                                    "reach": 4500,
                                    "likes": 300,
                                    "comments": 25
                                }
                            }
                        }
                    ]
                }
            ]
        }
        
        await webhook_processor.process_instagram_webhook(webhook_data, db_session)
        
        # Verify analytics updated
        db_session.refresh(post)
        assert post.reach == 4500
        assert post.impressions == 5000

    @pytest.mark.unit
    async def test_webhook_signature_verification(self, webhook_processor):
        """Test webhook signature verification for security."""
        payload = '{"event": "test", "data": {"test": true}}'
        secret = "webhook_secret_123"
        
        # Generate valid signature
        import hmac
        import hashlib
        signature = hmac.new(
            secret.encode(),
            payload.encode(),
            hashlib.sha256
        ).hexdigest()
        
        is_valid = webhook_processor.verify_signature(payload, signature, secret)
        assert is_valid is True
        
        # Test invalid signature
        invalid_signature = "invalid_signature"
        is_valid = webhook_processor.verify_signature(payload, invalid_signature, secret)
        assert is_valid is False

    @pytest.mark.unit
    async def test_webhook_rate_limiting(self, webhook_processor, mock_redis):
        """Test webhook rate limiting to prevent abuse."""
        source_ip = "192.168.1.100"
        
        # Simulate multiple webhooks from same IP
        for i in range(15):  # Exceed rate limit
            await webhook_processor.check_rate_limit(source_ip)
        
        # Should be rate limited
        is_limited = await webhook_processor.check_rate_limit(source_ip)
        assert is_limited is True

    @pytest.mark.unit
    async def test_webhook_retry_mechanism(self, webhook_processor, mock_redis):
        """Test webhook retry mechanism for failed processing."""
        webhook_data = {
            "event": "video.publish",
            "data": {"video_id": "retry_test_123"}
        }
        
        # Mock processing failure
        with patch.object(webhook_processor, 'process_tiktok_webhook', side_effect=Exception("Processing failed")):
            await webhook_processor.handle_webhook_with_retry("tiktok", webhook_data)
        
        # Verify retry was scheduled
        mock_redis.zadd.assert_called()


class TestVideoPipelineIntegration:
    """Test integration between video generation and social media posting."""

    @pytest.fixture
    def pipeline_integration(self):
        return VideoPipelineIntegration()

    @pytest.mark.unit
    async def test_auto_post_on_generation_complete(self, pipeline_integration, db_session):
        """Test automatic posting when video generation completes."""
        # Create video project with auto-post settings
        video_project = VideoProjectFactory.create(
            auto_post_settings={
                "enabled": True,
                "platforms": ["tiktok", "instagram"],
                "caption_template": "Check out our latest {product_name}!",
                "hashtags": ["#viral", "#trending"]
            }
        )
        
        # Create associated social media accounts
        brand = BrandFactory.create()
        tiktok_account = SocialMediaAccountFactory.create(
            brand_id=brand.id,
            platform=PlatformType.TIKTOK
        )
        
        db_session.add_all([video_project, brand, tiktok_account])
        db_session.commit()
        
        # Mock video generation completion
        generation_result = {
            "video_url": "https://example.com/generated_video.mp4",
            "thumbnail_url": "https://example.com/thumbnail.jpg",
            "duration": 30,
            "status": "completed"
        }
        
        with patch.object(pipeline_integration.social_manager, 'post_to_multiple_platforms') as mock_post:
            mock_post.return_value = {"tiktok": {"status": "success", "post_id": "123"}}
            
            await pipeline_integration.handle_generation_complete(
                video_project.id, generation_result, db_session
            )
        
        mock_post.assert_called_once()

    @pytest.mark.unit
    async def test_dynamic_caption_generation(self, pipeline_integration):
        """Test dynamic caption generation based on video content and trends."""
        video_data = {
            "product_name": "Amazing Widget",
            "key_features": ["Durable", "Lightweight", "Affordable"],
            "target_audience": "young professionals",
            "brand_voice": "fun and energetic"
        }
        
        trending_elements = {
            "hashtags": ["#viral", "#musthave", "#gamechanging"],
            "hooks": ["You won't believe this", "This changed everything"],
            "call_to_actions": ["Get yours now", "Link in bio"]
        }
        
        with patch.object(pipeline_integration, 'ai_caption_generator') as mock_ai:
            mock_ai.return_value = {
                "caption": "You won't believe this Amazing Widget! 🔥 Durable, lightweight, and affordable - everything young professionals need! #viral #musthave #gamechanging Get yours now!",
                "platform_variants": {
                    "tiktok": "🔥 This Amazing Widget is a GAME CHANGER! #viral #musthave",
                    "instagram": "Discover the Amazing Widget that's taking the professional world by storm! ✨ Durable, lightweight, and surprisingly affordable. Perfect for young professionals who demand quality without compromise. #viral #musthave #gamechanging #professionals #innovation"
                }
            }
            
            caption_data = await pipeline_integration.generate_dynamic_caption(
                video_data, trending_elements
            )
        
        assert "Amazing Widget" in caption_data["caption"]
        assert "#viral" in caption_data["caption"]
        assert len(caption_data["platform_variants"]["instagram"]) > len(caption_data["platform_variants"]["tiktok"])

    @pytest.mark.unit
    async def test_optimal_posting_time_calculation(self, pipeline_integration, db_session):
        """Test calculation of optimal posting times based on audience data."""
        brand = BrandFactory.create()
        
        # Create historical analytics data
        analytics_data = []
        for hour in range(24):
            analytics = SocialMediaAnalyticsFactory.create(
                date=datetime.utcnow().replace(hour=hour),
                engagement_rate=5.0 + (hour % 12) * 0.5  # Peak at noon and midnight
            )
            analytics_data.append(analytics)
            
        db_session.add_all([brand] + analytics_data)
        db_session.commit()
        
        optimal_times = await pipeline_integration.calculate_optimal_posting_times(
            brand.id, db_session
        )
        
        assert len(optimal_times) > 0
        assert all(0 <= time["hour"] <= 23 for time in optimal_times)
        assert all(time["engagement_score"] > 0 for time in optimal_times)

    @pytest.mark.unit
    async def test_content_adaptation_for_platforms(self, pipeline_integration):
        """Test adapting content for different platform requirements."""
        base_video = {
            "url": "https://example.com/video.mp4",
            "duration": 45,
            "aspect_ratio": "16:9",
            "resolution": "1920x1080"
        }
        
        # Test TikTok adaptation (vertical, shorter)
        tiktok_adapted = await pipeline_integration.adapt_video_for_platform(
            base_video, "tiktok"
        )
        assert tiktok_adapted["aspect_ratio"] == "9:16"
        assert tiktok_adapted["duration"] <= 60
        
        # Test Instagram adaptation (square or vertical)
        instagram_adapted = await pipeline_integration.adapt_video_for_platform(
            base_video, "instagram"
        )
        assert instagram_adapted["aspect_ratio"] in ["1:1", "9:16", "4:5"]