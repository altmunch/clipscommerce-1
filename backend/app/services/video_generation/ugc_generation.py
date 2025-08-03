"""
UGC (User-Generated Content) generation service for creating authentic testimonial videos from text reviews
"""

import asyncio
import json
import logging
import random
import uuid
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass
from enum import Enum
import re

from app.core.config import settings
from app.services.ai.providers import get_text_service
from app.models.product import Product
from .providers import DIDProvider, HeyGenProvider, SynthesiaProvider
from .text_to_speech import get_tts_service, VoiceSettings, EmotionType

logger = logging.getLogger(__name__)


class AvatarGender(Enum):
    """Avatar gender options"""
    MALE = "male"
    FEMALE = "female"
    NON_BINARY = "non_binary"


class AvatarEthnicity(Enum):
    """Avatar ethnicity options"""
    CAUCASIAN = "caucasian"
    AFRICAN_AMERICAN = "african_american"
    HISPANIC = "hispanic"
    ASIAN = "asian"
    MIDDLE_EASTERN = "middle_eastern"
    MIXED = "mixed"


class AvatarAgeRange(Enum):
    """Avatar age ranges"""
    YOUNG_ADULT = "20-30"
    ADULT = "30-40"
    MIDDLE_AGED = "40-50"
    MATURE = "50-60"


class TestimonialType(Enum):
    """Types of testimonials"""
    PRODUCT_REVIEW = "product_review"
    UNBOXING_REACTION = "unboxing_reaction"
    BEFORE_AFTER = "before_after"
    COMPARISON = "comparison"
    LIFESTYLE_INTEGRATION = "lifestyle_integration"
    PROBLEM_SOLVED = "problem_solved"


class AuthenticityLevel(Enum):
    """Levels of authenticity for UGC"""
    HIGHLY_AUTHENTIC = "highly_authentic"    # Very natural, includes hesitations, filler words
    MODERATELY_AUTHENTIC = "moderately_authentic"  # Some natural elements
    POLISHED = "polished"                    # Clean, professional but still personal


@dataclass
class ReviewData:
    """Structured review data"""
    original_text: str
    rating: float
    reviewer_name: Optional[str]
    review_source: str  # "amazon", "google", "yelp", "manual", etc.
    sentiment: str      # "positive", "negative", "neutral"
    key_points: List[str]
    emotions: List[str]
    product_benefits_mentioned: List[str]
    pain_points_addressed: List[str]
    credibility_score: float  # 0.0 to 1.0


@dataclass
class AvatarProfile:
    """Avatar characteristics"""
    avatar_id: str
    gender: AvatarGender
    ethnicity: AvatarEthnicity
    age_range: AvatarAgeRange
    personality_traits: List[str]
    voice_characteristics: str
    background_story: str
    interests: List[str]
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "avatar_id": self.avatar_id,
            "gender": self.gender.value,
            "ethnicity": self.ethnicity.value,
            "age_range": self.age_range.value,
            "personality_traits": self.personality_traits,
            "voice_characteristics": self.voice_characteristics,
            "background_story": self.background_story,
            "interests": self.interests
        }


@dataclass
class TestimonialScript:
    """Generated testimonial script"""
    script_text: str
    emotion_markers: List[Dict[str, Any]]  # Timing and emotion changes
    emphasis_points: List[Dict[str, Any]]   # Words/phrases to emphasize
    pause_points: List[float]               # Timing for natural pauses
    authenticity_elements: List[str]        # Filler words, hesitations
    estimated_duration: float
    credibility_score: float
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "script_text": self.script_text,
            "emotion_markers": self.emotion_markers,
            "emphasis_points": self.emphasis_points,
            "pause_points": self.pause_points,
            "authenticity_elements": self.authenticity_elements,
            "estimated_duration": self.estimated_duration,
            "credibility_score": self.credibility_score
        }


