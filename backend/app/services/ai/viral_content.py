"""
Viral Content Generation Service

Generates viral content ideas, hooks, and scores content for viral potential
using proven patterns and trend analysis.
"""

import asyncio
import json
import re
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple
import logging

import numpy as np
from diskcache import Cache

from app.core.config import settings
from app.services.ai.providers import get_text_service
from app.services.ai.vector_db import get_vector_service
from app.services.ai.prompts import get_prompt_template

logger = logging.getLogger(__name__)

# Cache for trends and viral patterns
trends_cache = Cache("/tmp/viralos_trends_cache", size_limit=100000000)  # 100MB cache


class Platform(str, Enum):
    """Social media platforms"""
    TIKTOK = "tiktok"
    INSTAGRAM = "instagram"
    YOUTUBE_SHORTS = "youtube_shorts"
    TWITTER = "twitter"
    FACEBOOK = "facebook"
    LINKEDIN = "linkedin"


class ViralPattern(str, Enum):
    """Proven viral content patterns"""
    CURIOSITY_GAP = "curiosity_gap"
    MISTAKE_REVEAL = "mistake_reveal"
    BEFORE_AFTER = "before_after"
    CONTROVERSY = "controversy"
    BEHIND_SCENES = "behind_scenes"
    TUTORIAL = "tutorial"
    REACTION = "reaction"
    TREND_HIJACK = "trend_hijack"
    SOCIAL_PROOF = "social_proof"
    EMOTIONAL_STORY = "emotional_story"


@dataclass
class ViralHook:
    """A viral content hook"""
    text: str
    pattern: ViralPattern
    viral_score: float
    emotion: str
    platform: Platform
    reasoning: str
    improvements: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "text": self.text,
            "pattern": self.pattern,
            "viral_score": self.viral_score,
            "emotion": self.emotion,
            "platform": self.platform,
            "reasoning": self.reasoning,
            "improvements": self.improvements
        }


@dataclass
class ContentIdea:
    """Complete content idea with hooks and metadata"""
    title: str
    hooks: List[ViralHook]
    content_pillar: str
    target_audience: str
    estimated_engagement: float
    content_type: str  # video, carousel, single_post
    keywords: List[str]
    trending_topics: List[str]
    created_at: float = field(default_factory=time.time)
    
    def get_best_hook(self) -> Optional[ViralHook]:
        """Get the highest scoring hook"""
        if not self.hooks:
            return None
        return max(self.hooks, key=lambda h: h.viral_score)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "title": self.title,
            "hooks": [h.to_dict() for h in self.hooks],
            "content_pillar": self.content_pillar,
            "target_audience": self.target_audience,
            "estimated_engagement": self.estimated_engagement,
            "content_type": self.content_type,
            "keywords": self.keywords,
            "trending_topics": self.trending_topics,
            "created_at": self.created_at
        }


@dataclass
class TrendData:
    """Trending topic or hashtag data"""
    topic: str
    platform: Platform
    engagement_score: float
    growth_rate: float
    keywords: List[str]
    sentiment: str
    first_seen: float
    last_updated: float = field(default_factory=time.time)
    
    def is_fresh(self, max_age_hours: int = 6) -> bool:
        """Check if trend data is still fresh"""
        age_hours = (time.time() - self.last_updated) / 3600
        return age_hours < max_age_hours


