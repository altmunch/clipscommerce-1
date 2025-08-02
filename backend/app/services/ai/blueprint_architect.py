"""
Blueprint Architecture Service

Generates detailed video scripts, shot lists, and scene breakdowns
for video content production with AI-powered direction and optimization.
"""

import asyncio
import json
import re
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple
import logging

from app.core.config import settings
from app.services.ai.providers import get_text_service
from app.services.ai.prompts import get_prompt_template
from app.services.ai.viral_content import ViralHook, Platform

logger = logging.getLogger(__name__)


class ShotType(str, Enum):
    """Types of camera shots"""
    EXTREME_CLOSEUP = "extreme_closeup"
    CLOSEUP = "closeup"
    MEDIUM_CLOSEUP = "medium_closeup"
    MEDIUM_SHOT = "medium_shot"
    MEDIUM_WIDE = "medium_wide"
    WIDE_SHOT = "wide_shot"
    EXTREME_WIDE = "extreme_wide"
    OVER_SHOULDER = "over_shoulder"
    CUTAWAY = "cutaway"
    INSERT = "insert"


class CameraAngle(str, Enum):
    """Camera angles"""
    EYE_LEVEL = "eye_level"
    HIGH_ANGLE = "high_angle"
    LOW_ANGLE = "low_angle"
    BIRDS_EYE = "birds_eye"
    WORMS_EYE = "worms_eye"
    DUTCH_ANGLE = "dutch_angle"


class CameraMovement(str, Enum):
    """Camera movements"""
    STATIC = "static"
    PAN_LEFT = "pan_left"
    PAN_RIGHT = "pan_right"
    TILT_UP = "tilt_up"
    TILT_DOWN = "tilt_down"
    ZOOM_IN = "zoom_in"
    ZOOM_OUT = "zoom_out"
    DOLLY_IN = "dolly_in"
    DOLLY_OUT = "dolly_out"
    TRACKING = "tracking"
    HANDHELD = "handheld"


class SceneTransition(str, Enum):
    """Scene transitions"""
    CUT = "cut"
    FADE_IN = "fade_in"
    FADE_OUT = "fade_out"
    DISSOLVE = "dissolve"
    WIPE = "wipe"
    MATCH_CUT = "match_cut"
    JUMP_CUT = "jump_cut"


@dataclass
class ScriptSegment:
    """A segment of the video script"""
    timestamp_start: float
    timestamp_end: float
    speaker: str
    dialogue: str
    action: str
    emotion: str
    notes: str = ""
    
    @property
    def duration(self) -> float:
        return self.timestamp_end - self.timestamp_start
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "timestamp_start": self.timestamp_start,
            "timestamp_end": self.timestamp_end,
            "speaker": self.speaker,
            "dialogue": self.dialogue,
            "action": self.action,
            "emotion": self.emotion,
            "notes": self.notes,
            "duration": self.duration
        }


@dataclass
class Shot:
    """Individual camera shot specification"""
    shot_number: int
    timestamp_start: float
    timestamp_end: float
    shot_type: ShotType
    camera_angle: CameraAngle
    camera_movement: CameraMovement
    subject: str
    visual_description: str
    audio_description: str
    lighting_notes: str
    props_needed: List[str]
    location: str
    transition_in: SceneTransition
    transition_out: SceneTransition
    notes: str = ""
    
    @property
    def duration(self) -> float:
        return self.timestamp_end - self.timestamp_start
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "shot_number": self.shot_number,
            "timestamp_start": self.timestamp_start,
            "timestamp_end": self.timestamp_end,
            "shot_type": self.shot_type,
            "camera_angle": self.camera_angle,
            "camera_movement": self.camera_movement,
            "subject": self.subject,
            "visual_description": self.visual_description,
            "audio_description": self.audio_description,
            "lighting_notes": self.lighting_notes,
            "props_needed": self.props_needed,
            "location": self.location,
            "transition_in": self.transition_in,
            "transition_out": self.transition_out,
            "duration": self.duration,
            "notes": self.notes
        }


