"""
Social Media Background Tasks

Celery tasks for handling scheduled posting, analytics synchronization,
and other social media automation features.
"""

import asyncio
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional
import logging

from celery import Celery
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_

from app.core.celery_app import celery_app
from app.db.session import SessionLocal
from app.models.social_media import (
    SocialMediaAccount, SocialMediaPost, SocialMediaAnalytics, PostingSchedule,
    PlatformType, AccountStatus, PostStatus
)
from app.services.social_media import SocialMediaManager, WebhookProcessor
from app.core.config import settings

logger = logging.getLogger(__name__)


def get_db() -> Session:
    """Get database session for tasks"""
    db = SessionLocal()
    try:
        return db
    finally:
        pass  # Don't close here, let the task handle it


@celery_app.task(bind=True, max_retries=3)
def process_scheduled_posts(self):
    """Process posts scheduled for publishing"""
    
    db = get_db()
    
    try:
        # Find posts that are due for publishing
        now = datetime.utcnow()
        scheduled_posts = db.query(SocialMediaPost).filter(
            and_(
                SocialMediaPost.status == PostStatus.SCHEDULED,
                SocialMediaPost.scheduled_at <= now
            )
        ).all()
        
        if not scheduled_posts:
            logger.info("No scheduled posts found")
            return {"processed": 0, "total": 0}
        
        logger.info(f"Processing {len(scheduled_posts)} scheduled posts")
        
        # Process posts using webhook processor (which has the logic)
        processor = WebhookProcessor(db)
        
        # Run the async method in sync context
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        try:
            result = loop.run_until_complete(processor.process_scheduled_posts())
        finally:
            loop.close()
            await processor.close()
        
        db.commit()
        
        logger.info(f"Scheduled posts processing result: {result}")
        
        return {
            "processed": result["processed_count"],
            "total": result["total_scheduled"],
            "timestamp": datetime.utcnow().isoformat()
        }
    
    except Exception as e:
        logger.error(f"Failed to process scheduled posts: {e}")
        
        # Retry the task with exponential backoff
        if self.request.retries < self.max_retries:
            raise self.retry(countdown=60 * (2 ** self.request.retries))
        
        return {"error": str(e), "processed": 0}
    
    finally:
        db.close()


@celery_app.task(bind=True, max_retries=3)
def sync_all_analytics(self):
    """Sync analytics for all active accounts"""
    
    db = get_db()
    
    try:
        # Get all active accounts
        accounts = db.query(SocialMediaAccount).filter(
            SocialMediaAccount.status == AccountStatus.ACTIVE
        ).all()
        
        if not accounts:
            logger.info("No active accounts found for analytics sync")
            return {"synced_brands": 0, "total_accounts": 0}
        
        # Group accounts by brand for efficient syncing
        brands_to_sync = set(account.brand_id for account in accounts)
        
        logger.info(f"Syncing analytics for {len(brands_to_sync)} brands ({len(accounts)} accounts)")
        
        sync_results = {}
        
        # Run async syncing
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        try:
            for brand_id in brands_to_sync:
                try:
                    manager = SocialMediaManager(db)
                    result = loop.run_until_complete(manager.sync_analytics(brand_id))
                    sync_results[brand_id] = result
                    loop.run_until_complete(manager.close())
                    
                except Exception as e:
                    logger.error(f"Failed to sync analytics for brand {brand_id}: {e}")
                    sync_results[brand_id] = {"error": str(e)}
        
        finally:
            loop.close()
        
        db.commit()
        
        successful_syncs = sum(1 for result in sync_results.values() if "error" not in result)
        
        logger.info(f"Analytics sync completed: {successful_syncs}/{len(brands_to_sync)} brands successful")
        
        return {
            "synced_brands": successful_syncs,
            "total_brands": len(brands_to_sync),
            "total_accounts": len(accounts),
            "results": sync_results,
            "timestamp": datetime.utcnow().isoformat()
        }
    
    except Exception as e:
        logger.error(f"Failed to sync analytics: {e}")
        
        # Retry the task with exponential backoff
        if self.request.retries < self.max_retries:
            raise self.retry(countdown=300 * (2 ** self.request.retries))  # 5 min base delay
        
        return {"error": str(e), "synced_brands": 0}
    
    finally:
        db.close()


