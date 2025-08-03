"""
Social Media API Endpoints

Provides REST API endpoints for managing social media accounts,
publishing content, retrieving analytics, and handling webhooks.
"""

from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional
import logging

from fastapi import APIRouter, Depends, HTTPException, Request, Response, BackgroundTasks
from fastapi.security import HTTPBearer
from sqlalchemy.orm import Session
from sqlalchemy import and_, desc

from app.api.deps import get_current_user, get_db
from app.models.user import User
from app.models.brand import Brand
from app.models.social_media import (
    SocialMediaAccount, SocialMediaPost, SocialMediaAnalytics, PostingSchedule,
    CrossPlatformCampaign, PlatformType, AccountStatus, PostStatus, ContentType
)
from app.services.social_media import SocialMediaManager, WebhookProcessor
from app.services.social_media.base_service import PostingRequest, AnalyticsRequest
from app.services.social_media.social_media_manager import CrossPlatformPostingRequest, PostingStrategy, OptimizationMode
from app.core.config import settings

logger = logging.getLogger(__name__)

router = APIRouter()
security = HTTPBearer()


# Pydantic schemas for request/response validation
from pydantic import BaseModel, Field
from typing import Union


class ConnectAccountRequest(BaseModel):
    platform: PlatformType
    auth_code: str
    redirect_uri: str


class ConnectAccountResponse(BaseModel):
    account_id: int
    platform: str
    username: str
    display_name: Optional[str]
    status: str
    follower_count: int
    is_business_account: bool


class PostContentRequest(BaseModel):
    content_type: ContentType
    media_urls: List[str]
    caption: Optional[str] = None
    hashtags: Optional[List[str]] = None
    mentions: Optional[List[str]] = None
    location_tag: Optional[str] = None
    privacy_settings: Optional[Dict[str, Any]] = None
    audience_targeting: Optional[Dict[str, Any]] = None
    platform_settings: Optional[Dict[str, Any]] = None
    scheduled_at: Optional[datetime] = None


class CrossPlatformPostRequest(BaseModel):
    video_project_id: Optional[int] = None
    campaign_id: Optional[int] = None
    platforms: List[PlatformType]
    base_content: PostContentRequest
    content_adaptations: Optional[Dict[str, Dict[str, Any]]] = None
    posting_strategy: PostingStrategy = PostingStrategy.OPTIMIZED
    optimization_mode: OptimizationMode = OptimizationMode.HASHTAGS_ONLY
    schedule_settings: Optional[Dict[str, Any]] = None


class AnalyticsRequestModel(BaseModel):
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    platforms: Optional[List[PlatformType]] = None
    post_ids: Optional[List[str]] = None
    metrics: Optional[List[str]] = None
    breakdown: Optional[str] = "daily"


class PostingScheduleRequest(BaseModel):
    account_id: int
    name: str
    description: Optional[str] = None
    timezone: str = "UTC"
    posting_times: List[str]  # ["09:00", "15:00", "20:00"]
    posting_frequency: Dict[str, Any]
    content_types: List[ContentType]
    hashtag_strategy: Optional[Dict[str, Any]] = None
    caption_templates: Optional[List[str]] = None
    auto_optimize_timing: bool = True
    auto_optimize_hashtags: bool = True


# Account Management Endpoints

@router.get("/auth-url/{platform}")
async def get_auth_url(
    platform: PlatformType,
    state: Optional[str] = None,
    current_user: User = Depends(get_current_user)
):
    """Get OAuth authorization URL for a social media platform"""
    
    try:
        if platform == PlatformType.TIKTOK:
            from app.services.social_media.tiktok_service import TikTokService
            service = TikTokService()
            auth_url = service.get_auth_url(state)
        
        elif platform == PlatformType.INSTAGRAM:
            from app.services.social_media.instagram_service import InstagramService
            service = InstagramService()
            auth_url = service.get_auth_url(state)
        
        else:
            raise HTTPException(status_code=400, detail=f"Unsupported platform: {platform}")
        
        return {
            "auth_url": auth_url,
            "platform": platform.value,
            "state": state
        }
    
    except Exception as e:
        logger.error(f"Failed to get auth URL for {platform}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to generate authorization URL: {str(e)}")


