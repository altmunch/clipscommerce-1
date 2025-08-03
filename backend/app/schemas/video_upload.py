"""
Pydantic schemas for video upload functionality
"""

from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field
from datetime import datetime


class VideoUploadBase(BaseModel):
    """Base schema for video uploads"""
    title: str = Field(..., description="Video title")
    description: Optional[str] = Field(None, description="Video description")
    target_platform: str = Field("tiktok", description="Target platform")
    tags: List[str] = Field(default_factory=list, description="Video tags")


class VideoUploadCreate(VideoUploadBase):
    """Schema for creating video upload"""
    product_id: str = Field(..., description="Associated product ID")
    brand_id: Optional[str] = Field(None, description="Associated brand ID")
    is_ugc: bool = Field(False, description="Whether this is user-generated content")


class VideoUploadResponse(VideoUploadBase):
    """Schema for video upload response"""
    id: str
    project_id: str
    status: str
    video_url: str
    thumbnail_url: Optional[str]
    duration: float
    file_size: int
    processing_status: str
    created_at: datetime
    
    class Config:
        from_attributes = True


class VideoClipUploadBase(BaseModel):
    """Base schema for video clip uploads"""
    clip_title: str = Field(..., description="Clip title")
    segment_number: int = Field(..., description="Order within project")
    start_time: float = Field(0.0, description="Start time in seconds")
    end_time: Optional[float] = Field(None, description="End time in seconds")
    description: Optional[str] = Field(None, description="Clip description")


class VideoClipUploadCreate(VideoClipUploadBase):
    """Schema for creating video clip upload"""
    project_id: str = Field(..., description="Parent project ID")


class VideoClipUploadResponse(VideoClipUploadBase):
    """Schema for video clip upload response"""
    id: str
    project_id: str
    status: str
    video_url: str
    duration: float
    file_size: int
    created_at: datetime
    
    class Config:
        from_attributes = True


class VideoProjectListItem(BaseModel):
    """Schema for video project list item"""
    id: str
    title: str
    description: Optional[str]
    project_type: str
    target_platform: str
    duration: float
    status: str
    video_url: str
    thumbnail_url: Optional[str]
    created_at: datetime
    tags: List[str]
    
    class Config:
        from_attributes = True


class VideoProjectListResponse(BaseModel):
    """Schema for video project list response"""
    projects: List[VideoProjectListItem]
    total: int
    limit: int
    offset: int


class VideoUploadStatusResponse(BaseModel):
    """Schema for video upload status response"""
    video_id: str
    status: str
    processing_progress: float
    error_message: Optional[str]
    estimated_completion: Optional[datetime]


class VideoMetadataResponse(BaseModel):
    """Schema for video metadata response"""
    duration: float
    resolution: str
    fps: int
    file_size: int
    format: str
    codec: str
    bitrate: Optional[int]
    
    class Config:
        from_attributes = True


class BulkVideoUploadRequest(BaseModel):
    """Schema for bulk video upload request"""
    product_id: str = Field(..., description="Associated product ID")
    brand_id: Optional[str] = Field(None, description="Associated brand ID")
    project_title: str = Field(..., description="Project title")
    project_description: Optional[str] = Field(None, description="Project description")
    target_platform: str = Field("tiktok", description="Target platform")
    is_ugc: bool = Field(False, description="Whether this is user-generated content")


class BulkVideoUploadResponse(BaseModel):
    """Schema for bulk video upload response"""
    project_id: str
    uploaded_clips: List[VideoClipUploadResponse]
    total_clips: int
    failed_uploads: List[Dict[str, Any]]
    total_duration: float
    total_file_size: int


class VideoProcessingOptions(BaseModel):
    """Schema for video processing options"""
    generate_thumbnail: bool = Field(True, description="Generate video thumbnail")
    extract_audio: bool = Field(False, description="Extract audio track")
    optimize_for_platform: bool = Field(True, description="Optimize for target platform")
    compress_video: bool = Field(False, description="Compress video file")
    target_quality: str = Field("medium", description="Target quality level")


class VideoUploadWithProcessing(VideoUploadCreate):
    """Schema for video upload with processing options"""
    processing_options: VideoProcessingOptions = Field(default_factory=VideoProcessingOptions)


class UserVideoLibrary(BaseModel):
    """Schema for user's video library"""
    user_id: str
    total_videos: int
    total_duration: float
    total_storage_used: int  # in bytes
    videos_by_platform: Dict[str, int]
    recent_uploads: List[VideoProjectListItem]
    
    class Config:
        from_attributes = True