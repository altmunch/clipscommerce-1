"""
TikTok Trend Scraping Celery Tasks

Scheduled tasks for automated TikTok trend monitoring, scraping, and analysis.
Integrates with Apify platform for data collection and processing pipelines.
"""

import asyncio
import json
import logging
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional

from celery import Task
from sqlalchemy.orm import Session
from sqlalchemy import desc, func, and_, or_

from app.core.celery_app import celery_app
from app.db.session import get_db
from app.models.tiktok_trend import (
    TikTokTrend, TikTokVideo, TikTokHashtag, TikTokSound,
    TikTokScrapingJob, TikTokAnalytics,
    TrendStatus, TrendType, ContentCategory
)
from app.services.scraping.apify_client import ApifyTikTokClient, ApifyJobStatus
from app.services.scraping.tiktok_processor import process_apify_results, calculate_trend_metrics
from app.core.config import settings

logger = logging.getLogger(__name__)


class TikTokScrapingTask(Task):
    """Base task class for TikTok scraping operations"""
    
    def __init__(self):
        self.apify_client = None
        self.db = None
    
    def before_start(self, task_id, args, kwargs):
        """Initialize resources before task execution"""
        self.db = next(get_db())
        
    def after_return(self, status, retval, task_id, args, kwargs, einfo):
        """Clean up resources after task completion"""
        if self.db:
            self.db.close()
    
    def on_failure(self, exc, task_id, args, kwargs, einfo):
        """Handle task failure"""
        logger.error(f"TikTok scraping task {task_id} failed: {exc}")
        if self.db:
            self.db.close()
    
    async def get_apify_client(self) -> ApifyTikTokClient:
        """Get Apify client instance"""
        if self.apify_client is None:
            self.apify_client = ApifyTikTokClient()
        return self.apify_client


@celery_app.task(bind=True, base=TikTokScrapingTask, name="tiktok.scrape_trending")
def scrape_trending_content(
    self,
    max_videos: int = 1000,
    regions: List[str] = None,
    include_analysis: bool = True,
    auto_process: bool = True
) -> Dict[str, Any]:
    """
    Scrape trending TikTok content
    
    Args:
        max_videos: Maximum number of videos to scrape
        regions: Geographic regions to focus on
        include_analysis: Whether to include content analysis
        auto_process: Whether to automatically process results
        
    Returns:
        Dict containing scraping results
    """
    
    logger.info(f"Starting trending content scraping task: {max_videos} videos")
    
    try:
        # Create scraping job record
        job_record = TikTokScrapingJob(
            job_id=self.request.id,
            job_type="trending",
            parameters={
                "max_videos": max_videos,
                "regions": regions or ["US", "UK", "CA", "AU"],
                "include_analysis": include_analysis
            },
            status="pending"
        )
        
        self.db.add(job_record)
        self.db.commit()
        
        # Run async scraping
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        try:
            result = loop.run_until_complete(
                self._execute_trending_scrape(
                    job_record, max_videos, regions, include_analysis, auto_process
                )
            )
            return result
        finally:
            loop.close()
            
    except Exception as e:
        logger.error(f"Trending scraping task failed: {e}")
        
        # Update job record
        if 'job_record' in locals():
            job_record.status = "failed"
            job_record.last_error = str(e)
            job_record.completed_at = datetime.utcnow()
            self.db.commit()
        
        raise
    
    async def _execute_trending_scrape(
        self,
        job_record: TikTokScrapingJob,
        max_videos: int,
        regions: List[str],
        include_analysis: bool,
        auto_process: bool
    ) -> Dict[str, Any]:
        """Execute the trending scraping operation"""
        
        client = await self.get_apify_client()
        
        # Start scraping
        job_record.status = "running"
        job_record.started_at = datetime.utcnow()
        self.db.commit()
        
        async with client:
            # Start Apify actor
            run_id = await client.start_trending_scrape(
                max_videos=max_videos,
                regions=regions,
                include_analysis=include_analysis
            )
            
            job_record.apify_run_id = run_id
            self.db.commit()
            
            # Wait for completion
            logger.info(f"Waiting for Apify run {run_id} to complete...")
            
            status_info = await client.wait_for_completion(run_id, timeout=3600)  # 1 hour timeout
            
            if status_info["status"] == ApifyJobStatus.SUCCEEDED.value:
                # Get results
                scraped_data = await client.get_run_results(run_id)
                analytics_data = await client.get_run_analytics(run_id)
                trend_analysis = await client.get_trend_analysis(run_id)
                
                # Update job record
                job_record.status = "completed"
                job_record.videos_scraped = len(scraped_data)
                job_record.completed_at = datetime.utcnow()
                self.db.commit()
                
                result = {
                    "job_id": self.request.id,
                    "run_id": run_id,
                    "status": "completed",
                    "videos_scraped": len(scraped_data),
                    "analytics": analytics_data
                }
                
                # Auto-process results if requested
                if auto_process and scraped_data:
                    logger.info(f"Auto-processing {len(scraped_data)} scraped videos...")
                    
                    processing_result = await process_apify_results(
                        job_id=self.request.id,
                        scraped_data=scraped_data,
                        analytics_data=analytics_data,
                        trend_analysis=trend_analysis
                    )
                    
                    # Update job record with processing results
                    job_record.trends_identified = processing_result.get('trends_created', 0)
                    job_record.hashtags_discovered = processing_result.get('hashtags_tracked', 0)
                    job_record.sounds_tracked = processing_result.get('sounds_tracked', 0)
                    self.db.commit()
                    
                    result["processing"] = processing_result
                    
                    # Schedule trend analysis update
                    update_trend_analysis.delay()
                
                return result
                
            else:
                # Job failed
                job_record.status = "failed"
                job_record.last_error = f"Apify job failed with status: {status_info['status']}"
                job_record.completed_at = datetime.utcnow()
                self.db.commit()
                
                raise Exception(f"Scraping failed with status: {status_info['status']}")