@dataclass
class ProductionRequirements:
    """Production requirements and resources needed"""
    total_duration: float
    locations: List[str]
    cast_required: List[str]
    props_needed: List[str]
    equipment_needed: List[str]
    lighting_setup: List[str]
    wardrobe_notes: List[str]
    special_effects: List[str]
    post_production_notes: List[str]
    estimated_budget: Dict[str, float]
    estimated_production_time: float  # hours
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "total_duration": self.total_duration,
            "locations": self.locations,
            "cast_required": self.cast_required,
            "props_needed": self.props_needed,
            "equipment_needed": self.equipment_needed,
            "lighting_setup": self.lighting_setup,
            "wardrobe_notes": self.wardrobe_notes,
            "special_effects": self.special_effects,
            "post_production_notes": self.post_production_notes,
            "estimated_budget": self.estimated_budget,
            "estimated_production_time": self.estimated_production_time
        }


@dataclass
class VideoBlueprint:
    """Complete video production blueprint"""
    title: str
    hook: ViralHook
    platform: Platform
    target_duration: float
    script_segments: List[ScriptSegment]
    shot_list: List[Shot]
    production_requirements: ProductionRequirements
    brand_guidelines: Dict[str, Any]
    optimization_notes: List[str]
    created_at: float = field(default_factory=time.time)
    
    def get_total_script_duration(self) -> float:
        """Calculate total script duration"""
        return sum(segment.duration for segment in self.script_segments)
    
    def get_total_shots_duration(self) -> float:
        """Calculate total shots duration"""
        return sum(shot.duration for shot in self.shot_list)
    
    def validate_timing(self) -> List[str]:
        """Validate timing consistency"""
        issues = []
        
        script_duration = self.get_total_script_duration()
        shots_duration = self.get_total_shots_duration()
        
        if abs(script_duration - shots_duration) > 1.0:  # Allow 1 second tolerance
            issues.append(f"Script duration ({script_duration:.1f}s) doesn't match shots duration ({shots_duration:.1f}s)")
        
        if script_duration > self.target_duration * 1.1:  # Allow 10% overage
            issues.append(f"Script too long: {script_duration:.1f}s vs target {self.target_duration:.1f}s")
        
        # Check for timing gaps in shots
        for i in range(1, len(self.shot_list)):
            prev_shot = self.shot_list[i-1]
            current_shot = self.shot_list[i]
            
            if current_shot.timestamp_start > prev_shot.timestamp_end + 0.1:  # Allow small gap
                issues.append(f"Timing gap between shot {prev_shot.shot_number} and {current_shot.shot_number}")
        
        return issues
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "title": self.title,
            "hook": self.hook.to_dict(),
            "platform": self.platform,
            "target_duration": self.target_duration,
            "script_segments": [s.to_dict() for s in self.script_segments],
            "shot_list": [s.to_dict() for s in self.shot_list],
            "production_requirements": self.production_requirements.to_dict(),
            "brand_guidelines": self.brand_guidelines,
            "optimization_notes": self.optimization_notes,
            "created_at": self.created_at,
            "total_script_duration": self.get_total_script_duration(),
            "total_shots_duration": self.get_total_shots_duration(),
            "timing_issues": self.validate_timing()
        }


