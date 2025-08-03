import pickle
import numpy as np
import pandas as pd
from typing import Dict, List, Tuple, Optional, Any
import logging
from pathlib import Path
import joblib
from sklearn.ensemble import RandomForestRegressor, GradientBoostingRegressor
from sklearn.model_selection import train_test_split, cross_val_score
from sklearn.preprocessing import StandardScaler, LabelEncoder
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
import json
from datetime import datetime, timedelta
from dataclasses import dataclass

from app.models.analytics import PlatformType, VideoPerformancePrediction
from app.core.config import settings
from .video_analyzer import VideoAnalyzer, VisualMetrics, AudioMetrics

logger = logging.getLogger(__name__)

@dataclass
class PredictionResult:
    """Container for prediction results"""
    overall_score: float
    confidence_interval: float
    predicted_views: int
    predicted_engagement_rate: float
    hook_score: float
    content_score: float
    cta_score: float
    recommendations: List[str]
    model_version: str
    feature_importance: Dict[str, float]

class PerformancePredictor:
    """ML-based video performance prediction system"""
    
    def __init__(self):
        self.models = {}  # Platform-specific models
        self.scalers = {}  # Platform-specific feature scalers
        self.feature_columns = []
        self.model_version = "1.0"
        self.video_analyzer = VideoAnalyzer()
        
        # Model paths
        self.model_dir = Path(settings.BASE_DIR) / "ml_models" / "performance"
        self.model_dir.mkdir(parents=True, exist_ok=True)
        
        # Feature engineering configuration
        self.feature_config = {
            'visual_features': [
                'hook_potential', 'scene_count', 'avg_scene_duration', 'text_clarity_score',
                'object_count', 'composition_score', 'color_diversity', 'contrast_score',
                'motion_intensity', 'energy_level', 'face_count'
            ],
            'audio_features': [
                'duration', 'tempo', 'energy', 'spectral_centroid', 'zero_crossing_rate',
                'onset_strength', 'dominant_frequency', 'audio_clarity'
            ],
            'metadata_features': [
                'video_duration', 'aspect_ratio', 'file_size_mb', 'resolution_score'
            ],
            'temporal_features': [
                'hour_of_day', 'day_of_week', 'month', 'is_weekend'
            ]
        }
        
        # Load existing models if available
        self._load_models()
    
    async def predict_performance(
        self, 
        video_path: str, 
        platform: PlatformType,
        metadata: Optional[Dict] = None
    ) -> PredictionResult:
        """
        Predict video performance for a specific platform
        
        Args:
            video_path: Path to video file
            platform: Target platform
            metadata: Additional video metadata
            
        Returns:
            Prediction results with scores and recommendations
        """
        try:
            # Analyze video content
            analysis_result = await self.video_analyzer.analyze_video(video_path)
            
            if 'error' in analysis_result:
                raise ValueError(f"Video analysis failed: {analysis_result['error']}")
            
            # Extract and engineer features
            features = self._extract_features(analysis_result, metadata)
            
            # Get platform-specific prediction
            if platform.value not in self.models:
                logger.warning(f"No model available for platform {platform.value}, using default")
                platform_key = 'default'
            else:
                platform_key = platform.value
            
            # Make prediction
            prediction = self._predict_with_model(features, platform_key)
            
            # Generate recommendations
            recommendations = self._generate_recommendations(analysis_result, prediction)
            
            # Calculate confidence interval
            confidence = self._calculate_confidence(features, platform_key)
            
            return PredictionResult(
                overall_score=prediction['overall_score'],
                confidence_interval=confidence,
                predicted_views=prediction['predicted_views'],
                predicted_engagement_rate=prediction['predicted_engagement_rate'],
                hook_score=prediction['hook_score'],
                content_score=prediction['content_score'],
                cta_score=prediction['cta_score'],
                recommendations=recommendations,
                model_version=self.model_version,
                feature_importance=self._get_feature_importance(platform_key)
            )
            
        except Exception as e:
            logger.error(f"Error predicting performance: {e}")
            raise
    
    def _extract_features(self, analysis_result: Dict, metadata: Optional[Dict] = None) -> np.ndarray:
        """Extract and engineer features from video analysis"""
        features = []
        
        # Visual features
        visual_metrics = analysis_result.get('visual_metrics', {})
        for feature in self.feature_config['visual_features']:
            features.append(visual_metrics.get(feature, 0.0))
        
        # Audio features
        audio_metrics = analysis_result.get('audio_metrics', {})
        for feature in self.feature_config['audio_features']:
            if feature == 'mfcc_features':
                # Use mean of MFCC coefficients
                mfcc = audio_metrics.get(feature, [0] * 13)
                features.extend(mfcc[:13])  # First 13 MFCC coefficients
            else:
                features.append(audio_metrics.get(feature, 0.0))
        
        # Metadata features
        if metadata:
            features.append(metadata.get('duration', 0.0))
            features.append(metadata.get('aspect_ratio', 16/9))
            features.append(metadata.get('file_size_mb', 0.0))
            features.append(self._calculate_resolution_score(metadata))
        else:
            features.extend([0.0, 16/9, 0.0, 0.5])  # Default values
        
        # Temporal features (current time context)
        now = datetime.now()
        features.extend([
            now.hour,
            now.weekday(),
            now.month,
            1 if now.weekday() >= 5 else 0  # is_weekend
        ])
        
        # Derived features
        features.extend(self._calculate_derived_features(visual_metrics, audio_metrics))
        
        return np.array(features).reshape(1, -1)
    
    def _calculate_derived_features(self, visual: Dict, audio: Dict) -> List[float]:
        """Calculate derived features from base metrics"""
        derived = []
        
        # Visual-audio sync score
        visual_energy = visual.get('energy_level', 0)
        audio_energy = audio.get('energy', 0) * 100
        sync_score = 1.0 - abs(visual_energy - audio_energy) / 100.0
        derived.append(max(0, sync_score))
        
        # Pacing score (combination of scene changes and tempo)
        scene_duration = visual.get('avg_scene_duration', 5.0)
        tempo = audio.get('tempo', 120)
        pacing_score = min(tempo / 120.0, 2.0) * min(5.0 / scene_duration, 2.0)
        derived.append(pacing_score)
        
        # Engagement potential (faces + motion + audio clarity)
        faces = min(visual.get('face_count', 0), 3) / 3.0
        motion = visual.get('motion_intensity', 0)
        clarity = audio.get('audio_clarity', 0)
        engagement = (faces * 0.4 + motion * 0.3 + clarity * 0.3)
        derived.append(engagement)
        
        # Visual complexity
        objects = min(visual.get('object_count', 0), 10) / 10.0
        color_div = visual.get('color_diversity', 0) / 100.0
        complexity = (objects * 0.6 + color_div * 0.4)
        derived.append(complexity)
        
        return derived
    
    def _calculate_resolution_score(self, metadata: Dict) -> float:
        """Calculate resolution quality score"""
        width = metadata.get('width', 1080)
        height = metadata.get('height', 1920)
        
        # Standard resolutions and their scores
        resolution_scores = {
            (1080, 1920): 1.0,  # Full HD vertical
            (720, 1280): 0.8,   # HD vertical
            (1920, 1080): 0.9,  # Full HD horizontal
            (1280, 720): 0.7,   # HD horizontal
        }
        
        # Find closest match
        best_score = 0.5  # Default score
        for (w, h), score in resolution_scores.items():
            if abs(width - w) <= 100 and abs(height - h) <= 100:
                best_score = score
                break
        
        return best_score
    
    def _predict_with_model(self, features: np.ndarray, platform: str) -> Dict[str, float]:
        """Make predictions using platform-specific model"""
        if platform not in self.models:
            # Use heuristic scoring if no model available
            return self._heuristic_scoring(features)
        
        model = self.models[platform]
        scaler = self.scalers[platform]
        
        # Scale features
        features_scaled = scaler.transform(features)
        
        # Make predictions
        predictions = model.predict(features_scaled)[0]
        
        # Parse predictions (assuming multi-output model)
        return {
            'overall_score': max(0, min(100, predictions[0])),
            'predicted_views': max(0, int(predictions[1])),
            'predicted_engagement_rate': max(0, min(1, predictions[2])),
            'hook_score': max(0, min(100, predictions[3])),
            'content_score': max(0, min(100, predictions[4])),
            'cta_score': max(0, min(100, predictions[5]))
        }
    
    def _heuristic_scoring(self, features: np.ndarray) -> Dict[str, float]:
        """Fallback heuristic scoring when no trained model is available"""
        # Extract key features for heuristic calculation
        hook_potential = features[0][0] if len(features[0]) > 0 else 50
        energy_level = features[0][9] if len(features[0]) > 9 else 50
        motion = features[0][8] if len(features[0]) > 8 else 50
        composition = features[0][5] if len(features[0]) > 5 else 50
        
        # Simple heuristic calculations
        hook_score = min(100, hook_potential)
        content_score = min(100, (energy_level + motion + composition) / 3)
        cta_score = min(100, (hook_potential + composition) / 2)
        overall_score = (hook_score * 0.4 + content_score * 0.4 + cta_score * 0.2)
        
        return {
            'overall_score': overall_score,
            'predicted_views': int(overall_score * 1000),  # Rough estimate
            'predicted_engagement_rate': overall_score / 100 * 0.1,  # 0-10% range
            'hook_score': hook_score,
            'content_score': content_score,
            'cta_score': cta_score
        }
    
    def _calculate_confidence(self, features: np.ndarray, platform: str) -> float:
        """Calculate prediction confidence interval"""
        if platform not in self.models:
            return 0.6  # Lower confidence for heuristic
        
        # For now, return a confidence based on feature completeness
        feature_completeness = np.sum(features != 0) / len(features[0])
        base_confidence = 0.7
        confidence = base_confidence + (feature_completeness * 0.3)
        
        return min(0.95, confidence)
    
    def _generate_recommendations(self, analysis_result: Dict, prediction: Dict) -> List[str]:
        """Generate actionable recommendations based on analysis"""
        recommendations = []
        
        visual = analysis_result.get('visual_metrics', {})
        audio = analysis_result.get('audio_metrics', {})
        
        # Hook recommendations
        hook_potential = visual.get('hook_potential', 0)
        if hook_potential < 60:
            recommendations.append("Improve hook: Add motion or faces in the first 3 seconds")
            if visual.get('face_count', 0) < 1:
                recommendations.append("Consider including faces early to capture attention")
        
        # Visual recommendations
        if visual.get('energy_level', 0) < 50:
            recommendations.append("Increase visual energy with faster cuts or more motion")
        
        if visual.get('color_diversity', 0) < 40:
            recommendations.append("Use more diverse colors to make content more engaging")
        
        if visual.get('text_clarity_score', 0) < 0.3:
            recommendations.append("Improve text readability with better contrast and sizing")
        
        # Audio recommendations
        if audio.get('energy', 0) < 0.3:
            recommendations.append("Consider adding more energetic audio to boost engagement")
        
        tempo = audio.get('tempo', 120)
        if tempo < 80:
            recommendations.append("Consider faster-paced audio to maintain viewer attention")
        elif tempo > 160:
            recommendations.append("Audio tempo might be too fast - consider slowing down")
        
        # Composition recommendations
        if visual.get('avg_scene_duration', 5) > 4:
            recommendations.append("Shorter scenes (2-3 seconds) typically perform better")
        
        # Overall performance recommendations
        if prediction['overall_score'] < 70:
            recommendations.append("Overall score is below threshold - focus on hook and pacing")
        
        return recommendations[:5]  # Limit to top 5 recommendations
    
    def _get_feature_importance(self, platform: str) -> Dict[str, float]:
        """Get feature importance from trained model"""
        if platform not in self.models:
            return {}
        
        model = self.models[platform]
        if hasattr(model, 'feature_importances_'):
            importance = model.feature_importances_
            feature_names = self._get_feature_names()
            
            return dict(zip(feature_names, importance.tolist()))
        
        return {}
    
    def _get_feature_names(self) -> List[str]:
        """Get list of feature names"""
        names = []
        names.extend(self.feature_config['visual_features'])
        names.extend(self.feature_config['audio_features'])
        names.extend([f'mfcc_{i}' for i in range(13)])  # MFCC coefficients
        names.extend(self.feature_config['metadata_features'])
        names.extend(self.feature_config['temporal_features'])
        names.extend(['sync_score', 'pacing_score', 'engagement_potential', 'visual_complexity'])
        
        return names
    
    def train_model(self, training_data: pd.DataFrame, platform: PlatformType) -> Dict[str, float]:
        """
        Train a new model for a specific platform
        
        Args:
            training_data: DataFrame with features and target variables
            platform: Target platform
            
        Returns:
            Training metrics
        """
        try:
            # Prepare features and targets
            feature_columns = self._get_feature_names()
            X = training_data[feature_columns]
            
            # Multiple targets: overall_score, views, engagement_rate, hook_score, content_score, cta_score
            y = training_data[['overall_score', 'views', 'engagement_rate', 'hook_score', 'content_score', 'cta_score']]
            
            # Split data
            X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)
            
            # Scale features
            scaler = StandardScaler()
            X_train_scaled = scaler.fit_transform(X_train)
            X_test_scaled = scaler.transform(X_test)
            
            # Train model (using RandomForest for multi-output regression)
            model = RandomForestRegressor(
                n_estimators=100,
                max_depth=10,
                min_samples_split=5,
                min_samples_leaf=2,
                random_state=42,
                n_jobs=-1
            )
            
            model.fit(X_train_scaled, y_train)
            
            # Make predictions
            y_pred = model.predict(X_test_scaled)
            
            # Calculate metrics
            metrics = {}
            target_names = ['overall_score', 'views', 'engagement_rate', 'hook_score', 'content_score', 'cta_score']
            
            for i, target in enumerate(target_names):
                mae = mean_absolute_error(y_test.iloc[:, i], y_pred[:, i])
                rmse = np.sqrt(mean_squared_error(y_test.iloc[:, i], y_pred[:, i]))
                r2 = r2_score(y_test.iloc[:, i], y_pred[:, i])
                
                metrics[f'{target}_mae'] = mae
                metrics[f'{target}_rmse'] = rmse
                metrics[f'{target}_r2'] = r2
            
            # Save model and scaler
            self.models[platform.value] = model
            self.scalers[platform.value] = scaler
            self._save_models()
            
            logger.info(f"Model trained for platform {platform.value} with R² scores: {[metrics[f'{t}_r2'] for t in target_names]}")
            
            return metrics
            
        except Exception as e:
            logger.error(f"Error training model: {e}")
            raise
    
    def _save_models(self):
        """Save trained models and scalers to disk"""
        try:
            for platform, model in self.models.items():
                model_path = self.model_dir / f"{platform}_model.pkl"
                scaler_path = self.model_dir / f"{platform}_scaler.pkl"
                
                joblib.dump(model, model_path)
                joblib.dump(self.scalers[platform], scaler_path)
            
            # Save metadata
            metadata = {
                'model_version': self.model_version,
                'feature_names': self._get_feature_names(),
                'platforms': list(self.models.keys()),
                'saved_at': datetime.now().isoformat()
            }
            
            metadata_path = self.model_dir / "model_metadata.json"
            with open(metadata_path, 'w') as f:
                json.dump(metadata, f, indent=2)
                
        except Exception as e:
            logger.error(f"Error saving models: {e}")
    
    def _load_models(self):
        """Load existing models from disk"""
        try:
            metadata_path = self.model_dir / "model_metadata.json"
            if not metadata_path.exists():
                logger.info("No existing models found")
                return
            
            with open(metadata_path, 'r') as f:
                metadata = json.load(f)
            
            self.model_version = metadata.get('model_version', '1.0')
            platforms = metadata.get('platforms', [])
            
            for platform in platforms:
                model_path = self.model_dir / f"{platform}_model.pkl"
                scaler_path = self.model_dir / f"{platform}_scaler.pkl"
                
                if model_path.exists() and scaler_path.exists():
                    self.models[platform] = joblib.load(model_path)
                    self.scalers[platform] = joblib.load(scaler_path)
                    logger.info(f"Loaded model for platform: {platform}")
            
        except Exception as e:
            logger.error(f"Error loading models: {e}")
    
    def retrain_all_models(self, training_data: Dict[str, pd.DataFrame]) -> Dict[str, Dict[str, float]]:
        """
        Retrain all platform models with new data
        
        Args:
            training_data: Dictionary mapping platform names to training DataFrames
            
        Returns:
            Training metrics for each platform
        """
        results = {}
        
        for platform_name, data in training_data.items():
            try:
                platform = PlatformType(platform_name)
                metrics = self.train_model(data, platform)
                results[platform_name] = metrics
            except Exception as e:
                logger.error(f"Error training model for {platform_name}: {e}")
                results[platform_name] = {'error': str(e)}
        
        return results