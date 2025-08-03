"""
TikTok Trend API Endpoints

REST API endpoints for TikTok trend management, scraping job control,
and trend data access for the ViralOS platform.
"""

from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, BackgroundTasks
from sqlalchemy.orm import Session
from sqlalchemy import desc, func, and_, or_

from app.api.deps import get_current_user, get_db
from app.models.user import User
from app.models.tiktok_trend import (
    TikTokTrend, TikTokVideo, TikTokHashtag, TikTokSound,
    TikTokScrapingJob, TikTokAnalytics,
    TrendStatus, TrendType, ContentCategory
)
from app.tasks.tiktok_tasks import (
    scrape_trending_content, scrape_hashtag_content, scrape_sound_content,
    monitor_competitor_accounts, update_trend_analysis,
    get_active_scraping_jobs, cancel_scraping_job, get_scraping_statistics
)
from app.services.scraping.tiktok_processor import calculate_trend_metrics

router = APIRouter()


# Trend Discovery and Analysis Endpoints

@router.get("/trends", response_model=Dict[str, Any])
async def get_trends(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    status: Optional[TrendStatus] = None,
    trend_type: Optional[TrendType] = None,
    category: Optional[ContentCategory] = None,
    min_viral_score: float = 0,
    max_viral_score: float = 100,
    limit: int = Query(50, le=200),
    offset: int = Query(0, ge=0),
    sort_by: str = Query("viral_score", regex="^(viral_score|growth_rate|total_views|first_detected)$"),
    sort_order: str = Query("desc", regex="^(asc|desc)$")
):
    """
    Get TikTok trends with filtering and sorting options
    
    Args:
        status: Filter by trend status
        trend_type: Filter by trend type
        category: Filter by content category
        min_viral_score: Minimum viral score filter
        max_viral_score: Maximum viral score filter
        limit: Number of results to return
        offset: Number of results to skip
        sort_by: Field to sort by
        sort_order: Sort order (asc/desc)
        
    Returns:
        Dict containing trends and metadata
    """
    
    # Build query
    query = db.query(TikTokTrend).filter(TikTokTrend.is_active == True)
    
    # Apply filters
    if status:
        query = query.filter(TikTokTrend.trend_status == status.value)
    
    if trend_type:
        query = query.filter(TikTokTrend.trend_type == trend_type.value)
    
    if category:
        query = query.filter(TikTokTrend.content_category == category.value)
    
    query = query.filter(
        and_(
            TikTokTrend.viral_score >= min_viral_score,
            TikTokTrend.viral_score <= max_viral_score
        )
    )
    
    # Apply sorting
    sort_column = getattr(TikTokTrend, sort_by)
    if sort_order == "desc":
        query = query.order_by(desc(sort_column))
    else:
        query = query.order_by(sort_column)
    
    # Get total count
    total_count = query.count()
    
    # Apply pagination
    trends = query.offset(offset).limit(limit).all()
    
    return {
        "trends": [trend.to_dict() for trend in trends],
        "pagination": {
            "total": total_count,
            "limit": limit,
            "offset": offset,
            "has_more": offset + limit < total_count
        },
        "filters": {
            "status": status.value if status else None,
            "trend_type": trend_type.value if trend_type else None,
            "category": category.value if category else None,
            "viral_score_range": [min_viral_score, max_viral_score]
        }
    }


@router.get("/trends/{trend_id}", response_model=Dict[str, Any])
async def get_trend_details(
    trend_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    include_videos: bool = Query(False),
    video_limit: int = Query(20, le=100)
):
    """
    Get detailed information about a specific trend
    
    Args:
        trend_id: Trend ID to retrieve
        include_videos: Whether to include associated videos
        video_limit: Maximum number of videos to include
        
    Returns:
        Dict containing detailed trend information
    """
    
    trend = db.query(TikTokTrend).filter(TikTokTrend.trend_id == trend_id).first()
    
    if not trend:
        raise HTTPException(status_code=404, detail="Trend not found")
    
    # Get trend metrics
    trend_data = await calculate_trend_metrics(trend_id)
    
    result = {
        "trend": trend_data,
        "last_updated": datetime.utcnow().isoformat()
    }
    
    # Include videos if requested
    if include_videos:
        videos = db.query(TikTokVideo).filter(
            TikTokVideo.trend_id == trend.id
        ).order_by(desc(TikTokVideo.viral_score)).limit(video_limit).all()
        
        result["videos"] = [video.to_dict() for video in videos]
        result["video_count"] = db.query(TikTokVideo).filter(
            TikTokVideo.trend_id == trend.id
        ).count()
    
    return result