class ViralPatternAnalyzer:
    """Analyzes content for viral patterns and potential"""
    
    VIRAL_PATTERNS = {
        ViralPattern.CURIOSITY_GAP: {
            "triggers": [
                "3 things", "what nobody tells you", "the truth about", "secret",
                "hidden", "revealed", "exposed", "what I learned", "shocking"
            ],
            "template": "What {experts} don't want you to know about {topic}",
            "effectiveness": 0.85
        },
        ViralPattern.MISTAKE_REVEAL: {
            "triggers": [
                "mistakes", "wrong about", "wish I knew", "don't do this",
                "avoid", "failed", "learned the hard way"
            ],
            "template": "5 mistakes everyone makes with {topic}",
            "effectiveness": 0.90
        },
        ViralPattern.BEFORE_AFTER: {
            "triggers": [
                "before vs after", "transformation", "results", "changed my life",
                "went from", "to", "journey"
            ],
            "template": "I went from {before_state} to {after_state} in {timeframe}",
            "effectiveness": 0.80
        },
        ViralPattern.CONTROVERSY: {
            "triggers": [
                "unpopular opinion", "controversial", "disagree", "wrong",
                "stop saying", "needs to stop", "overrated"
            ],
            "template": "Unpopular opinion: {controversial_statement}",
            "effectiveness": 0.75
        },
        ViralPattern.TUTORIAL: {
            "triggers": [
                "how to", "step by step", "tutorial", "guide", "learn",
                "easy way", "simple trick"
            ],
            "template": "How to {accomplish_goal} in {timeframe}",
            "effectiveness": 0.70
        }
    }
    
    @classmethod
    def identify_pattern(cls, text: str) -> Optional[ViralPattern]:
        """Identify viral pattern in text"""
        text_lower = text.lower()
        
        best_pattern = None
        max_matches = 0
        
        for pattern, data in cls.VIRAL_PATTERNS.items():
            matches = sum(1 for trigger in data["triggers"] if trigger in text_lower)
            if matches > max_matches:
                max_matches = matches
                best_pattern = pattern
        
        return best_pattern if max_matches > 0 else None
    
    @classmethod
    def calculate_pattern_score(cls, pattern: ViralPattern, text: str) -> float:
        """Calculate how well text matches a viral pattern"""
        if pattern not in cls.VIRAL_PATTERNS:
            return 0.0
        
        pattern_data = cls.VIRAL_PATTERNS[pattern]
        text_lower = text.lower()
        
        # Count trigger matches
        trigger_matches = sum(1 for trigger in pattern_data["triggers"] if trigger in text_lower)
        trigger_score = min(trigger_matches / len(pattern_data["triggers"]), 1.0)
        
        # Base effectiveness of pattern
        effectiveness = pattern_data["effectiveness"]
        
        return trigger_score * effectiveness
    
    @classmethod
    def suggest_improvements(cls, hook: str, pattern: ViralPattern) -> List[str]:
        """Suggest improvements for a hook"""
        suggestions = []
        
        if pattern == ViralPattern.CURIOSITY_GAP:
            if "secret" not in hook.lower():
                suggestions.append("Add mystery with words like 'secret' or 'hidden'")
            if not any(num in hook for num in ['3', '5', '7']):
                suggestions.append("Include specific numbers (3, 5, 7 work well)")
        
        elif pattern == ViralPattern.MISTAKE_REVEAL:
            if "mistake" not in hook.lower():
                suggestions.append("Use stronger language like 'biggest mistake'")
            if not re.search(r'\d+', hook):
                suggestions.append("Specify number of mistakes (e.g., '5 mistakes')")
        
        elif pattern == ViralPattern.BEFORE_AFTER:
            if "from" not in hook.lower() and "to" not in hook.lower():
                suggestions.append("Make the transformation clearer with 'from X to Y'")
        
        # General improvements
        if len(hook) > 60:
            suggestions.append("Shorten hook for better mobile readability")
        
        if not any(word in hook.lower() for word in ['you', 'your', 'yourself']):
            suggestions.append("Make it more personal with 'you' or 'your'")
        
        return suggestions


