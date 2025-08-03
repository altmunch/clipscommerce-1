"""
TikTok Business API Service

Handles TikTok Business API integration for automated video posting,
account management, and analytics tracking.
"""

import asyncio
import json
import hmac
import hashlib
import base64
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Union
import logging
import aiohttp
from urllib.parse import urlencode, parse_qs

from .base_service import (
    BaseSocialMediaService, TokenManager, SocialMediaResponse, PostingRequest,
    AnalyticsRequest, SocialMediaProvider, APIEndpointType, AuthenticationError,
    RateLimitError, ContentUploadError, PublishingError, AnalyticsError, WebhookError
)
from app.core.config import settings
from app.models.social_media import ContentType

logger = logging.getLogger(__name__)


class TikTokTokenManager(TokenManager):
    """TikTok-specific token management"""
    
    async def _refresh_token(self, account_id: str, refresh_token: str) -> str:
        """Refresh TikTok access token"""
        url = "https://business-api.tiktok.com/open_api/v1.3/oauth2/refresh_token/"
        
        data = {
            "app_id": settings.TIKTOK_APP_ID,
            "secret": settings.TIKTOK_APP_SECRET,
            "refresh_token": refresh_token
        }
        
        async with aiohttp.ClientSession() as session:
            async with session.post(url, json=data) as response:
                result = await response.json()
                
                if response.status != 200 or result.get("code") != 0:
                    error_msg = result.get("message", "Token refresh failed")
                    raise AuthenticationError(f"TikTok token refresh failed: {error_msg}")
                
                # Update token in database would go here
                return result["data"]["access_token"]


