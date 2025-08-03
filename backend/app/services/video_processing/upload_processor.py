"""
Video upload processing service for handling user-uploaded video files
"""

import logging
import subprocess
import asyncio
from typing import Dict, Any, Optional
from pathlib import Path
import uuid
import json

from app.schemas.video_upload import VideoProcessingOptions, VideoMetadataResponse

logger = logging.getLogger(__name__)


class VideoUploadProcessor:
    """Service for processing uploaded video files"""
    
    def __init__(self):
        self.ffmpeg_path = "ffmpeg"  # Assumes ffmpeg is in PATH
        self.ffprobe_path = "ffprobe"  # Assumes ffprobe is in PATH
        
    async def process_video(
        self, 
        video_path: Path, 
        processing_options: VideoProcessingOptions
    ) -> Dict[str, Any]:
        """
        Process uploaded video file according to processing options
        
        Args:
            video_path: Path to the uploaded video file
            processing_options: Processing configuration
            
        Returns:
            Dictionary with processing results and metadata
        """
        try:
            results = {
                "original_path": str(video_path),
                "metadata": {},
                "processed_files": {},
                "processing_status": "completed"
            }
            
            # Extract video metadata
            metadata = await self.extract_metadata(video_path)
            results["metadata"] = metadata
            
            # Generate thumbnail if requested
            if processing_options.generate_thumbnail:
                thumbnail_path = await self.generate_thumbnail(video_path)
                results["processed_files"]["thumbnail"] = str(thumbnail_path)
            
            # Extract audio if requested
            if processing_options.extract_audio:
                audio_path = await self.extract_audio(video_path)
                results["processed_files"]["audio"] = str(audio_path)
            
            # Optimize for platform if requested
            if processing_options.optimize_for_platform:
                optimized_path = await self.optimize_for_platform(
                    video_path, 
                    processing_options.target_quality
                )
                results["processed_files"]["optimized"] = str(optimized_path)
            
            # Compress video if requested
            if processing_options.compress_video:
                compressed_path = await self.compress_video(
                    video_path,
                    processing_options.target_quality
                )
                results["processed_files"]["compressed"] = str(compressed_path)
            
            return results
            
        except Exception as e:
            logger.error(f"Video processing failed: {e}")
            return {
                "original_path": str(video_path),
                "metadata": {},
                "processed_files": {},
                "processing_status": "failed",
                "error": str(e)
            }
    
    async def extract_metadata(self, video_path: Path) -> VideoMetadataResponse:
        """
        Extract metadata from video file using ffprobe
        
        Args:
            video_path: Path to the video file
            
        Returns:
            VideoMetadataResponse with extracted metadata
        """
        try:
            # Use ffprobe to extract metadata
            cmd = [
                self.ffprobe_path,
                "-v", "quiet",
                "-print_format", "json",
                "-show_format",
                "-show_streams",
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
            
            metadata = json.loads(stdout.decode())
            
            # Extract video stream information
            video_stream = None
            for stream in metadata.get("streams", []):
                if stream.get("codec_type") == "video":
                    video_stream = stream
                    break
            
            if not video_stream:
                raise Exception("No video stream found")
            
            # Parse metadata
            duration = float(metadata.get("format", {}).get("duration", 0))
            width = video_stream.get("width", 0)
            height = video_stream.get("height", 0)
            fps = eval(video_stream.get("r_frame_rate", "0/1"))  # Format like "30/1"
            codec = video_stream.get("codec_name", "unknown")
            bitrate = int(metadata.get("format", {}).get("bit_rate", 0))
            file_size = int(metadata.get("format", {}).get("size", 0))
            format_name = metadata.get("format", {}).get("format_name", "unknown")
            
            return VideoMetadataResponse(
                duration=duration,
                resolution=f"{width}x{height}",
                fps=int(fps) if fps else 0,
                file_size=file_size,
                format=format_name,
                codec=codec,
                bitrate=bitrate
            )
            
        except Exception as e:
            logger.error(f"Metadata extraction failed: {e}")
            return VideoMetadataResponse(
                duration=0.0,
                resolution="unknown",
                fps=0,
                file_size=0,
                format="unknown",
                codec="unknown",
                bitrate=None
            )
    
    async def generate_thumbnail(self, video_path: Path) -> Path:
        """
        Generate thumbnail from video file
        
        Args:
            video_path: Path to the video file
            
        Returns:
            Path to the generated thumbnail
        """
        try:
            thumbnail_path = video_path.parent / f"{video_path.stem}_thumbnail.jpg"
            
            cmd = [
                self.ffmpeg_path,
                "-i", str(video_path),
                "-ss", "00:00:01",  # Extract frame at 1 second
                "-vframes", "1",
                "-y",  # Overwrite output file
                str(thumbnail_path)
            ]
            
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            stdout, stderr = await process.communicate()
            
            if process.returncode != 0:
                raise Exception(f"Thumbnail generation failed: {stderr.decode()}")
            
            return thumbnail_path
            
        except Exception as e:
            logger.error(f"Thumbnail generation failed: {e}")
            raise
    
    async def extract_audio(self, video_path: Path) -> Path:
        """
        Extract audio track from video file
        
        Args:
            video_path: Path to the video file
            
        Returns:
            Path to the extracted audio file
        """
        try:
            audio_path = video_path.parent / f"{video_path.stem}_audio.mp3"
            
            cmd = [
                self.ffmpeg_path,
                "-i", str(video_path),
                "-vn",  # No video
                "-acodec", "mp3",
                "-ab", "192k",  # Audio bitrate
                "-y",  # Overwrite output file
                str(audio_path)
            ]
            
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            stdout, stderr = await process.communicate()
            
            if process.returncode != 0:
                raise Exception(f"Audio extraction failed: {stderr.decode()}")
            
            return audio_path
            
        except Exception as e:
            logger.error(f"Audio extraction failed: {e}")
            raise
    
    async def optimize_for_platform(self, video_path: Path, quality: str = "medium") -> Path:
        """
        Optimize video for specific platform requirements
        
        Args:
            video_path: Path to the video file
            quality: Target quality level
            
        Returns:
            Path to the optimized video file
        """
        try:
            optimized_path = video_path.parent / f"{video_path.stem}_optimized.mp4"
            
            # Quality settings
            quality_settings = {
                "low": {"crf": "28", "preset": "fast"},
                "medium": {"crf": "23", "preset": "medium"},
                "high": {"crf": "18", "preset": "slow"}
            }
            
            settings = quality_settings.get(quality, quality_settings["medium"])
            
            cmd = [
                self.ffmpeg_path,
                "-i", str(video_path),
                "-c:v", "libx264",
                "-crf", settings["crf"],
                "-preset", settings["preset"],
                "-c:a", "aac",
                "-b:a", "128k",
                "-movflags", "+faststart",  # Enable fast start for web playback
                "-y",  # Overwrite output file
                str(optimized_path)
            ]
            
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            stdout, stderr = await process.communicate()
            
            if process.returncode != 0:
                raise Exception(f"Video optimization failed: {stderr.decode()}")
            
            return optimized_path
            
        except Exception as e:
            logger.error(f"Video optimization failed: {e}")
            raise
    
    async def compress_video(self, video_path: Path, quality: str = "medium") -> Path:
        """
        Compress video file to reduce size
        
        Args:
            video_path: Path to the video file
            quality: Target quality level
            
        Returns:
            Path to the compressed video file
        """
        try:
            compressed_path = video_path.parent / f"{video_path.stem}_compressed.mp4"
            
            # Compression settings
            compression_settings = {
                "low": {"scale": "720:-2", "crf": "30"},
                "medium": {"scale": "1080:-2", "crf": "26"},
                "high": {"scale": "1920:-2", "crf": "22"}
            }
            
            settings = compression_settings.get(quality, compression_settings["medium"])
            
            cmd = [
                self.ffmpeg_path,
                "-i", str(video_path),
                "-vf", f"scale={settings['scale']}",
                "-c:v", "libx264",
                "-crf", settings["crf"],
                "-preset", "medium",
                "-c:a", "aac",
                "-b:a", "96k",
                "-y",  # Overwrite output file
                str(compressed_path)
            ]
            
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            stdout, stderr = await process.communicate()
            
            if process.returncode != 0:
                raise Exception(f"Video compression failed: {stderr.decode()}")
            
            return compressed_path
            
        except Exception as e:
            logger.error(f"Video compression failed: {e}")
            raise
    
    async def validate_video_file(self, video_path: Path) -> bool:
        """
        Validate that the uploaded file is a valid video
        
        Args:
            video_path: Path to the video file
            
        Returns:
            True if valid video, False otherwise
        """
        try:
            metadata = await self.extract_metadata(video_path)
            return metadata.duration > 0 and metadata.resolution != "unknown"
        except Exception:
            return False


# Dependency injection
_video_upload_processor = None

def get_video_upload_processor() -> VideoUploadProcessor:
    """Get video upload processor instance"""
    global _video_upload_processor
    if _video_upload_processor is None:
        _video_upload_processor = VideoUploadProcessor()
    return _video_upload_processor