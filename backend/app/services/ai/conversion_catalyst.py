"""
Conversion Catalyst Service

Optimizes content for maximum conversion through caption optimization,
hashtag research, CTA generation, and A/B testing recommendations.
"""

import asyncio
import json
import re
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Set, Tuple
import logging
from collections import Counter

from app.core.config import settings
from app.services.ai.providers import get_text_service
from app.services.ai.vector_db import get_vector_service
from app.services.ai.prompts import get_prompt_template
from app.services.ai.viral_content import Platform

logger = logging.getLogger(__name__)


class ConversionGoal(str, Enum):
    """Conversion goals for content optimization"""
    ENGAGEMENT = "engagement"
    WEBSITE_TRAFFIC = "website_traffic"
    LEAD_GENERATION = "lead_generation"
    SALES = "sales"
    BRAND_AWARENESS = "brand_awareness"
    FOLLOWERS = "followers"
    EMAIL_SIGNUP = "email_signup"
    APP_DOWNLOAD = "app_download"


class CTAType(str, Enum):
    """Types of call-to-action"""
    FOLLOW = "follow"
    LIKE = "like"
    SHARE = "share"
    COMMENT = "comment"
    VISIT_LINK = "visit_link"
    DOWNLOAD = "download"
    SUBSCRIBE = "subscribe"
    SIGN_UP = "sign_up"
    BUY_NOW = "buy_now"
    LEARN_MORE = "learn_more"
    SAVE_POST = "save_post"


@dataclass
class HashtagAnalysis:
    """Analysis of hashtag performance and relevance"""
    hashtag: str
    relevance_score: float
    competition_level: str  # low, medium, high
    estimated_reach: int
    engagement_rate: float
    trending_status: str  # trending, stable, declining
    related_hashtags: List[str]
    best_time_to_use: List[str]  # days of week or times
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "hashtag": self.hashtag,
            "relevance_score": self.relevance_score,
            "competition_level": self.competition_level,
            "estimated_reach": self.estimated_reach,
            "engagement_rate": self.engagement_rate,
            "trending_status": self.trending_status,
            "related_hashtags": self.related_hashtags,
            "best_time_to_use": self.best_time_to_use
        }


@dataclass
class OptimizedCaption:
    """Optimized caption with performance predictions"""
    original_caption: str
    optimized_caption: str
    hashtags: List[str]
    cta: str
    estimated_engagement_lift: float
    optimization_changes: List[str]
    a_b_test_variants: List[str]
    character_count: int
    readability_score: float
    sentiment: str
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "original_caption": self.original_caption,
            "optimized_caption": self.optimized_caption,
            "hashtags": self.hashtags,
            "cta": self.cta,
            "estimated_engagement_lift": self.estimated_engagement_lift,
            "optimization_changes": self.optimization_changes,
            "a_b_test_variants": self.a_b_test_variants,
            "character_count": self.character_count,
            "readability_score": self.readability_score,
            "sentiment": self.sentiment
        }


@dataclass
class ConversionOptimization:
    """Complete conversion optimization package"""
    campaign_id: str
    conversion_goal: ConversionGoal
    platform: Platform
    target_audience: str
    optimized_caption: OptimizedCaption
    recommended_hashtags: List[HashtagAnalysis]
    cta_recommendations: List[Dict[str, Any]]
    posting_schedule: Dict[str, Any]
    a_b_test_plan: Dict[str, Any]
    performance_predictions: Dict[str, float]
    created_at: float = field(default_factory=time.time)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "campaign_id": self.campaign_id,
            "conversion_goal": self.conversion_goal,
            "platform": self.platform,
            "target_audience": self.target_audience,
            "optimized_caption": self.optimized_caption.to_dict(),
            "recommended_hashtags": [h.to_dict() for h in self.recommended_hashtags],
            "cta_recommendations": self.cta_recommendations,
            "posting_schedule": self.posting_schedule,
            "a_b_test_plan": self.a_b_test_plan,
            "performance_predictions": self.performance_predictions,
            "created_at": self.created_at
        }


