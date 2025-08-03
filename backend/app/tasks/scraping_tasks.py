"""
Enhanced scraping tasks for comprehensive brand and product discovery.
"""

import uuid
import asyncio
import time
from typing import Any, Dict, List, Optional
from celery import current_task
from sqlalchemy.orm import Session
import logging

from app.core.celery_app import celery_app
from app.db.session import SessionLocal
from app.models import Brand, Job
from app.models.product import (
    Product, ProductPriceHistory, ScrapingJob, 
    ScrapingSession, CompetitorBrand
)
from app.services.scraping import (
    BrandScraper, ProductScraper, PlaywrightScraper,
    EcommerceDetector, ProxyManager, AntiDetectionManager
)

logger = logging.getLogger(__name__)


@celery_app.task(name="enhanced_brand_scraping")
def enhanced_brand_scraping(user_id: int, url: str, job_id: str, config: Dict[str, Any] = None):
    """
    Enhanced brand scraping with comprehensive data extraction
    """
    db = SessionLocal()
    scraping_job = None
    
    try:
        # Update job status
        job = db.query(Job).filter(Job.job_id == job_id).first()
        if job:
            job.status = "processing"
            job.progress = 5
            db.commit()
        
        # Create scraping job record
        scraping_job = ScrapingJob(
            brand_id=None,  # Will be set after brand creation
            job_id=job_id,
            job_type="enhanced_brand_scraping",
            target_urls=[url],
            scraping_config=config or {},
            status="running",
            progress=10
        )
        db.add(scraping_job)
        db.commit()
        
        current_task.update_state(state="PROGRESS", meta={"progress": 15})
        
        # Run scraping asynchronously
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        try:
            result = loop.run_until_complete(
                _run_enhanced_brand_scraping(url, config or {}, scraping_job.id, db)
            )
        finally:
            loop.close()
        
        current_task.update_state(state="PROGRESS", meta={"progress": 80})
        
        # Create or update brand record
        brand = _create_or_update_brand(user_id, url, result, db)
        
        # Update scraping job
        scraping_job.brand_id = brand.id
        scraping_job.status = "completed"
        scraping_job.progress = 100
        scraping_job.products_found = len(result.get("products", []))
        scraping_job.completed_at = db.execute("SELECT NOW()").scalar()
        
        current_task.update_state(state="PROGRESS", meta={"progress": 90})
        
        # Update main job
        if job:
            job.status = "complete"
            job.progress = 100
            job.result = {
                "message": "Enhanced brand scraping complete",
                "resourceId": str(brand.id),
                "brandId": brand.id,
                "brandName": brand.name,
                "productsFound": len(result.get("products", [])),
                "competitorsFound": len(result.get("competitors", []))
            }
        
        db.commit()
        
        return {
            "success": True,
            "brandId": brand.id,
            "brandName": brand.name,
            "productsFound": len(result.get("products", [])),
            "competitorsFound": len(result.get("competitors", []))
        }
        
    except Exception as e:
        logger.error(f"Enhanced brand scraping failed: {str(e)}")
        
        # Update scraping job status
        if scraping_job:
            scraping_job.status = "failed"
            scraping_job.error_message = str(e)
        
        # Update main job
        if job:
            job.status = "failed"
            job.error = str(e)
        
        db.commit()
        raise e
        
    finally:
        db.close()


