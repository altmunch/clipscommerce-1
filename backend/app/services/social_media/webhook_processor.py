"""
Social Media Webhook Processor

Handles incoming webhooks from social media platforms for real-time updates
on post performance, account changes, and engagement metrics.
"""

import asyncio
import json
from datetime import datetime
from typing import Any, Dict, List, Optional
import logging

from sqlalchemy.orm import Session
from sqlalchemy import and_

from .tiktok_service import TikTokService
from .instagram_service import InstagramService
from app.models.social_media import (
    SocialMediaAccount, SocialMediaPost, SocialMediaAnalytics, SocialMediaWebhook,
    PlatformType, PostStatus
)
from app.core.config import settings

logger = logging.getLogger(__name__)


class WebhookProcessor:
    """Central webhook processor for all social media platforms"""
    
    def __init__(self, db: Session):
        self.db = db
        self.platform_services = {
            PlatformType.TIKTOK: TikTokService(),
            PlatformType.INSTAGRAM: InstagramService()
        }
    
    async def process_webhook(
        self,
        platform: PlatformType,
        payload: Dict[str, Any],
        headers: Dict[str, str]
    ) -> Dict[str, Any]:
        """Process webhook from a specific platform"""
        
        # Log incoming webhook
        webhook_record = SocialMediaWebhook(
            platform=platform,
            event_type=self._extract_event_type(platform, payload),
            event_data=payload,
            processed=False
        )
        
        self.db.add(webhook_record)
        self.db.commit()
        self.db.refresh(webhook_record)
        
        try:
            # Get platform service
            service = self.platform_services[platform]
            
            # Process webhook with platform-specific service
            processing_result = await service.process_webhook(payload, headers)
            
            # Handle processed events
            await self._handle_processed_events(platform, processing_result, webhook_record.id)
            
            # Mark webhook as processed
            webhook_record.processed = True
            webhook_record.processed_at = datetime.utcnow()
            self.db.commit()
            
            logger.info(f"Successfully processed {platform.value} webhook: {webhook_record.event_type}")
            
            return {
                "success": True,
                "webhook_id": webhook_record.id,
                "events_processed": len(processing_result.get("processed_events", [])),
                "platform": platform.value
            }
            
        except Exception as e:
            # Mark webhook as failed
            webhook_record.processing_error = str(e)
            webhook_record.processed_at = datetime.utcnow()
            self.db.commit()
            
            logger.error(f"Failed to process {platform.value} webhook: {e}")
            
            return {
                "success": False,
                "webhook_id": webhook_record.id,
                "error": str(e),
                "platform": platform.value
            }
    
    def _extract_event_type(self, platform: PlatformType, payload: Dict[str, Any]) -> str:
        """Extract event type from webhook payload"""
        
        if platform == PlatformType.TIKTOK:
            return payload.get("type", "unknown")
        
        elif platform == PlatformType.INSTAGRAM:
            # Instagram webhooks come through Facebook format
            if "entry" in payload:
                entries = payload["entry"]
                if entries and len(entries) > 0:
                    changes = entries[0].get("changes", [])
                    if changes and len(changes) > 0:
                        return changes[0].get("field", "unknown")
            return "unknown"
        
        return "unknown"
    
    async def _handle_processed_events(
        self,
        platform: PlatformType,
        processing_result: Dict[str, Any],
        webhook_id: int
    ):
        """Handle the processed events from webhook"""
        
        processed_events = processing_result.get("processed_events", [])
        
        for event in processed_events:
            event_type = event.get("event", "")
            
            try:
                if event_type == "video_publish":
                    await self._handle_video_publish_event(platform, event, webhook_id)
                
                elif event_type == "video_insights":
                    await self._handle_video_insights_event(platform, event, webhook_id)
                
                elif event_type == "account_update":
                    await self._handle_account_update_event(platform, event, webhook_id)
                
                elif event_type == "comment":
                    await self._handle_comment_event(platform, event, webhook_id)
                
                elif event_type == "mention":
                    await self._handle_mention_event(platform, event, webhook_id)
                
                elif event_type == "story_insights":
                    await self._handle_story_insights_event(platform, event, webhook_id)
                
                else:
                    logger.warning(f"Unhandled event type: {event_type}")
            
            except Exception as e:
                logger.error(f"Failed to handle event {event_type}: {e}")
    
    async def _handle_video_publish_event(
        self,
        platform: PlatformType,
        event: Dict[str, Any],
        webhook_id: int
    ):
        """Handle video publish status update"""
        
        video_id = event.get("video_id", "")
        status = event.get("status", "")
        
        if not video_id:
            return
        
        # Find the corresponding post in our database
        post = self.db.query(SocialMediaPost).join(SocialMediaAccount).filter(
            and_(
                SocialMediaPost.platform_post_id == video_id,
                SocialMediaAccount.platform == platform
            )
        ).first()
        
        if post:
            # Update post status based on webhook
            if status == "published":
                post.status = PostStatus.PUBLISHED
                post.published_at = datetime.utcnow()
            elif status == "failed":
                post.status = PostStatus.FAILED
                post.error_message = "Publishing failed (webhook notification)"
            elif status == "processing":
                post.status = PostStatus.PUBLISHING
            
            # Link webhook to post
            webhook = self.db.query(SocialMediaWebhook).get(webhook_id)
            if webhook:
                webhook.post_id = post.id
            
            self.db.commit()
            
            logger.info(f"Updated post {post.id} status to {post.status} based on webhook")
    
    async def _handle_video_insights_event(
        self,
        platform: PlatformType,
        event: Dict[str, Any],
        webhook_id: int
    ):
        """Handle video insights/analytics update"""
        
        video_id = event.get("video_id", "")
        metrics = event.get("metrics", {})
        
        if not video_id or not metrics:
            return
        
        # Find the corresponding post
        post = self.db.query(SocialMediaPost).join(SocialMediaAccount).filter(
            and_(
                SocialMediaPost.platform_post_id == video_id,
                SocialMediaAccount.platform == platform
            )
        ).first()
        
        if post:
            # Update post metrics
            if platform == PlatformType.TIKTOK:
                post.view_count = metrics.get("video_view", post.view_count)
                post.like_count = metrics.get("like_count", post.like_count)
                post.comment_count = metrics.get("comment_count", post.comment_count)
                post.share_count = metrics.get("share_count", post.share_count)
            
            elif platform == PlatformType.INSTAGRAM:
                post.view_count = metrics.get("video_views", post.view_count)
                post.like_count = metrics.get("likes", post.like_count)
                post.comment_count = metrics.get("comments", post.comment_count)
                post.share_count = metrics.get("shares", post.share_count)
                post.reach = metrics.get("reach", post.reach)
                post.impressions = metrics.get("impressions", post.impressions)
            
            # Calculate engagement rate
            if post.view_count > 0:
                total_engagement = post.like_count + post.comment_count + post.share_count
                post.engagement_rate = (total_engagement / post.view_count) * 100
            
            # Create/update analytics record
            await self._create_analytics_record(post, metrics)
            
            self.db.commit()
            
            logger.info(f"Updated metrics for post {post.id} from webhook")
    
    async def _handle_account_update_event(
        self,
        platform: PlatformType,
        event: Dict[str, Any],
        webhook_id: int
    ):
        """Handle account information update"""
        
        account_id = event.get("account_id", "")
        changes = event.get("changes", {})
        
        if not account_id:
            return
        
        # Find the corresponding account
        account = self.db.query(SocialMediaAccount).filter(
            and_(
                SocialMediaAccount.platform_account_id == account_id,
                SocialMediaAccount.platform == platform
            )
        ).first()
        
        if account:
            # Update account information based on changes
            if "follower_count" in changes:
                account.follower_count = changes["follower_count"]
            
            if "following_count" in changes:
                account.following_count = changes["following_count"]
            
            if "display_name" in changes:
                account.display_name = changes["display_name"]
            
            if "profile_picture_url" in changes:
                account.profile_picture_url = changes["profile_picture_url"]
            
            account.last_sync_at = datetime.utcnow()
            self.db.commit()
            
            logger.info(f"Updated account {account.username} from webhook")
    
    async def _handle_comment_event(
        self,
        platform: PlatformType,
        event: Dict[str, Any],
        webhook_id: int
    ):
        """Handle new comment notification"""
        
        media_id = event.get("media_id", "")
        comment_id = event.get("comment_id", "")
        comment_text = event.get("text", "")
        
        if not media_id:
            return
        
        # Find the corresponding post
        post = self.db.query(SocialMediaPost).join(SocialMediaAccount).filter(
            and_(
                SocialMediaPost.platform_post_id == media_id,
                SocialMediaAccount.platform == platform
            )
        ).first()
        
        if post:
            # Increment comment count
            post.comment_count += 1
            
            # Update engagement rate
            if post.view_count > 0:
                total_engagement = post.like_count + post.comment_count + post.share_count
                post.engagement_rate = (total_engagement / post.view_count) * 100
            
            self.db.commit()
            
            # Here you could implement comment moderation, auto-replies, etc.
            logger.info(f"New comment on post {post.id}: {comment_text[:50]}...")
    
    async def _handle_mention_event(
        self,
        platform: PlatformType,
        event: Dict[str, Any],
        webhook_id: int
    ):
        """Handle mention notification"""
        
        media_id = event.get("media_id", "")
        mention_id = event.get("mention_id", "")
        
        if not media_id:
            return
        
        # Find the corresponding post if it's a mention on our content
        post = self.db.query(SocialMediaPost).join(SocialMediaAccount).filter(
            and_(
                SocialMediaPost.platform_post_id == media_id,
                SocialMediaAccount.platform == platform
            )
        ).first()
        
        if post:
            logger.info(f"Post {post.id} was mentioned")
            # Here you could implement mention tracking, notifications, etc.
    
    async def _handle_story_insights_event(
        self,
        platform: PlatformType,
        event: Dict[str, Any],
        webhook_id: int
    ):
        """Handle Instagram story insights update"""
        
        media_id = event.get("media_id", "")
        insights = event.get("insights", {})
        
        if not media_id or platform != PlatformType.INSTAGRAM:
            return
        
        # Find the corresponding story post
        post = self.db.query(SocialMediaPost).join(SocialMediaAccount).filter(
            and_(
                SocialMediaPost.platform_post_id == media_id,
                SocialMediaAccount.platform == platform,
                SocialMediaPost.content_type == "story"
            )
        ).first()
        
        if post:
            # Update story metrics
            post.view_count = insights.get("impressions", post.view_count)
            post.reach = insights.get("reach", post.reach)
            
            self.db.commit()
            
            logger.info(f"Updated story metrics for post {post.id}")
    
    async def _create_analytics_record(
        self,
        post: SocialMediaPost,
        metrics: Dict[str, Any]
    ):
        """Create or update analytics record for a post"""
        
        # Check if analytics record already exists for today
        today = datetime.utcnow().date()
        analytics = self.db.query(SocialMediaAnalytics).filter(
            and_(
                SocialMediaAnalytics.post_id == post.id,
                SocialMediaAnalytics.date == today
            )
        ).first()
        
        if not analytics:
            analytics = SocialMediaAnalytics(
                account_id=post.account_id,
                post_id=post.id,
                date=today,
                period_type="daily"
            )
            self.db.add(analytics)
        
        # Update analytics with new metrics
        analytics.views = metrics.get("video_view", metrics.get("video_views", analytics.views))
        analytics.likes = metrics.get("like_count", metrics.get("likes", analytics.likes))
        analytics.comments = metrics.get("comment_count", metrics.get("comments", analytics.comments))
        analytics.shares = metrics.get("share_count", metrics.get("shares", analytics.shares))
        analytics.reach = metrics.get("reach", analytics.reach)
        analytics.impressions = metrics.get("impressions", analytics.impressions)
        
        # Calculate engagement rate
        if analytics.views > 0:
            total_engagement = analytics.likes + analytics.comments + analytics.shares
            analytics.engagement_rate = (total_engagement / analytics.views) * 100
    
    async def process_scheduled_posts(self):
        """Process posts that are scheduled for publishing"""
        
        # Find posts that are scheduled and due for publishing
        now = datetime.utcnow()
        scheduled_posts = self.db.query(SocialMediaPost).filter(
            and_(
                SocialMediaPost.status == PostStatus.SCHEDULED,
                SocialMediaPost.scheduled_at <= now
            )
        ).all()
        
        processed_count = 0
        
        for post in scheduled_posts:
            try:
                # Get account information
                account = self.db.query(SocialMediaAccount).get(post.account_id)
                if not account:
                    continue
                
                # Get platform service
                service = self.platform_services[account.platform]
                
                # Get valid access token
                access_token = await service.token_manager.get_valid_token(
                    str(account.id),
                    {
                        "access_token": account.access_token,
                        "refresh_token": account.refresh_token,
                        "expires_at": account.token_expires_at
                    }
                )
                
                # Create posting request
                posting_request = self._create_posting_request_from_post(post)
                
                # Publish to platform
                if account.platform == PlatformType.TIKTOK:
                    result = await service.publish_post(access_token, posting_request)
                elif account.platform == PlatformType.INSTAGRAM:
                    result = await service.publish_post(access_token, posting_request, account.platform_account_id)
                
                # Update post status
                post.status = PostStatus.PUBLISHED
                post.platform_post_id = result.get("id", "")
                post.published_at = datetime.utcnow()
                
                processed_count += 1
                
                logger.info(f"Successfully published scheduled post {post.id}")
                
            except Exception as e:
                # Update post with error
                post.status = PostStatus.FAILED
                post.error_message = str(e)
                post.retry_count += 1
                
                logger.error(f"Failed to publish scheduled post {post.id}: {e}")
        
        self.db.commit()
        
        return {
            "processed_count": processed_count,
            "total_scheduled": len(scheduled_posts)
        }
    
    def _create_posting_request_from_post(self, post: SocialMediaPost):
        """Create a PostingRequest from a SocialMediaPost record"""
        from .base_service import PostingRequest
        
        return PostingRequest(
            content_type=post.content_type,
            media_urls=post.media_urls or [],
            caption=post.caption,
            hashtags=post.hashtags or [],
            mentions=post.mentions or [],
            location_tag=post.location_tag,
            privacy_settings=post.privacy_settings,
            audience_targeting=post.audience_targeting,
            platform_settings=post.post_settings
        )
    
    async def retry_failed_posts(self, max_retries: int = 3) -> Dict[str, Any]:
        """Retry posts that failed to publish"""
        
        failed_posts = self.db.query(SocialMediaPost).filter(
            and_(
                SocialMediaPost.status == PostStatus.FAILED,
                SocialMediaPost.retry_count < max_retries
            )
        ).all()
        
        retry_results = {
            "success_count": 0,
            "failed_count": 0,
            "total_retried": len(failed_posts)
        }
        
        for post in failed_posts:
            try:
                # Get account information
                account = self.db.query(SocialMediaAccount).get(post.account_id)
                if not account:
                    continue
                
                # Reset post status for retry
                post.status = PostStatus.PUBLISHING
                post.retry_count += 1
                
                # Get platform service
                service = self.platform_services[account.platform]
                
                # Get valid access token
                access_token = await service.token_manager.get_valid_token(
                    str(account.id),
                    {
                        "access_token": account.access_token,
                        "refresh_token": account.refresh_token,
                        "expires_at": account.token_expires_at
                    }
                )
                
                # Create posting request
                posting_request = self._create_posting_request_from_post(post)
                
                # Retry publishing
                if account.platform == PlatformType.TIKTOK:
                    result = await service.publish_post(access_token, posting_request)
                elif account.platform == PlatformType.INSTAGRAM:
                    result = await service.publish_post(access_token, posting_request, account.platform_account_id)
                
                # Update post status on success
                post.status = PostStatus.PUBLISHED
                post.platform_post_id = result.get("id", "")
                post.published_at = datetime.utcnow()
                post.error_message = None
                
                retry_results["success_count"] += 1
                
                logger.info(f"Successfully retried post {post.id}")
                
            except Exception as e:
                # Update post with new error
                post.status = PostStatus.FAILED
                post.error_message = str(e)
                
                retry_results["failed_count"] += 1
                
                logger.error(f"Retry failed for post {post.id}: {e}")
        
        self.db.commit()
        
        return retry_results
    
    async def close(self):
        """Clean up resources"""
        for service in self.platform_services.values():
            await service.close()