class TrendAnalyzer:
    """Analyzes current trends and viral content patterns"""
    
    def __init__(self):
        self.vector_service = None
    
    async def _get_vector_service(self):
        """Get vector service instance"""
        if self.vector_service is None:
            self.vector_service = await get_vector_service()
    
    async def get_trending_topics(self, platform: Platform, limit: int = 20) -> List[TrendData]:
        """Get current trending topics for platform"""
        cache_key = f"trends_{platform}_{int(time.time() // 3600)}"  # Hourly cache
        
        if cache_key in trends_cache:
            cached_trends = trends_cache[cache_key]
            return [TrendData(**trend) for trend in cached_trends if TrendData(**trend).is_fresh()]
        
        # In a real implementation, this would connect to trend APIs
        # For now, return mock trending data
        mock_trends = await self._generate_mock_trends(platform)
        
        # Cache the trends
        trends_cache.set(cache_key, [trend.__dict__ for trend in mock_trends], 
                        expire=settings.CACHE_TTL_TRENDS)
        
        return mock_trends
    
    async def _generate_mock_trends(self, platform: Platform) -> List[TrendData]:
        """Generate mock trending data (replace with real API calls)"""
        # This is mock data - in production, integrate with:
        # - TikTok Trending API
        # - Instagram Hashtag API  
        # - Twitter Trends API
        # - Google Trends API
        
        base_trends = {
            Platform.TIKTOK: [
                "AI productivity hacks", "Small business tips", "Remote work setup",
                "Budget meal prep", "Quick workouts", "Study methods", "Life hacks",
                "Tech reviews", "Behind the scenes", "Day in my life"
            ],
            Platform.INSTAGRAM: [
                "Aesthetic workspace", "Morning routine", "Sustainable living",
                "Business growth", "Minimalist lifestyle", "Travel tips",
                "Photography tips", "Self-care Sunday", "Outfit of the day"
            ],
            Platform.YOUTUBE_SHORTS: [
                "60 second tutorials", "Quick recipes", "Tech tips",
                "Productivity hacks", "Life advice", "Money tips",
                "Fitness shortcuts", "Learning techniques"
            ]
        }
        
        trends = []
        platform_topics = base_trends.get(platform, base_trends[Platform.TIKTOK])
        
        for i, topic in enumerate(platform_topics):
            trends.append(TrendData(
                topic=topic,
                platform=platform,
                engagement_score=0.6 + (i % 5) * 0.08,  # Mock engagement 0.6-0.9
                growth_rate=0.1 + (i % 3) * 0.15,  # Mock growth 0.1-0.4
                keywords=topic.lower().split(),
                sentiment="positive" if i % 3 == 0 else "neutral",
                first_seen=time.time() - (i * 3600),  # Stagger discovery times
                last_updated=time.time()
            ))
        
        return trends
    
    async def analyze_competitor_content(self, industry: str, limit: int = 50) -> Dict[str, Any]:
        """Analyze competitor content patterns"""
        await self._get_vector_service()
        
        # Search for competitor content in vector database
        competitor_content = await self.vector_service.search_similar(
            f"viral {industry} content marketing",
            namespace="competitor_analysis",
            top_k=limit,
            similarity_threshold=0.6
        )
        
        if not competitor_content:
            return {"patterns": [], "top_performers": [], "insights": []}
        
        # Analyze patterns in high-performing content
        high_performers = [c for c in competitor_content if c.score > 0.8]
        
        patterns = {}
        for content in high_performers:
            pattern = ViralPatternAnalyzer.identify_pattern(content.content)
            if pattern:
                patterns[pattern] = patterns.get(pattern, 0) + 1
        
        # Sort patterns by frequency
        top_patterns = sorted(patterns.items(), key=lambda x: x[1], reverse=True)
        
        return {
            "patterns": [{"pattern": p[0], "frequency": p[1]} for p in top_patterns[:5]],
            "top_performers": [
                {"content": c.content[:200], "score": c.score} 
                for c in high_performers[:10]
            ],
            "insights": [
                f"Most effective pattern: {top_patterns[0][0]}" if top_patterns else "No clear patterns found",
                f"Analyzed {len(competitor_content)} competitor posts",
                f"{len(high_performers)} high-performing posts identified"
            ]
        }


