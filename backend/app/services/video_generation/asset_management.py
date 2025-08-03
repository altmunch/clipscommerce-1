"""
Asset management service for video generation - handles images, backgrounds, logos, and other media assets
"""

import asyncio
import hashlib
import logging
import os
import tempfile
import uuid
from io import BytesIO
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple, Union
from dataclasses import dataclass
from enum import Enum
import aiofiles
import aiohttp
from PIL import Image, ImageEnhance, ImageFilter, ImageOps
import cv2
import numpy as np

from app.core.config import settings
from app.models.product import Product
from app.models.brand import Brand

logger = logging.getLogger(__name__)


class AssetType(Enum):
    """Types of assets"""
    PRODUCT_IMAGE = "product_image"
    LOGO = "logo"
    BACKGROUND = "background"
    OVERLAY = "overlay"
    THUMBNAIL = "thumbnail"
    STOCK_PHOTO = "stock_photo"
    STOCK_VIDEO = "stock_video"
    ICON = "icon"
    FONT = "font"
    MUSIC = "music"
    SOUND_EFFECT = "sound_effect"


class ProcessingType(Enum):
    """Image processing types"""
    BACKGROUND_REMOVAL = "background_removal"
    UPSCALING = "upscaling"
    COLOR_CORRECTION = "color_correction"
    BRIGHTNESS_CONTRAST = "brightness_contrast"
    CROPPING = "cropping"
    RESIZING = "resizing"
    FILTER_APPLICATION = "filter_application"
    WATERMARK_REMOVAL = "watermark_removal"
    OBJECT_EXTRACTION = "object_extraction"


class QualityScore(Enum):
    """Image quality scoring"""
    POOR = 1
    FAIR = 2
    GOOD = 3
    EXCELLENT = 4
    PERFECT = 5


@dataclass
class AssetMetadata:
    """Metadata for an asset"""
    asset_id: str
    asset_type: AssetType
    original_url: str
    processed_url: Optional[str]
    local_path: Optional[str]
    file_size: int
    dimensions: Tuple[int, int]
    format: str
    quality_score: QualityScore
    color_palette: List[str]
    has_transparency: bool
    processing_applied: List[ProcessingType]
    created_at: float
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "asset_id": self.asset_id,
            "asset_type": self.asset_type.value,
            "original_url": self.original_url,
            "processed_url": self.processed_url,
            "file_size": self.file_size,
            "dimensions": self.dimensions,
            "format": self.format,
            "quality_score": self.quality_score.value,
            "color_palette": self.color_palette,
            "has_transparency": self.has_transparency,
            "processing_applied": [p.value for p in self.processing_applied],
            "created_at": self.created_at
        }


@dataclass
class ProcessingRequest:
    """Request for asset processing"""
    asset_id: str
    processing_types: List[ProcessingType]
    target_dimensions: Optional[Tuple[int, int]] = None
    target_format: Optional[str] = None
    quality_settings: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.quality_settings is None:
            self.quality_settings = {}


@dataclass
class StockAssetSearch:
    """Search parameters for stock assets"""
    query: str
    asset_type: AssetType
    orientation: str = "any"  # landscape, portrait, square
    min_resolution: Tuple[int, int] = (1920, 1080)
    color_scheme: Optional[str] = None
    style: Optional[str] = None
    license_type: str = "royalty_free"
    max_results: int = 20


