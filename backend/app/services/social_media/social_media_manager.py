"""
Unified Social Media Management Service

Provides unified interface for managing multiple social media platforms,
cross-platform posting, analytics aggregation, and automation features.
"""

import asyncio
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Union, Tuple
import logging
from dataclasses import dataclass
from enum import Enum

from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, desc

from .tiktok_service import TikTokService
from .instagram_service import InstagramService
from .base_service import PostingRequest, AnalyticsRequest, SocialMediaResponse, ContentType
from app.models.social_media import (
    SocialMediaAccount, SocialMediaPost, SocialMediaAnalytics, PostingSchedule,
    CrossPlatformCampaign, PlatformType, AccountStatus, PostStatus
)
from app.models.video_project import VideoProject
from app.models.campaign import Campaign
from app.core.config import settings

logger = logging.getLogger(__name__)


class PostingStrategy(str, Enum):
    """Cross-platform posting strategies"""
    SIMULTANEOUS = "simultaneous"  # Post to all platforms at once
    SEQUENTIAL = "sequential"  # Post with delays between platforms
    OPTIMIZED = "optimized"  # Post at optimal times for each platform
    A_B_TEST = "a_b_test"  # Test different content versions


class OptimizationMode(str, Enum):
    """Content optimization modes"""
    DISABLED = "disabled"
    HASHTAGS_ONLY = "hashtags_only"
    CAPTION_ONLY = "caption_only"
    FULL_OPTIMIZATION = "full_optimization"


@dataclass
class CrossPlatformPostingRequest:
    """Request for posting across multiple platforms"""
    video_project_id: Optional[int] = None
    campaign_id: Optional[int] = None
    platforms: List[PlatformType] = None
    content_adaptations: Dict[PlatformType, Dict[str, Any]] = None
    posting_strategy: PostingStrategy = PostingStrategy.OPTIMIZED
    optimization_mode: OptimizationMode = OptimizationMode.HASHTAGS_ONLY
    base_content: PostingRequest = None
    schedule_settings: Optional[Dict[str, Any]] = None


@dataclass
class AnalyticsAggregation:
    """Aggregated analytics across platforms"""
    total_views: int = 0
    total_likes: int = 0
    total_comments: int = 0
    total_shares: int = 0
    total_reach: int = 0
    total_impressions: int = 0
    engagement_rate: float = 0.0
    platform_breakdown: Dict[str, Dict[str, Any]] = None
    top_performing_platform: Optional[str] = None
    growth_metrics: Dict[str, float] = None


