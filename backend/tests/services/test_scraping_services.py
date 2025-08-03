"""
Comprehensive unit tests for scraping services including web scraping,
product discovery, anti-bot handling, and data quality validation.
"""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from datetime import datetime, timedelta
import json

from app.services.scraping.brand_scraper import BrandScraper
from app.services.scraping.product_scraper import ProductScraper
from app.services.scraping.ecommerce_detector import EcommerceDetector
from app.services.scraping.data_normalizer import DataNormalizer
from app.services.scraping.proxy_manager import ProxyManager
from app.services.scraping.playwright_scraper import PlaywrightScraper
from app.services.scraping.base_scraper import BaseScraper, ScrapingError
from app.services.scraping.monitoring import ScrapingMonitor
from app.models.product import Product, ScrapingJob
from tests.factories import BrandFactory, ProductFactory, ScrapingJobFactory


class TestBrandScraper:
    """Test brand scraping functionality with comprehensive error handling."""

    @pytest.fixture
    def brand_scraper(self, mock_redis, mock_openai_client):
        with patch('app.services.scraping.brand_scraper.redis', mock_redis):
            with patch('app.services.scraping.brand_scraper.openai_client', mock_openai_client):
                return BrandScraper()

    @pytest.fixture
    def sample_brand_html(self):
        return """
        <html>
        <head>
            <title>Amazing Brand - Premium Products</title>
            <meta name="description" content="We create amazing premium products for modern consumers">
        </head>
        <body>
            <div class="header">
                <h1>Amazing Brand</h1>
                <nav>
                    <a href="/products">Products</a>
                    <a href="/about">About</a>
                </nav>
            </div>
            <main>
                <section class="hero">
                    <h2>Premium Quality, Affordable Prices</h2>
                    <p>Discover our collection of handcrafted products</p>
                </section>
                <section class="products">
                    <div class="product-grid">
                        <div class="product-card" data-product-id="123">
                            <img src="/images/product1.jpg" alt="Product 1">
                            <h3>Amazing Widget</h3>
                            <span class="price">$29.99</span>
                        </div>
                    </div>
                </section>
            </main>
        </body>
        </html>
        """

    @pytest.mark.unit
    @pytest.mark.ai
    async def test_extract_brand_info_success(self, brand_scraper, sample_brand_html):
        """Test successful brand information extraction."""
        mock_response = Mock()
        mock_response.text = sample_brand_html
        mock_response.status = 200
        
        with patch('httpx.AsyncClient.get', return_value=mock_response):
            brand_info = await brand_scraper.extract_brand_info("https://amazingbrand.com")
        
        assert brand_info is not None
        assert brand_info.get("name") is not None
        assert brand_info.get("description") is not None
        assert "products" in brand_info or "product_links" in brand_info

    @pytest.mark.unit
    async def test_extract_brand_info_invalid_url(self, brand_scraper):
        """Test brand extraction with invalid URL."""
        with pytest.raises(ScrapingError, match="Invalid URL"):
            await brand_scraper.extract_brand_info("not-a-url")

    @pytest.mark.unit
    async def test_extract_brand_info_timeout(self, brand_scraper):
        """Test brand extraction with timeout."""
        with patch('httpx.AsyncClient.get', side_effect=asyncio.TimeoutError()):
            with pytest.raises(ScrapingError, match="Request timeout"):
                await brand_scraper.extract_brand_info("https://slowsite.com")

    @pytest.mark.unit
    async def test_extract_brand_info_bot_detection(self, brand_scraper):
        """Test handling of bot detection mechanisms."""
        mock_response = Mock()
        mock_response.status = 403
        mock_response.text = "Access Denied - Bot Detection"
        
        with patch('httpx.AsyncClient.get', return_value=mock_response):
            with pytest.raises(ScrapingError, match="Bot detection"):
                await brand_scraper.extract_brand_info("https://protectedsite.com")

    @pytest.mark.unit
    async def test_detect_ecommerce_platform(self, brand_scraper, sample_brand_html):
        """Test e-commerce platform detection."""
        # Test Shopify detection
        shopify_html = sample_brand_html.replace(
            "<body>", 
            '<body><script>window.Shopify = {shop: "test-shop"};</script>'
        )
        
        platform = brand_scraper.detect_ecommerce_platform(shopify_html, "https://test.myshopify.com")
        assert platform == "shopify"
        
        # Test WooCommerce detection
        woo_html = sample_brand_html.replace(
            "<body>", 
            '<body><div class="woocommerce">'
        )
        
        platform = brand_scraper.detect_ecommerce_platform(woo_html, "https://test.com")
        assert platform == "woocommerce"

    @pytest.mark.unit
    async def test_extract_product_links(self, brand_scraper, sample_brand_html):
        """Test product link extraction."""
        product_links = brand_scraper.extract_product_links(
            sample_brand_html, 
            "https://amazingbrand.com"
        )
        
        assert len(product_links) > 0
        assert all(link.startswith("http") for link in product_links)

    @pytest.mark.unit
    async def test_cache_functionality(self, brand_scraper, mock_redis):
        """Test Redis caching functionality."""
        url = "https://cachedsite.com"
        cache_key = f"brand_scrape:{url}"
        
        # Test cache miss
        mock_redis.get.return_value = None
        mock_response = Mock()
        mock_response.text = "<html>Test</html>"
        mock_response.status = 200
        
        with patch('httpx.AsyncClient.get', return_value=mock_response):
            result = await brand_scraper.extract_brand_info(url)
        
        # Verify cache was set
        mock_redis.setex.assert_called()
        
        # Test cache hit
        cached_data = {"name": "Cached Brand", "description": "From cache"}
        mock_redis.get.return_value = json.dumps(cached_data)
        
        result = await brand_scraper.extract_brand_info(url)
        assert result == cached_data