@dataclass
class UGCGenerationRequest:
    """Request for UGC testimonial generation"""
    product: Product
    review_data: ReviewData
    testimonial_type: TestimonialType = TestimonialType.PRODUCT_REVIEW
    authenticity_level: AuthenticityLevel = AuthenticityLevel.MODERATELY_AUTHENTIC
    target_duration: float = 30.0
    target_audience: str = "general"
    avatar_preferences: Optional[Dict[str, Any]] = None
    brand_guidelines: Optional[Dict[str, Any]] = None
    
    def __post_init__(self):
        if self.avatar_preferences is None:
            self.avatar_preferences = {}
        if self.brand_guidelines is None:
            self.brand_guidelines = {}


@dataclass
class UGCGenerationResult:
    """Result of UGC generation"""
    testimonial_id: str
    avatar_profile: AvatarProfile
    testimonial_script: TestimonialScript
    video_url: Optional[str]
    audio_url: Optional[str]
    generation_metadata: Dict[str, Any]
    cost: float
    generation_time: float
    quality_score: float
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "testimonial_id": self.testimonial_id,
            "avatar_profile": self.avatar_profile.to_dict(),
            "testimonial_script": self.testimonial_script.to_dict(),
            "video_url": self.video_url,
            "audio_url": self.audio_url,
            "generation_metadata": self.generation_metadata,
            "cost": self.cost,
            "generation_time": self.generation_time,
            "quality_score": self.quality_score
        }


