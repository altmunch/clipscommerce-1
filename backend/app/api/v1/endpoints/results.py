from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from sqlalchemy import func
from app.db.session import get_db
from app.api.deps import get_current_user
from app.models.user import User
from app.models.brand import Brand
from app.models.content import Video
from app.schemas.results import (
    KPIResponse, ChartResponse, ContentResponse, InsightsResponse,
    KPIData, ChartDataPoint, ContentPerformance, Pagination, Insight
)
from datetime import datetime, date, timedelta
from typing import Optional
import math

router = APIRouter()

@router.get("/kpis", response_model=KPIResponse)
def get_kpis(
    brand_id: int = Query(..., alias="brandId"),
    start_date: Optional[date] = Query(None, alias="startDate"),
    end_date: Optional[date] = Query(None, alias="endDate"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get KPI data for the dashboard
    """
    # Verify brand belongs to user
    brand = db.query(Brand).filter(
        Brand.id == brand_id,
        Brand.user_id == current_user.id
    ).first()
    
    if not brand:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Brand not found"
        )
    
    # Build query with date filters
    query = db.query(Video).join(Blueprint).join(Idea).filter(
        Idea.brand_id == brand_id,
        Video.status.in_(["published", "scheduled"])
    )
    
    if start_date:
        query = query.filter(Video.created_at >= start_date)
    if end_date:
        query = query.filter(Video.created_at <= end_date)
    
    videos = query.all()
    
    # Calculate KPIs
    total_revenue = sum(video.revenue for video in videos)
    total_views = sum(video.views for video in videos)
    total_clicks = sum(video.clicks for video in videos)
    avg_conversion_rate = (total_clicks / total_views) if total_views > 0 else 0
    
    kpi_data = KPIData(
        attributedRevenue=total_revenue,
        totalViews=total_views,
        clicksDriven=total_clicks,
        avgConversionRate=round(avg_conversion_rate, 4)
    )
    
    return KPIResponse(data=kpi_data)

@router.get("/chart", response_model=ChartResponse)
def get_chart_data(
    brand_id: int = Query(..., alias="brandId"),
    metric: str = Query(...),
    start_date: Optional[date] = Query(None, alias="startDate"),
    end_date: Optional[date] = Query(None, alias="endDate"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get time-series data for performance chart
    """
    # Verify brand belongs to user
    brand = db.query(Brand).filter(
        Brand.id == brand_id,
        Brand.user_id == current_user.id
    ).first()
    
    if not brand:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Brand not found"
        )
    
    # Set default date range if not provided
    if not end_date:
        end_date = date.today()
    if not start_date:
        start_date = end_date - timedelta(days=30)
    
    # Map metric to field
    metric_field_map = {
        "views": Video.views,
        "clicks": Video.clicks,
        "revenue": Video.revenue
    }
    
    if metric not in metric_field_map:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid metric"
        )
    
    metric_field = metric_field_map[metric]
    
    # Query data grouped by date
    query = db.query(
        func.date(Video.created_at).label("date"),
        func.sum(metric_field).label("value")
    ).join(Blueprint).join(Idea).filter(
        Idea.brand_id == brand_id,
        Video.status.in_(["published", "scheduled"]),
        func.date(Video.created_at) >= start_date,
        func.date(Video.created_at) <= end_date
    ).group_by(func.date(Video.created_at)).order_by(func.date(Video.created_at))
    
    results = query.all()
    
    # Convert to chart data points
    chart_data = [
        ChartDataPoint(
            date=result.date.strftime("%Y-%m-%d"),
            value=float(result.value or 0)
        )
        for result in results
    ]
    
    return ChartResponse(data=chart_data)

@router.get("/content", response_model=ContentResponse)
def get_content_performance(
    brand_id: int = Query(..., alias="brandId"),
    sort_by: str = Query("revenue", alias="sortBy"),
    page: int = Query(1),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get paginated and sortable content performance table
    """
    # Verify brand belongs to user
    brand = db.query(Brand).filter(
        Brand.id == brand_id,
        Brand.user_id == current_user.id
    ).first()
    
    if not brand:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Brand not found"
        )
    
    # Map sort_by to field
    sort_field_map = {
        "views": Video.views,
        "clicks": Video.clicks,
        "revenue": Video.revenue
    }
    
    if sort_by not in sort_field_map:
        sort_by = "revenue"
    
    sort_field = sort_field_map[sort_by]
    
    # Pagination settings
    page_size = 20
    offset = (page - 1) * page_size
    
    # Query videos with pagination
    query = db.query(Video).join(Blueprint).join(Idea).filter(
        Idea.brand_id == brand_id,
        Video.status.in_(["published", "scheduled"])
    )
    
    total_count = query.count()
    total_pages = math.ceil(total_count / page_size)
    
    videos = query.order_by(sort_field.desc()).offset(offset).limit(page_size).all()
    
    # Convert to content performance objects
    content_data = [
        ContentPerformance(
            videoId=video.id,
            thumbnailUrl=video.thumbnail_url,
            views=video.views,
            clicks=video.clicks,
            revenue=video.revenue
        )
        for video in videos
    ]
    
    pagination = Pagination(
        currentPage=page,
        totalPages=total_pages
    )
    
    return ContentResponse(data=content_data, pagination=pagination)

@router.get("/insights", response_model=InsightsResponse)
def get_insights(
    brand_id: int = Query(..., alias="brandId"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get AI-generated growth recommendations
    """
    # Verify brand belongs to user
    brand = db.query(Brand).filter(
        Brand.id == brand_id,
        Brand.user_id == current_user.id
    ).first()
    
    if not brand:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Brand not found"
        )
    
    # Mock AI insights (in production, this would analyze performance data)
    insights = [
        Insight(
            title="Winning Format",
            insight="Your 'Unboxing' videos have a 50% higher CTR than other content types. Consider creating more unboxing content."
        ),
        Insight(
            title="Optimal Posting Time",
            insight="Videos posted between 6-8 PM generate 35% more engagement. Schedule your best content during these hours."
        ),
        Insight(
            title="Audience Preference",
            insight="Short-form videos (15-20 seconds) perform 60% better than longer content. Keep your hooks concise and impactful."
        )
    ]
    
    return InsightsResponse(data=insights)