class HashtagResearcher:
    """AI-powered hashtag research and analysis"""
    
    def __init__(self):
        self.text_service = None
        self.vector_service = None
        self.hashtag_database = {}  # In production, use proper database
    
    async def _get_services(self):
        """Initialize AI services"""
        if self.text_service is None:
            self.text_service = await get_text_service()
        if self.vector_service is None:
            self.vector_service = await get_vector_service()
    
    async def research_hashtags(
        self,
        content_theme: str,
        industry: str,
        platform: Platform,
        target_audience: str,
        limit: int = 30
    ) -> List[HashtagAnalysis]:
        """Research and analyze hashtags for content"""
        
        await self._get_services()
        
        logger.info(f"Researching hashtags for: {content_theme} in {industry}")
        
        # Generate base hashtags using AI
        base_hashtags = await self._generate_base_hashtags(
            content_theme, industry, platform, target_audience
        )
        
        # Expand with related hashtags
        expanded_hashtags = await self._expand_hashtag_list(base_hashtags, platform)
        
        # Analyze each hashtag
        analyzed_hashtags = []
        for hashtag in expanded_hashtags[:limit]:
            analysis = await self._analyze_hashtag(hashtag, platform, industry)
            analyzed_hashtags.append(analysis)
        
        # Sort by relevance and performance
        analyzed_hashtags.sort(key=lambda h: h.relevance_score * h.engagement_rate, reverse=True)
        
        return analyzed_hashtags
    
    async def _generate_base_hashtags(
        self,
        content_theme: str,
        industry: str,
        platform: Platform,
        target_audience: str
    ) -> List[str]:
        """Generate base hashtags using AI"""
        
        prompt = f"""Generate 15 relevant hashtags for social media content about "{content_theme}" in the {industry} industry.

Target audience: {target_audience}
Platform: {platform}

Consider:
- Industry-specific hashtags
- Audience interests
- Trending topics
- Mix of broad and niche hashtags
- Platform best practices

Format: Return only hashtags, one per line, without the # symbol."""
        
        response = await self.text_service.generate(
            prompt,
            max_tokens=300,
            temperature=0.6
        )
        
        if not response.success:
            logger.error(f"Hashtag generation failed: {response.error}")
            return self._get_fallback_hashtags(content_theme, industry)
        
        # Parse hashtags from response
        hashtags = []
        for line in response.content.strip().split('\n'):
            hashtag = line.strip().replace('#', '').replace('-', '').replace(' ', '')
            if hashtag and len(hashtag) > 2:
                hashtags.append(hashtag.lower())
        
        return hashtags[:15]
    
    def _get_fallback_hashtags(self, content_theme: str, industry: str) -> List[str]:
        """Fallback hashtags when AI generation fails"""
        theme_words = content_theme.lower().split()
        industry_words = industry.lower().split()
        
        base_hashtags = theme_words + industry_words + [
            "business", "entrepreneur", "success", "tips", "advice",
            "motivation", "productivity", "growth", "marketing", "strategy"
        ]
        
        return list(set(base_hashtags))[:15]
    
    async def _expand_hashtag_list(self, base_hashtags: List[str], platform: Platform) -> List[str]:
        """Expand hashtag list with related hashtags"""
        
        expanded = set(base_hashtags)
        
        # Add platform-specific hashtags
        platform_hashtags = {
            Platform.TIKTOK: ["fyp", "viral", "trending", "foryou", "tiktok"],
            Platform.INSTAGRAM: ["instagood", "photooftheday", "instadaily", "follow", "like4like"],
            Platform.YOUTUBE_SHORTS: ["shorts", "youtube", "youtubeshorts", "subscribe", "viral"],
            Platform.LINKEDIN: ["linkedin", "professional", "networking", "career", "business"],
            Platform.TWITTER: ["twitter", "tweet", "follow", "retweet", "trending"]
        }
        
        if platform in platform_hashtags:
            expanded.update(platform_hashtags[platform])
        
        # Add related hashtags based on semantic similarity
        for hashtag in base_hashtags:
            related = await self._find_related_hashtags(hashtag)
            expanded.update(related[:3])  # Add top 3 related
        
        return list(expanded)
    
    async def _find_related_hashtags(self, hashtag: str) -> List[str]:
        """Find hashtags related to given hashtag using vector similarity"""
        
        try:
            # Search for similar hashtags in vector database
            similar_content = await self.vector_service.search_similar(
                f"#{hashtag} content social media",
                namespace="hashtag_research",
                top_k=10,
                similarity_threshold=0.7
            )
            
            related_hashtags = []
            for content in similar_content:
                # Extract hashtags from similar content
                hashtags_in_content = re.findall(r'#(\w+)', content.content)
                related_hashtags.extend(hashtags_in_content)
            
            # Return unique hashtags, excluding the original
            unique_related = list(set(related_hashtags))
            return [h for h in unique_related if h.lower() != hashtag.lower()][:5]
            
        except Exception as e:
            logger.warning(f"Failed to find related hashtags for {hashtag}: {e}")
            return []
    
    async def _analyze_hashtag(
        self,
        hashtag: str,
        platform: Platform,
        industry: str
    ) -> HashtagAnalysis:
        """Analyze individual hashtag performance"""
        
        # In production, this would query real hashtag analytics APIs
        # For now, provide intelligent mock analysis
        
        # Calculate relevance based on hashtag characteristics
        relevance_score = self._calculate_relevance_score(hashtag, industry)
        
        # Estimate reach based on hashtag popularity patterns
        estimated_reach = self._estimate_hashtag_reach(hashtag, platform)
        
        # Determine competition level
        competition_level = self._determine_competition_level(hashtag)
        
        # Mock engagement rate based on patterns
        engagement_rate = self._estimate_engagement_rate(hashtag, platform)
        
        # Determine trending status
        trending_status = self._determine_trending_status(hashtag)
        
        # Generate related hashtags
        related_hashtags = await self._find_related_hashtags(hashtag)
        
        # Optimal posting times (mock data)
        best_time_to_use = self._get_optimal_posting_times(platform)
        
        return HashtagAnalysis(
            hashtag=f"#{hashtag}",
            relevance_score=relevance_score,
            competition_level=competition_level,
            estimated_reach=estimated_reach,
            engagement_rate=engagement_rate,
            trending_status=trending_status,
            related_hashtags=[f"#{h}" for h in related_hashtags[:5]],
            best_time_to_use=best_time_to_use
        )
    
    def _calculate_relevance_score(self, hashtag: str, industry: str) -> float:
        """Calculate hashtag relevance score"""
        score = 0.5  # Base score
        
        # Boost for industry-specific hashtags
        if industry.lower() in hashtag.lower():
            score += 0.3
        
        # Boost for specific vs generic hashtags
        if len(hashtag) > 8:  # More specific hashtags
            score += 0.2
        elif len(hashtag) < 5:  # Too generic
            score -= 0.1
        
        # Penalty for overly long hashtags
        if len(hashtag) > 20:
            score -= 0.2
        
        return min(max(score, 0.0), 1.0)
    
    def _estimate_hashtag_reach(self, hashtag: str, platform: Platform) -> int:
        """Estimate hashtag reach"""
        # Mock estimation based on hashtag characteristics
        base_reach = {
            Platform.TIKTOK: 100000,
            Platform.INSTAGRAM: 50000,
            Platform.YOUTUBE_SHORTS: 30000,
            Platform.LINKEDIN: 10000,
            Platform.TWITTER: 20000
        }
        
        reach = base_reach.get(platform, 50000)
        
        # Adjust based on hashtag specificity
        if len(hashtag) < 5:  # Very broad hashtag
            reach *= 5
        elif len(hashtag) > 12:  # Very specific hashtag
            reach *= 0.2
        
        return int(reach)
    
    def _determine_competition_level(self, hashtag: str) -> str:
        """Determine hashtag competition level"""
        if len(hashtag) < 5:
            return "high"
        elif len(hashtag) < 10:
            return "medium"
        else:
            return "low"
    
    def _estimate_engagement_rate(self, hashtag: str, platform: Platform) -> float:
        """Estimate engagement rate for hashtag"""
        base_rates = {
            Platform.TIKTOK: 0.08,
            Platform.INSTAGRAM: 0.04,
            Platform.YOUTUBE_SHORTS: 0.06,
            Platform.LINKEDIN: 0.03,
            Platform.TWITTER: 0.02
        }
        
        base_rate = base_rates.get(platform, 0.04)
        
        # Adjust based on competition
        competition = self._determine_competition_level(hashtag)
        if competition == "low":
            base_rate *= 1.5
        elif competition == "high":
            base_rate *= 0.7
        
        return round(base_rate, 3)
    
    def _determine_trending_status(self, hashtag: str) -> str:
        """Determine if hashtag is trending"""
        # Mock logic - in production, check against trending APIs
        trending_keywords = [
            "ai", "2024", "trend", "viral", "new", "latest", "hot", "trending"
        ]
        
        if any(keyword in hashtag.lower() for keyword in trending_keywords):
            return "trending"
        elif len(hashtag) < 6:
            return "stable"
        else:
            return "stable"
    
    def _get_optimal_posting_times(self, platform: Platform) -> List[str]:
        """Get optimal posting times for platform"""
        optimal_times = {
            Platform.TIKTOK: ["6-10am", "7-9pm", "weekends"],
            Platform.INSTAGRAM: ["11am-1pm", "7-9pm", "weekdays"],
            Platform.YOUTUBE_SHORTS: ["2-4pm", "8-10pm", "weekends"],
            Platform.LINKEDIN: ["8-10am", "12-2pm", "weekdays"],
            Platform.TWITTER: ["9am-10am", "7-9pm", "weekdays"]
        }
        
        return optimal_times.get(platform, ["9am-12pm", "6-9pm", "weekdays"])