class ViralContentGenerator:
    """Main service for generating viral content ideas and hooks"""
    
    def __init__(self):
        self.text_service = None
        self.vector_service = None
        self.trend_analyzer = TrendAnalyzer()
        self.pattern_analyzer = ViralPatternAnalyzer()
    
    async def _get_services(self):
        """Initialize AI services"""
        if self.text_service is None:
            self.text_service = await get_text_service()
        if self.vector_service is None:
            self.vector_service = await get_vector_service()
    
    async def generate_content_ideas(
        self,
        brand_name: str,
        industry: str,
        content_pillars: List[str],
        target_audience: str,
        platform: Platform,
        count: int = 5
    ) -> List[ContentIdea]:
        """Generate viral content ideas"""
        await self._get_services()
        
        logger.info(f"Generating {count} content ideas for {brand_name} on {platform}")
        
        # Get trending topics
        trends = await self.trend_analyzer.get_trending_topics(platform, limit=10)
        trending_topics = [t.topic for t in trends[:5]]
        
        # Analyze competitor content
        competitor_analysis = await self.trend_analyzer.analyze_competitor_content(industry)
        
        ideas = []
        for pillar in content_pillars[:count]:  # Generate ideas per pillar
            for trend_topic in trending_topics[:2]:  # Max 2 trends per pillar
                idea = await self._generate_single_idea(
                    brand_name=brand_name,
                    industry=industry,
                    content_pillar=pillar,
                    target_audience=target_audience,
                    platform=platform,
                    trending_topic=trend_topic,
                    competitor_patterns=competitor_analysis.get("patterns", [])
                )
                
                if idea:
                    ideas.append(idea)
                    
                if len(ideas) >= count:
                    break
            
            if len(ideas) >= count:
                break
        
        # Sort by estimated engagement
        ideas.sort(key=lambda x: x.estimated_engagement, reverse=True)
        
        return ideas[:count]
    
    async def _generate_single_idea(
        self,
        brand_name: str,
        industry: str,
        content_pillar: str,
        target_audience: str,
        platform: Platform,
        trending_topic: str,
        competitor_patterns: List[Dict[str, Any]]
    ) -> Optional[ContentIdea]:
        """Generate a single content idea"""
        
        # Generate hooks using AI
        hooks = await self.generate_viral_hooks(
            brand_name=brand_name,
            industry=industry,
            content_pillar=content_pillar,
            target_audience=target_audience,
            platform=platform,
            trending_topic=trending_topic,
            count=3
        )
        
        if not hooks:
            return None
        
        # Calculate estimated engagement based on various factors
        engagement_score = self._calculate_engagement_estimate(
            hooks, trending_topic, competitor_patterns
        )
        
        # Extract keywords from pillar and trending topic
        keywords = content_pillar.lower().split() + trending_topic.lower().split()
        keywords = list(dict.fromkeys(keywords))  # Remove duplicates while preserving order
        
        return ContentIdea(
            title=f"{content_pillar} x {trending_topic}",
            hooks=hooks,
            content_pillar=content_pillar,
            target_audience=target_audience,
            estimated_engagement=engagement_score,
            content_type="video",  # Default to video for most platforms
            keywords=keywords,
            trending_topics=[trending_topic]
        )
    
    async def generate_viral_hooks(
        self,
        brand_name: str,
        industry: str,
        content_pillar: str,
        target_audience: str,
        platform: Platform,
        trending_topic: str = "",
        count: int = 5
    ) -> List[ViralHook]:
        """Generate viral hooks for content"""
        
        # Get viral hook generation prompt
        hook_prompt = await get_prompt_template("viral_hook_generation")
        
        # Format prompt with context
        formatted_prompt = hook_prompt.format(
            brand_name=brand_name,
            industry=industry,
            content_pillar=content_pillar,
            target_audience=target_audience,
            platform=platform
        )
        
        # Add trending topic if provided
        if trending_topic:
            formatted_prompt += f"\n\nIncorporate this trending topic: {trending_topic}"
        
        # Generate hooks with AI
        response = await self.text_service.generate(
            formatted_prompt,
            max_tokens=800,
            temperature=0.8  # Higher creativity for viral content
        )
        
        if not response.success:
            raise Exception(f"AI hook generation failed: {response.error}")
        
        # Parse AI response into ViralHook objects
        hooks = self._parse_hooks_response(response.content, platform)
        
        if not hooks:
            raise Exception("AI hook generation returned no valid hooks")
        
        # Score and enhance each hook
        enhanced_hooks = []
        for hook in hooks:
            scored_hook = await self.score_viral_potential(hook, platform, target_audience)
            enhanced_hooks.append(scored_hook)
        
        # Sort by viral score and return top hooks
        enhanced_hooks.sort(key=lambda h: h.viral_score, reverse=True)
        return enhanced_hooks[:count]
    
    def _parse_hooks_response(self, ai_response: str, platform: Platform) -> List[ViralHook]:
        """Parse AI response into ViralHook objects"""
        hooks = []
        lines = ai_response.strip().split('\n')
        
        current_hook = None
        current_text = ""
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
            
            # Look for numbered hooks
            if re.match(r'^\d+\.', line):
                # Save previous hook if exists
                if current_text:
                    pattern = self.pattern_analyzer.identify_pattern(current_text)
                    hooks.append(ViralHook(
                        text=current_text,
                        pattern=pattern or ViralPattern.CURIOSITY_GAP,
                        viral_score=0.0,  # Will be scored later
                        emotion="curiosity",
                        platform=platform,
                        reasoning=""
                    ))
                
                # Start new hook
                current_text = re.sub(r'^\d+\.\s*', '', line)
            
            elif current_text and not line.startswith(('Hook:', 'Pattern:', 'Score:')):
                # Continue current hook text
                current_text += " " + line
        
        # Don't forget the last hook
        if current_text:
            pattern = self.pattern_analyzer.identify_pattern(current_text)
            hooks.append(ViralHook(
                text=current_text,
                pattern=pattern or ViralPattern.CURIOSITY_GAP,
                viral_score=0.0,
                emotion="curiosity",
                platform=platform,
                reasoning=""
            ))
        
        return hooks
    
    async def score_viral_potential(
        self, 
        hook: ViralHook, 
        platform: Platform, 
        target_audience: str
    ) -> ViralHook:
        """Score viral potential of a hook"""
        
        # Get viral scoring prompt
        scoring_prompt = await get_prompt_template("viral_scoring")
        
        # Generate detailed scoring
        response = await self.text_service.generate(
            scoring_prompt.format(
                hook=hook.text,
                platform=platform,
                target_audience=target_audience
            ),
            max_tokens=400,
            temperature=0.3
        )
        
        if response.success:
            # Parse AI scoring response
            score_data = self._parse_scoring_response(response.content)
            hook.viral_score = score_data.get("overall_score", 5.0)
            hook.reasoning = score_data.get("reasoning", "")
        else:
            raise Exception(f"AI scoring service failed: {response.error if hasattr(response, 'error') else 'Unknown error'}")
        
        # Add improvement suggestions
        hook.improvements = self.pattern_analyzer.suggest_improvements(hook.text, hook.pattern)
        
        return hook
    
    def _parse_scoring_response(self, ai_response: str) -> Dict[str, Any]:
        """Parse AI scoring response"""
        score_data = {"overall_score": 5.0, "reasoning": ai_response}
        
        # Look for overall score in response
        score_match = re.search(r'overall.*?score.*?(\d+(?:\.\d+)?)', ai_response.lower())
        if score_match:
            try:
                score_data["overall_score"] = float(score_match.group(1))
            except ValueError:
                pass
        
        return score_data
    
    def _calculate_fallback_score(self, hook: ViralHook) -> float:
        """Calculate fallback viral score based on pattern analysis"""
        base_score = 5.0
        
        # Pattern effectiveness
        pattern_score = self.pattern_analyzer.calculate_pattern_score(hook.pattern, hook.text)
        base_score += pattern_score * 3  # Scale to 0-3 points
        
        # Length optimization (shorter is often better for hooks)
        length_score = max(0, 2 - len(hook.text) / 30)  # Optimal around 30-60 chars
        base_score += length_score
        
        # Emotional trigger words
        emotional_words = [
            'secret', 'shocking', 'amazing', 'incredible', 'mistake', 'wrong',
            'truth', 'hidden', 'revealed', 'exposed', 'never', 'always'
        ]
        
        emotion_score = sum(0.2 for word in emotional_words if word in hook.text.lower())
        base_score += min(emotion_score, 1.0)  # Cap at 1 point
        
        return min(base_score, 10.0)  # Cap at 10
    
    def _calculate_engagement_estimate(
        self,
        hooks: List[ViralHook],
        trending_topic: str,
        competitor_patterns: List[Dict[str, Any]]
    ) -> float:
        """Calculate estimated engagement for content idea"""
        if not hooks:
            return 0.5
        
        # Base score from best hook
        best_hook = max(hooks, key=lambda h: h.viral_score)
        base_score = best_hook.viral_score / 10.0  # Normalize to 0-1
        
        # Boost for trending topic alignment
        trend_boost = 0.2 if trending_topic else 0.0
        
        # Boost for using proven competitor patterns
        pattern_boost = 0.0
        if competitor_patterns:
            hook_pattern = best_hook.pattern
            for pattern_data in competitor_patterns:
                if pattern_data.get("pattern") == hook_pattern:
                    pattern_boost = 0.15
                    break
        
        final_score = base_score + trend_boost + pattern_boost
        return min(final_score, 1.0)  # Cap at 1.0
    
    async def optimize_hook_for_platform(
        self, 
        hook: ViralHook, 
        target_platform: Platform
    ) -> ViralHook:
        """Optimize hook for specific platform requirements"""
        
        platform_limits = {
            Platform.TIKTOK: {"max_length": 100, "style": "casual"},
            Platform.INSTAGRAM: {"max_length": 125, "style": "aesthetic"},
            Platform.YOUTUBE_SHORTS: {"max_length": 100, "style": "tutorial"},
            Platform.TWITTER: {"max_length": 140, "style": "conversational"},
            Platform.LINKEDIN: {"max_length": 150, "style": "professional"}
        }
        
        platform_config = platform_limits.get(target_platform, {"max_length": 100, "style": "casual"})
        
        # Truncate if too long
        if len(hook.text) > platform_config["max_length"]:
            # Try to truncate at word boundary
            truncated = hook.text[:platform_config["max_length"]]
            last_space = truncated.rfind(' ')
            if last_space > platform_config["max_length"] * 0.8:  # If we can save most of the text
                hook.text = truncated[:last_space] + "..."
            else:
                hook.text = truncated + "..."
        
        # Platform-specific optimizations
        if target_platform == Platform.TIKTOK:
            # Add trending hashtag format
            if not hook.text.endswith("?") and not hook.text.endswith("!"):
                hook.text += "! 👀"
        
        elif target_platform == Platform.LINKEDIN:
            # Make more professional
            hook.text = hook.text.replace("you guys", "professionals")
            hook.text = hook.text.replace("omg", "notably")
        
        hook.platform = target_platform
        return hook
    
    async def generate_ideas(
        self,
        brand_data: Dict[str, Any],
        products: List[Dict[str, Any]],
        count: int = 5
    ) -> List[Dict[str, Any]]:
        """Generate viral content ideas based on brand and products"""
        
        await self._get_services()
        
        brand_name = brand_data.get("name", "Brand")
        description = brand_data.get("description", "")
        target_audience = brand_data.get("target_audience", {})
        value_proposition = brand_data.get("value_proposition", "")
        
        # Extract content pillars from products
        content_pillars = []
        for product in products[:5]:  # Use top 5 products
            if product.get("name"):
                content_pillars.append(product["name"])
        
        if not content_pillars:
            content_pillars = ["Product showcase", "Brand story", "Behind the scenes"]
        
        # Generate content ideas
        ideas = await self.generate_content_ideas(
            brand_name=brand_name,
            industry=self._detect_industry(brand_data, products),
            content_pillars=content_pillars,
            target_audience=str(target_audience),
            platform=Platform.TIKTOK,  # Default to TikTok
            count=count
        )
        
        # Convert to dict format for API response
        return [idea.to_dict() for idea in ideas]
    
    async def create_video_outline(
        self,
        content_idea: Dict[str, Any],
        brand_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Create detailed video outline from content idea"""
        
        await self._get_services()
        
        # Get the best hook from the content idea
        hooks = content_idea.get("hooks", [])
        if not hooks:
            return None
        
        best_hook = max(hooks, key=lambda h: h.get("viral_score", 0))
        
        # Generate video outline using AI
        outline_prompt = f"""
        Create a detailed video outline for this viral content:
        
        Hook: {best_hook.get("text", "")}
        Content Pillar: {content_idea.get("content_pillar", "")}
        Target Audience: {content_idea.get("target_audience", "")}
        Brand: {brand_data.get("name", "")}
        Brand Voice: {brand_data.get("brand_voice", {}).get("primary_voice", "casual")}
        
        Create a video outline with:
        1. Opening hook (first 3 seconds)
        2. Problem/pain point (3-8 seconds)
        3. Solution reveal (8-15 seconds)
        4. Proof/demonstration (15-25 seconds)
        5. Call to action (25-30 seconds)
        
        For each scene include:
        - Visual description
        - Dialogue/voiceover
        - Text overlay suggestions
        - Timing
        - Transition notes
        
        Format as JSON with scenes array and metadata.
        """
        
        try:
            response = await self.text_service.generate(outline_prompt, max_tokens=800, temperature=0.7)
            if response.success:
                try:
                    outline_data = json.loads(response.content)
                    outline_data["content_idea"] = content_idea
                    outline_data["hook"] = best_hook
                    return outline_data
                except json.JSONDecodeError:
                    raise Exception("AI returned invalid JSON for video outline")
        except Exception as e:
            raise Exception(f"Video outline generation failed: {e}")
        
        raise Exception("Video outline generation failed - no valid response from AI")
    
    def _detect_industry(self, brand_data: Dict[str, Any], products: List[Dict[str, Any]]) -> str:
        """Detect industry from brand and product data"""
        
        description = (brand_data.get("description", "") + " " + 
                      brand_data.get("value_proposition", "")).lower()
        
        # Add product names to analysis
        for product in products[:3]:
            description += " " + product.get("name", "").lower()
        
        industry_indicators = {
            "fashion": ["fashion", "clothing", "apparel", "style", "outfit"],
            "beauty": ["beauty", "skincare", "cosmetics", "makeup", "care"],
            "tech": ["technology", "tech", "software", "app", "digital"],
            "fitness": ["fitness", "health", "workout", "exercise", "wellness"],
            "food": ["food", "restaurant", "recipe", "cooking", "nutrition"],
            "home": ["home", "furniture", "decor", "kitchen", "interior"],
            "business": ["business", "professional", "service", "consulting"],
            "education": ["education", "learning", "course", "training"]
        }
        
        for industry, keywords in industry_indicators.items():
            if any(keyword in description for keyword in keywords):
                return industry
        
        return "general"  # Generic industry when detection fails
    


# Global service instance
_viral_content_service: Optional[ViralContentGenerator] = None


async def get_viral_content_service() -> ViralContentGenerator:
    """Get global viral content service instance"""
    global _viral_content_service
    if _viral_content_service is None:
        _viral_content_service = ViralContentGenerator()
    return _viral_content_service