@celery_app.task(bind=True, max_retries=2)
def sync_brand_analytics(self, brand_id: int):
    """Sync analytics for a specific brand"""
    
    db = get_db()
    
    try:
        # Verify brand has active accounts
        accounts = db.query(SocialMediaAccount).filter(
            and_(
                SocialMediaAccount.brand_id == brand_id,
                SocialMediaAccount.status == AccountStatus.ACTIVE
            )
        ).all()
        
        if not accounts:
            logger.warning(f"No active accounts found for brand {brand_id}")
            return {"error": "No active accounts", "brand_id": brand_id}
        
        logger.info(f"Syncing analytics for brand {brand_id} ({len(accounts)} accounts)")
        
        # Run async syncing
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        try:
            manager = SocialMediaManager(db)
            result = loop.run_until_complete(manager.sync_analytics(brand_id))
            loop.run_until_complete(manager.close())
        
        finally:
            loop.close()
        
        db.commit()
        
        logger.info(f"Analytics sync completed for brand {brand_id}: {result}")
        
        return {
            "brand_id": brand_id,
            "accounts_synced": len(accounts),
            "result": result,
            "timestamp": datetime.utcnow().isoformat()
        }
    
    except Exception as e:
        logger.error(f"Failed to sync analytics for brand {brand_id}: {e}")
        
        # Retry the task
        if self.request.retries < self.max_retries:
            raise self.retry(countdown=120 * (2 ** self.request.retries))  # 2 min base delay
        
        return {"error": str(e), "brand_id": brand_id}
    
    finally:
        db.close()


@celery_app.task(bind=True, max_retries=3)
def retry_failed_posts(self):
    """Retry posts that failed to publish"""
    
    db = get_db()
    
    try:
        # Find failed posts that haven't exceeded max retries
        max_retries = 3
        failed_posts = db.query(SocialMediaPost).filter(
            and_(
                SocialMediaPost.status == PostStatus.FAILED,
                SocialMediaPost.retry_count < max_retries,
                SocialMediaPost.created_at >= datetime.utcnow() - timedelta(days=7)  # Only retry recent posts
            )
        ).all()
        
        if not failed_posts:
            logger.info("No failed posts to retry")
            return {"retried": 0, "total": 0}
        
        logger.info(f"Retrying {len(failed_posts)} failed posts")
        
        # Process retries using webhook processor
        processor = WebhookProcessor(db)
        
        # Run the async method in sync context
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        try:
            result = loop.run_until_complete(processor.retry_failed_posts(max_retries))
        finally:
            loop.close()
            await processor.close()
        
        db.commit()
        
        logger.info(f"Failed posts retry result: {result}")
        
        return {
            "retried": result["total_retried"],
            "successful": result["success_count"],
            "failed": result["failed_count"],
            "timestamp": datetime.utcnow().isoformat()
        }
    
    except Exception as e:
        logger.error(f"Failed to retry posts: {e}")
        
        # Retry the task
        if self.request.retries < self.max_retries:
            raise self.retry(countdown=60 * (2 ** self.request.retries))
        
        return {"error": str(e), "retried": 0}
    
    finally:
        db.close()


@celery_app.task
def process_webhook_event(platform: str, payload: dict, headers: dict):
    """Process a webhook event in background"""
    
    db = get_db()
    
    try:
        # Convert platform string to enum
        platform_enum = PlatformType(platform)
        
        logger.info(f"Processing {platform} webhook event")
        
        # Process webhook using processor
        processor = WebhookProcessor(db)
        
        # Run the async method in sync context
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        try:
            result = loop.run_until_complete(
                processor.process_webhook(platform_enum, payload, headers)
            )
        finally:
            loop.close()
            await processor.close()
        
        db.commit()
        
        logger.info(f"Webhook processing result: {result}")
        
        return result
    
    except Exception as e:
        logger.error(f"Failed to process webhook: {e}")
        return {"error": str(e)}
    
    finally:
        db.close()


