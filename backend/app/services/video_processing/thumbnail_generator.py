"""
Video thumbnail generation service
"""

import logging
import asyncio
from typing import Optional, List
from pathlib import Path
import uuid

logger = logging.getLogger(__name__)


class ThumbnailGenerator:
    """Service for generating thumbnails from video files"""
    
    def __init__(self):
        self.ffmpeg_path = "ffmpeg"
    
    async def generate_thumbnail(
        self, 
        video_path: Path, 
        timestamp: str = "00:00:01",
        output_path: Optional[Path] = None
    ) -> Path:
        """
        Generate a single thumbnail from video at specified timestamp
        
        Args:
            video_path: Path to the video file
            timestamp: Time position to extract frame (HH:MM:SS format)
            output_path: Optional custom output path
            
        Returns:
            Path to the generated thumbnail
        """
        try:
            if output_path is None:
                output_path = video_path.parent / f"{video_path.stem}_thumbnail.jpg"
            
            cmd = [
                self.ffmpeg_path,
                "-i", str(video_path),
                "-ss", timestamp,
                "-vframes", "1",
                "-vf", "scale=320:240",  # Standard thumbnail size
                "-q:v", "2",  # High quality
                "-y",  # Overwrite output file
                str(output_path)
            ]
            
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            stdout, stderr = await process.communicate()
            
            if process.returncode != 0:
                raise Exception(f"Thumbnail generation failed: {stderr.decode()}")
            
            return output_path
            
        except Exception as e:
            logger.error(f"Thumbnail generation failed: {e}")
            raise
    
    async def generate_multiple_thumbnails(
        self,
        video_path: Path,
        count: int = 3,
        output_dir: Optional[Path] = None
    ) -> List[Path]:
        """
        Generate multiple thumbnails at different timestamps
        
        Args:
            video_path: Path to the video file
            count: Number of thumbnails to generate
            output_dir: Directory to save thumbnails
            
        Returns:
            List of paths to generated thumbnails
        """
        try:
            if output_dir is None:
                output_dir = video_path.parent
            
            # Get video duration first
            duration = await self._get_video_duration(video_path)
            if duration <= 0:
                raise Exception("Could not determine video duration")
            
            thumbnails = []
            
            # Generate thumbnails at evenly spaced intervals
            for i in range(count):
                # Calculate timestamp (avoid first and last second)
                timestamp_seconds = (duration / (count + 1)) * (i + 1)
                timestamp = self._seconds_to_timestamp(timestamp_seconds)
                
                thumbnail_path = output_dir / f"{video_path.stem}_thumb_{i+1}.jpg"
                
                cmd = [
                    self.ffmpeg_path,
                    "-i", str(video_path),
                    "-ss", timestamp,
                    "-vframes", "1",
                    "-vf", "scale=320:240",
                    "-q:v", "2",
                    "-y",
                    str(thumbnail_path)
                ]
                
                process = await asyncio.create_subprocess_exec(
                    *cmd,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE
                )
                
                stdout, stderr = await process.communicate()
                
                if process.returncode == 0 and thumbnail_path.exists():
                    thumbnails.append(thumbnail_path)
                else:
                    logger.warning(f"Failed to generate thumbnail {i+1}: {stderr.decode()}")
            
            return thumbnails
            
        except Exception as e:
            logger.error(f"Multiple thumbnail generation failed: {e}")
            return []
    
    async def generate_animated_thumbnail(
        self,
        video_path: Path,
        duration: int = 3,
        output_path: Optional[Path] = None
    ) -> Path:
        """
        Generate an animated GIF thumbnail from video
        
        Args:
            video_path: Path to the video file
            duration: Duration of the GIF in seconds
            output_path: Optional custom output path
            
        Returns:
            Path to the generated animated thumbnail
        """
        try:
            if output_path is None:
                output_path = video_path.parent / f"{video_path.stem}_animated.gif"
            
            cmd = [
                self.ffmpeg_path,
                "-i", str(video_path),
                "-ss", "00:00:01",  # Start at 1 second
                "-t", str(duration),  # Duration
                "-vf", "scale=200:150:flags=lanczos,fps=10",  # Scale and reduce fps
                "-y",
                str(output_path)
            ]
            
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            stdout, stderr = await process.communicate()
            
            if process.returncode != 0:
                raise Exception(f"Animated thumbnail generation failed: {stderr.decode()}")
            
            return output_path
            
        except Exception as e:
            logger.error(f"Animated thumbnail generation failed: {e}")
            raise
    
    async def generate_contact_sheet(
        self,
        video_path: Path,
        grid_size: str = "3x3",
        output_path: Optional[Path] = None
    ) -> Path:
        """
        Generate a contact sheet (grid of thumbnails) from video
        
        Args:
            video_path: Path to the video file
            grid_size: Grid layout (e.g., "3x3", "4x4")
            output_path: Optional custom output path
            
        Returns:
            Path to the generated contact sheet
        """
        try:
            if output_path is None:
                output_path = video_path.parent / f"{video_path.stem}_contact_sheet.jpg"
            
            cmd = [
                self.ffmpeg_path,
                "-i", str(video_path),
                "-vf", f"fps=1/10,scale=160:120,tile={grid_size}",
                "-y",
                str(output_path)
            ]
            
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            stdout, stderr = await process.communicate()
            
            if process.returncode != 0:
                raise Exception(f"Contact sheet generation failed: {stderr.decode()}")
            
            return output_path
            
        except Exception as e:
            logger.error(f"Contact sheet generation failed: {e}")
            raise
    
    async def _get_video_duration(self, video_path: Path) -> float:
        """Get video duration in seconds"""
        try:
            cmd = [
                "ffprobe",
                "-v", "quiet",
                "-show_entries", "format=duration",
                "-of", "csv=p=0",
                str(video_path)
            ]
            
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            stdout, stderr = await process.communicate()
            
            if process.returncode != 0:
                raise Exception(f"Duration extraction failed: {stderr.decode()}")
            
            return float(stdout.decode().strip())
            
        except Exception as e:
            logger.error(f"Duration extraction failed: {e}")
            return 0.0
    
    def _seconds_to_timestamp(self, seconds: float) -> str:
        """Convert seconds to HH:MM:SS timestamp format"""
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = int(seconds % 60)
        return f"{hours:02d}:{minutes:02d}:{secs:02d}"


# Dependency injection
_thumbnail_generator = None

def get_thumbnail_generator() -> ThumbnailGenerator:
    """Get thumbnail generator instance"""
    global _thumbnail_generator
    if _thumbnail_generator is None:
        _thumbnail_generator = ThumbnailGenerator()
    return _thumbnail_generator