class SocialMediaManager:
    """Unified social media management service"""
    
    def __init__(self, db: Session):
        self.db = db
        self.tiktok_service = TikTokService()
        self.instagram_service = InstagramService()
        self.platform_services = {
            PlatformType.TIKTOK: self.tiktok_service,
            PlatformType.INSTAGRAM: self.instagram_service
        }
    
    async def connect_account(
        self,
        brand_id: int,
        platform: PlatformType,
        auth_code: str,
        redirect_uri: str
    ) -> SocialMediaAccount:
        """Connect a new social media account to a brand"""
        
        service = self.platform_services[platform]
        
        try:
            # Complete authentication
            auth_data = await service.authenticate(auth_code, redirect_uri)
            
            # Get account information
            if platform == PlatformType.TIKTOK:
                account_info = await service.get_account_info(auth_data["access_token"])
                
                account = SocialMediaAccount(
                    brand_id=brand_id,
                    platform=platform,
                    username=account_info.get("display_name", ""),
                    display_name=account_info.get("display_name", ""),
                    profile_picture_url=account_info.get("avatar_url", ""),
                    platform_account_id=account_info.get("open_id", ""),
                    access_token=auth_data["access_token"],
                    refresh_token=auth_data.get("refresh_token", ""),
                    token_expires_at=datetime.utcnow() + timedelta(seconds=auth_data.get("expires_in", 3600)),
                    status=AccountStatus.ACTIVE,
                    is_business_account=True,
                    follower_count=account_info.get("follower_count", 0),
                    following_count=account_info.get("following_count", 0)
                )
            
            elif platform == PlatformType.INSTAGRAM:
                # Instagram returns multiple accounts, handle the first business account
                instagram_accounts = auth_data.get("instagram_accounts", [])
                if not instagram_accounts:
                    raise Exception("No Instagram Business accounts found")
                
                ig_account = instagram_accounts[0]  # Use first account for now
                
                account = SocialMediaAccount(
                    brand_id=brand_id,
                    platform=platform,
                    username=ig_account.get("username", ""),
                    display_name=ig_account.get("name", ""),
                    profile_picture_url=ig_account.get("profile_picture_url", ""),
                    platform_account_id=ig_account.get("id", ""),
                    business_account_id=ig_account.get("page_id", ""),
                    access_token=ig_account.get("page_access_token", ""),
                    refresh_token=auth_data.get("access_token", ""),  # Facebook token for refresh
                    status=AccountStatus.ACTIVE,
                    is_business_account=True,
                    follower_count=ig_account.get("followers_count", 0),
                    following_count=ig_account.get("follows_count", 0)
                )
            
            # Save to database
            self.db.add(account)
            self.db.commit()
            self.db.refresh(account)
            
            logger.info(f"Successfully connected {platform.value} account {account.username} for brand {brand_id}")
            return account
            
        except Exception as e:
            logger.error(f"Failed to connect {platform.value} account: {e}")
            raise
    
    async def post_to_multiple_platforms(
        self,
        brand_id: int,
        request: CrossPlatformPostingRequest
    ) -> Dict[str, Any]:
        """Post content to multiple social media platforms"""
        
        # Get active accounts for the brand and specified platforms
        accounts = self.db.query(SocialMediaAccount).filter(
            and_(
                SocialMediaAccount.brand_id == brand_id,
                SocialMediaAccount.status == AccountStatus.ACTIVE,
                SocialMediaAccount.platform.in_(request.platforms)
            )
        ).all()
        
        if not accounts:
            raise Exception("No active social media accounts found for specified platforms")
        
        results = {}
        posting_tasks = []
        
        # Optimize content for each platform
        optimized_content = await self._optimize_content_for_platforms(request, accounts)
        
        # Create posting tasks based on strategy
        if request.posting_strategy == PostingStrategy.SIMULTANEOUS:
            # Post to all platforms simultaneously
            for account in accounts:
                task = self._create_posting_task(account, optimized_content[account.platform], request)
                posting_tasks.append(task)
            
            # Execute all tasks concurrently
            posting_results = await asyncio.gather(*posting_tasks, return_exceptions=True)
            
            for i, result in enumerate(posting_results):
                platform = accounts[i].platform.value
                if isinstance(result, Exception):
                    results[platform] = {"success": False, "error": str(result)}
                else:
                    results[platform] = {"success": True, "data": result}
        
        elif request.posting_strategy == PostingStrategy.SEQUENTIAL:
            # Post with delays between platforms
            for account in accounts:
                try:
                    result = await self._post_to_platform(account, optimized_content[account.platform], request)
                    results[account.platform.value] = {"success": True, "data": result}
                    
                    # Add delay between posts (if not the last one)
                    if account != accounts[-1]:
                        await asyncio.sleep(30)  # 30 second delay
                        
                except Exception as e:
                    results[account.platform.value] = {"success": False, "error": str(e)}
        
        elif request.posting_strategy == PostingStrategy.OPTIMIZED:
            # Post at optimal times for each platform
            optimal_times = await self._get_optimal_posting_times(accounts)
            
            for account in accounts:
                optimal_time = optimal_times.get(account.platform, datetime.utcnow())
                
                # If optimal time is in the future, schedule the post
                if optimal_time > datetime.utcnow():
                    post_record = await self._schedule_post(account, optimized_content[account.platform], request, optimal_time)
                    results[account.platform.value] = {"success": True, "scheduled": True, "post_id": post_record.id}
                else:
                    # Post immediately
                    try:
                        result = await self._post_to_platform(account, optimized_content[account.platform], request)
                        results[account.platform.value] = {"success": True, "data": result}
                    except Exception as e:
                        results[account.platform.value] = {"success": False, "error": str(e)}
        
        # Create cross-platform campaign record
        if request.campaign_id:
            await self._create_cross_platform_campaign_record(brand_id, request, results)
        
        return {
            "results": results,
            "strategy": request.posting_strategy,
            "platforms": [account.platform.value for account in accounts],
            "posted_at": datetime.utcnow().isoformat()
        }
    
    async def _optimize_content_for_platforms(
        self,
        request: CrossPlatformPostingRequest,
        accounts: List[SocialMediaAccount]
    ) -> Dict[PlatformType, PostingRequest]:
        """Optimize content for each platform based on best practices"""
        
        optimized_content = {}
        base_content = request.base_content
        
        for account in accounts:
            platform = account.platform
            
            # Start with base content
            optimized_request = PostingRequest(
                content_type=base_content.content_type,
                media_urls=base_content.media_urls.copy(),
                caption=base_content.caption,
                hashtags=base_content.hashtags.copy() if base_content.hashtags else [],
                mentions=base_content.mentions.copy() if base_content.mentions else [],
                location_tag=base_content.location_tag,
                privacy_settings=base_content.privacy_settings,
                audience_targeting=base_content.audience_targeting,
                platform_settings=base_content.platform_settings or {}
            )
            
            # Apply platform-specific adaptations
            if request.content_adaptations and platform in request.content_adaptations:
                adaptations = request.content_adaptations[platform]
                
                if "caption" in adaptations:
                    optimized_request.caption = adaptations["caption"]
                if "hashtags" in adaptations:
                    optimized_request.hashtags = adaptations["hashtags"]
                if "platform_settings" in adaptations:
                    optimized_request.platform_settings.update(adaptations["platform_settings"])
            
            # Apply automatic optimization
            if request.optimization_mode != OptimizationMode.DISABLED:
                optimized_request = await self._apply_automatic_optimization(
                    optimized_request, platform, request.optimization_mode
                )
            
            optimized_content[platform] = optimized_request
        
        return optimized_content
    
    async def _apply_automatic_optimization(
        self,
        content: PostingRequest,
        platform: PlatformType,
        mode: OptimizationMode
    ) -> PostingRequest:
        """Apply automatic optimization based on platform best practices"""
        
        if mode in [OptimizationMode.HASHTAGS_ONLY, OptimizationMode.FULL_OPTIMIZATION]:
            # Optimize hashtags for platform
            optimized_hashtags = await self._optimize_hashtags_for_platform(content.hashtags, platform)
            content.hashtags = optimized_hashtags
        
        if mode in [OptimizationMode.CAPTION_ONLY, OptimizationMode.FULL_OPTIMIZATION]:
            # Optimize caption for platform
            optimized_caption = await self._optimize_caption_for_platform(content.caption, platform)
            content.caption = optimized_caption
        
        # Platform-specific optimizations
        if platform == PlatformType.TIKTOK:
            content = await self._optimize_for_tiktok(content)
        elif platform == PlatformType.INSTAGRAM:
            content = await self._optimize_for_instagram(content)
        
        return content
    
    async def _optimize_hashtags_for_platform(
        self,
        hashtags: List[str],
        platform: PlatformType
    ) -> List[str]:
        """Optimize hashtags based on platform-specific best practices"""
        
        if not hashtags:
            hashtags = []
        
        if platform == PlatformType.TIKTOK:
            # TikTok: Limit to 3-5 hashtags, include trending ones
            trending_hashtags = ["#fyp", "#viral", "#trending"]
            optimized = hashtags[:3] + [tag for tag in trending_hashtags if tag not in hashtags]
            return optimized[:5]
        
        elif platform == PlatformType.INSTAGRAM:
            # Instagram: Can use up to 30 hashtags
            if len(hashtags) < 10:
                # Add popular Instagram hashtags if under 10
                popular_ig_hashtags = ["#instagood", "#photooftheday", "#beautiful", "#happy", "#love"]
                hashtags.extend([tag for tag in popular_ig_hashtags if tag not in hashtags])
            return hashtags[:30]
        
        return hashtags
    
    async def _optimize_caption_for_platform(
        self,
        caption: str,
        platform: PlatformType
    ) -> str:
        """Optimize caption based on platform-specific best practices"""
        
        if not caption:
            return caption
        
        if platform == PlatformType.TIKTOK:
            # TikTok: Keep captions short and engaging
            if len(caption) > 150:
                caption = caption[:147] + "..."
        
        elif platform == PlatformType.INSTAGRAM:
            # Instagram: Can be longer, encourage engagement
            if not caption.endswith(("?", "!", ".")):
                caption += " What do you think? 💭"
        
        return caption
    
    async def _optimize_for_tiktok(self, content: PostingRequest) -> PostingRequest:
        """Apply TikTok-specific optimizations"""
        
        # TikTok platform settings
        if not content.platform_settings:
            content.platform_settings = {}
        
        # Default TikTok settings for maximum reach
        content.platform_settings.update({
            "privacy_level": "PUBLIC_TO_EVERYONE",
            "disable_duet": False,
            "disable_comment": False,
            "disable_stitch": False,
            "cover_timestamp": 1000
        })
        
        return content
    
    async def _optimize_for_instagram(self, content: PostingRequest) -> PostingRequest:
        """Apply Instagram-specific optimizations"""
        
        # Determine optimal content type
        if content.content_type == ContentType.VIDEO and len(content.media_urls) == 1:
            # Check if video should be a Reel based on duration/aspect ratio
            content.content_type = ContentType.REEL
        
        return content
    
    async def _create_posting_task(
        self,
        account: SocialMediaAccount,
        content: PostingRequest,
        request: CrossPlatformPostingRequest
    ):
        """Create an async task for posting to a platform"""
        return self._post_to_platform(account, content, request)
    
    async def _post_to_platform(
        self,
        account: SocialMediaAccount,
        content: PostingRequest,
        request: CrossPlatformPostingRequest
    ) -> Dict[str, Any]:
        """Post content to a specific platform"""
        
        service = self.platform_services[account.platform]
        
        # Create post record in database
        post_record = SocialMediaPost(
            account_id=account.id,
            video_project_id=request.video_project_id,
            campaign_id=request.campaign_id,
            content_type=content.content_type,
            caption=content.caption,
            hashtags=content.hashtags,
            mentions=content.mentions,
            location_tag=content.location_tag,
            media_urls=content.media_urls,
            privacy_settings=content.privacy_settings,
            audience_targeting=content.audience_targeting,
            post_settings=content.platform_settings,
            status=PostStatus.PUBLISHING
        )
        
        self.db.add(post_record)
        self.db.commit()
        self.db.refresh(post_record)
        
        try:
            # Get valid access token
            access_token = await service.token_manager.get_valid_token(
                str(account.id),
                {
                    "access_token": account.access_token,
                    "refresh_token": account.refresh_token,
                    "expires_at": account.token_expires_at
                }
            )
            
            # Publish to platform
            if account.platform == PlatformType.TIKTOK:
                result = await service.publish_post(access_token, content)
            elif account.platform == PlatformType.INSTAGRAM:
                result = await service.publish_post(access_token, content, account.platform_account_id)
            
            # Update post record with success
            post_record.status = PostStatus.PUBLISHED
            post_record.platform_post_id = result.get("id", "")
            post_record.published_at = datetime.utcnow()
            
            self.db.commit()
            
            logger.info(f"Successfully posted to {account.platform.value} account {account.username}")
            
            return {
                "post_id": post_record.id,
                "platform_post_id": result.get("id", ""),
                "platform": account.platform.value,
                "account": account.username
            }
            
        except Exception as e:
            # Update post record with error
            post_record.status = PostStatus.FAILED
            post_record.error_message = str(e)
            post_record.retry_count += 1
            
            self.db.commit()
            
            logger.error(f"Failed to post to {account.platform.value}: {e}")
            raise
    
    async def _schedule_post(
        self,
        account: SocialMediaAccount,
        content: PostingRequest,
        request: CrossPlatformPostingRequest,
        scheduled_time: datetime
    ) -> SocialMediaPost:
        """Schedule a post for future publishing"""
        
        post_record = SocialMediaPost(
            account_id=account.id,
            video_project_id=request.video_project_id,
            campaign_id=request.campaign_id,
            content_type=content.content_type,
            caption=content.caption,
            hashtags=content.hashtags,
            mentions=content.mentions,
            location_tag=content.location_tag,
            media_urls=content.media_urls,
            privacy_settings=content.privacy_settings,
            audience_targeting=content.audience_targeting,
            post_settings=content.platform_settings,
            status=PostStatus.SCHEDULED,
            scheduled_at=scheduled_time
        )
        
        self.db.add(post_record)
        self.db.commit()
        self.db.refresh(post_record)
        
        return post_record
    
    async def _get_optimal_posting_times(
        self,
        accounts: List[SocialMediaAccount]
    ) -> Dict[PlatformType, datetime]:
        """Get optimal posting times for each platform based on analytics"""
        
        optimal_times = {}
        
        for account in accounts:
            # Check if there's a posting schedule
            schedule = self.db.query(PostingSchedule).filter(
                PostingSchedule.account_id == account.id,
                PostingSchedule.is_active == True
            ).first()
            
            if schedule and schedule.posting_times:
                # Use schedule's optimal times
                current_hour = datetime.utcnow().hour
                posting_times = schedule.posting_times
                
                # Find next optimal time
                next_time = None
                for time_str in posting_times:
                    hour = int(time_str.split(":")[0])
                    if hour > current_hour:
                        next_time = datetime.utcnow().replace(hour=hour, minute=0, second=0, microsecond=0)
                        break
                
                if not next_time and posting_times:
                    # Use first time tomorrow
                    hour = int(posting_times[0].split(":")[0])
                    next_time = (datetime.utcnow() + timedelta(days=1)).replace(hour=hour, minute=0, second=0, microsecond=0)
                
                optimal_times[account.platform] = next_time or datetime.utcnow()
            else:
                # Use default optimal times based on platform
                if account.platform == PlatformType.TIKTOK:
                    # TikTok optimal: 6-10 PM
                    optimal_times[account.platform] = datetime.utcnow().replace(hour=19, minute=0, second=0, microsecond=0)
                elif account.platform == PlatformType.INSTAGRAM:
                    # Instagram optimal: 11 AM - 1 PM, 5-7 PM
                    current_hour = datetime.utcnow().hour
                    if current_hour < 11:
                        optimal_times[account.platform] = datetime.utcnow().replace(hour=11, minute=0, second=0, microsecond=0)
                    elif current_hour < 17:
                        optimal_times[account.platform] = datetime.utcnow().replace(hour=17, minute=0, second=0, microsecond=0)
                    else:
                        optimal_times[account.platform] = (datetime.utcnow() + timedelta(days=1)).replace(hour=11, minute=0, second=0, microsecond=0)
        
        return optimal_times
    
    async def get_aggregated_analytics(
        self,
        brand_id: int,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        platforms: Optional[List[PlatformType]] = None
    ) -> AnalyticsAggregation:
        """Get aggregated analytics across all platforms"""
        
        # Default date range: last 30 days
        if not end_date:
            end_date = datetime.utcnow()
        if not start_date:
            start_date = end_date - timedelta(days=30)
        
        # Get accounts for the brand
        query = self.db.query(SocialMediaAccount).filter(
            SocialMediaAccount.brand_id == brand_id,
            SocialMediaAccount.status == AccountStatus.ACTIVE
        )
        
        if platforms:
            query = query.filter(SocialMediaAccount.platform.in_(platforms))
        
        accounts = query.all()
        
        aggregation = AnalyticsAggregation(platform_breakdown={})
        
        for account in accounts:
            # Get analytics for this account
            analytics_data = self.db.query(SocialMediaAnalytics).filter(
                and_(
                    SocialMediaAnalytics.account_id == account.id,
                    SocialMediaAnalytics.date >= start_date,
                    SocialMediaAnalytics.date <= end_date
                )
            ).all()
            
            # Calculate platform totals
            platform_views = sum(a.views for a in analytics_data)
            platform_likes = sum(a.likes for a in analytics_data)
            platform_comments = sum(a.comments for a in analytics_data)
            platform_shares = sum(a.shares for a in analytics_data)
            platform_reach = sum(a.reach for a in analytics_data)
            platform_impressions = sum(a.impressions for a in analytics_data)
            
            # Add to aggregated totals
            aggregation.total_views += platform_views
            aggregation.total_likes += platform_likes
            aggregation.total_comments += platform_comments
            aggregation.total_shares += platform_shares
            aggregation.total_reach += platform_reach
            aggregation.total_impressions += platform_impressions
            
            # Store platform breakdown
            platform_key = account.platform.value
            aggregation.platform_breakdown[platform_key] = {
                "views": platform_views,
                "likes": platform_likes,
                "comments": platform_comments,
                "shares": platform_shares,
                "reach": platform_reach,
                "impressions": platform_impressions,
                "account": account.username
            }
        
        # Calculate overall engagement rate
        if aggregation.total_views > 0:
            total_engagement = aggregation.total_likes + aggregation.total_comments + aggregation.total_shares
            aggregation.engagement_rate = (total_engagement / aggregation.total_views) * 100
        
        # Determine top performing platform
        if aggregation.platform_breakdown:
            top_platform = max(
                aggregation.platform_breakdown.keys(),
                key=lambda p: aggregation.platform_breakdown[p]["views"]
            )
            aggregation.top_performing_platform = top_platform
        
        return aggregation
    
    async def sync_analytics(self, brand_id: int) -> Dict[str, Any]:
        """Sync analytics data from all connected platforms"""
        
        accounts = self.db.query(SocialMediaAccount).filter(
            SocialMediaAccount.brand_id == brand_id,
            SocialMediaAccount.status == AccountStatus.ACTIVE
        ).all()
        
        sync_results = {}
        
        for account in accounts:
            try:
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
                
                # Prepare analytics request
                analytics_request = AnalyticsRequest(
                    start_date=datetime.utcnow() - timedelta(days=7),  # Last 7 days
                    end_date=datetime.utcnow()
                )
                
                # Get analytics from platform
                if account.platform == PlatformType.TIKTOK:
                    analytics_data = await service.get_analytics(access_token, analytics_request)
                elif account.platform == PlatformType.INSTAGRAM:
                    analytics_data = await service.get_analytics(access_token, analytics_request, account.platform_account_id)
                
                # Process and store analytics data
                processed_count = await self._process_analytics_data(account, analytics_data)
                
                sync_results[account.platform.value] = {
                    "success": True,
                    "account": account.username,
                    "records_processed": processed_count
                }
                
                # Update last sync time
                account.last_sync_at = datetime.utcnow()
                
            except Exception as e:
                sync_results[account.platform.value] = {
                    "success": False,
                    "account": account.username,
                    "error": str(e)
                }
                logger.error(f"Failed to sync analytics for {account.platform.value} account {account.username}: {e}")
        
        self.db.commit()
        
        return sync_results
    
    async def _process_analytics_data(self, account: SocialMediaAccount, analytics_data: Dict[str, Any]) -> int:
        """Process and store analytics data in the database"""
        
        processed_count = 0
        
        # Process account-level analytics
        if "account" in analytics_data:
            for insight in analytics_data["account"]:
                # Store account analytics
                analytics_record = SocialMediaAnalytics(
                    account_id=account.id,
                    date=datetime.utcnow().date(),
                    period_type="daily",
                    # Map platform-specific metrics to our standard format
                    # This would be more sophisticated in production
                    reach=insight.get("reach", 0),
                    impressions=insight.get("impressions", 0)
                )
                
                self.db.add(analytics_record)
                processed_count += 1
        
        # Process media-level analytics
        if "media" in analytics_data:
            for media_id, media_insights in analytics_data["media"].items():
                # Find the corresponding post
                post = self.db.query(SocialMediaPost).filter(
                    SocialMediaPost.account_id == account.id,
                    SocialMediaPost.platform_post_id == media_id
                ).first()
                
                if post:
                    # Update post metrics
                    for insight in media_insights:
                        metric_name = insight.get("name", "")
                        value = insight.get("values", [{}])[0].get("value", 0)
                        
                        if metric_name == "impressions":
                            post.impressions = value
                        elif metric_name == "reach":
                            post.reach = value
                        elif metric_name == "likes":
                            post.like_count = value
                        elif metric_name == "comments":
                            post.comment_count = value
                        elif metric_name == "shares":
                            post.share_count = value
                    
                    # Calculate engagement rate
                    if post.reach > 0:
                        engagement = post.like_count + post.comment_count + post.share_count
                        post.engagement_rate = (engagement / post.reach) * 100
                    
                    processed_count += 1
        
        return processed_count
    
    async def _create_cross_platform_campaign_record(
        self,
        brand_id: int,
        request: CrossPlatformPostingRequest,
        results: Dict[str, Any]
    ):
        """Create a record for cross-platform campaign tracking"""
        
        successful_platforms = [
            platform for platform, result in results.items()
            if result.get("success", False)
        ]
        
        campaign = CrossPlatformCampaign(
            brand_id=brand_id,
            campaign_id=request.campaign_id,
            name=f"Cross-platform post {datetime.utcnow().strftime('%Y-%m-%d %H:%M')}",
            platforms=successful_platforms,
            platform_settings={
                "strategy": request.posting_strategy,
                "optimization_mode": request.optimization_mode,
                "results": results
            },
            total_posts=len(successful_platforms),
            status="active"
        )
        
        self.db.add(campaign)
        self.db.commit()
    
    async def close(self):
        """Clean up resources"""
        await self.tiktok_service.close()
        await self.instagram_service.close()