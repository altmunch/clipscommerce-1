"""
Video metadata extraction service
"""

import logging
import asyncio
import json
from typing import Dict, Any, Optional
from pathlib import Path

from app.schemas.video_upload import VideoMetadataResponse

logger = logging.getLogger(__name__)


class VideoMetadataExtractor:
    """Service for extracting detailed metadata from video files"""
    
    def __init__(self):
        self.ffprobe_path = "ffprobe"
    
    async def extract_full_metadata(self, video_path: Path) -> Dict[str, Any]:
        """
        Extract comprehensive metadata from video file
        
        Args:
            video_path: Path to the video file
            
        Returns:
            Dictionary with comprehensive metadata
        """
        try:
            cmd = [
                self.ffprobe_path,
                "-v", "quiet",
                "-print_format", "json",
                "-show_format",
                "-show_streams",
                "-show_chapters",
                str(video_path)
            ]
            
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            stdout, stderr = await process.communicate()
            
            if process.returncode != 0:
                raise Exception(f"ffprobe failed: {stderr.decode()}")
            
            return json.loads(stdout.decode())
            
        except Exception as e:
            logger.error(f"Metadata extraction failed: {e}")
            return {}
    
    async def get_video_info(self, video_path: Path) -> VideoMetadataResponse:
        """
        Get basic video information
        
        Args:
            video_path: Path to the video file
            
        Returns:
            VideoMetadataResponse with basic video info
        """
        try:
            metadata = await self.extract_full_metadata(video_path)
            
            # Extract video stream
            video_stream = None
            audio_stream = None
            
            for stream in metadata.get("streams", []):
                if stream.get("codec_type") == "video" and video_stream is None:
                    video_stream = stream
                elif stream.get("codec_type") == "audio" and audio_stream is None:
                    audio_stream = stream
            
            if not video_stream:
                raise Exception("No video stream found")
            
            # Parse video information
            format_info = metadata.get("format", {})
            duration = float(format_info.get("duration", 0))
            file_size = int(format_info.get("size", 0))
            format_name = format_info.get("format_name", "unknown")
            bitrate = int(format_info.get("bit_rate", 0))
            
            # Video stream info
            width = video_stream.get("width", 0)
            height = video_stream.get("height", 0)
            codec = video_stream.get("codec_name", "unknown")
            
            # Calculate FPS
            fps = 0
            if "r_frame_rate" in video_stream:
                fps_str = video_stream["r_frame_rate"]
                if "/" in fps_str:
                    num, den = fps_str.split("/")
                    fps = int(float(num) / float(den)) if float(den) != 0 else 0
            
            return VideoMetadataResponse(
                duration=duration,
                resolution=f"{width}x{height}",
                fps=fps,
                file_size=file_size,
                format=format_name,
                codec=codec,
                bitrate=bitrate
            )
            
        except Exception as e:
            logger.error(f"Video info extraction failed: {e}")
            return VideoMetadataResponse(
                duration=0.0,
                resolution="unknown",
                fps=0,
                file_size=0,
                format="unknown",
                codec="unknown",
                bitrate=None
            )
    
    async def analyze_video_quality(self, video_path: Path) -> Dict[str, Any]:
        """
        Analyze video quality metrics
        
        Args:
            video_path: Path to the video file
            
        Returns:
            Dictionary with quality analysis results
        """
        try:
            metadata = await self.extract_full_metadata(video_path)
            video_stream = None
            
            for stream in metadata.get("streams", []):
                if stream.get("codec_type") == "video":
                    video_stream = stream
                    break
            
            if not video_stream:
                return {"error": "No video stream found"}
            
            analysis = {
                "resolution_category": self._categorize_resolution(
                    video_stream.get("width", 0),
                    video_stream.get("height", 0)
                ),
                "bitrate_category": self._categorize_bitrate(
                    int(metadata.get("format", {}).get("bit_rate", 0))
                ),
                "codec_efficiency": self._analyze_codec_efficiency(
                    video_stream.get("codec_name", "")
                ),
                "aspect_ratio": self._calculate_aspect_ratio(
                    video_stream.get("width", 0),
                    video_stream.get("height", 0)
                ),
                "color_space": video_stream.get("color_space", "unknown"),
                "pixel_format": video_stream.get("pix_fmt", "unknown")
            }
            
            return analysis
            
        except Exception as e:
            logger.error(f"Video quality analysis failed: {e}")
            return {"error": str(e)}
    
    def _categorize_resolution(self, width: int, height: int) -> str:
        """Categorize video resolution"""
        total_pixels = width * height
        
        if total_pixels >= 3840 * 2160:  # 4K
            return "4K"
        elif total_pixels >= 1920 * 1080:  # 1080p
            return "1080p"
        elif total_pixels >= 1280 * 720:  # 720p
            return "720p"
        elif total_pixels >= 854 * 480:  # 480p
            return "480p"
        elif total_pixels >= 640 * 360:  # 360p
            return "360p"
        else:
            return "low"
    
    def _categorize_bitrate(self, bitrate: int) -> str:
        """Categorize video bitrate"""
        bitrate_mbps = bitrate / 1_000_000  # Convert to Mbps
        
        if bitrate_mbps >= 10:
            return "very_high"
        elif bitrate_mbps >= 5:
            return "high"
        elif bitrate_mbps >= 2:
            return "medium"
        elif bitrate_mbps >= 1:
            return "low"
        else:
            return "very_low"
    
    def _analyze_codec_efficiency(self, codec: str) -> str:
        """Analyze codec efficiency"""
        efficient_codecs = ["h264", "h265", "hevc", "vp9", "av1"]
        older_codecs = ["mpeg4", "mpeg2", "divx", "xvid"]
        
        codec_lower = codec.lower()
        
        if any(eff in codec_lower for eff in efficient_codecs):
            return "efficient"
        elif any(old in codec_lower for old in older_codecs):
            return "outdated"
        else:
            return "unknown"
    
    def _calculate_aspect_ratio(self, width: int, height: int) -> str:
        """Calculate and format aspect ratio"""
        if width == 0 or height == 0:
            return "unknown"
        
        # Common aspect ratios
        ratio = width / height
        
        if abs(ratio - 16/9) < 0.1:
            return "16:9"
        elif abs(ratio - 9/16) < 0.1:
            return "9:16"
        elif abs(ratio - 4/3) < 0.1:
            return "4:3"
        elif abs(ratio - 1) < 0.1:
            return "1:1"
        elif abs(ratio - 21/9) < 0.1:
            return "21:9"
        else:
            return f"{width}:{height}"


# Dependency injection
_metadata_extractor = None

def get_metadata_extractor() -> VideoMetadataExtractor:
    """Get metadata extractor instance"""
    global _metadata_extractor
    if _metadata_extractor is None:
        _metadata_extractor = VideoMetadataExtractor()
    return _metadata_extractor