class CaptionOptimizer:
    """AI-powered caption optimization"""
    
    def __init__(self):
        self.text_service = None
    
    async def _get_text_service(self):
        """Get text service instance"""
        if self.text_service is None:
            self.text_service = await get_text_service()
    
    async def optimize_caption(
        self,
        original_caption: str,
        platform: Platform,
        brand_name: str,
        target_audience: str,
        conversion_goal: ConversionGoal,
        brand_voice: Dict[str, Any],
        content_type: str = "video"
    ) -> OptimizedCaption:
        """Optimize caption for maximum engagement and conversion"""
        
        await self._get_text_service()
        
        logger.info(f"Optimizing caption for {brand_name} on {platform}")
        
        # Get caption optimization prompt
        optimization_prompt = await get_prompt_template("caption_optimization")
        
        # Format brand voice
        brand_voice_text = self._format_brand_voice(brand_voice)
        
        # Generate optimized caption
        response = await self.text_service.generate(
            optimization_prompt.format(
                original_caption=original_caption,
                platform=platform,
                brand_name=brand_name,
                target_audience=target_audience,
                content_type=content_type,
                brand_voice=brand_voice_text
            ),
            max_tokens=600,
            temperature=0.6
        )
        
        if not response.success:
            logger.error(f"Caption optimization failed: {response.error}")
            return self._create_fallback_optimization(original_caption, platform)
        
        # Parse optimization response
        optimization_data = self._parse_optimization_response(response.content)
        
        # Generate A/B test variants
        ab_variants = await self._generate_ab_test_variants(
            optimization_data["optimized_caption"], platform, conversion_goal
        )
        
        # Calculate metrics
        character_count = len(optimization_data["optimized_caption"])
        readability_score = self._calculate_readability_score(optimization_data["optimized_caption"])
        sentiment = self._analyze_sentiment(optimization_data["optimized_caption"])
        
        return OptimizedCaption(
            original_caption=original_caption,
            optimized_caption=optimization_data["optimized_caption"],
            hashtags=optimization_data.get("hashtags", []),
            cta=optimization_data.get("cta", ""),
            estimated_engagement_lift=optimization_data.get("estimated_lift", 0.15),
            optimization_changes=optimization_data.get("changes", []),
            a_b_test_variants=ab_variants,
            character_count=character_count,
            readability_score=readability_score,
            sentiment=sentiment
        )
    
    def _format_brand_voice(self, brand_voice: Dict[str, Any]) -> str:
        """Format brand voice for prompt"""
        if not brand_voice:
            return "Professional and friendly"
        
        parts = []
        if "tone" in brand_voice:
            parts.append(f"Tone: {brand_voice['tone']}")
        if "dos" in brand_voice:
            parts.append(f"Do: {', '.join(brand_voice['dos'][:3])}")
        if "donts" in brand_voice:
            parts.append(f"Don't: {', '.join(brand_voice['donts'][:3])}")
        
        return "; ".join(parts) if parts else "Professional and friendly"
    
    def _parse_optimization_response(self, response: str) -> Dict[str, Any]:
        """Parse AI optimization response"""
        data = {
            "optimized_caption": "",
            "hashtags": [],
            "cta": "",
            "changes": [],
            "estimated_lift": 0.15
        }
        
        lines = response.strip().split('\n')
        current_section = None
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
            
            if "optimized caption:" in line.lower():
                current_section = "caption"
                content = line.split(':', 1)[1].strip()
                if content:
                    data["optimized_caption"] = content
            elif "hashtag" in line.lower() and ":" in line:
                current_section = "hashtags"
                hashtags_text = line.split(':', 1)[1].strip()
                data["hashtags"] = [h.strip() for h in hashtags_text.split() if h.startswith('#')]
            elif "changes made:" in line.lower() or "improvements:" in line.lower():
                current_section = "changes"
            elif current_section == "caption" and not line.startswith(('Hashtag', 'Changes', 'CTA')):
                data["optimized_caption"] += " " + line
            elif current_section == "changes" and line.startswith('-'):
                data["changes"].append(line[1:].strip())
        
        # Clean up caption
        data["optimized_caption"] = data["optimized_caption"].strip()
        
        # If no optimized caption found, use a basic optimization
        if not data["optimized_caption"]:
            data["optimized_caption"] = response.strip()
        
        return data
    
    async def _generate_ab_test_variants(
        self,
        optimized_caption: str,
        platform: Platform,
        conversion_goal: ConversionGoal
    ) -> List[str]:
        """Generate A/B test variants of the caption"""
        
        variants = []
        
        # Variant 1: More emotional
        emotional_words = {
            "great": "amazing",
            "good": "incredible",
            "nice": "fantastic",
            "helpful": "game-changing",
            "useful": "powerful"
        }
        
        emotional_variant = optimized_caption
        for old, new in emotional_words.items():
            emotional_variant = emotional_variant.replace(old, new)
        
        if emotional_variant != optimized_caption:
            variants.append(emotional_variant)
        
        # Variant 2: More direct/urgent
        if conversion_goal in [ConversionGoal.SALES, ConversionGoal.LEAD_GENERATION]:
            urgent_variant = optimized_caption
            if not any(word in urgent_variant.lower() for word in ["now", "today", "limited", "urgent"]):
                urgent_variant = urgent_variant + " Don't wait - act now!"
                variants.append(urgent_variant)
        
        # Variant 3: Question format
        if not optimized_caption.endswith('?'):
            question_variant = "Want to know the secret? " + optimized_caption
            variants.append(question_variant)
        
        return variants[:3]  # Return max 3 variants
    
    def _calculate_readability_score(self, text: str) -> float:
        """Calculate readability score (simplified)"""
        # Simplified readability based on sentence length and complexity
        sentences = text.split('.')
        avg_sentence_length = sum(len(s.split()) for s in sentences) / max(len(sentences), 1)
        
        # Score from 0-1, where 1 is most readable
        if avg_sentence_length <= 10:
            return 0.9
        elif avg_sentence_length <= 15:
            return 0.7
        elif avg_sentence_length <= 20:
            return 0.5
        else:
            return 0.3
    
    def _analyze_sentiment(self, text: str) -> str:
        """Analyze text sentiment (simplified)"""
        positive_words = [
            "amazing", "great", "awesome", "fantastic", "incredible", "love",
            "excited", "happy", "perfect", "excellent", "wonderful"
        ]
        
        negative_words = [
            "bad", "terrible", "awful", "hate", "disappointed", "frustrated",
            "angry", "sad", "annoying", "worst", "horrible"
        ]
        
        text_lower = text.lower()
        
        positive_count = sum(1 for word in positive_words if word in text_lower)
        negative_count = sum(1 for word in negative_words if word in text_lower)
        
        if positive_count > negative_count:
            return "positive"
        elif negative_count > positive_count:
            return "negative"
        else:
            return "neutral"
    
    def _create_fallback_optimization(self, original_caption: str, platform: Platform) -> OptimizedCaption:
        """Create fallback optimization when AI fails"""
        # Basic optimizations
        optimized = original_caption
        
        # Add emoji if missing
        if not any(char in optimized for char in ['😀', '🎉', '💪', '🔥', '✨']):
            optimized += " ✨"
        
        # Add platform-specific CTA
        cta_map = {
            Platform.TIKTOK: "Follow for more! 🔥",
            Platform.INSTAGRAM: "Double tap if you agree! ❤️",
            Platform.YOUTUBE_SHORTS: "Subscribe for more tips! 👆",
            Platform.LINKEDIN: "What's your experience? Comment below! 💬",
            Platform.TWITTER: "Retweet if helpful! 🔄"
        }
        
        cta = cta_map.get(platform, "Engage with this post!")
        
        return OptimizedCaption(
            original_caption=original_caption,
            optimized_caption=optimized,
            hashtags=["#tips", "#advice", "#growth"],
            cta=cta,
            estimated_engagement_lift=0.10,
            optimization_changes=["Added emoji", "Added CTA"],
            a_b_test_variants=[original_caption],
            character_count=len(optimized),
            readability_score=0.7,
            sentiment="positive"
        )