class ScriptGenerator:
    """Generates detailed video scripts"""
    
    def __init__(self):
        self.text_service = None
    
    async def _get_text_service(self):
        """Get text service instance"""
        if self.text_service is None:
            self.text_service = await get_text_service()
    
    async def generate_script(
        self,
        hook: ViralHook,
        brand_name: str,
        brand_voice: Dict[str, Any],
        target_duration: float,
        platform: Platform,
        call_to_action: str = "Follow for more!"
    ) -> List[ScriptSegment]:
        """Generate detailed video script"""
        await self._get_text_service()
        
        # Get script generation prompt
        script_prompt = await get_prompt_template("script_generation")
        
        # Format brand voice for prompt
        brand_voice_text = self._format_brand_voice(brand_voice)
        
        # Generate script with AI
        response = await self.text_service.generate(
            script_prompt.format(
                hook=hook.text,
                brand_name=brand_name,
                duration=int(target_duration),
                platform=platform,
                cta=call_to_action,
                brand_voice=brand_voice_text
            ),
            max_tokens=1200,
            temperature=0.6
        )
        
        if not response.success:
            logger.error(f"Script generation failed: {response.error}")
            return self._create_fallback_script(hook, target_duration, call_to_action)
        
        # Parse AI response into script segments
        segments = self._parse_script_response(response.content, target_duration)
        
        # Validate and adjust timing
        segments = self._adjust_script_timing(segments, target_duration)
        
        return segments
    
    def _format_brand_voice(self, brand_voice: Dict[str, Any]) -> str:
        """Format brand voice for AI prompt"""
        if not brand_voice:
            return "Professional and friendly tone"
        
        voice_parts = []
        
        if "tone" in brand_voice:
            voice_parts.append(f"Tone: {brand_voice['tone']}")
        
        if "dos" in brand_voice and brand_voice["dos"]:
            voice_parts.append(f"Do: {', '.join(brand_voice['dos'][:3])}")
        
        if "donts" in brand_voice and brand_voice["donts"]:
            voice_parts.append(f"Don't: {', '.join(brand_voice['donts'][:3])}")
        
        return "; ".join(voice_parts) if voice_parts else "Professional and friendly tone"
    
    def _parse_script_response(self, ai_response: str, target_duration: float) -> List[ScriptSegment]:
        """Parse AI script response into segments"""
        segments = []
        lines = ai_response.strip().split('\n')
        
        current_segment = None
        segment_counter = 0
        time_per_segment = target_duration / 4  # Rough estimation
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
            
            # Look for section headers (Opening Hook, Main Content, etc.)
            if re.match(r'^(Opening Hook|Hook|Main Content|Value|Call-to-Action|Closing):', line, re.IGNORECASE):
                # Save previous segment
                if current_segment:
                    segments.append(current_segment)
                
                # Start new segment
                segment_start = segment_counter * time_per_segment
                segment_end = (segment_counter + 1) * time_per_segment
                
                section_name = line.split(':')[0].strip()
                content = ':'.join(line.split(':')[1:]).strip()
                
                current_segment = ScriptSegment(
                    timestamp_start=segment_start,
                    timestamp_end=min(segment_end, target_duration),
                    speaker="Host",
                    dialogue=content,
                    action=self._infer_action_from_section(section_name),
                    emotion=self._infer_emotion_from_section(section_name),
                    notes=f"Section: {section_name}"
                )
                
                segment_counter += 1
            
            elif current_segment and not line.startswith(('Visual:', 'Audio:', 'Timing:')):
                # Continue dialogue for current segment
                if current_segment.dialogue:
                    current_segment.dialogue += " " + line
                else:
                    current_segment.dialogue = line
        
        # Don't forget the last segment
        if current_segment:
            segments.append(current_segment)
        
        return segments
    
    def _infer_action_from_section(self, section_name: str) -> str:
        """Infer action from section name"""
        action_map = {
            "opening hook": "Direct eye contact with camera, energetic gesture",
            "hook": "Direct eye contact with camera, energetic gesture",
            "main content": "Explanatory gestures, engaging body language",
            "value": "Confident posture, emphasizing gestures",
            "call-to-action": "Pointing to camera, encouraging gesture",
            "closing": "Friendly wave or concluding gesture"
        }
        
        return action_map.get(section_name.lower(), "Natural, engaging presentation")
    
    def _infer_emotion_from_section(self, section_name: str) -> str:
        """Infer emotion from section name"""
        emotion_map = {
            "opening hook": "excitement",
            "hook": "curiosity",
            "main content": "informative",
            "value": "confident",
            "call-to-action": "encouraging",
            "closing": "friendly"
        }
        
        return emotion_map.get(section_name.lower(), "engaging")
    
    def _adjust_script_timing(self, segments: List[ScriptSegment], target_duration: float) -> List[ScriptSegment]:
        """Adjust script timing to match target duration"""
        if not segments:
            return segments
        
        # Calculate current total duration
        current_duration = sum(segment.duration for segment in segments)
        
        if abs(current_duration - target_duration) < 1.0:  # Close enough
            return segments
        
        # Proportionally adjust each segment
        scale_factor = target_duration / current_duration
        
        cumulative_time = 0.0
        for segment in segments:
            segment.timestamp_start = cumulative_time
            adjusted_duration = segment.duration * scale_factor
            segment.timestamp_end = cumulative_time + adjusted_duration
            cumulative_time = segment.timestamp_end
        
        return segments
    
    def _create_fallback_script(self, hook: ViralHook, target_duration: float, cta: str) -> List[ScriptSegment]:
        """Create fallback script when AI generation fails"""
        segment_duration = target_duration / 3
        
        return [
            ScriptSegment(
                timestamp_start=0.0,
                timestamp_end=segment_duration,
                speaker="Host",
                dialogue=hook.text,
                action="Direct eye contact with camera, energetic gesture",
                emotion="excitement",
                notes="Opening hook - grab attention"
            ),
            ScriptSegment(
                timestamp_start=segment_duration,
                timestamp_end=segment_duration * 2,
                speaker="Host",
                dialogue="Here's what you need to know about this topic...",
                action="Explanatory gestures, engaging body language",
                emotion="informative",
                notes="Main content - deliver value"
            ),
            ScriptSegment(
                timestamp_start=segment_duration * 2,
                timestamp_end=target_duration,
                speaker="Host",
                dialogue=cta,
                action="Pointing to camera, encouraging gesture",
                emotion="encouraging",
                notes="Call to action - drive engagement"
            )
        ]