@celery_app.task(name="product_catalog_scraping")
def product_catalog_scraping(brand_id: int, urls: List[str], job_id: str, config: Dict[str, Any] = None):
    """
    Comprehensive product catalog scraping
    """
    db = SessionLocal()
    scraping_job = None
    
    try:
        # Create scraping job
        scraping_job = ScrapingJob(
            brand_id=brand_id,
            job_id=job_id,
            job_type="product_catalog_scraping",
            target_urls=urls,
            scraping_config=config or {},
            status="running",
            progress=0
        )
        db.add(scraping_job)
        db.commit()
        
        current_task.update_state(state="PROGRESS", meta={"progress": 5})
        
        # Run product scraping
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        try:
            results = loop.run_until_complete(
                _run_product_catalog_scraping(urls, config or {}, scraping_job.id, db)
            )
        finally:
            loop.close()
        
        # Process results
        products_created = 0
        products_updated = 0
        
        for result in results:
            if result.get("success") and result.get("products"):
                for product_data in result["products"]:
                    product, created = _create_or_update_product(
                        brand_id, product_data, db
                    )
                    if created:
                        products_created += 1
                    else:
                        products_updated += 1
        
        # Update scraping job
        scraping_job.status = "completed"
        scraping_job.progress = 100
        scraping_job.products_found = len([r for r in results if r.get("products")])
        scraping_job.products_created = products_created
        scraping_job.products_updated = products_updated
        scraping_job.pages_scraped = len(urls)
        scraping_job.completed_at = db.execute("SELECT NOW()").scalar()
        
        db.commit()
        
        return {
            "success": True,
            "productsCreated": products_created,
            "productsUpdated": products_updated,
            "pagesScraped": len(urls)
        }
        
    except Exception as e:
        logger.error(f"Product catalog scraping failed: {str(e)}")
        
        if scraping_job:
            scraping_job.status = "failed"
            scraping_job.error_message = str(e)
            db.commit()
        
        raise e
        
    finally:
        db.close()


@celery_app.task(name="competitor_discovery")
def competitor_discovery(brand_id: int, job_id: str, config: Dict[str, Any] = None):
    """
    Discover and analyze competitor brands
    """
    db = SessionLocal()
    scraping_job = None
    
    try:
        # Get brand information
        brand = db.query(Brand).filter(Brand.id == brand_id).first()
        if not brand:
            raise ValueError("Brand not found")
        
        # Create scraping job
        scraping_job = ScrapingJob(
            brand_id=brand_id,
            job_id=job_id,
            job_type="competitor_discovery",
            target_urls=[],
            scraping_config=config or {},
            status="running",
            progress=0
        )
        db.add(scraping_job)
        db.commit()
        
        current_task.update_state(state="PROGRESS", meta={"progress": 10})
        
        # Run competitor discovery
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        try:
            competitors = loop.run_until_complete(
                _run_competitor_discovery(brand, config or {}, scraping_job.id, db)
            )
        finally:
            loop.close()
        
        # Store competitor data
        competitors_added = 0
        for competitor_data in competitors:
            competitor = _create_or_update_competitor(
                brand_id, competitor_data, db
            )
            if competitor:
                competitors_added += 1
        
        # Update scraping job
        scraping_job.status = "completed"
        scraping_job.progress = 100
        scraping_job.completed_at = db.execute("SELECT NOW()").scalar()
        
        db.commit()
        
        return {
            "success": True,
            "competitorsFound": len(competitors),
            "competitorsAdded": competitors_added
        }
        
    except Exception as e:
        logger.error(f"Competitor discovery failed: {str(e)}")
        
        if scraping_job:
            scraping_job.status = "failed"
            scraping_job.error_message = str(e)
            db.commit()
        
        raise e
        
    finally:
        db.close()


@celery_app.task(name="price_monitoring")
def price_monitoring(product_ids: List[int], job_id: str):
    """
    Monitor price changes for specific products
    """
    db = SessionLocal()
    scraping_job = None
    
    try:
        # Create scraping job
        scraping_job = ScrapingJob(
            job_id=job_id,
            job_type="price_monitoring",
            target_urls=[],
            scraping_config={"product_ids": product_ids},
            status="running",
            progress=0
        )
        db.add(scraping_job)
        db.commit()
        
        # Get products to monitor
        products = db.query(Product).filter(Product.id.in_(product_ids)).all()
        
        if not products:
            raise ValueError("No products found for monitoring")
        
        current_task.update_state(state="PROGRESS", meta={"progress": 10})
        
        # Run price monitoring
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        try:
            results = loop.run_until_complete(
                _run_price_monitoring(products, scraping_job.id, db)
            )
        finally:
            loop.close()
        
        # Process results and update price history
        price_updates = 0
        for result in results:
            if result.get("success") and result.get("price_data"):
                price_data = result["price_data"]
                product_id = result["product_id"]
                
                # Create price history record
                price_history = ProductPriceHistory(
                    product_id=product_id,
                    price=price_data.get("price"),
                    original_price=price_data.get("original_price"),
                    currency=price_data.get("currency", "USD"),
                    discount_percentage=price_data.get("discount_percentage"),
                    availability=price_data.get("availability"),
                    in_stock=price_data.get("availability") == "in_stock",
                    source_url=price_data.get("source_url")
                )
                db.add(price_history)
                
                # Update product with latest price
                product = db.query(Product).filter(Product.id == product_id).first()
                if product:
                    product.price = price_data.get("price")
                    product.availability = price_data.get("availability")
                    product.last_scraped_at = db.execute("SELECT NOW()").scalar()
                
                price_updates += 1
        
        # Update scraping job
        scraping_job.status = "completed"
        scraping_job.progress = 100
        scraping_job.products_updated = price_updates
        scraping_job.completed_at = db.execute("SELECT NOW()").scalar()
        
        db.commit()
        
        return {
            "success": True,
            "productsMonitored": len(products),
            "priceUpdates": price_updates
        }
        
    except Exception as e:
        logger.error(f"Price monitoring failed: {str(e)}")
        
        if scraping_job:
            scraping_job.status = "failed"
            scraping_job.error_message = str(e)
            db.commit()
        
        raise e
        
    finally:
        db.close()