@celery_app.task(bind=True, base=TikTokScrapingTask, name="tiktok.scrape_hashtags")
def scrape_hashtag_content(
    self,
    hashtags: List[str],
    max_videos: int = 2000,
    regions: List[str] = None,
    auto_process: bool = True
) -> Dict[str, Any]:
    """
    Scrape content for specific hashtags
    
    Args:
        hashtags: List of hashtags to scrape
        max_videos: Maximum number of videos to scrape
        regions: Geographic regions to focus on
        auto_process: Whether to automatically process results
        
    Returns:
        Dict containing scraping results
    """
    
    logger.info(f"Starting hashtag scraping task: {hashtags}")
    
    try:
        # Create scraping job record
        job_record = TikTokScrapingJob(
            job_id=self.request.id,
            job_type="hashtag",
            target=", ".join(hashtags),
            parameters={
                "hashtags": hashtags,
                "max_videos": max_videos,
                "regions": regions or ["US", "UK", "CA", "AU"]
            },
            status="pending"
        )
        
        self.db.add(job_record)
        self.db.commit()
        
        # Run async scraping
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        try:
            result = loop.run_until_complete(
                self._execute_hashtag_scrape(
                    job_record, hashtags, max_videos, regions, auto_process
                )
            )
            return result
        finally:
            loop.close()
            
    except Exception as e:
        logger.error(f"Hashtag scraping task failed: {e}")
        
        # Update job record
        if 'job_record' in locals():
            job_record.status = "failed"
            job_record.last_error = str(e)
            job_record.completed_at = datetime.utcnow()
            self.db.commit()
        
        raise
    
    async def _execute_hashtag_scrape(
        self,
        job_record: TikTokScrapingJob,
        hashtags: List[str],
        max_videos: int,
        regions: List[str],
        auto_process: bool
    ) -> Dict[str, Any]:
        """Execute hashtag scraping operation"""
        
        client = await self.get_apify_client()
        
        job_record.status = "running"
        job_record.started_at = datetime.utcnow()
        self.db.commit()
        
        async with client:
            # Start Apify actor
            run_id = await client.start_hashtag_scrape(
                hashtags=hashtags,
                max_videos=max_videos,
                regions=regions
            )
            
            job_record.apify_run_id = run_id
            self.db.commit()
            
            # Wait for completion
            status_info = await client.wait_for_completion(run_id, timeout=3600)
            
            if status_info["status"] == ApifyJobStatus.SUCCEEDED.value:
                # Get results
                scraped_data = await client.get_run_results(run_id)
                analytics_data = await client.get_run_analytics(run_id)
                
                # Update job record
                job_record.status = "completed"
                job_record.videos_scraped = len(scraped_data)
                job_record.completed_at = datetime.utcnow()
                self.db.commit()
                
                result = {
                    "job_id": self.request.id,
                    "run_id": run_id,
                    "status": "completed",
                    "hashtags": hashtags,
                    "videos_scraped": len(scraped_data),
                    "analytics": analytics_data
                }
                
                # Auto-process results
                if auto_process and scraped_data:
                    processing_result = await process_apify_results(
                        job_id=self.request.id,
                        scraped_data=scraped_data,
                        analytics_data=analytics_data
                    )
                    
                    job_record.trends_identified = processing_result.get('trends_created', 0)
                    job_record.hashtags_discovered = processing_result.get('hashtags_tracked', 0)
                    self.db.commit()
                    
                    result["processing"] = processing_result
                
                return result
                
            else:
                job_record.status = "failed"
                job_record.last_error = f"Apify job failed with status: {status_info['status']}"
                job_record.completed_at = datetime.utcnow()
                self.db.commit()
                
                raise Exception(f"Scraping failed with status: {status_info['status']}")