class ShotListGenerator:
    """Generates detailed shot lists for video production"""
    
    def __init__(self):
        self.text_service = None
    
    async def _get_text_service(self):
        """Get text service instance"""
        if self.text_service is None:
            self.text_service = await get_text_service()
    
    async def generate_shot_list(
        self,
        script_segments: List[ScriptSegment],
        platform: Platform,
        brand_name: str,
        target_duration: float
    ) -> List[Shot]:
        """Generate detailed shot list from script"""
        await self._get_text_service()
        
        # Convert script to text for AI processing
        script_text = self._script_segments_to_text(script_segments)
        
        # Get shot list generation prompt
        shot_prompt = await get_prompt_template("shot_list_creation")
        
        # Generate shot list with AI
        response = await self.text_service.generate(
            shot_prompt.format(
                script=script_text,
                duration=int(target_duration),
                platform=platform,
                brand_name=brand_name
            ),
            max_tokens=1000,
            temperature=0.4
        )
        
        if not response.success:
            logger.error(f"Shot list generation failed: {response.error}")
            return self._create_fallback_shots(script_segments, platform)
        
        # Parse AI response into shots
        shots = self._parse_shot_list_response(response.content, script_segments)
        
        # Optimize shots for platform
        shots = self._optimize_shots_for_platform(shots, platform)
        
        return shots
    
    def _script_segments_to_text(self, segments: List[ScriptSegment]) -> str:
        """Convert script segments to readable text"""
        script_lines = []
        
        for i, segment in enumerate(segments):
            script_lines.append(f"Segment {i+1} ({segment.timestamp_start:.1f}s - {segment.timestamp_end:.1f}s):")
            script_lines.append(f"Speaker: {segment.speaker}")
            script_lines.append(f"Dialogue: {segment.dialogue}")
            script_lines.append(f"Action: {segment.action}")
            script_lines.append(f"Emotion: {segment.emotion}")
            script_lines.append("")
        
        return "\n".join(script_lines)
    
    def _parse_shot_list_response(self, ai_response: str, script_segments: List[ScriptSegment]) -> List[Shot]:
        """Parse AI shot list response"""
        shots = []
        lines = ai_response.strip().split('\n')
        
        current_shot = None
        shot_counter = 1
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
            
            # Look for shot numbers
            if re.match(r'^Shot \d+|^\d+\.', line):
                # Save previous shot
                if current_shot:
                    shots.append(current_shot)
                
                # Start new shot
                current_shot = self._create_default_shot(shot_counter, script_segments)
                shot_counter += 1
            
            elif current_shot:
                # Parse shot details
                if line.lower().startswith('duration:'):
                    duration_match = re.search(r'(\d+(?:\.\d+)?)', line)
                    if duration_match:
                        duration = float(duration_match.group(1))
                        current_shot.timestamp_end = current_shot.timestamp_start + duration
                
                elif line.lower().startswith('shot type:'):
                    shot_type = self._parse_shot_type(line)
                    if shot_type:
                        current_shot.shot_type = shot_type
                
                elif line.lower().startswith('visual:'):
                    current_shot.visual_description = line.split(':', 1)[1].strip()
                
                elif line.lower().startswith('audio:'):
                    current_shot.audio_description = line.split(':', 1)[1].strip()
                
                elif line.lower().startswith('props:'):
                    props_text = line.split(':', 1)[1].strip()
                    current_shot.props_needed = [p.strip() for p in props_text.split(',') if p.strip()]
        
        # Don't forget the last shot
        if current_shot:
            shots.append(current_shot)
        
        # Adjust timing if needed
        shots = self._adjust_shot_timing(shots, script_segments)
        
        return shots
    
    def _create_default_shot(self, shot_number: int, script_segments: List[ScriptSegment]) -> Shot:
        """Create default shot with reasonable defaults"""
        # Estimate timing based on script segments
        if script_segments and shot_number <= len(script_segments):
            segment = script_segments[shot_number - 1]
            start_time = segment.timestamp_start
            end_time = segment.timestamp_end
        else:
            # Fallback timing
            start_time = (shot_number - 1) * 5.0  # 5 seconds per shot
            end_time = shot_number * 5.0
        
        return Shot(
            shot_number=shot_number,
            timestamp_start=start_time,
            timestamp_end=end_time,
            shot_type=ShotType.MEDIUM_SHOT,
            camera_angle=CameraAngle.EYE_LEVEL,
            camera_movement=CameraMovement.STATIC,
            subject="Host",
            visual_description="Host speaking to camera",
            audio_description="Clear dialogue recording",
            lighting_notes="Natural lighting or soft key light",
            props_needed=[],
            location="Indoor studio or clean background",
            transition_in=SceneTransition.CUT,
            transition_out=SceneTransition.CUT
        )
    
    def _parse_shot_type(self, line: str) -> Optional[ShotType]:
        """Parse shot type from text"""
        line_lower = line.lower()
        
        type_map = {
            "extreme close": ShotType.EXTREME_CLOSEUP,
            "close up": ShotType.CLOSEUP,
            "closeup": ShotType.CLOSEUP,
            "medium close": ShotType.MEDIUM_CLOSEUP,
            "medium shot": ShotType.MEDIUM_SHOT,
            "medium wide": ShotType.MEDIUM_WIDE,
            "wide shot": ShotType.WIDE_SHOT,
            "wide": ShotType.WIDE_SHOT,
            "extreme wide": ShotType.EXTREME_WIDE
        }
        
        for key, shot_type in type_map.items():
            if key in line_lower:
                return shot_type
        
        return None
    
    def _adjust_shot_timing(self, shots: List[Shot], script_segments: List[ScriptSegment]) -> List[Shot]:
        """Adjust shot timing to align with script segments"""
        if not shots or not script_segments:
            return shots
        
        # Simple approach: distribute shots evenly across script duration
        total_script_duration = sum(segment.duration for segment in script_segments)
        shot_duration = total_script_duration / len(shots)
        
        for i, shot in enumerate(shots):
            shot.timestamp_start = i * shot_duration
            shot.timestamp_end = (i + 1) * shot_duration
            shot.shot_number = i + 1
        
        return shots
    
    def _optimize_shots_for_platform(self, shots: List[Shot], platform: Platform) -> List[Shot]:
        """Optimize shots for specific platform requirements"""
        
        platform_preferences = {
            Platform.TIKTOK: {
                "preferred_shots": [ShotType.CLOSEUP, ShotType.MEDIUM_CLOSEUP],
                "preferred_movements": [CameraMovement.HANDHELD, CameraMovement.ZOOM_IN],
                "max_shot_duration": 3.0
            },
            Platform.INSTAGRAM: {
                "preferred_shots": [ShotType.MEDIUM_SHOT, ShotType.CLOSEUP],
                "preferred_movements": [CameraMovement.STATIC, CameraMovement.PAN_LEFT],
                "max_shot_duration": 4.0
            },
            Platform.YOUTUBE_SHORTS: {
                "preferred_shots": [ShotType.MEDIUM_SHOT, ShotType.WIDE_SHOT],
                "preferred_movements": [CameraMovement.STATIC, CameraMovement.DOLLY_IN],
                "max_shot_duration": 5.0
            }
        }
        
        prefs = platform_preferences.get(platform, platform_preferences[Platform.TIKTOK])
        
        for shot in shots:
            # Optimize shot type for platform
            if shot.shot_type not in prefs["preferred_shots"]:
                shot.shot_type = prefs["preferred_shots"][0]
            
            # Limit shot duration
            if shot.duration > prefs["max_shot_duration"]:
                shot.timestamp_end = shot.timestamp_start + prefs["max_shot_duration"]
            
            # Add platform-specific notes
            if platform == Platform.TIKTOK:
                shot.notes += " Keep energy high, use dynamic framing"
            elif platform == Platform.INSTAGRAM:
                shot.notes += " Maintain aesthetic quality, good lighting essential"
        
        return shots
    
    def _create_fallback_shots(self, script_segments: List[ScriptSegment], platform: Platform) -> List[Shot]:
        """Create fallback shots when AI generation fails"""
        shots = []
        
        for i, segment in enumerate(script_segments):
            shot = Shot(
                shot_number=i + 1,
                timestamp_start=segment.timestamp_start,
                timestamp_end=segment.timestamp_end,
                shot_type=ShotType.MEDIUM_SHOT if i == 0 else ShotType.CLOSEUP,
                camera_angle=CameraAngle.EYE_LEVEL,
                camera_movement=CameraMovement.STATIC,
                subject="Host",
                visual_description=f"Host delivering: {segment.dialogue[:50]}...",
                audio_description=segment.dialogue,
                lighting_notes="Natural lighting",
                props_needed=[],
                location="Studio",
                transition_in=SceneTransition.CUT,
                transition_out=SceneTransition.CUT,
                notes=f"Fallback shot for {segment.emotion} segment"
            )
            shots.append(shot)
        
        return shots