async def _run_enhanced_brand_scraping(url: str, config: Dict[str, Any], 
                                     job_id: int, db: Session) -> Dict[str, Any]:
    """
    Run enhanced brand scraping with comprehensive data extraction
    """
    start_time = time.time()
    
    # Choose scraper based on config
    use_playwright = config.get("use_playwright", False)
    
    if use_playwright:
        async with PlaywrightScraper(
            headless=config.get("headless", True),
            wait_timeout=config.get("timeout", 30000)
        ) as scraper:
            result = await scraper.scrape(url)
    else:
        async with BrandScraper(
            max_retries=config.get("max_retries", 3),
            timeout=config.get("timeout", 30)
        ) as scraper:
            result = await scraper.scrape(url)
    
    # Record session
    session = ScrapingSession(
        job_id=job_id,
        session_id=str(uuid.uuid4()),
        scraper_type="PlaywrightScraper" if use_playwright else "BrandScraper",
        target_url=url,
        target_domain=scraper.extract_domain(url),
        success=result.success,
        data_extracted=result.data if result.success else None,
        response_time=result.processing_time,
        error_type="scraping_error" if not result.success else None,
        error_message=result.error if not result.success else None,
        completed_at=db.execute("SELECT NOW()").scalar()
    )
    db.add(session)
    db.commit()
    
    if not result.success:
        raise Exception(f"Scraping failed: {result.error}")
    
    return result.data


async def _run_product_catalog_scraping(urls: List[str], config: Dict[str, Any],
                                      job_id: int, db: Session) -> List[Dict[str, Any]]:
    """
    Run product catalog scraping for multiple URLs
    """
    results = []
    
    # Setup proxy and anti-detection if configured
    proxy_manager = None
    if config.get("use_proxies"):
        proxy_manager = ProxyManager(config.get("proxy_list", []))
        if config.get("load_free_proxies"):
            await proxy_manager.load_free_proxies()
    
    anti_detection = AntiDetectionManager()
    
    # Choose scraper type
    use_playwright = config.get("use_playwright", False)
    
    for i, url in enumerate(urls):
        try:
            current_task.update_state(
                state="PROGRESS", 
                meta={"progress": 20 + (i * 60 / len(urls))}
            )
            
            # Get proxy if available
            proxy = None
            if proxy_manager:
                proxy = await proxy_manager.get_working_proxy()
            
            # Add intelligent delay
            if i > 0:
                delay = anti_detection.calculate_delay(
                    anti_detection.extract_domain(url)
                )
                await asyncio.sleep(delay)
            
            # Record request
            anti_detection.record_request(url)
            
            # Scrape with appropriate scraper
            if use_playwright:
                async with PlaywrightScraper(
                    headless=config.get("headless", True),
                    wait_timeout=config.get("timeout", 30000)
                ) as scraper:
                    result = await scraper.scrape(url)
            else:
                # Use product scraper for product-specific extraction
                async with ProductScraper(
                    max_retries=config.get("max_retries", 3),
                    timeout=config.get("timeout", 30)
                ) as scraper:
                    result = await scraper.scrape(url)
            
            # Record session
            session = ScrapingSession(
                job_id=job_id,
                session_id=str(uuid.uuid4()),
                scraper_type="PlaywrightScraper" if use_playwright else "ProductScraper",
                use_proxy=proxy is not None,
                proxy_info=proxy.dict if proxy else None,
                target_url=url,
                target_domain=scraper.extract_domain(url),
                success=result.success,
                data_extracted=result.data if result.success else None,
                products_found=len(result.data.get("products", [])) if result.success else 0,
                response_time=result.processing_time,
                error_type="scraping_error" if not result.success else None,
                error_message=result.error if not result.success else None,
                completed_at=db.execute("SELECT NOW()").scalar()
            )
            db.add(session)
            
            # Mark proxy success/failure
            if proxy:
                if result.success:
                    await proxy_manager.mark_proxy_success(proxy, result.processing_time)
                else:
                    await proxy_manager.mark_proxy_failure(proxy, result.error or "Unknown error")
            
            results.append({
                "url": url,
                "success": result.success,
                "products": result.data.get("products", []) if result.success else [],
                "error": result.error
            })
            
        except Exception as e:
            logger.error(f"Failed to scrape {url}: {e}")
            results.append({
                "url": url,
                "success": False,
                "products": [],
                "error": str(e)
            })
        
        # Commit session data periodically
        if i % 10 == 0:
            db.commit()
    
    db.commit()
    return results


