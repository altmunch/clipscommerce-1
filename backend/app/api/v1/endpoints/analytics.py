from typing import List, Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form, BackgroundTasks
from sqlalchemy.orm import Session
from pydantic import BaseModel
from datetime import datetime

from app.api.deps import get_db, get_current_user
from app.models.user import User
from app.models.analytics import (
    VideoPerformancePrediction, TrendRecommendation, ABTestExperiment, 
    ABTestVariant, PlatformType, ExperimentStatus
)
from app.services.analytics.video_analyzer import VideoAnalyzer
from app.services.analytics.performance_predictor import PerformancePredictor, PredictionResult
from app.services.analytics.trend_engine import TrendRecommendationEngine, RecommendationFilter
from app.services.optimization.ab_testing import (
    ABTestingService, ABTestConfig, VariationConfig, VariantType
)
from app.tasks.analytics_tasks import process_video_analysis, update_trend_data
import tempfile
import os
from pathlib import Path

router = APIRouter()

# Pydantic models for request/response

class VideoAnalysisRequest(BaseModel):
    video_id: int
    platform: PlatformType
    metadata: Optional[Dict[str, Any]] = None

class VideoAnalysisResponse(BaseModel):
    video_id: int
    platform: str
    overall_score: float
    confidence_interval: float
    predicted_views: int
    predicted_engagement_rate: float
    hook_score: float
    content_score: float
    cta_score: float
    recommendations: List[str]
    visual_analysis: Dict[str, Any]
    audio_analysis: Dict[str, Any]
    processing_time: float
    model_version: str

class TrendRequest(BaseModel):
    brand_id: int
    platform: PlatformType
    industry: Optional[str] = None
    target_audience: Optional[str] = None
    min_virality_score: float = 50.0
    max_age_days: int = 7

class TrendResponse(BaseModel):
    trend_id: str
    name: str
    description: str
    trend_type: str
    volume: int
    growth_rate: float
    virality_score: float
    relevance_score: float
    audio_url: Optional[str]
    audio_duration: Optional[float]
    audio_mood: Optional[str]
    copyright_status: Optional[str]
    recommended_usage_window: Dict[str, Any]

class ABTestCreateRequest(BaseModel):
    original_video_id: int
    brand_id: int
    campaign_id: int
    test_name: str
    hypothesis: str
    success_metrics: List[str]
    traffic_split: Dict[str, float]
    minimum_sample_size: int = 1000
    confidence_level: float = 0.95
    planned_duration_days: int = 7
    variation_types: List[str]  # ['hook', 'cta', 'text_overlay', etc.]
    variation_count_per_type: int = 2

class ABTestResponse(BaseModel):
    experiment_id: int
    name: str
    status: str
    variants_count: int
    start_date: Optional[datetime]
    end_date: Optional[datetime]
    current_sample_size: int
    statistical_significance: Optional[float]
    winner_variant: Optional[str]

class ABTestAnalysisResponse(BaseModel):
    experiment_id: int
    status: str
    analysis_results: Dict[str, Any]
    winner_analysis: Dict[str, Any]
    recommendations: List[str]

# Initialize services
video_analyzer = VideoAnalyzer()
performance_predictor = PerformancePredictor()
trend_engine = TrendRecommendationEngine()
ab_testing_service = ABTestingService()

