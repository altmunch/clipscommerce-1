"""
CapCut AI Client

Integrates with CapCut's video generation and editing capabilities.
Includes API client and browser automation fallback for comprehensive video production.
"""

import asyncio
import json
import os
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple, Union
import logging
from urllib.parse import urljoin
import hashlib
import base64

import aiohttp
import aiofiles
from playwright.async_api import async_playwright, Page, Browser, BrowserContext
from PIL import Image
import requests

from app.core.config import settings
from app.services.ai.video_generation import VideoQuality, VideoStyle, GenerationStatus

logger = logging.getLogger(__name__)


class CapCutVideoFormat(str, Enum):
    """CapCut video format options"""
    TIKTOK_VERTICAL = "9:16"  # 1080x1920
    INSTAGRAM_SQUARE = "1:1"  # 1080x1080
    INSTAGRAM_STORY = "9:16"  # 1080x1920
    YOUTUBE_SHORTS = "9:16"   # 1080x1920
    YOUTUBE_LANDSCAPE = "16:9"  # 1920x1080
    CUSTOM = "custom"


class CapCutTemplateCategory(str, Enum):
    """CapCut template categories"""
    UNBOXING = "unboxing"
    BEFORE_AFTER = "before_after"
    TUTORIAL = "tutorial"
    PRODUCT_SHOWCASE = "product_showcase"
    LIFESTYLE = "lifestyle"
    TESTIMONIAL = "testimonial"
    TRENDING = "trending"
    INDUSTRY_SPECIFIC = "industry_specific"


class CapCutAssetType(str, Enum):
    """CapCut asset types"""
    IMAGE = "image"
    VIDEO = "video"
    AUDIO = "audio"
    TEXT = "text"
    LOGO = "logo"
    STICKER = "sticker"
    EFFECT = "effect"


@dataclass
class CapCutAsset:
    """CapCut asset for video generation"""
    asset_id: str
    asset_type: CapCutAssetType
    url: str
    title: str
    duration: Optional[float] = None
    width: Optional[int] = None
    height: Optional[int] = None
    file_size: Optional[int] = None
    format: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "asset_id": self.asset_id,
            "asset_type": self.asset_type,
            "url": self.url,
            "title": self.title,
            "duration": self.duration,
            "width": self.width,
            "height": self.height,
            "file_size": self.file_size,
            "format": self.format,
            "metadata": self.metadata
        }


@dataclass
class CapCutVideoRequest:
    """CapCut video generation request"""
    title: str
    template_id: str
    assets: List[CapCutAsset]
    format: CapCutVideoFormat
    quality: VideoQuality
    duration: float
    script_text: Optional[str] = None
    background_music: Optional[str] = None
    brand_colors: List[str] = field(default_factory=list)
    brand_fonts: List[str] = field(default_factory=list)
    captions_enabled: bool = True
    auto_subtitle: bool = True
    effects: List[str] = field(default_factory=list)
    transitions: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "title": self.title,
            "template_id": self.template_id,
            "assets": [asset.to_dict() for asset in self.assets],
            "format": self.format,
            "quality": self.quality,
            "duration": self.duration,
            "script_text": self.script_text,
            "background_music": self.background_music,
            "brand_colors": self.brand_colors,
            "brand_fonts": self.brand_fonts,
            "captions_enabled": self.captions_enabled,
            "auto_subtitle": self.auto_subtitle,
            "effects": self.effects,
            "transitions": self.transitions
        }


@dataclass
class CapCutVideoResponse:
    """CapCut video generation response"""
    project_id: str
    status: GenerationStatus
    video_url: Optional[str] = None
    thumbnail_url: Optional[str] = None
    preview_url: Optional[str] = None
    download_url: Optional[str] = None
    duration: Optional[float] = None
    file_size: Optional[int] = None
    format: Optional[str] = None
    quality: Optional[VideoQuality] = None
    progress: float = 0.0
    error_message: Optional[str] = None
    cost: float = 0.0
    generation_time: Optional[float] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "project_id": self.project_id,
            "status": self.status,
            "video_url": self.video_url,
            "thumbnail_url": self.thumbnail_url,
            "preview_url": self.preview_url,
            "download_url": self.download_url,
            "duration": self.duration,
            "file_size": self.file_size,
            "format": self.format,
            "quality": self.quality,
            "progress": self.progress,
            "error_message": self.error_message,
            "cost": self.cost,
            "generation_time": self.generation_time,
            "metadata": self.metadata
        }