class AssetManagementService:
    """Service for managing video generation assets"""
    
    def __init__(self):
        self.temp_dir = Path(tempfile.gettempdir()) / "viral_os_assets"
        self.temp_dir.mkdir(exist_ok=True)
        
        # Asset storage configuration
        self.storage_config = {
            "local_storage": str(self.temp_dir),
            "cloud_storage": getattr(settings, 'ASSET_STORAGE_URL', 'https://storage.viral-os.com'),
            "max_file_size": 50 * 1024 * 1024,  # 50MB
            "supported_formats": {
                "images": [".jpg", ".jpeg", ".png", ".webp", ".bmp", ".tiff"],
                "videos": [".mp4", ".mov", ".avi", ".webm"],
                "audio": [".mp3", ".wav", ".aac", ".ogg"]
            }
        }
        
        # Stock photo providers
        self.stock_providers = {
            "unsplash": {
                "api_key": getattr(settings, 'UNSPLASH_ACCESS_KEY', ''),
                "base_url": "https://api.unsplash.com",
                "rate_limit": 50  # requests per hour
            },
            "pexels": {
                "api_key": getattr(settings, 'PEXELS_API_KEY', ''),
                "base_url": "https://api.pexels.com/v1",
                "rate_limit": 200  # requests per hour
            },
            "pixabay": {
                "api_key": getattr(settings, 'PIXABAY_API_KEY', ''),
                "base_url": "https://pixabay.com/api",
                "rate_limit": 100  # requests per hour
            }
        }
        
        # Image quality assessment
        self.quality_thresholds = {
            "min_resolution": (800, 600),
            "min_file_size": 50 * 1024,  # 50KB
            "max_compression_artifacts": 0.3,
            "min_sharpness": 0.5,
            "min_brightness": 0.2,
            "max_brightness": 0.8
        }
    
    async def extract_product_assets(self, product: Product) -> List[AssetMetadata]:
        """Extract and process assets from product data"""
        
        logger.info(f"Extracting assets for product: {product.name}")
        
        assets = []
        
        # Extract product images
        if product.images:
            for i, image_url in enumerate(product.images):
                try:
                    asset = await self._process_product_image(image_url, product, i)
                    if asset:
                        assets.append(asset)
                except Exception as e:
                    logger.error(f"Failed to process product image {image_url}: {e}")
        
        # Extract images from product description/content
        description_images = await self._extract_images_from_description(product.description or "")
        for image_url in description_images:
            try:
                asset = await self._process_product_image(image_url, product, len(assets))
                if asset:
                    assets.append(asset)
            except Exception as e:
                logger.error(f"Failed to process description image {image_url}: {e}")
        
        # Rank assets by quality
        assets = await self._rank_assets_by_quality(assets)
        
        logger.info(f"Extracted {len(assets)} assets for product {product.name}")
        
        return assets
    
    async def _process_product_image(self, image_url: str, product: Product, index: int) -> Optional[AssetMetadata]:
        """Process a single product image"""
        
        # Download and analyze image
        image_data = await self._download_asset(image_url)
        if not image_data:
            return None
        
        # Analyze image quality and properties
        analysis = await self._analyze_image(image_data, image_url)
        if analysis["quality_score"] == QualityScore.POOR:
            logger.warning(f"Skipping low-quality image: {image_url}")
            return None
        
        # Apply basic processing
        processed_data = await self._apply_basic_processing(image_data, analysis)
        
        # Create asset metadata
        asset_id = f"product_{product.id}_{index}_{uuid.uuid4().hex[:8]}"
        
        # Save processed image
        processed_path = await self._save_processed_asset(processed_data, asset_id, "jpg")
        processed_url = await self._upload_to_storage(processed_path, asset_id)
        
        return AssetMetadata(
            asset_id=asset_id,
            asset_type=AssetType.PRODUCT_IMAGE,
            original_url=image_url,
            processed_url=processed_url,
            local_path=processed_path,
            file_size=len(processed_data),
            dimensions=analysis["dimensions"],
            format="jpg",
            quality_score=analysis["quality_score"],
            color_palette=analysis["color_palette"],
            has_transparency=analysis["has_transparency"],
            processing_applied=[ProcessingType.COLOR_CORRECTION, ProcessingType.BRIGHTNESS_CONTRAST],
            created_at=asyncio.get_event_loop().time()
        )
    
    async def _download_asset(self, url: str) -> Optional[bytes]:
        """Download asset from URL"""
        
        try:
            timeout = aiohttp.ClientTimeout(total=30)
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.get(url) as response:
                    if response.status == 200:
                        content_length = response.headers.get('Content-Length')
                        if content_length and int(content_length) > self.storage_config["max_file_size"]:
                            logger.warning(f"Asset too large: {url}")
                            return None
                        
                        data = await response.read()
                        return data
                    else:
                        logger.error(f"Failed to download asset {url}: HTTP {response.status}")
                        return None
        
        except Exception as e:
            logger.error(f"Error downloading asset {url}: {e}")
            return None
    
    async def _analyze_image(self, image_data: bytes, url: str) -> Dict[str, Any]:
        """Analyze image quality and properties"""
        
        try:
            # Open image with PIL
            image = Image.open(BytesIO(image_data))
            
            # Basic properties
            width, height = image.size
            format_type = image.format or "unknown"
            has_transparency = image.mode in ("RGBA", "LA") or "transparency" in image.info
            
            # Convert to RGB for analysis
            if image.mode != "RGB":
                rgb_image = image.convert("RGB")
            else:
                rgb_image = image
            
            # Quality assessment
            quality_score = await self._assess_image_quality(rgb_image, image_data)
            
            # Color palette extraction
            color_palette = await self._extract_color_palette(rgb_image)
            
            # Additional properties
            file_size = len(image_data)
            
            return {
                "dimensions": (width, height),
                "format": format_type.lower(),
                "file_size": file_size,
                "has_transparency": has_transparency,
                "quality_score": quality_score,
                "color_palette": color_palette,
                "aspect_ratio": width / height if height > 0 else 1.0
            }
            
        except Exception as e:
            logger.error(f"Failed to analyze image from {url}: {e}")
            return {
                "dimensions": (0, 0),
                "format": "unknown",
                "file_size": 0,
                "has_transparency": False,
                "quality_score": QualityScore.POOR,
                "color_palette": [],
                "aspect_ratio": 1.0
            }
    
    async def _assess_image_quality(self, image: Image.Image, image_data: bytes) -> QualityScore:
        """Assess image quality using multiple metrics"""
        
        width, height = image.size
        file_size = len(image_data)
        
        score_factors = []
        
        # Resolution check
        min_width, min_height = self.quality_thresholds["min_resolution"]
        if width >= min_width and height >= min_height:
            resolution_score = min(1.0, (width * height) / (1920 * 1080))  # Normalize to 1080p
            score_factors.append(resolution_score)
        else:
            score_factors.append(0.3)  # Low score for small images
        
        # File size check
        if file_size >= self.quality_thresholds["min_file_size"]:
            size_score = min(1.0, file_size / (500 * 1024))  # Normalize to 500KB
            score_factors.append(size_score)
        else:
            score_factors.append(0.2)
        
        # Brightness analysis
        brightness_score = await self._analyze_brightness(image)
        score_factors.append(brightness_score)
        
        # Sharpness analysis
        sharpness_score = await self._analyze_sharpness(image)
        score_factors.append(sharpness_score)
        
        # Calculate overall score
        average_score = sum(score_factors) / len(score_factors)
        
        if average_score >= 0.8:
            return QualityScore.PERFECT
        elif average_score >= 0.7:
            return QualityScore.EXCELLENT
        elif average_score >= 0.5:
            return QualityScore.GOOD
        elif average_score >= 0.3:
            return QualityScore.FAIR
        else:
            return QualityScore.POOR
    
    async def _analyze_brightness(self, image: Image.Image) -> float:
        """Analyze image brightness"""
        
        try:
            # Convert to grayscale and calculate mean brightness
            grayscale = image.convert("L")
            pixel_values = list(grayscale.getdata())
            mean_brightness = sum(pixel_values) / len(pixel_values) / 255.0
            
            # Score based on optimal brightness range
            min_brightness = self.quality_thresholds["min_brightness"]
            max_brightness = self.quality_thresholds["max_brightness"]
            
            if min_brightness <= mean_brightness <= max_brightness:
                return 1.0
            elif mean_brightness < min_brightness:
                return mean_brightness / min_brightness
            else:  # Too bright
                return max_brightness / mean_brightness
                
        except Exception as e:
            logger.error(f"Failed to analyze brightness: {e}")
            return 0.5
    
    async def _analyze_sharpness(self, image: Image.Image) -> float:
        """Analyze image sharpness using Laplacian variance"""
        
        try:
            # Convert PIL image to OpenCV format
            image_array = np.array(image)
            
            # Convert to grayscale
            if len(image_array.shape) == 3:
                gray = cv2.cvtColor(image_array, cv2.COLOR_RGB2GRAY)
            else:
                gray = image_array
            
            # Calculate Laplacian variance
            laplacian_var = cv2.Laplacian(gray, cv2.CV_64F).var()
            
            # Normalize sharpness score
            # Values typically range from 0-500+, normalize to 0-1
            normalized_score = min(1.0, laplacian_var / 100.0)
            
            return normalized_score
            
        except Exception as e:
            logger.error(f"Failed to analyze sharpness: {e}")
            return 0.5
    
    async def _extract_color_palette(self, image: Image.Image) -> List[str]:
        """Extract dominant colors from image"""
        
        try:
            # Resize image for faster processing
            small_image = image.resize((150, 150))
            
            # Get colors using quantization
            quantized = small_image.quantize(colors=8)
            palette = quantized.getpalette()
            
            # Convert palette to hex colors
            colors = []
            for i in range(0, len(palette), 3):
                r, g, b = palette[i:i+3]
                hex_color = f"#{r:02x}{g:02x}{b:02x}"
                colors.append(hex_color)
            
            return colors[:5]  # Return top 5 colors
            
        except Exception as e:
            logger.error(f"Failed to extract color palette: {e}")
            return ["#000000"]  # Return black as fallback
    
    async def _apply_basic_processing(self, image_data: bytes, analysis: Dict[str, Any]) -> bytes:
        """Apply basic image processing improvements"""
        
        try:
            image = Image.open(BytesIO(image_data))
            
            # Convert to RGB if needed
            if image.mode != "RGB":
                image = image.convert("RGB")
            
            # Apply brightness/contrast correction if needed
            brightness_score = analysis.get("brightness_score", 0.5)
            if brightness_score < 0.5:
                # Increase brightness
                enhancer = ImageEnhance.Brightness(image)
                image = enhancer.enhance(1.2)
            
            # Apply slight sharpening
            image = image.filter(ImageFilter.UnsharpMask(radius=1, percent=120, threshold=3))
            
            # Ensure minimum resolution for video use
            width, height = image.size
            min_width, min_height = 1280, 720  # Minimum for video
            
            if width < min_width or height < min_height:
                # Calculate new size maintaining aspect ratio
                aspect_ratio = width / height
                if aspect_ratio > min_width / min_height:
                    new_width = min_width
                    new_height = int(min_width / aspect_ratio)
                else:
                    new_height = min_height
                    new_width = int(min_height * aspect_ratio)
                
                image = image.resize((new_width, new_height), Image.Resampling.LANCZOS)
            
            # Save to bytes
            output = BytesIO()
            image.save(output, format="JPEG", quality=90, optimize=True)
            return output.getvalue()
            
        except Exception as e:
            logger.error(f"Failed to process image: {e}")
            return image_data  # Return original if processing fails
    
    async def _save_processed_asset(self, asset_data: bytes, asset_id: str, format_ext: str) -> str:
        """Save processed asset to local storage"""
        
        filename = f"{asset_id}.{format_ext}"
        file_path = self.temp_dir / filename
        
        async with aiofiles.open(file_path, 'wb') as f:
            await f.write(asset_data)
        
        return str(file_path)
    
    async def _upload_to_storage(self, file_path: str, asset_id: str) -> str:
        """Upload asset to cloud storage (mock implementation)"""
        
        # Mock implementation - in production would upload to S3/GCS/etc.
        cloud_url = f"{self.storage_config['cloud_storage']}/assets/{asset_id}.jpg"
        
        # Simulate upload delay
        await asyncio.sleep(0.5)
        
        logger.info(f"Uploaded asset to: {cloud_url}")
        return cloud_url
    
    async def _extract_images_from_description(self, description: str) -> List[str]:
        """Extract image URLs from product description"""
        
        import re
        
        # Simple regex to find image URLs
        url_pattern = r'https?://[^\s<>"]+\.(?:jpg|jpeg|png|gif|webp)'
        urls = re.findall(url_pattern, description, re.IGNORECASE)
        
        return urls
    
    async def _rank_assets_by_quality(self, assets: List[AssetMetadata]) -> List[AssetMetadata]:
        """Rank assets by quality and suitability for video"""
        
        def quality_score(asset: AssetMetadata) -> float:
            score = asset.quality_score.value * 0.4  # Base quality score
            
            # Resolution bonus
            width, height = asset.dimensions
            resolution_score = min(1.0, (width * height) / (1920 * 1080))
            score += resolution_score * 0.3
            
            # Aspect ratio preference (closer to 16:9 or 9:16 is better)
            aspect_ratio = width / height if height > 0 else 1.0
            target_ratios = [16/9, 9/16, 1.0]  # Landscape, portrait, square
            ratio_score = max(1 - abs(aspect_ratio - target) / target for target in target_ratios)
            score += ratio_score * 0.2
            
            # File size consideration (larger is generally better, up to a point)
            size_score = min(1.0, asset.file_size / (1024 * 1024))  # Normalize to 1MB
            score += size_score * 0.1
            
            return score
        
        # Sort by quality score descending
        return sorted(assets, key=quality_score, reverse=True)
    
    async def search_stock_assets(self, search: StockAssetSearch) -> List[AssetMetadata]:
        """Search for stock assets from multiple providers"""
        
        logger.info(f"Searching for stock {search.asset_type.value}: {search.query}")
        
        all_assets = []
        
        # Search each provider
        for provider_name, provider_config in self.stock_providers.items():
            if not provider_config["api_key"]:
                continue
            
            try:
                provider_assets = await self._search_provider(provider_name, search)
                all_assets.extend(provider_assets)
                
                # Respect rate limits
                await asyncio.sleep(3600 / provider_config["rate_limit"])  # Sleep to stay under rate limit
                
            except Exception as e:
                logger.error(f"Failed to search {provider_name}: {e}")
        
        # Rank and return best results
        ranked_assets = await self._rank_assets_by_quality(all_assets)
        return ranked_assets[:search.max_results]
    
    async def _search_provider(self, provider_name: str, search: StockAssetSearch) -> List[AssetMetadata]:
        """Search a specific stock photo provider"""
        
        provider_config = self.stock_providers[provider_name]
        
        if provider_name == "unsplash":
            return await self._search_unsplash(search, provider_config)
        elif provider_name == "pexels":
            return await self._search_pexels(search, provider_config)
        elif provider_name == "pixabay":
            return await self._search_pixabay(search, provider_config)
        else:
            return []
    
    async def _search_unsplash(self, search: StockAssetSearch, config: Dict[str, Any]) -> List[AssetMetadata]:
        """Search Unsplash for stock photos"""
        
        if search.asset_type != AssetType.STOCK_PHOTO:
            return []
        
        headers = {"Authorization": f"Client-ID {config['api_key']}"}
        params = {
            "query": search.query,
            "per_page": min(30, search.max_results),
            "orientation": search.orientation if search.orientation != "any" else "landscape"
        }
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(f"{config['base_url']}/search/photos", headers=headers, params=params) as response:
                    if response.status == 200:
                        data = await response.json()
                        
                        assets = []
                        for photo in data.get("results", []):
                            asset = await self._create_stock_asset_metadata(photo, "unsplash", AssetType.STOCK_PHOTO)
                            if asset:
                                assets.append(asset)
                        
                        return assets
                    else:
                        logger.error(f"Unsplash search failed: HTTP {response.status}")
                        return []
        
        except Exception as e:
            logger.error(f"Unsplash search error: {e}")
            return []
    
    async def _search_pexels(self, search: StockAssetSearch, config: Dict[str, Any]) -> List[AssetMetadata]:
        """Search Pexels for stock photos and videos"""
        
        headers = {"Authorization": config['api_key']}
        params = {
            "query": search.query,
            "per_page": min(80, search.max_results),
            "orientation": search.orientation if search.orientation != "any" else "landscape"
        }
        
        endpoint = "search/videos" if search.asset_type == AssetType.STOCK_VIDEO else "search"
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(f"{config['base_url']}/{endpoint}", headers=headers, params=params) as response:
                    if response.status == 200:
                        data = await response.json()
                        
                        assets = []
                        results_key = "videos" if search.asset_type == AssetType.STOCK_VIDEO else "photos"
                        
                        for item in data.get(results_key, []):
                            asset = await self._create_stock_asset_metadata(item, "pexels", search.asset_type)
                            if asset:
                                assets.append(asset)
                        
                        return assets
                    else:
                        logger.error(f"Pexels search failed: HTTP {response.status}")
                        return []
        
        except Exception as e:
            logger.error(f"Pexels search error: {e}")
            return []
    
    async def _search_pixabay(self, search: StockAssetSearch, config: Dict[str, Any]) -> List[AssetMetadata]:
        """Search Pixabay for stock media"""
        
        media_type = "video" if search.asset_type == AssetType.STOCK_VIDEO else "photo"
        
        params = {
            "key": config['api_key'],
            "q": search.query,
            "image_type": "photo",
            "orientation": search.orientation if search.orientation != "any" else "all",
            "category": "all",
            "min_width": search.min_resolution[0],
            "min_height": search.min_resolution[1],
            "per_page": min(200, search.max_results),
            "safesearch": "true"
        }
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(f"{config['base_url']}/", params=params) as response:
                    if response.status == 200:
                        data = await response.json()
                        
                        assets = []
                        for item in data.get("hits", []):
                            asset = await self._create_stock_asset_metadata(item, "pixabay", search.asset_type)
                            if asset:
                                assets.append(asset)
                        
                        return assets
                    else:
                        logger.error(f"Pixabay search failed: HTTP {response.status}")
                        return []
        
        except Exception as e:
            logger.error(f"Pixabay search error: {e}")
            return []
    
    async def _create_stock_asset_metadata(self, item_data: Dict[str, Any], provider: str, asset_type: AssetType) -> Optional[AssetMetadata]:
        """Create asset metadata from stock provider response"""
        
        try:
            asset_id = f"{provider}_{item_data.get('id', uuid.uuid4().hex)}"
            
            # Extract URL based on provider
            if provider == "unsplash":
                url = item_data["urls"]["regular"]
                width = item_data["width"]
                height = item_data["height"]
            elif provider == "pexels":
                if asset_type == AssetType.STOCK_VIDEO:
                    url = item_data["video_files"][0]["link"] if item_data.get("video_files") else ""
                    width = item_data["width"]
                    height = item_data["height"]
                else:
                    url = item_data["src"]["large"]
                    width = item_data["width"]
                    height = item_data["height"]
            elif provider == "pixabay":
                url = item_data["largeImageURL"] if asset_type == AssetType.STOCK_PHOTO else item_data.get("videos", {}).get("large", {}).get("url", "")
                width = item_data["imageWidth"]
                height = item_data["imageHeight"]
            else:
                return None
            
            if not url:
                return None
            
            # Estimate quality based on resolution
            total_pixels = width * height
            if total_pixels >= 1920 * 1080:
                quality = QualityScore.EXCELLENT
            elif total_pixels >= 1280 * 720:
                quality = QualityScore.GOOD
            else:
                quality = QualityScore.FAIR
            
            return AssetMetadata(
                asset_id=asset_id,
                asset_type=asset_type,
                original_url=url,
                processed_url=None,
                local_path=None,
                file_size=0,  # Unknown for stock assets
                dimensions=(width, height),
                format="jpg" if asset_type == AssetType.STOCK_PHOTO else "mp4",
                quality_score=quality,
                color_palette=[],
                has_transparency=False,
                processing_applied=[],
                created_at=asyncio.get_event_loop().time()
            )
            
        except Exception as e:
            logger.error(f"Failed to create asset metadata from {provider}: {e}")
            return None
    
    async def process_brand_assets(self, brand: Brand) -> Dict[str, AssetMetadata]:
        """Process brand assets (logo, colors, fonts)"""
        
        logger.info(f"Processing brand assets for: {brand.name}")
        
        brand_assets = {}
        
        # Process brand logo
        if hasattr(brand, 'logo_url') and brand.logo_url:
            try:
                logo_asset = await self._process_brand_logo(brand.logo_url, brand)
                if logo_asset:
                    brand_assets["logo"] = logo_asset
            except Exception as e:
                logger.error(f"Failed to process brand logo: {e}")
        
        # Process brand guidelines
        if hasattr(brand, 'brand_guidelines') and brand.brand_guidelines:
            guidelines = brand.brand_guidelines
            if isinstance(guidelines, dict):
                
                # Extract color palette
                colors = guidelines.get("colors", {})
                if colors:
                    brand_assets["color_palette"] = self._create_color_palette_asset(colors, brand)
                
                # Extract fonts
                fonts = guidelines.get("fonts", {})
                if fonts:
                    brand_assets["typography"] = self._create_typography_asset(fonts, brand)
        
        return brand_assets
    
    async def _process_brand_logo(self, logo_url: str, brand: Brand) -> Optional[AssetMetadata]:
        """Process brand logo for video use"""
        
        # Download logo
        logo_data = await self._download_asset(logo_url)
        if not logo_data:
            return None
        
        # Analyze logo
        analysis = await self._analyze_image(logo_data, logo_url)
        
        # Process logo for video overlay use
        processed_data = await self._process_logo_for_overlay(logo_data, analysis)
        
        # Create asset metadata
        asset_id = f"brand_logo_{brand.id}_{uuid.uuid4().hex[:8]}"
        
        # Save processed logo
        processed_path = await self._save_processed_asset(processed_data, asset_id, "png")
        processed_url = await self._upload_to_storage(processed_path, asset_id)
        
        return AssetMetadata(
            asset_id=asset_id,
            asset_type=AssetType.LOGO,
            original_url=logo_url,
            processed_url=processed_url,
            local_path=processed_path,
            file_size=len(processed_data),
            dimensions=analysis["dimensions"],
            format="png",
            quality_score=analysis["quality_score"],
            color_palette=analysis["color_palette"],
            has_transparency=True,  # Processed logos should have transparency
            processing_applied=[ProcessingType.BACKGROUND_REMOVAL, ProcessingType.RESIZING],
            created_at=asyncio.get_event_loop().time()
        )
    
    async def _process_logo_for_overlay(self, logo_data: bytes, analysis: Dict[str, Any]) -> bytes:
        """Process logo for video overlay use"""
        
        try:
            image = Image.open(BytesIO(logo_data))
            
            # Convert to RGBA for transparency
            if image.mode != "RGBA":
                image = image.convert("RGBA")
            
            # Remove background if it's not transparent
            if not analysis["has_transparency"]:
                # Simple background removal (in production would use more sophisticated methods)
                image = await self._remove_background_simple(image)
            
            # Resize to reasonable overlay size
            max_size = 300  # Max 300px for overlay
            width, height = image.size
            
            if width > max_size or height > max_size:
                ratio = min(max_size / width, max_size / height)
                new_width = int(width * ratio)
                new_height = int(height * ratio)
                image = image.resize((new_width, new_height), Image.Resampling.LANCZOS)
            
            # Save as PNG with transparency
            output = BytesIO()
            image.save(output, format="PNG", optimize=True)
            return output.getvalue()
            
        except Exception as e:
            logger.error(f"Failed to process logo: {e}")
            return logo_data
    
    async def _remove_background_simple(self, image: Image.Image) -> Image.Image:
        """Simple background removal (placeholder for more sophisticated methods)"""
        
        # This is a simplified implementation
        # In production, would use rembg, DeepLab, or similar
        
        try:
            # Convert to array for processing
            img_array = np.array(image)
            
            # Simple threshold-based background removal
            # Assumes background is white or near-white
            mask = np.all(img_array[:, :, :3] > 240, axis=2)
            
            # Create alpha channel
            alpha = np.where(mask, 0, 255).astype(np.uint8)
            
            # Add alpha channel
            rgba_array = np.dstack((img_array[:, :, :3], alpha))
            
            return Image.fromarray(rgba_array, 'RGBA')
            
        except Exception as e:
            logger.error(f"Background removal failed: {e}")
            return image
    
    def _create_color_palette_asset(self, colors: Dict[str, str], brand: Brand) -> AssetMetadata:
        """Create color palette asset from brand colors"""
        
        asset_id = f"brand_colors_{brand.id}"
        
        return AssetMetadata(
            asset_id=asset_id,
            asset_type=AssetType.OVERLAY,
            original_url="",
            processed_url="",
            local_path="",
            file_size=0,
            dimensions=(0, 0),
            format="json",
            quality_score=QualityScore.PERFECT,
            color_palette=list(colors.values()),
            has_transparency=False,
            processing_applied=[],
            created_at=asyncio.get_event_loop().time()
        )
    
    def _create_typography_asset(self, fonts: Dict[str, str], brand: Brand) -> AssetMetadata:
        """Create typography asset from brand fonts"""
        
        asset_id = f"brand_fonts_{brand.id}"
        
        return AssetMetadata(
            asset_id=asset_id,
            asset_type=AssetType.FONT,
            original_url="",
            processed_url="",
            local_path="",
            file_size=0,
            dimensions=(0, 0),
            format="json",
            quality_score=QualityScore.PERFECT,
            color_palette=[],
            has_transparency=False,
            processing_applied=[],
            created_at=asyncio.get_event_loop().time()
        )
    
    async def cleanup_temp_assets(self, max_age_hours: int = 24):
        """Clean up temporary assets older than specified hours"""
        
        try:
            import time
            current_time = time.time()
            max_age_seconds = max_age_hours * 3600
            
            deleted_count = 0
            for file_path in self.temp_dir.iterdir():
                if file_path.is_file():
                    file_age = current_time - file_path.stat().st_mtime
                    if file_age > max_age_seconds:
                        file_path.unlink()
                        deleted_count += 1
            
            logger.info(f"Cleaned up {deleted_count} temporary assets")
            
        except Exception as e:
            logger.error(f"Failed to cleanup temp assets: {e}")


# Global service instance
_asset_management_service: Optional[AssetManagementService] = None


def get_asset_management_service() -> AssetManagementService:
    """Get global asset management service instance"""
    global _asset_management_service
    if _asset_management_service is None:
        _asset_management_service = AssetManagementService()
    return _asset_management_service