@router.post("/analyze-video/", response_model=VideoAnalysisResponse)
async def analyze_video(
    request: VideoAnalysisRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Analyze video for performance prediction
    """
    try:
        # Check if video exists
        # Note: You'd need to implement video lookup from your video model
        # For now, we'll proceed with the analysis
        
        # Add background task for analysis
        background_tasks.add_task(
            process_video_analysis,
            request.video_id,
            request.platform,
            request.metadata
        )
        
        # Return immediate response - actual analysis runs in background
        return VideoAnalysisResponse(
            video_id=request.video_id,
            platform=request.platform.value,
            overall_score=0.0,
            confidence_interval=0.0,
            predicted_views=0,
            predicted_engagement_rate=0.0,
            hook_score=0.0,
            content_score=0.0,
            cta_score=0.0,
            recommendations=[],
            visual_analysis={},
            audio_analysis={},
            processing_time=0.0,
            model_version="1.0",
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error analyzing video: {str(e)}"
        )

@router.post("/analyze-video-file/", response_model=VideoAnalysisResponse)
async def analyze_video_file(
    file: UploadFile = File(...),
    platform: str = Form(...),
    metadata: Optional[str] = Form(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Analyze uploaded video file directly
    """
    try:
        # Validate platform
        try:
            platform_enum = PlatformType(platform)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid platform: {platform}"
            )
        
        # Save uploaded file temporarily
        with tempfile.NamedTemporaryFile(delete=False, suffix=".mp4") as temp_file:
            content = await file.read()
            temp_file.write(content)
            temp_file_path = temp_file.name
        
        try:
            # Parse metadata if provided
            video_metadata = {}
            if metadata:
                import json
                video_metadata = json.loads(metadata)
            
            # Perform analysis
            prediction_result = await performance_predictor.predict_performance(
                temp_file_path,
                platform_enum,
                video_metadata
            )
            
            # Get detailed analysis
            analysis_result = await video_analyzer.analyze_video(temp_file_path)
            
            return VideoAnalysisResponse(
                video_id=0,  # No video ID for direct file upload
                platform=platform,
                overall_score=prediction_result.overall_score,
                confidence_interval=prediction_result.confidence_interval,
                predicted_views=prediction_result.predicted_views,
                predicted_engagement_rate=prediction_result.predicted_engagement_rate,
                hook_score=prediction_result.hook_score,
                content_score=prediction_result.content_score,
                cta_score=prediction_result.cta_score,
                recommendations=prediction_result.recommendations,
                visual_analysis=analysis_result.get('visual_metrics', {}),
                audio_analysis=analysis_result.get('audio_metrics', {}),
                processing_time=analysis_result.get('processing_time', 0.0),
                model_version=prediction_result.model_version
            )
            
        finally:
            # Clean up temporary file
            os.unlink(temp_file_path)
            
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error analyzing video file: {str(e)}"
        )

@router.get("/video-analysis/{video_id}", response_model=VideoAnalysisResponse)
async def get_video_analysis(
    video_id: int,
    platform: PlatformType,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get existing video analysis results
    """
    try:
        # Get analysis from database
        analysis = db.query(VideoPerformancePrediction).filter(
            VideoPerformancePrediction.video_id == video_id,
            VideoPerformancePrediction.platform == platform
        ).first()
        
        if not analysis:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Video analysis not found"
            )
        
        return VideoAnalysisResponse(
            video_id=video_id,
            platform=platform.value,
            overall_score=analysis.overall_score,
            confidence_interval=analysis.confidence_interval,
            predicted_views=analysis.predicted_views or 0,
            predicted_engagement_rate=analysis.predicted_engagement_rate or 0.0,
            hook_score=analysis.hook_score,
            content_score=analysis.content_score,
            cta_score=analysis.cta_score,
            recommendations=analysis.recommendations or [],
            visual_analysis=analysis.visual_analysis or {},
            audio_analysis=analysis.audio_analysis or {},
            processing_time=analysis.processing_time or 0.0,
            model_version=analysis.model_version
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error retrieving video analysis: {str(e)}"
        )

@router.post("/trends/", response_model=List[TrendResponse])
async def get_trend_recommendations(
    request: TrendRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get trend recommendations for a brand
    """
    try:
        # Create filter
        filters = RecommendationFilter(
            brand_id=request.brand_id,
            platform=request.platform,
            industry=request.industry,
            target_audience=request.target_audience,
            min_virality_score=request.min_virality_score,
            max_age_days=request.max_age_days
        )
        
        # Get recommendations
        recommendations = await trend_engine.get_trend_recommendations(
            request.brand_id,
            request.platform,
            filters
        )
        
        # Add background task to update trend data
        background_tasks.add_task(update_trend_data, request.platform.value)
        
        return [
            TrendResponse(
                trend_id=rec.trend_id,
                name=rec.trend_name,
                description=rec.trend_description,
                trend_type=rec.trend_type,
                volume=rec.trend_volume,
                growth_rate=rec.growth_rate,
                virality_score=rec.virality_score,
                relevance_score=rec.relevance_score,
                audio_url=rec.audio_url,
                audio_duration=rec.audio_duration,
                audio_mood=rec.audio_mood,
                copyright_status=rec.copyright_status,
                recommended_usage_window=rec.recommended_usage_window or {}
            )
            for rec in recommendations
        ]
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error getting trend recommendations: {str(e)}"
        )

