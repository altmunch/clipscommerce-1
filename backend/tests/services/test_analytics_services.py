"""
Comprehensive unit tests for analytics services including performance prediction,
trend analysis, computer vision analysis, and ML model performance.
"""

import pytest
import numpy as np
import pandas as pd
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from datetime import datetime, timedelta
import json

from app.services.analytics.performance_predictor import PerformancePredictor
from app.services.analytics.trend_engine import TrendAnalysisEngine
from app.services.analytics.video_analyzer import VideoAnalyzer
from app.services.optimization.ab_testing import ABTestingService
from app.models.analytics import AnalyticsModel, PredictionModel, PerformanceMetrics
from tests.factories import (
    ContentFactory, VideoProjectFactory, BrandFactory, CampaignFactory,
    SocialMediaPostFactory, TikTokTrendFactory, TikTokVideoFactory
)


class TestPerformancePredictor:
    """Test video performance prediction and ML models."""

    @pytest.fixture
    def performance_predictor(self, mock_redis):
        with patch('app.services.analytics.performance_predictor.redis', mock_redis):
            return PerformancePredictor()

    @pytest.fixture
    def sample_video_features(self):
        """Sample video features for prediction testing."""
        return {
            "duration": 30.0,
            "aspect_ratio": "9:16",
            "has_music": True,
            "has_text_overlay": True,
            "scene_changes": 5,
            "color_variance": 0.8,
            "motion_intensity": 0.7,
            "face_detection": True,
            "object_count": 3,
            "text_readability_score": 0.9,
            "audio_clarity": 0.85,
            "brand_logo_visible": True,
            "call_to_action_present": True,
            "trending_elements": ["trending_music", "popular_hashtag"],
            "content_category": "product_demo",
            "posting_time": "evening",
            "day_of_week": "friday"
        }

    @pytest.fixture
    def sample_historical_data(self):
        """Sample historical performance data for training."""
        return pd.DataFrame({
            "video_id": range(100),
            "views": np.random.randint(1000, 100000, 100),
            "likes": np.random.randint(50, 5000, 100),
            "shares": np.random.randint(10, 1000, 100),
            "comments": np.random.randint(5, 500, 100),
            "duration": np.random.uniform(15, 60, 100),
            "has_music": np.random.choice([True, False], 100),
            "scene_changes": np.random.randint(1, 10, 100),
            "color_variance": np.random.uniform(0.2, 1.0, 100),
            "motion_intensity": np.random.uniform(0.1, 1.0, 100),
            "engagement_rate": np.random.uniform(2.0, 15.0, 100)
        })

    @pytest.mark.unit
    async def test_predict_video_performance(self, performance_predictor, sample_video_features):
        """Test video performance prediction."""
        # Mock trained model
        mock_model = Mock()
        mock_model.predict.return_value = np.array([[50000, 2500, 500, 100, 8.5]])  # views, likes, shares, comments, engagement_rate
        
        with patch.object(performance_predictor, 'load_model', return_value=mock_model):
            prediction = await performance_predictor.predict_performance(sample_video_features)
        
        assert prediction is not None
        assert prediction["predicted_views"] == 50000
        assert prediction["predicted_likes"] == 2500
        assert prediction["predicted_engagement_rate"] == 8.5
        assert "confidence_score" in prediction
        assert 0 <= prediction["confidence_score"] <= 1

    @pytest.mark.unit
    async def test_feature_importance_analysis(self, performance_predictor, sample_historical_data):
        """Test feature importance analysis for predictions."""
        # Mock model with feature importance
        mock_model = Mock()
        mock_model.feature_importances_ = np.array([0.3, 0.2, 0.15, 0.1, 0.25])
        feature_names = ["duration", "has_music", "scene_changes", "color_variance", "motion_intensity"]
        
        with patch.object(performance_predictor, 'load_model', return_value=mock_model):
            importance = await performance_predictor.analyze_feature_importance(feature_names)
        
        assert len(importance) == len(feature_names)
        assert importance[0]["feature"] == "duration"
        assert importance[0]["importance"] == 0.3
        assert sum(item["importance"] for item in importance) == pytest.approx(1.0)

    @pytest.mark.unit
    async def test_model_training_pipeline(self, performance_predictor, sample_historical_data):
        """Test ML model training pipeline."""
        with patch('sklearn.ensemble.RandomForestRegressor') as mock_rf:
            with patch('sklearn.model_selection.train_test_split') as mock_split:
                with patch('joblib.dump') as mock_dump:
                    
                    mock_model = Mock()
                    mock_rf.return_value = mock_model
                    mock_split.return_value = (None, None, None, None)  # X_train, X_test, y_train, y_test
                    
                    result = await performance_predictor.train_model(sample_historical_data)
        
        assert result["status"] == "success"
        assert "model_path" in result
        assert "accuracy_score" in result
        mock_model.fit.assert_called_once()
        mock_dump.assert_called_once()

    @pytest.mark.unit
    async def test_model_validation(self, performance_predictor, sample_historical_data):
        """Test model validation and accuracy assessment."""
        # Mock trained model
        mock_model = Mock()
        # Simulate predictions close to actual values for good accuracy
        actual_values = np.array([1000, 2000, 1500])
        predicted_values = np.array([1100, 1900, 1600])  # Close predictions
        mock_model.predict.return_value = predicted_values
        
        with patch.object(performance_predictor, 'load_model', return_value=mock_model):
            validation = await performance_predictor.validate_model(actual_values, ["feature1", "feature2", "feature3"])
        
        assert validation["mae"] < 200  # Mean Absolute Error should be low
        assert validation["r2_score"] > 0.8  # R² should be high for good model
        assert validation["accuracy_within_20_percent"] > 0.5

    @pytest.mark.unit
    async def test_trending_factors_analysis(self, performance_predictor):
        """Test analysis of trending factors affecting performance."""
        trending_data = [
            {"hashtag": "#viral", "usage_count": 10000, "avg_engagement": 12.5},
            {"hashtag": "#trending", "usage_count": 8000, "avg_engagement": 10.2},
            {"sound": "trending_audio_123", "usage_count": 5000, "avg_engagement": 15.0},
        ]
        
        analysis = await performance_predictor.analyze_trending_factors(trending_data)
        
        assert len(analysis["top_hashtags"]) > 0
        assert len(analysis["top_sounds"]) > 0
        assert analysis["overall_trend_score"] > 0

    @pytest.mark.unit
    async def test_performance_benchmarking(self, performance_predictor):
        """Test performance benchmarking against industry standards."""
        video_metrics = {
            "views": 25000,
            "likes": 1250,
            "shares": 125,
            "comments": 80,
            "engagement_rate": 6.2
        }
        
        industry_benchmarks = {
            "beauty": {"avg_engagement": 5.8, "avg_views": 30000},
            "fitness": {"avg_engagement": 7.2, "avg_views": 20000},
            "tech": {"avg_engagement": 4.5, "avg_views": 35000}
        }
        
        with patch.object(performance_predictor, 'get_industry_benchmarks', return_value=industry_benchmarks):
            benchmark = await performance_predictor.benchmark_performance(video_metrics, "beauty")
        
        assert benchmark["category"] == "beauty"
        assert benchmark["engagement_percentile"] > 50  # Above average
        assert "improvement_suggestions" in benchmark

    @pytest.mark.unit
    async def test_audience_insight_analysis(self, performance_predictor):
        """Test audience insight analysis for content optimization."""
        audience_data = {
            "demographics": {
                "age_groups": {"18-24": 40, "25-34": 35, "35-44": 25},
                "gender": {"female": 65, "male": 35},
                "locations": {"US": 50, "UK": 20, "CA": 15, "AU": 15}
            },
            "behavior": {
                "peak_activity_hours": [18, 19, 20, 21],
                "device_usage": {"mobile": 85, "desktop": 15},
                "content_preferences": ["short_form", "visual_heavy", "music_driven"]
            }
        }
        
        insights = await performance_predictor.analyze_audience_insights(audience_data)
        
        assert "optimal_posting_times" in insights
        assert "content_recommendations" in insights
        assert "demographic_targeting" in insights

    @pytest.mark.unit
    async def test_real_time_performance_tracking(self, performance_predictor, mock_redis):
        """Test real-time performance tracking and alerts."""
        video_id = "video_123"
        current_metrics = {
            "views": 1000,
            "likes": 50,
            "shares": 5,
            "comments": 8,
            "timestamp": datetime.utcnow().isoformat()
        }
        
        # Mock Redis storage
        mock_redis.zadd.return_value = True
        mock_redis.zrange.return_value = [json.dumps(current_metrics)]
        
        await performance_predictor.track_real_time_performance(video_id, current_metrics)
        
        # Verify Redis calls
        mock_redis.zadd.assert_called()
        
        # Test performance analysis
        analysis = await performance_predictor.analyze_performance_trajectory(video_id)
        assert "growth_rate" in analysis
        assert "trend_direction" in analysis