@celery_app.task(bind=True, base=TikTokScrapingTask, name="tiktok.scrape_sounds")
def scrape_sound_content(
    self,
    sound_ids: List[str],
    max_videos: int = 1500,
    auto_process: bool = True
) -> Dict[str, Any]:
    """
    Scrape content for specific sounds
    
    Args:
        sound_ids: List of TikTok sound IDs to scrape
        max_videos: Maximum number of videos to scrape
        auto_process: Whether to automatically process results
        
    Returns:
        Dict containing scraping results
    """
    
    logger.info(f"Starting sound scraping task: {sound_ids}")
    
    try:
        # Create scraping job record
        job_record = TikTokScrapingJob(
            job_id=self.request.id,
            job_type="sound",
            target=", ".join(sound_ids),
            parameters={
                "sound_ids": sound_ids,
                "max_videos": max_videos
            },
            status="pending"
        )
        
        self.db.add(job_record)
        self.db.commit()
        
        # Run async scraping
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        try:
            result = loop.run_until_complete(
                self._execute_sound_scrape(job_record, sound_ids, max_videos, auto_process)
            )
            return result
        finally:
            loop.close()
            
    except Exception as e:
        logger.error(f"Sound scraping task failed: {e}")
        
        if 'job_record' in locals():
            job_record.status = "failed"
            job_record.last_error = str(e)
            job_record.completed_at = datetime.utcnow()
            self.db.commit()
        
        raise
    
    async def _execute_sound_scrape(
        self,
        job_record: TikTokScrapingJob,
        sound_ids: List[str],
        max_videos: int,
        auto_process: bool
    ) -> Dict[str, Any]:
        """Execute sound scraping operation"""
        
        client = await self.get_apify_client()
        
        job_record.status = "running"
        job_record.started_at = datetime.utcnow()
        self.db.commit()
        
        async with client:
            # Start Apify actor
            run_id = await client.start_sound_scrape(
                sound_ids=sound_ids,
                max_videos=max_videos
            )
            
            job_record.apify_run_id = run_id
            self.db.commit()
            
            # Wait for completion
            status_info = await client.wait_for_completion(run_id, timeout=3600)
            
            if status_info["status"] == ApifyJobStatus.SUCCEEDED.value:
                # Get results
                scraped_data = await client.get_run_results(run_id)
                analytics_data = await client.get_run_analytics(run_id)
                
                # Update job record
                job_record.status = "completed"
                job_record.videos_scraped = len(scraped_data)
                job_record.completed_at = datetime.utcnow()
                self.db.commit()
                
                result = {
                    "job_id": self.request.id,
                    "run_id": run_id,
                    "status": "completed",
                    "sound_ids": sound_ids,
                    "videos_scraped": len(scraped_data),
                    "analytics": analytics_data
                }
                
                # Auto-process results
                if auto_process and scraped_data:
                    processing_result = await process_apify_results(
                        job_id=self.request.id,
                        scraped_data=scraped_data,
                        analytics_data=analytics_data
                    )
                    
                    job_record.sounds_tracked = processing_result.get('sounds_tracked', 0)
                    self.db.commit()
                    
                    result["processing"] = processing_result
                
                return result
                
            else:
                job_record.status = "failed"
                job_record.last_error = f"Apify job failed with status: {status_info['status']}"
                job_record.completed_at = datetime.utcnow()
                self.db.commit()
                
                raise Exception(f"Scraping failed with status: {status_info['status']}")


