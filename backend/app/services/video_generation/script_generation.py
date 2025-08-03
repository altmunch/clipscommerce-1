"""
Script generation service for creating compelling video scripts from product data
"""

import asyncio
import json
import logging
import re
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass
from enum import Enum

from app.core.config import settings
from app.services.ai.providers import get_text_service
from app.models.product import Product
from app.models.brand import Brand

logger = logging.getLogger(__name__)


class ScriptType(Enum):
    """Types of video scripts"""
    PRODUCT_SHOWCASE = "product_showcase"
    UNBOXING = "unboxing" 
    COMPARISON = "comparison"
    TUTORIAL = "tutorial"
    TESTIMONIAL = "testimonial"
    LIFESTYLE = "lifestyle"
    PROBLEM_SOLUTION = "problem_solution"
    BRAND_STORY = "brand_story"


class ToneStyle(Enum):
    """Video tone and style options"""
    ENERGETIC = "energetic"
    PROFESSIONAL = "professional"
    CASUAL = "casual"
    ENTHUSIASTIC = "enthusiastic"
    EDUCATIONAL = "educational"
    HUMOROUS = "humorous"
    DRAMATIC = "dramatic"
    AUTHENTIC = "authentic"


class PlatformOptimization(Enum):
    """Platform-specific optimizations"""
    TIKTOK = "tiktok"        # Short, punchy, trend-aware
    INSTAGRAM = "instagram"   # Visual-first, aesthetic
    YOUTUBE_SHORTS = "youtube_shorts"  # Educational, clear
    YOUTUBE = "youtube"       # Detailed, informative
    FACEBOOK = "facebook"     # Community-focused
    TWITTER = "twitter"       # Concise, conversation-starter


@dataclass
class ScriptSegment:
    """Individual segment of a video script"""
    segment_number: int
    timestamp_start: float
    timestamp_end: float
    duration: float
    hook_element: Optional[str]  # What makes this segment engaging
    dialogue: str
    action_description: str
    visual_cues: List[str]
    emotion: str
    product_focus: Optional[str]  # Which product/feature to highlight
    call_to_action: Optional[str]
    
    @property
    def word_count(self) -> int:
        return len(self.dialogue.split())
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "segment_number": self.segment_number,
            "timestamp_start": self.timestamp_start,
            "timestamp_end": self.timestamp_end,
            "duration": self.duration,
            "hook_element": self.hook_element,
            "dialogue": self.dialogue,
            "action_description": self.action_description,
            "visual_cues": self.visual_cues,
            "emotion": self.emotion,
            "product_focus": self.product_focus,
            "call_to_action": self.call_to_action,
            "word_count": self.word_count
        }


@dataclass
class VideoScript:
    """Complete video script"""
    title: str
    description: str
    script_type: ScriptType
    tone_style: ToneStyle
    platform: PlatformOptimization
    target_duration: float
    hook: str
    segments: List[ScriptSegment]
    closing_cta: str
    hashtags: List[str]
    music_suggestions: List[str]
    
    # Analytics and optimization
    estimated_engagement_score: float
    viral_potential_score: float
    conversion_likelihood: float
    
    @property
    def total_word_count(self) -> int:
        return sum(segment.word_count for segment in self.segments)
    
    @property
    def actual_duration(self) -> float:
        # Estimate based on 150 words per minute average speaking rate
        return (self.total_word_count / 150) * 60
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "title": self.title,
            "description": self.description,
            "script_type": self.script_type.value,
            "tone_style": self.tone_style.value,
            "platform": self.platform.value,
            "target_duration": self.target_duration,
            "hook": self.hook,
            "segments": [segment.to_dict() for segment in self.segments],
            "closing_cta": self.closing_cta,
            "hashtags": self.hashtags,
            "music_suggestions": self.music_suggestions,
            "estimated_engagement_score": self.estimated_engagement_score,
            "viral_potential_score": self.viral_potential_score,
            "conversion_likelihood": self.conversion_likelihood,
            "total_word_count": self.total_word_count,
            "actual_duration": self.actual_duration
        }


