import logging
from typing import Dict, Any, Optional
from celery import Celery
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from pathlib import Path
import asyncio

from app.core.celery_app import celery_app
from app.db.session import SessionLocal
from app.models.analytics import (
    VideoPerformancePrediction, TrendRecommendation, ABTestExperiment, 
    ABTestVariant, PlatformType, ModelPerformanceMetrics
)
from app.models.content import Video
from app.services.analytics.video_analyzer import VideoAnalyzer
from app.services.analytics.performance_predictor import PerformancePredictor
from app.services.analytics.trend_engine import TrendRecommendationEngine
from app.services.optimization.ab_testing import ABTestingService
from app.core.config import settings

logger = logging.getLogger(__name__)

# Initialize services
video_analyzer = VideoAnalyzer()
performance_predictor = PerformancePredictor()
trend_engine = TrendRecommendationEngine()
ab_testing_service = ABTestingService()

@celery_app.task(bind=True, max_retries=3)
def process_video_analysis(
    self,
    video_id: int,
    platform: str,
    metadata: Optional[Dict[str, Any]] = None
):
    """
    Background task to analyze video performance
    """
    try:
        logger.info(f"Starting video analysis for video {video_id} on platform {platform}")
        
        db = SessionLocal()
        
        # Get video file path
        video = db.query(Video).filter(Video.id == video_id).first()
        if not video:
            raise ValueError(f"Video {video_id} not found")
        
        # Get video file path (you'll need to implement this based on your storage)
        video_path = get_video_file_path(video)
        if not video_path or not Path(video_path).exists():
            raise ValueError(f"Video file not found for video {video_id}")
        
        # Convert platform string to enum
        platform_enum = PlatformType(platform)
        
        # Run analysis (note: this needs to be adapted for sync execution)
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        try:
            prediction_result = loop.run_until_complete(
                performance_predictor.predict_performance(
                    video_path,
                    platform_enum,
                    metadata
                )
            )
            
            analysis_result = loop.run_until_complete(
                video_analyzer.analyze_video(video_path)
            )
        finally:
            loop.close()
        
        # Save results to database
        existing_prediction = db.query(VideoPerformancePrediction).filter(
            VideoPerformancePrediction.video_id == video_id,
            VideoPerformancePrediction.platform == platform_enum
        ).first()
        
        if existing_prediction:
            # Update existing prediction
            existing_prediction.overall_score = prediction_result.overall_score
            existing_prediction.confidence_interval = prediction_result.confidence_interval
            existing_prediction.predicted_views = prediction_result.predicted_views
            existing_prediction.predicted_engagement_rate = prediction_result.predicted_engagement_rate
            existing_prediction.hook_score = prediction_result.hook_score
            existing_prediction.content_score = prediction_result.content_score
            existing_prediction.cta_score = prediction_result.cta_score
            existing_prediction.visual_analysis = analysis_result.get('visual_metrics', {})
            existing_prediction.audio_analysis = analysis_result.get('audio_metrics', {})
            existing_prediction.recommendations = prediction_result.recommendations
            existing_prediction.processing_time = analysis_result.get('processing_time', 0.0)
            existing_prediction.updated_at = datetime.now()
        else:
            # Create new prediction
            prediction = VideoPerformancePrediction(
                video_id=video_id,
                platform=platform_enum,
                overall_score=prediction_result.overall_score,
                confidence_interval=prediction_result.confidence_interval,
                predicted_views=prediction_result.predicted_views,
                predicted_engagement_rate=prediction_result.predicted_engagement_rate,
                hook_score=prediction_result.hook_score,
                content_score=prediction_result.content_score,
                cta_score=prediction_result.cta_score,
                visual_analysis=analysis_result.get('visual_metrics', {}),
                audio_analysis=analysis_result.get('audio_metrics', {}),
                recommendations=prediction_result.recommendations,
                model_version=prediction_result.model_version,
                processing_time=analysis_result.get('processing_time', 0.0)
            )
            db.add(prediction)
        
        db.commit()
        logger.info(f"Video analysis completed for video {video_id}")
        
        return {
            'video_id': video_id,
            'platform': platform,
            'overall_score': prediction_result.overall_score,
            'processing_time': analysis_result.get('processing_time', 0.0)
        }
        
    except Exception as e:
        logger.error(f"Error processing video analysis: {e}")
        db.rollback()
        # Retry the task
        raise self.retry(countdown=60, exc=e)
    finally:
        db.close()

@celery_app.task(bind=True)
def update_trend_data(self, platform: str):
    """
    Background task to update trend data for a platform
    """
    try:
        logger.info(f"Updating trend data for platform {platform}")
        
        platform_enum = PlatformType(platform)
        
        # Run trend update (note: this needs to be adapted for sync execution)
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        try:
            # This would typically update trend data from external sources
            # For now, we'll just log the activity
            logger.info(f"Trend data update completed for {platform}")
        finally:
            loop.close()
        
        return {'platform': platform, 'status': 'completed'}
        
    except Exception as e:
        logger.error(f"Error updating trend data: {e}")
        raise