@celery_app.task(bind=True, base=TikTokScrapingTask, name="tiktok.monitor_competitors")
def monitor_competitor_accounts(
    self,
    usernames: List[str],
    max_videos: int = 500,
    auto_process: bool = True
) -> Dict[str, Any]:
    """
    Monitor competitor TikTok accounts
    
    Args:
        usernames: List of TikTok usernames to monitor
        max_videos: Maximum number of videos to scrape per account
        auto_process: Whether to automatically process results
        
    Returns:
        Dict containing monitoring results
    """
    
    logger.info(f"Starting competitor monitoring task: {usernames}")
    
    try:
        # Create scraping job record
        job_record = TikTokScrapingJob(
            job_id=self.request.id,
            job_type="user",
            target=", ".join(usernames),
            parameters={
                "usernames": usernames,
                "max_videos": max_videos
            },
            status="pending"
        )
        
        self.db.add(job_record)
        self.db.commit()
        
        # Run async scraping
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        try:
            result = loop.run_until_complete(
                self._execute_user_scrape(job_record, usernames, max_videos, auto_process)
            )
            return result
        finally:
            loop.close()
            
    except Exception as e:
        logger.error(f"Competitor monitoring task failed: {e}")
        
        if 'job_record' in locals():
            job_record.status = "failed"
            job_record.last_error = str(e)
            job_record.completed_at = datetime.utcnow()
            self.db.commit()
        
        raise
    
    async def _execute_user_scrape(
        self,
        job_record: TikTokScrapingJob,
        usernames: List[str],
        max_videos: int,
        auto_process: bool
    ) -> Dict[str, Any]:
        """Execute user scraping operation"""
        
        client = await self.get_apify_client()
        
        job_record.status = "running"
        job_record.started_at = datetime.utcnow()
        self.db.commit()
        
        async with client:
            # Start Apify actor
            run_id = await client.start_user_scrape(
                usernames=usernames,
                max_videos=max_videos
            )
            
            job_record.apify_run_id = run_id
            self.db.commit()
            
            # Wait for completion
            status_info = await client.wait_for_completion(run_id, timeout=3600)
            
            if status_info["status"] == ApifyJobStatus.SUCCEEDED.value:
                # Get results
                scraped_data = await client.get_run_results(run_id)
                analytics_data = await client.get_run_analytics(run_id)
                
                # Update job record
                job_record.status = "completed"
                job_record.videos_scraped = len(scraped_data)
                job_record.completed_at = datetime.utcnow()
                self.db.commit()
                
                result = {
                    "job_id": self.request.id,
                    "run_id": run_id,
                    "status": "completed",
                    "usernames": usernames,
                    "videos_scraped": len(scraped_data),
                    "analytics": analytics_data
                }
                
                # Auto-process results
                if auto_process and scraped_data:
                    processing_result = await process_apify_results(
                        job_id=self.request.id,
                        scraped_data=scraped_data,
                        analytics_data=analytics_data
                    )
                    
                    result["processing"] = processing_result
                
                return result
                
            else:
                job_record.status = "failed"
                job_record.last_error = f"Apify job failed with status: {status_info['status']}"
                job_record.completed_at = datetime.utcnow()
                self.db.commit()
                
                raise Exception(f"Scraping failed with status: {status_info['status']}")