class TikTokService(BaseSocialMediaService):
    """TikTok Business API service implementation"""
    
    BASE_URL = "https://business-api.tiktok.com/open_api/v1.3"
    UPLOAD_URL = "https://open-api.tiktok.com/share/v1"
    
    def __init__(self):
        super().__init__(SocialMediaProvider.TIKTOK)
        self.app_id = settings.TIKTOK_APP_ID
        self.app_secret = settings.TIKTOK_APP_SECRET
        self.redirect_uri = settings.TIKTOK_REDIRECT_URI
    
    def _create_token_manager(self) -> TokenManager:
        return TikTokTokenManager(self.provider.value)
    
    def get_auth_url(self, state: str = None) -> str:
        """Get TikTok OAuth authorization URL"""
        params = {
            "client_key": self.app_id,
            "response_type": "code",
            "scope": "user.info.basic,video.upload,video.publish,business.get",
            "redirect_uri": self.redirect_uri,
            "state": state or ""
        }
        
        return f"https://www.tiktok.com/auth/authorize/?{urlencode(params)}"
    
    async def authenticate(self, auth_code: str, redirect_uri: str) -> Dict[str, Any]:
        """Complete TikTok OAuth authentication flow"""
        url = f"{self.BASE_URL}/oauth2/access_token/"
        
        data = {
            "client_key": self.app_id,
            "client_secret": self.app_secret,
            "code": auth_code,
            "grant_type": "authorization_code",
            "redirect_uri": redirect_uri
        }
        
        response = await self._make_request(
            method="POST",
            url=url,
            data=json.dumps(data),
            headers={"Content-Type": "application/json"},
            endpoint_type=APIEndpointType.AUTHENTICATION
        )
        
        if not response.success:
            raise AuthenticationError(f"TikTok authentication failed: {response.error}")
        
        return response.data["data"]
    
    async def refresh_token(self, refresh_token: str) -> Dict[str, Any]:
        """Refresh TikTok access token"""
        return await self.token_manager._refresh_token("", refresh_token)
    
    async def get_account_info(self, access_token: str) -> Dict[str, Any]:
        """Get TikTok account information"""
        url = f"{self.BASE_URL}/user/info/"
        
        params = {
            "access_token": access_token,
            "fields": "open_id,union_id,avatar_url,display_name,follower_count,following_count,likes_count,video_count"
        }
        
        response = await self._make_request(
            method="GET",
            url=url,
            params=params,
            endpoint_type=APIEndpointType.ACCOUNT_INFO
        )
        
        if not response.success:
            raise AuthenticationError(f"Failed to get TikTok account info: {response.error}")
        
        return response.data["data"]
    
    async def upload_media(self, access_token: str, media_file: bytes, content_type: str) -> Dict[str, Any]:
        """Upload video to TikTok"""
        # Step 1: Initialize upload
        init_url = f"{self.UPLOAD_URL}/video/init/"
        
        init_data = {
            "source_info": {
                "source": "FILE_UPLOAD",
                "video_size": len(media_file),
                "chunk_size": 10485760,  # 10MB chunks
                "total_chunk_count": (len(media_file) + 10485759) // 10485760
            }
        }
        
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json; charset=UTF-8"
        }
        
        response = await self._make_request(
            method="POST",
            url=init_url,
            data=json.dumps(init_data),
            headers=headers,
            endpoint_type=APIEndpointType.CONTENT_UPLOAD
        )
        
        if not response.success:
            raise ContentUploadError(f"TikTok upload initialization failed: {response.error}")
        
        upload_id = response.data["data"]["upload_id"]
        upload_url = response.data["data"]["upload_url"]
        
        # Step 2: Upload video chunks
        chunk_size = 10485760  # 10MB
        total_chunks = (len(media_file) + chunk_size - 1) // chunk_size
        
        for i in range(total_chunks):
            start = i * chunk_size
            end = min(start + chunk_size, len(media_file))
            chunk = media_file[start:end]
            
            chunk_headers = {
                "Authorization": f"Bearer {access_token}",
                "Content-Type": "video/mp4",
                "Content-Range": f"bytes {start}-{end-1}/{len(media_file)}"
            }
            
            chunk_response = await self._make_request(
                method="PUT",
                url=upload_url,
                data=chunk,
                headers=chunk_headers,
                endpoint_type=APIEndpointType.CONTENT_UPLOAD
            )
            
            if not chunk_response.success:
                raise ContentUploadError(f"TikTok chunk upload failed: {chunk_response.error}")
        
        return {"upload_id": upload_id}
    
    async def publish_post(self, access_token: str, request: PostingRequest) -> Dict[str, Any]:
        """Publish video to TikTok"""
        url = f"{self.UPLOAD_URL}/video/publish/"
        
        # Build video info
        video_info = {
            "title": request.caption or "",
            "privacy_level": request.platform_settings.get("privacy_level", "SELF_ONLY") if request.platform_settings else "SELF_ONLY",
            "disable_duet": request.platform_settings.get("disable_duet", False) if request.platform_settings else False,
            "disable_comment": request.platform_settings.get("disable_comment", False) if request.platform_settings else False,
            "disable_stitch": request.platform_settings.get("disable_stitch", False) if request.platform_settings else False,
            "video_cover_timestamp_ms": request.platform_settings.get("cover_timestamp", 1000) if request.platform_settings else 1000
        }
        
        # Add auto-generated hashtags if provided
        if request.hashtags:
            hashtag_text = " ".join([f"#{tag.lstrip('#')}" for tag in request.hashtags])
            video_info["title"] = f"{video_info['title']} {hashtag_text}".strip()
        
        post_data = {
            "source_info": {
                "source": "FILE_UPLOAD",
                "video_id": request.media_urls[0] if request.media_urls else ""  # This should be the upload_id
            },
            "post_info": video_info
        }
        
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json; charset=UTF-8"
        }
        
        response = await self._make_request(
            method="POST",
            url=url,
            data=json.dumps(post_data),
            headers=headers,
            endpoint_type=APIEndpointType.CONTENT_PUBLISH
        )
        
        if not response.success:
            raise PublishingError(f"TikTok publish failed: {response.error}")
        
        return response.data["data"]
    
    async def get_video_list(self, access_token: str, cursor: str = "0", max_count: int = 20) -> Dict[str, Any]:
        """Get list of published videos"""
        url = f"{self.BASE_URL}/video/list/"
        
        params = {
            "access_token": access_token,
            "cursor": cursor,
            "max_count": str(max_count),
            "fields": "id,title,duration,cover_image_url,embed_link,like_count,comment_count,share_count,view_count"
        }
        
        response = await self._make_request(
            method="GET",
            url=url,
            params=params,
            endpoint_type=APIEndpointType.ANALYTICS
        )
        
        if not response.success:
            raise AnalyticsError(f"Failed to get TikTok video list: {response.error}")
        
        return response.data["data"]
    
    async def get_analytics(self, access_token: str, request: AnalyticsRequest) -> Dict[str, Any]:
        """Get analytics data from TikTok"""
        analytics_data = {}
        
        # Get video list if specific post IDs not provided
        if not request.post_ids:
            video_list_response = await self.get_video_list(access_token, max_count=100)
            video_ids = [video["id"] for video in video_list_response.get("videos", [])]
        else:
            video_ids = request.post_ids
        
        # Get detailed analytics for each video
        for video_id in video_ids[:10]:  # Limit to prevent rate limiting
            video_analytics = await self._get_video_analytics(access_token, video_id, request)
            analytics_data[video_id] = video_analytics
        
        return {
            "videos": analytics_data,
            "summary": self._calculate_analytics_summary(analytics_data)
        }
    
    async def _get_video_analytics(self, access_token: str, video_id: str, request: AnalyticsRequest) -> Dict[str, Any]:
        """Get analytics for a specific video"""
        url = f"{self.BASE_URL}/video/insights/"
        
        # Calculate date range
        end_date = request.end_date or datetime.utcnow()
        start_date = request.start_date or (end_date - timedelta(days=30))
        
        params = {
            "access_token": access_token,
            "video_id": video_id,
            "start_date": start_date.strftime("%Y-%m-%d"),
            "end_date": end_date.strftime("%Y-%m-%d"),
            "metrics": ",".join(request.metrics) if request.metrics else "video_view,like_count,comment_count,share_count,profile_view,follows"
        }
        
        response = await self._make_request(
            method="GET",
            url=url,
            params=params,
            endpoint_type=APIEndpointType.ANALYTICS
        )
        
        if response.success:
            return response.data.get("data", {})
        else:
            logger.warning(f"Failed to get analytics for video {video_id}: {response.error}")
            return {}
    
    def _calculate_analytics_summary(self, analytics_data: Dict[str, Dict]) -> Dict[str, Any]:
        """Calculate summary analytics from individual video data"""
        total_views = 0
        total_likes = 0
        total_comments = 0
        total_shares = 0
        video_count = len(analytics_data)
        
        for video_data in analytics_data.values():
            metrics = video_data.get("metrics", {})
            total_views += metrics.get("video_view", 0)
            total_likes += metrics.get("like_count", 0)
            total_comments += metrics.get("comment_count", 0)
            total_shares += metrics.get("share_count", 0)
        
        engagement_rate = 0.0
        if total_views > 0:
            engagement_rate = ((total_likes + total_comments + total_shares) / total_views) * 100
        
        return {
            "total_videos": video_count,
            "total_views": total_views,
            "total_likes": total_likes,
            "total_comments": total_comments,
            "total_shares": total_shares,
            "average_views": total_views / video_count if video_count > 0 else 0,
            "engagement_rate": engagement_rate
        }
    
    async def process_webhook(self, payload: Dict[str, Any], headers: Dict[str, str]) -> Dict[str, Any]:
        """Process TikTok webhook payload"""
        # Verify webhook signature
        if not self._verify_webhook_signature(payload, headers):
            raise WebhookError("Invalid webhook signature")
        
        event_type = payload.get("type", "")
        timestamp = payload.get("timestamp", 0)
        
        processed_events = []
        
        # Process different event types
        if event_type == "VIDEO_PUBLISH":
            processed_events.append(await self._process_video_publish_event(payload))
        elif event_type == "VIDEO_INSIGHTS":
            processed_events.append(await self._process_video_insights_event(payload))
        elif event_type == "ACCOUNT_UPDATE":
            processed_events.append(await self._process_account_update_event(payload))
        else:
            logger.warning(f"Unknown TikTok webhook event type: {event_type}")
        
        return {
            "processed_events": processed_events,
            "event_type": event_type,
            "timestamp": timestamp
        }
    
    def _verify_webhook_signature(self, payload: Dict[str, Any], headers: Dict[str, str]) -> bool:
        """Verify TikTok webhook signature"""
        signature = headers.get("X-TikTok-Signature", "")
        timestamp = headers.get("X-Timestamp", "")
        
        if not signature or not timestamp:
            return False
        
        # Create expected signature
        message = f"{timestamp}.{json.dumps(payload, separators=(',', ':'))}"
        expected_signature = hmac.new(
            self.app_secret.encode(),
            message.encode(),
            hashlib.sha256
        ).hexdigest()
        
        return hmac.compare_digest(signature, expected_signature)
    
    async def _process_video_publish_event(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Process video publish event"""
        video_data = payload.get("data", {})
        video_id = video_data.get("video_id", "")
        status = video_data.get("status", "")
        
        return {
            "event": "video_publish",
            "video_id": video_id,
            "status": status,
            "processed_at": datetime.utcnow().isoformat()
        }
    
    async def _process_video_insights_event(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Process video insights update event"""
        insights_data = payload.get("data", {})
        video_id = insights_data.get("video_id", "")
        metrics = insights_data.get("metrics", {})
        
        return {
            "event": "video_insights",
            "video_id": video_id,
            "metrics": metrics,
            "processed_at": datetime.utcnow().isoformat()
        }
    
    async def _process_account_update_event(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Process account update event"""
        account_data = payload.get("data", {})
        account_id = account_data.get("account_id", "")
        changes = account_data.get("changes", {})
        
        return {
            "event": "account_update",
            "account_id": account_id,
            "changes": changes,
            "processed_at": datetime.utcnow().isoformat()
        }
    
    async def get_posting_insights(self, access_token: str, days: int = 30) -> Dict[str, Any]:
        """Get insights for optimal posting times and content strategy"""
        # This would analyze historical performance to suggest optimal posting times
        url = f"{self.BASE_URL}/business/get/"
        
        params = {
            "access_token": access_token,
            "advertiser_ids": "[\"advertiser_id\"]",  # Would be actual advertiser ID
            "fields": "[\"audience_insight\",\"video_insight\"]"
        }
        
        response = await self._make_request(
            method="GET",
            url=url,
            params=params,
            endpoint_type=APIEndpointType.ANALYTICS
        )
        
        if response.success:
            return self._analyze_posting_insights(response.data)
        else:
            return {
                "optimal_times": ["20:00", "21:00", "22:00"],  # Default suggestions
                "suggested_hashtags": ["#fyp", "#viral", "#trending"],
                "content_strategy": "Focus on trending sounds and effects"
            }
    
    def _analyze_posting_insights(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze data to provide posting insights"""
        # Placeholder for analytics processing
        return {
            "optimal_times": ["19:00", "20:00", "21:00"],
            "optimal_days": ["Tuesday", "Wednesday", "Thursday"],
            "suggested_hashtags": ["#fyp", "#viral", "#trending"],
            "audience_demographics": data.get("audience_insight", {}),
            "content_strategy": "Focus on entertainment and educational content",
            "recommended_duration": "15-30 seconds for maximum engagement"
        }