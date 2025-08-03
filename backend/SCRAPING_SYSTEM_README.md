# Comprehensive Web Scraping System for ViralOS

This document provides an overview of the comprehensive web scraping system implemented for brand and product discovery in ViralOS.

## Overview

The scraping system provides robust web scraping capabilities for:
- **Brand Discovery**: Complete brand analysis including visual identity, voice, messaging, and competitor analysis
- **Product Catalog Scraping**: Comprehensive product data extraction from e-commerce sites
- **Competitor Analysis**: Automated discovery and monitoring of competitor brands
- **Price Monitoring**: Real-time price tracking and history for products
- **E-commerce Platform Detection**: Automatic detection and optimization for major platforms

## Architecture

### Core Components

1. **Base Scraper Framework** (`base_scraper.py`)
   - Abstract base class for all scrapers
   - Common functionality: retry logic, rate limiting, error handling
   - Support for both BeautifulSoup and selectolax parsers

2. **Platform-Specific Scrapers**
   - **ProductScraper**: Specialized for e-commerce product extraction
   - **BrandScraper**: Comprehensive brand analysis and data extraction
   - **PlaywrightScraper**: JavaScript-heavy sites using Playwright browser automation

3. **E-commerce Platform Detection** (`ecommerce_detector.py`)
   - Auto-detection of Shopify, WooCommerce, BigCommerce, Magento, etc.
   - Platform-specific selector optimization
   - Product vs. listing page classification

4. **Data Processing Pipeline**
   - **DataNormalizer**: Cleans and standardizes extracted data
   - **Quality Scoring**: Assigns quality scores to extracted data
   - **Tag Generation**: Automatic tagging based on content analysis

5. **Anti-Detection System** (`proxy_manager.py`)
   - Proxy rotation and health monitoring
   - User-agent rotation and header randomization
   - Bot detection identification and evasion strategies
   - Intelligent delay calculation

6. **Monitoring & Recovery** (`monitoring.py`)
   - Real-time performance monitoring
   - Automatic error recovery strategies
   - Health status reporting and alerting
   - Detailed performance analytics

## Features

### Brand Analysis
- **Visual Identity Extraction**: Colors, fonts, logo detection
- **Voice & Tone Analysis**: AI-powered brand voice characterization
- **Messaging Analysis**: Key value propositions, CTAs, content themes
- **Target Audience Identification**: Demographics and psychographics
- **Industry Classification**: Automatic industry categorization
- **Social Media Integration**: Social link discovery and analysis

### Product Data Extraction
- **Comprehensive Product Info**: Name, description, pricing, availability
- **Variant Detection**: Colors, sizes, materials, and other options
- **Image Collection**: Product gallery with type classification
- **Review & Rating Extraction**: Customer feedback and social proof
- **Structured Data Parsing**: JSON-LD, microdata, and schema.org
- **Trust Signal Detection**: Security badges, certifications, guarantees

### E-commerce Platform Support
- **Shopify**: Product API integration, variant handling, collection detection
- **WooCommerce**: WordPress integration, custom field extraction
- **BigCommerce**: GraphQL support, advanced catalog features
- **Magento**: Multi-store support, complex attribute systems
- **Generic Sites**: Fallback selectors for custom e-commerce implementations

### Anti-Bot Measures
- **Proxy Rotation**: Automatic proxy switching with health monitoring
- **User-Agent Diversity**: Realistic browser fingerprinting
- **Rate Limiting**: Intelligent request spacing and burst prevention
- **CAPTCHA Detection**: Identification and handling strategies
- **Session Management**: Cookie and session state management

## Database Schema

### Core Tables

1. **Products**: Complete product information with normalized data
2. **ProductPriceHistory**: Historical pricing data for trend analysis
3. **ProductCompetitors**: Product-to-product competition mapping
4. **ScrapingJobs**: Job tracking and performance metrics
5. **ScrapingSession**: Individual session tracking and debugging
6. **CompetitorBrands**: Discovered competitor information

### Key Fields

