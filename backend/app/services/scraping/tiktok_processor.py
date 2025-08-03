"""
TikTok Trend Data Processing Pipeline

Processes raw TikTok scraping data from Apify into structured trend insights.
Performs pattern recognition, viral analysis, and data normalization for
the ViralOS content generation pipeline.
"""

import asyncio
import json
import re
import time
from collections import Counter, defaultdict
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Tuple, Set
import hashlib
import statistics
import logging

import numpy as np
from sqlalchemy.orm import Session
from sqlalchemy import desc, func, and_, or_

from app.core.config import settings
from app.db.session import get_db
from app.models.tiktok_trend import (
    TikTokTrend, TikTokVideo, TikTokHashtag, TikTokSound,
    TikTokScrapingJob, TikTokAnalytics,
    TrendStatus, TrendType, ContentCategory
)
from app.services.ai.providers import get_text_service
from app.services.ai.vector_db import get_vector_service

logger = logging.getLogger(__name__)


class TrendPatternRecognizer:
    """Recognizes viral patterns and trends in TikTok content"""
    
    def __init__(self):
        self.viral_keywords = {
            'challenge': ['challenge', 'try this', 'attempt', 'dare', 'test'],
            'tutorial': ['how to', 'tutorial', 'guide', 'learn', 'diy', 'hack', 'tip'],
            'storytime': ['storytime', 'story time', 'story', 'tell', 'experience'],
            'transformation': ['transformation', 'before after', 'makeover', 'glow up'],
            'reaction': ['reaction', 'react', 'response', 'thoughts on'],
            'duet': ['duet', 'duetting', 'responding to'],
            'trend_participation': ['trend', 'trending', 'viral', 'fyp'],
            'lifestyle': ['day in my life', 'routine', 'lifestyle', 'morning'],
            'dance': ['dance', 'choreo', 'moves', 'dancing'],
            'comedy': ['funny', 'comedy', 'humor', 'joke', 'laugh'],
            'educational': ['facts', 'learn', 'education', 'did you know', 'fun fact']
        }
        
        self.hook_patterns = [
            r'^(POV|POV:)',
            r'^(When|If)\s+you',
            r'^(Imagine|What if)',
            r'^(Did you know|Fun fact)',
            r'^(This|That)\s+moment\s+when',
            r'^(Me|You)\s+when',
            r'^(Nobody|Everyone):',
            r'(Wait for it|Plot twist)',
            r'(You won\'t believe|This is crazy)',
            r'^\w+\s+challenge',
            r'(Rate this|Thoughts\?)',
            r'(Tell me|Am I the only one)'
        ]
        
        self.viral_indicators = {
            'engagement_spike': 0.05,  # 5% engagement rate threshold
            'view_velocity': 10000,    # Views per hour
            'share_ratio': 0.02,       # Share to view ratio
            'comment_ratio': 0.01,     # Comment to view ratio
            'like_ratio': 0.03         # Like to view ratio
        }

    def analyze_content_type(self, description: str, hashtags: List[str]) -> ContentCategory:
        """Classify content into categories"""
        
        if not description:
            return ContentCategory.OTHER
        
        desc_lower = description.lower()
        all_hashtags = ' '.join(hashtags).lower()
        combined_text = f"{desc_lower} {all_hashtags}"
        
        # Category scoring
        scores = defaultdict(int)
        
        # Educational content
        if any(kw in combined_text for kw in ['tutorial', 'how to', 'learn', 'tips', 'hack', 'guide']):
            scores[ContentCategory.EDUCATION] += 3
        
        # Entertainment content
        if any(kw in combined_text for kw in ['funny', 'comedy', 'dance', 'music', 'challenge']):
            scores[ContentCategory.ENTERTAINMENT] += 3
        
        # Lifestyle content
        if any(kw in combined_text for kw in ['lifestyle', 'routine', 'day in', 'morning', 'self care']):
            scores[ContentCategory.LIFESTYLE] += 3
        
        # Fashion/beauty content
        if any(kw in combined_text for kw in ['fashion', 'outfit', 'makeup', 'beauty', 'skincare', 'style']):
            scores[ContentCategory.FASHION] += 3
        
        # Food content
        if any(kw in combined_text for kw in ['recipe', 'cooking', 'food', 'meal', 'cook', 'baking']):
            scores[ContentCategory.FOOD] += 3
        
        # Fitness content
        if any(kw in combined_text for kw in ['workout', 'fitness', 'gym', 'exercise', 'health']):
            scores[ContentCategory.FITNESS] += 3
        
        # Technology content
        if any(kw in combined_text for kw in ['tech', 'technology', 'app', 'phone', 'computer', 'ai']):
            scores[ContentCategory.TECHNOLOGY] += 3
        
        # Business content
        if any(kw in combined_text for kw in ['business', 'entrepreneur', 'money', 'career', 'job']):
            scores[ContentCategory.BUSINESS] += 3
        
        # News content
        if any(kw in combined_text for kw in ['news', 'breaking', 'update', 'announcement']):
            scores[ContentCategory.NEWS] += 3
        
        if scores:
            return max(scores.items(), key=lambda x: x[1])[0]
        
        return ContentCategory.OTHER

    def extract_content_hooks(self, description: str) -> List[str]:
        """Extract viral hooks from content description"""
        
        if not description:
            return []
        
        hooks = []
        
        for pattern in self.hook_patterns:
            matches = re.findall(pattern, description, re.IGNORECASE | re.MULTILINE)
            if matches:
                hooks.extend(matches)
        
        # Extract questions
        questions = re.findall(r'[.!?]\s*([^.!?]*\?)', description)
        hooks.extend([q.strip() for q in questions if len(q.strip()) > 5])
        
        # Extract the first sentence as potential hook
        first_sentence = re.split(r'[.!?]', description)[0].strip()
        if len(first_sentence) > 10 and len(first_sentence) < 100:
            hooks.append(first_sentence)
        
        return list(set(hooks))[:5]  # Return unique hooks, max 5

    def identify_trend_type(self, description: str, hashtags: List[str], sounds: List[str]) -> TrendType:
        """Identify the type of trend"""
        
        desc_lower = description.lower() if description else ""
        hashtag_text = ' '.join(hashtags).lower()
        
        # Challenge detection
        if any(kw in desc_lower for kw in ['challenge', 'try this', 'attempt']):
            return TrendType.CHALLENGE
        
        # Dance detection
        if any(kw in desc_lower for kw in ['dance', 'choreo', 'moves']) or \
           any('#dance' in tag.lower() for tag in hashtags):
            return TrendType.DANCE
        
        # Sound trend
        if sounds or any('sound' in tag.lower() for tag in hashtags):
            return TrendType.SOUND
        
        # Hashtag trend
        if len(hashtags) > 8 or any(tag.lower() in ['#trending', '#viral', '#fyp'] for tag in hashtags):
            return TrendType.HASHTAG
        
        # Meme detection
        if any(kw in desc_lower for kw in ['meme', 'funny', 'comedy', 'humor']):
            return TrendType.MEME
        
        # Format trend
        if any(kw in desc_lower for kw in ['pov', 'when', 'nobody:', 'me when']):
            return TrendType.TREND_FORMAT
        
        return TrendType.VIRAL_VIDEO

    def calculate_viral_score(self, video_data: Dict[str, Any]) -> float:
        """Calculate viral score for a video"""
        
        stats = video_data.get('stats', {})
        views = stats.get('views', 0)
        likes = stats.get('likes', 0)
        shares = stats.get('shares', 0)
        comments = stats.get('comments', 0)
        
        if views == 0:
            return 0.0
        
        # Calculate ratios
        engagement_rate = ((likes + shares + comments) / views) * 100
        like_ratio = (likes / views) * 100
        share_ratio = (shares / views) * 100
        comment_ratio = (comments / views) * 100
        
        score = 0.0
        
        # Engagement rate component (0-40 points)
        score += min(engagement_rate * 8, 40)
        
        # View count component (0-25 points)
        if views > 10000000:  # 10M+
            score += 25
        elif views > 1000000:  # 1M+
            score += 20
        elif views > 100000:   # 100K+
            score += 15
        elif views > 10000:    # 10K+
            score += 10
        elif views > 1000:     # 1K+
            score += 5
        
        # Share component (0-15 points)
        score += min(share_ratio * 750, 15)  # 0.02% share ratio = 15 points
        
        # Content quality indicators (0-20 points)
        content_analysis = video_data.get('contentAnalysis', {})
        
        # Hooks bonus
        hooks = content_analysis.get('hooks', [])
        score += min(len(hooks) * 3, 9)
        
        # Hashtag strategy bonus
        hashtags = video_data.get('hashtags', [])
        if 5 <= len(hashtags) <= 15:  # Optimal hashtag count
            score += 3
        
        # Trending hashtag bonus
        viral_hashtags = ['#fyp', '#viral', '#trending', '#foryou', '#foryoupage']
        if any(tag.lower() in viral_hashtags for tag in hashtags):
            score += 5
        
        # Duration bonus (if available)
        duration = video_data.get('duration')
        if duration and 15 <= duration <= 60:  # Optimal duration
            score += 3
        
        return min(round(score, 2), 100.0)

    def detect_trend_status(self, trend_data: Dict[str, Any]) -> TrendStatus:
        """Detect the current status of a trend"""
        
        # This would typically involve time-series analysis
        # For now, we'll use simplified heuristics
        
        viral_score = trend_data.get('viral_score', 0)
        growth_rate = trend_data.get('growth_rate', 0)
        volume = trend_data.get('total_videos', 0)
        age_hours = trend_data.get('age_hours', 0)
        
        # Emerging: High growth, low volume, recent
        if growth_rate > 200 and volume < 10000 and age_hours < 24:
            return TrendStatus.EMERGING
        
        # Rising: Good growth, increasing volume
        elif growth_rate > 100 and volume < 100000 and age_hours < 72:
            return TrendStatus.RISING
        
        # Peak: High volume, stable or declining growth
        elif volume > 50000 and viral_score > 60:
            return TrendStatus.PEAK
        
        # Declining: Negative growth, high volume
        elif growth_rate < 0 and volume > 100000:
            return TrendStatus.DECLINING
        
        # Fading: Very low activity
        elif viral_score < 20 and growth_rate < 10:
            return TrendStatus.FADING
        
        # Default to rising for active trends
        return TrendStatus.RISING

    def extract_hashtag_clusters(self, hashtags_data: List[Dict[str, Any]]) -> Dict[str, List[str]]:
        """Group related hashtags into clusters"""
        
        clusters = defaultdict(list)
        
        for hashtag_info in hashtags_data:
            hashtag = hashtag_info.get('hashtag', '').lower()
            
            # Simple clustering based on common words
            words = re.findall(r'[a-zA-Z]+', hashtag)
            
            for word in words:
                if len(word) > 3:  # Skip very short words
                    clusters[word].append(hashtag)
        
        # Filter clusters with multiple hashtags
        return {k: v for k, v in clusters.items() if len(v) > 1}