class ProductionPlanner:
    """Plans production requirements and estimates"""
    
    @staticmethod
    def calculate_production_requirements(
        script_segments: List[ScriptSegment],
        shot_list: List[Shot],
        platform: Platform
    ) -> ProductionRequirements:
        """Calculate comprehensive production requirements"""
        
        # Extract unique requirements from shots
        locations = list(set(shot.location for shot in shot_list if shot.location))
        props_needed = list(set(prop for shot in shot_list for prop in shot.props_needed))
        
        # Determine cast requirements
        cast_required = list(set(segment.speaker for segment in script_segments))
        
        # Standard equipment for platform
        equipment_needed = ProductionPlanner._get_platform_equipment(platform)
        
        # Lighting requirements
        lighting_setup = list(set(shot.lighting_notes for shot in shot_list if shot.lighting_notes))
        
        # Calculate timing
        total_duration = max(
            sum(segment.duration for segment in script_segments),
            sum(shot.duration for shot in shot_list)
        )
        
        # Estimate production time (typically 10x the content duration)
        estimated_production_time = total_duration * 10 / 3600  # Convert to hours
        
        # Estimate budget
        estimated_budget = ProductionPlanner._estimate_budget(
            len(cast_required), len(locations), len(props_needed), estimated_production_time
        )
        
        return ProductionRequirements(
            total_duration=total_duration,
            locations=locations or ["Studio/Indoor location"],
            cast_required=cast_required,
            props_needed=props_needed,
            equipment_needed=equipment_needed,
            lighting_setup=lighting_setup or ["Natural lighting or basic key light"],
            wardrobe_notes=["Consistent with brand colors", "Avoid busy patterns"],
            special_effects=[],
            post_production_notes=[
                "Color correction to match brand palette",
                "Audio enhancement and noise reduction",
                "Add branded graphics/overlays"
            ],
            estimated_budget=estimated_budget,
            estimated_production_time=estimated_production_time
        )
    
    @staticmethod
    def _get_platform_equipment(platform: Platform) -> List[str]:
        """Get recommended equipment for platform"""
        base_equipment = [
            "Camera (smartphone or DSLR)",
            "Tripod or stabilizer",
            "External microphone",
            "Basic lighting setup"
        ]
        
        platform_specific = {
            Platform.TIKTOK: ["Ring light", "Handheld gimbal"],
            Platform.INSTAGRAM: ["Ring light", "Photo backdrop"],
            Platform.YOUTUBE_SHORTS: ["Softbox lighting", "Wireless microphone"]
        }
        
        return base_equipment + platform_specific.get(platform, [])
    
    @staticmethod
    def _estimate_budget(cast_count: int, location_count: int, props_count: int, production_hours: float) -> Dict[str, float]:
        """Estimate production budget"""
        
        # Base costs (in USD)
        base_costs = {
            "crew": production_hours * 50,  # $50/hour for basic crew
            "equipment": 100,  # Basic equipment rental
            "locations": location_count * 50,  # $50 per location
            "props": props_count * 20,  # $20 per prop
            "post_production": production_hours * 30,  # $30/hour for editing
            "miscellaneous": 100  # Buffer for unexpected costs
        }
        
        # Add cast costs if multiple people
        if cast_count > 1:
            base_costs["cast"] = (cast_count - 1) * 100  # Additional cast members
        
        total = sum(base_costs.values())
        base_costs["total"] = total
        
        return base_costs