class TestProductScraper:
    """Test product scraping with various e-commerce platforms."""

    @pytest.fixture
    def product_scraper(self, mock_redis):
        with patch('app.services.scraping.product_scraper.redis', mock_redis):
            return ProductScraper()

    @pytest.fixture
    def sample_product_html(self):
        return """
        <html>
        <head>
            <title>Amazing Widget - Premium Quality</title>
            <script type="application/ld+json">
            {
                "@type": "Product",
                "name": "Amazing Widget",
                "description": "High-quality widget for all your needs",
                "offers": {
                    "@type": "Offer",
                    "price": "29.99",
                    "priceCurrency": "USD",
                    "availability": "InStock"
                },
                "image": "/images/widget.jpg",
                "brand": {"name": "Amazing Brand"},
                "sku": "AW-001"
            }
            </script>
        </head>
        <body>
            <div class="product-page">
                <h1 class="product-title">Amazing Widget</h1>
                <div class="price">$29.99</div>
                <div class="description">High-quality widget for all your needs</div>
                <div class="availability">In Stock</div>
                <div class="reviews">
                    <span class="rating">4.5</span>
                    <span class="review-count">127 reviews</span>
                </div>
                <div class="variants">
                    <select name="color">
                        <option value="red">Red</option>
                        <option value="blue">Blue</option>
                    </select>
                </div>
            </div>
        </body>
        </html>
        """

    @pytest.mark.unit
    async def test_extract_product_info_success(self, product_scraper, sample_product_html):
        """Test successful product information extraction."""
        mock_response = Mock()
        mock_response.text = sample_product_html
        mock_response.status = 200
        
        with patch('httpx.AsyncClient.get', return_value=mock_response):
            product_info = await product_scraper.extract_product_info(
                "https://amazingbrand.com/products/widget"
            )
        
        assert product_info is not None
        assert product_info.get("name") == "Amazing Widget"
        assert product_info.get("price") == "29.99"
        assert product_info.get("currency") == "USD"
        assert product_info.get("availability") == "InStock"

    @pytest.mark.unit
    async def test_extract_json_ld_data(self, product_scraper, sample_product_html):
        """Test JSON-LD structured data extraction."""
        json_ld_data = product_scraper.extract_json_ld_data(sample_product_html)
        
        assert json_ld_data is not None
        assert json_ld_data.get("@type") == "Product"
        assert json_ld_data.get("name") == "Amazing Widget"
        assert json_ld_data.get("offers", {}).get("price") == "29.99"

    @pytest.mark.unit
    async def test_extract_microdata(self, product_scraper):
        """Test microdata extraction."""
        microdata_html = """
        <div itemscope itemtype="http://schema.org/Product">
            <h1 itemprop="name">Test Product</h1>
            <span itemprop="price">19.99</span>
            <span itemprop="priceCurrency">USD</span>
        </div>
        """
        
        microdata = product_scraper.extract_microdata(microdata_html)
        assert microdata.get("name") == "Test Product"
        assert microdata.get("price") == "19.99"

    @pytest.mark.unit
    async def test_fallback_extraction(self, product_scraper):
        """Test fallback extraction when structured data is unavailable."""
        basic_html = """
        <html>
        <body>
            <h1 class="product-title">Basic Product</h1>
            <span class="price">$15.99</span>
            <div class="description">Simple product description</div>
        </body>
        </html>
        """
        
        mock_response = Mock()
        mock_response.text = basic_html
        mock_response.status = 200
        
        with patch('httpx.AsyncClient.get', return_value=mock_response):
            product_info = await product_scraper.extract_product_info(
                "https://basicstore.com/product"
            )
        
        assert product_info is not None
        assert "Basic Product" in str(product_info.get("name", ""))

    @pytest.mark.unit
    async def test_product_variants_extraction(self, product_scraper, sample_product_html):
        """Test product variant extraction."""
        mock_response = Mock()
        mock_response.text = sample_product_html
        mock_response.status = 200
        
        with patch('httpx.AsyncClient.get', return_value=mock_response):
            product_info = await product_scraper.extract_product_info(
                "https://amazingbrand.com/products/widget"
            )
        
        variants = product_info.get("variants", [])
        assert len(variants) > 0
        color_variant = next((v for v in variants if v.get("name") == "color"), None)
        assert color_variant is not None
        assert "red" in color_variant.get("options", [])
        assert "blue" in color_variant.get("options", [])

    @pytest.mark.unit
    async def test_price_history_tracking(self, product_scraper, db_session):
        """Test price history tracking functionality."""
        product = ProductFactory.create()
        db_session.add(product)
        db_session.commit()
        
        # Simulate price change
        new_price_data = {
            "price": 24.99,
            "original_price": 29.99,
            "currency": "USD",
            "availability": "InStock"
        }
        
        await product_scraper.track_price_change(product.id, new_price_data, db_session)
        
        # Verify price history was created
        from app.models.product import ProductPriceHistory
        price_history = db_session.query(ProductPriceHistory).filter_by(
            product_id=product.id
        ).first()
        
        assert price_history is not None
        assert price_history.price == 24.99