@router.post("/accounts/connect/{brand_id}")
async def connect_account(
    brand_id: int,
    request: ConnectAccountRequest,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> ConnectAccountResponse:
    """Connect a social media account to a brand"""
    
    # Verify brand ownership
    brand = db.query(Brand).filter(
        and_(Brand.id == brand_id, Brand.user_id == current_user.id)
    ).first()
    
    if not brand:
        raise HTTPException(status_code=404, detail="Brand not found")
    
    try:
        # Initialize social media manager
        manager = SocialMediaManager(db)
        
        # Connect the account
        account = await manager.connect_account(
            brand_id=brand_id,
            platform=request.platform,
            auth_code=request.auth_code,
            redirect_uri=request.redirect_uri
        )
        
        # Schedule initial analytics sync
        background_tasks.add_task(sync_account_analytics, account.id, db)
        
        return ConnectAccountResponse(
            account_id=account.id,
            platform=account.platform.value,
            username=account.username,
            display_name=account.display_name,
            status=account.status.value,
            follower_count=account.follower_count,
            is_business_account=account.is_business_account
        )
    
    except Exception as e:
        logger.error(f"Failed to connect {request.platform} account: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to connect account: {str(e)}")


@router.get("/accounts/{brand_id}")
async def get_accounts(
    brand_id: int,
    platform: Optional[PlatformType] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get connected social media accounts for a brand"""
    
    # Verify brand ownership
    brand = db.query(Brand).filter(
        and_(Brand.id == brand_id, Brand.user_id == current_user.id)
    ).first()
    
    if not brand:
        raise HTTPException(status_code=404, detail="Brand not found")
    
    # Build query
    query = db.query(SocialMediaAccount).filter(SocialMediaAccount.brand_id == brand_id)
    
    if platform:
        query = query.filter(SocialMediaAccount.platform == platform)
    
    accounts = query.all()
    
    return {
        "accounts": [
            {
                "id": account.id,
                "platform": account.platform.value,
                "username": account.username,
                "display_name": account.display_name,
                "status": account.status.value,
                "follower_count": account.follower_count,
                "following_count": account.following_count,
                "is_business_account": account.is_business_account,
                "is_verified": account.is_verified,
                "profile_picture_url": account.profile_picture_url,
                "created_at": account.created_at,
                "last_sync_at": account.last_sync_at
            }
            for account in accounts
        ],
        "total": len(accounts)
    }


@router.delete("/accounts/{account_id}")
async def disconnect_account(
    account_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Disconnect a social media account"""
    
    # Get account and verify ownership
    account = db.query(SocialMediaAccount).join(Brand).filter(
        and_(
            SocialMediaAccount.id == account_id,
            Brand.user_id == current_user.id
        )
    ).first()
    
    if not account:
        raise HTTPException(status_code=404, detail="Account not found")
    
    # Update account status
    account.status = AccountStatus.INACTIVE
    db.commit()
    
    return {"message": "Account disconnected successfully"}


# Content Publishing Endpoints

@router.post("/posts/{brand_id}")
async def publish_content(
    brand_id: int,
    request: CrossPlatformPostRequest,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Publish content to multiple social media platforms"""
    
    # Verify brand ownership
    brand = db.query(Brand).filter(
        and_(Brand.id == brand_id, Brand.user_id == current_user.id)
    ).first()
    
    if not brand:
        raise HTTPException(status_code=404, detail="Brand not found")
    
    try:
        # Initialize social media manager
        manager = SocialMediaManager(db)
        
        # Convert request to internal format
        posting_request = CrossPlatformPostingRequest(
            video_project_id=request.video_project_id,
            campaign_id=request.campaign_id,
            platforms=request.platforms,
            content_adaptations=request.content_adaptations,
            posting_strategy=request.posting_strategy,
            optimization_mode=request.optimization_mode,
            base_content=PostingRequest(
                content_type=request.base_content.content_type,
                media_urls=request.base_content.media_urls,
                caption=request.base_content.caption,
                hashtags=request.base_content.hashtags,
                mentions=request.base_content.mentions,
                location_tag=request.base_content.location_tag,
                scheduled_at=request.base_content.scheduled_at,
                privacy_settings=request.base_content.privacy_settings,
                audience_targeting=request.base_content.audience_targeting,
                platform_settings=request.base_content.platform_settings
            ),
            schedule_settings=request.schedule_settings
        )
        
        # Post to platforms
        result = await manager.post_to_multiple_platforms(brand_id, posting_request)
        
        # Schedule analytics sync for successful posts
        for platform, platform_result in result["results"].items():
            if platform_result.get("success"):
                background_tasks.add_task(sync_platform_analytics, brand_id, platform, db)
        
        await manager.close()
        
        return result
    
    except Exception as e:
        logger.error(f"Failed to publish content: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to publish content: {str(e)}")


@router.get("/posts/{brand_id}")
async def get_posts(
    brand_id: int,
    platform: Optional[PlatformType] = None,
    status: Optional[PostStatus] = None,
    limit: int = 50,
    offset: int = 0,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get posts for a brand"""
    
    # Verify brand ownership
    brand = db.query(Brand).filter(
        and_(Brand.id == brand_id, Brand.user_id == current_user.id)
    ).first()
    
    if not brand:
        raise HTTPException(status_code=404, detail="Brand not found")
    
    # Build query
    query = db.query(SocialMediaPost).join(SocialMediaAccount).filter(
        SocialMediaAccount.brand_id == brand_id
    )
    
    if platform:
        query = query.filter(SocialMediaAccount.platform == platform)
    
    if status:
        query = query.filter(SocialMediaPost.status == status)
    
    # Get total count
    total = query.count()
    
    # Apply pagination and ordering
    posts = query.order_by(desc(SocialMediaPost.created_at)).offset(offset).limit(limit).all()
    
    return {
        "posts": [
            {
                "id": post.id,
                "platform": post.account.platform.value,
                "account_username": post.account.username,
                "content_type": post.content_type.value,
                "caption": post.caption,
                "hashtags": post.hashtags,
                "status": post.status.value,
                "scheduled_at": post.scheduled_at,
                "published_at": post.published_at,
                "platform_post_id": post.platform_post_id,
                "post_url": post.post_url,
                "view_count": post.view_count,
                "like_count": post.like_count,
                "comment_count": post.comment_count,
                "share_count": post.share_count,
                "engagement_rate": post.engagement_rate,
                "reach": post.reach,
                "impressions": post.impressions,
                "created_at": post.created_at,
                "error_message": post.error_message if post.status == PostStatus.FAILED else None
            }
            for post in posts
        ],
        "total": total,
        "limit": limit,
        "offset": offset
    }


@router.delete("/posts/{post_id}")
async def delete_post(
    post_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Delete a scheduled post (cannot delete published posts)"""
    
    # Get post and verify ownership
    post = db.query(SocialMediaPost).join(SocialMediaAccount).join(Brand).filter(
        and_(
            SocialMediaPost.id == post_id,
            Brand.user_id == current_user.id
        )
    ).first()
    
    if not post:
        raise HTTPException(status_code=404, detail="Post not found")
    
    if post.status == PostStatus.PUBLISHED:
        raise HTTPException(status_code=400, detail="Cannot delete published posts")
    
    # Update post status
    post.status = PostStatus.DELETED
    db.commit()
    
    return {"message": "Post deleted successfully"}


# Analytics Endpoints

@router.get("/analytics/{brand_id}")
async def get_analytics(
    brand_id: int,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    platforms: Optional[str] = None,  # Comma-separated platform names
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get aggregated analytics for a brand"""
    
    # Verify brand ownership
    brand = db.query(Brand).filter(
        and_(Brand.id == brand_id, Brand.user_id == current_user.id)
    ).first()
    
    if not brand:
        raise HTTPException(status_code=404, detail="Brand not found")
    
    try:
        # Parse platforms parameter
        platform_list = None
        if platforms:
            platform_names = platforms.split(",")
            platform_list = [PlatformType(name.strip()) for name in platform_names]
        
        # Initialize social media manager
        manager = SocialMediaManager(db)
        
        # Get aggregated analytics
        analytics = await manager.get_aggregated_analytics(
            brand_id=brand_id,
            start_date=start_date,
            end_date=end_date,
            platforms=platform_list
        )
        
        await manager.close()
        
        return {
            "total_views": analytics.total_views,
            "total_likes": analytics.total_likes,
            "total_comments": analytics.total_comments,
            "total_shares": analytics.total_shares,
            "total_reach": analytics.total_reach,
            "total_impressions": analytics.total_impressions,
            "engagement_rate": analytics.engagement_rate,
            "top_performing_platform": analytics.top_performing_platform,
            "platform_breakdown": analytics.platform_breakdown,
            "growth_metrics": analytics.growth_metrics
        }
    
    except Exception as e:
        logger.error(f"Failed to get analytics: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to retrieve analytics: {str(e)}")


@router.post("/analytics/sync/{brand_id}")
async def sync_analytics(
    brand_id: int,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Trigger analytics synchronization for all accounts"""
    
    # Verify brand ownership
    brand = db.query(Brand).filter(
        and_(Brand.id == brand_id, Brand.user_id == current_user.id)
    ).first()
    
    if not brand:
        raise HTTPException(status_code=404, detail="Brand not found")
    
    # Schedule background sync
    background_tasks.add_task(sync_brand_analytics, brand_id, db)
    
    return {"message": "Analytics sync started", "brand_id": brand_id}


# Scheduling Endpoints

@router.post("/schedules")
async def create_posting_schedule(
    request: PostingScheduleRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Create a posting schedule for an account"""
    
    # Verify account ownership
    account = db.query(SocialMediaAccount).join(Brand).filter(
        and_(
            SocialMediaAccount.id == request.account_id,
            Brand.user_id == current_user.id
        )
    ).first()
    
    if not account:
        raise HTTPException(status_code=404, detail="Account not found")
    
    # Create posting schedule
    schedule = PostingSchedule(
        account_id=request.account_id,
        brand_id=account.brand_id,
        name=request.name,
        description=request.description,
        timezone=request.timezone,
        posting_times=request.posting_times,
        posting_frequency=request.posting_frequency,
        content_types=[ct.value for ct in request.content_types],
        hashtag_strategy=request.hashtag_strategy,
        caption_templates=request.caption_templates,
        auto_optimize_timing=request.auto_optimize_timing,
        auto_optimize_hashtags=request.auto_optimize_hashtags
    )
    
    db.add(schedule)
    db.commit()
    db.refresh(schedule)
    
    return {
        "id": schedule.id,
        "name": schedule.name,
        "account_id": schedule.account_id,
        "posting_times": schedule.posting_times,
        "is_active": schedule.is_active,
        "created_at": schedule.created_at
    }


@router.get("/schedules/{brand_id}")
async def get_posting_schedules(
    brand_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get posting schedules for a brand"""
    
    # Verify brand ownership
    brand = db.query(Brand).filter(
        and_(Brand.id == brand_id, Brand.user_id == current_user.id)
    ).first()
    
    if not brand:
        raise HTTPException(status_code=404, detail="Brand not found")
    
    schedules = db.query(PostingSchedule).filter(PostingSchedule.brand_id == brand_id).all()
    
    return {
        "schedules": [
            {
                "id": schedule.id,
                "name": schedule.name,
                "account_id": schedule.account_id,
                "account_username": schedule.account.username,
                "platform": schedule.account.platform.value,
                "posting_times": schedule.posting_times,
                "posting_frequency": schedule.posting_frequency,
                "is_active": schedule.is_active,
                "auto_optimize_timing": schedule.auto_optimize_timing,
                "auto_optimize_hashtags": schedule.auto_optimize_hashtags,
                "posts_scheduled": schedule.posts_scheduled,
                "posts_published": schedule.posts_published,
                "average_engagement": schedule.average_engagement,
                "created_at": schedule.created_at,
                "last_posting_at": schedule.last_posting_at
            }
            for schedule in schedules
        ]
    }


# Webhook Endpoints

@router.post("/webhooks/{platform}")
async def handle_webhook(
    platform: PlatformType,
    request: Request,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """Handle incoming webhooks from social media platforms"""
    
    try:
        # Get request body and headers
        payload = await request.json()
        headers = dict(request.headers)
        
        # Process webhook in background
        background_tasks.add_task(process_webhook_background, platform, payload, headers, db)
        
        # Return success immediately (webhooks expect quick response)
        return {"status": "received"}
    
    except Exception as e:
        logger.error(f"Failed to handle {platform} webhook: {e}")
        raise HTTPException(status_code=500, detail="Webhook processing failed")


@router.get("/webhooks/{platform}/verify")
async def verify_webhook(
    platform: PlatformType,
    request: Request
):
    """Verify webhook subscription (for platforms that require it)"""
    
    if platform == PlatformType.INSTAGRAM:
        # Facebook/Instagram webhook verification
        hub_mode = request.query_params.get("hub.mode")
        hub_challenge = request.query_params.get("hub.challenge")
        hub_verify_token = request.query_params.get("hub.verify_token")
        
        if (hub_mode == "subscribe" and 
            hub_verify_token == settings.INSTAGRAM_WEBHOOK_VERIFY_TOKEN):
            return Response(content=hub_challenge, media_type="text/plain")
        else:
            raise HTTPException(status_code=403, detail="Verification failed")
    
    return {"status": "verified"}


# Background Tasks

async def sync_account_analytics(account_id: int, db: Session):
    """Background task to sync analytics for a specific account"""
    try:
        account = db.query(SocialMediaAccount).get(account_id)
        if account:
            manager = SocialMediaManager(db)
            await manager.sync_analytics(account.brand_id)
            await manager.close()
    except Exception as e:
        logger.error(f"Failed to sync analytics for account {account_id}: {e}")


async def sync_platform_analytics(brand_id: int, platform: str, db: Session):
    """Background task to sync analytics for a specific platform"""
    try:
        manager = SocialMediaManager(db)
        await manager.sync_analytics(brand_id)
        await manager.close()
    except Exception as e:
        logger.error(f"Failed to sync {platform} analytics for brand {brand_id}: {e}")


async def sync_brand_analytics(brand_id: int, db: Session):
    """Background task to sync analytics for all accounts of a brand"""
    try:
        manager = SocialMediaManager(db)
        result = await manager.sync_analytics(brand_id)
        await manager.close()
        logger.info(f"Analytics sync completed for brand {brand_id}: {result}")
    except Exception as e:
        logger.error(f"Failed to sync analytics for brand {brand_id}: {e}")


async def process_webhook_background(
    platform: PlatformType,
    payload: Dict[str, Any],
    headers: Dict[str, str],
    db: Session
):
    """Background task to process webhook"""
    try:
        processor = WebhookProcessor(db)
        result = await processor.process_webhook(platform, payload, headers)
        await processor.close()
        logger.info(f"Webhook processed: {result}")
    except Exception as e:
        logger.error(f"Failed to process webhook: {e}")


# Health Check and Status

@router.get("/health")
async def health_check():
    """Health check endpoint for social media services"""
    
    health_status = {
        "status": "healthy",
        "services": {},
        "timestamp": datetime.utcnow().isoformat()
    }
    
    try:
        # Check TikTok service
        from app.services.social_media.tiktok_service import TikTokService
        tiktok_service = TikTokService()
        health_status["services"]["tiktok"] = await tiktok_service.health_check()
        await tiktok_service.close()
        
        # Check Instagram service  
        from app.services.social_media.instagram_service import InstagramService
        instagram_service = InstagramService()
        health_status["services"]["instagram"] = await instagram_service.health_check()
        await instagram_service.close()
        
    except Exception as e:
        health_status["status"] = "degraded"
        health_status["error"] = str(e)
    
    return health_status