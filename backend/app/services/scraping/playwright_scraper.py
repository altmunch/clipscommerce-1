"""
Playwright-based scraper for JavaScript-heavy sites and dynamic content.
"""

import asyncio
import time
from typing import Any, Dict, List, Optional
import logging

from playwright.async_api import async_playwright, Page, Browser, BrowserContext
from bs4 import BeautifulSoup
from selectolax.parser import HTMLParser

from .base_scraper import BaseScraper, ScrapingResult
from .ecommerce_detector import EcommerceDetector
from .data_normalizer import DataNormalizer

logger = logging.getLogger(__name__)


class PlaywrightScraper(BaseScraper):
    """Playwright-based scraper for JavaScript-heavy sites"""
    
    def __init__(self, 
                 headless: bool = True,
                 browser_type: str = "chromium",
                 viewport_size: Dict[str, int] = None,
                 wait_for_selector: str = None,
                 wait_timeout: int = 30000,
                 **kwargs):
        
        super().__init__(**kwargs)
        
        self.headless = headless
        self.browser_type = browser_type
        self.viewport_size = viewport_size or {"width": 1920, "height": 1080}
        self.wait_for_selector = wait_for_selector
        self.wait_timeout = wait_timeout
        
        self.playwright = None
        self.browser = None
        self.context = None
        
        self.ecommerce_detector = EcommerceDetector()
        self.data_normalizer = DataNormalizer()
    
    async def __aenter__(self):
        """Initialize Playwright browser"""
        self.playwright = await async_playwright().start()
        
        # Launch browser with secure configuration
        browser_kwargs = {
            "headless": self.headless,
            "args": [
                "--disable-dev-shm-usage",  # Helps with Docker/container environments
                "--disable-blink-features=AutomationControlled",  # Reduce detection
                "--disable-features=VizDisplayCompositor",  # Performance optimization
                "--no-first-run",  # Skip first run wizard
                "--disable-default-apps",  # Don't load default apps
                # Security: Removed --no-sandbox and --disable-web-security
                # These flags create serious security vulnerabilities
            ]
        }
        
        if self.browser_type == "chromium":
            self.browser = await self.playwright.chromium.launch(**browser_kwargs)
        elif self.browser_type == "firefox":
            self.browser = await self.playwright.firefox.launch(**browser_kwargs)
        else:
            self.browser = await self.playwright.webkit.launch(**browser_kwargs)
        
        # Create context with secure settings
        self.context = await self.browser.new_context(
            viewport=self.viewport_size,
            user_agent=self.get_random_user_agent(),
            java_script_enabled=True,
            accept_downloads=False,
            ignore_https_errors=False,  # Security: Validate HTTPS certificates
            extra_http_headers={
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                "Accept-Language": "en-US,en;q=0.5",
                "Accept-Encoding": "gzip, deflate",
                "DNT": "1",
                "Connection": "keep-alive",
                "Upgrade-Insecure-Requests": "1",
                "Sec-Fetch-Dest": "document",
                "Sec-Fetch-Mode": "navigate",
                "Sec-Fetch-Site": "none",
            }
        )
        
        # Add stealth scripts to avoid detection
        await self.context.add_init_script("""
            // Remove webdriver property
            Object.defineProperty(navigator, 'webdriver', {
                get: () => undefined,
            });
            
            // Mock chrome runtime
            window.chrome = {
                runtime: {},
            };
            
            // Mock permissions
            const originalQuery = window.navigator.permissions.query;
            window.navigator.permissions.query = (parameters) => (
                parameters.name === 'notifications' ?
                    Promise.resolve({ state: Notification.permission }) :
                    originalQuery(parameters)
            );
            
            // Mock plugins
            Object.defineProperty(navigator, 'plugins', {
                get: () => [1, 2, 3, 4, 5],
            });
            
            // Mock languages
            Object.defineProperty(navigator, 'languages', {
                get: () => ['en-US', 'en'],
            });
        """)
        
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Clean up Playwright resources"""
        if self.context:
            await self.context.close()
        if self.browser:
            await self.browser.close()
        if self.playwright:
            await self.playwright.stop()
    
    async def parse_content(self, soup: BeautifulSoup, tree: HTMLParser, url: str) -> Dict[str, Any]:
        """Parse content from HTML - will be called after page is scraped"""
        
        # Detect e-commerce platform
        platform_info = self.ecommerce_detector.detect_platform(soup, url)
        
        # Check if this is a product page
        product_check = self.ecommerce_detector.is_product_page(soup, url)
        
        data = {
            "platform": platform_info,
            "is_product_page": product_check["is_product"],
            "confidence": product_check["confidence"],
            "signals": product_check["signals"]
        }
        
        if product_check["is_product"]:
            # Extract product data using specialized scraper logic
            from .product_scraper import ProductScraper
            product_scraper = ProductScraper()
            
            product_data = await product_scraper.extract_product_data(
                soup, tree, url, platform_info
            )
            data["product"] = product_data
            data["type"] = "product"
        else:
            # Extract general content
            data.update({
                "type": "general",
                "title": soup.title.string if soup.title else "",
                "text_content": self.extract_text_content(soup),
                "metadata": self.extract_metadata(soup),
                "links": self.extract_links(soup, url),
                "images": self.extract_images(soup, url)
            })
        
        return data
    
    async def scrape(self, url: str, **kwargs) -> ScrapingResult:
        """Scrape URL using Playwright"""
        if not self.should_scrape_url(url):
            return ScrapingResult(
                url=url,
                success=False,
                error="URL already scraped or invalid",
                scraper_type=self.__class__.__name__
            )
        
        start_time = time.time()
        
        try:
            page = await self.context.new_page()
            
            # Set up page event handlers
            await self.setup_page_handlers(page)
            
            # Navigate to page
            response = await page.goto(
                url, 
                wait_until="networkidle",
                timeout=self.wait_timeout
            )
            
            if not response or response.status >= 400:
                await page.close()
                return ScrapingResult(
                    url=url,
                    success=False,
                    error=f"HTTP {response.status if response else 'No response'}",
                    status_code=response.status if response else None,
                    scraper_type=self.__class__.__name__
                )
            
            # Wait for dynamic content to load
            await self.wait_for_content(page)
            
            # Handle popups and overlays
            await self.handle_popups(page)
            
            # Get page content
            html_content = await page.content()
            
            # Parse with BeautifulSoup and selectolax
            soup = BeautifulSoup(html_content, 'lxml')
            tree = HTMLParser(html_content)
            
            # Extract data
            data = await self.parse_content(soup, tree, url)
            
            # Add performance metrics
            performance_metrics = await self.get_performance_metrics(page)
            data["performance"] = performance_metrics
            
            # Take screenshot if needed
            if kwargs.get("screenshot"):
                screenshot_path = f"/tmp/screenshot_{int(time.time())}.png"
                await page.screenshot(path=screenshot_path)
                data["screenshot"] = screenshot_path
            
            await page.close()
            self.scraped_urls.add(url)
            
            processing_time = time.time() - start_time
            
            return ScrapingResult(
                url=url,
                success=True,
                data=data,
                status_code=response.status,
                processing_time=processing_time,
                scraper_type=self.__class__.__name__,
                metadata={
                    "user_agent": await page.evaluate("navigator.userAgent"),
                    "viewport": self.viewport_size,
                    "javascript_enabled": True
                }
            )
            
        except Exception as e:
            logger.error(f"Playwright scraping failed for {url}: {e}")
            processing_time = time.time() - start_time
            
            return ScrapingResult(
                url=url,
                success=False,
                error=str(e),
                processing_time=processing_time,
                scraper_type=self.__class__.__name__
            )
    
    async def setup_page_handlers(self, page: Page):
        """Set up page event handlers"""
        
        # Block unnecessary resources to speed up loading
        await page.route("**/*.{png,jpg,jpeg,gif,svg,css,woff,woff2}", 
                        lambda route: route.abort() if not route.request.url.endswith(('.css',)) else route.continue_())
        
        # Handle console logs (for debugging)
        page.on("console", lambda msg: logger.debug(f"Console: {msg.text}"))
        
        # Handle page errors
        page.on("pageerror", lambda error: logger.warning(f"Page error: {error}"))
        
        # Handle request failures
        page.on("requestfailed", lambda request: logger.debug(f"Request failed: {request.url}"))
    
    async def wait_for_content(self, page: Page):
        """Wait for dynamic content to load"""
        
        # Wait for specific selector if provided
        if self.wait_for_selector:
            try:
                await page.wait_for_selector(
                    self.wait_for_selector, 
                    timeout=self.wait_timeout
                )
            except TimeoutError:
                logger.debug(f"Selector {self.wait_for_selector} not found within timeout")
        
        # Common e-commerce specific waits
        common_selectors = [
            ".product", ".product-info", ".price", ".add-to-cart",
            ".product-title", ".product-name", ".product-description"
        ]
        
        for selector in common_selectors:
            try:
                await page.wait_for_selector(selector, timeout=5000)
                break  # Found one, good enough
            except (TimeoutError, Exception):
                continue
        
        # Wait for any lazy-loaded content
        try:
            await page.wait_for_load_state("networkidle", timeout=10000)
        except (TimeoutError, Exception):
            pass
        
        # Scroll to trigger lazy loading
        await self.scroll_page(page)
        
        # Additional wait for any triggered content
        await asyncio.sleep(2)
    
    async def scroll_page(self, page: Page):
        """Scroll page to trigger lazy loading"""
        try:
            # Get page height
            page_height = await page.evaluate("document.body.scrollHeight")
            
            # Scroll in steps
            step = 300
            current_position = 0
            
            while current_position < page_height:
                current_position += step
                await page.evaluate(f"window.scrollTo(0, {current_position})")
                await asyncio.sleep(0.5)
            
            # Scroll back to top
            await page.evaluate("window.scrollTo(0, 0)")
            await asyncio.sleep(1)
            
        except Exception as e:
            logger.debug(f"Scrolling failed: {e}")
    
    async def handle_popups(self, page: Page):
        """Handle popups, modals, and overlays"""
        
        popup_selectors = [
            # Cookie banners
            "[id*='cookie'], [class*='cookie']",
            ".cookie-banner, .cookie-notice, .cookie-consent",
            
            # Email popups
            "[id*='email'], [class*='email']",
            ".newsletter-popup, .email-popup, .subscription-modal",
            
            # General modals
            ".modal, .popup, .overlay, .lightbox",
            "[role='dialog'], [aria-modal='true']",
            
            # Close buttons
            ".close, .close-btn, .modal-close",
            "[aria-label*='close'], [title*='close']"
        ]
        
        for selector in popup_selectors:
            try:
                elements = await page.query_selector_all(selector)
                for element in elements[:3]:  # Limit to first 3 elements
                    # Try to click close buttons
                    if "close" in selector.lower():
                        await element.click(timeout=1000)
                        await asyncio.sleep(0.5)
                    else:
                        # For popup containers, try to find close button within
                        close_btn = await element.query_selector(".close, .close-btn, [aria-label*='close']")
                        if close_btn:
                            await close_btn.click(timeout=1000)
                            await asyncio.sleep(0.5)
            except (TimeoutError, Exception):
                continue
        
        # Handle age verification or region selection
        age_selectors = [
            "button[id*='age'], button[class*='age']",
            "input[value*='yes'], input[value*='enter']",
            ".age-verification button, .age-gate button"
        ]
        
        for selector in age_selectors:
            try:
                element = await page.query_selector(selector)
                if element:
                    await element.click(timeout=1000)
                    await asyncio.sleep(1)
                    break
            except (TimeoutError, Exception):
                continue
    
    async def get_performance_metrics(self, page: Page) -> Dict[str, Any]:
        """Get page performance metrics"""
        try:
            metrics = await page.evaluate("""
                () => {
                    const perfData = performance.getEntriesByType('navigation')[0];
                    return {
                        loadTime: perfData ? perfData.loadEventEnd - perfData.loadEventStart : 0,
                        domContentLoaded: perfData ? perfData.domContentLoadedEventEnd - perfData.domContentLoadedEventStart : 0,
                        firstPaint: performance.getEntriesByName('first-paint')[0]?.startTime || 0,
                        firstContentfulPaint: performance.getEntriesByName('first-contentful-paint')[0]?.startTime || 0,
                        resourceCount: performance.getEntriesByType('resource').length
                    };
                }
            """)
            return metrics
        except Exception as e:
            logger.debug(f"Performance metrics extraction failed: {e}")
            return {}
    
    async def extract_dynamic_content(self, page: Page) -> Dict[str, Any]:
        """Extract content that's only available via JavaScript"""
        
        dynamic_data = {}
        
        try:
            # Extract data from window object
            window_data = await page.evaluate("""
                () => {
                    const data = {};
                    
                    // Common e-commerce data objects
                    if (window.productData) data.productData = window.productData;
                    if (window.shopify) data.shopify = window.shopify;
                    if (window.dataLayer) data.dataLayer = window.dataLayer;
                    if (window.gtag) data.hasGoogleAnalytics = true;
                    
                    // Product variants from JavaScript
                    if (window.product) data.product = window.product;
                    if (window.variants) data.variants = window.variants;
                    
                    return data;
                }
            """)
            dynamic_data.update(window_data)
            
            # Extract lazy-loaded prices
            prices = await page.evaluate("""
                () => {
                    const priceElements = document.querySelectorAll('[data-price], .price');
                    return Array.from(priceElements).map(el => ({
                        text: el.textContent.trim(),
                        dataPrice: el.dataset.price,
                        className: el.className
                    }));
                }
            """)
            if prices:
                dynamic_data["dynamic_prices"] = prices
            
            # Extract inventory information
            inventory = await page.evaluate("""
                () => {
                    const stockElements = document.querySelectorAll('[data-inventory], .stock, .availability');
                    return Array.from(stockElements).map(el => ({
                        text: el.textContent.trim(),
                        dataInventory: el.dataset.inventory,
                        className: el.className
                    }));
                }
            """)
            if inventory:
                dynamic_data["inventory_data"] = inventory
            
        except Exception as e:
            logger.debug(f"Dynamic content extraction failed: {e}")
        
        return dynamic_data
    
    async def wait_and_extract_reviews(self, page: Page) -> Dict[str, Any]:
        """Wait for and extract review data that loads dynamically"""
        
        reviews_data = {
            "reviews": [],
            "average_rating": 0,
            "total_reviews": 0
        }
        
        try:
            # Wait for review sections to load
            review_selectors = [
                ".reviews", ".review-section", ".ratings",
                "[data-reviews]", ".testimonials"
            ]
            
            for selector in review_selectors:
                try:
                    await page.wait_for_selector(selector, timeout=5000)
                    break
                except:
                    continue
            
            # Extract review data
            reviews = await page.evaluate("""
                () => {
                    const reviewElements = document.querySelectorAll('.review, .testimonial, [data-review]');
                    return Array.from(reviewElements).slice(0, 10).map(el => ({
                        text: el.textContent.trim(),
                        rating: el.querySelector('.rating, .stars')?.textContent || '',
                        author: el.querySelector('.author, .reviewer')?.textContent || '',
                        date: el.querySelector('.date')?.textContent || ''
                    }));
                }
            """)
            
            if reviews:
                reviews_data["reviews"] = reviews
                reviews_data["total_reviews"] = len(reviews)
            
            # Extract average rating
            rating = await page.evaluate("""
                () => {
                    const ratingEl = document.querySelector('[data-rating], .average-rating, .rating-value');
                    return ratingEl ? ratingEl.textContent.trim() : '';
                }
            """)
            
            if rating:
                import re
                rating_match = re.search(r'(\d+\.?\d*)', rating)
                if rating_match:
                    reviews_data["average_rating"] = float(rating_match.group(1))
            
        except Exception as e:
            logger.debug(f"Review extraction failed: {e}")
        
        return reviews_data
    
    async def extract_variant_data(self, page: Page) -> List[Dict[str, Any]]:
        """Extract product variants that are loaded dynamically"""
        
        try:
            variants = await page.evaluate("""
                () => {
                    const variants = [];
                    
                    // Look for select dropdowns
                    const selects = document.querySelectorAll('select[name*="variant"], select[name*="option"]');
                    selects.forEach(select => {
                        const options = Array.from(select.options).map(option => ({
                            value: option.value,
                            text: option.textContent.trim(),
                            selected: option.selected
                        }));
                        
                        if (options.length > 1) {
                            variants.push({
                                name: select.name || select.id || 'variant',
                                type: 'select',
                                options: options
                            });
                        }
                    });
                    
                    // Look for radio buttons
                    const radioGroups = {};
                    const radios = document.querySelectorAll('input[type="radio"][name*="variant"], input[type="radio"][name*="option"]');
                    radios.forEach(radio => {
                        const name = radio.name;
                        if (!radioGroups[name]) radioGroups[name] = [];
                        
                        const label = document.querySelector(`label[for="${radio.id}"]`) || radio.nextElementSibling;
                        radioGroups[name].push({
                            value: radio.value,
                            text: label ? label.textContent.trim() : radio.value,
                            checked: radio.checked
                        });
                    });
                    
                    Object.keys(radioGroups).forEach(name => {
                        variants.push({
                            name: name,
                            type: 'radio',
                            options: radioGroups[name]
                        });
                    });
                    
                    return variants;
                }
            """)
            
            return variants
            
        except Exception as e:
            logger.debug(f"Variant extraction failed: {e}")
            return []
    
    async def capture_api_calls(self, page: Page) -> List[Dict[str, Any]]:
        """Capture API calls that might contain product data"""
        
        api_calls = []
        
        # Set up request interception
        async def handle_request(request):
            if any(api_path in request.url for api_path in ['/api/', '/products.json', '/wp-json/', '/graphql']):
                api_calls.append({
                    "url": request.url,
                    "method": request.method,
                    "headers": dict(request.headers),
                    "post_data": request.post_data
                })
        
        page.on("request", handle_request)
        
        return api_calls