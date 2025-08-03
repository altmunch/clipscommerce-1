"""
Instagram Graph API Service

Handles Instagram Graph API integration for automated content posting,
account management, and analytics tracking through Facebook Business.
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


class InstagramTokenManager(TokenManager):
    """Instagram-specific token management through Facebook"""
    
    async def _refresh_token(self, account_id: str, refresh_token: str) -> str:
        """Refresh Instagram access token through Facebook Graph API"""
        url = "https://graph.facebook.com/v18.0/oauth/access_token"
        
        params = {
            "grant_type": "fb_exchange_token",
            "client_id": settings.FACEBOOK_APP_ID,
            "client_secret": settings.FACEBOOK_APP_SECRET,
            "fb_exchange_token": refresh_token
        }
        
        async with aiohttp.ClientSession() as session:
            async with session.get(url, params=params) as response:
                result = await response.json()
                
                if response.status != 200 or "access_token" not in result:
                    error_msg = result.get("error", {}).get("message", "Token refresh failed")
                    raise AuthenticationError(f"Instagram token refresh failed: {error_msg}")
                
                # Update token in database would go here
                return result["access_token"]


class InstagramService(BaseSocialMediaService):
    """Instagram Graph API service implementation"""
    
    BASE_URL = "https://graph.facebook.com/v18.0"
    GRAPH_VIDEO_URL = "https://rupload.facebook.com/video-upload/v18.0"
    
    def __init__(self):
        super().__init__(SocialMediaProvider.INSTAGRAM)
        self.app_id = settings.FACEBOOK_APP_ID
        self.app_secret = settings.FACEBOOK_APP_SECRET
        self.redirect_uri = settings.INSTAGRAM_REDIRECT_URI
        self.supported_content_types = {
            ContentType.IMAGE: ["image/jpeg", "image/png"],
            ContentType.VIDEO: ["video/mp4", "video/quicktime"],
            ContentType.REEL: ["video/mp4", "video/quicktime"],
            ContentType.STORY: ["image/jpeg", "image/png", "video/mp4"],
            ContentType.CAROUSEL: ["image/jpeg", "image/png", "video/mp4"]
        }
    
    def _create_token_manager(self) -> TokenManager:
        return InstagramTokenManager(self.provider.value)
    
    def get_auth_url(self, state: str = None) -> str:
        """Get Instagram OAuth authorization URL through Facebook"""
        params = {
            "client_id": self.app_id,
            "redirect_uri": self.redirect_uri,
            "scope": "instagram_basic,instagram_content_publish,instagram_manage_insights,pages_show_list,pages_read_engagement",
            "response_type": "code",
            "state": state or ""
        }
        
        return f"https://www.facebook.com/v18.0/dialog/oauth?{urlencode(params)}"
    
    async def authenticate(self, auth_code: str, redirect_uri: str) -> Dict[str, Any]:
        """Complete Instagram OAuth authentication flow through Facebook"""
        # Step 1: Exchange code for access token
        token_url = f"{self.BASE_URL}/oauth/access_token"
        
        token_data = {
            "client_id": self.app_id,
            "client_secret": self.app_secret,
            "redirect_uri": redirect_uri,
            "code": auth_code
        }
        
        response = await self._make_request(
            method="POST",
            url=token_url,
            data=token_data,
            endpoint_type=APIEndpointType.AUTHENTICATION
        )
        
        if not response.success:
            raise AuthenticationError(f"Instagram authentication failed: {response.error}")
        
        access_token = response.data["access_token"]
        
        # Step 2: Get user's Facebook Pages (needed for Instagram Business accounts)
        pages_response = await self._get_facebook_pages(access_token)
        
        # Step 3: Get Instagram Business accounts connected to Facebook Pages
        instagram_accounts = []
        for page in pages_response:
            instagram_account = await self._get_page_instagram_account(page["id"], page["access_token"])
            if instagram_account:
                instagram_accounts.append({
                    **instagram_account,
                    "page_id": page["id"],
                    "page_access_token": page["access_token"]
                })
        
        return {
            "access_token": access_token,
            "instagram_accounts": instagram_accounts
        }
    
    async def _get_facebook_pages(self, access_token: str) -> List[Dict[str, Any]]:
        """Get Facebook Pages connected to the user account"""
        url = f"{self.BASE_URL}/me/accounts"
        
        params = {
            "access_token": access_token,
            "fields": "id,name,access_token,category,tasks"
        }
        
        response = await self._make_request(
            method="GET",
            url=url,
            params=params,
            endpoint_type=APIEndpointType.ACCOUNT_INFO
        )
        
        if not response.success:
            raise AuthenticationError(f"Failed to get Facebook pages: {response.error}")
        
        return response.data.get("data", [])
    
    async def _get_page_instagram_account(self, page_id: str, page_access_token: str) -> Optional[Dict[str, Any]]:
        """Get Instagram Business account connected to a Facebook Page"""
        url = f"{self.BASE_URL}/{page_id}"
        
        params = {
            "access_token": page_access_token,
            "fields": "instagram_business_account"
        }
        
        response = await self._make_request(
            method="GET",
            url=url,
            params=params,
            endpoint_type=APIEndpointType.ACCOUNT_INFO
        )
        
        if response.success and "instagram_business_account" in response.data:
            ig_account_id = response.data["instagram_business_account"]["id"]
            
            # Get detailed Instagram account info
            return await self._get_instagram_account_info(ig_account_id, page_access_token)
        
        return None
    
    async def _get_instagram_account_info(self, ig_account_id: str, access_token: str) -> Dict[str, Any]:
        """Get detailed Instagram account information"""
        url = f"{self.BASE_URL}/{ig_account_id}"
        
        params = {
            "access_token": access_token,
            "fields": "id,username,name,profile_picture_url,followers_count,follows_count,media_count,account_type"
        }
        
        response = await self._make_request(
            method="GET",
            url=url,
            params=params,
            endpoint_type=APIEndpointType.ACCOUNT_INFO
        )
        
        if response.success:
            return response.data
        
        return {}
    
    async def refresh_token(self, refresh_token: str) -> Dict[str, Any]:
        """Refresh Instagram access token"""
        new_token = await self.token_manager._refresh_token("", refresh_token)
        return {"access_token": new_token}
    
    async def get_account_info(self, access_token: str, ig_account_id: str = None) -> Dict[str, Any]:
        """Get Instagram account information"""
        if not ig_account_id:
            raise AuthenticationError("Instagram account ID is required")
        
        return await self._get_instagram_account_info(ig_account_id, access_token)
    
    async def upload_media(self, access_token: str, media_file: bytes, content_type: str, ig_account_id: str) -> Dict[str, Any]:
        """Upload media to Instagram (creates container, doesn't publish)"""
        
        if content_type.startswith("image/"):
            return await self._upload_image(access_token, media_file, content_type, ig_account_id)
        elif content_type.startswith("video/"):
            return await self._upload_video(access_token, media_file, content_type, ig_account_id)
        else:
            raise ContentUploadError(f"Unsupported content type: {content_type}")
    
    async def _upload_image(self, access_token: str, image_file: bytes, content_type: str, ig_account_id: str) -> Dict[str, Any]:
        """Upload image to Instagram"""
        # For images, we need to upload to a temporary URL first
        upload_url = f"{self.BASE_URL}/{ig_account_id}/media"
        
        # Create form data for image upload
        data = aiohttp.FormData()
        data.add_field('access_token', access_token)
        data.add_field('image', image_file, content_type=content_type)
        
        response = await self._make_request(
            method="POST",
            url=upload_url,
            data=data,
            endpoint_type=APIEndpointType.CONTENT_UPLOAD
        )
        
        if not response.success:
            raise ContentUploadError(f"Instagram image upload failed: {response.error}")
        
        return {"container_id": response.data["id"]}
    
    async def _upload_video(self, access_token: str, video_file: bytes, content_type: str, ig_account_id: str) -> Dict[str, Any]:
        """Upload video to Instagram using resumable upload"""
        # Step 1: Initialize upload session
        init_url = f"{self.GRAPH_VIDEO_URL}/{ig_account_id}/videos"
        
        init_data = {
            "access_token": access_token,
            "upload_phase": "start",
            "file_size": len(video_file)
        }
        
        response = await self._make_request(
            method="POST",
            url=init_url,
            data=init_data,
            endpoint_type=APIEndpointType.CONTENT_UPLOAD
        )
        
        if not response.success:
            raise ContentUploadError(f"Instagram video upload initialization failed: {response.error}")
        
        video_id = response.data["video_id"]
        upload_url = response.data["upload_url"]
        
        # Step 2: Upload video data
        headers = {
            "Authorization": f"OAuth {access_token}",
            "offset": "0",
            "file_size": str(len(video_file))
        }
        
        upload_response = await self._make_request(
            method="POST",
            url=upload_url,
            data=video_file,
            headers=headers,
            endpoint_type=APIEndpointType.CONTENT_UPLOAD
        )
        
        if not upload_response.success:
            raise ContentUploadError(f"Instagram video data upload failed: {upload_response.error}")
        
        # Step 3: Finish upload
        finish_data = {
            "access_token": access_token,
            "upload_phase": "finish",
            "video_id": video_id
        }
        
        finish_response = await self._make_request(
            method="POST",
            url=init_url,
            data=finish_data,
            endpoint_type=APIEndpointType.CONTENT_UPLOAD
        )
        
        if not finish_response.success:
            raise ContentUploadError(f"Instagram video upload finish failed: {finish_response.error}")
        
        return {"container_id": video_id}
    
    async def publish_post(self, access_token: str, request: PostingRequest, ig_account_id: str) -> Dict[str, Any]:
        """Publish content to Instagram"""
        
        if request.content_type == ContentType.CAROUSEL:
            return await self._publish_carousel(access_token, request, ig_account_id)
        elif request.content_type == ContentType.STORY:
            return await self._publish_story(access_token, request, ig_account_id)
        elif request.content_type == ContentType.REEL:
            return await self._publish_reel(access_token, request, ig_account_id)
        else:
            return await self._publish_single_media(access_token, request, ig_account_id)
    
    async def _publish_single_media(self, access_token: str, request: PostingRequest, ig_account_id: str) -> Dict[str, Any]:
        """Publish single image or video post"""
        url = f"{self.BASE_URL}/{ig_account_id}/media"
        
        # Prepare post data
        post_data = {
            "access_token": access_token,
            "caption": self._format_caption(request.caption, request.hashtags),
        }
        
        # Handle media URL (should be container ID from upload)
        if request.media_urls:
            if request.content_type == ContentType.VIDEO:
                post_data["video_url"] = request.media_urls[0]
                post_data["media_type"] = "VIDEO"
            else:
                post_data["image_url"] = request.media_urls[0]
                post_data["media_type"] = "IMAGE"
        
        # Add location if provided
        if request.location_tag:
            post_data["location_id"] = request.location_tag
        
        # Create media container
        response = await self._make_request(
            method="POST",
            url=url,
            data=post_data,
            endpoint_type=APIEndpointType.CONTENT_PUBLISH
        )
        
        if not response.success:
            raise PublishingError(f"Instagram media container creation failed: {response.error}")
        
        container_id = response.data["id"]
        
        # Publish the container
        return await self._publish_container(access_token, container_id, ig_account_id)
    
    async def _publish_carousel(self, access_token: str, request: PostingRequest, ig_account_id: str) -> Dict[str, Any]:
        """Publish carousel post with multiple media items"""
        url = f"{self.BASE_URL}/{ig_account_id}/media"
        
        # Create individual media containers first
        children_ids = []
        for media_url in request.media_urls:
            child_data = {
                "access_token": access_token,
                "image_url": media_url,  # Assuming images for carousel
                "is_carousel_item": "true"
            }
            
            child_response = await self._make_request(
                method="POST",
                url=url,
                data=child_data,
                endpoint_type=APIEndpointType.CONTENT_PUBLISH
            )
            
            if child_response.success:
                children_ids.append(child_response.data["id"])
        
        # Create carousel container
        carousel_data = {
            "access_token": access_token,
            "media_type": "CAROUSEL",
            "children": ",".join(children_ids),
            "caption": self._format_caption(request.caption, request.hashtags)
        }
        
        carousel_response = await self._make_request(
            method="POST",
            url=url,
            data=carousel_data,
            endpoint_type=APIEndpointType.CONTENT_PUBLISH
        )
        
        if not carousel_response.success:
            raise PublishingError(f"Instagram carousel creation failed: {carousel_response.error}")
        
        container_id = carousel_response.data["id"]
        
        # Publish the carousel
        return await self._publish_container(access_token, container_id, ig_account_id)
    
    async def _publish_story(self, access_token: str, request: PostingRequest, ig_account_id: str) -> Dict[str, Any]:
        """Publish Instagram Story"""
        url = f"{self.BASE_URL}/{ig_account_id}/media"
        
        story_data = {
            "access_token": access_token,
            "media_type": "STORIES"
        }
        
        # Add media URL
        if request.media_urls:
            if request.content_type == ContentType.VIDEO:
                story_data["video_url"] = request.media_urls[0]
            else:
                story_data["image_url"] = request.media_urls[0]
        
        response = await self._make_request(
            method="POST",
            url=url,
            data=story_data,
            endpoint_type=APIEndpointType.CONTENT_PUBLISH
        )
        
        if not response.success:
            raise PublishingError(f"Instagram story creation failed: {response.error}")
        
        container_id = response.data["id"]
        
        # Publish the story
        return await self._publish_container(access_token, container_id, ig_account_id)
    
    async def _publish_reel(self, access_token: str, request: PostingRequest, ig_account_id: str) -> Dict[str, Any]:
        """Publish Instagram Reel"""
        url = f"{self.BASE_URL}/{ig_account_id}/media"
        
        reel_data = {
            "access_token": access_token,
            "media_type": "REELS",
            "video_url": request.media_urls[0] if request.media_urls else "",
            "caption": self._format_caption(request.caption, request.hashtags)
        }
        
        # Add reel-specific settings
        if request.platform_settings:
            reel_data.update(request.platform_settings)
        
        response = await self._make_request(
            method="POST",
            url=url,
            data=reel_data,
            endpoint_type=APIEndpointType.CONTENT_PUBLISH
        )
        
        if not response.success:
            raise PublishingError(f"Instagram reel creation failed: {response.error}")
        
        container_id = response.data["id"]
        
        # Publish the reel
        return await self._publish_container(access_token, container_id, ig_account_id)
    
    async def _publish_container(self, access_token: str, container_id: str, ig_account_id: str) -> Dict[str, Any]:
        """Publish a media container"""
        url = f"{self.BASE_URL}/{ig_account_id}/media_publish"
        
        publish_data = {
            "access_token": access_token,
            "creation_id": container_id
        }
        
        response = await self._make_request(
            method="POST",
            url=url,
            data=publish_data,
            endpoint_type=APIEndpointType.CONTENT_PUBLISH
        )
        
        if not response.success:
            raise PublishingError(f"Instagram container publish failed: {response.error}")
        
        return response.data
    
    def _format_caption(self, caption: Optional[str], hashtags: Optional[List[str]]) -> str:
        """Format caption with hashtags"""
        formatted_caption = caption or ""
        
        if hashtags:
            hashtag_text = " ".join([f"#{tag.lstrip('#')}" for tag in hashtags])
            formatted_caption = f"{formatted_caption} {hashtag_text}".strip()
        
        return formatted_caption
    
    async def get_analytics(self, access_token: str, request: AnalyticsRequest, ig_account_id: str) -> Dict[str, Any]:
        """Get analytics data from Instagram"""
        analytics_data = {}
        
        # Get account insights
        account_insights = await self._get_account_insights(access_token, ig_account_id, request)
        analytics_data["account"] = account_insights
        
        # Get media insights
        if request.post_ids:
            media_insights = {}
            for post_id in request.post_ids:
                media_insight = await self._get_media_insights(access_token, post_id, request)
                media_insights[post_id] = media_insight
            analytics_data["media"] = media_insights
        else:
            # Get recent media insights
            recent_media = await self._get_recent_media(access_token, ig_account_id)
            media_insights = {}
            for media in recent_media[:10]:  # Limit to prevent rate limiting
                media_insight = await self._get_media_insights(access_token, media["id"], request)
                media_insights[media["id"]] = media_insight
            analytics_data["media"] = media_insights
        
        return analytics_data
    
    async def _get_account_insights(self, access_token: str, ig_account_id: str, request: AnalyticsRequest) -> Dict[str, Any]:
        """Get Instagram account insights"""
        url = f"{self.BASE_URL}/{ig_account_id}/insights"
        
        # Calculate date range
        end_date = request.end_date or datetime.utcnow()
        start_date = request.start_date or (end_date - timedelta(days=30))
        
        metrics = request.metrics or [
            "impressions", "reach", "profile_views", "website_clicks",
            "follower_count", "email_contacts", "phone_call_clicks"
        ]
        
        params = {
            "access_token": access_token,
            "metric": ",".join(metrics),
            "period": "day",
            "since": start_date.strftime("%Y-%m-%d"),
            "until": end_date.strftime("%Y-%m-%d")
        }
        
        response = await self._make_request(
            method="GET",
            url=url,
            params=params,
            endpoint_type=APIEndpointType.ANALYTICS
        )
        
        if response.success:
            return response.data.get("data", [])
        else:
            logger.warning(f"Failed to get account insights: {response.error}")
            return []
    
    async def _get_media_insights(self, access_token: str, media_id: str, request: AnalyticsRequest) -> Dict[str, Any]:
        """Get insights for specific media"""
        url = f"{self.BASE_URL}/{media_id}/insights"
        
        metrics = request.metrics or [
            "impressions", "reach", "likes", "comments", "shares", "saves"
        ]
        
        params = {
            "access_token": access_token,
            "metric": ",".join(metrics)
        }
        
        response = await self._make_request(
            method="GET",
            url=url,
            params=params,
            endpoint_type=APIEndpointType.ANALYTICS
        )
        
        if response.success:
            return response.data.get("data", [])
        else:
            logger.warning(f"Failed to get media insights for {media_id}: {response.error}")
            return []
    
    async def _get_recent_media(self, access_token: str, ig_account_id: str, limit: int = 25) -> List[Dict[str, Any]]:
        """Get recent media posts"""
        url = f"{self.BASE_URL}/{ig_account_id}/media"
        
        params = {
            "access_token": access_token,
            "fields": "id,media_type,media_url,caption,timestamp,like_count,comments_count",
            "limit": str(limit)
        }
        
        response = await self._make_request(
            method="GET",
            url=url,
            params=params,
            endpoint_type=APIEndpointType.ANALYTICS
        )
        
        if response.success:
            return response.data.get("data", [])
        else:
            return []
    
    async def process_webhook(self, payload: Dict[str, Any], headers: Dict[str, str]) -> Dict[str, Any]:
        """Process Instagram webhook payload"""
        # Verify webhook signature
        if not self._verify_webhook_signature(payload, headers):
            raise WebhookError("Invalid webhook signature")
        
        processed_events = []
        
        # Instagram webhooks come through Facebook's format
        for entry in payload.get("entry", []):
            for change in entry.get("changes", []):
                processed_event = await self._process_webhook_change(change)
                if processed_event:
                    processed_events.append(processed_event)
        
        return {
            "processed_events": processed_events,
            "timestamp": datetime.utcnow().isoformat()
        }
    
    def _verify_webhook_signature(self, payload: Dict[str, Any], headers: Dict[str, str]) -> bool:
        """Verify Instagram/Facebook webhook signature"""
        signature = headers.get("X-Hub-Signature-256", "")
        
        if not signature:
            return False
        
        # Remove 'sha256=' prefix
        signature = signature.replace("sha256=", "")
        
        # Calculate expected signature
        payload_str = json.dumps(payload, separators=(',', ':'))
        expected_signature = hmac.new(
            self.app_secret.encode(),
            payload_str.encode(),
            hashlib.sha256
        ).hexdigest()
        
        return hmac.compare_digest(signature, expected_signature)
    
    async def _process_webhook_change(self, change: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Process individual webhook change"""
        field = change.get("field", "")
        value = change.get("value", {})
        
        if field == "comments":
            return await self._process_comment_event(value)
        elif field == "mentions":
            return await self._process_mention_event(value)
        elif field == "story_insights":
            return await self._process_story_insights_event(value)
        else:
            logger.info(f"Unhandled Instagram webhook field: {field}")
            return None
    
    async def _process_comment_event(self, value: Dict[str, Any]) -> Dict[str, Any]:
        """Process comment webhook event"""
        return {
            "event": "comment",
            "media_id": value.get("media_id"),
            "comment_id": value.get("id"),
            "text": value.get("text"),
            "processed_at": datetime.utcnow().isoformat()
        }
    
    async def _process_mention_event(self, value: Dict[str, Any]) -> Dict[str, Any]:
        """Process mention webhook event"""
        return {
            "event": "mention",
            "media_id": value.get("media_id"),
            "mention_id": value.get("id"),
            "processed_at": datetime.utcnow().isoformat()
        }
    
    async def _process_story_insights_event(self, value: Dict[str, Any]) -> Dict[str, Any]:
        """Process story insights webhook event"""
        return {
            "event": "story_insights",
            "media_id": value.get("media_id"),
            "insights": value.get("insights", {}),
            "processed_at": datetime.utcnow().isoformat()
        }