@celery_app.task(name="tiktok.update_trend_analysis")
def update_trend_analysis() -> Dict[str, Any]:
    """
    Update trend analysis for all active trends
    
    Returns:
        Dict containing analysis results
    """
    
    logger.info("Starting trend analysis update...")
    
    db = next(get_db())
    
    try:
        # Get active trends that need analysis
        active_trends = db.query(TikTokTrend).filter(
            and_(
                TikTokTrend.is_active == True,
                TikTokTrend.last_scraped > datetime.utcnow() - timedelta(hours=24)
            )
        ).all()
        
        updated_count = 0
        
        # Run analysis update in async context
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        try:
            for trend in active_trends:
                try:
                    # Calculate updated metrics
                    metrics = loop.run_until_complete(
                        calculate_trend_metrics(trend.trend_id)
                    )
                    
                    # Update trend with new metrics
                    trend.viral_score = metrics.get('viral_score', trend.viral_score)
                    trend.growth_rate = metrics.get('growth_metrics', {}).get('growth_rate', trend.growth_rate)
                    trend.velocity = metrics.get('growth_metrics', {}).get('velocity', trend.velocity)
                    trend.updated_at = datetime.utcnow()
                    
                    updated_count += 1
                    
                except Exception as e:
                    logger.error(f"Error updating trend {trend.trend_id}: {e}")
            
            db.commit()
            
        finally:
            loop.close()
        
        result = {
            "trends_analyzed": len(active_trends),
            "trends_updated": updated_count,
            "completed_at": datetime.utcnow().isoformat()
        }
        
        logger.info(f"Trend analysis update completed: {result}")
        return result
        
    finally:
        db.close()


@celery_app.task(name="tiktok.cleanup_old_data")
def cleanup_old_data(days_to_keep: int = 30) -> Dict[str, Any]:
    """
    Clean up old TikTok data to manage database size
    
    Args:
        days_to_keep: Number of days of data to keep
        
    Returns:
        Dict containing cleanup results
    """
    
    logger.info(f"Starting cleanup of TikTok data older than {days_to_keep} days")
    
    db = next(get_db())
    
    try:
        cutoff_date = datetime.utcnow() - timedelta(days=days_to_keep)
        
        # Clean up old videos
        old_videos = db.query(TikTokVideo).filter(
            TikTokVideo.scraped_at < cutoff_date
        )
        video_count = old_videos.count()
        old_videos.delete(synchronize_session=False)
        
        # Clean up old scraping jobs
        old_jobs = db.query(TikTokScrapingJob).filter(
            TikTokScrapingJob.created_at < cutoff_date
        )
        job_count = old_jobs.count()
        old_jobs.delete(synchronize_session=False)
        
        # Clean up old analytics
        old_analytics = db.query(TikTokAnalytics).filter(
            TikTokAnalytics.date < cutoff_date.date()
        )
        analytics_count = old_analytics.count()
        old_analytics.delete(synchronize_session=False)
        
        # Mark old trends as inactive
        old_trends = db.query(TikTokTrend).filter(
            and_(
                TikTokTrend.last_scraped < cutoff_date,
                TikTokTrend.is_active == True
            )
        ).update({"is_active": False}, synchronize_session=False)
        
        db.commit()
        
        result = {
            "videos_deleted": video_count,
            "jobs_deleted": job_count,
            "analytics_deleted": analytics_count,
            "trends_deactivated": old_trends,
            "cutoff_date": cutoff_date.isoformat(),
            "completed_at": datetime.utcnow().isoformat()
        }
        
        logger.info(f"Cleanup completed: {result}")
        return result
        
    finally:
        db.close()


