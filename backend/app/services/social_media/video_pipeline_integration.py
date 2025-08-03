"""
Video Pipeline Integration

Integrates the social media posting system with the existing video generation pipeline
to enable automated posting of generated videos across platforms.
"""

import asyncio
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple
import logging

from sqlalchemy.orm import Session
from sqlalchemy import and_

from app.models.video_project import VideoProject, VideoGenerationJob, GenerationStatusEnum
from app.models.social_media import (
    SocialMediaAccount, SocialMediaPost, PostingSchedule, 
    PlatformType, AccountStatus, PostStatus, ContentType
)
from app.models.brand import Brand
from app.models.campaign import Campaign
from app.services.social_media.social_media_manager import (
    SocialMediaManager, CrossPlatformPostingRequest, PostingStrategy, OptimizationMode
)
from app.services.social_media.base_service import PostingRequest
from app.services.analytics.trend_engine import TrendEngine
from app.core.config import settings

logger = logging.getLogger(__name__)


class VideoPipelineIntegration:
    """Integrates video generation with social media posting"""
    
    def __init__(self, db: Session):
        self.db = db
        self.social_manager = SocialMediaManager(db)
        self.trend_engine = TrendEngine()
    
    async def auto_post_completed_video(
        self,
        video_project_id: int,
        posting_config: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Automatically post a completed video to configured social media platforms"""
        
        # Get video project
        video_project = self.db.query(VideoProject).get(video_project_id)
        if not video_project:
            raise ValueError(f"Video project {video_project_id} not found")
        
        # Check if video is completed
        if video_project.status != GenerationStatusEnum.COMPLETED:
            raise ValueError(f"Video project {video_project_id} is not completed")
        
        # Get brand and associated social media accounts
        brand = self.db.query(Brand).get(video_project.brand_id)
        if not brand:
            raise ValueError(f"Brand not found for video project {video_project_id}")
        
        # Get active social media accounts for the brand
        accounts = self.db.query(SocialMediaAccount).filter(
            and_(
                SocialMediaAccount.brand_id == brand.id,
                SocialMediaAccount.status == AccountStatus.ACTIVE
            )
        ).all()
        
        if not accounts:
            logger.warning(f"No active social media accounts found for brand {brand.id}")
            return {"error": "No active social media accounts", "posted": False}
        
        # Determine platforms to post to
        platforms_to_post = self._determine_posting_platforms(accounts, posting_config)
        
        if not platforms_to_post:
            logger.info(f"No platforms configured for posting for brand {brand.id}")
            return {"message": "No platforms configured for posting", "posted": False}
        
        # Generate optimized content for posting
        posting_content = await self._generate_posting_content(video_project, posting_config)
        
        # Create cross-platform posting request
        posting_request = CrossPlatformPostingRequest(
            video_project_id=video_project.id,
            campaign_id=video_project.campaign_id,
            platforms=platforms_to_post,
            base_content=posting_content,
            posting_strategy=PostingStrategy(posting_config.get("strategy", "optimized")),
            optimization_mode=OptimizationMode(posting_config.get("optimization", "full_optimization"))
        )
        
        # Execute posting
        try:
            result = await self.social_manager.post_to_multiple_platforms(
                brand_id=brand.id,
                request=posting_request
            )
            
            logger.info(f"Auto-posted video {video_project_id} to platforms: {result}")
            
            return {
                "video_project_id": video_project_id,
                "posted": True,
                "platforms": platforms_to_post,
                "results": result,
                "timestamp": datetime.utcnow().isoformat()
            }
        
        except Exception as e:
            logger.error(f"Failed to auto-post video {video_project_id}: {e}")
            return {
                "video_project_id": video_project_id,
                "posted": False,
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat()
            }
    
    def _determine_posting_platforms(
        self,
        accounts: List[SocialMediaAccount],
        posting_config: Optional[Dict[str, Any]]
    ) -> List[PlatformType]:
        """Determine which platforms to post to based on configuration and availability"""
        
        available_platforms = [account.platform for account in accounts]
        
        if posting_config and "platforms" in posting_config:
            # Use explicitly configured platforms
            configured_platforms = [PlatformType(p) for p in posting_config["platforms"]]
            return [p for p in configured_platforms if p in available_platforms]
        
        # Use all available platforms by default
        return available_platforms
    
    async def _generate_posting_content(
        self,
        video_project: VideoProject,
        posting_config: Optional[Dict[str, Any]]
    ) -> PostingRequest:
        """Generate optimized posting content for the video"""
        
        # Get video URL (assuming it's stored in video_project.output_url)
        video_url = getattr(video_project, 'output_url', None) or getattr(video_project, 'final_video_url', '')
        
        if not video_url:
            # Try to get from video assets
            video_assets = [asset for asset in video_project.assets if asset.asset_type == "final_video"]
            if video_assets:
                video_url = video_assets[0].file_path
        
        # Generate caption
        caption = await self._generate_caption(video_project, posting_config)
        
        # Generate hashtags
        hashtags = await self._generate_hashtags(video_project, posting_config)
        
        # Determine content type
        content_type = ContentType.VIDEO
        if posting_config and posting_config.get("content_type"):
            content_type = ContentType(posting_config["content_type"])
        
        return PostingRequest(
            content_type=content_type,
            media_urls=[video_url] if video_url else [],
            caption=caption,
            hashtags=hashtags,
            privacy_settings=posting_config.get("privacy_settings") if posting_config else None,
            platform_settings=posting_config.get("platform_settings") if posting_config else None
        )
    
    async def _generate_caption(
        self,
        video_project: VideoProject,
        posting_config: Optional[Dict[str, Any]]
    ) -> str:
        """Generate an optimized caption for the video"""
        
        if posting_config and posting_config.get("caption"):
            return posting_config["caption"]
        
        # Use video project description or script as base
        base_caption = ""
        
        if hasattr(video_project, 'description') and video_project.description:
            base_caption = video_project.description
        elif hasattr(video_project, 'script') and video_project.script:
            # Use first part of script
            script_lines = video_project.script.split('\n')
            base_caption = script_lines[0] if script_lines else ""
        
        # Optimize caption for social media
        if base_caption:
            # Limit length for platforms
            if len(base_caption) > 150:
                base_caption = base_caption[:147] + "..."
            
            # Add engagement hooks
            engagement_hooks = [
                "🔥 What do you think?",
                "💭 Drop a comment below!",
                "✨ Follow for more!",
                "🚀 Save this for later!"
            ]
            
            # Add a random engagement hook
            import random
            hook = random.choice(engagement_hooks)
            base_caption += f" {hook}"
        
        return base_caption or "Check out this amazing video! 🎥✨"
    
    async def _generate_hashtags(
        self,
        video_project: VideoProject,
        posting_config: Optional[Dict[str, Any]]
    ) -> List[str]:
        """Generate optimized hashtags for the video"""
        
        if posting_config and posting_config.get("hashtags"):
            return posting_config["hashtags"]
        
        hashtags = []
        
        # Get trending hashtags from trend engine
        try:
            trending_data = await self.trend_engine.get_trending_hashtags(limit=10)
            if trending_data and "hashtags" in trending_data:
                hashtags.extend(trending_data["hashtags"][:5])  # Top 5 trending
        except Exception as e:
            logger.warning(f"Failed to get trending hashtags: {e}")
        
        # Add category-based hashtags
        category_hashtags = {
            "product_demo": ["#productdemo", "#unboxing", "#review"],
            "educational": ["#learnwithme", "#educational", "#tutorial"],
            "entertainment": ["#fyp", "#viral", "#trending"],
            "lifestyle": ["#lifestyle", "#daily", "#motivation"],
            "business": ["#business", "#entrepreneur", "#success"]
        }
        
        # Try to determine category from video project metadata
        category = "entertainment"  # default
        if hasattr(video_project, 'category') and video_project.category:
            category = video_project.category.lower()
        elif hasattr(video_project, 'video_type') and video_project.video_type:
            category = video_project.video_type.lower()
        
        if category in category_hashtags:
            hashtags.extend(category_hashtags[category])
        
        # Add brand-specific hashtags if available
        brand = self.db.query(Brand).get(video_project.brand_id)
        if brand:
            brand_hashtag = f"#{brand.name.lower().replace(' ', '').replace('-', '')}"
            hashtags.append(brand_hashtag)
        
        # Add general engagement hashtags
        general_hashtags = ["#viral", "#fyp", "#trending", "#awesome", "#amazing"]
        hashtags.extend(general_hashtags[:3])
        
        # Remove duplicates and limit to reasonable number
        unique_hashtags = list(set(hashtags))
        return unique_hashtags[:15]  # Limit to 15 hashtags
    
    async def schedule_auto_posting(
        self,
        video_project_id: int,
        delay_hours: Optional[int] = None
    ) -> Dict[str, Any]:
        """Schedule automatic posting for when a video generation is completed"""
        
        video_project = self.db.query(VideoProject).get(video_project_id)
        if not video_project:
            raise ValueError(f"Video project {video_project_id} not found")
        
        # Calculate posting time
        if delay_hours:
            posting_time = datetime.utcnow() + timedelta(hours=delay_hours)
        else:
            # Use optimal posting times for the brand's accounts
            optimal_time = await self._get_optimal_posting_time(video_project.brand_id)
            posting_time = optimal_time or (datetime.utcnow() + timedelta(hours=1))
        
        # Store scheduling information in video project metadata
        if not hasattr(video_project, 'metadata'):
            video_project.metadata = {}
        
        video_project.metadata = video_project.metadata or {}
        video_project.metadata["auto_post_scheduled"] = True
        video_project.metadata["auto_post_time"] = posting_time.isoformat()
        
        self.db.commit()
        
        return {
            "video_project_id": video_project_id,
            "scheduled": True,
            "posting_time": posting_time.isoformat(),
            "message": "Video will be automatically posted when generation is complete"
        }
    
    async def _get_optimal_posting_time(self, brand_id: int) -> Optional[datetime]:
        """Get optimal posting time based on brand's posting schedules"""
        
        # Get posting schedules for the brand
        schedules = self.db.query(PostingSchedule).filter(
            and_(
                PostingSchedule.brand_id == brand_id,
                PostingSchedule.is_active == True
            )
        ).all()
        
        if not schedules:
            return None
        
        # Find next optimal posting time
        current_hour = datetime.utcnow().hour
        
        for schedule in schedules:
            if schedule.posting_times:
                for time_str in schedule.posting_times:
                    hour = int(time_str.split(":")[0])
                    if hour > current_hour:
                        return datetime.utcnow().replace(
                            hour=hour, minute=0, second=0, microsecond=0
                        )
        
        # If no time today, use first time tomorrow
        if schedules[0].posting_times:
            hour = int(schedules[0].posting_times[0].split(":")[0])
            return (datetime.utcnow() + timedelta(days=1)).replace(
                hour=hour, minute=0, second=0, microsecond=0
            )
        
        return None
    
    async def process_completed_videos(self) -> Dict[str, Any]:
        """Process all completed videos that are scheduled for auto-posting"""
        
        # Find completed videos that are scheduled for auto-posting
        completed_videos = self.db.query(VideoProject).filter(
            VideoProject.status == GenerationStatusEnum.COMPLETED
        ).all()
        
        processed_count = 0
        results = []
        
        for video in completed_videos:
            try:
                # Check if auto-posting is enabled and due
                metadata = getattr(video, 'metadata', {}) or {}
                
                if not metadata.get("auto_post_scheduled"):
                    continue
                
                posting_time_str = metadata.get("auto_post_time")
                if not posting_time_str:
                    continue
                
                posting_time = datetime.fromisoformat(posting_time_str)
                if posting_time > datetime.utcnow():
                    continue  # Not yet time to post
                
                # Check if already posted
                if metadata.get("auto_posted"):
                    continue
                
                # Post the video
                result = await self.auto_post_completed_video(video.id)
                
                if result.get("posted"):
                    # Mark as posted
                    metadata["auto_posted"] = True
                    metadata["auto_posted_at"] = datetime.utcnow().isoformat()
                    video.metadata = metadata
                    processed_count += 1
                
                results.append(result)
                
            except Exception as e:
                logger.error(f"Failed to process video {video.id} for auto-posting: {e}")
                results.append({
                    "video_project_id": video.id,
                    "posted": False,
                    "error": str(e)
                })
        
        self.db.commit()
        
        return {
            "processed_count": processed_count,
            "total_checked": len(completed_videos),
            "results": results,
            "timestamp": datetime.utcnow().isoformat()
        }
    
    async def get_posting_performance_insights(
        self,
        brand_id: int,
        days: int = 30
    ) -> Dict[str, Any]:
        """Get insights on posting performance to optimize future automated posts"""
        
        # Get posts from the last N days
        cutoff_date = datetime.utcnow() - timedelta(days=days)
        
        posts = self.db.query(SocialMediaPost).join(SocialMediaAccount).filter(
            and_(
                SocialMediaAccount.brand_id == brand_id,
                SocialMediaPost.published_at >= cutoff_date,
                SocialMediaPost.status == PostStatus.PUBLISHED
            )
        ).all()
        
        if not posts:
            return {"message": "No posts found for analysis", "insights": {}}
        
        # Analyze performance by platform
        platform_performance = {}
        hour_performance = {}
        hashtag_performance = {}
        
        for post in posts:
            platform = post.account.platform.value
            
            # Platform performance
            if platform not in platform_performance:
                platform_performance[platform] = {
                    "posts": 0, "total_engagement": 0, "total_views": 0
                }
            
            platform_performance[platform]["posts"] += 1
            platform_performance[platform]["total_engagement"] += (
                post.like_count + post.comment_count + post.share_count
            )
            platform_performance[platform]["total_views"] += post.view_count
            
            # Hour performance
            if post.published_at:
                hour = post.published_at.hour
                if hour not in hour_performance:
                    hour_performance[hour] = {"posts": 0, "total_engagement": 0}
                
                hour_performance[hour]["posts"] += 1
                hour_performance[hour]["total_engagement"] += (
                    post.like_count + post.comment_count + post.share_count
                )
            
            # Hashtag performance
            if post.hashtags:
                for hashtag in post.hashtags:
                    if hashtag not in hashtag_performance:
                        hashtag_performance[hashtag] = {"posts": 0, "total_engagement": 0}
                    
                    hashtag_performance[hashtag]["posts"] += 1
                    hashtag_performance[hashtag]["total_engagement"] += (
                        post.like_count + post.comment_count + post.share_count
                    )
        
        # Calculate averages and rankings
        for platform_data in platform_performance.values():
            if platform_data["posts"] > 0:
                platform_data["avg_engagement"] = platform_data["total_engagement"] / platform_data["posts"]
                platform_data["avg_views"] = platform_data["total_views"] / platform_data["posts"]
        
        for hour_data in hour_performance.values():
            if hour_data["posts"] > 0:
                hour_data["avg_engagement"] = hour_data["total_engagement"] / hour_data["posts"]
        
        for hashtag_data in hashtag_performance.values():
            if hashtag_data["posts"] > 0:
                hashtag_data["avg_engagement"] = hashtag_data["total_engagement"] / hashtag_data["posts"]
        
        # Get top performers
        top_platforms = sorted(
            platform_performance.items(),
            key=lambda x: x[1]["avg_engagement"],
            reverse=True
        )
        
        top_hours = sorted(
            hour_performance.items(),
            key=lambda x: x[1]["avg_engagement"],
            reverse=True
        )[:5]
        
        top_hashtags = sorted(
            hashtag_performance.items(),
            key=lambda x: x[1]["avg_engagement"],
            reverse=True
        )[:10]
        
        return {
            "analysis_period_days": days,
            "total_posts": len(posts),
            "platform_performance": platform_performance,
            "top_platforms": top_platforms,
            "best_posting_hours": top_hours,
            "top_performing_hashtags": top_hashtags,
            "recommendations": self._generate_recommendations(
                platform_performance, top_hours, top_hashtags
            )
        }
    
    def _generate_recommendations(
        self,
        platform_performance: Dict,
        top_hours: List,
        top_hashtags: List
    ) -> List[str]:
        """Generate actionable recommendations based on performance analysis"""
        
        recommendations = []
        
        # Platform recommendations
        if platform_performance:
            best_platform = max(platform_performance.items(), key=lambda x: x[1]["avg_engagement"])
            recommendations.append(
                f"Focus more content on {best_platform[0].title()} - it has the highest average engagement"
            )
        
        # Timing recommendations
        if top_hours:
            best_hours = [str(hour) for hour, _ in top_hours[:3]]
            recommendations.append(
                f"Post during these high-engagement hours: {', '.join(best_hours)}:00"
            )
        
        # Hashtag recommendations
        if top_hashtags:
            best_hashtags = [hashtag for hashtag, _ in top_hashtags[:5]]
            recommendations.append(
                f"Use these high-performing hashtags: {', '.join(best_hashtags)}"
            )
        
        return recommendations
    
    async def close(self):
        """Clean up resources"""
        await self.social_manager.close()