@router.get("/trends/search", response_model=Dict[str, Any])
async def search_trends(
    query: str = Query(..., min_length=2),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    limit: int = Query(20, le=100)
):
    """
    Search trends by name or keywords
    
    Args:
        query: Search query string
        limit: Maximum number of results
        
    Returns:
        Dict containing search results
    """
    
    # Search in trend names and keywords
    trends = db.query(TikTokTrend).filter(
        and_(
            TikTokTrend.is_active == True,
            or_(
                TikTokTrend.name.ilike(f"%{query}%"),
                TikTokTrend.normalized_name.ilike(f"%{query}%"),
                TikTokTrend.keywords.op("?")(query.lower())  # JSONB contains
            )
        )
    ).order_by(desc(TikTokTrend.viral_score)).limit(limit).all()
    
    return {
        "query": query,
        "results": [trend.to_dict() for trend in trends],
        "count": len(trends)
    }


# Hashtag and Sound Analysis Endpoints

@router.get("/hashtags", response_model=Dict[str, Any])
async def get_trending_hashtags(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    trending_only: bool = Query(True),
    limit: int = Query(50, le=200),
    min_score: float = Query(0)
):
    """
    Get trending hashtags
    
    Args:
        trending_only: Filter to only trending hashtags
        limit: Maximum number of results
        min_score: Minimum trend score filter
        
    Returns:
        Dict containing hashtag data
    """
    
    query = db.query(TikTokHashtag)
    
    if trending_only:
        query = query.filter(TikTokHashtag.is_trending == True)
    
    if min_score > 0:
        query = query.filter(TikTokHashtag.trend_score >= min_score)
    
    hashtags = query.order_by(desc(TikTokHashtag.trend_score)).limit(limit).all()
    
    return {
        "hashtags": [hashtag.to_dict() for hashtag in hashtags],
        "count": len(hashtags),
        "filters": {
            "trending_only": trending_only,
            "min_score": min_score
        }
    }


