import uuid
import random
from celery import current_task
from sqlalchemy.orm import Session
from app.core.celery_app import celery_app
from app.db.session import SessionLocal
from app.models import Brand, Idea, Blueprint, Video, Job
import logging

logger = logging.getLogger(__name__)

@celery_app.task(name="generate_ideas")
def generate_ideas(brand_id: int, campaign_id: int, job_id: str):
    """
    Background task to generate viral content ideas
    """
    db = SessionLocal()
    try:
        # Update job status
        job = db.query(Job).filter(Job.job_id == job_id).first()
        if job:
            job.status = "processing"
            job.progress = 10
            db.commit()
        
        # Get brand information
        brand = db.query(Brand).filter(Brand.id == brand_id).first()
        if not brand:
            raise ValueError("Brand not found")
        
        current_task.update_state(state="PROGRESS", meta={"progress": 30})
        
        # Generate mock ideas (in real implementation, this would use AI)
        idea_hooks = [
            f"3 Mistakes Every {brand.name} Customer Makes",
            f"Why {brand.name} Is Better Than The Competition",
            f"Behind The Scenes: How {brand.name} Products Are Made",
            f"Customer Transformation Using {brand.name}",
            f"The Secret {brand.name} Doesn't Want You To Know"
        ]
        
        ideas = []
        for i, hook in enumerate(idea_hooks):
            current_task.update_state(state="PROGRESS", meta={"progress": 30 + (i * 10)})
            
            idea = Idea(
                brand_id=brand_id,
                campaign_id=campaign_id if campaign_id else None,
                hook=hook,
                viral_score=round(random.uniform(7.0, 9.9), 1),
                status="pending"
            )
            db.add(idea)
            ideas.append(idea)
        
        db.commit()
        
        # Update job as complete
        if job:
            job.status = "complete"
            job.progress = 100
            job.result = {
                "message": "Ideas generated successfully.",
                "ideasGenerated": len(ideas),
                "ideas": [{"ideaId": idea.id, "hook": idea.hook, "viralScore": idea.viral_score} for idea in ideas]
            }
            db.commit()
        
        return {"message": "Ideas generated successfully.", "count": len(ideas)}
        
    except Exception as e:
        logger.error(f"Idea generation failed: {str(e)}")
        
        if job:
            job.status = "failed"
            job.error = str(e)
            db.commit()
            
        raise e
    finally:
        db.close()

@celery_app.task(name="generate_blueprint")
def generate_blueprint(idea_id: int, job_id: str):
    """
    Background task to generate blueprint from approved idea
    """
    db = SessionLocal()
    try:
        # Update job status
        job = db.query(Job).filter(Job.job_id == job_id).first()
        if job:
            job.status = "processing"
            job.progress = 10
            db.commit()
        
        # Get idea
        idea = db.query(Idea).filter(Idea.id == idea_id).first()
        if not idea:
            raise ValueError("Idea not found")
        
        current_task.update_state(state="PROGRESS", meta={"progress": 30})
        
        # Generate script (mock implementation)
        script = f"""
HOOK: {idea.hook}

SCENE 1 - Opening Hook (0-3 seconds)
- Start with compelling question or statement
- Use text overlay: "{idea.hook}"

SCENE 2 - Problem/Context (3-8 seconds)
- Establish the problem or context
- Show relatable scenario

SCENE 3 - Solution/Product (8-15 seconds)
- Introduce your product/solution
- Demonstrate key benefits

SCENE 4 - Social Proof (15-20 seconds)
- Show testimonials or results
- Include before/after if applicable

SCENE 5 - Call to Action (20-25 seconds)
- Clear CTA: "Link in bio"
- Create urgency or incentive
"""
        
        current_task.update_state(state="PROGRESS", meta={"progress": 60})
        
        # Generate shot list
        shot_list = [
            {"shot": 1, "type": "close-up", "description": "Hook text overlay"},
            {"shot": 2, "type": "medium", "description": "Problem demonstration"},
            {"shot": 3, "type": "product", "description": "Product showcase"},
            {"shot": 4, "type": "testimonial", "description": "Customer testimonial"},
            {"shot": 5, "type": "cta", "description": "Call to action overlay"}
        ]
        
        current_task.update_state(state="PROGRESS", meta={"progress": 80})
        
        # Create blueprint
        blueprint = Blueprint(
            idea_id=idea_id,
            script=script,
            shot_list=shot_list,
            status="complete"
        )
        db.add(blueprint)
        
        # Update idea status
        idea.status = "approved"
        
        db.commit()
        
        # Update job as complete
        if job:
            job.status = "complete"
            job.progress = 100
            job.result = {
                "message": "Blueprint generated successfully.",
                "resourceId": str(blueprint.id),
                "blueprintId": blueprint.id
            }
            db.commit()
        
        return {"message": "Blueprint generated successfully.", "blueprintId": blueprint.id}
        
    except Exception as e:
        logger.error(f"Blueprint generation failed: {str(e)}")
        
        if job:
            job.status = "failed"
            job.error = str(e)
            db.commit()
            
        raise e
    finally:
        db.close()

@celery_app.task(name="generate_video")
def generate_video(blueprint_id: int, job_id: str):
    """
    Background task to generate AI video from blueprint
    """
    db = SessionLocal()
    try:
        # Update job status
        job = db.query(Job).filter(Job.job_id == job_id).first()
        if job:
            job.status = "processing"
            job.progress = 10
            db.commit()
        
        # Get blueprint
        blueprint = db.query(Blueprint).filter(Blueprint.id == blueprint_id).first()
        if not blueprint:
            raise ValueError("Blueprint not found")
        
        current_task.update_state(state="PROGRESS", meta={"progress": 30})
        
        # Simulate AI video generation (mock implementation)
        # In real implementation, this would call AI video generation APIs
        
        current_task.update_state(state="PROGRESS", meta={"progress": 70})
        
        # Create video record
        video = Video(
            blueprint_id=blueprint_id,
            video_url=f"https://storage.example.com/videos/{uuid.uuid4()}.mp4",
            thumbnail_url=f"https://storage.example.com/thumbnails/{uuid.uuid4()}.jpg",
            status="draft"
        )
        db.add(video)
        db.commit()
        
        # Update job as complete
        if job:
            job.status = "complete"
            job.progress = 100
            job.result = {
                "message": "AI video generated successfully.",
                "resourceId": str(video.id),
                "videoId": video.id,
                "videoUrl": video.video_url
            }
            db.commit()
        
        return {"message": "AI video generated successfully.", "videoId": video.id}
        
    except Exception as e:
        logger.error(f"Video generation failed: {str(e)}")
        
        if job:
            job.status = "failed"
            job.error = str(e)
            db.commit()
            
        raise e
    finally:
        db.close()