class TestTrendAnalysisEngine:
    """Test trend analysis and viral pattern recognition."""

    @pytest.fixture
    def trend_engine(self, mock_redis, mock_vector_db):
        with patch('app.services.analytics.trend_engine.redis', mock_redis):
            with patch('app.services.analytics.trend_engine.vector_db', mock_vector_db):
                return TrendAnalysisEngine()

    @pytest.fixture
    def sample_trend_data(self):
        """Sample trending data for analysis."""
        return [
            {
                "hashtag": "#fyp",
                "usage_count": 100000,
                "growth_rate": 25.5,
                "engagement_rate": 8.2,
                "geographic_distribution": {"US": 40, "UK": 20, "CA": 15},
                "first_seen": (datetime.utcnow() - timedelta(days=7)).isoformat(),
                "category": "general"
            },
            {
                "hashtag": "#viral",
                "usage_count": 75000,
                "growth_rate": 45.2,
                "engagement_rate": 12.1,
                "geographic_distribution": {"US": 50, "UK": 25, "CA": 10},
                "first_seen": (datetime.utcnow() - timedelta(days=3)).isoformat(),
                "category": "entertainment"
            }
        ]

    @pytest.mark.unit
    async def test_identify_emerging_trends(self, trend_engine, sample_trend_data):
        """Test identification of emerging trends."""
        with patch.object(trend_engine, 'fetch_trending_data', return_value=sample_trend_data):
            emerging_trends = await trend_engine.identify_emerging_trends()
        
        assert len(emerging_trends) > 0
        # #viral should be identified as emerging due to high growth rate
        viral_trend = next((t for t in emerging_trends if t["hashtag"] == "#viral"), None)
        assert viral_trend is not None
        assert viral_trend["growth_rate"] > 40

    @pytest.mark.unit
    async def test_predict_trend_lifecycle(self, trend_engine):
        """Test trend lifecycle prediction."""
        trend_data = {
            "hashtag": "#trendingnow",
            "current_usage": 50000,
            "growth_rate": 30.0,
            "age_days": 5,
            "historical_pattern": [1000, 5000, 20000, 35000, 50000]
        }
        
        prediction = await trend_engine.predict_trend_lifecycle(trend_data)
        
        assert prediction["current_phase"] in ["emerging", "growing", "peak", "declining"]
        assert prediction["estimated_peak_date"] is not None
        assert prediction["predicted_peak_usage"] > trend_data["current_usage"]

    @pytest.mark.unit
    async def test_viral_pattern_analysis(self, trend_engine):
        """Test viral pattern recognition in content."""
        viral_content_data = [
            {
                "video_id": "viral_1",
                "views": 1000000,
                "likes": 50000,
                "shares": 10000,
                "viral_coefficient": 2.5,
                "content_features": ["trending_music", "dance_challenge", "celebrity_mention"]
            },
            {
                "video_id": "viral_2", 
                "views": 800000,
                "likes": 40000,
                "shares": 8000,
                "viral_coefficient": 2.1,
                "content_features": ["trending_music", "emotional_story", "surprise_element"]
            }
        ]
        
        patterns = await trend_engine.analyze_viral_patterns(viral_content_data)
        
        assert "common_features" in patterns
        assert "trending_music" in patterns["common_features"]
        assert patterns["average_viral_coefficient"] > 2.0
        assert "success_indicators" in patterns

    @pytest.mark.unit
    async def test_trend_recommendation_engine(self, trend_engine, sample_trend_data):
        """Test personalized trend recommendations."""
        brand_profile = {
            "industry": "beauty",
            "target_audience": {"age": "18-34", "gender": "female"},
            "content_style": "lifestyle",
            "previous_successful_trends": ["#skincare", "#makeup", "#selfcare"]
        }
        
        with patch.object(trend_engine, 'fetch_trending_data', return_value=sample_trend_data):
            recommendations = await trend_engine.recommend_trends_for_brand(brand_profile)
        
        assert len(recommendations) > 0
        assert all("relevance_score" in rec for rec in recommendations)
        assert all(0 <= rec["relevance_score"] <= 1 for rec in recommendations)

    @pytest.mark.unit
    async def test_competitor_trend_analysis(self, trend_engine):
        """Test competitor trend analysis."""
        competitor_data = [
            {
                "competitor": "Brand A",
                "trending_content": [
                    {"hashtag": "#brandAchallenge", "performance": "high"},
                    {"hashtag": "#newproduct", "performance": "medium"}
                ]
            },
            {
                "competitor": "Brand B",
                "trending_content": [
                    {"hashtag": "#brandBlaunch", "performance": "high"},
                    {"hashtag": "#sustainableliving", "performance": "high"}
                ]
            }
        ]
        
        analysis = await trend_engine.analyze_competitor_trends(competitor_data)
        
        assert "trending_strategies" in analysis
        assert "opportunity_gaps" in analysis
        assert "competitive_advantages" in analysis

    @pytest.mark.unit
    async def test_trend_sentiment_analysis(self, trend_engine, mock_openai_client):
        """Test sentiment analysis of trending content."""
        trend_content = [
            {"text": "I love this new trend! So amazing and fun!", "engagement": 1000},
            {"text": "This trend is getting old and annoying", "engagement": 50},
            {"text": "Best trend ever! Everyone should try this", "engagement": 800}
        ]
        
        mock_openai_client.chat.completions.create.return_value = Mock(
            choices=[Mock(message=Mock(content=json.dumps({
                "overall_sentiment": "positive",
                "sentiment_score": 0.75,
                "positive_ratio": 0.8,
                "negative_ratio": 0.2,
                "key_emotions": ["excitement", "joy", "enthusiasm"]
            })))]
        )
        
        with patch.object(trend_engine, 'openai_client', mock_openai_client):
            sentiment = await trend_engine.analyze_trend_sentiment(trend_content)
        
        assert sentiment["overall_sentiment"] == "positive"
        assert sentiment["sentiment_score"] > 0.5
        assert "key_emotions" in sentiment

    @pytest.mark.unit
    async def test_cross_platform_trend_analysis(self, trend_engine):
        """Test trend analysis across multiple platforms."""
        platform_data = {
            "tiktok": [
                {"hashtag": "#viral", "usage": 100000, "engagement": 8.5},
                {"hashtag": "#trending", "usage": 75000, "engagement": 7.2}
            ],
            "instagram": [
                {"hashtag": "#viral", "usage": 50000, "engagement": 6.8},
                {"hashtag": "#trendy", "usage": 30000, "engagement": 5.5}
            ]
        }
        
        analysis = await trend_engine.analyze_cross_platform_trends(platform_data)
        
        assert "cross_platform_trends" in analysis
        assert "platform_specific_trends" in analysis
        assert "#viral" in [t["hashtag"] for t in analysis["cross_platform_trends"]]