@router.get("/hashtags/{hashtag}", response_model=Dict[str, Any])
async def get_hashtag_details(
    hashtag: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get detailed information about a specific hashtag
    
    Args:
        hashtag: Hashtag to retrieve (with or without #)
        
    Returns:
        Dict containing hashtag details
    """
    
    # Clean hashtag
    clean_hashtag = hashtag.lower().replace("#", "")
    
    hashtag_record = db.query(TikTokHashtag).filter(
        TikTokHashtag.normalized_hashtag == clean_hashtag
    ).first()
    
    if not hashtag_record:
        raise HTTPException(status_code=404, detail="Hashtag not found")
    
    # Get recent videos using this hashtag
    recent_videos = db.query(TikTokVideo).filter(
        TikTokVideo.hashtags.op("?")(f"#{clean_hashtag}")
    ).order_by(desc(TikTokVideo.scraped_at)).limit(10).all()
    
    return {
        "hashtag": hashtag_record.to_dict(),
        "recent_videos": [video.to_dict() for video in recent_videos],
        "video_sample_count": len(recent_videos)
    }


@router.get("/sounds", response_model=Dict[str, Any])
async def get_trending_sounds(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    trending_only: bool = Query(True),
    limit: int = Query(50, le=200),
    genre: Optional[str] = None
):
    """
    Get trending sounds
    
    Args:
        trending_only: Filter to only trending sounds
        limit: Maximum number of results
        genre: Filter by music genre
        
    Returns:
        Dict containing sound data
    """
    
    query = db.query(TikTokSound)
    
    if trending_only:
        query = query.filter(TikTokSound.is_trending == True)
    
    if genre:
        query = query.filter(TikTokSound.genre.ilike(f"%{genre}%"))
    
    sounds = query.order_by(desc(TikTokSound.trend_score)).limit(limit).all()
    
    return {
        "sounds": [sound.to_dict() for sound in sounds],
        "count": len(sounds),
        "filters": {
            "trending_only": trending_only,
            "genre": genre
        }
    }


# Video Analysis Endpoints

@router.get("/videos", response_model=Dict[str, Any])
async def get_videos(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    min_viral_score: float = Query(0),
    min_views: int = Query(0),
    creator: Optional[str] = None,
    limit: int = Query(50, le=200),
    offset: int = Query(0, ge=0)
):
    """
    Get TikTok videos with filtering options
    
    Args:
        min_viral_score: Minimum viral score filter
        min_views: Minimum view count filter
        creator: Filter by creator username
        limit: Number of results to return
        offset: Number of results to skip
        
    Returns:
        Dict containing video data
    """
    
    query = db.query(TikTokVideo).filter(TikTokVideo.is_active == True)
    
    # Apply filters
    if min_viral_score > 0:
        # Calculate viral score on-the-fly if not stored
        query = query.filter(TikTokVideo.engagement_rate >= min_viral_score / 20)  # Approximate
    
    if min_views > 0:
        query = query.filter(TikTokVideo.view_count >= min_views)
    
    if creator:
        query = query.filter(TikTokVideo.creator_username.ilike(f"%{creator}%"))
    
    # Get total count
    total_count = query.count()
    
    # Apply pagination and sorting
    videos = query.order_by(desc(TikTokVideo.view_count)).offset(offset).limit(limit).all()
    
    return {
        "videos": [video.to_dict() for video in videos],
        "pagination": {
            "total": total_count,
            "limit": limit,
            "offset": offset,
            "has_more": offset + limit < total_count
        }
    }


@router.get("/videos/{video_id}", response_model=Dict[str, Any])
async def get_video_details(
    video_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get detailed information about a specific video
    
    Args:
        video_id: TikTok video ID
        
    Returns:
        Dict containing video details
    """
    
    video = db.query(TikTokVideo).filter(TikTokVideo.video_id == video_id).first()
    
    if not video:
        raise HTTPException(status_code=404, detail="Video not found")
    
    return {
        "video": video.to_dict(),
        "analysis": {
            "viral_indicators": video.content_hooks if hasattr(video, 'content_hooks') else [],
            "trend_participation": bool(video.trend_id),
            "hashtag_strategy": {
                "count": len(video.hashtags) if video.hashtags else 0,
                "trending_tags": [tag for tag in (video.hashtags or []) if tag.lower() in ['#fyp', '#viral', '#trending']]
            }
        }
    }


# Scraping Job Management Endpoints

@router.post("/scraping/trending", response_model=Dict[str, Any])
async def start_trending_scrape(
    background_tasks: BackgroundTasks,
    max_videos: int = Query(1000, ge=100, le=5000),
    regions: List[str] = Query(["US", "UK", "CA", "AU"]),
    current_user: User = Depends(get_current_user)
):
    """
    Start a trending content scraping job
    
    Args:
        max_videos: Maximum number of videos to scrape
        regions: Geographic regions to focus on
        
    Returns:
        Dict containing job information
    """
    
    # Start background task
    task = scrape_trending_content.delay(
        max_videos=max_videos,
        regions=regions,
        include_analysis=True,
        auto_process=True
    )
    
    return {
        "job_id": task.id,
        "status": "started",
        "parameters": {
            "max_videos": max_videos,
            "regions": regions,
            "type": "trending"
        },
        "estimated_duration": "15-30 minutes",
        "started_at": datetime.utcnow().isoformat()
    }


@router.post("/scraping/hashtags", response_model=Dict[str, Any])
async def start_hashtag_scrape(
    hashtags: List[str],
    background_tasks: BackgroundTasks,
    max_videos: int = Query(2000, ge=100, le=10000),
    regions: List[str] = Query(["US", "UK", "CA", "AU"]),
    current_user: User = Depends(get_current_user)
):
    """
    Start a hashtag-specific scraping job
    
    Args:
        hashtags: List of hashtags to scrape
        max_videos: Maximum number of videos to scrape
        regions: Geographic regions to focus on
        
    Returns:
        Dict containing job information
    """
    
    if not hashtags:
        raise HTTPException(status_code=400, detail="At least one hashtag is required")
    
    if len(hashtags) > 20:
        raise HTTPException(status_code=400, detail="Maximum 20 hashtags allowed")
    
    # Start background task
    task = scrape_hashtag_content.delay(
        hashtags=hashtags,
        max_videos=max_videos,
        regions=regions,
        auto_process=True
    )
    
    return {
        "job_id": task.id,
        "status": "started",
        "parameters": {
            "hashtags": hashtags,
            "max_videos": max_videos,
            "regions": regions,
            "type": "hashtag"
        },
        "estimated_duration": f"{len(hashtags) * 5}-{len(hashtags) * 10} minutes",
        "started_at": datetime.utcnow().isoformat()
    }


@router.post("/scraping/sounds", response_model=Dict[str, Any])
async def start_sound_scrape(
    sound_ids: List[str],
    background_tasks: BackgroundTasks,
    max_videos: int = Query(1500, ge=100, le=5000),
    current_user: User = Depends(get_current_user)
):
    """
    Start a sound-specific scraping job
    
    Args:
        sound_ids: List of TikTok sound IDs to scrape
        max_videos: Maximum number of videos to scrape
        
    Returns:
        Dict containing job information
    """
    
    if not sound_ids:
        raise HTTPException(status_code=400, detail="At least one sound ID is required")
    
    if len(sound_ids) > 10:
        raise HTTPException(status_code=400, detail="Maximum 10 sound IDs allowed")
    
    # Start background task
    task = scrape_sound_content.delay(
        sound_ids=sound_ids,
        max_videos=max_videos,
        auto_process=True
    )
    
    return {
        "job_id": task.id,
        "status": "started",
        "parameters": {
            "sound_ids": sound_ids,
            "max_videos": max_videos,
            "type": "sound"
        },
        "estimated_duration": f"{len(sound_ids) * 3}-{len(sound_ids) * 8} minutes",
        "started_at": datetime.utcnow().isoformat()
    }


@router.post("/scraping/competitors", response_model=Dict[str, Any])
async def start_competitor_monitoring(
    usernames: List[str],
    background_tasks: BackgroundTasks,
    max_videos: int = Query(500, ge=50, le=2000),
    current_user: User = Depends(get_current_user)
):
    """
    Start competitor account monitoring
    
    Args:
        usernames: List of TikTok usernames to monitor
        max_videos: Maximum number of videos to scrape per account
        
    Returns:
        Dict containing job information
    """
    
    if not usernames:
        raise HTTPException(status_code=400, detail="At least one username is required")
    
    if len(usernames) > 15:
        raise HTTPException(status_code=400, detail="Maximum 15 usernames allowed")
    
    # Start background task
    task = monitor_competitor_accounts.delay(
        usernames=usernames,
        max_videos=max_videos,
        auto_process=True
    )
    
    return {
        "job_id": task.id,
        "status": "started",
        "parameters": {
            "usernames": usernames,
            "max_videos": max_videos,
            "type": "competitor"
        },
        "estimated_duration": f"{len(usernames) * 2}-{len(usernames) * 5} minutes",
        "started_at": datetime.utcnow().isoformat()
    }


@router.get("/scraping/jobs", response_model=Dict[str, Any])
async def get_scraping_jobs(
    current_user: User = Depends(get_current_user),
    status: Optional[str] = Query(None, regex="^(pending|running|completed|failed|aborted)$"),
    limit: int = Query(50, le=200)
):
    """
    Get scraping job history and status
    
    Args:
        status: Filter by job status
        limit: Maximum number of jobs to return
        
    Returns:
        Dict containing job list and statistics
    """
    
    # Get active jobs
    active_jobs = get_active_scraping_jobs()
    
    # Get statistics
    stats = get_scraping_statistics()
    
    # Filter by status if requested
    if status:
        active_jobs = [job for job in active_jobs if job.get('status') == status]
    
    return {
        "jobs": active_jobs[:limit],
        "statistics": stats,
        "filters": {
            "status": status
        }
    }


@router.get("/scraping/jobs/{job_id}", response_model=Dict[str, Any])
async def get_scraping_job_details(
    job_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get detailed information about a specific scraping job
    
    Args:
        job_id: Scraping job ID
        
    Returns:
        Dict containing job details
    """
    
    job = db.query(TikTokScrapingJob).filter(
        TikTokScrapingJob.job_id == job_id
    ).first()
    
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    
    return {
        "job": job.to_dict(),
        "progress": {
            "estimated_completion": None,  # Would calculate based on current progress
            "current_stage": "processing" if job.status == "running" else job.status
        }
    }


@router.delete("/scraping/jobs/{job_id}", response_model=Dict[str, Any])
async def cancel_scraping_job_endpoint(
    job_id: str,
    current_user: User = Depends(get_current_user)
):
    """
    Cancel a running scraping job
    
    Args:
        job_id: Scraping job ID to cancel
        
    Returns:
        Dict containing cancellation result
    """
    
    success = cancel_scraping_job(job_id)
    
    if not success:
        raise HTTPException(status_code=400, detail="Unable to cancel job")
    
    return {
        "job_id": job_id,
        "status": "cancelled",
        "cancelled_at": datetime.utcnow().isoformat()
    }


# Analytics and Reporting Endpoints

@router.get("/analytics/summary", response_model=Dict[str, Any])
async def get_analytics_summary(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    days: int = Query(7, ge=1, le=30)
):
    """
    Get analytics summary for the specified time period
    
    Args:
        days: Number of days to include in summary
        
    Returns:
        Dict containing analytics summary
    """
    
    start_date = datetime.utcnow().date() - timedelta(days=days)
    
    # Get daily analytics
    daily_analytics = db.query(TikTokAnalytics).filter(
        and_(
            TikTokAnalytics.date >= start_date,
            TikTokAnalytics.period_type == "daily"
        )
    ).order_by(TikTokAnalytics.date).all()
    
    # Get current totals
    total_trends = db.query(TikTokTrend).filter(TikTokTrend.is_active == True).count()
    total_videos = db.query(TikTokVideo).filter(TikTokVideo.is_active == True).count()
    total_hashtags = db.query(TikTokHashtag).count()
    total_sounds = db.query(TikTokSound).count()
    
    # Get top performing trends
    top_trends = db.query(TikTokTrend).filter(
        and_(
            TikTokTrend.is_active == True,
            TikTokTrend.first_detected >= datetime.utcnow() - timedelta(days=days)
        )
    ).order_by(desc(TikTokTrend.viral_score)).limit(5).all()
    
    return {
        "period": {
            "days": days,
            "start_date": start_date.isoformat(),
            "end_date": datetime.utcnow().date().isoformat()
        },
        "current_totals": {
            "trends": total_trends,
            "videos": total_videos,
            "hashtags": total_hashtags,
            "sounds": total_sounds
        },
        "daily_analytics": [analytics.to_dict() for analytics in daily_analytics],
        "top_trends": [trend.to_dict() for trend in top_trends],
        "generated_at": datetime.utcnow().isoformat()
    }


@router.post("/analytics/refresh", response_model=Dict[str, Any])
async def refresh_trend_analysis(
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user)
):
    """
    Trigger a refresh of trend analysis
    
    Returns:
        Dict containing refresh job information
    """
    
    # Start background task
    task = update_trend_analysis.delay()
    
    return {
        "task_id": task.id,
        "status": "started",
        "message": "Trend analysis refresh initiated",
        "started_at": datetime.utcnow().isoformat()
    }


# Content Opportunity Endpoints

@router.get("/opportunities", response_model=Dict[str, Any])
async def get_content_opportunities(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    category: Optional[ContentCategory] = None,
    min_viral_score: float = Query(60),
    limit: int = Query(20, le=100)
):
    """
    Get content creation opportunities based on trending data
    
    Args:
        category: Filter by content category
        min_viral_score: Minimum viral score for opportunities
        limit: Maximum number of opportunities to return
        
    Returns:
        Dict containing content opportunities
    """
    
    # Get emerging and rising trends
    query = db.query(TikTokTrend).filter(
        and_(
            TikTokTrend.is_active == True,
            TikTokTrend.viral_score >= min_viral_score,
            TikTokTrend.trend_status.in_([TrendStatus.EMERGING.value, TrendStatus.RISING.value])
        )
    )
    
    if category:
        query = query.filter(TikTokTrend.content_category == category.value)
    
    opportunities = query.order_by(desc(TikTokTrend.viral_score)).limit(limit).all()
    
    # Enhance with opportunity data
    enhanced_opportunities = []
    for trend in opportunities:
        opportunity = {
            "trend": trend.to_dict(),
            "opportunity_score": min(trend.viral_score + trend.growth_rate * 0.1, 100),
            "recommended_actions": [
                f"Create content using trending hashtags: {', '.join(trend.hashtags[:3])}" if trend.hashtags else None,
                f"Participate in {trend.name} trend" if trend.trend_type == TrendType.CHALLENGE.value else None,
                f"Use popular format patterns from {trend.name}" if trend.trend_type == TrendType.TREND_FORMAT.value else None
            ],
            "estimated_window": "24-48 hours" if trend.trend_status == TrendStatus.EMERGING.value else "2-7 days",
            "competition_level": "low" if trend.total_videos < 10000 else "medium" if trend.total_videos < 100000 else "high"
        }
        
        # Remove None actions
        opportunity["recommended_actions"] = [
            action for action in opportunity["recommended_actions"] if action
        ]
        
        enhanced_opportunities.append(opportunity)
    
    return {
        "opportunities": enhanced_opportunities,
        "count": len(enhanced_opportunities),
        "filters": {
            "category": category.value if category else None,
            "min_viral_score": min_viral_score
        },
        "generated_at": datetime.utcnow().isoformat()
    }