class TikTokDataProcessor:
    """Main processor for TikTok trend data"""
    
    def __init__(self, db: Session):
        self.db = db
        self.pattern_recognizer = TrendPatternRecognizer()
        self.text_service = None
        self.vector_service = None
    
    async def _get_ai_services(self):
        """Initialize AI services"""
        if self.text_service is None:
            self.text_service = await get_text_service()
        if self.vector_service is None:
            self.vector_service = await get_vector_service()
    
    async def process_scraping_results(
        self,
        job_id: str,
        scraped_data: List[Dict[str, Any]],
        analytics_data: Dict[str, Any] = None,
        trend_analysis: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """
        Process raw scraping results into structured trend data
        
        Args:
            job_id: Scraping job ID
            scraped_data: Raw video data from Apify
            analytics_data: Analytics summary from scraper
            trend_analysis: Trend analysis from scraper
            
        Returns:
            Dict containing processing results
        """
        
        logger.info(f"Processing {len(scraped_data)} videos from job {job_id}")
        
        processing_results = {
            'job_id': job_id,
            'videos_processed': 0,
            'trends_created': 0,
            'hashtags_tracked': 0,
            'sounds_tracked': 0,
            'processing_errors': 0,
            'started_at': datetime.utcnow(),
            'processing_stats': {}
        }
        
        try:
            # Initialize AI services
            await self._get_ai_services()
            
            # Process videos
            video_results = await self._process_videos(scraped_data, job_id)
            processing_results.update(video_results)
            
            # Extract and process hashtags
            hashtag_results = await self._process_hashtags(scraped_data)
            processing_results.update(hashtag_results)
            
            # Extract and process sounds
            sound_results = await self._process_sounds(scraped_data)
            processing_results.update(sound_results)
            
            # Identify and create trends
            trend_results = await self._identify_trends(scraped_data)
            processing_results.update(trend_results)
            
            # Update analytics
            await self._update_analytics(processing_results, analytics_data)
            
            processing_results['finished_at'] = datetime.utcnow()
            processing_results['duration'] = (
                processing_results['finished_at'] - processing_results['started_at']
            ).total_seconds()
            
            logger.info(f"Processing completed for job {job_id}")
            
        except Exception as e:
            logger.error(f"Error processing job {job_id}: {e}")
            processing_results['error'] = str(e)
            processing_results['processing_errors'] += 1
        
        return processing_results
    
    async def _process_videos(self, scraped_data: List[Dict[str, Any]], job_id: str) -> Dict[str, Any]:
        """Process individual video data"""
        
        processed_count = 0
        error_count = 0
        
        for video_data in scraped_data:
            try:
                # Check if video already exists
                video_id = video_data.get('id')
                if not video_id:
                    continue
                
                existing_video = self.db.query(TikTokVideo).filter(
                    TikTokVideo.video_id == video_id
                ).first()
                
                if existing_video:
                    # Update existing video
                    await self._update_video(existing_video, video_data)
                else:
                    # Create new video
                    await self._create_video(video_data, job_id)
                
                processed_count += 1
                
            except Exception as e:
                logger.error(f"Error processing video {video_data.get('id', 'unknown')}: {e}")
                error_count += 1
        
        return {
            'videos_processed': processed_count,
            'video_errors': error_count
        }
    
    async def _create_video(self, video_data: Dict[str, Any], job_id: str):
        """Create new video record"""
        
        # Calculate viral score
        viral_score = self.pattern_recognizer.calculate_viral_score(video_data)
        
        # Extract content hooks
        description = video_data.get('description', '')
        hooks = self.pattern_recognizer.extract_content_hooks(description)
        
        # Classify content
        hashtags = video_data.get('hashtags', [])
        content_category = self.pattern_recognizer.analyze_content_type(description, hashtags)
        
        # Calculate engagement rate
        stats = video_data.get('stats', {})
        views = stats.get('views', 0)
        likes = stats.get('likes', 0)
        shares = stats.get('shares', 0)
        comments = stats.get('comments', 0)
        
        engagement_rate = 0.0
        if views > 0:
            engagement_rate = ((likes + shares + comments) / views) * 100
        
        # Create video record
        video = TikTokVideo(
            video_id=video_data['id'],
            title=video_data.get('title'),
            description=description,
            duration=video_data.get('duration'),
            creator_username=video_data.get('creator', {}).get('username'),
            creator_display_name=video_data.get('creator', {}).get('displayName'),
            creator_follower_count=video_data.get('userMetrics', {}).get('followers', 0),
            creator_verified=video_data.get('creator', {}).get('verified', False),
            view_count=views,
            like_count=likes,
            share_count=shares,
            comment_count=comments,
            engagement_rate=engagement_rate,
            hashtags=hashtags,
            mentions=video_data.get('mentions', []),
            sounds_used=video_data.get('sounds', []),
            effects_used=video_data.get('effects', []),
            content_hooks=hooks,
            video_structure=video_data.get('contentAnalysis', {}).get('structure', {}),
            tiktok_url=video_data.get('url'),
            posted_at=self._parse_timestamp(video_data.get('timestamp')),
            scraped_at=datetime.utcnow(),
            scraping_source='apify',
            raw_data=video_data
        )
        
        self.db.add(video)
        self.db.commit()
    
    async def _update_video(self, existing_video: TikTokVideo, video_data: Dict[str, Any]):
        """Update existing video with new data"""
        
        # Update metrics
        stats = video_data.get('stats', {})
        existing_video.view_count = stats.get('views', existing_video.view_count)
        existing_video.like_count = stats.get('likes', existing_video.like_count)
        existing_video.share_count = stats.get('shares', existing_video.share_count)
        existing_video.comment_count = stats.get('comments', existing_video.comment_count)
        
        # Recalculate engagement rate
        if existing_video.view_count > 0:
            total_engagement = (
                existing_video.like_count + 
                existing_video.share_count + 
                existing_video.comment_count
            )
            existing_video.engagement_rate = (total_engagement / existing_video.view_count) * 100
        
        existing_video.updated_at = datetime.utcnow()
        
        self.db.commit()
    
    async def _process_hashtags(self, scraped_data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Process hashtag data"""
        
        hashtag_stats = defaultdict(lambda: {
            'total_videos': 0,
            'total_views': 0,
            'total_likes': 0,
            'usage_velocity': 0.0,
            'videos': []
        })
        
        # Aggregate hashtag statistics
        for video_data in scraped_data:
            hashtags = video_data.get('hashtags', [])
            stats = video_data.get('stats', {})
            
            for hashtag in hashtags:
                hashtag_clean = hashtag.lower().strip()
                hashtag_stats[hashtag_clean]['total_videos'] += 1
                hashtag_stats[hashtag_clean]['total_views'] += stats.get('views', 0)
                hashtag_stats[hashtag_clean]['total_likes'] += stats.get('likes', 0)
                hashtag_stats[hashtag_clean]['videos'].append(video_data.get('id'))
        
        # Process each hashtag
        processed_count = 0
        
        for hashtag, stats in hashtag_stats.items():
            try:
                await self._create_or_update_hashtag(hashtag, stats)
                processed_count += 1
            except Exception as e:
                logger.error(f"Error processing hashtag {hashtag}: {e}")
        
        return {
            'hashtags_tracked': processed_count
        }
    
    async def _create_or_update_hashtag(self, hashtag: str, stats: Dict[str, Any]):
        """Create or update hashtag record"""
        
        existing_hashtag = self.db.query(TikTokHashtag).filter(
            TikTokHashtag.normalized_hashtag == hashtag.lower()
        ).first()
        
        # Calculate trend score
        trend_score = min((stats['total_videos'] / 1000) + (stats['total_views'] / 1000000), 100)
        is_trending = trend_score > 10
        
        if existing_hashtag:
            # Update existing
            existing_hashtag.total_videos += stats['total_videos']
            existing_hashtag.total_views += stats['total_views']
            existing_hashtag.trend_score = trend_score
            existing_hashtag.is_trending = is_trending
            existing_hashtag.updated_at = datetime.utcnow()
        else:
            # Create new
            new_hashtag = TikTokHashtag(
                hashtag=hashtag,
                normalized_hashtag=hashtag.lower(),
                total_videos=stats['total_videos'],
                total_views=stats['total_views'],
                trend_score=trend_score,
                is_trending=is_trending,
                top_creators=stats.get('top_creators', [])[:10]
            )
            self.db.add(new_hashtag)
        
        self.db.commit()
    
    async def _process_sounds(self, scraped_data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Process sound/music data"""
        
        sound_stats = defaultdict(lambda: {
            'total_videos': 0,
            'total_views': 0,
            'videos': []
        })
        
        # Aggregate sound statistics
        for video_data in scraped_data:
            sounds = video_data.get('sounds', [])
            stats = video_data.get('stats', {})
            
            for sound in sounds:
                sound_stats[sound]['total_videos'] += 1
                sound_stats[sound]['total_views'] += stats.get('views', 0)
                sound_stats[sound]['videos'].append(video_data.get('id'))
        
        # Process each sound
        processed_count = 0
        
        for sound_id, stats in sound_stats.items():
            try:
                await self._create_or_update_sound(sound_id, stats)
                processed_count += 1
            except Exception as e:
                logger.error(f"Error processing sound {sound_id}: {e}")
        
        return {
            'sounds_tracked': processed_count
        }
    
    async def _create_or_update_sound(self, sound_id: str, stats: Dict[str, Any]):
        """Create or update sound record"""
        
        existing_sound = self.db.query(TikTokSound).filter(
            TikTokSound.sound_id == sound_id
        ).first()
        
        # Calculate trend score
        trend_score = min((stats['total_videos'] / 500) + (stats['total_views'] / 500000), 100)
        is_trending = trend_score > 15
        
        if existing_sound:
            # Update existing
            existing_sound.total_videos += stats['total_videos']
            existing_sound.total_views += stats['total_views']
            existing_sound.trend_score = trend_score
            existing_sound.is_trending = is_trending
            existing_sound.updated_at = datetime.utcnow()
        else:
            # Create new
            new_sound = TikTokSound(
                sound_id=sound_id,
                total_videos=stats['total_videos'],
                total_views=stats['total_views'],
                trend_score=trend_score,
                is_trending=is_trending
            )
            self.db.add(new_sound)
        
        self.db.commit()
    
    async def _identify_trends(self, scraped_data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Identify and create trend records"""
        
        # Group videos by similar characteristics
        trend_candidates = await self._find_trend_candidates(scraped_data)
        
        trends_created = 0
        
        for trend_data in trend_candidates:
            try:
                await self._create_or_update_trend(trend_data)
                trends_created += 1
            except Exception as e:
                logger.error(f"Error creating trend: {e}")
        
        return {
            'trends_created': trends_created
        }
    
    async def _find_trend_candidates(self, scraped_data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Find potential trends in the data"""
        
        # Group by hashtags
        hashtag_groups = defaultdict(list)
        sound_groups = defaultdict(list)
        hook_groups = defaultdict(list)
        
        for video_data in scraped_data:
            # Group by hashtags
            hashtags = video_data.get('hashtags', [])
            for hashtag in hashtags:
                hashtag_groups[hashtag.lower()].append(video_data)
            
            # Group by sounds
            sounds = video_data.get('sounds', [])
            for sound in sounds:
                sound_groups[sound].append(video_data)
            
            # Group by content hooks
            content_analysis = video_data.get('contentAnalysis', {})
            hooks = content_analysis.get('hooks', [])
            for hook in hooks:
                hook_groups[hook.lower()].append(video_data)
        
        trend_candidates = []
        
        # Hashtag trends
        for hashtag, videos in hashtag_groups.items():
            if len(videos) >= 5:  # Minimum videos for a trend
                trend_candidates.append(self._create_trend_data(
                    name=hashtag,
                    trend_type=TrendType.HASHTAG,
                    videos=videos
                ))
        
        # Sound trends
        for sound, videos in sound_groups.items():
            if len(videos) >= 3:
                trend_candidates.append(self._create_trend_data(
                    name=f"Sound: {sound}",
                    trend_type=TrendType.SOUND,
                    videos=videos
                ))
        
        # Hook trends
        for hook, videos in hook_groups.items():
            if len(videos) >= 4:
                trend_candidates.append(self._create_trend_data(
                    name=f"Hook: {hook}",
                    trend_type=TrendType.TREND_FORMAT,
                    videos=videos
                ))
        
        return trend_candidates
    
    def _create_trend_data(self, name: str, trend_type: TrendType, videos: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Create trend data structure"""
        
        # Calculate aggregate statistics
        total_views = sum(v.get('stats', {}).get('views', 0) for v in videos)
        total_likes = sum(v.get('stats', {}).get('likes', 0) for v in videos)
        total_shares = sum(v.get('stats', {}).get('shares', 0) for v in videos)
        total_comments = sum(v.get('stats', {}).get('comments', 0) for v in videos)
        
        avg_engagement = 0
        if total_views > 0:
            avg_engagement = ((total_likes + total_shares + total_comments) / total_views) * 100
        
        # Calculate viral score
        viral_scores = [self.pattern_recognizer.calculate_viral_score(v) for v in videos]
        avg_viral_score = statistics.mean(viral_scores) if viral_scores else 0
        
        # Determine trend status
        trend_status = self.pattern_recognizer.detect_trend_status({
            'viral_score': avg_viral_score,
            'growth_rate': len(videos) * 10,  # Simplified growth rate
            'total_videos': len(videos),
            'age_hours': 24  # Assume recent
        })
        
        # Extract keywords
        all_descriptions = ' '.join([v.get('description', '') for v in videos])
        keywords = self._extract_keywords(all_descriptions)
        
        # Extract hashtags
        all_hashtags = []
        for video in videos:
            all_hashtags.extend(video.get('hashtags', []))
        common_hashtags = [tag for tag, count in Counter(all_hashtags).most_common(10)]
        
        return {
            'name': name,
            'trend_type': trend_type,
            'trend_status': trend_status,
            'total_videos': len(videos),
            'total_views': total_views,
            'total_likes': total_likes,
            'total_shares': total_shares,
            'total_comments': total_comments,
            'viral_score': avg_viral_score,
            'engagement_rate': avg_engagement,
            'keywords': keywords,
            'hashtags': common_hashtags,
            'videos': [v.get('id') for v in videos],
            'first_detected': datetime.utcnow()
        }
    
    def _extract_keywords(self, text: str) -> List[str]:
        """Extract keywords from text"""
        
        if not text:
            return []
        
        # Simple keyword extraction
        words = re.findall(r'\b\w+\b', text.lower())
        
        # Filter out common words
        stop_words = {
            'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 
            'of', 'with', 'by', 'is', 'are', 'was', 'were', 'be', 'been', 'have',
            'has', 'had', 'do', 'does', 'did', 'will', 'would', 'could', 'should',
            'this', 'that', 'these', 'those', 'i', 'you', 'he', 'she', 'it', 'we',
            'they', 'me', 'him', 'her', 'us', 'them', 'my', 'your', 'his', 'its',
            'our', 'their', 'what', 'when', 'where', 'why', 'how'
        }
        
        # Filter and count
        keyword_counts = Counter([
            word for word in words 
            if len(word) > 3 and word not in stop_words
        ])
        
        return [word for word, count in keyword_counts.most_common(15)]
    
    async def _create_or_update_trend(self, trend_data: Dict[str, Any]):
        """Create or update trend record"""
        
        # Generate trend ID
        trend_name = trend_data['name']
        trend_id = hashlib.md5(trend_name.encode()).hexdigest()[:16]
        
        existing_trend = self.db.query(TikTokTrend).filter(
            TikTokTrend.trend_id == trend_id
        ).first()
        
        if existing_trend:
            # Update existing trend
            existing_trend.total_videos = trend_data['total_videos']
            existing_trend.total_views = trend_data['total_views']
            existing_trend.total_likes = trend_data['total_likes']
            existing_trend.total_shares = trend_data['total_shares']
            existing_trend.total_comments = trend_data['total_comments']
            existing_trend.viral_score = trend_data['viral_score']
            existing_trend.engagement_rate = trend_data['engagement_rate']
            existing_trend.trend_status = trend_data['trend_status'].value
            existing_trend.last_scraped = datetime.utcnow()
            existing_trend.updated_at = datetime.utcnow()
        else:
            # Create new trend
            new_trend = TikTokTrend(
                trend_id=trend_id,
                name=trend_name,
                normalized_name=trend_name.lower(),
                trend_type=trend_data['trend_type'].value,
                trend_status=trend_data['trend_status'].value,
                total_videos=trend_data['total_videos'],
                total_views=trend_data['total_views'],
                total_likes=trend_data['total_likes'],
                total_shares=trend_data['total_shares'],
                total_comments=trend_data['total_comments'],
                viral_score=trend_data['viral_score'],
                engagement_rate=trend_data['engagement_rate'],
                keywords=trend_data['keywords'],
                hashtags=trend_data['hashtags'],
                first_detected=trend_data['first_detected']
            )
            self.db.add(new_trend)
        
        self.db.commit()
    
    async def _update_analytics(self, processing_results: Dict[str, Any], analytics_data: Dict[str, Any]):
        """Update analytics tables"""
        
        today = datetime.utcnow().date()
        
        existing_analytics = self.db.query(TikTokAnalytics).filter(
            and_(
                func.date(TikTokAnalytics.date) == today,
                TikTokAnalytics.period_type == "daily"
            )
        ).first()
        
        if existing_analytics:
            # Update existing
            existing_analytics.total_videos_analyzed += processing_results.get('videos_processed', 0)
            existing_analytics.total_trends += processing_results.get('trends_created', 0)
            existing_analytics.total_hashtags += processing_results.get('hashtags_tracked', 0)
            existing_analytics.total_sounds += processing_results.get('sounds_tracked', 0)
            existing_analytics.updated_at = datetime.utcnow()
        else:
            # Create new
            new_analytics = TikTokAnalytics(
                date=datetime.utcnow(),
                period_type="daily",
                total_videos_analyzed=processing_results.get('videos_processed', 0),
                total_trends=processing_results.get('trends_created', 0),
                total_hashtags=processing_results.get('hashtags_tracked', 0),
                total_sounds=processing_results.get('sounds_tracked', 0)
            )
            self.db.add(new_analytics)
        
        self.db.commit()
    
    def _parse_timestamp(self, timestamp_str: str) -> Optional[datetime]:
        """Parse timestamp string to datetime"""
        
        if not timestamp_str:
            return None
        
        try:
            # Try ISO format first
            return datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
        except (ValueError, AttributeError):
            try:
                # Try timestamp
                return datetime.fromtimestamp(float(timestamp_str))
            except (ValueError, TypeError):
                return None


# Utility functions
async def process_apify_results(
    job_id: str,
    scraped_data: List[Dict[str, Any]],
    analytics_data: Dict[str, Any] = None,
    trend_analysis: Dict[str, Any] = None
) -> Dict[str, Any]:
    """Process Apify scraping results"""
    
    db = next(get_db())
    try:
        processor = TikTokDataProcessor(db)
        return await processor.process_scraping_results(
            job_id=job_id,
            scraped_data=scraped_data,
            analytics_data=analytics_data,
            trend_analysis=trend_analysis
        )
    finally:
        db.close()


async def calculate_trend_metrics(trend_id: str) -> Dict[str, Any]:
    """Calculate comprehensive metrics for a trend"""
    
    db = next(get_db())
    try:
        trend = db.query(TikTokTrend).filter(TikTokTrend.trend_id == trend_id).first()
        if not trend:
            raise ValueError(f"Trend {trend_id} not found")
        
        # Get associated videos
        videos = db.query(TikTokVideo).filter(TikTokVideo.trend_id == trend.id).all()
        
        if not videos:
            return trend.to_dict()
        
        # Calculate metrics
        total_engagement = sum(v.like_count + v.share_count + v.comment_count for v in videos)
        avg_engagement_rate = statistics.mean([v.engagement_rate for v in videos])
        
        # Calculate growth rate (simplified)
        if len(videos) > 1:
            videos_by_date = sorted(videos, key=lambda v: v.posted_at or v.created_at)
            early_videos = videos_by_date[:len(videos)//2]
            recent_videos = videos_by_date[len(videos)//2:]
            
            early_avg_views = statistics.mean([v.view_count for v in early_videos])
            recent_avg_views = statistics.mean([v.view_count for v in recent_videos])
            
            if early_avg_views > 0:
                growth_rate = ((recent_avg_views - early_avg_views) / early_avg_views) * 100
            else:
                growth_rate = 0
        else:
            growth_rate = 0
        
        # Update trend with calculated metrics
        trend.growth_rate = growth_rate
        trend.velocity = growth_rate / max((datetime.utcnow() - trend.first_detected).total_seconds() / 3600, 1)
        
        db.commit()
        
        return {
            **trend.to_dict(),
            'video_count': len(videos),
            'total_engagement': total_engagement,
            'avg_engagement_rate': avg_engagement_rate,
            'growth_metrics': {
                'growth_rate': growth_rate,
                'velocity': trend.velocity
            }
        }
        
    finally:
        db.close()