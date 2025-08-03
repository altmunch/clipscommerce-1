from fastapi import APIRouter

from app.api.v1.endpoints import core_pipeline

api_router = APIRouter()

# Core pipeline - the only endpoint we need
api_router.include_router(core_pipeline.router, prefix="/pipeline", tags=["pipeline"])