class TestVideoAnalyzer:
    """Test computer vision and video content analysis."""

    @pytest.fixture
    def video_analyzer(self, mock_openai_client):
        with patch('app.services.analytics.video_analyzer.openai_client', mock_openai_client):
            return VideoAnalyzer()

    @pytest.mark.unit
    async def test_analyze_video_content(self, video_analyzer):
        """Test comprehensive video content analysis."""
        video_path = "/tmp/test_video.mp4"
        
        # Mock OpenCV operations
        with patch('cv2.VideoCapture') as mock_cv2:
            mock_cap = Mock()
            mock_cap.read.side_effect = [(True, np.zeros((480, 640, 3), dtype=np.uint8))] * 30 + [(False, None)]
            mock_cap.get.return_value = 30  # FPS
            mock_cv2.return_value = mock_cap
            
            analysis = await video_analyzer.analyze_video_content(video_path)
        
        assert analysis is not None
        assert "frame_count" in analysis
        assert "duration" in analysis
        assert "resolution" in analysis
        assert "scene_changes" in analysis

    @pytest.mark.unit
    async def test_detect_objects_and_faces(self, video_analyzer):
        """Test object and face detection in video frames."""
        # Mock frame data
        frame = np.zeros((480, 640, 3), dtype=np.uint8)
        
        # Mock face detection
        with patch('cv2.CascadeClassifier') as mock_cascade:
            mock_classifier = Mock()
            mock_classifier.detectMultiScale.return_value = np.array([[100, 100, 50, 50]])  # x, y, w, h
            mock_cascade.return_value = mock_classifier
            
            detection = await video_analyzer.detect_faces_and_objects(frame)
        
        assert "faces" in detection
        assert len(detection["faces"]) > 0
        assert detection["faces"][0]["confidence"] > 0

    @pytest.mark.unit
    async def test_analyze_color_composition(self, video_analyzer):
        """Test color composition analysis."""
        # Create test frame with specific colors
        frame = np.zeros((100, 100, 3), dtype=np.uint8)
        frame[0:50, 0:50] = [255, 0, 0]  # Red
        frame[0:50, 50:100] = [0, 255, 0]  # Green
        frame[50:100, 0:50] = [0, 0, 255]  # Blue
        frame[50:100, 50:100] = [255, 255, 255]  # White
        
        color_analysis = await video_analyzer.analyze_color_composition(frame)
        
        assert "dominant_colors" in color_analysis
        assert "color_diversity" in color_analysis
        assert "brightness_average" in color_analysis
        assert len(color_analysis["dominant_colors"]) > 0

    @pytest.mark.unit
    async def test_motion_analysis(self, video_analyzer):
        """Test motion and movement analysis."""
        # Create two frames with slight difference
        frame1 = np.zeros((100, 100, 3), dtype=np.uint8)
        frame2 = np.zeros((100, 100, 3), dtype=np.uint8)
        frame2[10:20, 10:20] = 255  # Add a white square
        
        with patch('cv2.calcOpticalFlowPyrLK') as mock_optical_flow:
            mock_optical_flow.return_value = (
                np.array([[15, 15]], dtype=np.float32),  # New points
                np.array([1], dtype=np.uint8),  # Status
                np.array([0.1], dtype=np.float32)  # Error
            )
            
            motion_analysis = await video_analyzer.analyze_motion(frame1, frame2)
        
        assert "motion_vectors" in motion_analysis
        assert "motion_intensity" in motion_analysis
        assert motion_analysis["motion_intensity"] >= 0

    @pytest.mark.unit
    async def test_scene_change_detection(self, video_analyzer):
        """Test scene change detection algorithm."""
        frames = [
            np.zeros((100, 100, 3), dtype=np.uint8),  # Black frame
            np.zeros((100, 100, 3), dtype=np.uint8),  # Same black frame
            np.ones((100, 100, 3), dtype=np.uint8) * 255,  # White frame - scene change
            np.ones((100, 100, 3), dtype=np.uint8) * 255,  # Same white frame
        ]
        
        scene_changes = await video_analyzer.detect_scene_changes(frames)
        
        assert len(scene_changes) > 0
        assert 2 in scene_changes  # Scene change at frame 2

    @pytest.mark.unit
    async def test_text_extraction_and_readability(self, video_analyzer):
        """Test text extraction and readability analysis."""
        # Mock OCR results
        with patch('pytesseract.image_to_string', return_value="SALE 50% OFF"):
            with patch('pytesseract.image_to_data') as mock_data:
                mock_data.return_value = {
                    'conf': [95, 90, 88],
                    'text': ['SALE', '50%', 'OFF'],
                    'left': [10, 50, 90],
                    'top': [10, 10, 10],
                    'width': [30, 25, 25],
                    'height': [20, 20, 20]
                }
                
                frame = np.ones((100, 200, 3), dtype=np.uint8) * 255
                text_analysis = await video_analyzer.extract_and_analyze_text(frame)
        
        assert "text_content" in text_analysis
        assert "readability_score" in text_analysis
        assert "text_regions" in text_analysis
        assert text_analysis["text_content"] == "SALE 50% OFF"

    @pytest.mark.unit
    async def test_aesthetic_quality_assessment(self, video_analyzer):
        """Test aesthetic quality assessment of video content."""
        frame = np.random.randint(0, 255, (480, 640, 3), dtype=np.uint8)
        
        quality_assessment = await video_analyzer.assess_aesthetic_quality(frame)
        
        assert "composition_score" in quality_assessment
        assert "visual_appeal" in quality_assessment
        assert "technical_quality" in quality_assessment
        assert all(0 <= score <= 1 for score in quality_assessment.values() if isinstance(score, (int, float)))

    @pytest.mark.unit
    async def test_brand_element_detection(self, video_analyzer):
        """Test detection of brand elements in video."""
        frame = np.zeros((480, 640, 3), dtype=np.uint8)
        brand_assets = {
            "logo_path": "/tmp/logo.png",
            "brand_colors": ["#FF0000", "#00FF00"],
            "fonts": ["Arial", "Helvetica"]
        }
        
        # Mock template matching for logo detection
        with patch('cv2.matchTemplate') as mock_match:
            mock_match.return_value = np.array([[0.9]])  # High confidence match
            
            with patch('cv2.minMaxLoc') as mock_minmax:
                mock_minmax.return_value = (0.1, 0.9, (10, 10), (50, 50))
                
                brand_analysis = await video_analyzer.detect_brand_elements(frame, brand_assets)
        
        assert "logo_detected" in brand_analysis
        assert "brand_color_presence" in brand_analysis
        assert "logo_confidence" in brand_analysis

    @pytest.mark.unit
    async def test_engagement_prediction_from_visual_features(self, video_analyzer):
        """Test predicting engagement from visual features."""
        visual_features = {
            "scene_changes": 8,
            "motion_intensity": 0.7,
            "color_diversity": 0.8,
            "face_count": 2,
            "text_readability": 0.9,
            "visual_appeal": 0.75,
            "object_density": 0.6,
            "brightness_variation": 0.5
        }
        
        # Mock trained model
        with patch.object(video_analyzer, 'load_engagement_model') as mock_model:
            mock_model.return_value.predict.return_value = np.array([8.5])  # Predicted engagement rate
            
            prediction = await video_analyzer.predict_engagement_from_visuals(visual_features)
        
        assert prediction["predicted_engagement_rate"] == 8.5
        assert "confidence_score" in prediction
        assert "key_factors" in prediction


