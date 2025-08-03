"""
Comprehensive Web Scraping System for Brand and Product Discovery

This package provides a robust web scraping framework for extracting:
- Brand information and visual identity
- Product catalogs and pricing data
- E-commerce platform detection
- Competitor analysis
- Content for brand voice analysis
"""

from .base_scraper import BaseScraper, ScrapingResult
from .product_scraper import ProductScraper
from .brand_scraper import BrandScraper
from .ecommerce_detector import EcommerceDetector
from .playwright_scraper import PlaywrightScraper
from .scrapy_runner import ScrapyRunner
from .proxy_manager import ProxyManager
from .data_normalizer import DataNormalizer
from .apify_client import ApifyTikTokClient, ApifyJobStatus, ScrapingMode

__all__ = [
    "BaseScraper",
    "ScrapingResult", 
    "ProductScraper",
    "BrandScraper",
    "EcommerceDetector",
    "PlaywrightScraper",
    "ScrapyRunner",
    "ProxyManager",
    "DataNormalizer",
    "ApifyTikTokClient",
    "ApifyJobStatus",
    "ScrapingMode",
]