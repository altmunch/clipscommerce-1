"""
Video assembly service with FFmpeg integration for combining AI-generated segments
"""

import asyncio
import json
import logging
import os
import subprocess
import tempfile
import uuid
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass
from pathlib import Path
import aiofiles
import aiohttp

from app.core.config import settings
from app.models.video_project import VideoProject, VideoSegment, BRollClip, VideoAsset
from .text_to_speech import TTSService, get_tts_service

logger = logging.getLogger(__name__)


@dataclass
class VideoTrack:
    """Represents a video track in the timeline"""
    track_id: str
    source_url: str
    start_time: float
    end_time: float
    duration: float
    track_type: str  # "main", "broll", "overlay", "text"
    position: Dict[str, Any]  # x, y, width, height for positioning
    effects: List[Dict[str, Any]]  # Filters and effects to apply
    opacity: float = 1.0
    volume: float = 1.0


@dataclass
class AudioTrack:
    """Represents an audio track in the timeline"""
    track_id: str
    source_url: str
    start_time: float
    end_time: float
    volume: float = 1.0
    fade_in: float = 0.0
    fade_out: float = 0.0
    effects: List[Dict[str, Any]] = None


@dataclass
class TextOverlay:
    """Text overlay configuration"""
    text: str
    start_time: float
    end_time: float
    position: str  # "center", "top", "bottom", "top_left", etc.
    font_size: int = 48
    font_family: str = "Arial"
    font_color: str = "#FFFFFF"
    background_color: Optional[str] = None
    animation: str = "fade_in"  # "fade_in", "slide_up", "bounce", etc.
    product_tag: Optional[Dict[str, Any]] = None  # Product tagging info


@dataclass
class Timeline:
    """Complete video timeline"""
    video_tracks: List[VideoTrack]
    audio_tracks: List[AudioTrack]
    text_overlays: List[TextOverlay]
    transitions: List[Dict[str, Any]]
    total_duration: float
    resolution: Tuple[int, int] = (1920, 1080)
    fps: int = 30
    aspect_ratio: str = "16:9"