@router.get("/trends/{brand_id}", response_model=List[TrendResponse])
async def get_saved_trends(
    brand_id: int,
    platform: Optional[PlatformType] = None,
    limit: int = 20,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get saved trend recommendations for a brand
    """
    try:
        query = db.query(TrendRecommendation).filter(
            TrendRecommendation.brand_id == brand_id,
            TrendRecommendation.is_active == True
        )
        
        if platform:
            query = query.filter(TrendRecommendation.platform == platform)
        
        trends = query.order_by(TrendRecommendation.virality_score.desc()).limit(limit).all()
        
        return [
            TrendResponse(
                trend_id=trend.trend_id,
                name=trend.trend_name,
                description=trend.trend_description,
                trend_type=trend.trend_type,
                volume=trend.trend_volume,
                growth_rate=trend.growth_rate,
                virality_score=trend.virality_score,
                relevance_score=trend.relevance_score,
                audio_url=trend.audio_url,
                audio_duration=trend.audio_duration,
                audio_mood=trend.audio_mood,
                copyright_status=trend.copyright_status,
                recommended_usage_window=trend.recommended_usage_window or {}
            )
            for trend in trends
        ]
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error retrieving saved trends: {str(e)}"
        )

@router.post("/ab-test/", response_model=ABTestResponse)
async def create_ab_test(
    request: ABTestCreateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Create a new A/B test experiment
    """
    try:
        # Create test configuration
        test_config = ABTestConfig(
            test_name=request.test_name,
            hypothesis=request.hypothesis,
            success_metrics=request.success_metrics,
            traffic_split=request.traffic_split,
            minimum_sample_size=request.minimum_sample_size,
            confidence_level=request.confidence_level,
            planned_duration_days=request.planned_duration_days
        )
        
        # Create variation configurations
        variation_configs = []
        for variant_type in request.variation_types:
            try:
                variant_enum = VariantType(variant_type)
                config = VariationConfig(
                    element_type=variant_enum,
                    variation_count=request.variation_count_per_type
                )
                variation_configs.append(config)
            except ValueError:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Invalid variation type: {variant_type}"
                )
        
        # Create experiment
        experiment = await ab_testing_service.create_ab_test(
            request.original_video_id,
            request.brand_id,
            request.campaign_id,
            test_config,
            variation_configs
        )
        
        # Count variants
        variant_count = db.query(ABTestVariant).filter(
            ABTestVariant.experiment_id == experiment.id
        ).count()
        
        return ABTestResponse(
            experiment_id=experiment.id,
            name=experiment.name,
            status=experiment.status.value,
            variants_count=variant_count,
            start_date=experiment.start_date,
            end_date=experiment.end_date,
            current_sample_size=experiment.current_sample_size,
            statistical_significance=experiment.statistical_significance,
            winner_variant=experiment.winner_variant
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error creating A/B test: {str(e)}"
        )