@celery_app.task(bind=True, max_retries=2)
def refresh_account_tokens(self):
    """Refresh access tokens for accounts that are about to expire"""
    
    db = get_db()
    
    try:
        # Find accounts with tokens expiring in the next 24 hours
        expiry_threshold = datetime.utcnow() + timedelta(hours=24)
        
        accounts_to_refresh = db.query(SocialMediaAccount).filter(
            and_(
                SocialMediaAccount.status == AccountStatus.ACTIVE,
                SocialMediaAccount.token_expires_at <= expiry_threshold,
                SocialMediaAccount.refresh_token.isnot(None)
            )
        ).all()
        
        if not accounts_to_refresh:
            logger.info("No accounts need token refresh")
            return {"refreshed": 0, "total": 0}
        
        logger.info(f"Refreshing tokens for {len(accounts_to_refresh)} accounts")
        
        refresh_results = {"success": 0, "failed": 0, "errors": []}
        
        # Process token refreshes
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        try:
            for account in accounts_to_refresh:
                try:
                    # Get appropriate service
                    if account.platform == PlatformType.TIKTOK:
                        from app.services.social_media.tiktok_service import TikTokService
                        service = TikTokService()
                    elif account.platform == PlatformType.INSTAGRAM:
                        from app.services.social_media.instagram_service import InstagramService
                        service = InstagramService()
                    else:
                        continue
                    
                    # Refresh token
                    new_token_data = loop.run_until_complete(
                        service.refresh_token(account.refresh_token)
                    )
                    
                    # Update account with new token
                    account.access_token = new_token_data["access_token"]
                    if "expires_in" in new_token_data:
                        account.token_expires_at = datetime.utcnow() + timedelta(
                            seconds=new_token_data["expires_in"]
                        )
                    
                    refresh_results["success"] += 1
                    
                    loop.run_until_complete(service.close())
                    
                    logger.info(f"Refreshed token for {account.platform.value} account {account.username}")
                
                except Exception as e:
                    refresh_results["failed"] += 1
                    refresh_results["errors"].append({
                        "account_id": account.id,
                        "platform": account.platform.value,
                        "username": account.username,
                        "error": str(e)
                    })
                    
                    logger.error(f"Failed to refresh token for account {account.id}: {e}")
        
        finally:
            loop.close()
        
        db.commit()
        
        logger.info(f"Token refresh completed: {refresh_results['success']} successful, {refresh_results['failed']} failed")
        
        return {
            "refreshed": refresh_results["success"],
            "failed": refresh_results["failed"],
            "total": len(accounts_to_refresh),
            "errors": refresh_results["errors"],
            "timestamp": datetime.utcnow().isoformat()
        }
    
    except Exception as e:
        logger.error(f"Failed to refresh tokens: {e}")
        
        # Retry the task
        if self.request.retries < self.max_retries:
            raise self.retry(countdown=300 * (2 ** self.request.retries))  # 5 min base delay
        
        return {"error": str(e), "refreshed": 0}
    
    finally:
        db.close()


@celery_app.task
def cleanup_old_analytics(days_to_keep: int = 90):
    """Clean up old analytics data to manage database size"""
    
    db = get_db()
    
    try:
        cutoff_date = datetime.utcnow() - timedelta(days=days_to_keep)
        
        # Delete old analytics records
        deleted_count = db.query(SocialMediaAnalytics).filter(
            SocialMediaAnalytics.date < cutoff_date.date()
        ).delete()
        
        # Delete old webhook records
        webhook_deleted = db.query(SocialMediaAnalytics).filter(
            SocialMediaAnalytics.created_at < cutoff_date
        ).delete()
        
        db.commit()
        
        logger.info(f"Cleanup completed: {deleted_count} analytics records, {webhook_deleted} webhook records deleted")
        
        return {
            "analytics_deleted": deleted_count,
            "webhooks_deleted": webhook_deleted,
            "cutoff_date": cutoff_date.isoformat(),
            "timestamp": datetime.utcnow().isoformat()
        }
    
    except Exception as e:
        logger.error(f"Failed to cleanup old data: {e}")
        return {"error": str(e)}
    
    finally:
        db.close()