```sql
-- Products table
CREATE TABLE products (
    id SERIAL PRIMARY KEY,
    brand_id INTEGER REFERENCES brands(id),
    name VARCHAR NOT NULL,
    description TEXT,
    price DECIMAL,
    currency VARCHAR(3) DEFAULT 'USD',
    availability VARCHAR,
    source_url VARCHAR NOT NULL,
    platform_type VARCHAR,
    images JSON,
    variants JSON,
    attributes JSON,
    data_quality_score DECIMAL,
    -- ... additional fields
);

-- Performance indexes
CREATE INDEX idx_product_brand_category ON products(brand_id, category);
CREATE INDEX idx_product_price_range ON products(price, currency);
CREATE INDEX idx_product_availability ON products(availability, is_active);
```

## API Endpoints

### Scraping Operations

```http
# Enhanced brand scraping
POST /api/v1/scraping/brand
{
    "url": "https://example.com",
    "use_playwright": false,
    "use_proxies": false,
    "max_retries": 3,
    "timeout": 30
}

# Product catalog scraping
POST /api/v1/scraping/products
{
    "brand_id": 123,
    "urls": ["https://shop.example.com/products"],
    "use_playwright": false,
    "max_products_per_page": 20
}

# Competitor discovery
POST /api/v1/scraping/competitors
{
    "brand_id": 123,
    "search_queries": ["eco-friendly clothing"],
    "max_competitors": 10
}

# Price monitoring
POST /api/v1/scraping/price-monitoring
{
    "product_ids": [456, 789]
}
```

### Monitoring & Analytics

```http
# Get scraping job status
GET /api/v1/scraping/jobs/{job_id}

# System health check
GET /api/v1/scraping/health

# Domain-specific metrics
GET /api/v1/scraping/metrics/domain/{domain}

# Job performance analysis
GET /api/v1/scraping/jobs/{job_id}/analysis
```

## Usage Examples

### Basic Brand Scraping

```python
from app.services.scraping import BrandScraper

async with BrandScraper() as scraper:
    result = await scraper.scrape("https://example.com")
    
    if result.success:
        brand_data = result.data["brand"]
        print(f"Brand: {brand_data['name']}")
        print(f"Industry: {brand_data['industry']}")
        print(f"Colors: {brand_data['colors']}")
```

### Product Catalog Scraping

```python
from app.services.scraping import ProductScraper

async with ProductScraper() as scraper:
    result = await scraper.scrape("https://shop.example.com/products/item")
    
    if result.success and result.data.get("product"):
        product = result.data["product"]
        print(f"Product: {product['name']}")
        print(f"Price: {product['price']} {product['currency']}")
        print(f"Quality Score: {product['data_quality_score']}")
```

### JavaScript-Heavy Sites

```python
from app.services.scraping import PlaywrightScraper

async with PlaywrightScraper(use_playwright=True) as scraper:
    result = await scraper.scrape("https://spa-ecommerce.com")
    
    # Handles dynamic content loading, popups, etc.
    if result.success:
        print(f"Extracted data: {result.data}")
```

## Configuration

### Environment Variables

```bash
# Basic scraping settings
SCRAPING_TIMEOUT=30
SCRAPING_MAX_RETRIES=3
SCRAPING_CONCURRENT_REQUESTS=8

# Playwright settings
PLAYWRIGHT_HEADLESS=true
PLAYWRIGHT_TIMEOUT=30000

# Anti-detection
SCRAPING_USE_PROXIES=false
SCRAPING_RANDOM_USER_AGENTS=true

# Data quality
MIN_DATA_QUALITY_SCORE=0.6
MAX_PRODUCT_NAME_LENGTH=500
```

### Proxy Configuration

```python
# Configure proxy list
proxy_configs = [
    {
        "host": "proxy1.example.com",
        "port": 8080,
        "username": "user",
        "password": "pass",
        "protocol": "http"
    }
]

# Initialize proxy manager
proxy_manager = ProxyManager(proxy_configs)
```

## Monitoring & Alerts

### Health Monitoring

The system continuously monitors:
- Success/failure rates per domain
- Average response times
- Bot detection incidents
- Proxy health and rotation
- Data quality scores

### Alert Conditions