@celery_app.task(name="tiktok.generate_daily_report")
def generate_daily_report() -> Dict[str, Any]:
    """
    Generate daily TikTok trend analysis report
    
    Returns:
        Dict containing daily report data
    """
    
    logger.info("Generating daily TikTok trend report...")
    
    db = next(get_db())
    
    try:
        today = datetime.utcnow().date()
        yesterday = today - timedelta(days=1)
        
        # Get today's analytics
        today_analytics = db.query(TikTokAnalytics).filter(
            and_(
                func.date(TikTokAnalytics.date) == today,
                TikTokAnalytics.period_type == "daily"
            )
        ).first()
        
        # Get yesterday's analytics for comparison
        yesterday_analytics = db.query(TikTokAnalytics).filter(
            and_(
                func.date(TikTokAnalytics.date) == yesterday,
                TikTokAnalytics.period_type == "daily"
            )
        ).first()
        
        # Get top trends
        top_trends = db.query(TikTokTrend).filter(
            and_(
                TikTokTrend.is_active == True,
                TikTokTrend.viral_score > 50
            )
        ).order_by(desc(TikTokTrend.viral_score)).limit(10).all()
        
        # Get emerging trends
        emerging_trends = db.query(TikTokTrend).filter(
            and_(
                TikTokTrend.trend_status == TrendStatus.EMERGING.value,
                TikTokTrend.first_detected > datetime.utcnow() - timedelta(hours=24)
            )
        ).order_by(desc(TikTokTrend.viral_score)).limit(5).all()
        
        # Get top hashtags
        top_hashtags = db.query(TikTokHashtag).filter(
            TikTokHashtag.is_trending == True
        ).order_by(desc(TikTokHashtag.trend_score)).limit(10).all()
        
        # Get top sounds
        top_sounds = db.query(TikTokSound).filter(
            TikTokSound.is_trending == True
        ).order_by(desc(TikTokSound.trend_score)).limit(10).all()
        
        # Calculate growth metrics
        growth_metrics = {}
        if today_analytics and yesterday_analytics:
            growth_metrics = {
                "videos_growth": today_analytics.total_videos_analyzed - yesterday_analytics.total_videos_analyzed,
                "trends_growth": today_analytics.total_trends - yesterday_analytics.total_trends,
                "hashtags_growth": today_analytics.total_hashtags - yesterday_analytics.total_hashtags,
                "sounds_growth": today_analytics.total_sounds - yesterday_analytics.total_sounds
            }
        
        report = {
            "date": today.isoformat(),
            "summary": {
                "total_videos_analyzed": today_analytics.total_videos_analyzed if today_analytics else 0,
                "total_trends": today_analytics.total_trends if today_analytics else 0,
                "total_hashtags": today_analytics.total_hashtags if today_analytics else 0,
                "total_sounds": today_analytics.total_sounds if today_analytics else 0,
                "avg_viral_score": today_analytics.avg_viral_score if today_analytics else 0
            },
            "growth_metrics": growth_metrics,
            "top_trends": [trend.to_dict() for trend in top_trends],
            "emerging_trends": [trend.to_dict() for trend in emerging_trends],
            "top_hashtags": [hashtag.to_dict() for hashtag in top_hashtags],
            "top_sounds": [sound.to_dict() for sound in top_sounds],
            "generated_at": datetime.utcnow().isoformat()
        }
        
        logger.info(f"Daily report generated with {len(top_trends)} trends")
        return report
        
    finally:
        db.close()