async def _run_competitor_discovery(brand: Brand, config: Dict[str, Any],
                                  job_id: int, db: Session) -> List[Dict[str, Any]]:
    """
    Run competitor discovery and analysis
    """
    competitors = []
    
    # This would implement various competitor discovery strategies:
    # 1. Search engine scraping
    # 2. Industry directory scraping
    # 3. Social media competitor analysis
    # 4. Similar website analysis
    
    # For now, return placeholder structure
    return competitors


async def _run_price_monitoring(products: List[Product], job_id: int, 
                              db: Session) -> List[Dict[str, Any]]:
    """
    Monitor prices for given products
    """
    results = []
    
    async with ProductScraper() as scraper:
        for product in products:
            try:
                current_task.update_state(
                    state="PROGRESS",
                    meta={"progress": 20 + (len(results) * 60 / len(products))}
                )
                
                # Scrape current product page
                result = await scraper.scrape(product.source_url)
                
                if result.success and result.data.get("product"):
                    product_data = result.data["product"]
                    
                    results.append({
                        "product_id": product.id,
                        "success": True,
                        "price_data": {
                            "price": product_data.get("price"),
                            "original_price": product_data.get("original_price"),
                            "currency": product_data.get("currency"),
                            "discount_percentage": product_data.get("discount_percentage"),
                            "availability": product_data.get("availability"),
                            "source_url": product.source_url
                        }
                    })
                else:
                    results.append({
                        "product_id": product.id,
                        "success": False,
                        "error": result.error
                    })
                
                # Add delay between products
                await asyncio.sleep(1)
                
            except Exception as e:
                logger.error(f"Failed to monitor price for product {product.id}: {e}")
                results.append({
                    "product_id": product.id,
                    "success": False,
                    "error": str(e)
                })
    
    return results


def _create_or_update_brand(user_id: int, url: str, scraping_result: Dict[str, Any], 
                           db: Session) -> Brand:
    """
    Create or update brand with scraping results
    """
    brand_data = scraping_result.get("brand", {})
    
    # Check if brand already exists
    brand = db.query(Brand).filter(
        Brand.user_id == user_id,
        Brand.url == url
    ).first()
    
    if not brand:
        # Create new brand
        brand = Brand(
            user_id=user_id,
            name=brand_data.get("name", "Unknown Brand"),
            url=url,
            logo_url=brand_data.get("logo_url"),
            colors=brand_data.get("colors", {}),
            voice=brand_data.get("voice_tone", {}),
            pillars=brand_data.get("content_themes", []),
            industry=brand_data.get("industry"),
            target_audience=brand_data.get("target_audience", {}),
            unique_value_proposition=brand_data.get("value_proposition"),
            competitors=brand_data.get("competitors", [])
        )
        db.add(brand)
    else:
        # Update existing brand
        brand.name = brand_data.get("name", brand.name)
        brand.logo_url = brand_data.get("logo_url", brand.logo_url)
        brand.colors = brand_data.get("colors", brand.colors)
        brand.voice = brand_data.get("voice_tone", brand.voice)
        brand.industry = brand_data.get("industry", brand.industry)
        brand.target_audience = brand_data.get("target_audience", brand.target_audience)
        brand.unique_value_proposition = brand_data.get("value_proposition", brand.unique_value_proposition)
        brand.updated_at = db.execute("SELECT NOW()").scalar()
    
    db.flush()
    return brand