@celery_app.task
def update_posting_schedules():
    """Update posting schedules based on analytics performance"""
    
    db = get_db()
    
    try:
        # Get all active posting schedules
        schedules = db.query(PostingSchedule).filter(
            and_(
                PostingSchedule.is_active == True,
                PostingSchedule.auto_optimize_timing == True
            )
        ).all()
        
        if not schedules:
            logger.info("No schedules to optimize")
            return {"optimized": 0, "total": 0}
        
        optimized_count = 0
        
        for schedule in schedules:
            try:
                # Analyze recent post performance for this account
                recent_posts = db.query(SocialMediaPost).filter(
                    and_(
                        SocialMediaPost.account_id == schedule.account_id,
                        SocialMediaPost.status == PostStatus.PUBLISHED,
                        SocialMediaPost.published_at >= datetime.utcnow() - timedelta(days=30)
                    )
                ).all()
                
                if len(recent_posts) < 5:  # Need minimum data for optimization
                    continue
                
                # Calculate engagement rates by hour
                hour_performance = {}
                for post in recent_posts:
                    if post.published_at and post.engagement_rate:
                        hour = post.published_at.hour
                        if hour not in hour_performance:
                            hour_performance[hour] = []
                        hour_performance[hour].append(post.engagement_rate)
                
                # Find top performing hours
                if hour_performance:
                    avg_performance = {
                        hour: sum(rates) / len(rates)
                        for hour, rates in hour_performance.items()
                        if len(rates) >= 2  # Minimum posts per hour
                    }
                    
                    if avg_performance:
                        # Get top 3 performing hours
                        top_hours = sorted(avg_performance.keys(), 
                                         key=lambda h: avg_performance[h], 
                                         reverse=True)[:3]
                        
                        # Update posting times
                        new_times = [f"{hour:02d}:00" for hour in top_hours]
                        schedule.posting_times = new_times
                        schedule.average_engagement = sum(avg_performance.values()) / len(avg_performance)
                        
                        optimized_count += 1
                        
                        logger.info(f"Optimized schedule {schedule.id}: new times {new_times}")
            
            except Exception as e:
                logger.error(f"Failed to optimize schedule {schedule.id}: {e}")
        
        db.commit()
        
        return {
            "optimized": optimized_count,
            "total": len(schedules),
            "timestamp": datetime.utcnow().isoformat()
        }
    
    except Exception as e:
        logger.error(f"Failed to update posting schedules: {e}")
        return {"error": str(e), "optimized": 0}
    
    finally:
        db.close()


# Periodic task configuration (to be set up in celery beat)
@celery_app.task
def setup_periodic_tasks():
    """Set up periodic social media tasks"""
    
    from celery.schedules import crontab
    
    # Schedule tasks
    celery_app.conf.beat_schedule = {
        # Process scheduled posts every 5 minutes
        'process-scheduled-posts': {
            'task': 'app.tasks.social_media_tasks.process_scheduled_posts',
            'schedule': crontab(minute='*/5'),
        },
        
        # Sync analytics every hour
        'sync-all-analytics': {
            'task': 'app.tasks.social_media_tasks.sync_all_analytics',
            'schedule': crontab(minute=0),
        },
        
        # Retry failed posts every 30 minutes
        'retry-failed-posts': {
            'task': 'app.tasks.social_media_tasks.retry_failed_posts',
            'schedule': crontab(minute='*/30'),
        },
        
        # Refresh tokens every 6 hours
        'refresh-account-tokens': {
            'task': 'app.tasks.social_media_tasks.refresh_account_tokens',
            'schedule': crontab(minute=0, hour='*/6'),
        },
        
        # Cleanup old data weekly
        'cleanup-old-analytics': {
            'task': 'app.tasks.social_media_tasks.cleanup_old_analytics',
            'schedule': crontab(minute=0, hour=2, day_of_week=0),  # Sunday 2 AM
        },
        
        # Update posting schedules daily
        'update-posting-schedules': {
            'task': 'app.tasks.social_media_tasks.update_posting_schedules',
            'schedule': crontab(minute=0, hour=4),  # Daily at 4 AM
        },
    }
    
    return {"message": "Periodic tasks configured"}