class BlueprintArchitectService:
    """Main service for creating video production blueprints"""
    
    def __init__(self):
        self.script_generator = ScriptGenerator()
        self.shot_generator = ShotListGenerator()
    
    async def create_blueprint(
        self,
        hook: ViralHook,
        brand_name: str,
        brand_voice: Dict[str, Any],
        brand_guidelines: Dict[str, Any],
        target_duration: float,
        platform: Platform,
        call_to_action: str = "Follow for more tips!"
    ) -> VideoBlueprint:
        """Create complete video production blueprint"""
        
        logger.info(f"Creating blueprint for {brand_name} on {platform}")
        
        # Generate script
        script_segments = await self.script_generator.generate_script(
            hook=hook,
            brand_name=brand_name,
            brand_voice=brand_voice,
            target_duration=target_duration,
            platform=platform,
            call_to_action=call_to_action
        )
        
        # Generate shot list
        shot_list = await self.shot_generator.generate_shot_list(
            script_segments=script_segments,
            platform=platform,
            brand_name=brand_name,
            target_duration=target_duration
        )
        
        # Calculate production requirements
        production_requirements = ProductionPlanner.calculate_production_requirements(
            script_segments, shot_list, platform
        )
        
        # Generate optimization notes
        optimization_notes = self._generate_optimization_notes(
            script_segments, shot_list, platform, brand_guidelines
        )
        
        blueprint = VideoBlueprint(
            title=f"{brand_name} - {hook.text[:30]}...",
            hook=hook,
            platform=platform,
            target_duration=target_duration,
            script_segments=script_segments,
            shot_list=shot_list,
            production_requirements=production_requirements,
            brand_guidelines=brand_guidelines,
            optimization_notes=optimization_notes
        )
        
        # Validate blueprint
        timing_issues = blueprint.validate_timing()
        if timing_issues:
            logger.warning(f"Blueprint timing issues: {timing_issues}")
            blueprint.optimization_notes.extend([f"Timing issue: {issue}" for issue in timing_issues])
        
        return blueprint
    
    def _generate_optimization_notes(
        self,
        script_segments: List[ScriptSegment],
        shot_list: List[Shot],
        platform: Platform,
        brand_guidelines: Dict[str, Any]
    ) -> List[str]:
        """Generate optimization notes for the blueprint"""
        
        notes = []
        
        # Platform-specific optimizations
        if platform == Platform.TIKTOK:
            notes.append("Keep first 3 seconds extremely engaging to prevent scroll-away")
            notes.append("Use trending sounds or music for better reach")
            notes.append("Include captions/text overlays for accessibility")
        
        elif platform == Platform.INSTAGRAM:
            notes.append("Maintain high visual quality throughout")
            notes.append("Use consistent brand aesthetic")
            notes.append("Optimize for both feed and stories")
        
        elif platform == Platform.YOUTUBE_SHORTS:
            notes.append("Include clear value proposition in first 5 seconds")
            notes.append("Use engaging thumbnails and titles")
            notes.append("Add end screen to promote channel subscription")
        
        # Script optimizations
        total_dialogue = sum(len(segment.dialogue) for segment in script_segments)
        if total_dialogue > 500:  # Rough estimate
            notes.append("Consider shortening dialogue for better pacing")
        
        # Shot optimizations
        static_shots = sum(1 for shot in shot_list if shot.camera_movement == CameraMovement.STATIC)
        if static_shots > len(shot_list) * 0.7:
            notes.append("Add more camera movement for visual interest")
        
        # Brand consistency
        if brand_guidelines:
            if "colors" in brand_guidelines:
                notes.append(f"Ensure lighting complements brand colors: {brand_guidelines['colors']}")
            
            if "voice" in brand_guidelines:
                notes.append(f"Maintain brand voice: {brand_guidelines['voice'].get('tone', 'professional')}")
        
        return notes


# Global service instance
_blueprint_service: Optional[BlueprintArchitectService] = None


async def get_blueprint_service() -> BlueprintArchitectService:
    """Get global blueprint service instance"""
    global _blueprint_service
    if _blueprint_service is None:
        _blueprint_service = BlueprintArchitectService()
    return _blueprint_service