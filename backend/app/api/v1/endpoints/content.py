from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.api.deps import get_current_user
from app.models.user import User
from app.models.brand import Brand
from app.models.content import Idea, Blueprint, Video
from app.models.job import Job
from app.schemas.content import (
    IdeaGenerateRequest, IdeaGenerateResponse, IdeasResponse, Idea as IdeaSchema,
    BlueprintGenerateRequest, BlueprintGenerateResponse,
    VideoGenerateRequest, VideoGenerateResponse,
    VideoOptimizeRequest, VideoOptimizeResponse,
    VideoScheduleRequest, VideoScheduleResponse
)
from app.tasks.content_tasks import generate_ideas, generate_blueprint, generate_video
import uuid
from typing import List

router = APIRouter()

@router.post("/ideas/generate", status_code=202, response_model=IdeaGenerateResponse)
async def generate_ideas_endpoint(
    request: IdeaGenerateRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Generate viral content ideas based on brand kit and trends
    """
    # Verify brand belongs to user
    brand = db.query(Brand).filter(
        Brand.id == request.brandId,
        Brand.user_id == current_user.id
    ).first()
    
    if not brand:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Brand not found"
        )
    
    # Create job record
    job_id = str(uuid.uuid4())
    job = Job(
        job_id=job_id,
        job_type="generate_ideas",
        status="processing",
        progress=0
    )
    db.add(job)
    db.commit()
    
    # Start background task
    generate_ideas.delay(request.brandId, request.campaignId, job_id)
    
    return IdeaGenerateResponse(
        jobId=job_id,
        message="Idea generation started."
    )

@router.get("/ideas", response_model=IdeasResponse)
def get_ideas(
    brand_id: int = Query(..., alias="brandId"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get generated ideas for a brand
    """
    # Verify brand belongs to user
    brand = db.query(Brand).filter(
        Brand.id == brand_id,
        Brand.user_id == current_user.id
    ).first()
    
    if not brand:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Brand not found"
        )
    
    # Get ideas for the brand
    ideas = db.query(Idea).filter(Idea.brand_id == brand_id).all()
    
    idea_schemas = [
        IdeaSchema(
            ideaId=idea.id,
            hook=idea.hook,
            status=idea.status,
            viralScore=idea.viral_score
        )
        for idea in ideas
    ]
    
    return IdeasResponse(data=idea_schemas)

@router.post("/blueprints/generate", status_code=202, response_model=BlueprintGenerateResponse)
async def generate_blueprint_endpoint(
    request: BlueprintGenerateRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Generate detailed blueprint from approved idea
    """
    # Verify idea exists and belongs to user's brand
    idea = db.query(Idea).join(Brand).filter(
        Idea.id == request.ideaId,
        Brand.user_id == current_user.id
    ).first()
    
    if not idea:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Idea not found"
        )
    
    # Create job record
    job_id = str(uuid.uuid4())
    job = Job(
        job_id=job_id,
        job_type="generate_blueprint",
        status="processing",
        progress=0
    )
    db.add(job)
    db.commit()
    
    # Start background task
    generate_blueprint.delay(request.ideaId, job_id)
    
    return BlueprintGenerateResponse(
        jobId=job_id,
        message="Blueprint generation started."
    )

@router.post("/videos/generate-ai", status_code=202, response_model=VideoGenerateResponse)
async def generate_video_endpoint(
    request: VideoGenerateRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Generate AI video from blueprint
    """
    # Verify blueprint exists and belongs to user's brand
    blueprint = db.query(Blueprint).join(Idea).join(Brand).filter(
        Blueprint.id == request.blueprintId,
        Brand.user_id == current_user.id
    ).first()
    
    if not blueprint:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Blueprint not found"
        )
    
    # Create job record
    job_id = str(uuid.uuid4())
    job = Job(
        job_id=job_id,
        job_type="generate_video",
        status="processing",
        progress=0
    )
    db.add(job)
    db.commit()
    
    # Start background task
    generate_video.delay(request.blueprintId, job_id)
    
    return VideoGenerateResponse(
        jobId=job_id,
        message="AI video generation started."
    )

@router.put("/videos/{video_id}/optimize", response_model=VideoOptimizeResponse)
def optimize_video(
    video_id: int,
    request: VideoOptimizeRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Update video with optimization data (caption, hashtags, CTA)
    """
    # Verify video exists and belongs to user's brand
    video = db.query(Video).join(Blueprint).join(Idea).join(Brand).filter(
        Video.id == video_id,
        Brand.user_id == current_user.id
    ).first()
    
    if not video:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Video not found"
        )
    
    # Update video with optimization data
    video.caption = request.caption
    video.hashtags = request.hashtags
    video.cta = request.cta
    video.status = "optimized"
    
    db.commit()
    
    return VideoOptimizeResponse(message="Video optimized successfully.")

@router.post("/videos/{video_id}/schedule", response_model=VideoScheduleResponse)
def schedule_video(
    video_id: int,
    request: VideoScheduleRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Schedule optimized video for publishing
    """
    # Verify video exists and belongs to user's brand
    video = db.query(Video).join(Blueprint).join(Idea).join(Brand).filter(
        Video.id == video_id,
        Brand.user_id == current_user.id
    ).first()
    
    if not video:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Video not found"
        )
    
    # Schedule video
    video.scheduled_at = request.publishAt
    video.platforms = request.platforms
    video.status = "scheduled"
    
    db.commit()
    
    return VideoScheduleResponse(message="Video scheduled for publishing.")