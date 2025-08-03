"""
SEO optimizer for viral content to maximize conversion.
"""

import asyncio
import json
from typing import Any, Dict, List, Optional
import logging

from app.services.ai.providers import get_text_service
from app.core.config import settings

logger = logging.getLogger(__name__)


class SEOOptimizer:
    """SEO optimization for viral content conversion"""
    
    def __init__(self):
        self.ai_service = None
    
    async def _get_ai_service(self):
        """Initialize AI service"""
        if self.ai_service is None:
            self.ai_service = await get_text_service()
    
    async def optimize_for_conversion(self, video_outline: Dict[str, Any], brand_data: Dict[str, Any]) -> Dict[str, Any]:
        """Optimize video content for SEO and conversion"""
        
        await self._get_ai_service()
        
        content_idea = video_outline.get("content_idea", {})
        scenes = video_outline.get("scenes", [])
        
        optimization_data = {
            "title_options": await self._generate_seo_titles(content_idea, brand_data),
            "description": await self._generate_seo_description(video_outline, brand_data),
            "hashtags": await self._generate_seo_hashtags(content_idea, brand_data),
            "keywords": await self._extract_target_keywords(content_idea, brand_data),
            "call_to_action": await self._optimize_cta(video_outline, brand_data),
            "thumbnails": await self._suggest_thumbnails(content_idea, brand_data),
            "posting_strategy": await self._suggest_posting_strategy(content_idea, brand_data)
        }
        
        return optimization_data
    
    async def _generate_seo_titles(self, content_idea: Dict[str, Any], brand_data: Dict[str, Any]) -> List[str]:
        """Generate SEO-optimized titles"""
        
        hook = content_idea.get("hook", "")
        description = content_idea.get("description", "")
        brand_name = brand_data.get("name", "")
        
        prompt = f"""
        Create 5 SEO-optimized video titles for this content:
        
        Hook: {hook}
        Content: {description}
        Brand: {brand_name}
        
        Requirements:
        1. Include target keywords naturally
        2. Create curiosity and urgency
        3. Keep under 60 characters for mobile
        4. Include emotional triggers
        5. Be click-worthy but not clickbait
        
        Return as JSON array: ["title1", "title2", "title3", "title4", "title5"]
        """
        
        try:
            response = await self.ai_service.generate(prompt, max_tokens=400, temperature=0.7)
            if response.success:
                try:
                    return json.loads(response.content)
                except:
                    # Fallback: extract titles from text
                    lines = response.content.strip().split('\n')
                    return [line.strip('- ').strip('"').strip("'") for line in lines if line.strip()][:5]
        except Exception as e:
            raise Exception(f"SEO title generation failed: {e}")
        
        raise Exception("SEO title generation failed - no valid response from AI")
    
    async def _generate_seo_description(self, video_outline: Dict[str, Any], brand_data: Dict[str, Any]) -> str:
        """Generate SEO-optimized description"""
        
        content_idea = video_outline.get("content_idea", {})
        scenes = video_outline.get("scenes", [])
        brand_name = brand_data.get("name", "")
        
        prompt = f"""
        Create an SEO-optimized video description:
        
        Content: {content_idea.get("description", "")}
        Video Scenes: {[scene.get("dialogue", "") for scene in scenes[:3]]}
        Brand: {brand_name}
        
        Requirements:
        1. Hook in first line
        2. Include target keywords naturally
        3. Add value proposition
        4. Include clear call-to-action
        5. Add relevant hashtags
        6. Keep engaging and scannable
        7. Include brand mention
        
        Format: One compelling description paragraph.
        """
        
        try:
            response = await self.ai_service.generate(prompt, max_tokens=300, temperature=0.6)
            if response.success:
                return response.content.strip()
        except Exception as e:
            raise Exception(f"SEO description generation failed: {e}")
        
        raise Exception("SEO description generation failed - no valid response from AI")
    
    async def _generate_seo_hashtags(self, content_idea: Dict[str, Any], brand_data: Dict[str, Any]) -> List[str]:
        """Generate SEO-optimized hashtags"""
        
        hook = content_idea.get("hook", "")
        platform = content_idea.get("platform", "tiktok")
        brand_name = brand_data.get("name", "")
        target_audience = brand_data.get("target_audience", {})
        
        prompt = f"""
        Generate hashtags for this content:
        
        Content: {hook}
        Platform: {platform}
        Brand: {brand_name}
        Target Audience: {target_audience}
        
        Create 3 categories:
        1. Trending hashtags (5-10M+ posts)
        2. Medium hashtags (100K-5M posts) 
        3. Niche hashtags (1K-100K posts)
        
        Requirements:
        - Mix of broad and specific
        - Platform-appropriate
        - Include brand-related tags
        - Avoid banned/shadowban hashtags
        
        Return as JSON: {"trending": [...], "medium": [...], "niche": [...]}
        """
        
        try:
            response = await self.ai_service.generate(prompt, max_tokens=400, temperature=0.6)
            if response.success:
                try:
                    hashtag_data = json.loads(response.content)
                    # Flatten all hashtags
                    all_hashtags = []
                    for category in hashtag_data.values():
                        all_hashtags.extend(category)
                    return all_hashtags[:20]  # Max 20 hashtags
                except:
                    # Fallback: extract hashtags from text
                    hashtags = []
                    lines = response.content.split('\n')
                    for line in lines:
                        if '#' in line:
                            line_hashtags = [tag.strip() for tag in line.split() if tag.startswith('#')]
                            hashtags.extend(line_hashtags)
                    return hashtags[:20]
        except Exception as e:
            raise Exception(f"Hashtag generation failed: {e}")
        
        raise Exception("Hashtag generation failed - no valid response from AI")
    
    async def _extract_target_keywords(self, content_idea: Dict[str, Any], brand_data: Dict[str, Any]) -> List[str]:
        """Extract target keywords for SEO"""
        
        description = content_idea.get("description", "")
        brand_description = brand_data.get("description", "")
        value_proposition = brand_data.get("value_proposition", "")
        
        prompt = f"""
        Extract target keywords for SEO from this content:
        
        Content: {description}
        Brand: {brand_description}
        Value Prop: {value_proposition}
        
        Find:
        1. Primary keywords (main topic)
        2. Secondary keywords (related terms)
        3. Long-tail keywords (specific phrases)
        4. Brand keywords
        
        Return as JSON: {"primary": [...], "secondary": [...], "long_tail": [...], "brand": [...]}
        """
        
        try:
            response = await self.ai_service.generate(prompt, max_tokens=300, temperature=0.5)
            if response.success:
                try:
                    keyword_data = json.loads(response.content)
                    # Flatten all keywords
                    all_keywords = []
                    for category in keyword_data.values():
                        all_keywords.extend(category)
                    return all_keywords[:15]  # Max 15 keywords
                except:
                    # Simple keyword extraction
                    text = f"{description} {brand_description} {value_proposition}".lower()
                    words = text.split()
                    # Filter for meaningful keywords
                    keywords = [word for word in words if len(word) > 3 and word.isalpha()]
                    return list(set(keywords))[:15]
        except Exception as e:
            logger.debug(f"Keyword extraction failed: {e}")
        
        return ["viral", "trending", brand_data.get("name", "").lower()]
    
    async def _optimize_cta(self, video_outline: Dict[str, Any], brand_data: Dict[str, Any]) -> Dict[str, Any]:
        """Optimize call-to-action for conversion"""
        
        content_idea = video_outline.get("content_idea", {})
        brand_name = brand_data.get("name", "")
        social_links = brand_data.get("social_links", {})
        
        prompt = f"""
        Create optimized call-to-actions for this video:
        
        Content: {content_idea.get("description", "")}
        Brand: {brand_name}
        Social Links: {social_links}
        
        Create 3 types:
        1. Primary CTA (main conversion goal)
        2. Secondary CTA (engagement goal)
        3. Social CTA (follow/subscribe)
        
        Requirements:
        - Action-oriented language
        - Create urgency
        - Specific next steps
        - Mobile-friendly
        
        Return as JSON: {"primary": "...", "secondary": "...", "social": "..."}
        """
        
        try:
            response = await self.ai_service.generate(prompt, max_tokens=300, temperature=0.6)
            if response.success:
                try:
                    return json.loads(response.content)
                except:
                    return {
                        "primary": "Check the link in bio to get yours!",
                        "secondary": "Save this for later!",
                        "social": f"Follow @{brand_name.lower()} for more!"
                    }
        except Exception as e:
            logger.debug(f"CTA optimization failed: {e}")
        
        return {
            "primary": "Click the link to learn more!",
            "secondary": "Like if this helped you!",
            "social": f"Follow for more from {brand_name}!"
        }
    
    async def _suggest_thumbnails(self, content_idea: Dict[str, Any], brand_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Suggest thumbnail concepts"""
        
        hook = content_idea.get("hook", "")
        framework = content_idea.get("framework", "")
        
        prompt = f"""
        Suggest 3 thumbnail concepts for this video:
        
        Hook: {hook}
        Framework: {framework}
        
        For each thumbnail describe:
        1. Main visual element
        2. Text overlay (if any)
        3. Color scheme
        4. Emotional appeal
        5. Click-through potential
        
        Return as JSON array of objects with keys: visual, text, colors, emotion, appeal
        """
        
        try:
            response = await self.ai_service.generate(prompt, max_tokens=400, temperature=0.7)
            if response.success:
                try:
                    return json.loads(response.content)
                except:
                    # Fallback thumbnails
                    return [
                        {
                            "visual": "Product close-up with dramatic lighting",
                            "text": "VIRAL!",
                            "colors": "Bold red and white",
                            "emotion": "Excitement",
                            "appeal": "High contrast draws attention"
                        }
                    ]
        except Exception as e:
            logger.debug(f"Thumbnail suggestion failed: {e}")
        
        return [
            {
                "visual": "Eye-catching product shot",
                "text": "Must See!",
                "colors": "Bright and contrasting",
                "emotion": "Curiosity",
                "appeal": "Draws clicks with intrigue"
            }
        ]
    
    async def _suggest_posting_strategy(self, content_idea: Dict[str, Any], brand_data: Dict[str, Any]) -> Dict[str, Any]:
        """Suggest optimal posting strategy"""
        
        platform = content_idea.get("platform", "tiktok")
        target_audience = brand_data.get("target_audience", {})
        
        # Platform-specific optimal times (these would come from data analysis)
        platform_times = {
            "tiktok": {
                "best_days": ["Tuesday", "Thursday", "Friday"],
                "best_times": ["6-10am", "7-9pm"],
                "peak_engagement": "Tuesday 9am, Thursday 7pm"
            },
            "instagram": {
                "best_days": ["Wednesday", "Thursday", "Friday"],
                "best_times": ["11am-1pm", "7-9pm"],
                "peak_engagement": "Wednesday 11am, Thursday 8pm"
            },
            "youtube": {
                "best_days": ["Thursday", "Friday", "Saturday"],
                "best_times": ["2-4pm", "8-9pm"],
                "peak_engagement": "Friday 3pm, Saturday 9am"
            }
        }
        
        strategy = platform_times.get(platform, platform_times["tiktok"])
        
        strategy.update({
            "posting_frequency": "3-5 times per week",
            "cross_platform": "Post variations across all platforms",
            "engagement_window": "First 2 hours are critical",
            "follow_up": "Engage with comments immediately",
            "repurpose": "Create 3 versions: full, short, story format"
        })
        
        return strategy