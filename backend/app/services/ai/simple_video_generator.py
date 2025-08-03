"""
Simple Video Generator for the core pipeline
Generates videos from content outlines for the streamlined workflow.
"""

import asyncio
import json
import time
import hashlib
from typing import Any, Dict, List, Optional
import logging

from app.services.ai.providers import get_text_service
from app.core.config import settings

logger = logging.getLogger(__name__)


class VideoGenerator:
    """Simplified video generator for the core pipeline"""
    
    def __init__(self):
        self.text_service = None
    
    async def _get_text_service(self):
        """Initialize AI service"""
        if self.text_service is None:
            self.text_service = await get_text_service()
    
    async def generate_video(
        self,
        outline: Dict[str, Any],
        brand_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Generate main video from outline"""
        
        await self._get_text_service()
        
        try:
            scenes = outline.get("scenes", [])
            video_id = hashlib.md5(f"{outline.get('hook', {}).get('text', '')}{time.time()}".encode()).hexdigest()
            
            # Generate video assets for each scene
            video_assets = []
            for scene in scenes:
                asset = await self._generate_scene_asset(scene, brand_data)
                if asset:
                    video_assets.append(asset)
            
            # Create video project data
            video_result = {
                "video_id": video_id,
                "title": f"Viral Video - {brand_data.get('name', 'Brand')}",
                "duration": outline.get("total_duration", 30),
                "status": "completed",
                "assets": video_assets,
                "editing_instructions": await self._generate_editing_instructions(outline, brand_data),
                "platform_optimizations": self._get_platform_optimizations(outline),
                "generated_at": time.time()
            }
            
            logger.info(f"Generated video: {video_id}")
            return video_result
            
        except Exception as e:
            logger.error(f"Video generation failed: {e}")
            return {
                "status": "failed",
                "error": str(e),
                "generated_at": time.time()
            }
    
    async def generate_short(
        self,
        outline: Dict[str, Any],
        brand_data: Dict[str, Any],
        original_video: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Generate short version of the video"""
        
        try:
            scenes = outline.get("scenes", [])
            short_id = hashlib.md5(f"short_{outline.get('hook', {}).get('text', '')}{time.time()}".encode()).hexdigest()
            
            # Create shorter version - focus on hook and CTA
            key_scenes = []
            for scene in scenes:
                scene_type = scene.get("type", "")
                if scene_type in ["hook", "solution", "cta"]:
                    key_scenes.append(scene)
            
            # Generate short video assets
            short_assets = []
            for scene in key_scenes:
                asset = await self._generate_scene_asset(scene, brand_data, short_format=True)
                if asset:
                    short_assets.append(asset)
            
            short_result = {
                "video_id": short_id,
                "title": f"Short - {brand_data.get('name', 'Brand')}",
                "duration": 15,  # 15-second short
                "status": "completed",
                "assets": short_assets,
                "format": "vertical_short",
                "platform_optimizations": {
                    "tiktok": True,
                    "instagram_reels": True,
                    "youtube_shorts": True
                },
                "generated_at": time.time()
            }
            
            logger.info(f"Generated short video: {short_id}")
            return short_result
            
        except Exception as e:
            logger.error(f"Short video generation failed: {e}")
            return {
                "status": "failed",
                "error": str(e),
                "generated_at": time.time()
            }
    
    async def _generate_scene_asset(
        self,
        scene: Dict[str, Any],
        brand_data: Dict[str, Any],
        short_format: bool = False
    ) -> Dict[str, Any]:
        """Generate video asset for a scene"""
        
        try:
            scene_id = hashlib.md5(f"{scene.get('dialogue', '')}{time.time()}".encode()).hexdigest()
            
            # Create video prompt for AI generation
            visual_prompt = await self._create_visual_prompt(scene, brand_data, short_format)
            
            # Simulate video generation (in production, call actual video AI APIs)
            asset = {
                "scene_id": scene_id,
                "type": scene.get("type", "main"),
                "timing": scene.get("timing", "0-5s"),
                "visual_prompt": visual_prompt,
                "dialogue": scene.get("dialogue", ""),
                "text_overlay": scene.get("text_overlay", ""),
                "video_url": f"https://mock-video-api.com/video/{scene_id}.mp4",
                "thumbnail_url": f"https://mock-video-api.com/thumb/{scene_id}.jpg",
                "duration": self._parse_duration(scene.get("timing", "0-5s")),
                "transition": scene.get("transition", "cut"),
                "status": "generated"
            }
            
            return asset
            
        except Exception as e:
            logger.debug(f"Scene asset generation failed: {e}")
            return None
    
    async def _create_visual_prompt(
        self,
        scene: Dict[str, Any],
        brand_data: Dict[str, Any],
        short_format: bool = False
    ) -> str:
        """Create visual prompt for video generation"""
        
        await self._get_text_service()
        
        scene_type = scene.get("type", "main")
        visual_desc = scene.get("visual", "")
        dialogue = scene.get("dialogue", "")
        
        format_style = "vertical 9:16 format, mobile-optimized" if short_format else "standard format"
        brand_voice = brand_data.get("brand_voice", {}).get("primary_voice", "professional")
        
        prompt = f"""
        Create a video scene with the following specifications:
        
        Scene Type: {scene_type}
        Visual Description: {visual_desc}
        Dialogue Context: {dialogue}
        Brand Voice: {brand_voice}
        Format: {format_style}
        
        Visual Requirements:
        1. High-quality, professional appearance
        2. Good lighting and clear composition
        3. Engaging and attention-grabbing
        4. Brand-appropriate aesthetic
        5. Mobile-friendly if short format
        
        Generate a detailed visual prompt for AI video generation.
        """
        
        try:
            response = await self.text_service.generate(prompt, max_tokens=200, temperature=0.6)
            if response.success:
                return response.content.strip()
        except Exception as e:
            logger.debug(f"Visual prompt generation failed: {e}")
        
        # Fallback prompt
        return f"{visual_desc}. {brand_voice} style, {format_style}, professional quality."
    
    async def _generate_editing_instructions(
        self,
        outline: Dict[str, Any],
        brand_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Generate editing instructions for the video"""
        
        scenes = outline.get("scenes", [])
        brand_colors = brand_data.get("brand_voice", {})
        
        instructions = {
            "timeline": [],
            "transitions": [],
            "text_overlays": [],
            "branding": {
                "logo_placement": "top_left",
                "logo_opacity": 0.7,
                "brand_colors": ["#000000", "#FFFFFF"],  # Default colors
                "font_style": "modern_bold"
            },
            "audio": {
                "background_music": "upbeat_trending",
                "voice_over": True,
                "sound_effects": ["transition_whoosh", "notification_ping"]
            }
        }
        
        # Timeline instructions
        current_time = 0.0
        for i, scene in enumerate(scenes):
            duration = self._parse_duration(scene.get("timing", "0-5s"))
            
            instructions["timeline"].append({
                "scene_number": i + 1,
                "start_time": current_time,
                "end_time": current_time + duration,
                "primary_action": scene.get("type", "main"),
                "pacing": "fast" if scene.get("type") == "hook" else "medium"
            })
            
            # Add transition (except for last scene)
            if i < len(scenes) - 1:
                instructions["transitions"].append({
                    "position": current_time + duration,
                    "type": scene.get("transition", "cut"),
                    "duration": 0.3
                })
            
            # Add text overlay
            if scene.get("text_overlay"):
                instructions["text_overlays"].append({
                    "start_time": current_time,
                    "end_time": current_time + duration,
                    "text": scene.get("text_overlay"),
                    "position": "center",
                    "style": "bold_white_shadow",
                    "animation": "fade_in"
                })
            
            current_time += duration
        
        return instructions
    
    def _get_platform_optimizations(self, outline: Dict[str, Any]) -> Dict[str, Any]:
        """Get platform-specific optimizations"""
        
        return {
            "tiktok": {
                "aspect_ratio": "9:16",
                "duration": "15-30s",
                "captions": True,
                "trending_effects": True,
                "hashtag_overlay": True
            },
            "instagram": {
                "aspect_ratio": "9:16",
                "duration": "15-60s",
                "high_quality": True,
                "story_format": True,
                "aesthetic_filters": True
            },
            "youtube_shorts": {
                "aspect_ratio": "9:16",
                "duration": "15-60s",
                "thumbnail_optimization": True,
                "engagement_hooks": True,
                "subscribe_reminder": True
            }
        }
    
    def _parse_duration(self, timing: str) -> float:
        """Parse duration from timing string like '0-3s' or '3-8s'"""
        try:
            if '-' in timing and 's' in timing:
                start, end = timing.replace('s', '').split('-')
                return float(end) - float(start)
            return 5.0  # Default duration
        except:
            return 5.0