import cv2
import numpy as np
import logging
from typing import Dict, List, Tuple, Optional, Any
from pathlib import Path
import json
import time
from dataclasses import dataclass
import asyncio
from concurrent.futures import ThreadPoolExecutor
import librosa
import tempfile
import subprocess
from collections import defaultdict

logger = logging.getLogger(__name__)

@dataclass
class VisualMetrics:
    """Container for visual analysis metrics"""
    hook_potential: float
    scene_count: int
    avg_scene_duration: float
    text_clarity_score: float
    object_count: int
    composition_score: float
    color_diversity: float
    contrast_score: float
    motion_intensity: float
    energy_level: float
    face_count: int
    emotion_scores: Dict[str, float]

@dataclass
class AudioMetrics:
    """Container for audio analysis metrics"""
    duration: float
    tempo: float
    energy: float
    spectral_centroid: float
    zero_crossing_rate: float
    mfcc_features: List[float]
    onset_strength: float
    beat_positions: List[float]
    dominant_frequency: float
    audio_clarity: float

class VideoAnalyzer:
    """Advanced computer vision and audio analysis for viral video prediction"""
    
    def __init__(self):
        self.face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')
        self.object_detector = None  # Will initialize YOLO if available
        self.executor = ThreadPoolExecutor(max_workers=4)
        
        # Try to load YOLO model
        self._init_yolo()
        
        # Video analysis parameters
        self.hook_duration = 3.0  # Analyze first 3 seconds for hook
        self.sample_rate = 1.0    # Sample every 1 second for analysis
        
    def _init_yolo(self):
        """Initialize YOLO object detection model"""
        try:
            # This would require downloading YOLO weights
            # For now, we'll use a placeholder that can be extended
            logger.info("YOLO model initialization skipped - implement with actual weights")
        except Exception as e:
            logger.warning(f"Could not initialize YOLO: {e}")
    
    async def analyze_video(self, video_path: str) -> Dict[str, Any]:
        """
        Comprehensive video analysis combining visual and audio metrics
        
        Args:
            video_path: Path to the video file
            
        Returns:
            Dictionary containing all analysis metrics
        """
        start_time = time.time()
        
        try:
            # Run visual and audio analysis in parallel
            visual_task = asyncio.create_task(
                asyncio.get_event_loop().run_in_executor(
                    self.executor, self._analyze_visual, video_path
                )
            )
            
            audio_task = asyncio.create_task(
                asyncio.get_event_loop().run_in_executor(
                    self.executor, self._analyze_audio, video_path
                )
            )
            
            visual_metrics, audio_metrics = await asyncio.gather(visual_task, audio_task)
            
            # Combine metrics and calculate composite scores
            analysis_result = {
                'visual_metrics': visual_metrics.__dict__ if visual_metrics else {},
                'audio_metrics': audio_metrics.__dict__ if audio_metrics else {},
                'composite_scores': self._calculate_composite_scores(visual_metrics, audio_metrics),
                'processing_time': time.time() - start_time,
                'analysis_version': '1.0'
            }
            
            return analysis_result
            
        except Exception as e:
            logger.error(f"Error analyzing video {video_path}: {e}")
            return {
                'error': str(e),
                'processing_time': time.time() - start_time,
                'analysis_version': '1.0'
            }
    
    def _analyze_visual(self, video_path: str) -> Optional[VisualMetrics]:
        """Analyze visual aspects of the video"""
        try:
            cap = cv2.VideoCapture(video_path)
            
            if not cap.isOpened():
                logger.error(f"Could not open video: {video_path}")
                return None
            
            fps = cap.get(cv2.CAP_PROP_FPS)
            total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
            duration = total_frames / fps if fps > 0 else 0
            
            # Initialize tracking variables
            scene_changes = []
            motion_scores = []
            color_histograms = []
            contrast_scores = []
            face_counts = []
            object_counts = []
            text_regions = []
            
            frame_count = 0
            prev_frame = None
            sample_interval = max(1, int(fps * self.sample_rate))
            
            while True:
                ret, frame = cap.read()
                if not ret:
                    break
                
                if frame_count % sample_interval == 0:
                    # Resize for faster processing
                    frame_resized = cv2.resize(frame, (640, 360))
                    
                    # Scene change detection
                    if prev_frame is not None:
                        scene_change = self._detect_scene_change(prev_frame, frame_resized)
                        scene_changes.append(scene_change)
                    
                    # Motion analysis
                    motion_score = self._calculate_motion_intensity(frame_resized, prev_frame)
                    motion_scores.append(motion_score)
                    
                    # Color analysis
                    color_hist = self._analyze_color_distribution(frame_resized)
                    color_histograms.append(color_hist)
                    
                    # Contrast analysis
                    contrast = self._calculate_contrast(frame_resized)
                    contrast_scores.append(contrast)
                    
                    # Face detection
                    faces = self._detect_faces(frame_resized)
                    face_counts.append(len(faces))
                    
                    # Object detection (simplified)
                    objects = self._detect_objects(frame_resized)
                    object_counts.append(len(objects))
                    
                    # Text detection
                    text_score = self._detect_text_regions(frame_resized)
                    text_regions.append(text_score)
                    
                    prev_frame = frame_resized.copy()
                
                frame_count += 1
            
            cap.release()
            
            # Calculate hook potential (first 3 seconds)
            hook_frames = int(fps * self.hook_duration)
            hook_motion = np.mean(motion_scores[:hook_frames]) if motion_scores else 0
            hook_faces = np.mean(face_counts[:hook_frames]) if face_counts else 0
            hook_potential = self._calculate_hook_potential(hook_motion, hook_faces, contrast_scores[:hook_frames])
            
            # Calculate scene metrics
            scene_count = len([sc for sc in scene_changes if sc > 0.3])  # Threshold for scene change
            avg_scene_duration = duration / max(scene_count, 1)
            
            # Calculate other metrics
            text_clarity = np.mean(text_regions) if text_regions else 0
            avg_objects = np.mean(object_counts) if object_counts else 0
            composition_score = self._calculate_composition_score(face_counts, object_counts)
            color_diversity = self._calculate_color_diversity(color_histograms)
            avg_contrast = np.mean(contrast_scores) if contrast_scores else 0
            avg_motion = np.mean(motion_scores) if motion_scores else 0
            energy_level = self._calculate_energy_level(motion_scores, contrast_scores)
            avg_faces = np.mean(face_counts) if face_counts else 0
            
            return VisualMetrics(
                hook_potential=hook_potential,
                scene_count=scene_count,
                avg_scene_duration=avg_scene_duration,
                text_clarity_score=text_clarity,
                object_count=avg_objects,
                composition_score=composition_score,
                color_diversity=color_diversity,
                contrast_score=avg_contrast,
                motion_intensity=avg_motion,
                energy_level=energy_level,
                face_count=avg_faces,
                emotion_scores={}  # Placeholder for emotion detection
            )
            
        except Exception as e:
            logger.error(f"Error in visual analysis: {e}")
            return None
    
    def _analyze_audio(self, video_path: str) -> Optional[AudioMetrics]:
        """Analyze audio aspects of the video"""
        try:
            # Extract audio from video
            with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as temp_audio:
                temp_audio_path = temp_audio.name
            
            # Use ffmpeg to extract audio
            cmd = [
                'ffmpeg', '-i', video_path, '-vn', '-acodec', 'pcm_s16le',
                '-ar', '22050', '-ac', '1', temp_audio_path, '-y'
            ]
            
            try:
                subprocess.run(cmd, check=True, capture_output=True)
            except subprocess.CalledProcessError:
                logger.warning("Could not extract audio from video")
                return None
            
            # Load audio with librosa
            y, sr = librosa.load(temp_audio_path, sr=22050)
            
            # Clean up temp file
            Path(temp_audio_path).unlink(missing_ok=True)
            
            if len(y) == 0:
                return None
            
            # Calculate audio features
            duration = len(y) / sr
            
            # Tempo and beat tracking
            tempo, beats = librosa.beat.beat_track(y=y, sr=sr)
            beat_positions = librosa.frames_to_time(beats, sr=sr).tolist()
            
            # Spectral features
            spectral_centroids = librosa.feature.spectral_centroid(y=y, sr=sr)
            spectral_centroid = np.mean(spectral_centroids)
            
            # Zero crossing rate
            zcr = librosa.feature.zero_crossing_rate(y)
            zero_crossing_rate = np.mean(zcr)
            
            # MFCC features
            mfccs = librosa.feature.mfcc(y=y, sr=sr, n_mfcc=13)
            mfcc_features = np.mean(mfccs, axis=1).tolist()
            
            # Onset strength
            onset_envelope = librosa.onset.onset_strength(y=y, sr=sr)
            onset_strength = np.mean(onset_envelope)
            
            # Energy
            rms = librosa.feature.rms(y=y)
            energy = np.mean(rms)
            
            # Dominant frequency
            fft = np.fft.fft(y)
            freqs = np.fft.fftfreq(len(fft), 1/sr)
            dominant_freq = freqs[np.argmax(np.abs(fft))]
            
            # Audio clarity (simplified spectral flatness)
            spectral_flatness = librosa.feature.spectral_flatness(y=y)
            audio_clarity = 1.0 - np.mean(spectral_flatness)  # Inverse of flatness
            
            return AudioMetrics(
                duration=duration,
                tempo=float(tempo),
                energy=float(energy),
                spectral_centroid=float(spectral_centroid),
                zero_crossing_rate=float(zero_crossing_rate),
                mfcc_features=mfcc_features,
                onset_strength=float(onset_strength),
                beat_positions=beat_positions,
                dominant_frequency=float(abs(dominant_freq)),
                audio_clarity=float(audio_clarity)
            )
            
        except Exception as e:
            logger.error(f"Error in audio analysis: {e}")
            return None
    
    def _detect_scene_change(self, frame1: np.ndarray, frame2: np.ndarray) -> float:
        """Detect scene changes between frames"""
        # Convert to grayscale
        gray1 = cv2.cvtColor(frame1, cv2.COLOR_BGR2GRAY)
        gray2 = cv2.cvtColor(frame2, cv2.COLOR_BGR2GRAY)
        
        # Calculate histogram difference
        hist1 = cv2.calcHist([gray1], [0], None, [256], [0, 256])
        hist2 = cv2.calcHist([gray2], [0], None, [256], [0, 256])
        
        # Compare histograms
        correlation = cv2.compareHist(hist1, hist2, cv2.HISTCMP_CORREL)
        return 1.0 - correlation  # Higher value = more change
    
    def _calculate_motion_intensity(self, frame: np.ndarray, prev_frame: Optional[np.ndarray]) -> float:
        """Calculate motion intensity between frames"""
        if prev_frame is None:
            return 0.0
        
        # Convert to grayscale
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        prev_gray = cv2.cvtColor(prev_frame, cv2.COLOR_BGR2GRAY)
        
        # Calculate optical flow
        flow = cv2.calcOpticalFlowPyrLK(prev_gray, gray, None, None)
        
        # Calculate motion magnitude
        if flow[0] is not None and len(flow[0]) > 0:
            motion_vectors = flow[0] - flow[1] if flow[1] is not None else flow[0]
            motion_magnitude = np.mean(np.sqrt(np.sum(motion_vectors**2, axis=1)))
            return min(motion_magnitude / 10.0, 1.0)  # Normalize to 0-1
        
        return 0.0
    
    def _analyze_color_distribution(self, frame: np.ndarray) -> np.ndarray:
        """Analyze color distribution in frame"""
        # Calculate color histogram in HSV space
        hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
        hist = cv2.calcHist([hsv], [0, 1, 2], None, [50, 60, 60], [0, 180, 0, 256, 0, 256])
        return hist.flatten()
    
    def _calculate_contrast(self, frame: np.ndarray) -> float:
        """Calculate contrast score for frame"""
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        return np.std(gray) / 255.0  # Normalized standard deviation
    
    def _detect_faces(self, frame: np.ndarray) -> List[Tuple[int, int, int, int]]:
        """Detect faces in frame"""
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        faces = self.face_cascade.detectMultiScale(gray, 1.1, 4)
        return faces.tolist()
    
    def _detect_objects(self, frame: np.ndarray) -> List[Dict]:
        """Detect objects in frame (simplified implementation)"""
        # Placeholder for YOLO object detection
        # In production, this would use a trained YOLO model
        return []
    
    def _detect_text_regions(self, frame: np.ndarray) -> float:
        """Detect and score text regions in frame"""
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        
        # Use edge detection to find potential text regions
        edges = cv2.Canny(gray, 50, 150)
        contours, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        # Score based on rectangular contours (potential text)
        text_score = 0.0
        for contour in contours:
            area = cv2.contourArea(contour)
            if area > 100:  # Minimum area for text
                x, y, w, h = cv2.boundingRect(contour)
                aspect_ratio = w / h if h > 0 else 0
                if 0.1 < aspect_ratio < 10:  # Reasonable text aspect ratios
                    text_score += area
        
        # Normalize by frame area
        frame_area = frame.shape[0] * frame.shape[1]
        return min(text_score / frame_area, 1.0)
    
    def _calculate_hook_potential(self, motion: float, faces: float, contrast_scores: List[float]) -> float:
        """Calculate hook potential score for first 3 seconds"""
        # Combine motion, face presence, and visual contrast
        contrast_score = np.mean(contrast_scores) if contrast_scores else 0
        
        # Weighted combination
        hook_score = (
            motion * 0.4 +           # Motion captures attention
            (min(faces, 1.0)) * 0.3 + # Face presence (capped at 1)
            contrast_score * 0.3      # Visual contrast
        )
        
        return min(hook_score, 1.0) * 100  # Scale to 0-100
    
    def _calculate_composition_score(self, face_counts: List[int], object_counts: List[int]) -> float:
        """Calculate composition quality score"""
        if not face_counts and not object_counts:
            return 0.0
        
        # Ideal composition has 1-3 faces and moderate object count
        avg_faces = np.mean(face_counts) if face_counts else 0
        avg_objects = np.mean(object_counts) if object_counts else 0
        
        # Score based on optimal ranges
        face_score = 1.0 - abs(2 - avg_faces) / 3.0  # Optimal around 2 faces
        object_score = min(avg_objects / 10.0, 1.0)  # More objects = higher score, capped
        
        return max((face_score + object_score) / 2.0, 0.0) * 100
    
    def _calculate_color_diversity(self, color_histograms: List[np.ndarray]) -> float:
        """Calculate color diversity score"""
        if not color_histograms:
            return 0.0
        
        # Calculate entropy of average color histogram
        avg_hist = np.mean(color_histograms, axis=0)
        avg_hist = avg_hist / np.sum(avg_hist)  # Normalize
        
        # Calculate entropy (higher = more diverse)
        entropy = -np.sum(avg_hist * np.log(avg_hist + 1e-10))
        
        # Normalize to 0-100 scale
        max_entropy = np.log(len(avg_hist))
        return (entropy / max_entropy) * 100
    
    def _calculate_energy_level(self, motion_scores: List[float], contrast_scores: List[float]) -> float:
        """Calculate overall energy level of video"""
        if not motion_scores and not contrast_scores:
            return 0.0
        
        motion_energy = np.mean(motion_scores) if motion_scores else 0
        visual_energy = np.mean(contrast_scores) if contrast_scores else 0
        
        # Combine motion and visual energy
        total_energy = (motion_energy * 0.7 + visual_energy * 0.3)
        return total_energy * 100
    
    def _calculate_composite_scores(self, visual: Optional[VisualMetrics], audio: Optional[AudioMetrics]) -> Dict[str, float]:
        """Calculate composite scores combining visual and audio analysis"""
        scores = {
            'hook_score': 0.0,
            'content_score': 0.0,
            'cta_score': 0.0,
            'overall_score': 0.0
        }
        
        if visual:
            # Hook score (first impression)
            scores['hook_score'] = visual.hook_potential
            
            # Content score (visual quality and engagement)
            content_factors = [
                visual.composition_score * 0.25,
                visual.color_diversity * 0.2,
                visual.motion_intensity * 0.2,
                visual.energy_level * 0.2,
                visual.text_clarity_score * 100 * 0.15
            ]
            scores['content_score'] = sum(content_factors)
            
            # CTA score (text clarity and scene structure)
            cta_factors = [
                visual.text_clarity_score * 100 * 0.6,
                (100 - min(visual.avg_scene_duration * 10, 100)) * 0.4  # Shorter scenes = better pacing
            ]
            scores['cta_score'] = sum(cta_factors)
        
        if audio:
            # Enhance scores with audio data
            audio_boost = min(audio.energy * 100, 20)  # Max 20 point boost
            scores['content_score'] += audio_boost * 0.5
            scores['hook_score'] += audio_boost * 0.3
            
            # Tempo affects engagement
            if 60 <= audio.tempo <= 140:  # Optimal tempo range
                tempo_boost = 10
            else:
                tempo_boost = max(0, 10 - abs(audio.tempo - 100) / 10)
            
            scores['content_score'] += tempo_boost
        
        # Calculate overall score
        scores['overall_score'] = (
            scores['hook_score'] * 0.4 +
            scores['content_score'] * 0.4 +
            scores['cta_score'] * 0.2
        )
        
        # Ensure all scores are in 0-100 range
        for key in scores:
            scores[key] = max(0, min(100, scores[key]))
        
        return scores