# Scheduled tasks setup
@celery_app.on_after_configure.connect
def setup_periodic_tasks(sender, **kwargs):
    """Setup periodic TikTok scraping tasks"""
    
    # Daily trending content scraping (every day at 6 AM UTC)
    sender.add_periodic_task(
        schedule=settings.CELERY_BEAT_SCHEDULE.get('tiktok-daily-trending', {
            'schedule': crontab(hour=6, minute=0),  # 6 AM UTC daily
            'task': 'tiktok.scrape_trending'
        }),
        args=[1500, ["US", "UK", "CA", "AU"], True, True]  # max_videos, regions, include_analysis, auto_process
    )
    
    # Trend analysis update (every 2 hours)
    sender.add_periodic_task(
        schedule=settings.CELERY_BEAT_SCHEDULE.get('tiktok-trend-analysis', {
            'schedule': crontab(minute=0, hour='*/2'),  # Every 2 hours
            'task': 'tiktok.update_trend_analysis'
        })
    )
    
    # Daily report generation (every day at 8 AM UTC)
    sender.add_periodic_task(
        schedule=settings.CELERY_BEAT_SCHEDULE.get('tiktok-daily-report', {
            'schedule': crontab(hour=8, minute=0),  # 8 AM UTC daily
            'task': 'tiktok.generate_daily_report'
        })
    )
    
    # Weekly cleanup (every Sunday at 2 AM UTC)
    sender.add_periodic_task(
        schedule=settings.CELERY_BEAT_SCHEDULE.get('tiktok-weekly-cleanup', {
            'schedule': crontab(hour=2, minute=0, day_of_week=0),  # Sunday 2 AM UTC
            'task': 'tiktok.cleanup_old_data'
        }),
        args=[30]  # Keep 30 days of data
    )


# Utility functions for task management
def get_active_scraping_jobs() -> List[Dict[str, Any]]:
    """Get list of active scraping jobs"""
    
    db = next(get_db())
    try:
        active_jobs = db.query(TikTokScrapingJob).filter(
            TikTokScrapingJob.status.in_(["pending", "running"])
        ).order_by(desc(TikTokScrapingJob.created_at)).all()
        
        return [job.to_dict() for job in active_jobs]
    finally:
        db.close()


def cancel_scraping_job(job_id: str) -> bool:
    """Cancel a running scraping job"""
    
    try:
        # Revoke Celery task
        celery_app.control.revoke(job_id, terminate=True)
        
        # Update database record
        db = next(get_db())
        try:
            job = db.query(TikTokScrapingJob).filter(
                TikTokScrapingJob.job_id == job_id
            ).first()
            
            if job:
                job.status = "aborted"
                job.completed_at = datetime.utcnow()
                db.commit()
                return True
        finally:
            db.close()
        
        return False
        
    except Exception as e:
        logger.error(f"Error canceling job {job_id}: {e}")
        return False


def get_scraping_statistics() -> Dict[str, Any]:
    """Get overall scraping statistics"""
    
    db = next(get_db())
    try:
        # Get job statistics
        total_jobs = db.query(TikTokScrapingJob).count()
        completed_jobs = db.query(TikTokScrapingJob).filter(
            TikTokScrapingJob.status == "completed"
        ).count()
        failed_jobs = db.query(TikTokScrapingJob).filter(
            TikTokScrapingJob.status == "failed"
        ).count()
        
        # Get data statistics
        total_videos = db.query(TikTokVideo).count()
        total_trends = db.query(TikTokTrend).filter(
            TikTokTrend.is_active == True
        ).count()
        total_hashtags = db.query(TikTokHashtag).count()
        total_sounds = db.query(TikTokSound).count()
        
        # Get recent activity
        recent_jobs = db.query(TikTokScrapingJob).filter(
            TikTokScrapingJob.created_at > datetime.utcnow() - timedelta(hours=24)
        ).count()
        
        return {
            "jobs": {
                "total": total_jobs,
                "completed": completed_jobs,
                "failed": failed_jobs,
                "success_rate": (completed_jobs / total_jobs * 100) if total_jobs > 0 else 0,
                "recent_24h": recent_jobs
            },
            "data": {
                "total_videos": total_videos,
                "active_trends": total_trends,
                "total_hashtags": total_hashtags,
                "total_sounds": total_sounds
            },
            "updated_at": datetime.utcnow().isoformat()
        }
        
    finally:
        db.close()