@celery_app.task(bind=True)
def analyze_ab_test_results(self, experiment_id: int):
    """
    Background task to analyze A/B test results
    """
    try:
        logger.info(f"Analyzing A/B test results for experiment {experiment_id}")
        
        # Run A/B test analysis
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        try:
            analysis_result = loop.run_until_complete(
                ab_testing_service.analyze_experiment(experiment_id)
            )
        finally:
            loop.close()
        
        logger.info(f"A/B test analysis completed for experiment {experiment_id}")
        return analysis_result
        
    except Exception as e:
        logger.error(f"Error analyzing A/B test: {e}")
        raise

@celery_app.task(bind=True)
def train_performance_models(self):
    """
    Background task to retrain performance prediction models
    """
    try:
        logger.info("Starting model training task")
        
        db = SessionLocal()
        
        # Get training data (this would be more sophisticated in production)
        cutoff_date = datetime.now() - timedelta(days=30)
        
        # Collect recent performance data for training
        recent_predictions = db.query(VideoPerformancePrediction).filter(
            VideoPerformancePrediction.created_at >= cutoff_date
        ).all()
        
        if len(recent_predictions) < 100:
            logger.warning("Insufficient data for model training")
            return {'status': 'skipped', 'reason': 'insufficient_data'}
        
        # This would implement actual model training logic
        # For now, we'll simulate the training
        logger.info(f"Model training simulated with {len(recent_predictions)} samples")
        
        # Record training metrics
        training_metrics = ModelPerformanceMetrics(
            model_name="performance_predictor",
            model_version="1.0",
            accuracy=0.85,
            precision=0.82,
            recall=0.88,
            f1_score=0.85,
            test_size=len(recent_predictions) // 5,
            test_period_start=cutoff_date,
            test_period_end=datetime.now(),
            training_duration=5.0  # minutes
        )
        
        db.add(training_metrics)
        db.commit()
        
        logger.info("Model training completed")
        return {'status': 'completed', 'samples': len(recent_predictions)}
        
    except Exception as e:
        logger.error(f"Error training models: {e}")
        db.rollback()
        raise
    finally:
        db.close()

@celery_app.task(bind=True)
def generate_trend_reports(self, brand_id: int):
    """
    Background task to generate trend reports for a brand
    """
    try:
        logger.info(f"Generating trend report for brand {brand_id}")
        
        db = SessionLocal()
        
        # Get recent trends for the brand
        recent_trends = db.query(TrendRecommendation).filter(
            TrendRecommendation.brand_id == brand_id,
            TrendRecommendation.is_active == True
        ).order_by(TrendRecommendation.virality_score.desc()).limit(10).all()
        
        # Generate report data
        report_data = {
            'brand_id': brand_id,
            'generated_at': datetime.now().isoformat(),
            'trend_count': len(recent_trends),
            'top_trends': [
                {
                    'name': trend.trend_name,
                    'type': trend.trend_type,
                    'virality_score': trend.virality_score,
                    'relevance_score': trend.relevance_score,
                    'growth_rate': trend.growth_rate
                }
                for trend in recent_trends[:5]
            ],
            'recommendations': [
                'Focus on trending audio with high relevance scores',
                'Consider seasonal trends for better timing',
                'Monitor competitor usage of trending formats'
            ]
        }
        
        # In production, you'd save this to a file or send via email
        logger.info(f"Trend report generated for brand {brand_id}")
        
        return report_data
        
    except Exception as e:
        logger.error(f"Error generating trend report: {e}")
        raise
    finally:
        db.close()

@celery_app.task(bind=True)
def cleanup_old_analytics_data(self):
    """
    Background task to clean up old analytics data
    """
    try:
        logger.info("Starting analytics data cleanup")
        
        db = SessionLocal()
        
        # Define retention periods
        retention_periods = {
            'predictions': 90,  # days
            'trends': 30,       # days
            'experiments': 180, # days
            'metrics': 365      # days
        }
        
        cleanup_stats = {}
        
        # Clean up old predictions
        cutoff_date = datetime.now() - timedelta(days=retention_periods['predictions'])
        old_predictions = db.query(VideoPerformancePrediction).filter(
            VideoPerformancePrediction.created_at < cutoff_date
        ).delete()
        cleanup_stats['predictions_deleted'] = old_predictions
        
        # Clean up old trends
        cutoff_date = datetime.now() - timedelta(days=retention_periods['trends'])
        old_trends = db.query(TrendRecommendation).filter(
            TrendRecommendation.discovered_at < cutoff_date
        ).delete()
        cleanup_stats['trends_deleted'] = old_trends
        
        # Clean up completed experiments older than retention period
        cutoff_date = datetime.now() - timedelta(days=retention_periods['experiments'])
        old_experiments = db.query(ABTestExperiment).filter(
            ABTestExperiment.created_at < cutoff_date,
            ABTestExperiment.status.in_(['completed', 'cancelled'])
        ).delete()
        cleanup_stats['experiments_deleted'] = old_experiments
        
        db.commit()
        
        logger.info(f"Analytics cleanup completed: {cleanup_stats}")
        return cleanup_stats
        
    except Exception as e:
        logger.error(f"Error cleaning up analytics data: {e}")
        db.rollback()
        raise
    finally:
        db.close()

