from fastapi import HTTPException, Request, status
from fastapi.responses import JSONResponse
from sqlalchemy.exc import SQLAlchemyError
import logging

logger = logging.getLogger(__name__)

class ViralOSException(Exception):
    """Base exception for ViralOS application"""
    def __init__(self, message: str, status_code: int = 500):
        self.message = message
        self.status_code = status_code
        super().__init__(self.message)

class BrandNotFoundError(ViralOSException):
    """Raised when a brand is not found or doesn't belong to user"""
    def __init__(self, message: str = "Brand not found"):
        super().__init__(message, status.HTTP_404_NOT_FOUND)

class JobNotFoundError(ViralOSException):
    """Raised when a job is not found"""
    def __init__(self, message: str = "Job not found"):
        super().__init__(message, status.HTTP_404_NOT_FOUND)

class ValidationError(ViralOSException):
    """Raised when validation fails"""
    def __init__(self, message: str = "Validation error"):
        super().__init__(message, status.HTTP_400_BAD_REQUEST)

async def viralos_exception_handler(request: Request, exc: ViralOSException):
    """Handle custom ViralOS exceptions"""
    logger.error(f"ViralOS exception: {exc.message}")
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.message}
    )

async def sqlalchemy_exception_handler(request: Request, exc: SQLAlchemyError):
    """Handle SQLAlchemy database exceptions"""
    logger.error(f"Database error: {str(exc)}")
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"detail": "Database error occurred"}
    )

async def general_exception_handler(request: Request, exc: Exception):
    """Handle general exceptions"""
    logger.error(f"Unexpected error: {str(exc)}")
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"detail": "Internal server error"}
    )