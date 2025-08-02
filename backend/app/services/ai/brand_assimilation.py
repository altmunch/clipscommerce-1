"""
Brand Assimilation AI Service

Analyzes brand websites to extract brand identity, voice, tone, and visual elements
for automated brand kit generation and content personalization.
"""

import asyncio
import re
import time
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Set, Tuple
from urllib.parse import urljoin, urlparse
import logging

import aiohttp
import requests
from bs4 import BeautifulSoup
from PIL import Image
import colorsys
import webcolors

from app.core.config import settings
from app.services.ai.providers import get_text_service
from app.services.ai.vector_db import get_vector_service
from app.services.ai.prompts import PromptTemplate, get_prompt_template

logger = logging.getLogger(__name__)


@dataclass
class ColorPalette:
    """Brand color palette"""
    primary: str
    secondary: str
    accent: str
    text: str
    background: str
    
    def to_dict(self) -> Dict[str, str]:
        return {
            "primary": self.primary,
            "secondary": self.secondary,
            "accent": self.accent,
            "text": self.text,
            "background": self.background
        }


@dataclass
class BrandVoice:
    """Brand voice characteristics"""
    tone: str
    personality_traits: List[str]
    dos: List[str]
    donts: List[str]
    sample_phrases: List[str]
    formality_level: str  # casual, professional, formal
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "tone": self.tone,
            "personality_traits": self.personality_traits,
            "dos": self.dos,
            "donts": self.donts,
            "sample_phrases": self.sample_phrases,
            "formality_level": self.formality_level
        }


@dataclass
class ContentPillar:
    """Content pillar/theme"""
    name: str
    description: str
    keywords: List[str]
    content_types: List[str]
    target_audience: str
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "description": self.description,
            "keywords": self.keywords,
            "content_types": self.content_types,
            "target_audience": self.target_audience
        }


@dataclass
class BrandKit:
    """Complete brand kit"""
    brand_name: str
    logo_url: Optional[str]
    website_url: str
    colors: ColorPalette
    voice: BrandVoice
    pillars: List[ContentPillar]
    industry: str
    target_audience: str
    unique_value_proposition: str
    competitors: List[str]
    metadata: Dict[str, Any]
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "brand_name": self.brand_name,
            "logo_url": self.logo_url,
            "website_url": self.website_url,
            "colors": self.colors.to_dict(),
            "voice": self.voice.to_dict(),
            "pillars": [p.to_dict() for p in self.pillars],
            "industry": self.industry,
            "target_audience": self.target_audience,
            "unique_value_proposition": self.unique_value_proposition,
            "competitors": self.competitors,
            "metadata": self.metadata
        }