class VideoAssemblyService:
    """Service for assembling final videos from AI-generated segments"""
    
    def __init__(self):
        self.tts_service = get_tts_service()
        self.temp_dir = Path(tempfile.gettempdir()) / "viral_os_video_assembly"
        self.temp_dir.mkdir(exist_ok=True)
        
        # Video assembly templates for different platforms
        self.platform_templates = {
            "tiktok": {
                "resolution": (1080, 1920),  # 9:16 vertical
                "fps": 30,
                "aspect_ratio": "9:16",
                "max_duration": 60,
                "text_safe_area": {"top": 100, "bottom": 200}  # Account for UI elements
            },
            "instagram": {
                "resolution": (1080, 1920),  # 9:16 for stories/reels
                "fps": 30, 
                "aspect_ratio": "9:16",
                "max_duration": 90,
                "text_safe_area": {"top": 120, "bottom": 180}
            },
            "youtube_shorts": {
                "resolution": (1080, 1920),  # 9:16 vertical
                "fps": 60,
                "aspect_ratio": "9:16", 
                "max_duration": 60,
                "text_safe_area": {"top": 80, "bottom": 160}
            },
            "youtube": {
                "resolution": (1920, 1080),  # 16:9 horizontal
                "fps": 30,
                "aspect_ratio": "16:9",
                "max_duration": 300,
                "text_safe_area": {"top": 60, "bottom": 120}
            }
        }
    
    async def assemble_video_project(self, project: VideoProject) -> Dict[str, Any]:
        """Assemble complete video from project segments"""
        logger.info(f"Starting video assembly for project: {project.id}")
        
        try:
            # Create timeline from project data
            timeline = await self._create_timeline_from_project(project)
            
            # Download all required assets
            asset_paths = await self._download_assets(timeline)
            
            # Generate audio narration if needed
            audio_paths = await self._generate_audio_tracks(project, timeline)
            
            # Assemble video using FFmpeg
            output_path = await self._assemble_with_ffmpeg(timeline, asset_paths, audio_paths, project)
            
            # Upload final video to storage
            final_url = await self._upload_final_video(output_path, project)
            
            # Generate thumbnails and previews
            thumbnail_url = await self._generate_thumbnail(output_path, project)
            preview_url = await self._generate_preview(output_path, project)
            
            # Clean up temporary files
            await self._cleanup_temp_files([output_path] + list(asset_paths.values()) + list(audio_paths.values()))
            
            return {
                "status": "completed",
                "video_url": final_url,
                "thumbnail_url": thumbnail_url,
                "preview_url": preview_url,
                "duration": timeline.total_duration,
                "resolution": timeline.resolution,
                "file_size": os.path.getsize(output_path) if os.path.exists(output_path) else 0,
                "timeline": self._timeline_to_dict(timeline)
            }
            
        except Exception as e:
            logger.error(f"Video assembly failed for project {project.id}: {e}")
            return {
                "status": "failed",
                "error": str(e)
            }
    
    async def _create_timeline_from_project(self, project: VideoProject) -> Timeline:
        """Create timeline from project segments and configuration"""
        
        platform = project.target_platform or "tiktok"
        template = self.platform_templates.get(platform, self.platform_templates["tiktok"])
        
        video_tracks = []
        audio_tracks = []
        text_overlays = []
        transitions = []
        
        current_time = 0.0
        
        # Process main video segments
        for i, segment in enumerate(project.video_segments):
            if segment.status.value == "completed" and segment.video_url:
                
                # Main video track
                video_track = VideoTrack(
                    track_id=f"main_{i}",
                    source_url=segment.video_url,
                    start_time=current_time,
                    end_time=current_time + segment.duration,
                    duration=segment.duration,
                    track_type="main",
                    position={
                        "x": 0, "y": 0,
                        "width": template["resolution"][0],
                        "height": template["resolution"][1]
                    },
                    effects=[]
                )
                video_tracks.append(video_track)
                
                # Add speech audio if available
                if segment.has_speech and segment.speech_url:
                    audio_track = AudioTrack(
                        track_id=f"speech_{i}",
                        source_url=segment.speech_url,
                        start_time=current_time,
                        end_time=current_time + segment.duration,
                        volume=0.8,
                        fade_in=0.1,
                        fade_out=0.1
                    )
                    audio_tracks.append(audio_track)
                
                # Add product appearance timing from AI generation metadata
                self._add_product_overlays_from_metadata(
                    segment, current_time, text_overlays, project
                )
                
                current_time += segment.duration
        
        # Process B-roll clips
        for clip in project.broll_clips:
            if clip.used_in_timeline and clip.timeline_start_time is not None:
                
                broll_track = VideoTrack(
                    track_id=f"broll_{clip.id}",
                    source_url=clip.video_url,
                    start_time=clip.timeline_start_time,
                    end_time=clip.timeline_end_time or clip.timeline_start_time + clip.duration,
                    duration=clip.duration,
                    track_type="broll",
                    position=self._get_broll_position(clip.overlay_position, template),
                    effects=[],
                    opacity=clip.opacity
                )
                video_tracks.append(broll_track)
        
        # Add brand assets and overlays
        self._add_brand_overlays(project, text_overlays, current_time, template)
        
        # Add call-to-action overlays
        self._add_cta_overlays(project, text_overlays, current_time, template)
        
        # Generate transitions between segments
        transitions = self._generate_transitions(video_tracks, platform)
        
        return Timeline(
            video_tracks=video_tracks,
            audio_tracks=audio_tracks,
            text_overlays=text_overlays,
            transitions=transitions,
            total_duration=current_time,
            resolution=template["resolution"],
            fps=template["fps"],
            aspect_ratio=template["aspect_ratio"]
        )
    
    def _add_product_overlays_from_metadata(
        self, 
        segment: VideoSegment, 
        start_time: float, 
        text_overlays: List[TextOverlay],
        project: VideoProject
    ):
        """Add product tagging overlays based on AI generation metadata"""
        
        # Extract product timing from AI provider metadata
        metadata = segment.provider_response or {}
        product_appearances = metadata.get("product_appearances", [])
        
        # If no explicit product timing, infer from segment content
        if not product_appearances and segment.prompt:
            product_appearances = self._infer_product_timing_from_prompt(segment)
        
        for appearance in product_appearances:
            # Create product tag overlay
            product_name = appearance.get("product_name", "Product")
            appearance_start = start_time + appearance.get("start_time", 0)
            appearance_end = start_time + appearance.get("end_time", segment.duration)
            
            overlay = TextOverlay(
                text=f"🏷️ {product_name}",
                start_time=appearance_start,
                end_time=appearance_end,
                position="bottom_left",
                font_size=36,
                font_color="#FFFFFF",
                background_color="rgba(0,0,0,0.7)",
                animation="fade_in",
                product_tag={
                    "product_name": product_name,
                    "product_url": appearance.get("product_url"),
                    "price": appearance.get("price"),
                    "discount": appearance.get("discount")
                }
            )
            text_overlays.append(overlay)
    
    def _infer_product_timing_from_prompt(self, segment: VideoSegment) -> List[Dict[str, Any]]:
        """Infer product appearance timing from segment prompt when not provided by AI"""
        
        # Simple keyword-based inference - in production would use NLP
        prompt_lower = segment.prompt.lower()
        
        appearances = []
        
        # Look for product-related keywords
        product_keywords = ["product", "item", "buy", "purchase", "price", "discount", "sale"]
        
        if any(keyword in prompt_lower for keyword in product_keywords):
            # Assume product appears for most of the segment
            appearances.append({
                "product_name": "Featured Product",
                "start_time": 0.0,
                "end_time": segment.duration * 0.8,  # 80% of segment
                "confidence": 0.7
            })
        
        return appearances
    
    def _get_broll_position(self, overlay_position: str, template: Dict[str, Any]) -> Dict[str, Any]:
        """Get position coordinates for B-roll overlay"""
        
        width, height = template["resolution"]
        broll_width = width // 3  # B-roll takes 1/3 of screen
        broll_height = height // 3
        
        positions = {
            "top_left": {"x": 20, "y": 20, "width": broll_width, "height": broll_height},
            "top_right": {"x": width - broll_width - 20, "y": 20, "width": broll_width, "height": broll_height},
            "bottom_left": {"x": 20, "y": height - broll_height - 20, "width": broll_width, "height": broll_height},
            "bottom_right": {"x": width - broll_width - 20, "y": height - broll_height - 20, "width": broll_width, "height": broll_height},
            "center": {"x": (width - broll_width) // 2, "y": (height - broll_height) // 2, "width": broll_width, "height": broll_height}
        }
        
        return positions.get(overlay_position, positions["bottom_right"])
    
    def _add_brand_overlays(
        self, 
        project: VideoProject, 
        text_overlays: List[TextOverlay], 
        duration: float,
        template: Dict[str, Any]
    ):
        """Add brand logo and consistent overlays"""
        
        brand_guidelines = project.brand_guidelines or {}
        
        # Add brand logo if available
        logo_url = brand_guidelines.get("logo_url")
        if logo_url:
            # Logo will be added as a video track overlay in FFmpeg
            pass
        
        # Add brand hashtags
        brand_hashtags = brand_guidelines.get("hashtags", [])
        if brand_hashtags:
            hashtag_text = " ".join(f"#{tag}" for tag in brand_hashtags[:3])  # Max 3 hashtags
            
            overlay = TextOverlay(
                text=hashtag_text,
                start_time=duration - 3.0,  # Last 3 seconds
                end_time=duration,
                position="bottom_center",
                font_size=32,
                font_color=brand_guidelines.get("colors", {}).get("primary", "#FFFFFF"),
                animation="slide_up"
            )
            text_overlays.append(overlay)
    
    def _add_cta_overlays(
        self, 
        project: VideoProject, 
        text_overlays: List[TextOverlay], 
        duration: float,
        template: Dict[str, Any]
    ):
        """Add call-to-action overlays"""
        
        platform = project.target_platform or "tiktok"
        
        # Platform-specific CTAs
        cta_messages = {
            "tiktok": "Follow for more! 👆",
            "instagram": "Save this post! 💾",
            "youtube_shorts": "Subscribe! 🔔",
            "youtube": "Like and Subscribe! 👍"
        }
        
        cta_text = cta_messages.get(platform, "Follow for more!")
        
        overlay = TextOverlay(
            text=cta_text,
            start_time=duration - 2.0,  # Last 2 seconds
            end_time=duration,
            position="top_center",
            font_size=40,
            font_color="#FFFFFF",
            background_color="rgba(255,0,100,0.8)",  # Bright attention-grabbing background
            animation="bounce"
        )
        text_overlays.append(overlay)
    
    def _generate_transitions(self, video_tracks: List[VideoTrack], platform: str) -> List[Dict[str, Any]]:
        """Generate transitions between video segments"""
        
        transitions = []
        
        # Platform-specific transition styles
        platform_transitions = {
            "tiktok": ["cut", "zoom_in", "spin", "slide"],
            "instagram": ["fade", "dissolve", "slide"],
            "youtube_shorts": ["cut", "fade", "wipe"],
            "youtube": ["fade", "dissolve", "slide"]
        }
        
        transition_types = platform_transitions.get(platform, ["cut", "fade"])
        
        # Add transitions between main video tracks
        main_tracks = [track for track in video_tracks if track.track_type == "main"]
        
        for i in range(len(main_tracks) - 1):
            current_track = main_tracks[i]
            next_track = main_tracks[i + 1]
            
            transition_type = transition_types[i % len(transition_types)]
            
            transitions.append({
                "type": transition_type,
                "start_time": current_track.end_time - 0.5,  # 0.5s overlap
                "duration": 0.5,
                "from_track": current_track.track_id,
                "to_track": next_track.track_id
            })
        
        return transitions
    
    async def _download_assets(self, timeline: Timeline) -> Dict[str, str]:
        """Download all video and audio assets to local temp files"""
        
        assets = {}
        download_tasks = []
        
        # Collect all URLs that need downloading
        urls_to_download = []
        
        for track in timeline.video_tracks:
            urls_to_download.append(("video", track.track_id, track.source_url))
        
        for track in timeline.audio_tracks:
            urls_to_download.append(("audio", track.track_id, track.source_url))
        
        # Download assets concurrently
        semaphore = asyncio.Semaphore(5)  # Limit concurrent downloads
        
        async def download_asset(asset_type: str, asset_id: str, url: str):
            async with semaphore:
                return await self._download_single_asset(asset_type, asset_id, url)
        
        download_tasks = [
            download_asset(asset_type, asset_id, url) 
            for asset_type, asset_id, url in urls_to_download
        ]
        
        results = await asyncio.gather(*download_tasks, return_exceptions=True)
        
        # Process results
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                logger.error(f"Failed to download asset {urls_to_download[i][1]}: {result}")
            else:
                asset_id = urls_to_download[i][1]
                assets[asset_id] = result
        
        return assets
    
    async def _download_single_asset(self, asset_type: str, asset_id: str, url: str) -> str:
        """Download a single asset to temp file"""
        
        # Generate temp file path
        extension = "mp4" if asset_type == "video" else "mp3"
        temp_path = self.temp_dir / f"{asset_id}_{uuid.uuid4().hex}.{extension}"
        
        try:
            timeout = aiohttp.ClientTimeout(total=300)  # 5 minute timeout for large files
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.get(url) as response:
                    response.raise_for_status()
                    
                    async with aiofiles.open(temp_path, 'wb') as f:
                        async for chunk in response.content.iter_chunked(8192):
                            await f.write(chunk)
            
            logger.info(f"Downloaded {asset_type} asset: {asset_id} -> {temp_path}")
            return str(temp_path)
            
        except Exception as e:
            logger.error(f"Failed to download {asset_type} asset {asset_id} from {url}: {e}")
            raise
    
    async def _generate_audio_tracks(self, project: VideoProject, timeline: Timeline) -> Dict[str, str]:
        """Generate TTS audio for segments that need it"""
        
        audio_paths = {}
        
        # Find segments that need TTS generation
        segments_needing_audio = []
        for segment in project.video_segments:
            if segment.speech_text and not segment.speech_url:
                segments_needing_audio.append(segment)
        
        if not segments_needing_audio:
            return audio_paths
        
        # Generate TTS for each segment
        for segment in segments_needing_audio:
            try:
                voice_id = project.voice_id or "21m00Tcm4TlvDq8ikWAM"  # Default ElevenLabs Rachel
                
                tts_result = await self.tts_service.generate_speech(
                    text=segment.speech_text,
                    voice_id=voice_id,
                    provider="elevenlabs"
                )
                
                # Download generated audio
                audio_path = await self._download_single_asset(
                    "audio", 
                    f"tts_{segment.id}", 
                    tts_result.audio_url
                )
                
                audio_paths[f"tts_{segment.id}"] = audio_path
                
                # Update segment with audio URL
                segment.speech_url = tts_result.audio_url
                
            except Exception as e:
                logger.error(f"Failed to generate TTS for segment {segment.id}: {e}")
        
        return audio_paths
    
    async def _assemble_with_ffmpeg(
        self, 
        timeline: Timeline, 
        asset_paths: Dict[str, str], 
        audio_paths: Dict[str, str],
        project: VideoProject
    ) -> str:
        """Assemble final video using FFmpeg"""
        
        output_path = self.temp_dir / f"final_{project.id}_{uuid.uuid4().hex}.mp4"
        
        # Build FFmpeg command
        cmd = ["ffmpeg", "-y"]  # -y to overwrite output file
        
        # Add input files
        input_files = []
        for track in timeline.video_tracks:
            if track.track_id in asset_paths:
                cmd.extend(["-i", asset_paths[track.track_id]])
                input_files.append(track.track_id)
        
        for track in timeline.audio_tracks:
            if track.track_id in asset_paths:
                cmd.extend(["-i", asset_paths[track.track_id]])
                input_files.append(track.track_id)
        
        # Add TTS audio files
        for audio_id, audio_path in audio_paths.items():
            cmd.extend(["-i", audio_path])
            input_files.append(audio_id)
        
        # Build filter complex for video composition
        filter_complex = self._build_filter_complex(timeline, input_files)
        
        if filter_complex:
            cmd.extend(["-filter_complex", filter_complex])
        
        # Output settings
        cmd.extend([
            "-map", "[final_video]",  # Map the final composed video
            "-map", "[final_audio]",  # Map the final mixed audio
            "-c:v", "libx264",        # Video codec
            "-preset", "medium",      # Encoding preset
            "-crf", "23",             # Quality setting
            "-c:a", "aac",            # Audio codec
            "-b:a", "128k",           # Audio bitrate
            "-r", str(timeline.fps),  # Frame rate
            "-s", f"{timeline.resolution[0]}x{timeline.resolution[1]}",  # Resolution
            str(output_path)
        ])
        
        # Execute FFmpeg command
        logger.info(f"Executing FFmpeg command: {' '.join(cmd)}")
        
        try:
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            stdout, stderr = await process.communicate()
            
            if process.returncode != 0:
                error_msg = stderr.decode() if stderr else "Unknown FFmpeg error"
                logger.error(f"FFmpeg failed: {error_msg}")
                raise RuntimeError(f"FFmpeg assembly failed: {error_msg}")
            
            logger.info(f"Video assembly completed: {output_path}")
            return str(output_path)
            
        except Exception as e:
            logger.error(f"FFmpeg execution failed: {e}")
            raise
    
    def _build_filter_complex(self, timeline: Timeline, input_files: List[str]) -> str:
        """Build FFmpeg filter_complex string for video composition"""
        
        filters = []
        input_index = 0
        
        # Scale and position video tracks
        for i, track in enumerate(timeline.video_tracks):
            if track.track_id in input_files:
                # Scale video to fit position
                scale_filter = f"[{input_index}:v]scale={track.position['width']}:{track.position['height']}[v{i}]"
                filters.append(scale_filter)
                
                input_index += 1
        
        # Overlay videos
        if len(timeline.video_tracks) > 1:
            # Start with first video as base
            current_output = "[v0]"
            
            for i in range(1, len(timeline.video_tracks)):
                track = timeline.video_tracks[i]
                
                # Create overlay
                overlay_filter = f"{current_output}[v{i}]overlay={track.position['x']}:{track.position['y']}:enable='between(t,{track.start_time},{track.end_time})'[ov{i}]"
                filters.append(overlay_filter)
                current_output = f"[ov{i}]"
            
            video_output = current_output
        else:
            video_output = "[v0]"
        
        # Add text overlays
        for i, overlay in enumerate(timeline.text_overlays):
            text_filter = self._create_text_overlay_filter(overlay, video_output, i)
            filters.append(text_filter)
            video_output = f"[text{i}]"
        
        # Set final video output
        filters.append(f"{video_output}[final_video]")
        
        # Mix audio tracks
        audio_inputs = []
        for track in timeline.audio_tracks:
            if track.track_id in input_files:
                audio_inputs.append(f"[{input_index}:a]")
                input_index += 1
        
        if audio_inputs:
            if len(audio_inputs) == 1:
                filters.append(f"{audio_inputs[0]}[final_audio]")
            else:
                mix_filter = f"{''.join(audio_inputs)}amix=inputs={len(audio_inputs)}[final_audio]"
                filters.append(mix_filter)
        else:
            # Create silent audio track
            filters.append("anullsrc=channel_layout=stereo:sample_rate=48000[final_audio]")
        
        return ";".join(filters)
    
    def _create_text_overlay_filter(self, overlay: TextOverlay, input_stream: str, index: int) -> str:
        """Create FFmpeg filter for text overlay"""
        
        # Position mapping
        positions = {
            "center": "main_w/2-text_w/2:main_h/2-text_h/2",
            "top_center": "main_w/2-text_w/2:50",
            "bottom_center": "main_w/2-text_w/2:main_h-text_h-50",
            "top_left": "50:50",
            "top_right": "main_w-text_w-50:50",
            "bottom_left": "50:main_h-text_h-50",
            "bottom_right": "main_w-text_w-50:main_h-text_h-50"
        }
        
        position = positions.get(overlay.position, positions["center"])
        
        # Escape text for FFmpeg
        escaped_text = overlay.text.replace("'", "\\'").replace(":", "\\:")
        
        # Build drawtext filter
        text_filter = f"{input_stream}drawtext=text='{escaped_text}':fontsize={overlay.font_size}:fontcolor={overlay.font_color}:x={position}:enable='between(t,{overlay.start_time},{overlay.end_time})'[text{index}]"
        
        # Add background if specified
        if overlay.background_color:
            # This would be enhanced with box=1:boxcolor=color in production
            pass
        
        return text_filter
    
    async def _upload_final_video(self, video_path: str, project: VideoProject) -> str:
        """Upload final video to cloud storage"""
        
        # Mock implementation - in production would upload to S3/GCS/etc
        final_url = f"https://storage.viral-os.com/videos/{project.id}/final.mp4"
        
        # Simulate upload delay
        await asyncio.sleep(2)
        
        logger.info(f"Uploaded final video: {final_url}")
        return final_url
    
    async def _generate_thumbnail(self, video_path: str, project: VideoProject) -> str:
        """Generate thumbnail from video"""
        
        thumbnail_path = self.temp_dir / f"thumb_{project.id}.jpg"
        
        # Use FFmpeg to extract frame at 2 second mark
        cmd = [
            "ffmpeg", "-y",
            "-i", video_path,
            "-ss", "2",  # Seek to 2 seconds
            "-vframes", "1",  # Extract 1 frame
            "-q:v", "2",  # High quality
            str(thumbnail_path)
        ]
        
        try:
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            await process.communicate()
            
            if process.returncode == 0:
                # Upload thumbnail
                thumbnail_url = f"https://storage.viral-os.com/videos/{project.id}/thumbnail.jpg"
                return thumbnail_url
            else:
                logger.error("Thumbnail generation failed")
                return ""
                
        except Exception as e:
            logger.error(f"Thumbnail generation error: {e}")
            return ""
    
    async def _generate_preview(self, video_path: str, project: VideoProject) -> str:
        """Generate preview/trailer from video"""
        
        preview_path = self.temp_dir / f"preview_{project.id}.mp4"
        
        # Create 10-second preview with highlights
        cmd = [
            "ffmpeg", "-y",
            "-i", video_path,
            "-ss", "0",      # Start from beginning
            "-t", "10",      # 10 seconds duration
            "-c:v", "libx264",
            "-crf", "25",
            "-preset", "fast",
            str(preview_path)
        ]
        
        try:
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            await process.communicate()
            
            if process.returncode == 0:
                # Upload preview
                preview_url = f"https://storage.viral-os.com/videos/{project.id}/preview.mp4"
                return preview_url
            else:
                logger.error("Preview generation failed")
                return ""
                
        except Exception as e:
            logger.error(f"Preview generation error: {e}")
            return ""
    
    async def _cleanup_temp_files(self, file_paths: List[str]):
        """Clean up temporary files"""
        
        for file_path in file_paths:
            try:
                if os.path.exists(file_path):
                    os.remove(file_path)
                    logger.debug(f"Cleaned up temp file: {file_path}")
            except Exception as e:
                logger.warning(f"Failed to clean up temp file {file_path}: {e}")
    
    def _timeline_to_dict(self, timeline: Timeline) -> Dict[str, Any]:
        """Convert timeline to dictionary for JSON serialization"""
        
        return {
            "video_tracks": [
                {
                    "track_id": track.track_id,
                    "start_time": track.start_time,
                    "end_time": track.end_time,
                    "duration": track.duration,
                    "track_type": track.track_type,
                    "position": track.position,
                    "opacity": track.opacity
                }
                for track in timeline.video_tracks
            ],
            "audio_tracks": [
                {
                    "track_id": track.track_id,
                    "start_time": track.start_time,
                    "end_time": track.end_time,
                    "volume": track.volume
                }
                for track in timeline.audio_tracks
            ],
            "text_overlays": [
                {
                    "text": overlay.text,
                    "start_time": overlay.start_time,
                    "end_time": overlay.end_time,
                    "position": overlay.position,
                    "product_tag": overlay.product_tag
                }
                for overlay in timeline.text_overlays
            ],
            "total_duration": timeline.total_duration,
            "resolution": timeline.resolution,
            "fps": timeline.fps,
            "aspect_ratio": timeline.aspect_ratio
        }


# Global service instance
_video_assembly_service: Optional[VideoAssemblyService] = None


def get_video_assembly_service() -> VideoAssemblyService:
    """Get global video assembly service instance"""
    global _video_assembly_service
    if _video_assembly_service is None:
        _video_assembly_service = VideoAssemblyService()
    return _video_assembly_service