"""
Scrapy runner for large-scale scraping operations.
"""

import asyncio
import tempfile
import subprocess
import json
import os
from typing import Any, Dict, List, Optional
from datetime import datetime
import logging

from twisted.internet import reactor, defer
from scrapy.crawler import CrawlerRunner, CrawlerProcess
from scrapy.utils.project import get_project_settings
from scrapy import Spider, Request
from scrapy.http import Response

from app.core.security_utils import SecureSubprocessExecutor, SafeTempFile
from .data_normalizer import DataNormalizer
from .ecommerce_detector import EcommerceDetector

logger = logging.getLogger(__name__)


class ProductSpider(Spider):
    """Scrapy spider for product scraping"""
    name = "product_spider"
    
    def __init__(self, start_urls=None, scraping_config=None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.start_urls = start_urls or []
        self.config = scraping_config or {}
        self.ecommerce_detector = EcommerceDetector()
        self.data_normalizer = DataNormalizer()
        self.results = []
    
    def start_requests(self):
        """Generate initial requests"""
        for url in self.start_urls:
            yield Request(
                url=url,
                callback=self.parse,
                meta={
                    "dont_cache": True,
                    "download_timeout": self.config.get("timeout", 30)
                }
            )
    
    def parse(self, response: Response):
        """Parse product pages"""
        try:
            # Detect platform
            from bs4 import BeautifulSoup
            soup = BeautifulSoup(response.text, 'lxml')
            
            platform_info = self.ecommerce_detector.detect_platform(soup, response.url)
            
            # Check if this is a product page
            product_check = self.ecommerce_detector.is_product_page(soup, response.url)
            
            if product_check["is_product"]:
                # Extract product data
                product_data = self._extract_product_data(soup, response.url, platform_info)
                if product_data:
                    self.results.append({
                        "type": "product",
                        "url": response.url,
                        "platform": platform_info,
                        "product": product_data,
                        "scraped_at": datetime.now().isoformat()
                    })
            else:
                # Extract product links for further crawling
                product_links = self._extract_product_links(soup, response.url)
                for link in product_links[:self.config.get("max_products_per_page", 20)]:
                    yield Request(
                        url=link,
                        callback=self.parse,
                        meta=response.meta
                    )
        
        except Exception as e:
            self.logger.error(f"Error parsing {response.url}: {e}")
    
    def _extract_product_data(self, soup, url: str, platform_info: Dict[str, Any]) -> Dict[str, Any]:
        """Extract product data using platform-specific selectors"""
        
        selectors = platform_info.get("selectors", {})
        product_data = {}
        
        # Extract basic product information
        product_data["name"] = self._extract_text_by_selectors(
            soup, selectors.get("title", ["h1", ".product-title"])
        )
        
        product_data["description"] = self._extract_text_by_selectors(
            soup, selectors.get("description", [".product-description", ".description"])
        )
        
        # Extract price
        price_text = self._extract_text_by_selectors(
            soup, selectors.get("price", [".price", ".product-price"])
        )
        if price_text:
            from price_parser import Price
            try:
                parsed_price = Price.fromstring(price_text)
                if parsed_price.amount:
                    product_data["price"] = float(parsed_price.amount)
                    product_data["currency"] = parsed_price.currency
            except (ValueError, AttributeError, TypeError) as e:
                logger.debug(f"Price parsing failed for '{price_text}': {e}")
                pass
        
        # Extract availability
        availability_text = self._extract_text_by_selectors(
            soup, selectors.get("availability", [".stock", ".availability"])
        )
        if availability_text:
            product_data["availability"] = self._normalize_availability(availability_text)
        
        # Extract images
        image_elements = soup.select(".product-image img, .gallery img")
        product_data["images"] = []
        for img in image_elements[:5]:  # Limit to 5 images
            src = img.get("src") or img.get("data-src")
            if src:
                from urllib.parse import urljoin
                product_data["images"].append({
                    "url": urljoin(url, src),
                    "alt": img.get("alt", "")
                })
        
        # Normalize the data
        return self.data_normalizer.normalize_product_data(product_data)
    
    def _extract_text_by_selectors(self, soup, selectors: List[str]) -> Optional[str]:
        """Extract text using list of CSS selectors"""
        for selector in selectors:
            element = soup.select_one(selector)
            if element:
                text = element.get_text(strip=True)
                if text:
                    return text
        return None
    
    def _extract_product_links(self, soup, base_url: str) -> List[str]:
        """Extract product page links"""
        links = []
        
        # Common product link patterns
        product_selectors = [
            "a[href*='/product/']",
            "a[href*='/products/']",
            "a[href*='/item/']",
            ".product-item a",
            ".product-card a"
        ]
        
        for selector in product_selectors:
            elements = soup.select(selector)
            for element in elements:
                href = element.get("href")
                if href:
                    from urllib.parse import urljoin
                    full_url = urljoin(base_url, href)
                    links.append(full_url)
        
        return list(set(links))  # Remove duplicates
    
    def _normalize_availability(self, availability_text: str) -> str:
        """Normalize availability status"""
        text = availability_text.lower()
        
        if any(term in text for term in ["in stock", "available", "ready"]):
            return "in_stock"
        elif any(term in text for term in ["out of stock", "sold out"]):
            return "out_of_stock"
        elif any(term in text for term in ["pre-order", "coming soon"]):
            return "pre_order"
        
        return "unknown"


class BrandSpider(Spider):
    """Scrapy spider for brand analysis"""
    name = "brand_spider"
    
    def __init__(self, start_urls=None, scraping_config=None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.start_urls = start_urls or []
        self.config = scraping_config or {}
        self.results = []
    
    def parse(self, response: Response):
        """Parse brand pages"""
        try:
            from bs4 import BeautifulSoup
            soup = BeautifulSoup(response.text, 'lxml')
            
            brand_data = self._extract_brand_data(soup, response.url)
            
            self.results.append({
                "type": "brand",
                "url": response.url,
                "brand": brand_data,
                "scraped_at": datetime.now().isoformat()
            })
            
        except Exception as e:
            self.logger.error(f"Error parsing brand page {response.url}: {e}")
    
    def _extract_brand_data(self, soup, url: str) -> Dict[str, Any]:
        """Extract brand data"""
        
        brand_data = {}
        
        # Extract brand name
        title = soup.find("title")
        if title:
            brand_data["name"] = title.get_text().strip().split(" - ")[0]
        
        # Extract description
        meta_desc = soup.find("meta", attrs={"name": "description"})
        if meta_desc:
            brand_data["description"] = meta_desc.get("content", "")
        
        # Extract colors from CSS
        colors = []
        style_tags = soup.find_all("style")
        for style_tag in style_tags:
            css_content = style_tag.string or ""
            import re
            color_matches = re.findall(r'#[0-9a-fA-F]{6}', css_content)
            colors.extend(color_matches)
        
        brand_data["colors"] = list(set(colors))[:10]  # Top 10 unique colors
        
        # Extract social links
        social_links = {}
        social_platforms = {
            "facebook": "facebook.com",
            "twitter": "twitter.com",
            "instagram": "instagram.com",
            "linkedin": "linkedin.com"
        }
        
        for platform, domain in social_platforms.items():
            links = soup.find_all("a", href=lambda x: x and domain in x)
            if links:
                social_links[platform] = links[0]["href"]
        
        brand_data["social_links"] = social_links
        
        return brand_data


class ScrapyRunner:
    """Runner for Scrapy spiders"""
    
    def __init__(self):
        self.results = []
        self.runner = None
    
    async def run_product_scraping(self, urls: List[str], 
                                 config: Dict[str, Any] = None) -> List[Dict[str, Any]]:
        """Run product scraping with Scrapy"""
        
        if not urls:
            return []
        
        config = config or {}
        
        # Setup Scrapy settings
        settings = self._get_scrapy_settings(config)
        
        # Run in subprocess to avoid reactor issues
        return await self._run_spider_subprocess("product", urls, config)
    
    async def run_brand_scraping(self, urls: List[str], 
                               config: Dict[str, Any] = None) -> List[Dict[str, Any]]:
        """Run brand scraping with Scrapy"""
        
        if not urls:
            return []
        
        config = config or {}
        
        return await self._run_spider_subprocess("brand", urls, config)
    
    def _get_scrapy_settings(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """Get Scrapy settings"""
        
        settings = {
            "USER_AGENT": config.get("user_agent", "ScrapyBot/1.0"),
            "ROBOTSTXT_OBEY": config.get("obey_robots", False),
            "CONCURRENT_REQUESTS": config.get("concurrent_requests", 16),
            "CONCURRENT_REQUESTS_PER_DOMAIN": config.get("concurrent_requests_per_domain", 8),
            "DOWNLOAD_DELAY": config.get("download_delay", 1),
            "RANDOMIZE_DOWNLOAD_DELAY": config.get("randomize_delay", True),
            "DOWNLOAD_TIMEOUT": config.get("timeout", 30),
            "RETRY_TIMES": config.get("retry_times", 2),
            "REDIRECT_ENABLED": True,
            "COOKIES_ENABLED": config.get("cookies_enabled", True),
            "TELNETCONSOLE_ENABLED": False,
            "LOG_LEVEL": config.get("log_level", "INFO")
        }
        
        # Add proxy middleware if proxies are configured
        if config.get("proxies"):
            settings["DOWNLOADER_MIDDLEWARES"] = {
                "scrapy.downloadermiddlewares.httpproxy.HttpProxyMiddleware": 110,
            }
        
        # Add custom middlewares
        if config.get("custom_middlewares"):
            settings["DOWNLOADER_MIDDLEWARES"].update(config["custom_middlewares"])
        
        return settings
    
    async def _run_spider_subprocess(self, spider_type: str, urls: List[str], 
                                   config: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Run spider in subprocess to avoid reactor conflicts"""
        
        # Create temporary files for input and output
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as input_file:
            json.dump({
                "urls": urls,
                "config": config,
                "spider_type": spider_type
            }, input_file)
            input_file_path = input_file.name
        
        output_file_path = input_file_path.replace('.json', '_output.json')
        
        try:
            # Create spider script
            spider_script = self._create_spider_script()
            
            with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as script_file:
                script_file.write(spider_script)
                script_file_path = script_file.name
            
            # Run spider in subprocess securely
            result = await SecureSubprocessExecutor.execute_safe(
                executable="python",
                args=[script_file_path, input_file_path, output_file_path],
                timeout=1800  # 30 minutes timeout for scraping
            )
            
            if result["success"]:
                # Read results
                if os.path.exists(output_file_path):
                    with open(output_file_path, 'r') as f:
                        results = json.load(f)
                    return results
                else:
                    logger.warning("No output file generated")
                    return []
            else:
                logger.error(f"Scrapy subprocess failed: {result['stderr']}")
                return []
        
        except Exception as e:
            logger.error(f"Failed to run Scrapy subprocess: {e}")
            return []
        
        finally:
            # Cleanup temporary files
            for file_path in [input_file_path, output_file_path, script_file_path]:
                try:
                    if os.path.exists(file_path):
                        os.unlink(file_path)
                except:
                    pass
    
    def _create_spider_script(self) -> str:
        """Create the spider execution script"""
        
        return '''
import sys
import json
import asyncio
from scrapy.crawler import CrawlerProcess
from scrapy.utils.project import get_project_settings
from scrapy import Spider, Request
from scrapy.http import Response

class ScrapingSpider(Spider):
    name = "scraping_spider"
    
    def __init__(self, urls, config, spider_type):
        self.start_urls = urls
        self.config = config
        self.spider_type = spider_type
        self.results = []
    
    def parse(self, response):
        try:
            from bs4 import BeautifulSoup
            soup = BeautifulSoup(response.text, 'lxml')
            
            if self.spider_type == "product":
                data = self._extract_product_data(soup, response.url)
            elif self.spider_type == "brand":
                data = self._extract_brand_data(soup, response.url)
            else:
                data = {}
            
            if data:
                self.results.append({
                    "url": response.url,
                    "type": self.spider_type,
                    "data": data
                })
        
        except Exception as e:
            self.logger.error(f"Error parsing {response.url}: {e}")
    
    def _extract_product_data(self, soup, url):
        # Simplified product extraction
        data = {}
        
        # Extract title
        title_selectors = ["h1", ".product-title", ".product-name"]
        for selector in title_selectors:
            element = soup.select_one(selector)
            if element:
                data["name"] = element.get_text(strip=True)
                break
        
        # Extract price
        price_selectors = [".price", ".product-price", "[data-price]"]
        for selector in price_selectors:
            element = soup.select_one(selector)
            if element:
                price_text = element.get_text(strip=True)
                # Simple price extraction
                import re
                price_match = re.search(r'[\d,]+\.?\d*', price_text.replace(',', ''))
                if price_match:
                    try:
                        data["price"] = float(price_match.group())
                    except:
                        pass
                break
        
        return data
    
    def _extract_brand_data(self, soup, url):
        # Simplified brand extraction
        data = {}
        
        # Extract title
        title = soup.find("title")
        if title:
            data["name"] = title.get_text().strip()
        
        # Extract description
        meta_desc = soup.find("meta", attrs={"name": "description"})
        if meta_desc:
            data["description"] = meta_desc.get("content", "")
        
        return data

def main():
    if len(sys.argv) != 3:
        print("Usage: script.py input_file output_file")
        sys.exit(1)
    
    input_file = sys.argv[1]
    output_file = sys.argv[2]
    
    # Load input
    with open(input_file, 'r') as f:
        input_data = json.load(f)
    
    urls = input_data["urls"]
    config = input_data["config"]
    spider_type = input_data["spider_type"]
    
    # Setup Scrapy
    settings = get_project_settings()
    settings.update({
        "USER_AGENT": config.get("user_agent", "ScrapyBot/1.0"),
        "ROBOTSTXT_OBEY": False,
        "CONCURRENT_REQUESTS": config.get("concurrent_requests", 8),
        "DOWNLOAD_DELAY": config.get("download_delay", 1),
        "DOWNLOAD_TIMEOUT": config.get("timeout", 30),
        "LOG_LEVEL": "ERROR"  # Reduce logging
    })
    
    process = CrawlerProcess(settings)
    spider = ScrapingSpider(urls, config, spider_type)
    
    process.crawl(spider)
    process.start()
    
    # Save results
    with open(output_file, 'w') as f:
        json.dump(spider.results, f)

if __name__ == "__main__":
    main()
'''


# Example usage functions

async def scrape_product_catalog(brand_url: str, max_products: int = 100) -> List[Dict[str, Any]]:
    """Scrape product catalog for a brand"""
    
    runner = ScrapyRunner()
    
    config = {
        "max_products_per_page": 20,
        "concurrent_requests": 8,
        "download_delay": 2,
        "timeout": 30
    }
    
    # Start with main URL and let spider discover product pages
    results = await runner.run_product_scraping([brand_url], config)
    
    return results[:max_products]


async def scrape_competitor_brands(brand_urls: List[str]) -> List[Dict[str, Any]]:
    """Scrape multiple competitor brand sites"""
    
    runner = ScrapyRunner()
    
    config = {
        "concurrent_requests": 4,  # Be respectful to multiple sites
        "download_delay": 3,
        "timeout": 30
    }
    
    results = await runner.run_brand_scraping(brand_urls, config)
    
    return results