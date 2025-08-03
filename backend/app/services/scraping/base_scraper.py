"""
Base scraper interface and common functionality for all scraping operations.
"""

import asyncio
import time
import random
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Set, Union
from urllib.parse import urljoin, urlparse
import logging

import aiohttp
import requests
from fake_useragent import UserAgent
from bs4 import BeautifulSoup
from selectolax.parser import HTMLParser

from app.core.config import settings

logger = logging.getLogger(__name__)


@dataclass
class ScrapingResult:
    """Standard result format for all scraping operations"""
    url: str
    success: bool
    data: Dict[str, Any] = field(default_factory=dict)
    error: Optional[str] = None
    status_code: Optional[int] = None
    timestamp: float = field(default_factory=time.time)
    scraper_type: str = "base"
    processing_time: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "url": self.url,
            "success": self.success,
            "data": self.data,
            "error": self.error,
            "status_code": self.status_code,
            "timestamp": self.timestamp,
            "scraper_type": self.scraper_type,
            "processing_time": self.processing_time,
            "metadata": self.metadata
        }


class BaseScraper(ABC):
    """Base class for all scrapers with common functionality"""
    
    def __init__(self, 
                 max_retries: int = 3,
                 delay_range: tuple = (1, 3),
                 timeout: int = 30,
                 respect_robots: bool = True,
                 custom_headers: Optional[Dict[str, str]] = None):
        
        self.max_retries = max_retries
        self.delay_range = delay_range
        self.timeout = timeout
        self.respect_robots = respect_robots
        self.session = None
        self.scraped_urls: Set[str] = set()
        self.ua = UserAgent()
        
        # Default headers
        self.headers = {
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
        
        if custom_headers:
            self.headers.update(custom_headers)
    
    async def __aenter__(self):
        """Async context manager entry"""
        self.session = aiohttp.ClientSession(
            timeout=aiohttp.ClientTimeout(total=self.timeout),
            headers=self.headers,
            connector=aiohttp.TCPConnector(limit=10, limit_per_host=5)
        )
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        if self.session:
            await self.session.close()
    
    def get_random_user_agent(self) -> str:
        """Get a random user agent"""
        try:
            return self.ua.random
        except Exception:
            return settings.USER_AGENT
    
    async def random_delay(self):
        """Add random delay between requests"""
        delay = random.uniform(*self.delay_range)
        await asyncio.sleep(delay)
    
    def is_valid_url(self, url: str) -> bool:
        """Check if URL is valid"""
        try:
            result = urlparse(url)
            return all([result.scheme, result.netloc])
        except:
            return False
    
    def normalize_url(self, url: str, base_url: str = None) -> str:
        """Normalize and clean URL"""
        if not url:
            return ""
        
        # Handle relative URLs
        if url.startswith("//"):
            return f"https:{url}"
        elif url.startswith("/") and base_url:
            return urljoin(base_url, url)
        elif not url.startswith(("http://", "https://")) and base_url:
            return urljoin(base_url, url)
        
        return url
    
    def extract_domain(self, url: str) -> str:
        """Extract domain from URL"""
        try:
            parsed = urlparse(url)
            return parsed.netloc.lower()
        except:
            return ""
    
    def should_scrape_url(self, url: str) -> bool:
        """Check if URL should be scraped"""
        if url in self.scraped_urls:
            return False
        
        if not self.is_valid_url(url):
            return False
        
        # Check robots.txt if needed
        if self.respect_robots:
            # Implementation would go here
            pass
        
        return True
    
    async def fetch_page(self, url: str, **kwargs) -> ScrapingResult:
        """Fetch a single page with retry logic"""
        start_time = time.time()
        
        for attempt in range(self.max_retries):
            try:
                # Update user agent for each request
                headers = self.headers.copy()
                headers["User-Agent"] = self.get_random_user_agent()
                
                async with self.session.get(url, headers=headers, **kwargs) as response:
                    content = await response.text()
                    processing_time = time.time() - start_time
                    
                    if response.status == 200:
                        self.scraped_urls.add(url)
                        
                        # Parse with both BeautifulSoup and selectolax
                        soup = BeautifulSoup(content, 'lxml')
                        tree = HTMLParser(content)
                        
                        return ScrapingResult(
                            url=url,
                            success=True,
                            data=await self.parse_content(soup, tree, url),
                            status_code=response.status,
                            processing_time=processing_time,
                            scraper_type=self.__class__.__name__,
                            metadata={
                                "content_length": len(content),
                                "attempt": attempt + 1,
                                "headers": dict(response.headers)
                            }
                        )
                    else:
                        logger.warning(f"HTTP {response.status} for {url}")
                        
            except Exception as e:
                logger.error(f"Attempt {attempt + 1} failed for {url}: {e}")
                
                if attempt < self.max_retries - 1:
                    await self.random_delay()
                    continue
        
        # All attempts failed
        processing_time = time.time() - start_time
        return ScrapingResult(
            url=url,
            success=False,
            error=f"Failed after {self.max_retries} attempts",
            processing_time=processing_time,
            scraper_type=self.__class__.__name__
        )
    
    @abstractmethod
    async def parse_content(self, soup: BeautifulSoup, tree: HTMLParser, url: str) -> Dict[str, Any]:
        """Parse content from HTML - to be implemented by subclasses"""
        pass
    
    @abstractmethod
    async def scrape(self, url: str, **kwargs) -> ScrapingResult:
        """Main scraping method - to be implemented by subclasses"""
        pass
    
    def extract_text_content(self, soup: BeautifulSoup, 
                           selectors: List[str] = None,
                           exclude_tags: List[str] = None) -> str:
        """Extract clean text content from HTML"""
        
        if exclude_tags is None:
            exclude_tags = ["script", "style", "nav", "footer", "header", "aside"]
        
        # Remove unwanted elements
        for tag in exclude_tags:
            for element in soup.find_all(tag):
                element.decompose()
        
        # Extract text from specific selectors or general content
        if selectors:
            text_parts = []
            for selector in selectors:
                elements = soup.select(selector)
                for element in elements:
                    text = element.get_text(strip=True, separator=" ")
                    if text and len(text) > 10:
                        text_parts.append(text)
        else:
            # Extract from common content containers
            content_selectors = [
                "main", "article", ".content", "#content",
                ".main-content", ".page-content", ".entry-content"
            ]
            
            text_parts = []
            for selector in content_selectors:
                elements = soup.select(selector)
                if elements:
                    for element in elements:
                        text = element.get_text(strip=True, separator=" ")
                        if text:
                            text_parts.append(text)
                    break  # Stop after finding first matching selector
            
            # Fallback to body content
            if not text_parts:
                body = soup.find("body")
                if body:
                    text_parts.append(body.get_text(strip=True, separator=" "))
        
        return "\n\n".join(text_parts)
    
    def extract_metadata(self, soup: BeautifulSoup) -> Dict[str, Any]:
        """Extract page metadata"""
        metadata = {}
        
        # Basic meta tags
        title = soup.find("title")
        if title:
            metadata["title"] = title.get_text(strip=True)
        
        meta_description = soup.find("meta", attrs={"name": "description"})
        if meta_description:
            metadata["description"] = meta_description.get("content", "")
        
        meta_keywords = soup.find("meta", attrs={"name": "keywords"})
        if meta_keywords:
            metadata["keywords"] = meta_keywords.get("content", "")
        
        # Open Graph metadata
        og_tags = soup.find_all("meta", property=lambda x: x and x.startswith("og:"))
        for tag in og_tags:
            property_name = tag.get("property", "").replace("og:", "")
            metadata[f"og_{property_name}"] = tag.get("content", "")
        
        # Twitter Card metadata
        twitter_tags = soup.find_all("meta", attrs={"name": lambda x: x and x.startswith("twitter:")})
        for tag in twitter_tags:
            name = tag.get("name", "").replace("twitter:", "")
            metadata[f"twitter_{name}"] = tag.get("content", "")
        
        # Schema.org structured data
        json_ld_scripts = soup.find_all("script", type="application/ld+json")
        structured_data = []
        for script in json_ld_scripts:
            try:
                import json
                data = json.loads(script.string)
                structured_data.append(data)
            except:
                pass
        
        if structured_data:
            metadata["structured_data"] = structured_data
        
        return metadata
    
    def extract_links(self, soup: BeautifulSoup, base_url: str, 
                     same_domain_only: bool = True) -> List[Dict[str, str]]:
        """Extract links from page"""
        links = []
        base_domain = self.extract_domain(base_url)
        
        for a_tag in soup.find_all("a", href=True):
            href = a_tag["href"]
            normalized_url = self.normalize_url(href, base_url)
            
            if not self.is_valid_url(normalized_url):
                continue
            
            if same_domain_only and self.extract_domain(normalized_url) != base_domain:
                continue
            
            link_data = {
                "url": normalized_url,
                "text": a_tag.get_text(strip=True),
                "title": a_tag.get("title", ""),
                "rel": a_tag.get("rel", [])
            }
            
            links.append(link_data)
        
        return links
    
    def extract_images(self, soup: BeautifulSoup, base_url: str, 
                      limit: int = 50) -> List[Dict[str, str]]:
        """Extract images from page"""
        images = []
        
        for img in soup.find_all("img", src=True):
            src = self.normalize_url(img["src"], base_url)
            
            if not src or src.startswith("data:"):
                continue
            
            image_data = {
                "src": src,
                "alt": img.get("alt", ""),
                "title": img.get("title", ""),
                "width": img.get("width", ""),
                "height": img.get("height", ""),
                "loading": img.get("loading", ""),
                "srcset": img.get("srcset", "")
            }
            
            images.append(image_data)
            
            if len(images) >= limit:
                break
        
        return images