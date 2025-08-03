from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.exc import SQLAlchemyError
from slowapi.errors import RateLimitExceeded
from contextlib import asynccontextmanager
from app.core.config import settings
from app.core.logging import setup_logging
from app.core.exceptions import (
    ViralOSException, viralos_exception_handler,
    sqlalchemy_exception_handler, general_exception_handler
)
from app.core.rate_limiting import limiter, custom_rate_limit_exceeded_handler
from app.core.resource_manager import get_resource_manager, cleanup_all_resources
from app.api.v1.api import api_router

# Set up logging
setup_logging()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan management"""
    # Startup
    resource_manager = await get_resource_manager()
    app.state.resource_manager = resource_manager
    
    yield
    
    # Shutdown
    await cleanup_all_resources()


app = FastAPI(
    title="ViralOS API",
    description="AI-Powered Video Marketing Platform",
    version="1.0.0",
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
    lifespan=lifespan
)

# Add rate limiter to app
app.state.limiter = limiter

# Exception handlers
app.add_exception_handler(RateLimitExceeded, custom_rate_limit_exceeded_handler)
app.add_exception_handler(ViralOSException, viralos_exception_handler)
app.add_exception_handler(SQLAlchemyError, sqlalchemy_exception_handler)
app.add_exception_handler(Exception, general_exception_handler)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.BACKEND_CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API router
app.include_router(api_router, prefix=settings.API_V1_STR)

@app.get("/")
async def root():
    return {"message": "ViralOS API is running"}

@app.get("/health")
async def health_check():
    return {"status": "healthy"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=True)