class CTAGenerator:
    """Generates optimized call-to-action elements"""
    
    def __init__(self):
        self.text_service = None
    
    async def _get_text_service(self):
        """Get text service instance"""
        if self.text_service is None:
            self.text_service = await get_text_service()
    
    async def generate_ctas(
        self,
        conversion_goal: ConversionGoal,
        platform: Platform,
        brand_name: str,
        content_theme: str,
        target_audience: str
    ) -> List[Dict[str, Any]]:
        """Generate optimized CTAs for specific goals"""
        
        await self._get_text_service()
        
        # Get CTA generation prompt
        cta_prompt = await get_prompt_template("cta_generation")
        
        # Generate CTAs with AI
        response = await self.text_service.generate(
            cta_prompt.format(
                conversion_goal=conversion_goal,
                platform=platform,
                brand_name=brand_name,
                content_theme=content_theme,
                target_audience=target_audience
            ),
            max_tokens=400,
            temperature=0.7
        )
        
        if response.success:
            ctas = self._parse_cta_response(response.content, conversion_goal, platform)
        else:
            ctas = self._generate_fallback_ctas(conversion_goal, platform)
        
        # Add performance predictions
        for cta in ctas:
            cta["predicted_ctr"] = self._predict_ctr(cta, platform, conversion_goal)
            cta["optimization_score"] = self._calculate_optimization_score(cta)
        
        # Sort by optimization score
        ctas.sort(key=lambda x: x["optimization_score"], reverse=True)
        
        return ctas
    
    def _parse_cta_response(self, response: str, goal: ConversionGoal, platform: Platform) -> List[Dict[str, Any]]:
        """Parse AI CTA response"""
        ctas = []
        lines = response.strip().split('\n')
        
        for line in lines:
            line = line.strip()
            if not line or line.startswith('#'):
                continue
            
            # Remove numbering
            cta_text = re.sub(r'^\d+\.?\s*', '', line)
            
            if len(cta_text) > 5:  # Valid CTA
                ctas.append({
                    "text": cta_text,
                    "type": self._classify_cta_type(cta_text),
                    "platform": platform,
                    "goal": goal,
                    "urgency_level": self._assess_urgency(cta_text),
                    "personalization": self._assess_personalization(cta_text)
                })
        
        return ctas[:5]  # Return top 5
    
    def _classify_cta_type(self, cta_text: str) -> CTAType:
        """Classify CTA type based on text"""
        text_lower = cta_text.lower()
        
        if "follow" in text_lower:
            return CTAType.FOLLOW
        elif "like" in text_lower or "heart" in text_lower:
            return CTAType.LIKE
        elif "share" in text_lower:
            return CTAType.SHARE
        elif "comment" in text_lower:
            return CTAType.COMMENT
        elif "visit" in text_lower or "link" in text_lower:
            return CTAType.VISIT_LINK
        elif "download" in text_lower:
            return CTAType.DOWNLOAD
        elif "subscribe" in text_lower:
            return CTAType.SUBSCRIBE
        elif "sign up" in text_lower:
            return CTAType.SIGN_UP
        elif "buy" in text_lower or "purchase" in text_lower:
            return CTAType.BUY_NOW
        elif "learn more" in text_lower:
            return CTAType.LEARN_MORE
        elif "save" in text_lower:
            return CTAType.SAVE_POST
        else:
            return CTAType.ENGAGEMENT
    
    def _assess_urgency(self, cta_text: str) -> str:
        """Assess urgency level of CTA"""
        urgent_words = ["now", "today", "limited", "urgent", "hurry", "fast", "quick", "immediately"]
        
        if any(word in cta_text.lower() for word in urgent_words):
            return "high"
        elif any(word in cta_text.lower() for word in ["soon", "don't wait", "act"]):
            return "medium"
        else:
            return "low"
    
    def _assess_personalization(self, cta_text: str) -> str:
        """Assess personalization level of CTA"""
        personal_words = ["you", "your", "yourself", "personally"]
        
        personal_count = sum(1 for word in personal_words if word in cta_text.lower())
        
        if personal_count >= 2:
            return "high"
        elif personal_count >= 1:
            return "medium"
        else:
            return "low"
    
    def _predict_ctr(self, cta: Dict[str, Any], platform: Platform, goal: ConversionGoal) -> float:
        """Predict click-through rate for CTA"""
        base_ctr = {
            Platform.TIKTOK: 0.06,
            Platform.INSTAGRAM: 0.04,
            Platform.YOUTUBE_SHORTS: 0.05,
            Platform.LINKEDIN: 0.03,
            Platform.TWITTER: 0.02
        }
        
        ctr = base_ctr.get(platform, 0.04)
        
        # Adjust based on CTA characteristics
        if cta["urgency_level"] == "high":
            ctr *= 1.3
        elif cta["urgency_level"] == "medium":
            ctr *= 1.1
        
        if cta["personalization"] == "high":
            ctr *= 1.2
        elif cta["personalization"] == "medium":
            ctr *= 1.1
        
        # Adjust based on goal alignment
        goal_multipliers = {
            ConversionGoal.ENGAGEMENT: 1.2,
            ConversionGoal.FOLLOWERS: 1.1,
            ConversionGoal.SALES: 0.8,
            ConversionGoal.LEAD_GENERATION: 0.9
        }
        
        ctr *= goal_multipliers.get(goal, 1.0)
        
        return round(ctr, 3)
    
    def _calculate_optimization_score(self, cta: Dict[str, Any]) -> float:
        """Calculate overall optimization score for CTA"""
        score = 0.5  # Base score
        
        # Text length optimization
        text_length = len(cta["text"])
        if 10 <= text_length <= 50:  # Optimal length
            score += 0.2
        elif text_length > 50:
            score -= 0.1
        
        # Urgency bonus
        urgency_bonus = {
            "high": 0.15,
            "medium": 0.1,
            "low": 0.0
        }
        score += urgency_bonus.get(cta["urgency_level"], 0.0)
        
        # Personalization bonus
        personalization_bonus = {
            "high": 0.15,
            "medium": 0.1,
            "low": 0.0
        }
        score += personalization_bonus.get(cta["personalization"], 0.0)
        
        return min(score, 1.0)
    
    def _generate_fallback_ctas(self, goal: ConversionGoal, platform: Platform) -> List[Dict[str, Any]]:
        """Generate fallback CTAs when AI fails"""
        
        goal_ctas = {
            ConversionGoal.ENGAGEMENT: [
                "What do you think? Comment below!",
                "Double tap if you agree!",
                "Share this with someone who needs to see it!"
            ],
            ConversionGoal.FOLLOWERS: [
                "Follow for more tips like this!",
                "Hit that follow button for daily insights!",
                "Join our community - follow now!"
            ],
            ConversionGoal.WEBSITE_TRAFFIC: [
                "Check out the full guide in our bio!",
                "Link in bio for more details!",
                "Visit our website for the complete story!"
            ],
            ConversionGoal.SALES: [
                "Get yours today - limited time offer!",
                "Shop now while supplies last!",
                "Ready to buy? Link in bio!"
            ]
        }
        
        cta_texts = goal_ctas.get(goal, goal_ctas[ConversionGoal.ENGAGEMENT])
        
        ctas = []
        for text in cta_texts:
            ctas.append({
                "text": text,
                "type": self._classify_cta_type(text),
                "platform": platform,
                "goal": goal,
                "urgency_level": self._assess_urgency(text),
                "personalization": self._assess_personalization(text)
            })
        
        return ctas


