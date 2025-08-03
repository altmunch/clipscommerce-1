"""
Production Guide Generator

Creates detailed guides for users to produce high-quality videos themselves.
Focuses on practical instructions rather than automated generation.
"""

import asyncio
import json
from typing import Any, Dict, List, Optional
import logging

from app.services.ai.providers import get_text_service
from app.core.config import settings

logger = logging.getLogger(__name__)


class ProductionGuideGenerator:
    """Generates detailed production guides for video creation"""
    
    def __init__(self):
        self.text_service = None
    
    async def _get_text_service(self):
        """Initialize AI service"""
        if self.text_service is None:
            self.text_service = await get_text_service()
    
    async def create_production_guide(
        self,
        video_outline: Dict[str, Any],
        brand_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Create comprehensive production guide for video creation"""
        
        await self._get_text_service()
        
        try:
            scenes = video_outline.get("scenes", [])
            hook = video_outline.get("hook", {})
            brand_name = brand_data.get("name", "Brand")
            
            # Generate different components of the production guide
            filming_instructions = await self._generate_filming_instructions(scenes, brand_data)
            equipment_list = self._generate_equipment_list(scenes)
            shot_list = self._generate_detailed_shot_list(scenes, brand_data)
            editing_guide = await self._generate_editing_guide(scenes, brand_data)
            asset_requirements = self._generate_asset_requirements(scenes, brand_data)
            
            production_guide = {
                "video_title": f"Production Guide: {hook.get('text', 'Viral Video')}",
                "overview": {
                    "concept": hook.get("text", ""),
                    "target_duration": video_outline.get("total_duration", 30),
                    "platform": video_outline.get("metadata", {}).get("target_platform", "tiktok"),
                    "style": video_outline.get("metadata", {}).get("video_style", "engaging")
                },
                "pre_production": {
                    "equipment_needed": equipment_list,
                    "asset_requirements": asset_requirements,
                    "location_setup": await self._generate_location_setup(scenes),
                    "preparation_checklist": self._generate_prep_checklist(scenes, brand_data)
                },
                "production": {
                    "shot_list": shot_list,
                    "filming_instructions": filming_instructions,
                    "dialogue_script": self._extract_dialogue_script(scenes),
                    "timing_notes": self._generate_timing_notes(scenes)
                },
                "post_production": {
                    "editing_guide": editing_guide,
                    "text_overlays": self._extract_text_overlays(scenes),
                    "transitions": self._extract_transitions(scenes),
                    "music_suggestions": await self._generate_music_suggestions(video_outline),
                    "color_grading": self._generate_color_grading_guide(brand_data)
                },
                "quality_checklist": {
                    "video_quality": [
                        "1080p minimum resolution",
                        "Stable footage (use tripod/gimbal)",
                        "Good lighting (natural light preferred)",
                        "Clear audio (consider external mic)",
                        "Consistent framing throughout"
                    ],
                    "content_quality": [
                        "Hook delivered within first 3 seconds",
                        "Clear value proposition presented",
                        "Strong call-to-action at end",
                        "Brand elements visible but not overwhelming",
                        "Engaging throughout entire duration"
                    ],
                    "technical_requirements": [
                        "Vertical 9:16 aspect ratio for TikTok/Instagram",
                        "Clear text overlays (readable on mobile)",
                        "Appropriate volume levels",
                        "Smooth transitions between scenes",
                        "Consistent brand colors used"
                    ]
                }
            }
            
            return production_guide
            
        except Exception as e:
            raise Exception(f"Production guide generation failed: {e}")
    
    async def _generate_filming_instructions(
        self,
        scenes: List[Dict[str, Any]],
        brand_data: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Generate detailed filming instructions for each scene"""
        
        instructions = []
        
        for i, scene in enumerate(scenes):
            scene_instruction = {
                "scene_number": i + 1,
                "timing": scene.get("timing", f"{i*5}-{(i+1)*5}s"),
                "type": scene.get("type", "main"),
                "setup": await self._generate_scene_setup(scene, brand_data),
                "camera_work": self._generate_camera_instructions(scene),
                "talent_direction": self._generate_talent_direction(scene),
                "key_elements": self._identify_key_elements(scene)
            }
            instructions.append(scene_instruction)
        
        return instructions
    
    async def _generate_scene_setup(
        self,
        scene: Dict[str, Any],
        brand_data: Dict[str, Any]
    ) -> str:
        """Generate setup instructions for a specific scene"""
        
        scene_type = scene.get("type", "main")
        visual = scene.get("visual", "")
        
        setup_templates = {
            "hook": "Set up for maximum impact - good lighting, clear background, product prominently visible. This scene needs to grab attention immediately.",
            "problem": "Create a relatable scenario - show the problem/frustration clearly. Use before/after setup if applicable.",
            "solution": "Showcase the product in action - demonstrate key features clearly. Good lighting on product is essential.",
            "cta": "Clean, professional setup - brand elements visible, clear call-to-action display. Ensure text overlay space is available."
        }
        
        base_setup = setup_templates.get(scene_type, "Standard product showcase setup")
        
        if visual:
            return f"{base_setup} Specific visual: {visual}"
        
        return base_setup
    
    def _generate_camera_instructions(self, scene: Dict[str, Any]) -> List[str]:
        """Generate camera movement and framing instructions"""
        
        scene_type = scene.get("type", "main")
        
        camera_guides = {
            "hook": [
                "Start with close-up for impact",
                "Quick zoom or pan for energy",
                "Ensure product/face is clearly visible",
                "Use dynamic movement but keep stable"
            ],
            "problem": [
                "Show the problem clearly",
                "Use wider shots to show context",
                "Consider before/after comparisons",
                "Keep framing consistent"
            ],
            "solution": [
                "Focus on product demonstration",
                "Use multiple angles if needed",
                "Show details and key features",
                "Smooth movements between shots"
            ],
            "cta": [
                "Clear, stable shot",
                "Center the key message",
                "Ensure brand elements are visible",
                "Hold shot steady for text overlay"
            ]
        }
        
        return camera_guides.get(scene_type, [
            "Standard framing and movement",
            "Keep shots stable and clear",
            "Focus on key elements"
        ])
    
    def _generate_talent_direction(self, scene: Dict[str, Any]) -> str:
        """Generate direction for on-screen talent"""
        
        dialogue = scene.get("dialogue", "")
        scene_type = scene.get("type", "main")
        
        direction_templates = {
            "hook": "High energy, enthusiastic delivery. Make eye contact with camera. Show genuine excitement about the product.",
            "problem": "Relatable, slightly frustrated tone. Connect with viewer's pain point. Be authentic and empathetic.",
            "solution": "Confident, helpful tone. Demonstrate clearly. Show genuine satisfaction with the solution.",
            "cta": "Clear, direct, and friendly. Make it easy for viewer to take action. End with positive energy."
        }
        
        base_direction = direction_templates.get(scene_type, "Natural, conversational delivery")
        
        if dialogue:
            return f"{base_direction} Script: '{dialogue}'"
        
        return base_direction
    
    def _identify_key_elements(self, scene: Dict[str, Any]) -> List[str]:
        """Identify key elements that must be captured in scene"""
        
        elements = []
        
        if scene.get("visual"):
            elements.append(f"Visual: {scene['visual']}")
        
        if scene.get("text_overlay"):
            elements.append(f"Text overlay space for: {scene['text_overlay']}")
        
        if scene.get("dialogue"):
            elements.append(f"Clear audio for: {scene['dialogue']}")
        
        scene_type = scene.get("type", "")
        if scene_type == "hook":
            elements.append("Product prominently featured")
            elements.append("Attention-grabbing opening")
        elif scene_type == "cta":
            elements.append("Brand elements visible")
            elements.append("Clear call-to-action space")
        
        return elements if elements else ["Clear product visibility", "Good lighting", "Stable footage"]
    
    def _generate_equipment_list(self, scenes: List[Dict[str, Any]]) -> Dict[str, List[str]]:
        """Generate equipment list based on scenes"""
        
        return {
            "essential": [
                "Smartphone or camera with good video quality",
                "Tripod or phone mount for stability",
                "Good lighting (ring light or natural window light)",
                "Clean background or backdrop"
            ],
            "recommended": [
                "External microphone for better audio",
                "Reflector for even lighting",
                "Extra phone battery or charger",
                "Props related to your product"
            ],
            "optional": [
                "Gimbal for smooth movement shots",
                "Additional lighting setup",
                "Teleprompter app for dialogue",
                "Color correction tools"
            ]
        }
    
    def _generate_detailed_shot_list(
        self,
        scenes: List[Dict[str, Any]],
        brand_data: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Generate detailed shot list with specific instructions"""
        
        shot_list = []
        
        for i, scene in enumerate(scenes):
            shot = {
                "shot_number": i + 1,
                "scene_type": scene.get("type", "main"),
                "duration": scene.get("timing", f"{i*5}-{(i+1)*5}s"),
                "frame_type": self._determine_frame_type(scene),
                "movement": self._determine_movement(scene),
                "focus_point": self._determine_focus_point(scene),
                "lighting_notes": self._determine_lighting(scene),
                "audio_notes": scene.get("dialogue", "Background music only")
            }
            shot_list.append(shot)
        
        return shot_list
    
    def _determine_frame_type(self, scene: Dict[str, Any]) -> str:
        """Determine appropriate frame type for scene"""
        scene_type = scene.get("type", "main")
        
        frame_types = {
            "hook": "Close-up to medium shot",
            "problem": "Medium to wide shot",
            "solution": "Medium shot with product focus",
            "cta": "Medium shot with clear branding"
        }
        
        return frame_types.get(scene_type, "Medium shot")
    
    def _determine_movement(self, scene: Dict[str, Any]) -> str:
        """Determine camera movement for scene"""
        scene_type = scene.get("type", "main")
        
        movements = {
            "hook": "Quick zoom in or dynamic reveal",
            "problem": "Stable with possible pan",
            "solution": "Smooth movement to showcase product",
            "cta": "Static, stable shot"
        }
        
        return movements.get(scene_type, "Stable, minimal movement")
    
    def _determine_focus_point(self, scene: Dict[str, Any]) -> str:
        """Determine main focus point for scene"""
        scene_type = scene.get("type", "main")
        
        focus_points = {
            "hook": "Product and talent's reaction",
            "problem": "Problem situation/context",
            "solution": "Product in action/demonstration",
            "cta": "Brand elements and call-to-action"
        }
        
        return focus_points.get(scene_type, "Main subject/product")
    
    def _determine_lighting(self, scene: Dict[str, Any]) -> str:
        """Determine lighting requirements for scene"""
        scene_type = scene.get("type", "main")
        
        lighting_notes = {
            "hook": "Bright, energetic lighting",
            "problem": "Natural, slightly softer lighting",
            "solution": "Clear, bright lighting on product",
            "cta": "Professional, even lighting"
        }
        
        return lighting_notes.get(scene_type, "Even, natural lighting")
    
    async def _generate_editing_guide(
        self,
        scenes: List[Dict[str, Any]],
        brand_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Generate post-production editing guide"""
        
        return {
            "sequence_structure": [
                {
                    "step": 1,
                    "action": "Import all footage and organize by scene",
                    "notes": "Create folders for each scene type"
                },
                {
                    "step": 2,
                    "action": "Rough cut following shot list timing",
                    "notes": "Focus on pacing - first 3 seconds are critical"
                },
                {
                    "step": 3,
                    "action": "Add text overlays at designated moments",
                    "notes": "Ensure text is readable on mobile devices"
                },
                {
                    "step": 4,
                    "action": "Insert transitions between scenes",
                    "notes": "Keep transitions quick and engaging"
                },
                {
                    "step": 5,
                    "action": "Add background music and adjust audio levels",
                    "notes": "Music should enhance but not overpower dialogue"
                },
                {
                    "step": 6,
                    "action": "Color correction and final polish",
                    "notes": "Maintain consistent look throughout"
                }
            ],
            "timing_guidelines": {
                "hook_section": "First 3 seconds - must grab attention",
                "problem_section": "Seconds 3-8 - establish pain point",
                "solution_section": "Seconds 8-25 - demonstrate value",
                "cta_section": "Final 5 seconds - clear next step"
            },
            "export_settings": {
                "resolution": "1080x1920 (9:16 vertical)",
                "frame_rate": "30fps",
                "format": "MP4 (H.264)",
                "quality": "High (for upload platforms)"
            }
        }
    
    def _extract_dialogue_script(self, scenes: List[Dict[str, Any]]) -> List[Dict[str, str]]:
        """Extract dialogue script for talent"""
        
        script = []
        for i, scene in enumerate(scenes):
            if scene.get("dialogue"):
                script.append({
                    "scene": f"Scene {i+1} ({scene.get('type', 'main')})",
                    "timing": scene.get("timing", f"{i*5}-{(i+1)*5}s"),
                    "dialogue": scene.get("dialogue", ""),
                    "delivery_notes": self._get_delivery_notes(scene.get("type", "main"))
                })
        
        return script
    
    def _get_delivery_notes(self, scene_type: str) -> str:
        """Get delivery notes for different scene types"""
        
        notes = {
            "hook": "Energetic, attention-grabbing delivery",
            "problem": "Relatable, empathetic tone",
            "solution": "Confident, helpful explanation",
            "cta": "Clear, direct, and friendly"
        }
        
        return notes.get(scene_type, "Natural, conversational tone")
    
    def _extract_text_overlays(self, scenes: List[Dict[str, Any]]) -> List[Dict[str, str]]:
        """Extract text overlay requirements"""
        
        overlays = []
        for i, scene in enumerate(scenes):
            if scene.get("text_overlay"):
                overlays.append({
                    "scene": f"Scene {i+1}",
                    "timing": scene.get("timing", f"{i*5}-{(i+1)*5}s"),
                    "text": scene.get("text_overlay", ""),
                    "style": "Bold, readable font with contrasting background",
                    "position": "Center or bottom third"
                })
        
        return overlays
    
    def _extract_transitions(self, scenes: List[Dict[str, Any]]) -> List[str]:
        """Extract transition requirements"""
        
        transitions = []
        for i, scene in enumerate(scenes[:-1]):  # All except last scene
            transition = scene.get("transition", "cut")
            transitions.append(f"Scene {i+1} to {i+2}: {transition}")
        
        return transitions
    
    async def _generate_music_suggestions(self, video_outline: Dict[str, Any]) -> Dict[str, Any]:
        """Generate music and audio suggestions"""
        
        platform = video_outline.get("metadata", {}).get("target_platform", "tiktok")
        
        return {
            "style": "Upbeat, trending audio that matches content energy",
            "platform_notes": {
                "tiktok": "Use trending TikTok sounds when possible",
                "instagram": "Licensed music or original audio works well",
                "youtube": "Ensure music is copyright-free or licensed"
            }.get(platform, "Use platform-appropriate audio"),
            "volume_levels": "Background music at 20-30% volume, dialogue at 70-80%",
            "timing": "Music should enhance scene transitions and key moments"
        }
    
    def _generate_color_grading_guide(self, brand_data: Dict[str, Any]) -> Dict[str, str]:
        """Generate color grading guidelines"""
        
        return {
            "overall_tone": "Bright, vibrant, and engaging",
            "brand_consistency": f"Incorporate {brand_data.get('name', 'brand')} colors where appropriate",
            "mobile_optimization": "High contrast for mobile viewing",
            "saturation": "Slightly enhanced for social media appeal",
            "exposure": "Well-lit, avoid dark or muddy footage"
        }
    
    async def _generate_location_setup(self, scenes: List[Dict[str, Any]]) -> List[str]:
        """Generate location and setup requirements"""
        
        return [
            "Clean, uncluttered background that doesn't distract from main subject",
            "Good natural lighting or well-positioned artificial lighting",
            "Quiet environment for clear audio recording",
            "Stable surface for camera/phone placement",
            "Props and products easily accessible and well-organized",
            "Backup power source for extended filming sessions"
        ]
    
    def _generate_prep_checklist(
        self,
        scenes: List[Dict[str, Any]],
        brand_data: Dict[str, Any]
    ) -> List[str]:
        """Generate pre-production checklist"""
        
        return [
            "Review all scenes and shot list thoroughly",
            "Test camera/phone video quality and audio",
            "Prepare all props and product samples",
            "Practice dialogue and timing for each scene",
            "Set up lighting and test different angles",
            "Charge all devices and have backup power ready",
            f"Prepare {brand_data.get('name', 'brand')} materials and branding elements",
            "Clear shooting schedule with adequate time for each scene",
            "Have editing software ready and familiar with basic functions"
        ]
    
    def _generate_timing_notes(self, scenes: List[Dict[str, Any]]) -> List[str]:
        """Generate timing and pacing notes"""
        
        return [
            "First 3 seconds: Must immediately grab attention - no slow buildup",
            "Seconds 3-8: Quickly establish the problem or pain point",
            "Seconds 8-25: Demonstrate solution with clear value proposition",
            "Final 5 seconds: Strong call-to-action with clear next steps",
            "Overall pacing: Keep energy high throughout - avoid dead air",
            "Transitions: Quick and seamless between scenes",
            "Audio sync: Ensure dialogue matches visual timing perfectly"
        ]
    
