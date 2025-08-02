from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.models.job import Job
from app.schemas.job import JobResponse

router = APIRouter()

@router.get("/{job_id}/status", response_model=JobResponse)
def get_job_status(
    job_id: str,
    db: Session = Depends(get_db)
):
    """
    Get the status of an asynchronous job
    """
    job = db.query(Job).filter(Job.job_id == job_id).first()
    
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Job not found"
        )
    
    return JobResponse(
        jobId=job.job_id,
        status=job.status,
        progress=job.progress,
        result=job.result,
        error=job.error
    )