class ConversionCatalystService:
    """Main service for conversion optimization"""
    
    def __init__(self):
        self.hashtag_researcher = HashtagResearcher()
        self.caption_optimizer = CaptionOptimizer()
        self.cta_generator = CTAGenerator()
    
    async def create_conversion_optimization(
        self,
        campaign_id: str,
        original_caption: str,
        content_theme: str,
        brand_name: str,
        industry: str,
        platform: Platform,
        target_audience: str,
        conversion_goal: ConversionGoal,
        brand_voice: Dict[str, Any] = None
    ) -> ConversionOptimization:
        """Create complete conversion optimization package"""
        
        logger.info(f"Creating conversion optimization for campaign: {campaign_id}")
        
        # Optimize caption
        optimized_caption = await self.caption_optimizer.optimize_caption(
            original_caption=original_caption,
            platform=platform,
            brand_name=brand_name,
            target_audience=target_audience,
            conversion_goal=conversion_goal,
            brand_voice=brand_voice or {}
        )
        
        # Research hashtags
        recommended_hashtags = await self.hashtag_researcher.research_hashtags(
            content_theme=content_theme,
            industry=industry,
            platform=platform,
            target_audience=target_audience,
            limit=20
        )
        
        # Generate CTAs
        cta_recommendations = await self.cta_generator.generate_ctas(
            conversion_goal=conversion_goal,
            platform=platform,
            brand_name=brand_name,
            content_theme=content_theme,
            target_audience=target_audience
        )
        
        # Generate posting schedule
        posting_schedule = self._generate_posting_schedule(platform, target_audience)
        
        # Create A/B test plan
        ab_test_plan = self._create_ab_test_plan(optimized_caption, recommended_hashtags, cta_recommendations)
        
        # Predict performance
        performance_predictions = self._predict_performance(
            optimized_caption, recommended_hashtags, cta_recommendations, platform, conversion_goal
        )
        
        optimization = ConversionOptimization(
            campaign_id=campaign_id,
            conversion_goal=conversion_goal,
            platform=platform,
            target_audience=target_audience,
            optimized_caption=optimized_caption,
            recommended_hashtags=recommended_hashtags,
            cta_recommendations=cta_recommendations,
            posting_schedule=posting_schedule,
            a_b_test_plan=ab_test_plan,
            performance_predictions=performance_predictions
        )
        
        logger.info(f"Conversion optimization completed for campaign: {campaign_id}")
        
        return optimization
    
    def _generate_posting_schedule(self, platform: Platform, target_audience: str) -> Dict[str, Any]:
        """Generate optimal posting schedule"""
        
        platform_schedules = {
            Platform.TIKTOK: {
                "best_days": ["Tuesday", "Thursday", "Sunday"],
                "best_times": ["6:00-10:00", "19:00-21:00"],
                "frequency": "1-3 times per day",
                "timezone_note": "Post in audience timezone"
            },
            Platform.INSTAGRAM: {
                "best_days": ["Wednesday", "Friday", "Saturday"],
                "best_times": ["11:00-13:00", "19:00-21:00"],
                "frequency": "1 time per day",
                "timezone_note": "Post in audience timezone"
            },
            Platform.YOUTUBE_SHORTS: {
                "best_days": ["Thursday", "Friday", "Saturday", "Sunday"],
                "best_times": ["14:00-16:00", "20:00-22:00"],
                "frequency": "3-5 times per week",
                "timezone_note": "Post in audience timezone"
            },
            Platform.LINKEDIN: {
                "best_days": ["Tuesday", "Wednesday", "Thursday"],
                "best_times": ["8:00-10:00", "12:00-14:00"],
                "frequency": "3-5 times per week",
                "timezone_note": "Post in business hours"
            }
        }
        
        schedule = platform_schedules.get(platform, platform_schedules[Platform.INSTAGRAM])
        
        # Adjust for target audience
        if "business" in target_audience.lower():
            schedule["best_times"] = ["8:00-10:00", "12:00-14:00", "17:00-19:00"]
        elif "student" in target_audience.lower():
            schedule["best_times"] = ["12:00-15:00", "19:00-23:00"]
        
        return schedule
    
    def _create_ab_test_plan(
        self,
        optimized_caption: OptimizedCaption,
        hashtags: List[HashtagAnalysis],
        ctas: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Create A/B testing plan"""
        
        return {
            "caption_variants": {
                "variant_a": optimized_caption.optimized_caption,
                "variant_b": optimized_caption.a_b_test_variants[0] if optimized_caption.a_b_test_variants else optimized_caption.optimized_caption,
                "test_metric": "engagement_rate",
                "duration_days": 7
            },
            "hashtag_variants": {
                "variant_a": [h.hashtag for h in hashtags[:10]],
                "variant_b": [h.hashtag for h in hashtags[5:15]],
                "test_metric": "reach",
                "duration_days": 7
            },
            "cta_variants": {
                "variant_a": ctas[0]["text"] if ctas else "Engage with this post!",
                "variant_b": ctas[1]["text"] if len(ctas) > 1 else "Let us know what you think!",
                "test_metric": "conversion_rate",
                "duration_days": 14
            },
            "sample_size_per_variant": 1000,
            "confidence_level": 0.95
        }
    
    def _predict_performance(
        self,
        caption: OptimizedCaption,
        hashtags: List[HashtagAnalysis],
        ctas: List[Dict[str, Any]],
        platform: Platform,
        goal: ConversionGoal
    ) -> Dict[str, float]:
        """Predict content performance metrics"""
        
        # Base predictions for platform
        base_metrics = {
            Platform.TIKTOK: {
                "engagement_rate": 0.08,
                "reach_multiplier": 2.5,
                "conversion_rate": 0.02
            },
            Platform.INSTAGRAM: {
                "engagement_rate": 0.04,
                "reach_multiplier": 1.8,
                "conversion_rate": 0.015
            },
            Platform.YOUTUBE_SHORTS: {
                "engagement_rate": 0.06,
                "reach_multiplier": 2.0,
                "conversion_rate": 0.025
            }
        }
        
        metrics = base_metrics.get(platform, base_metrics[Platform.INSTAGRAM])
        
        # Apply optimization multipliers
        engagement_rate = metrics["engagement_rate"] * (1 + caption.estimated_engagement_lift)
        
        # Hashtag impact on reach
        avg_hashtag_reach = sum(h.estimated_reach for h in hashtags[:10]) / len(hashtags[:10]) if hashtags else 10000
        estimated_reach = avg_hashtag_reach * metrics["reach_multiplier"]
        
        # CTA impact on conversion
        best_cta_ctr = max([cta.get("predicted_ctr", 0.02) for cta in ctas]) if ctas else 0.02
        conversion_rate = metrics["conversion_rate"] * (best_cta_ctr / 0.02)  # Normalize to base CTR
        
        return {
            "estimated_engagement_rate": round(engagement_rate, 3),
            "estimated_reach": int(estimated_reach),
            "estimated_conversion_rate": round(conversion_rate, 3),
            "estimated_likes": int(estimated_reach * engagement_rate * 0.7),
            "estimated_comments": int(estimated_reach * engagement_rate * 0.2),
            "estimated_shares": int(estimated_reach * engagement_rate * 0.1),
            "estimated_conversions": int(estimated_reach * conversion_rate)
        }


# Global service instance
_conversion_catalyst_service: Optional[ConversionCatalystService] = None


async def get_conversion_catalyst_service() -> ConversionCatalystService:
    """Get global conversion catalyst service instance"""
    global _conversion_catalyst_service
    if _conversion_catalyst_service is None:
        _conversion_catalyst_service = ConversionCatalystService()
    return _conversion_catalyst_service