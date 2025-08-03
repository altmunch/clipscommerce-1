from fastapi import APIRouter

from app.api.v1.endpoints import auth, brands, campaigns, content, results, jobs, scraping, tiktok, video_generation, analytics, social_media

api_router = APIRouter()

api_router.include_router(auth.router, prefix="/auth", tags=["authentication"])
api_router.include_router(brands.router, prefix="/brands", tags=["brands"])
api_router.include_router(campaigns.router, prefix="/campaigns", tags=["campaigns"])
api_router.include_router(content.router, prefix="", tags=["content"])
api_router.include_router(results.router, prefix="/results", tags=["results"])
api_router.include_router(jobs.router, prefix="/jobs", tags=["jobs"])
api_router.include_router(scraping.router, prefix="/scraping", tags=["scraping"])
api_router.include_router(tiktok.router, prefix="/tiktok", tags=["tiktok"])
api_router.include_router(video_generation.router, prefix="/video", tags=["video_generation"])
api_router.include_router(analytics.router, prefix="/analytics", tags=["analytics"])
api_router.include_router(social_media.router, prefix="/social-media", tags=["social_media"])