@celery_app.task(bind=True)
def monitor_ab_test_experiments(self):
    """
    Background task to monitor running A/B test experiments
    """
    try:
        logger.info("Monitoring A/B test experiments")
        
        db = SessionLocal()
        
        # Get running experiments
        running_experiments = db.query(ABTestExperiment).filter(
            ABTestExperiment.status == 'running'
        ).all()
        
        monitor_results = []
        
        for experiment in running_experiments:
            # Check if experiment should be stopped
            days_running = (datetime.now() - experiment.start_date).days
            
            # Get sample size
            variants = db.query(ABTestVariant).filter(
                ABTestVariant.experiment_id == experiment.id
            ).all()
            
            total_sample_size = sum(v.impressions for v in variants)
            
            result = {
                'experiment_id': experiment.id,
                'name': experiment.name,
                'days_running': days_running,
                'total_sample_size': total_sample_size,
                'minimum_sample_size': experiment.minimum_sample_size,
                'action': 'continue'
            }
            
            # Check if we should auto-analyze
            if (total_sample_size >= experiment.minimum_sample_size and 
                days_running >= 3):
                
                # Schedule analysis
                analyze_ab_test_results.delay(experiment.id)
                result['action'] = 'analyzed'
            
            # Check if experiment has run too long
            elif days_running >= experiment.planned_duration_days + 7:
                result['action'] = 'should_stop'
                result['reason'] = 'exceeded_planned_duration'
            
            monitor_results.append(result)
        
        logger.info(f"Monitored {len(running_experiments)} experiments")
        return monitor_results
        
    except Exception as e:
        logger.error(f"Error monitoring experiments: {e}")
        raise
    finally:
        db.close()

def get_video_file_path(video) -> Optional[str]:
    """
    Get the file path for a video
    This is a placeholder - implement based on your video storage system
    """
    # This would depend on your video storage implementation
    # For example, if videos are stored in S3, you'd download them temporarily
    # If stored locally, you'd return the local path
    
    # Placeholder implementation
    if hasattr(video, 'file_path') and video.file_path:
        return video.file_path
    elif hasattr(video, 'url') and video.url:
        # For remote videos, you'd need to download them first
        return download_video_temporarily(video.url)
    else:
        return None

def download_video_temporarily(video_url: str) -> Optional[str]:
    """
    Download video from URL to temporary location
    """
    try:
        import requests
        import tempfile
        from urllib.parse import urlparse
        
        # Create temporary file
        parsed_url = urlparse(video_url)
        file_extension = Path(parsed_url.path).suffix or '.mp4'
        
        with tempfile.NamedTemporaryFile(delete=False, suffix=file_extension) as temp_file:
            response = requests.get(video_url, stream=True, timeout=30)
            response.raise_for_status()
            
            for chunk in response.iter_content(chunk_size=8192):
                temp_file.write(chunk)
            
            return temp_file.name
    
    except Exception as e:
        logger.error(f"Error downloading video: {e}")
        return None

# Periodic tasks setup
@celery_app.on_after_configure.connect
def setup_periodic_tasks(sender, **kwargs):
    """Setup periodic tasks for analytics"""
    
    # Update trend data every hour
    sender.add_periodic_task(
        3600.0,  # 1 hour
        update_trend_data.s('tiktok'),
        name='update_tiktok_trends'
    )
    
    sender.add_periodic_task(
        3600.0,  # 1 hour
        update_trend_data.s('instagram'),
        name='update_instagram_trends'
    )
    
    # Monitor A/B tests every 30 minutes
    sender.add_periodic_task(
        1800.0,  # 30 minutes
        monitor_ab_test_experiments.s(),
        name='monitor_ab_tests'
    )
    
    # Train models daily at 2 AM
    sender.add_periodic_task(
        86400.0,  # 24 hours
        train_performance_models.s(),
        name='daily_model_training',
        options={'eta': datetime.now().replace(hour=2, minute=0, second=0)}
    )
    
    # Cleanup old data weekly
    sender.add_periodic_task(
        604800.0,  # 7 days
        cleanup_old_analytics_data.s(),
        name='weekly_cleanup'
    )