class CapCutAPIClient:
    """CapCut API client for video generation"""
    
    def __init__(self):
        self.api_key = getattr(settings, 'CAPCUT_API_KEY', '')
        self.api_secret = getattr(settings, 'CAPCUT_API_SECRET', '')
        self.base_url = getattr(settings, 'CAPCUT_API_URL', 'https://api.capcut.com/v1')
        self.session: Optional[aiohttp.ClientSession] = None
        
        # Rate limiting
        self.rate_limit_semaphore = asyncio.Semaphore(5)  # 5 concurrent requests
        self.last_request_time = 0.0
        self.min_request_interval = 1.0  # 1 second between requests
        
        if not self.api_key:
            logger.warning("CapCut API key not configured - will use browser automation")
    
    async def __aenter__(self):
        timeout = aiohttp.ClientTimeout(total=300)  # 5 minute timeout
        self.session = aiohttp.ClientSession(
            timeout=timeout,
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
                "User-Agent": "ViralOS/1.0"
            }
        )
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()
    
    async def _rate_limit(self):
        """Apply rate limiting"""
        async with self.rate_limit_semaphore:
            current_time = time.time()
            time_since_last = current_time - self.last_request_time
            if time_since_last < self.min_request_interval:
                await asyncio.sleep(self.min_request_interval - time_since_last)
            self.last_request_time = time.time()
    
    async def _make_request(
        self, 
        method: str, 
        endpoint: str, 
        data: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Make authenticated API request"""
        await self._rate_limit()
        
        url = urljoin(self.base_url, endpoint)
        
        try:
            if method.upper() == "GET":
                async with self.session.get(url, params=data) as response:
                    response.raise_for_status()
                    return await response.json()
            else:
                async with self.session.request(method, url, json=data) as response:
                    response.raise_for_status()
                    return await response.json()
                    
        except aiohttp.ClientError as e:
            logger.error(f"CapCut API request failed: {e}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error in CapCut API request: {e}")
            raise
    
    async def create_video_project(
        self, 
        request: CapCutVideoRequest
    ) -> CapCutVideoResponse:
        """Create new video project"""
        
        if not self.api_key:
            raise ValueError("CapCut API key not configured")
        
        project_data = request.to_dict()
        
        try:
            response_data = await self._make_request(
                "POST", 
                "/projects", 
                project_data
            )
            
            return CapCutVideoResponse(
                project_id=response_data["project_id"],
                status=GenerationStatus.PENDING,
                progress=0.0,
                metadata=response_data.get("metadata", {})
            )
            
        except Exception as e:
            logger.error(f"Failed to create CapCut project: {e}")
            return CapCutVideoResponse(
                project_id=str(uuid.uuid4()),
                status=GenerationStatus.FAILED,
                error_message=str(e)
            )
    
    async def get_project_status(self, project_id: str) -> CapCutVideoResponse:
        """Get project generation status"""
        
        try:
            response_data = await self._make_request(
                "GET", 
                f"/projects/{project_id}"
            )
            
            # Map API status to our enum
            api_status = response_data.get("status", "pending")
            status_mapping = {
                "pending": GenerationStatus.PENDING,
                "processing": GenerationStatus.IN_PROGRESS,
                "completed": GenerationStatus.COMPLETED,
                "failed": GenerationStatus.FAILED,
                "cancelled": GenerationStatus.CANCELLED
            }
            
            status = status_mapping.get(api_status, GenerationStatus.PENDING)
            
            return CapCutVideoResponse(
                project_id=project_id,
                status=status,
                video_url=response_data.get("video_url"),
                thumbnail_url=response_data.get("thumbnail_url"),
                preview_url=response_data.get("preview_url"),
                download_url=response_data.get("download_url"),
                duration=response_data.get("duration"),
                file_size=response_data.get("file_size"),
                format=response_data.get("format"),
                progress=response_data.get("progress", 0.0),
                error_message=response_data.get("error_message"),
                cost=response_data.get("cost", 0.0),
                generation_time=response_data.get("generation_time"),
                metadata=response_data.get("metadata", {})
            )
            
        except Exception as e:
            logger.error(f"Failed to get CapCut project status: {e}")
            return CapCutVideoResponse(
                project_id=project_id,
                status=GenerationStatus.FAILED,
                error_message=str(e)
            )
    
    async def list_templates(
        self, 
        category: Optional[CapCutTemplateCategory] = None,
        industry: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """List available video templates"""
        
        params = {}
        if category:
            params["category"] = category
        if industry:
            params["industry"] = industry
        
        try:
            response_data = await self._make_request("GET", "/templates", params)
            return response_data.get("templates", [])
            
        except Exception as e:
            logger.error(f"Failed to list CapCut templates: {e}")
            return []
    
    async def upload_asset(
        self, 
        file_path: str, 
        asset_type: CapCutAssetType
    ) -> Optional[CapCutAsset]:
        """Upload asset to CapCut"""
        
        try:
            # Read file
            async with aiofiles.open(file_path, 'rb') as f:
                file_data = await f.read()
            
            # Get file info
            file_name = os.path.basename(file_path)
            file_size = len(file_data)
            
            # Upload file
            form_data = aiohttp.FormData()
            form_data.add_field('file', file_data, filename=file_name)
            form_data.add_field('asset_type', asset_type)
            
            # Override content type for file upload
            headers = self.session.headers.copy()
            del headers['Content-Type']  # Let aiohttp set multipart content type
            
            async with self.session.post(
                urljoin(self.base_url, "/assets/upload"),
                data=form_data,
                headers=headers
            ) as response:
                response.raise_for_status()
                response_data = await response.json()
            
            return CapCutAsset(
                asset_id=response_data["asset_id"],
                asset_type=asset_type,
                url=response_data["url"],
                title=file_name,
                file_size=file_size,
                format=os.path.splitext(file_name)[1].lower(),
                metadata=response_data.get("metadata", {})
            )
            
        except Exception as e:
            logger.error(f"Failed to upload asset to CapCut: {e}")
            return None
    
    async def download_video(
        self, 
        download_url: str, 
        output_path: str
    ) -> bool:
        """Download generated video"""
        
        try:
            async with self.session.get(download_url) as response:
                response.raise_for_status()
                
                async with aiofiles.open(output_path, 'wb') as f:
                    async for chunk in response.content.iter_chunked(8192):
                        await f.write(chunk)
                
                logger.info(f"Video downloaded: {output_path}")
                return True
                
        except Exception as e:
            logger.error(f"Failed to download video: {e}")
            return False


class CapCutBrowserAutomation:
    """Browser automation fallback for CapCut when API is not available"""
    
    def __init__(self):
        self.browser: Optional[Browser] = None
        self.context: Optional[BrowserContext] = None
        self.page: Optional[Page] = None
        self.capcut_url = "https://www.capcut.com/"
        
        # Automation settings
        self.headless = getattr(settings, 'CAPCUT_HEADLESS', True)
        self.viewport = {
            "width": getattr(settings, 'PLAYWRIGHT_VIEWPORT_WIDTH', 1920),
            "height": getattr(settings, 'PLAYWRIGHT_VIEWPORT_HEIGHT', 1080)
        }
        self.timeout = getattr(settings, 'CAPCUT_TIMEOUT', 60000)
    
    async def __aenter__(self):
        self.playwright = await async_playwright().start()
        
        # Launch browser with stealth settings
        self.browser = await self.playwright.chromium.launch(
            headless=self.headless,
            args=[
                "--no-sandbox",
                "--disable-setuid-sandbox",
                "--disable-dev-shm-usage",
                "--disable-accelerated-2d-canvas",
                "--no-first-run",
                "--no-zygote",
                "--disable-gpu"
            ]
        )
        
        # Create context with realistic settings
        self.context = await self.browser.new_context(
            viewport=self.viewport,
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36"
        )
        
        # Create page
        self.page = await self.context.new_page()
        
        # Set reasonable timeouts
        self.page.set_default_timeout(self.timeout)
        
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.page:
            await self.page.close()
        if self.context:
            await self.context.close()
        if self.browser:
            await self.browser.close()
        if hasattr(self, 'playwright'):
            await self.playwright.stop()
    
    async def login(self, email: str, password: str) -> bool:
        """Login to CapCut"""
        
        try:
            await self.page.goto(self.capcut_url)
            await self.page.wait_for_load_state("networkidle")
            
            # Look for login button
            login_selector = "text=Log in"
            await self.page.wait_for_selector(login_selector, timeout=10000)
            await self.page.click(login_selector)
            
            # Fill login form
            await self.page.fill("input[type='email']", email)
            await self.page.fill("input[type='password']", password)
            
            # Submit login
            await self.page.click("button[type='submit']")
            
            # Wait for redirect/login success
            await self.page.wait_for_url("**/workspace**", timeout=30000)
            
            logger.info("Successfully logged in to CapCut")
            return True
            
        except Exception as e:
            logger.error(f"Failed to login to CapCut: {e}")
            return False
    
    async def create_project_from_template(
        self,
        template_id: str,
        assets: List[CapCutAsset],
        project_title: str
    ) -> Optional[str]:
        """Create project from template using browser automation"""
        
        try:
            # Navigate to templates
            await self.page.goto(f"{self.capcut_url}templates")
            await self.page.wait_for_load_state("networkidle")
            
            # Search for template
            search_selector = "input[placeholder*='Search templates']"
            await self.page.wait_for_selector(search_selector)
            await self.page.fill(search_selector, template_id)
            await self.page.press(search_selector, "Enter")
            
            # Wait for search results
            await self.page.wait_for_timeout(3000)
            
            # Click first template result
            template_selector = ".template-card:first-child"
            await self.page.wait_for_selector(template_selector)
            await self.page.click(template_selector)
            
            # Click "Use template" button
            use_template_selector = "text=Use template"
            await self.page.wait_for_selector(use_template_selector)
            await self.page.click(use_template_selector)
            
            # Wait for editor to load
            await self.page.wait_for_selector(".editor-workspace", timeout=30000)
            
            # Replace assets if provided
            if assets:
                await self._replace_template_assets(assets)
            
            # Set project title
            if project_title:
                await self._set_project_title(project_title)
            
            # Get project ID from URL
            current_url = self.page.url
            project_id = current_url.split("/")[-1] if "/" in current_url else str(uuid.uuid4())
            
            logger.info(f"Created CapCut project: {project_id}")
            return project_id
            
        except Exception as e:
            logger.error(f"Failed to create CapCut project: {e}")
            return None
    
    async def _replace_template_assets(self, assets: List[CapCutAsset]):
        """Replace template assets with custom assets"""
        
        try:
            # Look for asset replacement areas
            media_slots = await self.page.query_selector_all(".media-slot")
            
            for i, asset in enumerate(assets[:len(media_slots)]):
                if asset.asset_type == CapCutAssetType.IMAGE:
                    await self._upload_image_asset(media_slots[i], asset)
                elif asset.asset_type == CapCutAssetType.VIDEO:
                    await self._upload_video_asset(media_slots[i], asset)
                    
        except Exception as e:
            logger.error(f"Failed to replace template assets: {e}")
    
    async def _upload_image_asset(self, slot_element, asset: CapCutAsset):
        """Upload image asset to slot"""
        
        try:
            # Click on media slot
            await slot_element.click()
            
            # Look for upload button
            upload_selector = "text=Upload"
            await self.page.wait_for_selector(upload_selector, timeout=5000)
            await self.page.click(upload_selector)
            
            # Handle file upload
            async with self.page.expect_file_chooser() as fc_info:
                await self.page.click("input[type='file']")
            file_chooser = await fc_info.value
            
            # Download asset locally first if it's a URL
            local_path = await self._download_asset_locally(asset)
            if local_path:
                await file_chooser.set_files(local_path)
                
        except Exception as e:
            logger.error(f"Failed to upload image asset: {e}")
    
    async def _upload_video_asset(self, slot_element, asset: CapCutAsset):
        """Upload video asset to slot"""
        
        try:
            # Similar to image upload but for video
            await slot_element.click()
            
            upload_selector = "text=Upload video"
            await self.page.wait_for_selector(upload_selector, timeout=5000)
            await self.page.click(upload_selector)
            
            async with self.page.expect_file_chooser() as fc_info:
                await self.page.click("input[type='file'][accept*='video']")
            file_chooser = await fc_info.value
            
            local_path = await self._download_asset_locally(asset)
            if local_path:
                await file_chooser.set_files(local_path)
                
        except Exception as e:
            logger.error(f"Failed to upload video asset: {e}")
    
    async def _download_asset_locally(self, asset: CapCutAsset) -> Optional[str]:
        """Download asset URL to local temp file"""
        
        try:
            # Create temp directory
            temp_dir = "/tmp/capcut_assets"
            os.makedirs(temp_dir, exist_ok=True)
            
            # Generate local filename
            file_ext = asset.format or ".jpg"
            local_filename = f"{asset.asset_id}{file_ext}"
            local_path = os.path.join(temp_dir, local_filename)
            
            # Download file
            async with aiohttp.ClientSession() as session:
                async with session.get(asset.url) as response:
                    response.raise_for_status()
                    
                    async with aiofiles.open(local_path, 'wb') as f:
                        async for chunk in response.content.iter_chunked(8192):
                            await f.write(chunk)
            
            return local_path
            
        except Exception as e:
            logger.error(f"Failed to download asset locally: {e}")
            return None
    
    async def _set_project_title(self, title: str):
        """Set project title"""
        
        try:
            # Look for project title input
            title_selector = "input[placeholder*='Untitled']"
            await self.page.wait_for_selector(title_selector, timeout=5000)
            
            # Clear and set new title
            await self.page.fill(title_selector, title)
            await self.page.press(title_selector, "Enter")
            
        except Exception as e:
            logger.error(f"Failed to set project title: {e}")
    
    async def export_video(
        self,
        quality: VideoQuality = VideoQuality.HIGH,
        format: CapCutVideoFormat = CapCutVideoFormat.TIKTOK_VERTICAL
    ) -> Optional[str]:
        """Export video and get download URL"""
        
        try:
            # Click export button
            export_selector = "text=Export"
            await self.page.wait_for_selector(export_selector)
            await self.page.click(export_selector)
            
            # Set quality settings
            quality_mapping = {
                VideoQuality.LOW: "480p",
                VideoQuality.MEDIUM: "720p", 
                VideoQuality.HIGH: "1080p",
                VideoQuality.ULTRA: "4K"
            }
            
            quality_text = quality_mapping.get(quality, "1080p")
            await self.page.click(f"text={quality_text}")
            
            # Set format if needed
            if format != CapCutVideoFormat.TIKTOK_VERTICAL:
                await self._set_export_format(format)
            
            # Start export
            start_export_selector = "text=Start export"
            await self.page.click(start_export_selector)
            
            # Wait for export completion (with timeout)
            export_complete_selector = "text=Export complete"
            await self.page.wait_for_selector(export_complete_selector, timeout=300000)  # 5 minutes
            
            # Get download link
            download_selector = "text=Download"
            await self.page.wait_for_selector(download_selector)
            
            # Get download URL from the download button
            download_element = await self.page.query_selector(download_selector)
            download_url = await download_element.get_attribute("href")
            
            logger.info("Video export completed successfully")
            return download_url
            
        except Exception as e:
            logger.error(f"Failed to export video: {e}")
            return None
    
    async def _set_export_format(self, format: CapCutVideoFormat):
        """Set export format"""
        
        try:
            format_selector = "text=Format"
            await self.page.click(format_selector)
            
            format_mapping = {
                CapCutVideoFormat.TIKTOK_VERTICAL: "9:16",
                CapCutVideoFormat.INSTAGRAM_SQUARE: "1:1",
                CapCutVideoFormat.YOUTUBE_LANDSCAPE: "16:9"
            }
            
            format_text = format_mapping.get(format, "9:16")
            await self.page.click(f"text={format_text}")
            
        except Exception as e:
            logger.error(f"Failed to set export format: {e}")


class CapCutService:
    """Main CapCut service combining API and browser automation"""
    
    def __init__(self):
        self.api_client = CapCutAPIClient()
        self.browser_automation = CapCutBrowserAutomation()
        self.use_api = getattr(settings, 'CAPCUT_USE_API', True)
        
        # Cost estimation (mock values - replace with actual pricing)
        self.cost_per_minute = {
            VideoQuality.LOW: 2.0,
            VideoQuality.MEDIUM: 4.0,
            VideoQuality.HIGH: 8.0,
            VideoQuality.ULTRA: 15.0
        }
    
    async def create_video(
        self,
        request: CapCutVideoRequest
    ) -> CapCutVideoResponse:
        """Create video using API or browser automation"""
        
        if self.use_api and self.api_client.api_key:
            return await self._create_video_api(request)
        else:
            return await self._create_video_browser(request)
    
    async def _create_video_api(
        self,
        request: CapCutVideoRequest
    ) -> CapCutVideoResponse:
        """Create video using API"""
        
        async with self.api_client:
            response = await self.api_client.create_video_project(request)
            
            # Estimate cost
            cost_per_min = self.cost_per_minute.get(request.quality, 4.0)
            response.cost = (request.duration / 60.0) * cost_per_min
            
            return response
    
    async def _create_video_browser(
        self,
        request: CapCutVideoRequest
    ) -> CapCutVideoResponse:
        """Create video using browser automation"""
        
        try:
            async with self.browser_automation:
                # Login if credentials are available
                email = getattr(settings, 'CAPCUT_EMAIL', '')
                password = getattr(settings, 'CAPCUT_PASSWORD', '')
                
                if email and password:
                    await self.browser_automation.login(email, password)
                
                # Create project
                project_id = await self.browser_automation.create_project_from_template(
                    request.template_id,
                    request.assets,
                    request.title
                )
                
                if not project_id:
                    raise Exception("Failed to create project")
                
                # Export video
                download_url = await self.browser_automation.export_video(
                    request.quality,
                    request.format
                )
                
                # Estimate cost
                cost_per_min = self.cost_per_minute.get(request.quality, 4.0)
                cost = (request.duration / 60.0) * cost_per_min
                
                return CapCutVideoResponse(
                    project_id=project_id,
                    status=GenerationStatus.COMPLETED,
                    download_url=download_url,
                    duration=request.duration,
                    quality=request.quality,
                    cost=cost,
                    generation_time=300.0  # Estimated 5 minutes
                )
                
        except Exception as e:
            logger.error(f"Browser automation failed: {e}")
            return CapCutVideoResponse(
                project_id=str(uuid.uuid4()),
                status=GenerationStatus.FAILED,
                error_message=str(e)
            )
    
    async def get_status(self, project_id: str) -> CapCutVideoResponse:
        """Get project status"""
        
        if self.use_api and self.api_client.api_key:
            async with self.api_client:
                return await self.api_client.get_project_status(project_id)
        else:
            # For browser automation, we assume immediate completion
            return CapCutVideoResponse(
                project_id=project_id,
                status=GenerationStatus.COMPLETED,
                progress=100.0
            )
    
    async def list_templates(
        self,
        category: Optional[CapCutTemplateCategory] = None,
        industry: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """List available templates"""
        
        if self.use_api and self.api_client.api_key:
            async with self.api_client:
                return await self.api_client.list_templates(category, industry)
        else:
            # Return mock templates for browser automation
            return self._get_mock_templates(category, industry)
    
    def _get_mock_templates(
        self,
        category: Optional[CapCutTemplateCategory] = None,
        industry: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Get mock templates for browser automation"""
        
        templates = [
            {
                "id": "unboxing_modern",
                "title": "Modern Unboxing",
                "category": CapCutTemplateCategory.UNBOXING,
                "industry": "general",
                "duration": 30,
                "format": CapCutVideoFormat.TIKTOK_VERTICAL,
                "thumbnail": "https://example.com/template1.jpg"
            },
            {
                "id": "product_showcase_tech",
                "title": "Tech Product Showcase",
                "category": CapCutTemplateCategory.PRODUCT_SHOWCASE,
                "industry": "technology",
                "duration": 45,
                "format": CapCutVideoFormat.TIKTOK_VERTICAL,
                "thumbnail": "https://example.com/template2.jpg"
            },
            {
                "id": "lifestyle_trendy",
                "title": "Trendy Lifestyle",
                "category": CapCutTemplateCategory.LIFESTYLE,
                "industry": "fashion",
                "duration": 60,
                "format": CapCutVideoFormat.INSTAGRAM_STORY,
                "thumbnail": "https://example.com/template3.jpg"
            }
        ]
        
        # Filter by category and industry
        filtered = templates
        
        if category:
            filtered = [t for t in filtered if t["category"] == category]
        
        if industry:
            filtered = [t for t in filtered if t["industry"] == industry or t["industry"] == "general"]
        
        return filtered
    
    def estimate_cost(
        self,
        duration: float,
        quality: VideoQuality
    ) -> float:
        """Estimate video generation cost"""
        
        cost_per_min = self.cost_per_minute.get(quality, 4.0)
        return (duration / 60.0) * cost_per_min


# Global service instance
_capcut_service: Optional[CapCutService] = None


async def get_capcut_service() -> CapCutService:
    """Get global CapCut service instance"""
    global _capcut_service
    if _capcut_service is None:
        _capcut_service = CapCutService()
    return _capcut_service