class WebScraper:
    """Website content scraper with rate limiting"""
    
    def __init__(self):
        self.session = None
        self.scraped_urls: Set[str] = set()
    
    async def __aenter__(self):
        timeout = aiohttp.ClientTimeout(total=settings.SCRAPING_TIMEOUT)
        self.session = aiohttp.ClientSession(
            timeout=timeout,
            headers={"User-Agent": settings.USER_AGENT}
        )
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()
    
    async def scrape_page(self, url: str) -> Dict[str, Any]:
        """Scrape a single page"""
        if url in self.scraped_urls or len(self.scraped_urls) >= settings.MAX_PAGES_PER_DOMAIN:
            return {}
        
        try:
            async with self.session.get(url) as response:
                if response.status != 200:
                    logger.warning(f"Failed to scrape {url}: HTTP {response.status}")
                    return {}
                
                html = await response.text()
                self.scraped_urls.add(url)
                
                soup = BeautifulSoup(html, 'html.parser')
                
                # Extract text content
                text_content = self._extract_text_content(soup)
                
                # Extract metadata
                metadata = self._extract_metadata(soup)
                
                # Extract images
                images = self._extract_images(soup, url)
                
                # Extract colors from CSS
                colors = self._extract_colors(soup)
                
                return {
                    "url": url,
                    "title": soup.title.string if soup.title else "",
                    "text_content": text_content,
                    "metadata": metadata,
                    "images": images,
                    "colors": colors,
                    "links": self._extract_links(soup, url)
                }
                
        except Exception as e:
            logger.error(f"Error scraping {url}: {e}")
            return {}
    
    def _extract_text_content(self, soup: BeautifulSoup) -> str:
        """Extract clean text content from HTML"""
        # Remove script and style elements
        for script in soup(["script", "style"]):
            script.decompose()
        
        # Get text from important elements
        important_elements = soup.find_all(['h1', 'h2', 'h3', 'p', 'div', 'span', 'li'])
        text_parts = []
        
        for element in important_elements:
            text = element.get_text(strip=True)
            if text and len(text) > 10:  # Filter out very short text
                text_parts.append(text)
        
        return "\n".join(text_parts)
    
    def _extract_metadata(self, soup: BeautifulSoup) -> Dict[str, str]:
        """Extract page metadata"""
        metadata = {}
        
        # Meta description
        meta_desc = soup.find("meta", attrs={"name": "description"})
        if meta_desc:
            metadata["description"] = meta_desc.get("content", "")
        
        # Open Graph data
        og_tags = soup.find_all("meta", property=re.compile("^og:"))
        for tag in og_tags:
            property_name = tag.get("property", "").replace("og:", "")
            metadata[f"og_{property_name}"] = tag.get("content", "")
        
        # Twitter Card data
        twitter_tags = soup.find_all("meta", attrs={"name": re.compile("^twitter:")})
        for tag in twitter_tags:
            name = tag.get("name", "").replace("twitter:", "")
            metadata[f"twitter_{name}"] = tag.get("content", "")
        
        return metadata
    
    def _extract_images(self, soup: BeautifulSoup, base_url: str) -> List[Dict[str, str]]:
        """Extract image information"""
        images = []
        img_tags = soup.find_all("img")
        
        for img in img_tags[:10]:  # Limit to first 10 images
            src = img.get("src")
            if src:
                # Convert relative URLs to absolute
                if src.startswith("//"):
                    src = f"https:{src}"
                elif src.startswith("/"):
                    src = urljoin(base_url, src)
                
                images.append({
                    "src": src,
                    "alt": img.get("alt", ""),
                    "title": img.get("title", "")
                })
        
        return images
    
    def _extract_colors(self, soup: BeautifulSoup) -> List[str]:
        """Extract colors from CSS and inline styles"""
        colors = set()
        
        # Extract from style attributes
        elements_with_style = soup.find_all(attrs={"style": True})
        for element in elements_with_style:
            style = element.get("style", "")
            color_matches = re.findall(r'#[0-9a-fA-F]{6}|#[0-9a-fA-F]{3}|rgb\([^)]+\)', style)
            colors.update(color_matches)
        
        # Extract from CSS classes (limited extraction)
        style_tags = soup.find_all("style")
        for style_tag in style_tags:
            css_content = style_tag.string or ""
            color_matches = re.findall(r'#[0-9a-fA-F]{6}|#[0-9a-fA-F]{3}|rgb\([^)]+\)', css_content)
            colors.update(color_matches)
        
        return list(colors)[:20]  # Limit to 20 colors
    
    def _extract_links(self, soup: BeautifulSoup, base_url: str) -> List[str]:
        """Extract internal links for further scraping"""
        domain = urlparse(base_url).netloc
        links = []
        
        for a_tag in soup.find_all("a", href=True):
            href = a_tag["href"]
            
            # Convert to absolute URL
            if href.startswith("/"):
                href = urljoin(base_url, href)
            
            # Only include same-domain links
            if urlparse(href).netloc == domain:
                links.append(href)
        
        return list(set(links))[:20]  # Limit and deduplicate