class TestEcommerceDetector:
    """Test e-commerce platform detection and configuration."""

    @pytest.fixture
    def ecommerce_detector(self):
        return EcommerceDetector()

    @pytest.mark.unit
    def test_detect_shopify(self, ecommerce_detector):
        """Test Shopify platform detection."""
        shopify_html = """
        <html>
        <head>
            <script>window.Shopify = {shop: "test-shop"};</script>
        </head>
        <body>
            <div class="shopify-section">Content</div>
        </body>
        </html>
        """
        
        platform = ecommerce_detector.detect_platform(
            shopify_html, 
            "https://test.myshopify.com"
        )
        
        assert platform.name == "shopify"
        assert platform.confidence > 0.8
        assert "myshopify.com" in platform.indicators

    @pytest.mark.unit
    def test_detect_woocommerce(self, ecommerce_detector):
        """Test WooCommerce platform detection."""
        woo_html = """
        <html>
        <head>
            <link rel="stylesheet" href="/wp-content/plugins/woocommerce/assets/css/woocommerce.css">
        </head>
        <body class="woocommerce-page">
            <div class="woocommerce">
                <div class="products">Content</div>
            </div>
        </body>
        </html>
        """
        
        platform = ecommerce_detector.detect_platform(woo_html, "https://example.com")
        
        assert platform.name == "woocommerce"
        assert platform.confidence > 0.7

    @pytest.mark.unit
    def test_detect_bigcommerce(self, ecommerce_detector):
        """Test BigCommerce platform detection."""
        bc_html = """
        <html>
        <head>
            <meta name="generator" content="BigCommerce">
        </head>
        <body>
            <script>window.BCData = {csrf_token: "test"};</script>
        </body>
        </html>
        """
        
        platform = ecommerce_detector.detect_platform(bc_html, "https://store.com")
        
        assert platform.name == "bigcommerce"
        assert platform.confidence > 0.7

    @pytest.mark.unit
    def test_detect_magento(self, ecommerce_detector):
        """Test Magento platform detection."""
        magento_html = """
        <html>
        <head>
            <script src="/static/version123/frontend/Magento/luma/en_US/mage/requirejs/mixins.js"></script>
        </head>
        <body class="cms-index-index">
            <div class="page-wrapper">Content</div>
        </body>
        </html>
        """
        
        platform = ecommerce_detector.detect_platform(magento_html, "https://store.com")
        
        assert platform.name == "magento"
        assert platform.confidence > 0.6

    @pytest.mark.unit
    def test_get_scraping_config(self, ecommerce_detector):
        """Test getting platform-specific scraping configuration."""
        config = ecommerce_detector.get_scraping_config("shopify")
        
        assert config is not None
        assert "selectors" in config
        assert "product_title" in config["selectors"]
        assert "product_price" in config["selectors"]
        assert "rate_limit" in config
        assert "headers" in config

    @pytest.mark.unit
    def test_unknown_platform_detection(self, ecommerce_detector):
        """Test handling of unknown platforms."""
        basic_html = """
        <html>
        <body>
            <h1>Basic Website</h1>
            <p>No e-commerce indicators</p>
        </body>
        </html>
        """
        
        platform = ecommerce_detector.detect_platform(basic_html, "https://basic.com")
        
        assert platform.name == "unknown"
        assert platform.confidence < 0.5