class UGCGenerationService:
    """Service for generating authentic UGC testimonials from reviews"""
    
    def __init__(self):
        self.text_service = None
        self.tts_service = get_tts_service()
        
        # Avatar providers
        self.avatar_providers = {
            "did": DIDProvider(),
            "heygen": HeyGenProvider(),
            "synthesia": SynthesiaProvider()
        }
        
        # Pre-defined avatar profiles for different demographics
        self.avatar_profiles = self._initialize_avatar_profiles()
        
        # Authenticity templates and patterns
        self.authenticity_patterns = {
            AuthenticityLevel.HIGHLY_AUTHENTIC: {
                "filler_words": ["um", "uh", "like", "you know", "so", "actually", "honestly"],
                "hesitation_phrases": ["I mean", "well", "let me think", "how do I put this"],
                "natural_transitions": ["but anyway", "oh and", "also", "one more thing"],
                "emphasis_patterns": ["really", "super", "totally", "absolutely", "definitely"]
            },
            AuthenticityLevel.MODERATELY_AUTHENTIC: {
                "filler_words": ["so", "actually", "honestly"],
                "hesitation_phrases": ["I mean", "well"],
                "natural_transitions": ["and", "also", "plus"],
                "emphasis_patterns": ["really", "definitely"]
            },
            AuthenticityLevel.POLISHED: {
                "filler_words": [],
                "hesitation_phrases": [],
                "natural_transitions": ["and", "also", "furthermore", "additionally"],
                "emphasis_patterns": ["particularly", "especially", "notably"]
            }
        }
    
    async def _get_text_service(self):
        """Get text service instance"""
        if self.text_service is None:
            self.text_service = await get_text_service()
    
    def _initialize_avatar_profiles(self) -> List[AvatarProfile]:
        """Initialize diverse avatar profiles"""
        
        profiles = []
        
        # Create diverse set of avatars
        avatar_configs = [
            {
                "gender": AvatarGender.FEMALE,
                "ethnicity": AvatarEthnicity.CAUCASIAN,
                "age_range": AvatarAgeRange.YOUNG_ADULT,
                "personality": ["enthusiastic", "friendly", "optimistic"],
                "voice": "bright, clear, energetic",
                "background": "college student, loves trying new products",
                "interests": ["fashion", "beauty", "lifestyle"]
            },
            {
                "gender": AvatarGender.MALE,
                "ethnicity": AvatarEthnicity.AFRICAN_AMERICAN,
                "age_range": AvatarAgeRange.ADULT,
                "personality": ["confident", "analytical", "trustworthy"],
                "voice": "deep, calm, authoritative",
                "background": "working professional, tech enthusiast",
                "interests": ["technology", "fitness", "productivity"]
            },
            {
                "gender": AvatarGender.FEMALE,
                "ethnicity": AvatarEthnicity.HISPANIC,
                "age_range": AvatarAgeRange.MIDDLE_AGED,
                "personality": ["warm", "practical", "family-oriented"],
                "voice": "warm, caring, experienced",
                "background": "mother of two, values quality and value",
                "interests": ["family", "home", "health"]
            },
            {
                "gender": AvatarGender.MALE,
                "ethnicity": AvatarEthnicity.ASIAN,
                "age_range": AvatarAgeRange.YOUNG_ADULT,
                "personality": ["detail-oriented", "innovative", "efficient"],
                "voice": "clear, measured, intelligent",
                "background": "graduate student, early adopter",
                "interests": ["technology", "education", "innovation"]
            },
            {
                "gender": AvatarGender.FEMALE,
                "ethnicity": AvatarEthnicity.MIDDLE_EASTERN,
                "age_range": AvatarAgeRange.ADULT,
                "personality": ["sophisticated", "discerning", "articulate"],
                "voice": "elegant, articulate, confident",
                "background": "business professional, values quality",
                "interests": ["business", "luxury", "culture"]
            }
        ]
        
        for i, config in enumerate(avatar_configs):
            profile = AvatarProfile(
                avatar_id=f"avatar_{i+1}",
                gender=config["gender"],
                ethnicity=config["ethnicity"],
                age_range=config["age_range"],
                personality_traits=config["personality"],
                voice_characteristics=config["voice"],
                background_story=config["background"],
                interests=config["interests"]
            )
            profiles.append(profile)
        
        return profiles
    
    async def generate_ugc_testimonial(self, request: UGCGenerationRequest) -> UGCGenerationResult:
        """Generate complete UGC testimonial from review data"""
        
        await self._get_text_service()
        
        logger.info(f"Generating UGC testimonial for product: {request.product.name}")
        
        start_time = asyncio.get_event_loop().time()
        
        # Select appropriate avatar based on review and preferences
        avatar_profile = await self._select_avatar(request)
        
        # Analyze and process the review
        processed_review = await self._analyze_review(request.review_data, request.product)
        
        # Generate authentic testimonial script
        testimonial_script = await self._generate_testimonial_script(
            request, processed_review, avatar_profile
        )
        
        # Generate avatar video
        video_result = await self._generate_avatar_video(
            testimonial_script, avatar_profile, request
        )
        
        generation_time = asyncio.get_event_loop().time() - start_time
        
        # Calculate quality score
        quality_score = await self._calculate_quality_score(
            testimonial_script, avatar_profile, processed_review
        )
        
        testimonial_id = str(uuid.uuid4())
        
        result = UGCGenerationResult(
            testimonial_id=testimonial_id,
            avatar_profile=avatar_profile,
            testimonial_script=testimonial_script,
            video_url=video_result.get("video_url"),
            audio_url=video_result.get("audio_url"),
            generation_metadata={
                "provider": video_result.get("provider"),
                "model_version": video_result.get("model_version"),
                "processing_steps": [
                    "review_analysis",
                    "avatar_selection", 
                    "script_generation",
                    "video_generation"
                ]
            },
            cost=video_result.get("cost", 0.0),
            generation_time=generation_time,
            quality_score=quality_score
        )
        
        logger.info(f"Generated UGC testimonial {testimonial_id} in {generation_time:.1f}s")
        
        return result
    
    async def _select_avatar(self, request: UGCGenerationRequest) -> AvatarProfile:
        """Select appropriate avatar based on review characteristics and preferences"""
        
        # Filter avatars based on preferences
        suitable_avatars = []
        
        for avatar in self.avatar_profiles:
            # Check gender preference
            if request.avatar_preferences.get("gender"):
                if avatar.gender.value != request.avatar_preferences["gender"]:
                    continue
            
            # Check age preference
            if request.avatar_preferences.get("age_range"):
                if avatar.age_range.value != request.avatar_preferences["age_range"]:
                    continue
            
            # Check if avatar interests align with product category
            product_category = request.product.category or "general"
            if product_category.lower() in [interest.lower() for interest in avatar.interests]:
                suitable_avatars.append((avatar, 1.0))  # Perfect match
            else:
                suitable_avatars.append((avatar, 0.7))  # Partial match
        
        if not suitable_avatars:
            suitable_avatars = [(avatar, 0.5) for avatar in self.avatar_profiles]
        
        # Select avatar with highest match score, with some randomization
        suitable_avatars.sort(key=lambda x: x[1], reverse=True)
        
        # Select from top 3 matches to add variety
        top_matches = suitable_avatars[:3]
        selected_avatar, _ = random.choice(top_matches)
        
        logger.info(f"Selected avatar: {selected_avatar.avatar_id} ({selected_avatar.gender.value}, {selected_avatar.age_range.value})")
        
        return selected_avatar
    
    async def _analyze_review(self, review_data: ReviewData, product: Product) -> ReviewData:
        """Analyze and enrich review data"""
        
        # Extract key points if not already done
        if not review_data.key_points:
            key_points = await self._extract_key_points(review_data.original_text)
            review_data.key_points = key_points
        
        # Extract emotions if not already done
        if not review_data.emotions:
            emotions = await self._extract_emotions(review_data.original_text)
            review_data.emotions = emotions
        
        # Extract product benefits mentioned
        if not review_data.product_benefits_mentioned:
            benefits = await self._extract_product_benefits(review_data.original_text, product)
            review_data.product_benefits_mentioned = benefits
        
        # Calculate credibility score if not set
        if review_data.credibility_score == 0.0:
            credibility = await self._calculate_credibility_score(review_data)
            review_data.credibility_score = credibility
        
        return review_data
    
    async def _extract_key_points(self, review_text: str) -> List[str]:
        """Extract key points from review text"""
        
        prompt = f"""
        Extract the 3-5 most important points from this product review:
        
        "{review_text}"
        
        Focus on:
        - Specific product features mentioned
        - Benefits or problems solved
        - User experience highlights
        - Value propositions
        
        Return as a bullet-pointed list, maximum 5 points.
        """
        
        try:
            response = await self.text_service.generate_response(prompt)
            
            # Parse bullet points
            points = []
            for line in response.split('\n'):
                line = line.strip()
                if line.startswith(('•', '-', '*', '1.', '2.', '3.', '4.', '5.')):
                    point = line.lstrip('•-*123456789. ').strip()
                    if point:
                        points.append(point)
            
            return points[:5]
            
        except Exception as e:
            logger.error(f"Failed to extract key points: {e}")
            # Fallback: simple sentence splitting
            sentences = review_text.split('. ')
            return sentences[:3]
    
    async def _extract_emotions(self, review_text: str) -> List[str]:
        """Extract emotions from review text"""
        
        # Simple emotion detection based on keywords
        emotion_keywords = {
            "happy": ["happy", "love", "amazing", "fantastic", "wonderful", "great", "excellent"],
            "excited": ["excited", "thrilled", "impressed", "wow", "incredible", "outstanding"],
            "satisfied": ["satisfied", "pleased", "good", "solid", "reliable", "works"],
            "surprised": ["surprised", "unexpected", "didn't expect", "blown away"],
            "disappointed": ["disappointed", "expected better", "not what I thought"],
            "frustrated": ["frustrated", "annoying", "difficult", "hard to use"],
            "grateful": ["grateful", "thankful", "appreciate", "helped me"]
        }
        
        text_lower = review_text.lower()
        detected_emotions = []
        
        for emotion, keywords in emotion_keywords.items():
            if any(keyword in text_lower for keyword in keywords):
                detected_emotions.append(emotion)
        
        return detected_emotions[:3]  # Return top 3 emotions
    
    async def _extract_product_benefits(self, review_text: str, product: Product) -> List[str]:
        """Extract product benefits mentioned in review"""
        
        prompt = f"""
        From this review of "{product.name}", extract the specific benefits the user experienced:
        
        "{review_text}"
        
        Focus on:
        - How the product helped solve a problem
        - What improvements the user noticed
        - Specific value delivered
        
        Return as a simple list, maximum 4 benefits.
        """
        
        try:
            response = await self.text_service.generate_response(prompt)
            
            # Parse benefits
            benefits = []
            for line in response.split('\n'):
                line = line.strip()
                if line and not line.startswith('#'):
                    # Clean up numbered lists
                    line = re.sub(r'^\d+[\.\)]\s*', '', line)
                    line = line.lstrip('•-* ').strip()
                    if line:
                        benefits.append(line)
            
            return benefits[:4]
            
        except Exception as e:
            logger.error(f"Failed to extract benefits: {e}")
            return ["Quality product", "Good value"]
    
    async def _calculate_credibility_score(self, review_data: ReviewData) -> float:
        """Calculate credibility score for review"""
        
        score = 0.5  # Base score
        
        # Length factor (longer reviews are generally more credible)
        word_count = len(review_data.original_text.split())
        if word_count > 50:
            score += 0.2
        elif word_count > 20:
            score += 0.1
        
        # Specificity factor (specific details increase credibility)
        specific_keywords = ["exactly", "specifically", "after", "before", "days", "weeks", "months"]
        specificity_count = sum(1 for keyword in specific_keywords if keyword in review_data.original_text.lower())
        score += min(0.2, specificity_count * 0.05)
        
        # Balance factor (mentions both pros and cons)
        positive_words = ["good", "great", "love", "excellent", "amazing"]
        negative_words = ["but", "however", "although", "wish", "could be better"]
        
        has_positive = any(word in review_data.original_text.lower() for word in positive_words)
        has_caveats = any(word in review_data.original_text.lower() for word in negative_words)
        
        if has_positive and has_caveats:
            score += 0.1  # Balanced reviews are more credible
        
        # Rating consistency (extreme ratings with moderate language, or vice versa, reduce credibility)
        if review_data.rating:
            if review_data.rating >= 4.0 and has_positive:
                score += 0.1
            elif review_data.rating <= 2.0 and not has_positive:
                score += 0.1
        
        return min(1.0, max(0.0, score))
    
    async def _generate_testimonial_script(
        self, 
        request: UGCGenerationRequest,
        review_data: ReviewData,
        avatar_profile: AvatarProfile
    ) -> TestimonialScript:
        """Generate authentic testimonial script"""
        
        authenticity_patterns = self.authenticity_patterns[request.authenticity_level]
        
        # Create personality-informed prompt
        personality_context = f"Avatar personality: {', '.join(avatar_profile.personality_traits)}"
        background_context = f"Avatar background: {avatar_profile.background_story}"
        
        prompt = f"""
        Create an authentic {request.testimonial_type.value} testimonial script based on this review:
        
        Original Review: "{review_data.original_text}"
        Product: {request.product.name}
        Rating: {review_data.rating}/5
        Key Points: {', '.join(review_data.key_points)}
        
        {personality_context}
        {background_context}
        
        Requirements:
        - Target duration: {request.target_duration} seconds
        - Authenticity level: {request.authenticity_level.value}
        - Sound like a real person, not a commercial
        - Include personal experience and specific details
        - Match the avatar's personality and background
        
        {"Include natural speech patterns: " + ", ".join(authenticity_patterns["filler_words"][:3]) if authenticity_patterns["filler_words"] else "Keep speech polished and clear"}
        
        Structure:
        1. Natural opening/introduction
        2. Share personal experience with the product
        3. Mention specific benefits/results
        4. Authentic recommendation
        
        Return only the script text, first person perspective.
        """
        
        try:
            script_text = await self.text_service.generate_response(prompt)
            script_text = script_text.strip().strip('"\'')
            
            # Add authenticity elements
            script_text = await self._add_authenticity_elements(
                script_text, authenticity_patterns, request.authenticity_level
            )
            
            # Generate emotion markers and emphasis points
            emotion_markers = await self._generate_emotion_markers(script_text, review_data.emotions)
            emphasis_points = await self._identify_emphasis_points(script_text, review_data.key_points)
            pause_points = self._identify_pause_points(script_text)
            
            # Calculate estimated duration
            word_count = len(script_text.split())
            estimated_duration = (word_count / 150) * 60  # 150 words per minute average
            
            return TestimonialScript(
                script_text=script_text,
                emotion_markers=emotion_markers,
                emphasis_points=emphasis_points,
                pause_points=pause_points,
                authenticity_elements=authenticity_patterns["filler_words"] + authenticity_patterns["hesitation_phrases"],
                estimated_duration=estimated_duration,
                credibility_score=review_data.credibility_score
            )
            
        except Exception as e:
            logger.error(f"Failed to generate testimonial script: {e}")
            # Fallback script
            return TestimonialScript(
                script_text=f"I recently tried {request.product.name} and I have to say, I'm really impressed. {review_data.original_text[:100]}... I would definitely recommend this to others.",
                emotion_markers=[],
                emphasis_points=[],
                pause_points=[5.0, 15.0],
                authenticity_elements=[],
                estimated_duration=20.0,
                credibility_score=0.7
            )
    
    async def _add_authenticity_elements(
        self,
        script_text: str,
        patterns: Dict[str, List[str]],
        authenticity_level: AuthenticityLevel
    ) -> str:
        """Add natural speech patterns to make script more authentic"""
        
        if authenticity_level == AuthenticityLevel.POLISHED:
            return script_text
        
        # Add filler words at natural break points
        sentences = script_text.split('. ')
        
        for i, sentence in enumerate(sentences):
            # Randomly add authenticity elements
            if random.random() < 0.3 and patterns["filler_words"]:  # 30% chance
                filler = random.choice(patterns["filler_words"])
                # Add filler word at the beginning of some sentences
                if not sentence.strip().startswith(tuple(patterns["filler_words"])):
                    sentences[i] = f"{filler}, {sentence}"
            
            # Add hesitation phrases occasionally
            if random.random() < 0.2 and patterns["hesitation_phrases"]:  # 20% chance
                hesitation = random.choice(patterns["hesitation_phrases"])
                sentences[i] = sentence.replace(', ', f', {hesitation}, ', 1)
        
        return '. '.join(sentences)
    
    async def _generate_emotion_markers(self, script_text: str, emotions: List[str]) -> List[Dict[str, Any]]:
        """Generate emotion timing markers for the script"""
        
        markers = []
        words = script_text.split()
        total_words = len(words)
        
        # Map emotions to timing
        for i, emotion in enumerate(emotions[:3]):  # Max 3 emotion changes
            # Distribute emotions across the script
            word_position = int((i + 1) * total_words / (len(emotions) + 1))
            time_position = (word_position / total_words) * 30  # Assuming 30-second script
            
            markers.append({
                "emotion": emotion,
                "start_time": time_position,
                "duration": 5.0,
                "intensity": 0.7
            })
        
        return markers
    
    async def _identify_emphasis_points(self, script_text: str, key_points: List[str]) -> List[Dict[str, Any]]:
        """Identify words/phrases that should be emphasized"""
        
        emphasis_points = []
        
        # Look for key point mentions in script
        for key_point in key_points:
            # Find key words from the point
            key_words = [word.lower() for word in key_point.split() if len(word) > 3]
            
            for word in key_words:
                if word in script_text.lower():
                    # Find position in script
                    word_index = script_text.lower().find(word)
                    if word_index != -1:
                        emphasis_points.append({
                            "text": word,
                            "position": word_index,
                            "type": "stress",
                            "intensity": 0.8
                        })
        
        # Add emphasis for superlatives and strong adjectives
        emphasis_words = ["amazing", "incredible", "fantastic", "excellent", "perfect", "love", "hate"]
        for word in emphasis_words:
            if word in script_text.lower():
                word_index = script_text.lower().find(word)
                if word_index != -1:
                    emphasis_points.append({
                        "text": word,
                        "position": word_index,
                        "type": "emphasis",
                        "intensity": 0.9
                    })
        
        return emphasis_points[:10]  # Limit to 10 emphasis points
    
    def _identify_pause_points(self, script_text: str) -> List[float]:
        """Identify natural pause points in the script"""
        
        pauses = []
        
        # Add pauses at sentence boundaries
        sentences = script_text.split('. ')
        current_position = 0.0
        
        for sentence in sentences[:-1]:  # Don't add pause after last sentence
            word_count = len(sentence.split())
            sentence_duration = (word_count / 150) * 60  # 150 words per minute
            current_position += sentence_duration
            pauses.append(current_position + 0.5)  # 0.5 second pause
        
        # Add pauses at natural break points (commas, conjunctions)
        break_words = [", and", ", but", ", so", ", however"]
        for break_word in break_words:
            if break_word in script_text.lower():
                # Calculate approximate timing (simplified)
                word_position = script_text.lower().find(break_word)
                words_before = len(script_text[:word_position].split())
                time_position = (words_before / 150) * 60
                pauses.append(time_position + 0.3)  # 0.3 second pause
        
        return sorted(pauses)[:8]  # Limit to 8 pause points
    
    async def _generate_avatar_video(
        self,
        testimonial_script: TestimonialScript,
        avatar_profile: AvatarProfile,
        request: UGCGenerationRequest
    ) -> Dict[str, Any]:
        """Generate avatar video with testimonial"""
        
        # Select best provider for avatar generation
        provider_name = "did"  # Default to D-ID for testimonials
        if "avatar_provider" in request.avatar_preferences:
            provider_name = request.avatar_preferences["avatar_provider"]
        
        provider = self.avatar_providers.get(provider_name)
        if not provider:
            logger.error(f"Avatar provider {provider_name} not available")
            return {"error": "Provider not available"}
        
        # Generate voice settings based on avatar profile
        voice_settings = self._create_voice_settings(avatar_profile, testimonial_script)
        
        try:
            async with provider:
                # Prepare generation request
                generation_request = {
                    "script_text": testimonial_script.script_text,
                    "avatar_id": self._map_avatar_to_provider(avatar_profile, provider_name),
                    "voice_settings": voice_settings,
                    "emotion_markers": testimonial_script.emotion_markers,
                    "emphasis_points": testimonial_script.emphasis_points
                }
                
                # Generate avatar video
                from .base_provider import GenerationRequest
                from app.models.video_project import VideoQualityEnum, VideoStyleEnum
                
                gen_request = GenerationRequest(
                    prompt=testimonial_script.script_text,
                    duration=testimonial_script.estimated_duration,
                    style=VideoStyleEnum.REALISTIC,
                    quality=VideoQualityEnum.HIGH,
                    additional_params=generation_request
                )
                
                result = await provider.generate_video(gen_request)
                
                # Poll for completion (simplified)
                for _ in range(30):  # Wait up to 15 minutes
                    if result.status.value == "completed":
                        break
                    await asyncio.sleep(30)
                    result = await provider.check_status(result.job_id)
                
                return {
                    "video_url": result.video_url,
                    "audio_url": result.metadata.get("audio_url"),
                    "provider": provider_name,
                    "model_version": result.metadata.get("model_version"),
                    "cost": result.cost,
                    "generation_time": result.generation_time
                }
                
        except Exception as e:
            logger.error(f"Avatar video generation failed: {e}")
            return {
                "error": str(e),
                "provider": provider_name,
                "cost": 0.0
            }
    
    def _create_voice_settings(self, avatar_profile: AvatarProfile, testimonial_script: TestimonialScript) -> VoiceSettings:
        """Create voice settings based on avatar profile"""
        
        # Map avatar characteristics to voice settings
        base_voice_id = "21m00Tcm4TlvDq8ikWAM"  # Default ElevenLabs Rachel
        
        # Select voice based on avatar gender and age
        if avatar_profile.gender == AvatarGender.MALE:
            if avatar_profile.age_range == AvatarAgeRange.YOUNG_ADULT:
                base_voice_id = "TX3LPaxmHKxFdv7VOQHJ"  # Liam - young male
            else:
                base_voice_id = "29vD33N1CtxCmqQRPOHJ"  # Drew - adult male
        else:  # Female
            if avatar_profile.age_range == AvatarAgeRange.YOUNG_ADULT:
                base_voice_id = "MF3mGyEYCl7XYWbV9V6O"  # Elli - young female
            else:
                base_voice_id = "21m00Tcm4TlvDq8ikWAM"  # Rachel - adult female
        
        # Adjust settings based on personality
        stability = 0.75
        clarity = 0.75
        emotion = EmotionType.NEUTRAL
        
        if "enthusiastic" in avatar_profile.personality_traits:
            emotion = EmotionType.EXCITED
            clarity = 0.85
        elif "calm" in avatar_profile.personality_traits:
            stability = 0.85
            emotion = EmotionType.CALM
        elif "confident" in avatar_profile.personality_traits:
            stability = 0.80
            emotion = EmotionType.PROFESSIONAL
        
        return VoiceSettings(
            voice_id=base_voice_id,
            stability=stability,
            clarity=clarity,
            emotion=emotion
        )
    
    def _map_avatar_to_provider(self, avatar_profile: AvatarProfile, provider_name: str) -> str:
        """Map our avatar profile to provider-specific avatar ID"""
        
        # Provider-specific avatar mappings
        provider_avatars = {
            "did": {
                "female_young_caucasian": "amy",
                "female_adult_caucasian": "anna",
                "male_young_caucasian": "will",
                "male_adult_caucasian": "daniel",
                "female_young_hispanic": "maria",
                "male_adult_african_american": "marcus"
            },
            "heygen": {
                "female_young_caucasian": "Lily_public_3_20230814",
                "male_adult_caucasian": "Wayne_20220513",
                "female_adult_hispanic": "Maria_public_20230815"
            },
            "synthesia": {
                "female_young_caucasian": "anna_costume1_cameraA",
                "male_adult_caucasian": "daniel_costume1_cameraA"
            }
        }
        
        # Create avatar key
        avatar_key = f"{avatar_profile.gender.value}_{avatar_profile.age_range.value.split('-')[0]}_{avatar_profile.ethnicity.value}"
        
        # Simplify key for mapping
        if "20" in avatar_profile.age_range.value or "30" in avatar_profile.age_range.value:
            age_key = "young"
        else:
            age_key = "adult"
        
        simplified_key = f"{avatar_profile.gender.value}_{age_key}_{avatar_profile.ethnicity.value}"
        
        provider_mapping = provider_avatars.get(provider_name, {})
        return provider_mapping.get(simplified_key, list(provider_mapping.values())[0] if provider_mapping else "default")
    
    async def _calculate_quality_score(
        self,
        testimonial_script: TestimonialScript,
        avatar_profile: AvatarProfile,
        review_data: ReviewData
    ) -> float:
        """Calculate overall quality score for the generated testimonial"""
        
        score = 0.0
        
        # Script quality (40% of score)
        script_score = 0.7  # Base score
        
        # Length appropriateness
        if 15 <= testimonial_script.estimated_duration <= 45:
            script_score += 0.1
        
        # Authenticity elements
        if testimonial_script.authenticity_elements:
            script_score += 0.1
        
        # Emotion markers
        if testimonial_script.emotion_markers:
            script_score += 0.1
        
        score += script_score * 0.4
        
        # Avatar selection quality (30% of score)
        avatar_score = 0.7  # Base score
        
        # Avatar diversity bonus
        if avatar_profile.ethnicity != AvatarEthnicity.CAUCASIAN:
            avatar_score += 0.1
        
        # Personality match (if we have product category)
        avatar_score += 0.2  # Assume good match for now
        
        score += avatar_score * 0.3
        
        # Review credibility (30% of score)
        score += review_data.credibility_score * 0.3
        
        return min(1.0, max(0.0, score))
    
    async def generate_batch_testimonials(
        self,
        product: Product,
        reviews: List[ReviewData],
        batch_config: Dict[str, Any]
    ) -> List[UGCGenerationResult]:
        """Generate multiple testimonials for a product"""
        
        logger.info(f"Generating batch of {len(reviews)} testimonials for {product.name}")
        
        results = []
        
        # Process reviews in parallel (with rate limiting)
        semaphore = asyncio.Semaphore(3)  # Limit concurrent generations
        
        async def generate_single(review_data: ReviewData) -> UGCGenerationResult:
            async with semaphore:
                request = UGCGenerationRequest(
                    product=product,
                    review_data=review_data,
                    **batch_config
                )
                return await self.generate_ugc_testimonial(request)
        
        tasks = [generate_single(review) for review in reviews]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Filter out failed generations
        successful_results = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                logger.error(f"Failed to generate testimonial {i}: {result}")
            else:
                successful_results.append(result)
        
        logger.info(f"Successfully generated {len(successful_results)}/{len(reviews)} testimonials")
        
        return successful_results


# Global service instance
_ugc_generation_service: Optional[UGCGenerationService] = None


def get_ugc_generation_service() -> UGCGenerationService:
    """Get global UGC generation service instance"""
    global _ugc_generation_service
    if _ugc_generation_service is None:
        _ugc_generation_service = UGCGenerationService()
    return _ugc_generation_service