class ColorAnalyzer:
    """Analyzes extracted colors to create brand palette"""
    
    @staticmethod
    def analyze_colors(color_strings: List[str]) -> ColorPalette:
        """Analyze colors and create a brand palette"""
        if not color_strings:
            return ColorAnalyzer._create_default_palette()
        
        # Convert color strings to RGB values
        rgb_colors = []
        for color_str in color_strings:
            rgb = ColorAnalyzer._parse_color(color_str)
            if rgb:
                rgb_colors.append(rgb)
        
        if not rgb_colors:
            return ColorAnalyzer._create_default_palette()
        
        # Analyze color frequency and properties
        color_analysis = ColorAnalyzer._analyze_color_properties(rgb_colors)
        
        # Select colors for brand palette
        primary = ColorAnalyzer._select_primary_color(color_analysis)
        secondary = ColorAnalyzer._select_secondary_color(color_analysis, primary)
        accent = ColorAnalyzer._select_accent_color(color_analysis, [primary, secondary])
        
        return ColorPalette(
            primary=ColorAnalyzer._rgb_to_hex(primary),
            secondary=ColorAnalyzer._rgb_to_hex(secondary),
            accent=ColorAnalyzer._rgb_to_hex(accent),
            text="#333333",  # Default dark text
            background="#FFFFFF"  # Default white background
        )
    
    @staticmethod
    def _parse_color(color_str: str) -> Optional[Tuple[int, int, int]]:
        """Parse color string to RGB tuple"""
        try:
            # Handle hex colors
            if color_str.startswith("#"):
                hex_color = color_str[1:]
                if len(hex_color) == 3:
                    hex_color = "".join([c*2 for c in hex_color])
                return tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))
            
            # Handle rgb() colors
            if color_str.startswith("rgb("):
                rgb_values = re.findall(r'\d+', color_str)
                if len(rgb_values) >= 3:
                    return tuple(int(rgb_values[i]) for i in range(3))
            
            # Handle named colors
            try:
                return webcolors.name_to_rgb(color_str)
            except ValueError:
                pass
            
        except (ValueError, IndexError):
            pass
        
        return None
    
    @staticmethod
    def _analyze_color_properties(rgb_colors: List[Tuple[int, int, int]]) -> Dict[str, Any]:
        """Analyze color properties like saturation, brightness, etc."""
        analysis = {
            "colors": rgb_colors,
            "hsl_colors": [],
            "dominant_hues": [],
            "saturation_levels": [],
            "brightness_levels": []
        }
        
        for r, g, b in rgb_colors:
            h, l, s = colorsys.rgb_to_hls(r/255, g/255, b/255)
            hsl = (int(h*360), int(s*100), int(l*100))
            analysis["hsl_colors"].append(hsl)
            analysis["dominant_hues"].append(hsl[0])
            analysis["saturation_levels"].append(hsl[1])
            analysis["brightness_levels"].append(hsl[2])
        
        return analysis
    
    @staticmethod
    def _select_primary_color(analysis: Dict[str, Any]) -> Tuple[int, int, int]:
        """Select primary brand color"""
        colors = analysis["colors"]
        hsl_colors = analysis["hsl_colors"]
        
        # Prefer colors with medium to high saturation and medium brightness
        scored_colors = []
        for i, (rgb, hsl) in enumerate(zip(colors, hsl_colors)):
            h, s, l = hsl
            # Score based on saturation and brightness
            score = 0
            if 30 <= s <= 90:  # Good saturation range
                score += 2
            if 20 <= l <= 80:  # Good brightness range
                score += 2
            if 200 <= h <= 260:  # Prefer blue hues for primary
                score += 1
            
            scored_colors.append((score, rgb))
        
        # Return highest scored color or first color as fallback
        if scored_colors:
            scored_colors.sort(key=lambda x: x[0], reverse=True)
            return scored_colors[0][1]
        
        return colors[0] if colors else (66, 139, 202)  # Default blue
    
    @staticmethod  
    def _select_secondary_color(analysis: Dict[str, Any], primary: Tuple[int, int, int]) -> Tuple[int, int, int]:
        """Select secondary brand color"""
        colors = analysis["colors"]
        
        # Find color most different from primary
        best_color = None
        max_distance = 0
        
        for color in colors:
            if color == primary:
                continue
            
            # Calculate color distance
            distance = sum((a - b) ** 2 for a, b in zip(color, primary)) ** 0.5
            if distance > max_distance:
                max_distance = distance
                best_color = color
        
        return best_color or (128, 128, 128)  # Default gray
    
    @staticmethod
    def _select_accent_color(analysis: Dict[str, Any], existing_colors: List[Tuple[int, int, int]]) -> Tuple[int, int, int]:
        """Select accent color"""
        colors = analysis["colors"]
        
        # Find vibrant color different from existing colors
        for color in colors:
            if color in existing_colors:
                continue
            
            r, g, b = color
            h, l, s = colorsys.rgb_to_hls(r/255, g/255, b/255)
            
            # Prefer high saturation colors for accent
            if s > 0.6:
                return color
        
        return (255, 165, 0)  # Default orange
    
    @staticmethod
    def _rgb_to_hex(rgb: Tuple[int, int, int]) -> str:
        """Convert RGB tuple to hex string"""
        return f"#{rgb[0]:02x}{rgb[1]:02x}{rgb[2]:02x}"
    
    @staticmethod
    def _create_default_palette() -> ColorPalette:
        """Create default color palette"""
        return ColorPalette(
            primary="#4285f4",
            secondary="#34a853", 
            accent="#ea4335",
            text="#333333",
            background="#ffffff"
        )