class TestDataNormalizer:
    """Test data normalization and quality validation."""

    @pytest.fixture
    def data_normalizer(self):
        return DataNormalizer()

    @pytest.mark.unit
    def test_normalize_price(self, data_normalizer):
        """Test price normalization."""
        test_cases = [
            ("$29.99", 29.99),
            ("£25.50", 25.50),
            ("€35,99", 35.99),
            ("¥1,000", 1000.0),
            ("29.99 USD", 29.99),
            ("$1,299.00", 1299.0),
            ("Free", 0.0),
            ("Contact for price", None),
        ]
        
        for input_price, expected in test_cases:
            result = data_normalizer.normalize_price(input_price)
            if expected is None:
                assert result is None
            else:
                assert abs(result - expected) < 0.01

    @pytest.mark.unit
    def test_normalize_currency(self, data_normalizer):
        """Test currency code extraction and normalization."""
        test_cases = [
            ("$29.99", "USD"),
            ("£25.50", "GBP"),
            ("€35.99", "EUR"),
            ("¥1,000", "JPY"),
            ("29.99 CAD", "CAD"),
            ("AUD 45.00", "AUD"),
        ]
        
        for input_text, expected in test_cases:
            result = data_normalizer.extract_currency(input_text)
            assert result == expected

    @pytest.mark.unit
    def test_normalize_availability(self, data_normalizer):
        """Test availability status normalization."""
        test_cases = [
            ("In Stock", "in_stock"),
            ("Available", "in_stock"),
            ("Out of Stock", "out_of_stock"),
            ("Sold Out", "out_of_stock"),
            ("Pre-order", "pre_order"),
            ("Coming Soon", "pre_order"),
            ("Limited Stock", "limited"),
            ("Only 2 left", "limited"),
        ]
        
        for input_availability, expected in test_cases:
            result = data_normalizer.normalize_availability(input_availability)
            assert result == expected

    @pytest.mark.unit
    def test_validate_product_data(self, data_normalizer):
        """Test product data validation."""
        valid_product = {
            "name": "Test Product",
            "price": 29.99,
            "currency": "USD",
            "availability": "in_stock",
            "description": "A test product",
            "images": [{"url": "https://example.com/image.jpg"}]
        }
        
        validation_result = data_normalizer.validate_product_data(valid_product)
        assert validation_result.is_valid is True
        assert len(validation_result.errors) == 0
        assert validation_result.quality_score > 0.8

    @pytest.mark.unit
    def test_validate_incomplete_product_data(self, data_normalizer):
        """Test validation of incomplete product data."""
        incomplete_product = {
            "name": "",  # Missing name
            "price": "invalid",  # Invalid price
            # Missing currency, availability
        }
        
        validation_result = data_normalizer.validate_product_data(incomplete_product)
        assert validation_result.is_valid is False
        assert len(validation_result.errors) > 0
        assert validation_result.quality_score < 0.5

    @pytest.mark.unit
    def test_clean_text_data(self, data_normalizer):
        """Test text data cleaning."""
        dirty_text = "  \n\t Product   Name\r\n  with   extra    spaces  \t\n  "
        clean_text = data_normalizer.clean_text(dirty_text)
        assert clean_text == "Product Name with extra spaces"

    @pytest.mark.unit
    def test_extract_features(self, data_normalizer):
        """Test feature extraction from product descriptions."""
        description = """
        Premium quality widget made from stainless steel.
        Features: Waterproof, Durable, Lightweight.
        Dimensions: 10x5x2 inches. Weight: 2 lbs.
        """
        
        features = data_normalizer.extract_features(description)
        assert "waterproof" in [f.lower() for f in features]
        assert "durable" in [f.lower() for f in features]
        assert "lightweight" in [f.lower() for f in features]


