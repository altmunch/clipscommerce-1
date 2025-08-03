"""
Brand scraper for comprehensive brand analysis and competitor discovery.
"""

import asyncio
import re
import time
from typing import Any, Dict, List, Optional, Set, Tuple
from urllib.parse import urljoin, urlparse
import logging

import aiohttp
from bs4 import BeautifulSoup
from selectolax.parser import HTMLParser

from .base_scraper import BaseScraper, ScrapingResult
from .product_scraper import ProductScraper
from .ecommerce_detector import EcommerceDetector
from .data_normalizer import DataNormalizer
from ..ai.providers import get_text_service

logger = logging.getLogger(__name__)


class BrandScraper(BaseScraper):
    """Comprehensive brand scraper for brand analysis and competitor discovery"""
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.ecommerce_detector = EcommerceDetector()
        self.data_normalizer = DataNormalizer()
        self.product_scraper = ProductScraper()
        self.ai_service = None
    
    async def parse_content(self, soup: BeautifulSoup, tree: HTMLParser, url: str) -> Dict[str, Any]:
        """Parse brand content from HTML"""
        
        # Detect e-commerce platform
        platform_info = self.ecommerce_detector.detect_platform(soup, url)
        
        # Extract comprehensive brand data
        brand_data = await self.extract_brand_data(soup, tree, url, platform_info)
        
        return {
            "type": "brand_analysis",
            "platform": platform_info,
            "brand": brand_data,
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
    
    async def extract_brand_data(self, soup: BeautifulSoup, tree: HTMLParser, 
                                url: str, platform_info: Dict[str, Any]) -> Dict[str, Any]:
        """Extract comprehensive brand information"""
        
        brand_data = {
            "name": None,
            "description": None,
            "logo_url": None,
            "colors": {},
            "fonts": [],
            "voice_tone": {},
            "messaging": [],
            "target_audience": {},
            "industry": None,
            "value_proposition": None,
            "social_links": {},
            "contact_info": {},
            "business_info": {},
            "products": [],
            "competitors": [],
            "market_analysis": {},
            "content_themes": [],
            "trust_signals": []
        }
        
        # Extract brand name
        brand_data["name"] = self.extract_brand_name(soup, url)
        
        # Extract brand description
        brand_data["description"] = self.extract_brand_description(soup)
        
        # Extract logo
        brand_data["logo_url"] = self.extract_logo_url(soup, url)
        
        # Extract visual identity
        brand_data["colors"] = self.extract_brand_colors(soup)
        brand_data["fonts"] = self.extract_brand_fonts(soup)
        
        # Extract messaging and content
        messaging = self.extract_brand_messaging(soup)
        brand_data["messaging"] = messaging
        
        # Extract value proposition
        brand_data["value_proposition"] = self.extract_value_proposition(soup)
        
        # Extract social media links
        brand_data["social_links"] = self.extract_social_links(soup, url)
        
        # Extract contact and business information
        brand_data["contact_info"] = self.extract_contact_info(soup)
        brand_data["business_info"] = self.extract_business_info(soup)
        
        # Extract product information (sample)
        brand_data["products"] = await self.extract_product_samples(soup, url, platform_info)
        
        # Extract trust signals
        brand_data["trust_signals"] = self.extract_trust_signals(soup)
        
        # Analyze brand voice and tone with AI
        if messaging:
            brand_data["voice_tone"] = await self.analyze_brand_voice_ai(messaging)
        
        # Determine target audience
        brand_data["target_audience"] = await self.analyze_target_audience(soup, brand_data)
        
        # Determine industry
        brand_data["industry"] = await self.determine_industry(brand_data)
        
        # Extract content themes
        brand_data["content_themes"] = self.extract_content_themes(soup)
        
        return brand_data
    
    def extract_brand_name(self, soup: BeautifulSoup, url: str) -> str:
        """Extract brand name from page"""
        
        # Try structured data first
        json_ld_scripts = soup.find_all("script", type="application/ld+json")
        for script in json_ld_scripts:
            try:
                import json
                data = json.loads(script.string)
                if isinstance(data, dict) and data.get("@type") == "Organization":
                    if data.get("name"):
                        return data["name"]
            except:
                pass
        
        # Try meta tags
        meta_brand = soup.find("meta", property="og:site_name")
        if meta_brand:
            return meta_brand.get("content", "").strip()
        
        # Try title tag (first part before separator)
        title = soup.find("title")
        if title:
            title_text = title.get_text().strip()
            separators = [" - ", " | ", " :: ", " • "]
            for sep in separators:
                if sep in title_text:
                    return title_text.split(sep)[0].strip()
            return title_text
        
        # Try header/logo area
        header_selectors = ["header .logo", ".brand-name", ".site-title", ".company-name"]
        for selector in header_selectors:
            element = soup.select_one(selector)
            if element:
                text = element.get_text(strip=True)
                if text and len(text) < 50:
                    return text
        
        # Fallback to domain name
        domain = urlparse(url).netloc
        return domain.replace("www.", "").split(".")[0].title()
    
    def extract_brand_description(self, soup: BeautifulSoup) -> str:
        """Extract brand description"""
        
        # Try meta description
        meta_desc = soup.find("meta", attrs={"name": "description"})
        if meta_desc:
            description = meta_desc.get("content", "").strip()
            if description and len(description) > 50:
                return description
        
        # Try about sections
        about_selectors = [
            ".about-section", ".brand-story", ".company-description",
            ".mission", ".about-us", ".hero-description"
        ]
        
        for selector in about_selectors:
            element = soup.select_one(selector)
            if element:
                text = element.get_text(strip=True, separator=" ")
                if text and len(text) > 50:
                    return text[:500]  # Limit length
        
        # Try first paragraph in main content
        main_content = soup.select_one("main, .main, .content, .page-content")
        if main_content:
            paragraphs = main_content.find_all("p")
            for p in paragraphs:
                text = p.get_text(strip=True)
                if text and len(text) > 50 and len(text) < 300:
                    return text
        
        return ""
    
    def extract_logo_url(self, soup: BeautifulSoup, base_url: str) -> Optional[str]:
        """Extract brand logo URL"""
        
        # Try common logo selectors
        logo_selectors = [
            ".logo img", ".brand img", ".site-logo img",
            "header img[alt*='logo']", "img[class*='logo']",
            ".navbar-brand img", ".brand-logo img"
        ]
        
        for selector in logo_selectors:
            img = soup.select_one(selector)
            if img and img.get("src"):
                return self.normalize_url(img["src"], base_url)
        
        # Try favicon as fallback
        favicon = soup.find("link", rel=lambda x: x and "icon" in x.lower())
        if favicon and favicon.get("href"):
            favicon_url = self.normalize_url(favicon["href"], base_url)
            if not favicon_url.endswith((".ico", ".png", ".jpg", ".jpeg", ".svg")):
                return None
            return favicon_url
        
        return None
    
    def extract_brand_colors(self, soup: BeautifulSoup) -> Dict[str, List[str]]:
        """Extract brand colors from CSS and inline styles"""
        
        colors = {
            "primary": [],
            "secondary": [],
            "accent": [],
            "text": [],
            "background": []
        }
        
        # Extract from style attributes
        elements_with_style = soup.find_all(attrs={"style": True})
        for element in elements_with_style:
            style = element.get("style", "")
            self._extract_colors_from_css(style, colors)
        
        # Extract from CSS stylesheets
        style_tags = soup.find_all("style")
        for style_tag in style_tags:
            css_content = style_tag.string or ""
            self._extract_colors_from_css(css_content, colors)
        
        # Analyze color frequency and categorize
        return self._categorize_colors(colors)
    
    def _extract_colors_from_css(self, css_content: str, colors: Dict[str, List[str]]):
        """Extract colors from CSS content"""
        
        # Color patterns
        hex_pattern = r'#[0-9a-fA-F]{6}|#[0-9a-fA-F]{3}'
        rgb_pattern = r'rgb\([^)]+\)'
        rgba_pattern = r'rgba\([^)]+\)'
        hsl_pattern = r'hsl\([^)]+\)'
        
        patterns = [hex_pattern, rgb_pattern, rgba_pattern, hsl_pattern]
        
        for pattern in patterns:
            matches = re.findall(pattern, css_content)
            colors["primary"].extend(matches)
    
    def _categorize_colors(self, colors: Dict[str, List[str]]) -> Dict[str, str]:
        """Categorize colors into brand palette"""
        
        all_colors = colors["primary"]
        if not all_colors:
            return {}
        
        # Count color frequency
        color_counts = {}
        for color in all_colors:
            color_counts[color] = color_counts.get(color, 0) + 1
        
        # Sort by frequency
        sorted_colors = sorted(color_counts.items(), key=lambda x: x[1], reverse=True)
        
        # Categorize most frequent colors
        categorized = {}
        if len(sorted_colors) > 0:
            categorized["primary"] = sorted_colors[0][0]
        if len(sorted_colors) > 1:
            categorized["secondary"] = sorted_colors[1][0]
        if len(sorted_colors) > 2:
            categorized["accent"] = sorted_colors[2][0]
        
        return categorized
    
    def extract_brand_fonts(self, soup: BeautifulSoup) -> List[str]:
        """Extract font families used on the site"""
        
        fonts = set()
        
        # Extract from style attributes
        elements_with_style = soup.find_all(attrs={"style": True})
        for element in elements_with_style:
            style = element.get("style", "")
            font_match = re.search(r'font-family:\s*([^;]+)', style)
            if font_match:
                font_family = font_match.group(1).strip().strip('"\'')
                fonts.add(font_family)
        
        # Extract from CSS
        style_tags = soup.find_all("style")
        for style_tag in style_tags:
            css_content = style_tag.string or ""
            font_matches = re.findall(r'font-family:\s*([^;}]+)', css_content)
            for font_family in font_matches:
                font_family = font_family.strip().strip('"\'')
                fonts.add(font_family)
        
        return list(fonts)[:10]  # Limit to 10 fonts
    
    def extract_brand_messaging(self, soup: BeautifulSoup) -> List[str]:
        """Extract key brand messaging and copy"""
        
        messaging = []
        
        # Headlines and key messages
        headline_selectors = ["h1", "h2", ".hero-title", ".tagline", ".slogan"]
        for selector in headline_selectors:
            elements = soup.select(selector)
            for element in elements:
                text = element.get_text(strip=True)
                if text and len(text) > 10 and len(text) < 200:
                    messaging.append(text)
        
        # Call-to-action text
        cta_selectors = [".cta", ".btn", "button", ".call-to-action"]
        for selector in cta_selectors:
            elements = soup.select(selector)
            for element in elements:
                text = element.get_text(strip=True)
                if text and len(text) > 5 and len(text) < 50:
                    messaging.append(text)
        
        # Value propositions
        value_selectors = [".value-prop", ".benefits", ".features", ".why-choose"]
        for selector in value_selectors:
            elements = soup.select(selector)
            for element in elements:
                text = element.get_text(strip=True)
                if text and len(text) > 20 and len(text) < 300:
                    messaging.append(text)
        
        return messaging[:20]  # Limit to 20 messages
    
    def extract_value_proposition(self, soup: BeautifulSoup) -> str:
        """Extract main value proposition"""
        
        # Try hero section first
        hero_selectors = [".hero", ".banner", ".jumbotron", ".hero-section"]
        for selector in hero_selectors:
            hero = soup.select_one(selector)
            if hero:
                # Look for main headline
                headline = hero.select_one("h1, h2, .headline, .title")
                if headline:
                    text = headline.get_text(strip=True)
                    if text and len(text) > 20:
                        return text
        
        # Try main headline
        h1 = soup.find("h1")
        if h1:
            text = h1.get_text(strip=True)
            if text and len(text) > 20:
                return text
        
        # Try tagline or slogan
        tagline_selectors = [".tagline", ".slogan", ".subtitle", ".lead"]
        for selector in tagline_selectors:
            element = soup.select_one(selector)
            if element:
                text = element.get_text(strip=True)
                if text and len(text) > 20:
                    return text
        
        return ""
    
    def extract_social_links(self, soup: BeautifulSoup, base_url: str) -> Dict[str, str]:
        """Extract social media links"""
        
        social_links = {}
        
        # Common social platforms
        platforms = {
            "facebook": ["facebook.com", "fb.com"],
            "twitter": ["twitter.com", "x.com"],
            "instagram": ["instagram.com"],
            "linkedin": ["linkedin.com"],
            "youtube": ["youtube.com", "youtu.be"],
            "tiktok": ["tiktok.com"],
            "pinterest": ["pinterest.com"],
            "snapchat": ["snapchat.com"]
        }
        
        # Find all links
        links = soup.find_all("a", href=True)
        for link in links:
            href = link["href"]
            
            # Check if link is to a social platform
            for platform, domains in platforms.items():
                if any(domain in href for domain in domains):
                    social_links[platform] = href
                    break
        
        return social_links
    
    def extract_contact_info(self, soup: BeautifulSoup) -> Dict[str, str]:
        """Extract contact information"""
        
        contact_info = {}
        
        # Extract email addresses
        email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
        page_text = soup.get_text()
        emails = re.findall(email_pattern, page_text)
        if emails:
            contact_info["email"] = emails[0]  # First email found
        
        # Extract phone numbers
        phone_patterns = [
            r'\b\d{3}-\d{3}-\d{4}\b',  # 123-456-7890
            r'\b\(\d{3}\)\s*\d{3}-\d{4}\b',  # (123) 456-7890
            r'\b\d{3}\.\d{3}\.\d{4}\b',  # 123.456.7890
            r'\b\+\d{1,3}\s*\d{3,}\b'  # International
        ]
        
        for pattern in phone_patterns:
            phones = re.findall(pattern, page_text)
            if phones:
                contact_info["phone"] = phones[0]
                break
        
        # Extract address
        address_selectors = [".address", ".location", ".contact-address"]
        for selector in address_selectors:
            element = soup.select_one(selector)
            if element:
                address = element.get_text(strip=True)
                if address and len(address) > 20:
                    contact_info["address"] = address
                    break
        
        return contact_info
    
    def extract_business_info(self, soup: BeautifulSoup) -> Dict[str, str]:
        """Extract business information"""
        
        business_info = {}
        
        # Try structured data
        json_ld_scripts = soup.find_all("script", type="application/ld+json")
        for script in json_ld_scripts:
            try:
                import json
                data = json.loads(script.string)
                if isinstance(data, dict) and data.get("@type") == "Organization":
                    if data.get("foundingDate"):
                        business_info["founded"] = data["foundingDate"]
                    if data.get("numberOfEmployees"):
                        business_info["employees"] = data["numberOfEmployees"]
                    if data.get("address"):
                        business_info["address"] = data["address"]
            except:
                pass
        
        # Look for about page information
        about_text = soup.get_text().lower()
        
        # Extract founding year
        year_patterns = [
            r'founded in (\d{4})',
            r'established (\d{4})',
            r'since (\d{4})',
            r'est\.?\s*(\d{4})'
        ]
        
        for pattern in year_patterns:
            match = re.search(pattern, about_text)
            if match:
                business_info["founded"] = match.group(1)
                break
        
        # Extract company size indicators
        size_patterns = [
            r'(\d+)\s*employees',
            r'team of (\d+)',
            r'(\d+)\s*people'
        ]
        
        for pattern in size_patterns:
            match = re.search(pattern, about_text)
            if match:
                business_info["employees"] = match.group(1)
                break
        
        return business_info
    
    async def extract_product_samples(self, soup: BeautifulSoup, base_url: str, 
                                    platform_info: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Extract sample products for brand analysis"""
        
        products = []
        
        # Try to find product links
        product_links = []
        
        # Common product page patterns
        product_patterns = [
            r'/product[s]?/',
            r'/item[s]?/',
            r'/shop/',
            r'/store/',
            r'/catalog/'
        ]
        
        links = soup.find_all("a", href=True)
        for link in links:
            href = link["href"]
            if any(pattern in href for pattern in product_patterns):
                full_url = self.normalize_url(href, base_url)
                product_links.append(full_url)
        
        # Limit to first 5 product links
        product_links = product_links[:5]
        
        # Scrape basic product info from each link
        for product_url in product_links:
            try:
                product_result = await self.product_scraper.scrape(product_url)
                if product_result.success and product_result.data.get("product"):
                    product_data = product_result.data["product"]
                    
                    # Extract key info for brand analysis
                    product_summary = {
                        "name": product_data.get("name"),
                        "price": product_data.get("price"),
                        "currency": product_data.get("currency"),
                        "category": product_data.get("category"),
                        "url": product_url
                    }
                    products.append(product_summary)
                    
            except Exception as e:
                logger.debug(f"Failed to scrape product {product_url}: {e}")
                continue
        
        return products
    
    def extract_trust_signals(self, soup: BeautifulSoup) -> List[Dict[str, str]]:
        """Extract trust signals and certifications"""
        
        trust_signals = []
        
        # Security badges
        security_indicators = soup.select("img[alt*='ssl'], img[alt*='secure'], img[alt*='encrypted']")
        for img in security_indicators:
            trust_signals.append({
                "type": "security",
                "text": img.get("alt", ""),
                "image": img.get("src", "")
            })
        
        # Payment badges
        payment_indicators = soup.select("img[alt*='visa'], img[alt*='mastercard'], img[alt*='paypal']")
        for img in payment_indicators:
            trust_signals.append({
                "type": "payment",
                "text": img.get("alt", ""),
                "image": img.get("src", "")
            })
        
        # Certification badges
        cert_selectors = [".certifications", ".badges", ".trust-badges"]
        for selector in cert_selectors:
            elements = soup.select(selector)
            for element in elements:
                trust_signals.append({
                    "type": "certification",
                    "text": element.get_text(strip=True)
                })
        
        # Reviews and ratings
        review_selectors = [".reviews", ".rating", ".testimonials"]
        for selector in review_selectors:
            elements = soup.select(selector)
            for element in elements:
                text = element.get_text(strip=True)
                if "review" in text.lower() or "rating" in text.lower():
                    trust_signals.append({
                        "type": "reviews",
                        "text": text
                    })
        
        return trust_signals[:10]  # Limit to 10 trust signals
    
    async def analyze_brand_voice_ai(self, messaging: List[str]) -> Dict[str, Any]:
        """Analyze brand voice and tone using AI"""
        
        if not messaging:
            return {}
        
        try:
            # Initialize AI service if needed
            if not self.ai_service:
                self.ai_service = await get_text_service()
            
            # Combine messaging for analysis
            content = "\n".join(messaging[:10])  # Limit content
            
            prompt = f"""
            Analyze the following brand messaging and copy to determine the brand's voice and tone:

            {content}

            Please identify:
            1. Overall tone (formal, casual, friendly, professional, playful, etc.)
            2. Personality traits (confident, approachable, innovative, trustworthy, etc.)
            3. Communication style (direct, storytelling, educational, persuasive, etc.)
            4. Target audience indicators
            5. Key themes and values

            Provide a structured analysis.
            """
            
            response = await self.ai_service.generate(
                prompt,
                max_tokens=500,
                temperature=0.3
            )
            
            if response.success:
                # Parse the response (in production, use structured prompts)
                return {
                    "analysis": response.content,
                    "confidence": 0.8
                }
            
        except Exception as e:
            logger.debug(f"AI brand voice analysis failed: {e}")
        
        # Fallback analysis
        return self._analyze_brand_voice_simple(messaging)
    
    def _analyze_brand_voice_simple(self, messaging: List[str]) -> Dict[str, Any]:
        """Simple brand voice analysis without AI"""
        
        combined_text = " ".join(messaging).lower()
        
        # Simple tone indicators
        tone_indicators = {
            "professional": ["professional", "expert", "quality", "excellence"],
            "friendly": ["friendly", "welcome", "hello", "love", "enjoy"],
            "casual": ["hey", "awesome", "cool", "fun", "easy"],
            "luxury": ["luxury", "premium", "exclusive", "finest", "elite"],
            "innovative": ["innovative", "cutting-edge", "advanced", "modern", "new"]
        }
        
        tone_scores = {}
        for tone, keywords in tone_indicators.items():
            score = sum(1 for keyword in keywords if keyword in combined_text)
            if score > 0:
                tone_scores[tone] = score
        
        # Determine primary tone
        primary_tone = max(tone_scores.items(), key=lambda x: x[1])[0] if tone_scores else "professional"
        
        return {
            "primary_tone": primary_tone,
            "tone_scores": tone_scores,
            "confidence": 0.6
        }
    
    async def analyze_target_audience(self, soup: BeautifulSoup, brand_data: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze target audience based on content and messaging"""
        
        audience_indicators = {
            "age_groups": {
                "young_adults": ["trendy", "instagram", "social", "cool", "awesome"],
                "millennials": ["authentic", "sustainable", "experience", "community"],
                "gen_x": ["quality", "reliable", "family", "practical"],
                "boomers": ["traditional", "established", "trusted", "proven"]
            },
            "demographics": {
                "business": ["business", "professional", "enterprise", "corporate"],
                "consumers": ["family", "home", "personal", "lifestyle"],
                "students": ["student", "education", "learning", "affordable"],
                "luxury": ["luxury", "premium", "exclusive", "high-end"]
            }
        }
        
        page_text = soup.get_text().lower()
        messaging_text = " ".join(brand_data.get("messaging", [])).lower()
        combined_text = f"{page_text} {messaging_text}"
        
        audience_analysis = {}
        
        for category, groups in audience_indicators.items():
            scores = {}
            for group, keywords in groups.items():
                score = sum(1 for keyword in keywords if keyword in combined_text)
                if score > 0:
                    scores[group] = score
            
            if scores:
                audience_analysis[category] = max(scores.items(), key=lambda x: x[1])[0]
        
        return audience_analysis
    
    async def determine_industry(self, brand_data: Dict[str, Any]) -> str:
        """Determine industry based on brand data"""
        
        # Combine all text data
        text_data = []
        if brand_data.get("description"):
            text_data.append(brand_data["description"])
        if brand_data.get("messaging"):
            text_data.extend(brand_data["messaging"][:5])
        if brand_data.get("value_proposition"):
            text_data.append(brand_data["value_proposition"])
        
        combined_text = " ".join(text_data).lower()
        
        # Industry keywords
        industry_keywords = {
            "technology": ["software", "app", "tech", "digital", "ai", "saas", "platform"],
            "fashion": ["clothing", "fashion", "style", "apparel", "wear", "design"],
            "beauty": ["beauty", "cosmetics", "skincare", "makeup", "hair", "wellness"],
            "food": ["food", "restaurant", "cuisine", "cooking", "recipe", "nutrition"],
            "health": ["health", "medical", "wellness", "fitness", "healthcare", "therapy"],
            "finance": ["finance", "banking", "investment", "money", "financial", "loan"],
            "education": ["education", "learning", "course", "training", "academy", "school"],
            "retail": ["shop", "store", "retail", "shopping", "marketplace", "buy"],
            "automotive": ["car", "auto", "vehicle", "automotive", "driving", "transport"],
            "real_estate": ["property", "real estate", "home", "house", "apartment", "rent"]
        }
        
        industry_scores = {}
        for industry, keywords in industry_keywords.items():
            score = sum(1 for keyword in keywords if keyword in combined_text)
            if score > 0:
                industry_scores[industry] = score
        
        if industry_scores:
            return max(industry_scores.items(), key=lambda x: x[1])[0]
        
        return "general"
    
    def extract_content_themes(self, soup: BeautifulSoup) -> List[str]:
        """Extract main content themes"""
        
        themes = []
        
        # Navigation menu items often indicate content themes
        nav_selectors = ["nav a", ".menu a", ".navigation a", "header a"]
        for selector in nav_selectors:
            elements = soup.select(selector)
            for element in elements:
                text = element.get_text(strip=True)
                if text and len(text) > 3 and len(text) < 30:
                    themes.append(text)
        
        # Section headings
        heading_selectors = ["h2", "h3", ".section-title", ".heading"]
        for selector in heading_selectors:
            elements = soup.select(selector)
            for element in elements:
                text = element.get_text(strip=True)
                if text and len(text) > 5 and len(text) < 50:
                    themes.append(text)
        
        # Clean and deduplicate themes
        clean_themes = []
        seen = set()
        for theme in themes:
            theme_clean = theme.lower().strip()
            if theme_clean not in seen and theme_clean not in ["home", "contact", "about"]:
                clean_themes.append(theme)
                seen.add(theme_clean)
        
        return clean_themes[:15]  # Limit to 15 themes
    
    async def discover_competitors(self, brand_data: Dict[str, Any], 
                                 search_queries: List[str] = None) -> List[Dict[str, Any]]:
        """Discover competitor brands based on brand analysis"""
        
        competitors = []
        
        if not search_queries:
            # Generate search queries from brand data
            search_queries = self._generate_competitor_search_queries(brand_data)
        
        # This would integrate with search APIs or competitor databases
        # For now, providing a placeholder structure
        
        return competitors
    
    def _generate_competitor_search_queries(self, brand_data: Dict[str, Any]) -> List[str]:
        """Generate search queries to find competitors"""
        
        queries = []
        
        industry = brand_data.get("industry", "")
        if industry:
            queries.append(f"{industry} brands")
            queries.append(f"best {industry} companies")
        
        # Use product categories
        products = brand_data.get("products", [])
        if products:
            categories = [p.get("category") for p in products if p.get("category")]
            for category in set(categories):
                queries.append(f"{category} brands")
        
        # Use value proposition keywords
        value_prop = brand_data.get("value_proposition", "")
        if value_prop:
            # Extract key terms
            key_terms = re.findall(r'\b\w{4,}\b', value_prop.lower())
            for term in key_terms[:3]:
                queries.append(f"{term} companies")
        
        return queries[:10]  # Limit to 10 queries