@router.post("/ab-test/{experiment_id}/start")
async def start_ab_test(
    experiment_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Start an A/B test experiment
    """
    try:
        experiment = await ab_testing_service.start_experiment(experiment_id)
        
        return {
            "message": "Experiment started successfully",
            "experiment_id": experiment_id,
            "status": experiment.status.value,
            "start_date": experiment.start_date
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error starting experiment: {str(e)}"
        )

@router.get("/ab-test/{experiment_id}/analysis", response_model=ABTestAnalysisResponse)
async def analyze_ab_test(
    experiment_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Analyze A/B test results
    """
    try:
        analysis = await ab_testing_service.analyze_experiment(experiment_id)
        
        return ABTestAnalysisResponse(
            experiment_id=experiment_id,
            status=analysis['status'],
            analysis_results=analysis['analysis_results'],
            winner_analysis=analysis['winner_analysis'],
            recommendations=analysis['recommendations']
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error analyzing experiment: {str(e)}"
        )

@router.get("/ab-test/{experiment_id}", response_model=ABTestResponse)
async def get_ab_test(
    experiment_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get A/B test experiment details
    """
    try:
        experiment = db.query(ABTestExperiment).filter(
            ABTestExperiment.id == experiment_id
        ).first()
        
        if not experiment:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Experiment not found"
            )
        
        variant_count = db.query(ABTestVariant).filter(
            ABTestVariant.experiment_id == experiment_id
        ).count()
        
        return ABTestResponse(
            experiment_id=experiment.id,
            name=experiment.name,
            status=experiment.status.value,
            variants_count=variant_count,
            start_date=experiment.start_date,
            end_date=experiment.end_date,
            current_sample_size=experiment.current_sample_size,
            statistical_significance=experiment.statistical_significance,
            winner_variant=experiment.winner_variant
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error retrieving experiment: {str(e)}"
        )

@router.get("/ab-test/{experiment_id}/variants")
async def get_ab_test_variants(
    experiment_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get all variants for an A/B test
    """
    try:
        variants = db.query(ABTestVariant).filter(
            ABTestVariant.experiment_id == experiment_id
        ).all()
        
        return [
            {
                "variant_id": variant.id,
                "variant_name": variant.variant_name,
                "variant_type": variant.variant_type,
                "description": variant.description,
                "modifications": variant.modifications,
                "impressions": variant.impressions,
                "clicks": variant.clicks,
                "conversions": variant.conversions,
                "conversion_rate": variant.conversion_rate,
                "engagement_rate": variant.engagement_rate,
                "is_active": variant.is_active
            }
            for variant in variants
        ]
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error retrieving variants: {str(e)}"
        )

@router.get("/experiments/", response_model=List[ABTestResponse])
async def list_experiments(
    brand_id: Optional[int] = None,
    status: Optional[ExperimentStatus] = None,
    limit: int = 20,
    offset: int = 0,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    List A/B test experiments
    """
    try:
        query = db.query(ABTestExperiment)
        
        if brand_id:
            query = query.filter(ABTestExperiment.brand_id == brand_id)
        
        if status:
            query = query.filter(ABTestExperiment.status == status)
        
        experiments = query.order_by(ABTestExperiment.created_at.desc()).offset(offset).limit(limit).all()
        
        results = []
        for experiment in experiments:
            variant_count = db.query(ABTestVariant).filter(
                ABTestVariant.experiment_id == experiment.id
            ).count()
            
            results.append(ABTestResponse(
                experiment_id=experiment.id,
                name=experiment.name,
                status=experiment.status.value,
                variants_count=variant_count,
                start_date=experiment.start_date,
                end_date=experiment.end_date,
                current_sample_size=experiment.current_sample_size,
                statistical_significance=experiment.statistical_significance,
                winner_variant=experiment.winner_variant
            ))
        
        return results
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error listing experiments: {str(e)}"
        )

@router.delete("/ab-test/{experiment_id}")
async def delete_ab_test(
    experiment_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Delete an A/B test experiment
    """
    try:
        experiment = db.query(ABTestExperiment).filter(
            ABTestExperiment.id == experiment_id
        ).first()
        
        if not experiment:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Experiment not found"
            )
        
        # Can only delete draft experiments
        if experiment.status != ExperimentStatus.DRAFT:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Can only delete draft experiments"
            )
        
        db.delete(experiment)
        db.commit()
        
        return {"message": "Experiment deleted successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error deleting experiment: {str(e)}"
        )

@router.get("/analytics/dashboard/{brand_id}")
async def get_analytics_dashboard(
    brand_id: int,
    days: int = 30,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get analytics dashboard data for a brand
    """
    try:
        cutoff_date = datetime.now() - timedelta(days=days)
        
        # Get recent video analyses
        recent_analyses = db.query(VideoPerformancePrediction).filter(
            VideoPerformancePrediction.created_at >= cutoff_date
        ).order_by(VideoPerformancePrediction.created_at.desc()).limit(10).all()
        
        # Get active trends
        active_trends = db.query(TrendRecommendation).filter(
            TrendRecommendation.brand_id == brand_id,
            TrendRecommendation.is_active == True
        ).order_by(TrendRecommendation.virality_score.desc()).limit(5).all()
        
        # Get running experiments
        running_experiments = db.query(ABTestExperiment).filter(
            ABTestExperiment.brand_id == brand_id,
            ABTestExperiment.status == ExperimentStatus.RUNNING
        ).all()
        
        # Calculate summary statistics
        if recent_analyses:
            avg_score = sum(a.overall_score for a in recent_analyses) / len(recent_analyses)
            avg_confidence = sum(a.confidence_interval for a in recent_analyses) / len(recent_analyses)
        else:
            avg_score = 0
            avg_confidence = 0
        
        return {
            "summary": {
                "total_analyses": len(recent_analyses),
                "average_score": round(avg_score, 2),
                "average_confidence": round(avg_confidence, 2),
                "active_trends": len(active_trends),
                "running_experiments": len(running_experiments)
            },
            "recent_analyses": [
                {
                    "video_id": a.video_id,
                    "platform": a.platform.value,
                    "overall_score": a.overall_score,
                    "created_at": a.created_at
                }
                for a in recent_analyses
            ],
            "top_trends": [
                {
                    "name": t.trend_name,
                    "type": t.trend_type,
                    "virality_score": t.virality_score,
                    "relevance_score": t.relevance_score
                }
                for t in active_trends
            ],
            "experiments": [
                {
                    "name": e.name,
                    "status": e.status.value,
                    "start_date": e.start_date,
                    "current_sample_size": e.current_sample_size
                }
                for e in running_experiments
            ]
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error retrieving dashboard data: {str(e)}"
        )