class TestProxyManager:
    """Test proxy management and rotation."""

    @pytest.fixture
    def proxy_manager(self, mock_redis):
        with patch('app.services.scraping.proxy_manager.redis', mock_redis):
            return ProxyManager()

    @pytest.mark.unit
    async def test_get_random_proxy(self, proxy_manager, mock_redis):
        """Test getting a random proxy."""
        mock_proxies = [
            {"host": "proxy1.com", "port": 8080, "username": "user1", "password": "pass1"},
            {"host": "proxy2.com", "port": 8080, "username": "user2", "password": "pass2"},
        ]
        
        mock_redis.lrange.return_value = [json.dumps(p) for p in mock_proxies]
        
        proxy = await proxy_manager.get_random_proxy()
        assert proxy is not None
        assert proxy["host"] in ["proxy1.com", "proxy2.com"]

    @pytest.mark.unit
    async def test_proxy_rotation(self, proxy_manager, mock_redis):
        """Test proxy rotation functionality."""
        mock_proxies = [
            {"host": "proxy1.com", "port": 8080},
            {"host": "proxy2.com", "port": 8080},
            {"host": "proxy3.com", "port": 8080},
        ]
        
        mock_redis.lrange.return_value = [json.dumps(p) for p in mock_proxies]
        
        # Get multiple proxies and ensure rotation
        used_proxies = set()
        for _ in range(6):  # More than available proxies
            proxy = await proxy_manager.get_random_proxy()
            used_proxies.add(proxy["host"])
        
        assert len(used_proxies) == 3  # All proxies were used

    @pytest.mark.unit
    async def test_proxy_health_check(self, proxy_manager):
        """Test proxy health checking."""
        proxy = {"host": "proxy1.com", "port": 8080}
        
        # Mock successful health check
        mock_response = Mock()
        mock_response.status_code = 200
        
        with patch('httpx.get', return_value=mock_response):
            is_healthy = await proxy_manager.check_proxy_health(proxy)
            assert is_healthy is True
        
        # Mock failed health check
        with patch('httpx.get', side_effect=Exception("Connection failed")):
            is_healthy = await proxy_manager.check_proxy_health(proxy)
            assert is_healthy is False

    @pytest.mark.unit
    async def test_mark_proxy_failed(self, proxy_manager, mock_redis):
        """Test marking proxy as failed."""
        proxy = {"host": "failed-proxy.com", "port": 8080}
        
        await proxy_manager.mark_proxy_failed(proxy)
        
        # Verify Redis operations
        mock_redis.zadd.assert_called()  # Failed proxy tracking
        mock_redis.expire.assert_called()  # TTL for failed status


