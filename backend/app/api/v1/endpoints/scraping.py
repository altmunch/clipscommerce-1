"""
API endpoints for web scraping operations.
"""

from typing import Any, List, Optional
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, Query
from sqlalchemy.orm import Session
from pydantic import BaseModel, HttpUrl

from app.api.deps import get_current_user, get_db
from app.models import User
from app.models.product import Product, ScrapingJob, CompetitorBrand
from app.tasks.scraping_tasks import (
    enhanced_brand_scraping, product_catalog_scraping,
    competitor_discovery, price_monitoring
)
from app.services.scraping.monitoring import scraping_monitor

router = APIRouter()


# Request models
class BrandScrapingRequest(BaseModel):
    url: HttpUrl
    use_playwright: bool = False
    use_proxies: bool = False
    max_retries: int = 3
    timeout: int = 30


class ProductCatalogRequest(BaseModel):
    brand_id: int
    urls: List[HttpUrl]
    use_playwright: bool = False
    use_proxies: bool = False
    max_products_per_page: int = 20
    concurrent_requests: int = 8


class CompetitorDiscoveryRequest(BaseModel):
    brand_id: int
    search_queries: Optional[List[str]] = None
    max_competitors: int = 10


class PriceMonitoringRequest(BaseModel):
    product_ids: List[int]


# Response models
class ScrapingJobResponse(BaseModel):
    job_id: str
    status: str
    message: str
    
    class Config:
        from_attributes = True


class ScrapingMetricsResponse(BaseModel):
    total_requests: int
    success_rate: float
    avg_response_time: float
    bot_detections: int
    
    class Config:
        from_attributes = True


class HealthStatusResponse(BaseModel):
    status: str
    health_score: float
    issues: List[str]
    metrics: dict
    
    class Config:
        from_attributes = True