class TestABTestingService:
    """Test A/B testing functionality for content optimization."""

    @pytest.fixture
    def ab_testing_service(self, mock_redis):
        with patch('app.services.optimization.ab_testing.redis', mock_redis):
            return ABTestingService()

    @pytest.mark.unit
    async def test_create_ab_test(self, ab_testing_service, db_session):
        """Test creating A/B test experiments."""
        test_config = {
            "name": "Video Hook Test",
            "description": "Testing different video hooks",
            "variants": [
                {
                    "name": "Variant A - Question Hook",
                    "video_config": {"hook_type": "question", "script": "Did you know...?"}
                },
                {
                    "name": "Variant B - Stat Hook", 
                    "video_config": {"hook_type": "statistic", "script": "95% of people..."}
                }
            ],
            "success_metric": "engagement_rate",
            "target_significance": 0.95,
            "minimum_sample_size": 1000
        }
        
        test = await ab_testing_service.create_test(test_config, db_session)
        
        assert test["test_id"] is not None
        assert test["status"] == "created"
        assert len(test["variants"]) == 2

    @pytest.mark.unit
    async def test_assign_variant_to_user(self, ab_testing_service, mock_redis):
        """Test variant assignment for users."""
        test_id = "test_123"
        user_id = "user_456"
        
        # Mock test configuration
        test_config = {
            "variants": [
                {"id": "variant_a", "name": "Variant A", "traffic_allocation": 50},
                {"id": "variant_b", "name": "Variant B", "traffic_allocation": 50}
            ]
        }
        
        mock_redis.get.return_value = json.dumps(test_config)
        
        variant = await ab_testing_service.assign_variant(test_id, user_id)
        
        assert variant["variant_id"] in ["variant_a", "variant_b"]
        mock_redis.set.assert_called()  # User assignment should be cached

    @pytest.mark.unit
    async def test_record_conversion_event(self, ab_testing_service, mock_redis):
        """Test recording conversion events for A/B tests."""
        test_id = "test_123"
        user_id = "user_456"
        variant_id = "variant_a"
        conversion_data = {
            "event_type": "video_view",
            "value": 1,
            "metadata": {"duration_watched": 25.5}
        }
        
        await ab_testing_service.record_conversion(test_id, user_id, variant_id, conversion_data)
        
        # Verify Redis calls for storing conversion data
        mock_redis.zadd.assert_called()
        mock_redis.incr.assert_called()

    @pytest.mark.unit
    async def test_calculate_statistical_significance(self, ab_testing_service):
        """Test statistical significance calculation."""
        variant_a_data = {
            "conversions": 450,
            "total_users": 5000,
            "conversion_rate": 0.09
        }
        
        variant_b_data = {
            "conversions": 520,
            "total_users": 5000,
            "conversion_rate": 0.104
        }
        
        significance = await ab_testing_service.calculate_significance(variant_a_data, variant_b_data)
        
        assert "p_value" in significance
        assert "confidence_level" in significance
        assert "is_significant" in significance
        assert "improvement" in significance

    @pytest.mark.unit
    async def test_multi_variant_testing(self, ab_testing_service):
        """Test multi-variant testing (more than 2 variants)."""
        test_config = {
            "name": "Multi-Variant Hook Test",
            "variants": [
                {"name": "Control", "traffic_allocation": 25},
                {"name": "Question Hook", "traffic_allocation": 25},
                {"name": "Stat Hook", "traffic_allocation": 25},
                {"name": "Story Hook", "traffic_allocation": 25}
            ],
            "success_metric": "engagement_rate"
        }
        
        # Simulate performance data for each variant
        performance_data = {
            "control": {"conversions": 200, "total_users": 2500},
            "question_hook": {"conversions": 240, "total_users": 2500},
            "stat_hook": {"conversions": 260, "total_users": 2500},
            "story_hook": {"conversions": 220, "total_users": 2500}
        }
        
        analysis = await ab_testing_service.analyze_multi_variant_test(performance_data)
        
        assert "best_variant" in analysis
        assert "variant_rankings" in analysis
        assert len(analysis["variant_rankings"]) == 4

    @pytest.mark.unit
    async def test_sequential_testing(self, ab_testing_service):
        """Test sequential testing for early stopping."""
        test_data = {
            "variant_a": {"conversions": [10, 25, 45, 70, 100], "users": [100, 250, 500, 750, 1000]},
            "variant_b": {"conversions": [15, 35, 60, 95, 135], "users": [100, 250, 500, 750, 1000]}
        }
        
        early_stop_decision = await ab_testing_service.check_early_stopping(test_data)
        
        assert "should_stop" in early_stop_decision
        assert "reason" in early_stop_decision
        assert "confidence_level" in early_stop_decision

    @pytest.mark.unit
    async def test_test_results_reporting(self, ab_testing_service, mock_redis):
        """Test comprehensive test results reporting."""
        test_id = "test_123"
        
        # Mock test data in Redis
        test_results = {
            "variant_a": {
                "name": "Control",
                "users": 5000,
                "conversions": 450,
                "conversion_rate": 0.09,
                "confidence_interval": [0.085, 0.095]
            },
            "variant_b": {
                "name": "Treatment",
                "users": 5000,
                "conversions": 520,
                "conversion_rate": 0.104,
                "confidence_interval": [0.099, 0.109]
            }
        }
        
        mock_redis.get.return_value = json.dumps(test_results)
        
        report = await ab_testing_service.generate_test_report(test_id)
        
        assert "test_summary" in report
        assert "variant_performance" in report
        assert "statistical_analysis" in report
        assert "recommendations" in report

    @pytest.mark.unit
    async def test_power_analysis(self, ab_testing_service):
        """Test statistical power analysis for test planning."""
        test_parameters = {
            "baseline_conversion_rate": 0.08,
            "minimum_detectable_effect": 0.02,  # 2 percentage points
            "significance_level": 0.05,
            "statistical_power": 0.80
        }
        
        power_analysis = await ab_testing_service.calculate_sample_size(test_parameters)
        
        assert power_analysis["required_sample_size"] > 0
        assert power_analysis["test_duration_estimate"] > 0
        assert "assumptions" in power_analysis