class TestPlaywrightScraper:
    """Test Playwright-based scraping for JavaScript-heavy sites."""

    @pytest.fixture
    def playwright_scraper(self):
        return PlaywrightScraper()

    @pytest.mark.unit
    async def test_scrape_with_javascript(self, playwright_scraper):
        """Test scraping sites that require JavaScript execution."""
        mock_page = AsyncMock()
        mock_page.goto = AsyncMock()
        mock_page.wait_for_load_state = AsyncMock()
        mock_page.content = AsyncMock(return_value="<html>Rendered content</html>")
        
        mock_browser = AsyncMock()
        mock_browser.new_page = AsyncMock(return_value=mock_page)
        
        with patch('playwright.async_api.async_playwright') as mock_playwright:
            mock_playwright.return_value.__aenter__.return_value.chromium.launch = AsyncMock(return_value=mock_browser)
            
            content = await playwright_scraper.scrape_url("https://spa-site.com")
            
            assert content == "<html>Rendered content</html>"
            mock_page.goto.assert_called_once_with("https://spa-site.com")

    @pytest.mark.unit
    async def test_handle_popup_blocking(self, playwright_scraper):
        """Test handling of popups and modals."""
        mock_page = AsyncMock()
        mock_page.goto = AsyncMock()
        mock_page.wait_for_load_state = AsyncMock()
        mock_page.content = AsyncMock(return_value="<html>Content</html>")
        
        # Mock popup detection and handling
        mock_page.query_selector = AsyncMock(return_value=Mock())  # Popup found
        mock_page.click = AsyncMock()  # Close popup
        
        mock_browser = AsyncMock()
        mock_browser.new_page = AsyncMock(return_value=mock_page)
        
        with patch('playwright.async_api.async_playwright') as mock_playwright:
            mock_playwright.return_value.__aenter__.return_value.chromium.launch = AsyncMock(return_value=mock_browser)
            
            content = await playwright_scraper.scrape_url("https://popup-site.com")
            
            # Verify popup was handled
            mock_page.click.assert_called()

    @pytest.mark.unit
    async def test_stealth_mode(self, playwright_scraper):
        """Test stealth mode configuration to avoid detection."""
        mock_context = AsyncMock()
        mock_context.new_page = AsyncMock()
        
        mock_browser = AsyncMock()
        mock_browser.new_context = AsyncMock(return_value=mock_context)
        
        with patch('playwright.async_api.async_playwright') as mock_playwright:
            mock_playwright.return_value.__aenter__.return_value.chromium.launch = AsyncMock(return_value=mock_browser)
            
            await playwright_scraper.setup_stealth_mode()
            
            # Verify stealth configuration
            mock_browser.new_context.assert_called_with(
                user_agent=playwright_scraper.get_random_user_agent(),
                viewport={"width": 1920, "height": 1080},
                extra_http_headers={"Accept-Language": "en-US,en;q=0.9"}
            )


class TestScrapingMonitor:
    """Test scraping monitoring and performance tracking."""

    @pytest.fixture
    def scraping_monitor(self, mock_redis):
        with patch('app.services.scraping.monitoring.redis', mock_redis):
            return ScrapingMonitor()

    @pytest.mark.unit
    async def test_track_scraping_session(self, scraping_monitor, mock_redis, db_session):
        """Test scraping session tracking."""
        job = ScrapingJobFactory.create()
        db_session.add(job)
        db_session.commit()
        
        session_data = {
            "url": "https://test.com",
            "success": True,
            "response_time": 1.5,
            "data_quality": 0.85
        }
        
        await scraping_monitor.track_session(job.id, session_data)
        
        # Verify metrics were recorded
        mock_redis.zadd.assert_called()  # Performance metrics
        mock_redis.incr.assert_called()  # Success counters

    @pytest.mark.unit
    async def test_detect_rate_limiting(self, scraping_monitor):
        """Test rate limiting detection."""
        # Simulate rate limiting response
        response_data = {
            "status_code": 429,
            "headers": {"Retry-After": "60"},
            "response_time": 0.1
        }
        
        is_rate_limited = await scraping_monitor.detect_rate_limiting(response_data)
        assert is_rate_limited is True
        
        # Normal response
        normal_response = {
            "status_code": 200,
            "headers": {},
            "response_time": 1.0
        }
        
        is_rate_limited = await scraping_monitor.detect_rate_limiting(normal_response)
        assert is_rate_limited is False

    @pytest.mark.unit
    async def test_bot_detection_analysis(self, scraping_monitor):
        """Test bot detection analysis."""
        # Simulate bot detection response
        bot_response = {
            "status_code": 403,
            "content": "Access Denied - Bot Detection",
            "headers": {"Server": "Cloudflare"}
        }
        
        is_bot_detected = await scraping_monitor.analyze_bot_detection(bot_response)
        assert is_bot_detected is True
        
        # Normal response
        normal_response = {
            "status_code": 200,
            "content": "<html>Normal content</html>",
            "headers": {"Server": "nginx"}
        }
        
        is_bot_detected = await scraping_monitor.analyze_bot_detection(normal_response)
        assert is_bot_detected is False

    @pytest.mark.unit
    async def test_performance_metrics_calculation(self, scraping_monitor, mock_redis):
        """Test performance metrics calculation."""
        # Mock performance data
        mock_redis.zrange.return_value = [
            json.dumps({"response_time": 1.0, "success": True}),
            json.dumps({"response_time": 1.5, "success": True}),
            json.dumps({"response_time": 2.0, "success": False}),
        ]
        
        metrics = await scraping_monitor.calculate_performance_metrics("test-domain")
        
        assert metrics["average_response_time"] == 1.5
        assert metrics["success_rate"] == 2/3
        assert metrics["total_requests"] == 3

    @pytest.mark.unit
    async def test_alert_triggering(self, scraping_monitor):
        """Test alert triggering based on thresholds."""
        # High error rate should trigger alert
        metrics = {
            "success_rate": 0.3,  # Below threshold
            "average_response_time": 5.0,  # Above threshold
            "bot_detection_rate": 0.8  # Above threshold
        }
        
        alerts = await scraping_monitor.check_alert_conditions(metrics)
        
        assert len(alerts) > 0
        assert any("success_rate" in alert["type"] for alert in alerts)
        assert any("response_time" in alert["type"] for alert in alerts)
        assert any("bot_detection" in alert["type"] for alert in alerts)