@router.post("/brand", response_model=ScrapingJobResponse)
async def scrape_brand(
    request: BrandScrapingRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Start enhanced brand scraping job
    """
    import uuid
    from app.models import Job
    
    # Create job record
    job_id = str(uuid.uuid4())
    job = Job(
        job_id=job_id,
        user_id=current_user.id,
        job_type="enhanced_brand_scraping",
        status="pending",
        progress=0
    )
    db.add(job)
    db.commit()
    
    # Start scraping task
    config = {
        "use_playwright": request.use_playwright,
        "use_proxies": request.use_proxies,
        "max_retries": request.max_retries,
        "timeout": request.timeout
    }
    
    background_tasks.add_task(
        enhanced_brand_scraping.delay,
        current_user.id,
        str(request.url),
        job_id,
        config
    )
    
    return ScrapingJobResponse(
        job_id=job_id,
        status="pending",
        message="Brand scraping job started"
    )


@router.post("/products", response_model=ScrapingJobResponse)
async def scrape_product_catalog(
    request: ProductCatalogRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Start product catalog scraping job
    """
    import uuid
    from app.models import Brand
    
    # Verify brand ownership
    brand = db.query(Brand).filter(
        Brand.id == request.brand_id,
        Brand.user_id == current_user.id
    ).first()
    
    if not brand:
        raise HTTPException(status_code=404, detail="Brand not found")
    
    # Create job record
    job_id = str(uuid.uuid4())
    
    # Start scraping task
    config = {
        "use_playwright": request.use_playwright,
        "use_proxies": request.use_proxies,
        "max_products_per_page": request.max_products_per_page,
        "concurrent_requests": request.concurrent_requests
    }
    
    background_tasks.add_task(
        product_catalog_scraping.delay,
        request.brand_id,
        [str(url) for url in request.urls],
        job_id,
        config
    )
    
    return ScrapingJobResponse(
        job_id=job_id,
        status="pending",
        message="Product catalog scraping job started"
    )


@router.post("/competitors", response_model=ScrapingJobResponse)
async def discover_competitors(
    request: CompetitorDiscoveryRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Start competitor discovery job
    """
    import uuid
    from app.models import Brand
    
    # Verify brand ownership
    brand = db.query(Brand).filter(
        Brand.id == request.brand_id,
        Brand.user_id == current_user.id
    ).first()
    
    if not brand:
        raise HTTPException(status_code=404, detail="Brand not found")
    
    # Create job record
    job_id = str(uuid.uuid4())
    
    # Start discovery task
    config = {
        "search_queries": request.search_queries,
        "max_competitors": request.max_competitors
    }
    
    background_tasks.add_task(
        competitor_discovery.delay,
        request.brand_id,
        job_id,
        config
    )
    
    return ScrapingJobResponse(
        job_id=job_id,
        status="pending",
        message="Competitor discovery job started"
    )


@router.post("/price-monitoring", response_model=ScrapingJobResponse)
async def monitor_prices(
    request: PriceMonitoringRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Start price monitoring job
    """
    import uuid
    
    # Verify product ownership through brands
    from app.models import Brand
    user_brand_ids = db.query(Brand.id).filter(Brand.user_id == current_user.id).subquery()
    
    valid_products = db.query(Product.id).filter(
        Product.id.in_(request.product_ids),
        Product.brand_id.in_(user_brand_ids)
    ).all()
    
    valid_product_ids = [p.id for p in valid_products]
    
    if not valid_product_ids:
        raise HTTPException(status_code=404, detail="No valid products found")
    
    # Create job record
    job_id = str(uuid.uuid4())
    
    # Start monitoring task
    background_tasks.add_task(
        price_monitoring.delay,
        valid_product_ids,
        job_id
    )
    
    return ScrapingJobResponse(
        job_id=job_id,
        status="pending",
        message=f"Price monitoring started for {len(valid_product_ids)} products"
    )


@router.get("/jobs/{job_id}")
async def get_scraping_job(
    job_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get scraping job status and results
    """
    job = db.query(ScrapingJob).filter(ScrapingJob.job_id == job_id).first()
    
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    
    # Check access permission
    if job.brand_id:
        from app.models import Brand
        brand = db.query(Brand).filter(
            Brand.id == job.brand_id,
            Brand.user_id == current_user.id
        ).first()
        
        if not brand:
            raise HTTPException(status_code=403, detail="Access denied")
    
    return {
        "job_id": job.job_id,
        "job_type": job.job_type,
        "status": job.status,
        "progress": job.progress,
        "products_found": job.products_found,
        "products_created": job.products_created,
        "products_updated": job.products_updated,
        "pages_scraped": job.pages_scraped,
        "error_message": job.error_message,
        "created_at": job.created_at,
        "completed_at": job.completed_at
    }


@router.get("/jobs")
async def list_scraping_jobs(
    limit: int = Query(default=20, le=100),
    offset: int = Query(default=0, ge=0),
    job_type: Optional[str] = Query(default=None),
    status: Optional[str] = Query(default=None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    List scraping jobs for current user
    """
    from app.models import Brand
    
    # Get user's brand IDs
    user_brand_ids = db.query(Brand.id).filter(Brand.user_id == current_user.id).subquery()
    
    query = db.query(ScrapingJob).filter(
        ScrapingJob.brand_id.in_(user_brand_ids)
    )
    
    if job_type:
        query = query.filter(ScrapingJob.job_type == job_type)
    
    if status:
        query = query.filter(ScrapingJob.status == status)
    
    total = query.count()
    jobs = query.order_by(ScrapingJob.created_at.desc()).offset(offset).limit(limit).all()
    
    return {
        "total": total,
        "jobs": [
            {
                "job_id": job.job_id,
                "job_type": job.job_type,
                "status": job.status,
                "progress": job.progress,
                "created_at": job.created_at,
                "completed_at": job.completed_at
            }
            for job in jobs
        ]
    }


@router.get("/products")
async def list_scraped_products(
    brand_id: Optional[int] = Query(default=None),
    limit: int = Query(default=20, le=100),
    offset: int = Query(default=0, ge=0),
    category: Optional[str] = Query(default=None),
    availability: Optional[str] = Query(default=None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    List scraped products
    """
    from app.models import Brand
    
    # Get user's brand IDs
    user_brand_ids = db.query(Brand.id).filter(Brand.user_id == current_user.id).subquery()
    
    query = db.query(Product).filter(Product.brand_id.in_(user_brand_ids))
    
    if brand_id:
        # Verify brand ownership
        brand = db.query(Brand).filter(
            Brand.id == brand_id,
            Brand.user_id == current_user.id
        ).first()
        
        if not brand:
            raise HTTPException(status_code=404, detail="Brand not found")
        
        query = query.filter(Product.brand_id == brand_id)
    
    if category:
        query = query.filter(Product.category.ilike(f"%{category}%"))
    
    if availability:
        query = query.filter(Product.availability == availability)
    
    total = query.count()
    products = query.order_by(Product.last_updated_at.desc()).offset(offset).limit(limit).all()
    
    return {
        "total": total,
        "products": [
            {
                "id": product.id,
                "name": product.name,
                "price": product.price,
                "currency": product.currency,
                "availability": product.availability,
                "category": product.category,
                "source_url": product.source_url,
                "images": product.images[:1] if product.images else [],  # First image only
                "last_updated_at": product.last_updated_at
            }
            for product in products
        ]
    }


@router.get("/competitors")
async def list_competitors(
    brand_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    List competitor brands
    """
    from app.models import Brand
    
    # Verify brand ownership
    brand = db.query(Brand).filter(
        Brand.id == brand_id,
        Brand.user_id == current_user.id
    ).first()
    
    if not brand:
        raise HTTPException(status_code=404, detail="Brand not found")
    
    competitors = db.query(CompetitorBrand).filter(
        CompetitorBrand.brand_id == brand_id
    ).order_by(CompetitorBrand.similarity_score.desc()).all()
    
    return {
        "competitors": [
            {
                "id": comp.id,
                "name": comp.name,
                "url": comp.url,
                "similarity_score": comp.similarity_score,
                "threat_level": comp.threat_level,
                "competition_type": comp.competition_type,
                "products_tracked": comp.products_tracked,
                "avg_product_price": comp.avg_product_price,
                "discovered_at": comp.discovered_at
            }
            for comp in competitors
        ]
    }


@router.get("/metrics/domain/{domain}", response_model=ScrapingMetricsResponse)
async def get_domain_metrics(
    domain: str,
    current_user: User = Depends(get_current_user)
):
    """
    Get scraping metrics for specific domain
    """
    metrics = scraping_monitor.get_domain_metrics(domain)
    
    return ScrapingMetricsResponse(
        total_requests=metrics.total_requests,
        success_rate=metrics.success_rate,
        avg_response_time=metrics.avg_response_time,
        bot_detections=metrics.bot_detections
    )


@router.get("/health", response_model=HealthStatusResponse)
async def get_scraping_health(
    current_user: User = Depends(get_current_user)
):
    """
    Get overall scraping system health
    """
    health_status = scraping_monitor.get_health_status()
    
    return HealthStatusResponse(**health_status)


@router.get("/jobs/{job_id}/analysis")
async def get_job_analysis(
    job_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get detailed performance analysis for a scraping job
    """
    # Verify job access
    job = db.query(ScrapingJob).filter(ScrapingJob.id == job_id).first()
    
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    
    if job.brand_id:
        from app.models import Brand
        brand = db.query(Brand).filter(
            Brand.id == job.brand_id,
            Brand.user_id == current_user.id
        ).first()
        
        if not brand:
            raise HTTPException(status_code=403, detail="Access denied")
    
    # Get performance analysis
    analysis = await scraping_monitor.analyze_job_performance(job_id)
    
    return analysis


@router.post("/jobs/{job_id}/retry")
async def retry_failed_job(
    job_id: str,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Retry a failed scraping job
    """
    job = db.query(ScrapingJob).filter(ScrapingJob.job_id == job_id).first()
    
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    
    if job.status != "failed":
        raise HTTPException(status_code=400, detail="Job is not in failed state")
    
    # Verify access
    if job.brand_id:
        from app.models import Brand
        brand = db.query(Brand).filter(
            Brand.id == job.brand_id,
            Brand.user_id == current_user.id
        ).first()
        
        if not brand:
            raise HTTPException(status_code=403, detail="Access denied")
    
    # Reset job status
    job.status = "pending"
    job.progress = 0
    job.error_message = None
    job.retry_count = (job.retry_count or 0) + 1
    
    if job.retry_count > job.max_retries:
        raise HTTPException(status_code=400, detail="Maximum retries exceeded")
    
    db.commit()
    
    # Restart appropriate task
    if job.job_type == "enhanced_brand_scraping":
        background_tasks.add_task(
            enhanced_brand_scraping.delay,
            # Get user_id from brand
            brand.user_id if job.brand_id else current_user.id,
            job.target_urls[0] if job.target_urls else "",
            job.job_id,
            job.scraping_config or {}
        )
    elif job.job_type == "product_catalog_scraping":
        background_tasks.add_task(
            product_catalog_scraping.delay,
            job.brand_id,
            job.target_urls or [],
            job.job_id,
            job.scraping_config or {}
        )
    # Add other job types as needed
    
    return {"message": "Job retry initiated", "retry_count": job.retry_count}