Alerts are triggered for:
- Failure rate > 50% over 10+ requests
- Average response time > 30 seconds
- Bot detection rate > 30%
- Multiple proxy failures (>10)

### Performance Analytics

```python
# Get domain performance
metrics = scraping_monitor.get_domain_metrics("shopify.com")
print(f"Success rate: {metrics.success_rate:.1%}")

# Get job analysis
analysis = await scraping_monitor.analyze_job_performance(job_id)
print(f"Recommendations: {analysis['recommendations']}")
```

## Error Handling & Recovery

### Automatic Recovery Strategies

1. **Rate Limiting**: Increase delays, rotate proxies
2. **Bot Detection**: Switch to Playwright, change fingerprints
3. **Network Errors**: Retry with exponential backoff
4. **Proxy Failures**: Rotate to healthy proxies
5. **Parsing Errors**: Use fallback selectors, different parsers

### Manual Intervention

```python
# Retry failed job
POST /api/v1/scraping/jobs/{job_id}/retry

# Get recovery strategy
strategy = await monitor.get_recovery_strategy("bot_detection", error_data)
```

## Performance Optimization

### Best Practices

1. **Respect Rate Limits**: Use appropriate delays between requests
2. **Optimize Selectors**: Use efficient CSS selectors and XPath
3. **Cache Strategy**: Cache static resources and repeated data
4. **Batch Processing**: Group similar operations together
5. **Resource Management**: Properly close connections and clean up

### Scaling Considerations

- **Horizontal Scaling**: Distribute scraping across multiple workers
- **Database Optimization**: Use proper indexing and partitioning
- **Proxy Pool Management**: Maintain healthy proxy rotations
- **Memory Management**: Process large datasets in chunks

## Security & Compliance

### Ethical Scraping

- Respect robots.txt files (configurable)
- Implement reasonable rate limiting
- Honor website terms of service
- Avoid overwhelming small websites

### Data Privacy

- Don't collect personal information
- Anonymize extracted data when possible
- Implement data retention policies
- Comply with GDPR and similar regulations

## Troubleshooting

### Common Issues

1. **High Failure Rates**
   - Check if sites have implemented new anti-bot measures
   - Verify proxy health and rotation
   - Update selectors for site changes

2. **Slow Performance**
   - Optimize database queries and indexes
   - Reduce concurrent request limits
   - Check proxy response times

3. **Data Quality Issues**
   - Review and update extraction selectors
   - Implement additional validation rules
   - Check for site structure changes

### Debugging Tools

```python
# Enable detailed logging
import logging
logging.getLogger("scraping").setLevel(logging.DEBUG)

# Get session logs
logs = scraping_logger.get_session_logs(session_id)

# Analyze job performance
analysis = await scraping_monitor.analyze_job_performance(job_id)
```

## Future Enhancements

### Planned Features

1. **ML-Powered Extraction**: Use machine learning for better data extraction
2. **Real-time Monitoring**: Live dashboards for scraping operations
3. **API Integration**: Direct integration with e-commerce APIs
4. **Advanced Analytics**: Trend analysis and predictive insights
5. **CAPTCHA Solving**: Integration with CAPTCHA solving services

### Integration Opportunities

- **Social Media Scraping**: Instagram, TikTok, Pinterest integration
- **Review Aggregation**: Multi-platform review collection
- **SEO Analysis**: Technical SEO and content analysis
- **Market Intelligence**: Pricing and trend analysis tools

## Support & Maintenance

### Regular Maintenance Tasks

1. **Selector Updates**: Monitor for site changes and update selectors
2. **Proxy Health**: Maintain and rotate proxy pools
3. **Performance Optimization**: Regular performance reviews and optimizations
4. **Security Updates**: Keep dependencies and security measures current

### Monitoring Checklist

- [ ] Daily health status review
- [ ] Weekly performance analysis
- [ ] Monthly selector accuracy audit
- [ ] Quarterly security review

---

This scraping system provides a robust foundation for comprehensive brand and product discovery, with built-in monitoring, error recovery, and scaling capabilities. The modular architecture allows for easy extension and customization based on specific requirements.