class TestBaseScraper:
    """Test base scraper functionality and error handling."""

    @pytest.fixture
    def base_scraper(self):
        return BaseScraper()

    @pytest.mark.unit
    async def test_request_with_retry(self, base_scraper):
        """Test HTTP request with retry logic."""
        # Mock failing then succeeding
        mock_responses = [
            Exception("Connection failed"),
            Exception("Timeout"),
            Mock(status_code=200, text="Success")
        ]
        
        with patch('httpx.AsyncClient.get', side_effect=mock_responses):
            response = await base_scraper.request_with_retry("https://test.com")
            assert response.text == "Success"

    @pytest.mark.unit
    async def test_request_retry_exhausted(self, base_scraper):
        """Test request failure after retry exhaustion."""
        with patch('httpx.AsyncClient.get', side_effect=Exception("Always fails")):
            with pytest.raises(ScrapingError, match="Max retries exceeded"):
                await base_scraper.request_with_retry("https://test.com", max_retries=2)

    @pytest.mark.unit
    def test_clean_html(self, base_scraper):
        """Test HTML cleaning and sanitization."""
        dirty_html = """
        <html>
        <head>
            <script>alert('xss')</script>
            <style>body {color: red;}</style>
        </head>
        <body>
            <h1>Title</h1>
            <p>Content</p>
            <script>malicious_code()</script>
        </body>
        </html>
        """
        
        clean_html = base_scraper.clean_html(dirty_html)
        
        assert "<script>" not in clean_html
        assert "alert('xss')" not in clean_html
        assert "malicious_code()" not in clean_html
        assert "<h1>Title</h1>" in clean_html
        assert "<p>Content</p>" in clean_html

    @pytest.mark.unit
    def test_extract_urls(self, base_scraper):
        """Test URL extraction from HTML."""
        html = """
        <html>
        <body>
            <a href="https://example.com/page1">Link 1</a>
            <a href="/relative/page2">Link 2</a>
            <a href="mailto:test@example.com">Email</a>
            <a href="javascript:void(0)">JS Link</a>
        </body>
        </html>
        """
        
        urls = base_scraper.extract_urls(html, "https://example.com")
        
        assert "https://example.com/page1" in urls
        assert "https://example.com/relative/page2" in urls
        assert "mailto:test@example.com" not in urls
        assert "javascript:void(0)" not in urls

    @pytest.mark.unit
    def test_validate_url(self, base_scraper):
        """Test URL validation."""
        valid_urls = [
            "https://example.com",
            "http://test.org/path",
            "https://subdomain.example.com/page?param=value"
        ]
        
        invalid_urls = [
            "not-a-url",
            "ftp://example.com",
            "javascript:alert('xss')",
            "mailto:test@example.com"
        ]
        
        for url in valid_urls:
            assert base_scraper.validate_url(url) is True
        
        for url in invalid_urls:
            assert base_scraper.validate_url(url) is False

    @pytest.mark.unit
    def test_calculate_data_quality_score(self, base_scraper):
        """Test data quality score calculation."""
        high_quality_data = {
            "name": "Complete Product Name",
            "price": 29.99,
            "currency": "USD",
            "description": "Detailed product description with multiple sentences.",
            "images": [{"url": "https://example.com/img1.jpg"}],
            "availability": "in_stock",
            "brand": "Brand Name",
            "sku": "SKU-123"
        }
        
        low_quality_data = {
            "name": "",  # Missing
            "price": None,  # Missing
            "description": "Short",  # Too short
            "images": [],  # Empty
        }
        
        high_score = base_scraper.calculate_data_quality_score(high_quality_data)
        low_score = base_scraper.calculate_data_quality_score(low_quality_data)
        
        assert high_score > 0.8
        assert low_score < 0.5
        assert high_score > low_score