from fastapi import APIRouter

from app.api.v1.endpoints import auth, brands, campaigns, content, results, jobs

api_router = APIRouter()

api_router.include_router(auth.router, prefix="/auth", tags=["authentication"])
api_router.include_router(brands.router, prefix="/brands", tags=["brands"])
api_router.include_router(campaigns.router, prefix="/campaigns", tags=["campaigns"])
api_router.include_router(content.router, prefix="", tags=["content"])
api_router.include_router(results.router, prefix="/results", tags=["results"])
api_router.include_router(jobs.router, prefix="/jobs", tags=["jobs"])