class BrandAssimilationService:
    """Main service for brand assimilation and analysis"""
    
    def __init__(self):
        self.text_service = None
        self.vector_service = None
    
    async def _get_services(self):
        """Initialize AI services"""
        if self.text_service is None:
            self.text_service = await get_text_service()
        if self.vector_service is None:
            self.vector_service = await get_vector_service()
    
    async def assimilate_brand(self, website_url: str) -> BrandKit:
        """Complete brand assimilation process"""
        await self._get_services()
        
        logger.info(f"Starting brand assimilation for {website_url}")
        
        # Step 1: Scrape website
        scraped_data = await self._scrape_website(website_url)
        
        # Step 2: Analyze content with AI
        brand_analysis = await self._analyze_brand_content(scraped_data)
        
        # Step 3: Extract colors
        colors = self._analyze_brand_colors(scraped_data)
        
        # Step 4: Generate brand voice
        voice = await self._analyze_brand_voice(scraped_data)
        
        # Step 5: Identify content pillars
        pillars = await self._identify_content_pillars(scraped_data)
        
        # Step 6: Create embeddings for brand content
        await self._create_brand_embeddings(scraped_data, brand_analysis["brand_name"])
        
        # Compile brand kit
        brand_kit = BrandKit(
            brand_name=brand_analysis["brand_name"],
            logo_url=self._extract_logo_url(scraped_data),
            website_url=website_url,
            colors=colors,
            voice=voice,
            pillars=pillars,
            industry=brand_analysis["industry"],
            target_audience=brand_analysis["target_audience"],
            unique_value_proposition=brand_analysis["unique_value_proposition"],
            competitors=brand_analysis["competitors"],
            metadata={
                "assimilation_date": time.time(),
                "pages_analyzed": len(scraped_data),
                "confidence_score": brand_analysis.get("confidence_score", 0.8)
            }
        )
        
        logger.info(f"Brand assimilation completed for {brand_analysis['brand_name']}")
        return brand_kit
    
    async def _scrape_website(self, website_url: str) -> List[Dict[str, Any]]:
        """Scrape website content"""
        scraped_pages = []
        
        async with WebScraper() as scraper:
            # Start with homepage
            homepage_data = await scraper.scrape_page(website_url)
            if homepage_data:
                scraped_pages.append(homepage_data)
                
                # Scrape additional important pages
                important_links = self._select_important_links(homepage_data.get("links", []))
                
                for link in important_links[:5]:  # Limit to 5 additional pages
                    page_data = await scraper.scrape_page(link)
                    if page_data:
                        scraped_pages.append(page_data)
                    
                    # Small delay to be respectful
                    await asyncio.sleep(1)
        
        return scraped_pages
    
    def _select_important_links(self, links: List[str]) -> List[str]:
        """Select most important links to scrape"""
        important_keywords = [
            "about", "mission", "story", "values", "team",
            "products", "services", "solutions",
            "contact", "careers", "press"
        ]
        
        scored_links = []
        for link in links:
            score = 0
            link_lower = link.lower()
            
            for keyword in important_keywords:
                if keyword in link_lower:
                    score += 1
            
            scored_links.append((score, link))
        
        # Sort by score and return top links
        scored_links.sort(key=lambda x: x[0], reverse=True)
        return [link for score, link in scored_links if score > 0]
    
    async def _analyze_brand_content(self, scraped_data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Analyze scraped content to extract brand information"""
        # Combine all text content
        all_text = "\n\n".join([
            f"Page: {page.get('title', '')}\n{page.get('text_content', '')}"
            for page in scraped_data if page.get('text_content')
        ])
        
        # Get brand analysis prompt
        analysis_prompt = await get_prompt_template("brand_analysis")
        
        # Generate analysis
        response = await self.text_service.generate(
            analysis_prompt.format(website_content=all_text[:8000]),  # Limit content length
            max_tokens=1000,
            temperature=0.3
        )
        
        if not response.success:
            logger.error(f"Brand analysis failed: {response.error}")
            return self._create_fallback_analysis(scraped_data)
        
        # Parse AI response
        try:
            # The prompt should return structured JSON
            analysis = self._parse_brand_analysis(response.content)
            analysis["confidence_score"] = 0.9 if response.success else 0.5
            return analysis
            
        except Exception as e:
            logger.error(f"Failed to parse brand analysis: {e}")
            return self._create_fallback_analysis(scraped_data)
    
    def _parse_brand_analysis(self, ai_response: str) -> Dict[str, Any]:
        """Parse AI response into structured data"""
        # This would parse the AI response based on the expected format
        # For now, providing a basic implementation
        lines = ai_response.strip().split('\n')
        analysis = {
            "brand_name": "Unknown Brand",
            "industry": "Technology",
            "target_audience": "General consumers",
            "unique_value_proposition": "Quality products and services",
            "competitors": []
        }
        
        # Simple parsing logic - in production you'd want more robust parsing
        for line in lines:
            if "Brand Name:" in line:
                analysis["brand_name"] = line.split(":", 1)[1].strip()
            elif "Industry:" in line:
                analysis["industry"] = line.split(":", 1)[1].strip()
            elif "Target Audience:" in line:
                analysis["target_audience"] = line.split(":", 1)[1].strip()
            elif "Value Proposition:" in line:
                analysis["unique_value_proposition"] = line.split(":", 1)[1].strip()
        
        return analysis
    
    def _create_fallback_analysis(self, scraped_data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Create fallback analysis when AI analysis fails"""
        # Extract brand name from first page title
        brand_name = "Unknown Brand"
        if scraped_data and scraped_data[0].get("title"):
            brand_name = scraped_data[0]["title"].split(" - ")[0].strip()
        
        return {
            "brand_name": brand_name,
            "industry": "Technology",
            "target_audience": "General consumers",
            "unique_value_proposition": "Quality products and services",
            "competitors": [],
            "confidence_score": 0.3
        }
    
    def _analyze_brand_colors(self, scraped_data: List[Dict[str, Any]]) -> ColorPalette:
        """Analyze brand colors from scraped data"""
        all_colors = []
        for page in scraped_data:
            all_colors.extend(page.get("colors", []))
        
        return ColorAnalyzer.analyze_colors(all_colors)
    
    async def _analyze_brand_voice(self, scraped_data: List[Dict[str, Any]]) -> BrandVoice:
        """Analyze brand voice and tone"""
        # Combine text content for voice analysis
        text_content = "\n".join([
            page.get("text_content", "")
            for page in scraped_data if page.get("text_content")
        ])[:6000]  # Limit length
        
        voice_prompt = await get_prompt_template("brand_voice_analysis")
        
        response = await self.text_service.generate(
            voice_prompt.format(brand_content=text_content),
            max_tokens=800,
            temperature=0.3
        )
        
        if response.success:
            return self._parse_brand_voice(response.content)
        else:
            return self._create_default_voice()
    
    def _parse_brand_voice(self, ai_response: str) -> BrandVoice:
        """Parse brand voice analysis"""
        # Basic parsing - in production, use more structured approach
        return BrandVoice(
            tone="Professional yet approachable",
            personality_traits=["Trustworthy", "Innovative", "Customer-focused"],
            dos=["Use clear, concise language", "Focus on benefits", "Be authentic"],
            donts=["Use jargon", "Make exaggerated claims", "Be overly formal"],
            sample_phrases=["We believe in quality", "Your success is our priority"],
            formality_level="professional"
        )
    
    def _create_default_voice(self) -> BrandVoice:
        """Create default brand voice"""
        return BrandVoice(
            tone="Professional",
            personality_traits=["Reliable", "Professional"],
            dos=["Be clear and concise"],
            donts=["Use complicated language"],
            sample_phrases=["Quality matters", "We deliver results"],
            formality_level="professional"
        )
    
    async def _identify_content_pillars(self, scraped_data: List[Dict[str, Any]]) -> List[ContentPillar]:
        """Identify content pillars from website analysis"""
        content = "\n".join([
            page.get("text_content", "")
            for page in scraped_data if page.get("text_content")
        ])[:5000]
        
        pillars_prompt = await get_prompt_template("content_pillars_identification")
        
        response = await self.text_service.generate(
            pillars_prompt.format(website_content=content),
            max_tokens=600,
            temperature=0.4
        )
        
        if response.success:
            return self._parse_content_pillars(response.content)
        else:
            return self._create_default_pillars()
    
    def _parse_content_pillars(self, ai_response: str) -> List[ContentPillar]:
        """Parse content pillars from AI response"""
        # Basic parsing - in production, use structured JSON response
        pillars = [
            ContentPillar(
                name="Product Education",
                description="Educational content about products and services",
                keywords=["tutorial", "guide", "how-to", "education"],
                content_types=["video", "blog", "infographic"],
                target_audience="prospects and customers"
            ),
            ContentPillar(
                name="Industry Insights",
                description="Thought leadership and industry trends",
                keywords=["trends", "insights", "analysis", "industry"],
                content_types=["article", "report", "video"],
                target_audience="industry professionals"
            )
        ]
        return pillars
    
    def _create_default_pillars(self) -> List[ContentPillar]:
        """Create default content pillars"""
        return [
            ContentPillar(
                name="Brand Story",
                description="Content showcasing brand values and mission",
                keywords=["story", "values", "mission", "culture"],
                content_types=["video", "blog", "social"],
                target_audience="general audience"
            )
        ]
    
    def _extract_logo_url(self, scraped_data: List[Dict[str, Any]]) -> Optional[str]:
        """Extract logo URL from scraped data"""
        for page in scraped_data:
            for image in page.get("images", []):
                alt_text = image.get("alt", "").lower()
                if "logo" in alt_text or "brand" in alt_text:
                    return image.get("src")
        
        # Fallback to first image if no logo found
        if scraped_data and scraped_data[0].get("images"):
            return scraped_data[0]["images"][0].get("src")
        
        return None
    
    async def _create_brand_embeddings(self, scraped_data: List[Dict[str, Any]], brand_name: str):
        """Create embeddings for brand content"""
        try:
            contents = []
            metadatas = []
            
            for page in scraped_data:
                if page.get("text_content"):
                    contents.append(page["text_content"][:2000])  # Limit length
                    metadatas.append({
                        "brand_name": brand_name,
                        "page_title": page.get("title", ""),
                        "url": page.get("url", ""),
                        "content_type": "brand_content"
                    })
            
            if contents:
                await self.vector_service.add_documents(
                    contents=contents,
                    metadatas=metadatas,
                    namespace=f"brand_{brand_name.lower().replace(' ', '_')}"
                )
                
                logger.info(f"Created {len(contents)} embeddings for {brand_name}")
                
        except Exception as e:
            logger.error(f"Failed to create brand embeddings: {e}")


# Global service instance
_brand_service: Optional[BrandAssimilationService] = None


async def get_brand_assimilation_service() -> BrandAssimilationService:
    """Get global brand assimilation service instance"""
    global _brand_service
    if _brand_service is None:
        _brand_service = BrandAssimilationService()
    return _brand_service