@dataclass
class ScriptGenerationRequest:
    """Request for script generation"""
    product: Product
    brand: Optional[Brand] = None
    script_type: ScriptType = ScriptType.PRODUCT_SHOWCASE
    tone_style: ToneStyle = ToneStyle.ENERGETIC
    platform: PlatformOptimization = PlatformOptimization.TIKTOK
    target_duration: float = 30.0
    target_audience: str = "general"
    key_messages: List[str] = None
    competing_products: List[str] = None
    seasonal_context: Optional[str] = None
    trending_topics: List[str] = None
    
    def __post_init__(self):
        if self.key_messages is None:
            self.key_messages = []
        if self.competing_products is None:
            self.competing_products = []
        if self.trending_topics is None:
            self.trending_topics = []


class ScriptGenerationService:
    """Service for generating video scripts from product data"""
    
    def __init__(self):
        self.text_service = None
        
        # Platform-specific constraints
        self.platform_constraints = {
            PlatformOptimization.TIKTOK: {
                "max_duration": 60,
                "hook_duration": 3,
                "optimal_segments": 3,
                "words_per_minute": 180,  # Faster paced
                "engagement_elements": ["trending_sounds", "challenges", "effects"]
            },
            PlatformOptimization.INSTAGRAM: {
                "max_duration": 90,
                "hook_duration": 3,
                "optimal_segments": 4,
                "words_per_minute": 160,
                "engagement_elements": ["aesthetics", "story_arcs", "save_worthy"]
            },
            PlatformOptimization.YOUTUBE_SHORTS: {
                "max_duration": 60,
                "hook_duration": 5,
                "optimal_segments": 4,
                "words_per_minute": 150,
                "engagement_elements": ["educational", "how_to", "problem_solving"]
            },
            PlatformOptimization.YOUTUBE: {
                "max_duration": 300,
                "hook_duration": 10,
                "optimal_segments": 6,
                "words_per_minute": 140,
                "engagement_elements": ["detailed_info", "comparisons", "demonstrations"]
            }
        }
        
        # Script templates for different types
        self.script_templates = {
            ScriptType.PRODUCT_SHOWCASE: self._get_product_showcase_template(),
            ScriptType.UNBOXING: self._get_unboxing_template(),
            ScriptType.PROBLEM_SOLUTION: self._get_problem_solution_template(),
            ScriptType.COMPARISON: self._get_comparison_template(),
            ScriptType.TUTORIAL: self._get_tutorial_template(),
            ScriptType.TESTIMONIAL: self._get_testimonial_template()
        }
    
    async def _get_text_service(self):
        """Get text service instance"""
        if self.text_service is None:
            self.text_service = await get_text_service()
    
    async def generate_script(self, request: ScriptGenerationRequest) -> VideoScript:
        """Generate a complete video script from product data"""
        
        await self._get_text_service()
        
        logger.info(f"Generating {request.script_type.value} script for product: {request.product.name}")
        
        # Extract product insights
        product_insights = await self._analyze_product(request.product, request.brand)
        
        # Generate hook
        hook = await self._generate_hook(request, product_insights)
        
        # Generate script segments
        segments = await self._generate_segments(request, product_insights, hook)
        
        # Generate closing CTA
        closing_cta = await self._generate_closing_cta(request, product_insights)
        
        # Generate supporting elements
        hashtags = await self._generate_hashtags(request, product_insights)
        music_suggestions = await self._suggest_music(request, product_insights)
        
        # Calculate engagement scores
        scores = await self._calculate_engagement_scores(request, segments)
        
        script = VideoScript(
            title=f"{request.script_type.value.title()} - {request.product.name}",
            description=f"AI-generated {request.script_type.value} script for {request.product.name}",
            script_type=request.script_type,
            tone_style=request.tone_style,
            platform=request.platform,
            target_duration=request.target_duration,
            hook=hook,
            segments=segments,
            closing_cta=closing_cta,
            hashtags=hashtags,
            music_suggestions=music_suggestions,
            estimated_engagement_score=scores["engagement"],
            viral_potential_score=scores["viral_potential"],
            conversion_likelihood=scores["conversion"]
        )
        
        logger.info(f"Generated script with {len(segments)} segments, {script.total_word_count} words")
        
        return script
    
    async def _analyze_product(self, product: Product, brand: Optional[Brand]) -> Dict[str, Any]:
        """Analyze product to extract key insights for script generation"""
        
        # Extract product features and benefits
        features = self._extract_features(product.description or "")
        benefits = await self._extract_benefits(product, features)
        
        # Determine unique selling propositions
        usps = await self._identify_usps(product, features, benefits)
        
        # Extract emotional triggers
        emotional_triggers = await self._identify_emotional_triggers(product, brand)
        
        # Analyze pricing and value proposition
        value_proposition = self._analyze_value_proposition(product)
        
        # Extract target audience insights
        audience_insights = await self._analyze_target_audience(product, brand)
        
        return {
            "features": features,
            "benefits": benefits,
            "usps": usps,
            "emotional_triggers": emotional_triggers,
            "value_proposition": value_proposition,
            "audience_insights": audience_insights,
            "product_category": product.category or "general",
            "price_range": self._categorize_price_range(product.price),
            "brand_personality": self._extract_brand_personality(brand) if brand else {}
        }
    
    def _extract_features(self, description: str) -> List[str]:
        """Extract product features from description"""
        
        # Simple feature extraction using keywords and patterns
        feature_patterns = [
            r"(\w+(?:\s+\w+)*)\s+(?:feature|technology|material|design)",
            r"made (?:of|from|with)\s+(\w+(?:\s+\w+)*)",
            r"includes?\s+(\w+(?:\s+\w+)*)",
            r"with\s+(\w+(?:\s+\w+)*)\s+(?:support|capability|function)"
        ]
        
        features = []
        for pattern in feature_patterns:
            matches = re.findall(pattern, description.lower())
            features.extend(matches)
        
        # Also look for bullet points or lists
        lines = description.split('\n')
        for line in lines:
            line = line.strip()
            if line.startswith(('•', '-', '*')) or line.endswith(':'):
                feature = line.lstrip('•-* ').rstrip(':')
                if feature and len(feature.split()) <= 5:  # Keep short features
                    features.append(feature)
        
        # Remove duplicates and clean up
        unique_features = []
        for feature in features:
            if feature not in unique_features and len(feature) > 2:
                unique_features.append(feature.strip())
        
        return unique_features[:10]  # Limit to top 10 features
    
    async def _extract_benefits(self, product: Product, features: List[str]) -> List[str]:
        """Convert features into customer benefits using AI"""
        
        prompt = f"""
        Convert these product features into customer benefits for {product.name}:
        
        Features: {', '.join(features)}
        Product Category: {product.category or 'general'}
        
        For each feature, explain the specific benefit to the customer. Focus on:
        - How it solves a problem
        - What outcome it provides
        - Why the customer should care
        
        Return only the benefits as a bullet-pointed list, maximum 8 benefits.
        """
        
        try:
            response = await self.text_service.generate_response(prompt)
            
            # Extract benefits from response
            benefits = []
            for line in response.split('\n'):
                line = line.strip()
                if line.startswith(('•', '-', '*')):
                    benefit = line.lstrip('•-* ').strip()
                    if benefit:
                        benefits.append(benefit)
            
            return benefits[:8]
            
        except Exception as e:
            logger.error(f"Failed to extract benefits: {e}")
            # Fallback to basic benefit mapping
            return [f"Enhanced {feature}" for feature in features[:5]]
    
    async def _identify_usps(self, product: Product, features: List[str], benefits: List[str]) -> List[str]:
        """Identify unique selling propositions"""
        
        prompt = f"""
        Identify the top 3 unique selling propositions for {product.name}.
        
        Product: {product.name}
        Category: {product.category or 'general'}
        Price: ${product.price or 'N/A'}
        Features: {', '.join(features)}
        Benefits: {', '.join(benefits)}
        
        What makes this product uniquely valuable compared to competitors?
        Focus on:
        - Unique features or capabilities
        - Superior value proposition
        - Distinctive brand positioning
        
        Return exactly 3 USPs as short, punchy statements.
        """
        
        try:
            response = await self.text_service.generate_response(prompt)
            
            usps = []
            for line in response.split('\n'):
                line = line.strip()
                if line and not line.startswith('#') and len(line) > 10:
                    # Clean up numbered lists
                    line = re.sub(r'^\d+[\.\)]\s*', '', line)
                    line = line.lstrip('•-* ').strip()
                    if line:
                        usps.append(line)
            
            return usps[:3]
            
        except Exception as e:
            logger.error(f"Failed to identify USPs: {e}")
            return ["High quality product", "Great value for money", "Trusted brand"]
    
    async def _identify_emotional_triggers(self, product: Product, brand: Optional[Brand]) -> List[str]:
        """Identify emotional triggers for the product"""
        
        category_emotions = {
            "electronics": ["excitement", "innovation", "empowerment"],
            "fashion": ["confidence", "self-expression", "beauty"],
            "home": ["comfort", "security", "pride"],
            "beauty": ["confidence", "self-care", "transformation"],
            "fitness": ["achievement", "health", "strength"],
            "food": ["comfort", "pleasure", "nostalgia"],
            "toys": ["joy", "creativity", "wonder"],
            "automotive": ["freedom", "status", "adventure"]
        }
        
        category = product.category.lower() if product.category else "general"
        emotions = category_emotions.get(category, ["satisfaction", "value", "quality"])
        
        # Add brand-specific emotions if available
        if brand and hasattr(brand, 'brand_voice'):
            brand_voice = getattr(brand, 'brand_voice', {})
            if isinstance(brand_voice, dict):
                brand_emotions = brand_voice.get('emotions', [])
                emotions.extend(brand_emotions)
        
        return list(set(emotions))[:5]  # Return unique emotions, max 5
    
    def _analyze_value_proposition(self, product: Product) -> Dict[str, Any]:
        """Analyze product value proposition"""
        
        price = product.price or 0
        
        if price == 0:
            price_positioning = "unknown"
        elif price < 25:
            price_positioning = "budget-friendly"
        elif price < 100:
            price_positioning = "mid-range"
        elif price < 500:
            price_positioning = "premium"
        else:
            price_positioning = "luxury"
        
        return {
            "price_positioning": price_positioning,
            "value_angle": self._get_value_angle(price_positioning),
            "urgency_factors": self._identify_urgency_factors(product)
        }
    
    def _get_value_angle(self, price_positioning: str) -> str:
        """Get appropriate value angle based on price positioning"""
        
        angles = {
            "budget-friendly": "Incredible value at an unbeatable price",
            "mid-range": "Perfect balance of quality and affordability", 
            "premium": "Investment in quality that pays off",
            "luxury": "Exclusive experience worth every penny",
            "unknown": "Great value for money"
        }
        
        return angles.get(price_positioning, "Great value for money")
    
    def _identify_urgency_factors(self, product: Product) -> List[str]:
        """Identify factors that create urgency to purchase"""
        
        urgency_factors = []
        
        # Check for sale/discount indicators
        if product.discount and product.discount > 0:
            urgency_factors.append(f"{product.discount}% discount available")
        
        # Check description for urgency keywords
        description = (product.description or "").lower()
        urgency_keywords = {
            "limited": "Limited time offer",
            "exclusive": "Exclusive deal",
            "sale": "Special sale price",
            "popular": "High demand item",
            "trending": "Trending product"
        }
        
        for keyword, factor in urgency_keywords.items():
            if keyword in description:
                urgency_factors.append(factor)
        
        return urgency_factors[:3]  # Max 3 urgency factors
    
    async def _analyze_target_audience(self, product: Product, brand: Optional[Brand]) -> Dict[str, Any]:
        """Analyze target audience characteristics"""
        
        # Basic audience inference from product category
        category_audiences = {
            "electronics": {"age": "25-45", "interests": ["technology", "innovation"], "pain_points": ["complexity", "reliability"]},
            "fashion": {"age": "18-35", "interests": ["style", "trends"], "pain_points": ["finding the right fit", "staying current"]},
            "beauty": {"age": "18-50", "interests": ["self-care", "appearance"], "pain_points": ["skin issues", "aging"]},
            "fitness": {"age": "20-40", "interests": ["health", "fitness"], "pain_points": ["lack of motivation", "time constraints"]},
            "home": {"age": "25-55", "interests": ["comfort", "decoration"], "pain_points": ["organization", "space limitations"]}
        }
        
        category = product.category.lower() if product.category else "general"
        audience = category_audiences.get(category, {
            "age": "18-65",
            "interests": ["quality", "value"],
            "pain_points": ["decision making", "value for money"]
        })
        
        return audience
    
    def _categorize_price_range(self, price: Optional[float]) -> str:
        """Categorize product price range"""
        
        if not price or price == 0:
            return "unknown"
        elif price < 25:
            return "under_25"
        elif price < 100:
            return "25_to_100"
        elif price < 500:
            return "100_to_500"
        else:
            return "over_500"
    
    def _extract_brand_personality(self, brand: Brand) -> Dict[str, Any]:
        """Extract brand personality traits"""
        
        if not brand:
            return {}
        
        # Extract from brand guidelines if available
        guidelines = getattr(brand, 'brand_guidelines', {})
        if isinstance(guidelines, dict):
            return {
                "voice": guidelines.get("voice", "friendly"),
                "tone": guidelines.get("tone", "professional"),
                "values": guidelines.get("values", []),
                "personality_traits": guidelines.get("personality", [])
            }
        
        return {"voice": "friendly", "tone": "professional"}
    
    async def _generate_hook(self, request: ScriptGenerationRequest, insights: Dict[str, Any]) -> str:
        """Generate compelling hook for the video"""
        
        platform_constraints = self.platform_constraints[request.platform]
        hook_duration = platform_constraints["hook_duration"]
        
        # Hook templates based on script type
        hook_templates = {
            ScriptType.PRODUCT_SHOWCASE: [
                "What if I told you there's a {product} that {main_benefit}?",
                "This {product} just changed my {lifestyle_area} forever!",
                "You won't believe what this {product} can do...",
                "POV: You finally found the perfect {product}",
                "This is why everyone's obsessed with {product}"
            ],
            ScriptType.PROBLEM_SOLUTION: [
                "Tired of {pain_point}? This will change everything.",
                "Here's how I solved {pain_point} in seconds",
                "If you struggle with {pain_point}, watch this",
                "The {pain_point} solution you've been waiting for"
            ],
            ScriptType.UNBOXING: [
                "Unboxing the {product} everyone's talking about",
                "Is this {product} worth the hype? Let's find out...",
                "Opening the most requested {product}",
                "First impressions of this viral {product}"
            ]
        }
        
        templates = hook_templates.get(request.script_type, hook_templates[ScriptType.PRODUCT_SHOWCASE])
        
        prompt = f"""
        Create a compelling {hook_duration}-second hook for a {request.platform.value} video about {request.product.name}.
        
        Script Type: {request.script_type.value}
        Tone: {request.tone_style.value}
        Target Audience: {request.target_audience}
        
        Product Insights:
        - Main Benefits: {', '.join(insights['benefits'][:3])}
        - USPs: {', '.join(insights['usps'])}
        - Emotional Triggers: {', '.join(insights['emotional_triggers'])}
        
        Template Options: {templates}
        
        Requirements:
        - Must grab attention in first 3 seconds
        - Should be {request.tone_style.value} in tone
        - Must be platform-appropriate for {request.platform.value}
        - Include emotional trigger or curiosity gap
        
        Return only the hook text, no explanations.
        """
        
        try:
            hook = await self.text_service.generate_response(prompt)
            return hook.strip().strip('"\'')
            
        except Exception as e:
            logger.error(f"Failed to generate hook: {e}")
            # Fallback hook
            return f"You need to see this {request.product.name}!"
    
    async def _generate_segments(
        self, 
        request: ScriptGenerationRequest, 
        insights: Dict[str, Any], 
        hook: str
    ) -> List[ScriptSegment]:
        """Generate script segments"""
        
        platform_constraints = self.platform_constraints[request.platform]
        optimal_segments = platform_constraints["optimal_segments"]
        words_per_minute = platform_constraints["words_per_minute"]
        
        # Calculate timing
        hook_duration = platform_constraints["hook_duration"]
        remaining_duration = request.target_duration - hook_duration - 3  # 3 seconds for CTA
        segment_duration = remaining_duration / optimal_segments
        
        template = self.script_templates.get(request.script_type)
        if not template:
            template = self.script_templates[ScriptType.PRODUCT_SHOWCASE]
        
        segments = []
        current_time = hook_duration
        
        for i in range(optimal_segments):
            segment_prompt = template["segments"][i % len(template["segments"])]
            
            # Customize prompt with product insights
            customized_prompt = segment_prompt.format(
                product=request.product.name,
                benefits=insights["benefits"],
                usps=insights["usps"],
                emotional_triggers=insights["emotional_triggers"],
                target_audience=request.target_audience,
                tone=request.tone_style.value
            )
            
            segment = await self._generate_single_segment(
                customized_prompt,
                i + 1,
                current_time,
                current_time + segment_duration,
                request,
                insights
            )
            
            segments.append(segment)
            current_time += segment_duration
        
        return segments
    
    async def _generate_single_segment(
        self,
        segment_prompt: str,
        segment_number: int,
        start_time: float,
        end_time: float,
        request: ScriptGenerationRequest,
        insights: Dict[str, Any]
    ) -> ScriptSegment:
        """Generate a single script segment"""
        
        duration = end_time - start_time
        target_words = int((duration / 60) * self.platform_constraints[request.platform]["words_per_minute"])
        
        prompt = f"""
        {segment_prompt}
        
        Requirements:
        - Duration: {duration:.1f} seconds
        - Target words: {target_words}
        - Tone: {request.tone_style.value}
        - Platform: {request.platform.value}
        
        Include:
        1. Dialogue (what to say)
        2. Action description (what to show)
        3. Visual cues (camera angles, effects)
        4. Emotion to convey
        5. Product focus point
        
        Format as JSON:
        {{
            "dialogue": "...",
            "action_description": "...",
            "visual_cues": ["..."],
            "emotion": "...",
            "product_focus": "..."
        }}
        """
        
        try:
            response = await self.text_service.generate_response(prompt)
            
            # Parse JSON response
            try:
                segment_data = json.loads(response)
            except json.JSONDecodeError:
                # Fallback parsing
                segment_data = self._parse_segment_response(response)
            
            return ScriptSegment(
                segment_number=segment_number,
                timestamp_start=start_time,
                timestamp_end=end_time,
                duration=duration,
                hook_element=self._identify_hook_element(segment_data, request.platform),
                dialogue=segment_data.get("dialogue", ""),
                action_description=segment_data.get("action_description", ""),
                visual_cues=segment_data.get("visual_cues", []),
                emotion=segment_data.get("emotion", "neutral"),
                product_focus=segment_data.get("product_focus"),
                call_to_action=None  # Will be added to final segment
            )
            
        except Exception as e:
            logger.error(f"Failed to generate segment {segment_number}: {e}")
            
            # Fallback segment
            return ScriptSegment(
                segment_number=segment_number,
                timestamp_start=start_time,
                timestamp_end=end_time,
                duration=duration,
                hook_element="product_feature",
                dialogue=f"Here's what makes {request.product.name} special...",
                action_description="Show product close-up",
                visual_cues=["close-up shot", "good lighting"],
                emotion="enthusiastic",
                product_focus=request.product.name,
                call_to_action=None
            )
    
    def _parse_segment_response(self, response: str) -> Dict[str, Any]:
        """Parse segment response when JSON parsing fails"""
        
        segment_data = {
            "dialogue": "",
            "action_description": "",
            "visual_cues": [],
            "emotion": "neutral",
            "product_focus": ""
        }
        
        lines = response.split('\n')
        current_field = None
        
        for line in lines:
            line = line.strip()
            
            if line.lower().startswith('dialogue:'):
                current_field = 'dialogue'
                segment_data['dialogue'] = line[9:].strip()
            elif line.lower().startswith('action:'):
                current_field = 'action_description'
                segment_data['action_description'] = line[7:].strip()
            elif line.lower().startswith('visual:'):
                current_field = 'visual_cues'
                segment_data['visual_cues'] = [line[7:].strip()]
            elif line.lower().startswith('emotion:'):
                segment_data['emotion'] = line[8:].strip()
            elif line.lower().startswith('product:'):
                segment_data['product_focus'] = line[8:].strip()
            elif current_field and line:
                # Continue previous field
                if current_field == 'visual_cues':
                    segment_data['visual_cues'].append(line)
                else:
                    segment_data[current_field] += " " + line
        
        return segment_data
    
    def _identify_hook_element(self, segment_data: Dict[str, Any], platform: PlatformOptimization) -> str:
        """Identify the hook element for the segment"""
        
        platform_hooks = {
            PlatformOptimization.TIKTOK: ["transition", "effect", "trending_sound", "reveal"],
            PlatformOptimization.INSTAGRAM: ["aesthetic_shot", "transformation", "before_after"],
            PlatformOptimization.YOUTUBE_SHORTS: ["education", "demonstration", "tip"],
            PlatformOptimization.YOUTUBE: ["detailed_explanation", "comparison", "analysis"]
        }
        
        hooks = platform_hooks.get(platform, ["product_feature"])
        
        # Analyze segment content to determine best hook
        action = segment_data.get("action_description", "").lower()
        
        if "show" in action or "reveal" in action:
            return "reveal"
        elif "compare" in action or "vs" in action:
            return "comparison"
        elif "demonstrate" in action or "use" in action:
            return "demonstration"
        else:
            return hooks[0]
    
    async def _generate_closing_cta(self, request: ScriptGenerationRequest, insights: Dict[str, Any]) -> str:
        """Generate closing call-to-action"""
        
        platform_ctas = {
            PlatformOptimization.TIKTOK: [
                "Follow for more product reviews!",
                "Double tap if you want this!",
                "Comment 'NEED' if you're buying this!",
                "Share this with someone who needs it!"
            ],
            PlatformOptimization.INSTAGRAM: [
                "Save this post for later!",
                "Share this in your story!",
                "Follow for more product finds!",
                "Tag someone who would love this!"
            ],
            PlatformOptimization.YOUTUBE_SHORTS: [
                "Subscribe for more reviews!",
                "Like if this was helpful!",
                "Subscribe and hit the bell!",
                "What should I review next?"
            ],
            PlatformOptimization.YOUTUBE: [
                "Like and subscribe for more detailed reviews!",
                "Check the description for links!",
                "Subscribe for weekly product reviews!",
                "What product should I cover next? Comment below!"
            ]
        }
        
        ctas = platform_ctas.get(request.platform, platform_ctas[PlatformOptimization.TIKTOK])
        
        # Add purchase urgency if applicable
        urgency_factors = insights["value_proposition"]["urgency_factors"]
        if urgency_factors:
            purchase_cta = f"Get yours now - {urgency_factors[0]}! Link in bio."
            return f"{ctas[0]} {purchase_cta}"
        
        return ctas[0]
    
    async def _generate_hashtags(self, request: ScriptGenerationRequest, insights: Dict[str, Any]) -> List[str]:
        """Generate relevant hashtags"""
        
        hashtags = []
        
        # Product-specific hashtags
        product_name = request.product.name.replace(" ", "").lower()
        hashtags.append(f"#{product_name}")
        
        # Category hashtags
        if request.product.category:
            hashtags.append(f"#{request.product.category.lower()}")
        
        # Platform-specific hashtags
        platform_hashtags = {
            PlatformOptimization.TIKTOK: ["#fyp", "#viral", "#musthave", "#trending"],
            PlatformOptimization.INSTAGRAM: ["#insta", "#discover", "#explore", "#lifestyle"],
            PlatformOptimization.YOUTUBE_SHORTS: ["#shorts", "#review", "#recommendation"],
            PlatformOptimization.YOUTUBE: ["#review", "#productreview", "#recommendation"]
        }
        
        hashtags.extend(platform_hashtags.get(request.platform, []))
        
        # Add emotional and benefit hashtags
        for trigger in insights["emotional_triggers"][:2]:
            hashtags.append(f"#{trigger.replace(' ', '')}")
        
        # Add trending topics if provided
        for topic in request.trending_topics[:2]:
            hashtags.append(f"#{topic.replace(' ', '')}")
        
        return hashtags[:15]  # Limit to 15 hashtags
    
    async def _suggest_music(self, request: ScriptGenerationRequest, insights: Dict[str, Any]) -> List[str]:
        """Suggest appropriate music for the video"""
        
        # Music suggestions based on tone and platform
        tone_music = {
            ToneStyle.ENERGETIC: ["upbeat pop", "electronic dance", "motivational"],
            ToneStyle.PROFESSIONAL: ["corporate", "ambient", "light instrumental"],
            ToneStyle.CASUAL: ["acoustic", "indie pop", "chill"],
            ToneStyle.ENTHUSIASTIC: ["uplifting", "positive pop", "energetic"],
            ToneStyle.EDUCATIONAL: ["soft instrumental", "ambient", "focus music"],
            ToneStyle.HUMOROUS: ["playful", "quirky", "light comedy"]
        }
        
        platform_music = {
            PlatformOptimization.TIKTOK: ["trending sounds", "viral audio", "popular songs"],
            PlatformOptimization.INSTAGRAM: ["aesthetic music", "indie tracks", "trendy beats"],
            PlatformOptimization.YOUTUBE: ["royalty-free", "background music", "instrumental"]
        }
        
        suggestions = []
        suggestions.extend(tone_music.get(request.tone_style, ["upbeat"]))
        suggestions.extend(platform_music.get(request.platform, ["background music"]))
        
        return list(set(suggestions))[:5]  # Return unique suggestions, max 5
    
    async def _calculate_engagement_scores(self, request: ScriptGenerationRequest, segments: List[ScriptSegment]) -> Dict[str, float]:
        """Calculate predicted engagement scores"""
        
        # Simple scoring algorithm - in production would use ML models
        engagement_score = 0.7  # Base score
        viral_potential = 0.5
        conversion_likelihood = 0.6
        
        # Platform bonuses
        platform_bonuses = {
            PlatformOptimization.TIKTOK: {"engagement": 0.1, "viral": 0.2},
            PlatformOptimization.INSTAGRAM: {"engagement": 0.05, "viral": 0.1},
            PlatformOptimization.YOUTUBE_SHORTS: {"engagement": 0.08, "viral": 0.15}
        }
        
        bonus = platform_bonuses.get(request.platform, {"engagement": 0, "viral": 0})
        engagement_score += bonus["engagement"]
        viral_potential += bonus["viral"]
        
        # Hook quality bonus
        if any(word in request.product.name.lower() for word in ["new", "limited", "exclusive"]):
            engagement_score += 0.1
            viral_potential += 0.1
        
        # Duration optimization
        optimal_duration = self.platform_constraints[request.platform]["max_duration"] * 0.7
        if abs(request.target_duration - optimal_duration) < 10:
            engagement_score += 0.05
        
        # Ensure scores are within valid range
        engagement_score = min(1.0, max(0.0, engagement_score))
        viral_potential = min(1.0, max(0.0, viral_potential))
        conversion_likelihood = min(1.0, max(0.0, conversion_likelihood))
        
        return {
            "engagement": engagement_score,
            "viral_potential": viral_potential,
            "conversion": conversion_likelihood
        }
    
    # Script templates
    
    def _get_product_showcase_template(self) -> Dict[str, Any]:
        """Get product showcase script template"""
        return {
            "segments": [
                "Open with the {product} in action, showing its most impressive feature. Use {emotional_triggers[0]} tone.",
                "Highlight the main {benefits[0]} and why it matters to {target_audience}.",
                "Demonstrate another key feature with clear before/after or comparison.",
                "Address common concerns and show how {product} solves them uniquely."
            ]
        }
    
    def _get_unboxing_template(self) -> Dict[str, Any]:
        """Get unboxing script template"""
        return {
            "segments": [
                "Start with excitement about receiving {product}. Show the packaging and first impressions.",
                "Reveal the product and immediate reaction. Point out design details and build quality.",
                "Go through included accessories and items. Explain what each does.",
                "First use/test of the product. Share honest initial thoughts and reactions."
            ]
        }
    
    def _get_problem_solution_template(self) -> Dict[str, Any]:
        """Get problem-solution script template"""
        return {
            "segments": [
                "Start by relating to the common problem that {target_audience} faces daily.",
                "Introduce {product} as the solution. Show how it directly addresses the problem.",
                "Demonstrate the product solving the problem in real-time.",
                "Highlight additional benefits and why this solution is better than alternatives."
            ]
        }
    
    def _get_comparison_template(self) -> Dict[str, Any]:
        """Get comparison script template"""
        return {
            "segments": [
                "Set up the comparison: {product} vs other options in the market.",
                "Compare key features side-by-side. Focus on {usps[0]}.",
                "Show real-world performance differences with demonstrations.",
                "Conclude with why {product} is the clear winner for {target_audience}."
            ]
        }
    
    def _get_tutorial_template(self) -> Dict[str, Any]:
        """Get tutorial script template"""
        return {
            "segments": [
                "Introduce what you'll teach and why {product} is perfect for this tutorial.",
                "Step 1: Basic setup and preparation with {product}.",
                "Step 2: Main technique or process using {product} features.",
                "Final result and pro tips for getting the best outcome with {product}."
            ]
        }
    
    def _get_testimonial_template(self) -> Dict[str, Any]:
        """Get testimonial script template"""
        return {
            "segments": [
                "Share personal story of why you needed {product} and initial skepticism.",
                "Describe the first time using {product} and immediate results.",
                "Explain how {product} has improved your life over time.",
                "Give honest recommendation and who would benefit most from {product}."
            ]
        }


# Global service instance
_script_generation_service: Optional[ScriptGenerationService] = None


def get_script_generation_service() -> ScriptGenerationService:
    """Get global script generation service instance"""
    global _script_generation_service
    if _script_generation_service is None:
        _script_generation_service = ScriptGenerationService()
    return _script_generation_service