"""
Core brand scraper for extracting brand info and products for viral content generation.
"""

import asyncio
import re
import json
from typing import Any, Dict, List, Optional
from urllib.parse import urljoin, urlparse
import logging

import aiohttp
from bs4 import BeautifulSoup
from selectolax.parser import HTMLParser

from .base_scraper import BaseScraper, ScrapingResult
from app.core.config import settings

logger = logging.getLogger(__name__)


class CoreBrandScraper(BaseScraper):
    """Streamlined brand scraper for the core pipeline"""
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
    
    async def parse_content(self, soup: BeautifulSoup, tree: HTMLParser, url: str) -> Dict[str, Any]:
        """Parse brand content from HTML"""
        
        brand_data = await self.extract_brand_info(soup, url)
        products_data = await self.extract_products(soup, url)
        
        return {
            "brand": brand_data,
            "products": products_data,
            "url": url
        }
    
    async def scrape(self, url: str, **kwargs) -> ScrapingResult:
        """Scrape brand data from URL"""
        if not self.should_scrape_url(url):
            return ScrapingResult(
                url=url,
                success=False,
                error="URL already scraped or invalid",
                scraper_type=self.__class__.__name__
            )
        
        return await self.fetch_page(url, **kwargs)
    
    async def extract_brand_info(self, soup: BeautifulSoup, url: str) -> Dict[str, Any]:
        """Extract essential brand information"""
        
        brand_info = {
            "name": self.extract_brand_name(soup, url),
            "description": self.extract_brand_description(soup),
            "logo_url": self.extract_logo_url(soup, url),
            "target_audience": self.extract_target_audience(soup),
            "value_proposition": self.extract_value_proposition(soup),
            "brand_voice": self.extract_brand_voice(soup),
            "social_links": self.extract_social_links(soup),
            "contact_info": self.extract_contact_info(soup)
        }
        
        return brand_info
    
    async def extract_products(self, soup: BeautifulSoup, url: str) -> List[Dict[str, Any]]:
        """Extract product information"""
        
        products = []
        
        # Find product links
        product_links = self.find_product_links(soup, url)
        
        # Scrape first 10 products for content ideas
        for product_url in product_links[:10]:
            try:
                product_data = await self.scrape_product(product_url)
                if product_data:
                    products.append(product_data)
                    
                # Rate limiting
                await asyncio.sleep(1)
                
            except Exception as e:
                logger.debug(f"Error scraping product {product_url}: {e}")
                continue
        
        return products
    
    def extract_brand_name(self, soup: BeautifulSoup, url: str) -> str:
        """Extract brand name"""
        
        # Try meta tags
        og_site_name = soup.find("meta", property="og:site_name")
        if og_site_name:
            return og_site_name.get("content", "").strip()
        
        # Try title
        title = soup.find("title")
        if title:
            title_text = title.get_text().strip()
            # Remove common separators
            for sep in [" - ", " | ", " :: "]:
                if sep in title_text:
                    return title_text.split(sep)[0].strip()
            return title_text
        
        # Fallback to domain
        domain = urlparse(url).netloc.replace("www.", "")
        return domain.split(".")[0].title()
    
    def extract_brand_description(self, soup: BeautifulSoup) -> str:
        """Extract brand description"""
        
        # Try meta description
        meta_desc = soup.find("meta", attrs={"name": "description"})
        if meta_desc:
            return meta_desc.get("content", "").strip()
        
        # Try about sections
        about_selectors = [".about", ".brand-story", ".hero-description", ".intro"]
        for selector in about_selectors:
            element = soup.select_one(selector)
            if element:
                text = element.get_text(strip=True, separator=" ")
                if len(text) > 50:
                    return text[:300]
        
        return ""
    
    def extract_logo_url(self, soup: BeautifulSoup, base_url: str) -> Optional[str]:
        """Extract brand logo URL"""
        
        logo_selectors = [".logo img", ".brand img", ".header-logo img", "img[alt*='logo']"]
        
        for selector in logo_selectors:
            img = soup.select_one(selector)
            if img and img.get("src"):
                return self.normalize_url(img["src"], base_url)
        
        return None
    
    def extract_target_audience(self, soup: BeautifulSoup) -> Dict[str, Any]:
        """Extract target audience indicators"""
        
        text_content = soup.get_text().lower()
        
        audience_indicators = {
            "demographics": {
                "young_adults": ["trendy", "cool", "awesome", "vibes"],
                "professionals": ["business", "professional", "career", "corporate"],
                "families": ["family", "kids", "children", "parents"],
                "fitness": ["fitness", "health", "workout", "gym"],
                "luxury": ["luxury", "premium", "exclusive", "high-end"]
            },
            "interests": {
                "fashion": ["fashion", "style", "outfit", "clothing"],
                "tech": ["technology", "tech", "gadget", "digital"],
                "beauty": ["beauty", "skincare", "cosmetics", "makeup"],
                "home": ["home", "decor", "furniture", "kitchen"],
                "outdoor": ["outdoor", "adventure", "travel", "nature"]
            }
        }
        
        detected_audience = {"demographics": [], "interests": []}
        
        for category, groups in audience_indicators.items():
            for group, keywords in groups.items():
                score = sum(1 for keyword in keywords if keyword in text_content)
                if score > 0:
                    detected_audience[category].append({"segment": group, "score": score})
        
        return detected_audience
    
    def extract_value_proposition(self, soup: BeautifulSoup) -> str:
        """Extract main value proposition"""
        
        # Try hero section
        hero_selectors = [".hero h1", ".banner h1", ".jumbotron h1", "h1"]
        for selector in hero_selectors:
            element = soup.select_one(selector)
            if element:
                text = element.get_text(strip=True)
                if len(text) > 20 and len(text) < 200:
                    return text
        
        return ""
    
    def extract_brand_voice(self, soup: BeautifulSoup) -> Dict[str, Any]:
        """Extract brand voice indicators"""
        
        text_content = soup.get_text().lower()
        
        voice_indicators = {
            "casual": ["hey", "awesome", "cool", "fun", "easy"],
            "professional": ["professional", "expert", "quality", "excellence"],
            "friendly": ["friendly", "welcome", "love", "enjoy", "happy"],
            "luxury": ["luxury", "premium", "exclusive", "finest"],
            "innovative": ["innovative", "cutting-edge", "advanced", "modern"]
        }
        
        voice_scores = {}
        for tone, keywords in voice_indicators.items():
            score = sum(1 for keyword in keywords if keyword in text_content)
            if score > 0:
                voice_scores[tone] = score
        
        primary_voice = max(voice_scores.items(), key=lambda x: x[1])[0] if voice_scores else "neutral"
        
        return {"primary_voice": primary_voice, "scores": voice_scores}
    
    def extract_social_links(self, soup: BeautifulSoup) -> Dict[str, str]:
        """Extract social media links"""
        
        social_links = {}
        platforms = ["facebook", "twitter", "instagram", "linkedin", "youtube", "tiktok"]
        
        links = soup.find_all("a", href=True)
        for link in links:
            href = link["href"].lower()
            for platform in platforms:
                if platform in href:
                    social_links[platform] = link["href"]
                    break
        
        return social_links
    
    def extract_contact_info(self, soup: BeautifulSoup) -> Dict[str, str]:
        """Extract contact information"""
        
        contact_info = {}
        text_content = soup.get_text()
        
        # Extract email
        email_match = re.search(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', text_content)
        if email_match:
            contact_info["email"] = email_match.group()
        
        # Extract phone
        phone_match = re.search(r'\b\d{3}-\d{3}-\d{4}\b|\(\d{3}\)\s*\d{3}-\d{4}', text_content)
        if phone_match:
            contact_info["phone"] = phone_match.group()
        
        return contact_info
    
    def find_product_links(self, soup: BeautifulSoup, base_url: str) -> List[str]:
        """Find product page links"""
        
        product_links = []
        
        # Common product URL patterns
        product_patterns = [
            r'/product[s]?/',
            r'/item[s]?/',
            r'/shop/',
            r'/store/',
            r'/collection[s]?/'
        ]
        
        links = soup.find_all("a", href=True)
        for link in links:
            href = link["href"]
            if any(re.search(pattern, href, re.I) for pattern in product_patterns):
                full_url = self.normalize_url(href, base_url)
                if full_url not in product_links:
                    product_links.append(full_url)
        
        return product_links[:20]  # Limit to 20 products
    
    async def scrape_product(self, product_url: str) -> Optional[Dict[str, Any]]:
        """Scrape individual product information"""
        
        try:
            result = await self.fetch_page(product_url)
            if not result.success:
                return None
            
            soup = BeautifulSoup(result.data.get("content", ""), 'lxml')
            
            product_data = {
                "name": self.extract_product_name(soup),
                "price": self.extract_product_price(soup),
                "description": self.extract_product_description(soup),
                "images": self.extract_product_images(soup, product_url),
                "features": self.extract_product_features(soup),
                "benefits": self.extract_product_benefits(soup),
                "use_cases": self.extract_use_cases(soup),
                "url": product_url
            }
            
            # Only return if we got essential info
            if product_data["name"]:
                return product_data
            
        except Exception as e:
            logger.debug(f"Error scraping product {product_url}: {e}")
        
        return None
    
    def extract_product_name(self, soup: BeautifulSoup) -> str:
        """Extract product name"""
        
        selectors = ["h1", ".product-title", ".product-name", ".title"]
        for selector in selectors:
            element = soup.select_one(selector)
            if element:
                text = element.get_text(strip=True)
                if text and len(text) > 3:
                    return text
        
        return ""
    
    def extract_product_price(self, soup: BeautifulSoup) -> Optional[str]:
        """Extract product price"""
        
        price_selectors = [".price", ".cost", ".amount", ".product-price"]
        for selector in price_selectors:
            element = soup.select_one(selector)
            if element:
                price_text = element.get_text(strip=True)
                # Look for currency symbols or numbers
                if re.search(r'[\$£€¥]|\d+', price_text):
                    return price_text
        
        return None
    
    def extract_product_description(self, soup: BeautifulSoup) -> str:
        """Extract product description"""
        
        desc_selectors = [".description", ".product-description", ".details", ".about"]
        for selector in desc_selectors:
            element = soup.select_one(selector)
            if element:
                text = element.get_text(strip=True, separator=" ")
                if len(text) > 50:
                    return text[:500]
        
        return ""
    
    def extract_product_images(self, soup: BeautifulSoup, base_url: str) -> List[str]:
        """Extract product images"""
        
        images = []
        img_selectors = [".product-image img", ".gallery img", ".photos img"]
        
        for selector in img_selectors:
            imgs = soup.select(selector)
            for img in imgs:
                src = img.get("src") or img.get("data-src")
                if src:
                    full_url = self.normalize_url(src, base_url)
                    if full_url not in images:
                        images.append(full_url)
        
        return images[:5]  # Limit to 5 images
    
    def extract_product_features(self, soup: BeautifulSoup) -> List[str]:
        """Extract product features"""
        
        features = []
        
        # Look for feature lists
        feature_selectors = [".features li", ".specs li", ".highlights li"]
        for selector in feature_selectors:
            elements = soup.select(selector)
            for element in elements:
                text = element.get_text(strip=True)
                if text and len(text) > 5:
                    features.append(text)
        
        return features[:10]  # Limit to 10 features
    
    def extract_product_benefits(self, soup: BeautifulSoup) -> List[str]:
        """Extract product benefits"""
        
        benefits = []
        text_content = soup.get_text().lower()
        
        # Look for benefit indicators
        benefit_patterns = [
            r'(saves? \w+)',
            r'(improves? \w+)',
            r'(reduces? \w+)',
            r'(increases? \w+)',
            r'(helps? \w+)',
            r'(makes? \w+ easier)',
            r'(perfect for \w+)'
        ]
        
        for pattern in benefit_patterns:
            matches = re.findall(pattern, text_content)
            benefits.extend(matches)
        
        return list(set(benefits))[:5]  # Limit to 5 unique benefits
    
    def extract_use_cases(self, soup: BeautifulSoup) -> List[str]:
        """Extract product use cases"""
        
        use_cases = []
        text_content = soup.get_text().lower()
        
        # Look for use case indicators
        use_case_patterns = [
            r'(use for \w+)',
            r'(great for \w+)',
            r'(ideal for \w+)',
            r'(perfect for \w+)',
            r'(suitable for \w+)'
        ]
        
        for pattern in use_case_patterns:
            matches = re.findall(pattern, text_content)
            use_cases.extend(matches)
        
        return list(set(use_cases))[:5]  # Limit to 5 unique use cases