def _create_or_update_product(brand_id: int, product_data: Dict[str, Any], 
                             db: Session) -> Tuple[Product, bool]:
    """
    Create or update product with scraping data
    """
    # Check if product exists (by URL or SKU)
    product = None
    if product_data.get("url"):
        product = db.query(Product).filter(
            Product.source_url == product_data["url"]
        ).first()
    
    if not product and product_data.get("sku"):
        product = db.query(Product).filter(
            Product.brand_id == brand_id,
            Product.sku == product_data["sku"]
        ).first()
    
    created = False
    
    if not product:
        # Create new product
        product = Product(
            brand_id=brand_id,
            name=product_data.get("name"),
            description=product_data.get("description"),
            short_description=product_data.get("short_description"),
            sku=product_data.get("sku"),
            brand_name=product_data.get("brand"),
            category=product_data.get("category"),
            price=product_data.get("price"),
            original_price=product_data.get("original_price"),
            currency=product_data.get("currency", "USD"),
            availability=product_data.get("availability"),
            source_url=product_data.get("url"),
            source_domain=product_data.get("source_domain"),
            platform_type=product_data.get("platform_type"),
            images=product_data.get("images", []),
            variants=product_data.get("variants", []),
            attributes=product_data.get("attributes", {}),
            features=product_data.get("features", []),
            tags=product_data.get("tags", []),
            reviews_data=product_data.get("reviews", {}),
            shipping_info=product_data.get("shipping_info", {}),
            seller_info=product_data.get("seller_info", {}),
            social_proof=product_data.get("social_proof", []),
            data_quality_score=product_data.get("data_quality_score", 0.0),
            last_scraped_at=db.execute("SELECT NOW()").scalar()
        )
        db.add(product)
        created = True
    else:
        # Update existing product
        product.name = product_data.get("name", product.name)
        product.description = product_data.get("description", product.description)
        product.price = product_data.get("price", product.price)
        product.availability = product_data.get("availability", product.availability)
        product.images = product_data.get("images", product.images)
        product.variants = product_data.get("variants", product.variants)
        product.last_updated_at = db.execute("SELECT NOW()").scalar()
        product.last_scraped_at = db.execute("SELECT NOW()").scalar()
    
    db.flush()
    return product, created


def _create_or_update_competitor(brand_id: int, competitor_data: Dict[str, Any], 
                                db: Session) -> Optional[CompetitorBrand]:
    """
    Create or update competitor brand
    """
    # Check if competitor exists
    competitor = db.query(CompetitorBrand).filter(
        CompetitorBrand.brand_id == brand_id,
        CompetitorBrand.url == competitor_data.get("url")
    ).first()
    
    if not competitor:
        # Create new competitor
        competitor = CompetitorBrand(
            brand_id=brand_id,
            name=competitor_data.get("name"),
            url=competitor_data.get("url"),
            similarity_score=competitor_data.get("similarity_score"),
            threat_level=competitor_data.get("threat_level"),
            competition_type=competitor_data.get("competition_type"),
            brand_colors=competitor_data.get("colors", {}),
            brand_voice=competitor_data.get("voice", {}),
            target_audience=competitor_data.get("target_audience", {}),
            monitoring_enabled=True
        )
        db.add(competitor)
        db.flush()
        return competitor
    else:
        # Update existing competitor
        competitor.similarity_score = competitor_data.get("similarity_score", competitor.similarity_score)
        competitor.threat_level = competitor_data.get("threat_level", competitor.threat_level)
        competitor.updated_at = db.execute("SELECT NOW()").scalar()
        db.flush()
        return competitor