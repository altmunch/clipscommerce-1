"""
Viral Video Template System

Provides industry-specific and trending video templates for automated content generation.
Includes template management, customization, and optimization for different platforms.
"""

import json
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple
import logging
from pathlib import Path

from app.services.ai.capcut_client import CapCutTemplateCategory, CapCutVideoFormat, CapCutAssetType
from app.services.ai.viral_content import Platform
from app.services.ai.video_generation import VideoQuality, VideoStyle

logger = logging.getLogger(__name__)


class TemplateIndustry(str, Enum):
    """Template industry categories"""
    GENERAL = "general"
    TECHNOLOGY = "technology"
    FASHION = "fashion"
    BEAUTY = "beauty"
    FITNESS = "fitness"
    FOOD = "food"
    TRAVEL = "travel"
    LIFESTYLE = "lifestyle"
    BUSINESS = "business"
    EDUCATION = "education"
    ENTERTAINMENT = "entertainment"
    HEALTHCARE = "healthcare"
    AUTOMOTIVE = "automotive"
    REAL_ESTATE = "real_estate"
    HOME_DECOR = "home_decor"


class TemplateStyle(str, Enum):
    """Template visual styles"""
    MINIMAL = "minimal"
    BOLD = "bold"
    TRENDY = "trendy"
    PROFESSIONAL = "professional"
    PLAYFUL = "playful"
    ELEGANT = "elegant"
    MODERN = "modern"
    VINTAGE = "vintage"
    DYNAMIC = "dynamic"
    CALM = "calm"


class TemplateDifficulty(str, Enum):
    """Template complexity levels"""
    BEGINNER = "beginner"
    INTERMEDIATE = "intermediate"
    ADVANCED = "advanced"


@dataclass
class TemplateAssetSlot:
    """Asset slot in video template"""
    slot_id: str
    asset_type: CapCutAssetType
    title: str
    description: str
    duration: Optional[float] = None
    position: Tuple[float, float] = (0.0, 0.0)  # x, y position (0-1 normalized)
    size: Tuple[float, float] = (1.0, 1.0)  # width, height (0-1 normalized)
    required: bool = True
    default_asset: Optional[str] = None
    constraints: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "slot_id": self.slot_id,
            "asset_type": self.asset_type,
            "title": self.title,
            "description": self.description,
            "duration": self.duration,
            "position": self.position,
            "size": self.size,
            "required": self.required,
            "default_asset": self.default_asset,
            "constraints": self.constraints
        }


@dataclass
class TemplateScene:
    """Scene in video template"""
    scene_id: str
    title: str
    description: str
    start_time: float
    end_time: float
    asset_slots: List[TemplateAssetSlot]
    transitions: List[str] = field(default_factory=list)
    effects: List[str] = field(default_factory=list)
    text_overlays: List[Dict[str, Any]] = field(default_factory=list)
    audio_tracks: List[Dict[str, Any]] = field(default_factory=list)
    
    @property
    def duration(self) -> float:
        return self.end_time - self.start_time
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "scene_id": self.scene_id,
            "title": self.title,
            "description": self.description,
            "start_time": self.start_time,
            "end_time": self.end_time,
            "duration": self.duration,
            "asset_slots": [slot.to_dict() for slot in self.asset_slots],
            "transitions": self.transitions,
            "effects": self.effects,
            "text_overlays": self.text_overlays,
            "audio_tracks": self.audio_tracks
        }


@dataclass
class VideoTemplate:
    """Complete video template"""
    template_id: str
    title: str
    description: str
    category: CapCutTemplateCategory
    industry: TemplateIndustry
    style: TemplateStyle
    difficulty: TemplateDifficulty
    platform: Platform
    video_format: CapCutVideoFormat
    duration: float
    scenes: List[TemplateScene]
    brand_customizable: bool = True
    trending_score: float = 0.0
    usage_count: int = 0
    success_rate: float = 0.0
    tags: List[str] = field(default_factory=list)
    requirements: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "template_id": self.template_id,
            "title": self.title,
            "description": self.description,
            "category": self.category,
            "industry": self.industry,
            "style": self.style,
            "difficulty": self.difficulty,
            "platform": self.platform,
            "video_format": self.video_format,
            "duration": self.duration,
            "scenes": [scene.to_dict() for scene in self.scenes],
            "brand_customizable": self.brand_customizable,
            "trending_score": self.trending_score,
            "usage_count": self.usage_count,
            "success_rate": self.success_rate,
            "tags": self.tags,
            "requirements": self.requirements,
            "metadata": self.metadata,
            "created_at": self.created_at,
            "updated_at": self.updated_at
        }
    
    def get_total_asset_slots(self) -> int:
        """Get total number of asset slots"""
        return sum(len(scene.asset_slots) for scene in self.scenes)
    
    def get_required_assets(self) -> List[TemplateAssetSlot]:
        """Get all required asset slots"""
        required = []
        for scene in self.scenes:
            required.extend([slot for slot in scene.asset_slots if slot.required])
        return required
    
    def is_compatible_with_platform(self, platform: Platform) -> bool:
        """Check if template is compatible with platform"""
        if self.platform == platform:
            return True
        
        # Cross-platform compatibility rules
        if platform == Platform.TIKTOK and self.video_format == CapCutVideoFormat.TIKTOK_VERTICAL:
            return True
        if platform == Platform.INSTAGRAM and self.video_format in [
            CapCutVideoFormat.INSTAGRAM_SQUARE, 
            CapCutVideoFormat.INSTAGRAM_STORY
        ]:
            return True
        if platform == Platform.YOUTUBE_SHORTS and self.video_format == CapCutVideoFormat.YOUTUBE_SHORTS:
            return True
        
        return False


class ViralTemplateLibrary:
    """Library of viral video templates"""
    
    def __init__(self):
        self.templates: Dict[str, VideoTemplate] = {}
        self._load_default_templates()
    
    def _load_default_templates(self):
        """Load default viral video templates"""
        
        # Modern Unboxing Template
        unboxing_template = self._create_unboxing_template()
        self.templates[unboxing_template.template_id] = unboxing_template
        
        # Product Showcase Template
        showcase_template = self._create_product_showcase_template()
        self.templates[showcase_template.template_id] = showcase_template
        
        # Before/After Template
        before_after_template = self._create_before_after_template()
        self.templates[before_after_template.template_id] = before_after_template
        
        # Tutorial Template
        tutorial_template = self._create_tutorial_template()
        self.templates[tutorial_template.template_id] = tutorial_template
        
        # Lifestyle Template
        lifestyle_template = self._create_lifestyle_template()
        self.templates[lifestyle_template.template_id] = lifestyle_template
        
        # Tech Review Template
        tech_template = self._create_tech_review_template()
        self.templates[tech_template.template_id] = tech_template
        
        # Fashion Haul Template
        fashion_template = self._create_fashion_haul_template()
        self.templates[fashion_template.template_id] = fashion_template
        
        # Food Recipe Template
        food_template = self._create_food_recipe_template()
        self.templates[food_template.template_id] = food_template
        
        logger.info(f"Loaded {len(self.templates)} default video templates")
    
    def _create_unboxing_template(self) -> VideoTemplate:
        """Create modern unboxing template"""
        
        # Hook scene
        hook_scene = TemplateScene(
            scene_id="hook",
            title="Hook",
            description="Attention-grabbing opening",
            start_time=0.0,
            end_time=3.0,
            asset_slots=[
                TemplateAssetSlot(
                    slot_id="product_hero",
                    asset_type=CapCutAssetType.IMAGE,
                    title="Product Hero Shot",
                    description="Main product image",
                    position=(0.1, 0.1),
                    size=(0.8, 0.6),
                    constraints={"min_resolution": "1080x1080"}
                )
            ],
            text_overlays=[
                {
                    "text": "UNBOXING THE {{PRODUCT_NAME}}!",
                    "position": "bottom_center",
                    "style": "bold_white_shadow",
                    "animation": "fade_in"
                }
            ]
        )
        
        # Unboxing scene
        unboxing_scene = TemplateScene(
            scene_id="unboxing",
            title="Unboxing Process",
            description="Show the unboxing experience",
            start_time=3.0,
            end_time=15.0,
            asset_slots=[
                TemplateAssetSlot(
                    slot_id="unboxing_video",
                    asset_type=CapCutAssetType.VIDEO,
                    title="Unboxing Video",
                    description="Video of unboxing process",
                    duration=12.0,
                    constraints={"min_duration": 10.0}
                ),
                TemplateAssetSlot(
                    slot_id="package_close_up",
                    asset_type=CapCutAssetType.IMAGE,
                    title="Package Close-up",
                    description="Close-up of package/box",
                    position=(0.6, 0.6),
                    size=(0.3, 0.3)
                )
            ],
            transitions=["zoom_in", "slide"],
            effects=["quick_cuts", "speed_ramp"]
        )
        
        # Feature highlight scene
        features_scene = TemplateScene(
            scene_id="features",
            title="Key Features",
            description="Highlight product features",
            start_time=15.0,
            end_time=25.0,
            asset_slots=[
                TemplateAssetSlot(
                    slot_id="feature_image_1",
                    asset_type=CapCutAssetType.IMAGE,
                    title="Feature 1",
                    description="First key feature image"
                ),
                TemplateAssetSlot(
                    slot_id="feature_image_2",
                    asset_type=CapCutAssetType.IMAGE,
                    title="Feature 2",
                    description="Second key feature image"
                ),
                TemplateAssetSlot(
                    slot_id="feature_image_3",
                    asset_type=CapCutAssetType.IMAGE,
                    title="Feature 3",
                    description="Third key feature image"
                )
            ],
            text_overlays=[
                {
                    "text": "KEY FEATURES",
                    "position": "top_center",
                    "style": "bold_brand_color"
                }
            ]
        )
        
        # Call to action scene
        cta_scene = TemplateScene(
            scene_id="cta",
            title="Call to Action",
            description="Drive engagement and follows",
            start_time=25.0,
            end_time=30.0,
            asset_slots=[
                TemplateAssetSlot(
                    slot_id="brand_logo",
                    asset_type=CapCutAssetType.IMAGE,
                    title="Brand Logo",
                    description="Brand logo for credibility",
                    position=(0.1, 0.1),
                    size=(0.2, 0.2)
                )
            ],
            text_overlays=[
                {
                    "text": "FOLLOW FOR MORE REVIEWS!",
                    "position": "center",
                    "style": "bold_white_shadow",
                    "animation": "pulse"
                },
                {
                    "text": "Link in bio 👆",
                    "position": "bottom_center",
                    "style": "medium_white"
                }
            ]
        )
        
        return VideoTemplate(
            template_id="modern_unboxing_tiktok",
            title="Modern Unboxing",
            description="Engaging unboxing template perfect for product reveals",
            category=CapCutTemplateCategory.UNBOXING,
            industry=TemplateIndustry.GENERAL,
            style=TemplateStyle.MODERN,
            difficulty=TemplateDifficulty.BEGINNER,
            platform=Platform.TIKTOK,
            video_format=CapCutVideoFormat.TIKTOK_VERTICAL,
            duration=30.0,
            scenes=[hook_scene, unboxing_scene, features_scene, cta_scene],
            trending_score=8.5,
            tags=["unboxing", "product", "reveal", "viral", "trendy"],
            requirements={
                "min_images": 4,
                "min_videos": 1,
                "brand_logo": True
            }
        )
    
    def _create_product_showcase_template(self) -> VideoTemplate:
        """Create product showcase template"""
        
        # Attention grabber
        hook_scene = TemplateScene(
            scene_id="hook",
            title="Attention Hook",
            description="Quick product tease",
            start_time=0.0,
            end_time=2.0,
            asset_slots=[
                TemplateAssetSlot(
                    slot_id="product_hero",
                    asset_type=CapCutAssetType.IMAGE,
                    title="Product Hero",
                    description="Main product beauty shot"
                )
            ],
            text_overlays=[
                {
                    "text": "This {{PRODUCT_TYPE}} is AMAZING! 🤩",
                    "position": "center",
                    "style": "bold_white_shadow"
                }
            ],
            effects=["zoom_in", "dramatic_reveal"]
        )
        
        # Product demonstration
        demo_scene = TemplateScene(
            scene_id="demonstration",
            title="Product Demo",
            description="Show product in action",
            start_time=2.0,
            end_time=20.0,
            asset_slots=[
                TemplateAssetSlot(
                    slot_id="demo_video",
                    asset_type=CapCutAssetType.VIDEO,
                    title="Demonstration Video",
                    description="Product being used/demonstrated",
                    duration=18.0
                ),
                TemplateAssetSlot(
                    slot_id="detail_shot_1",
                    asset_type=CapCutAssetType.IMAGE,
                    title="Detail Shot 1",
                    description="Close-up detail image",
                    position=(0.65, 0.65),
                    size=(0.3, 0.3)
                ),
                TemplateAssetSlot(
                    slot_id="detail_shot_2",
                    asset_type=CapCutAssetType.IMAGE,
                    title="Detail Shot 2",
                    description="Another detail angle",
                    position=(0.05, 0.65),
                    size=(0.3, 0.3)
                )
            ],
            transitions=["quick_cut", "slide", "fade"],
            effects=["speed_ramp", "highlight_zoom"]
        )
        
        # Social proof
        proof_scene = TemplateScene(
            scene_id="social_proof",
            title="Social Proof",
            description="Show reviews or testimonials",
            start_time=20.0,
            end_time=35.0,
            asset_slots=[
                TemplateAssetSlot(
                    slot_id="review_screenshot",
                    asset_type=CapCutAssetType.IMAGE,
                    title="Customer Review",
                    description="Screenshot of positive review",
                    required=False
                ),
                TemplateAssetSlot(
                    slot_id="rating_graphic",
                    asset_type=CapCutAssetType.IMAGE,
                    title="Rating Graphic",
                    description="Star rating or score display",
                    required=False
                )
            ],
            text_overlays=[
                {
                    "text": "⭐⭐⭐⭐⭐ 5-STAR REVIEWS",
                    "position": "center",
                    "style": "bold_yellow"
                }
            ]
        )
        
        # Final CTA
        cta_scene = TemplateScene(
            scene_id="cta",
            title="Call to Action",
            description="Drive purchase or engagement",
            start_time=35.0,
            end_time=45.0,
            asset_slots=[
                TemplateAssetSlot(
                    slot_id="final_product_shot",
                    asset_type=CapCutAssetType.IMAGE,
                    title="Final Product Shot",
                    description="Clean final product image"
                )
            ],
            text_overlays=[
                {
                    "text": "GET YOURS NOW! 👆",
                    "position": "center",
                    "style": "bold_white_shadow",
                    "animation": "bounce"
                },
                {
                    "text": "Link in bio",
                    "position": "bottom_center",
                    "style": "medium_white"
                }
            ]
        )
        
        return VideoTemplate(
            template_id="product_showcase_versatile",
            title="Product Showcase",
            description="Versatile product showcase template with social proof",
            category=CapCutTemplateCategory.PRODUCT_SHOWCASE,
            industry=TemplateIndustry.GENERAL,
            style=TemplateStyle.DYNAMIC,
            difficulty=TemplateDifficulty.INTERMEDIATE,
            platform=Platform.TIKTOK,
            video_format=CapCutVideoFormat.TIKTOK_VERTICAL,
            duration=45.0,
            scenes=[hook_scene, demo_scene, proof_scene, cta_scene],
            trending_score=9.2,
            tags=["product", "showcase", "review", "demo", "conversion"],
            requirements={
                "min_images": 5,
                "min_videos": 1,
                "customer_reviews": True
            }
        )
    
    def _create_before_after_template(self) -> VideoTemplate:
        """Create before/after transformation template"""
        
        # Problem introduction
        problem_scene = TemplateScene(
            scene_id="problem",
            title="The Problem",
            description="Show the problem/before state",
            start_time=0.0,
            end_time=8.0,
            asset_slots=[
                TemplateAssetSlot(
                    slot_id="before_image",
                    asset_type=CapCutAssetType.IMAGE,
                    title="Before Image",
                    description="Before transformation state"
                )
            ],
            text_overlays=[
                {
                    "text": "THE PROBLEM:",
                    "position": "top_center",
                    "style": "bold_red"
                },
                {
                    "text": "{{PROBLEM_DESCRIPTION}}",
                    "position": "bottom_center",
                    "style": "medium_white"
                }
            ]
        )
        
        # Solution process
        solution_scene = TemplateScene(
            scene_id="solution",
            title="The Solution",
            description="Show the transformation process",
            start_time=8.0,
            end_time=25.0,
            asset_slots=[
                TemplateAssetSlot(
                    slot_id="process_video",
                    asset_type=CapCutAssetType.VIDEO,
                    title="Process Video",
                    description="Video of transformation process",
                    duration=17.0
                ),
                TemplateAssetSlot(
                    slot_id="product_in_use",
                    asset_type=CapCutAssetType.IMAGE,
                    title="Product in Use",
                    description="Product being applied/used",
                    position=(0.6, 0.1),
                    size=(0.35, 0.35)
                )
            ],
            text_overlays=[
                {
                    "text": "THE SOLUTION:",
                    "position": "top_center",
                    "style": "bold_green"
                }
            ],
            transitions=["dissolve", "wipe"],
            effects=["time_lapse", "highlight"]
        )
        
        # Dramatic reveal
        reveal_scene = TemplateScene(
            scene_id="reveal",
            title="The Reveal",
            description="Show dramatic after results",
            start_time=25.0,
            end_time=35.0,
            asset_slots=[
                TemplateAssetSlot(
                    slot_id="after_image",
                    asset_type=CapCutAssetType.IMAGE,
                    title="After Image",
                    description="After transformation result"
                ),
                TemplateAssetSlot(
                    slot_id="comparison_split",
                    asset_type=CapCutAssetType.IMAGE,
                    title="Before/After Split",
                    description="Side-by-side comparison",
                    required=False
                )
            ],
            text_overlays=[
                {
                    "text": "AMAZING RESULTS! 🤩",
                    "position": "center",
                    "style": "bold_gold",
                    "animation": "zoom_in"
                }
            ],
            effects=["dramatic_reveal", "glow"]
        )
        
        # Call to action
        cta_scene = TemplateScene(
            scene_id="cta",
            title="Get Your Results",
            description="Drive action for transformation",
            start_time=35.0,
            end_time=40.0,
            asset_slots=[
                TemplateAssetSlot(
                    slot_id="product_final",
                    asset_type=CapCutAssetType.IMAGE,
                    title="Product Final",
                    description="Final product shot"
                )
            ],
            text_overlays=[
                {
                    "text": "GET YOUR TRANSFORMATION! ✨",
                    "position": "center",
                    "style": "bold_white_shadow",
                    "animation": "pulse"
                }
            ]
        )
        
        return VideoTemplate(
            template_id="before_after_transformation",
            title="Before/After Transformation",
            description="Powerful before/after template for dramatic results",
            category=CapCutTemplateCategory.BEFORE_AFTER,
            industry=TemplateIndustry.BEAUTY,
            style=TemplateStyle.DRAMATIC,
            difficulty=TemplateDifficulty.INTERMEDIATE,
            platform=Platform.TIKTOK,
            video_format=CapCutVideoFormat.TIKTOK_VERTICAL,
            duration=40.0,
            scenes=[problem_scene, solution_scene, reveal_scene, cta_scene],
            trending_score=9.8,
            tags=["transformation", "before_after", "results", "dramatic", "beauty"],
            requirements={
                "before_image": True,
                "after_image": True,
                "process_video": True
            }
        )
    
    def _create_tutorial_template(self) -> VideoTemplate:
        """Create step-by-step tutorial template"""
        
        # Tutorial intro
        intro_scene = TemplateScene(
            scene_id="intro",
            title="Tutorial Introduction",
            description="Introduce what will be taught",
            start_time=0.0,
            end_time=5.0,
            asset_slots=[
                TemplateAssetSlot(
                    slot_id="final_result",
                    asset_type=CapCutAssetType.IMAGE,
                    title="Final Result Preview",
                    description="Show what they'll learn to create"
                )
            ],
            text_overlays=[
                {
                    "text": "Learn {{SKILL_NAME}} in 60 seconds! 📚",
                    "position": "center",
                    "style": "bold_blue"
                }
            ]
        )
        
        # Steps demonstration
        steps_scene = TemplateScene(
            scene_id="steps",
            title="Step-by-Step",
            description="Show tutorial steps",
            start_time=5.0,
            end_time=50.0,
            asset_slots=[
                TemplateAssetSlot(
                    slot_id="step_video",
                    asset_type=CapCutAssetType.VIDEO,
                    title="Steps Video",
                    description="Video showing all steps",
                    duration=45.0
                ),
                TemplateAssetSlot(
                    slot_id="step_1_highlight",
                    asset_type=CapCutAssetType.IMAGE,
                    title="Step 1 Highlight",
                    description="Key moment from step 1",
                    required=False
                ),
                TemplateAssetSlot(
                    slot_id="step_2_highlight",
                    asset_type=CapCutAssetType.IMAGE,
                    title="Step 2 Highlight",
                    description="Key moment from step 2",
                    required=False
                )
            ],
            text_overlays=[
                {
                    "text": "STEP 1",
                    "position": "top_left",
                    "style": "bold_number"
                },
                {
                    "text": "STEP 2",
                    "position": "top_left",
                    "style": "bold_number"
                },
                {
                    "text": "STEP 3",
                    "position": "top_left",
                    "style": "bold_number"
                }
            ],
            transitions=["numbered_steps", "highlight"],
            effects=["step_counter", "progress_bar"]
        )
        
        # Results & engagement
        outro_scene = TemplateScene(
            scene_id="outro",
            title="Results & Engagement",
            description="Show final result and drive engagement",
            start_time=50.0,
            end_time=60.0,
            asset_slots=[
                TemplateAssetSlot(
                    slot_id="completed_result",
                    asset_type=CapCutAssetType.IMAGE,
                    title="Completed Result",
                    description="Final completed tutorial result"
                )
            ],
            text_overlays=[
                {
                    "text": "You did it! 🎉 Follow for more tutorials!",
                    "position": "center",
                    "style": "bold_green",
                    "animation": "celebration"
                }
            ]
        )
        
        return VideoTemplate(
            template_id="step_by_step_tutorial",
            title="Step-by-Step Tutorial",
            description="Educational tutorial template with clear steps",
            category=CapCutTemplateCategory.TUTORIAL,
            industry=TemplateIndustry.EDUCATION,
            style=TemplateStyle.PROFESSIONAL,
            difficulty=TemplateDifficulty.INTERMEDIATE,
            platform=Platform.TIKTOK,
            video_format=CapCutVideoFormat.TIKTOK_VERTICAL,
            duration=60.0,
            scenes=[intro_scene, steps_scene, outro_scene],
            trending_score=7.8,
            tags=["tutorial", "education", "how_to", "step_by_step", "learning"],
            requirements={
                "instructional_video": True,
                "clear_steps": True,
                "final_result": True
            }
        )
    
    def _create_lifestyle_template(self) -> VideoTemplate:
        """Create lifestyle/day-in-the-life template"""
        
        morning_scene = TemplateScene(
            scene_id="morning",
            title="Morning Routine",
            description="Start of the day",
            start_time=0.0,
            end_time=15.0,
            asset_slots=[
                TemplateAssetSlot(
                    slot_id="morning_video",
                    asset_type=CapCutAssetType.VIDEO,
                    title="Morning Footage",
                    description="Morning routine video",
                    duration=15.0
                )
            ],
            text_overlays=[
                {
                    "text": "My morning routine ☀️",
                    "position": "top_center",
                    "style": "aesthetic_gold"
                }
            ]
        )
        
        lifestyle_montage = TemplateScene(
            scene_id="lifestyle",
            title="Lifestyle Montage",
            description="Day activities and lifestyle",
            start_time=15.0,
            end_time=45.0,
            asset_slots=[
                TemplateAssetSlot(
                    slot_id="activity_1",
                    asset_type=CapCutAssetType.VIDEO,
                    title="Activity 1",
                    description="First lifestyle activity",
                    duration=10.0
                ),
                TemplateAssetSlot(
                    slot_id="activity_2",
                    asset_type=CapCutAssetType.VIDEO,
                    title="Activity 2",
                    description="Second lifestyle activity",
                    duration=10.0
                ),
                TemplateAssetSlot(
                    slot_id="aesthetic_shot",
                    asset_type=CapCutAssetType.IMAGE,
                    title="Aesthetic Shot",
                    description="Beautiful lifestyle photo"
                )
            ],
            transitions=["smooth_cut", "aesthetic_fade"],
            effects=["warm_filter", "dreamy"]
        )
        
        inspiration_scene = TemplateScene(
            scene_id="inspiration",
            title="Inspiration",
            description="Motivational ending",
            start_time=45.0,
            end_time=60.0,
            asset_slots=[
                TemplateAssetSlot(
                    slot_id="sunset_moment",
                    asset_type=CapCutAssetType.IMAGE,
                    title="Golden Hour",
                    description="Beautiful golden hour shot"
                )
            ],
            text_overlays=[
                {
                    "text": "Living my best life ✨",
                    "position": "center",
                    "style": "elegant_white",
                    "animation": "gentle_fade"
                },
                {
                    "text": "What's your routine? 💭",
                    "position": "bottom_center",
                    "style": "light_italic"
                }
            ]
        )
        
        return VideoTemplate(
            template_id="aesthetic_lifestyle",
            title="Aesthetic Lifestyle",
            description="Beautiful lifestyle content template",
            category=CapCutTemplateCategory.LIFESTYLE,
            industry=TemplateIndustry.LIFESTYLE,
            style=TemplateStyle.ELEGANT,
            difficulty=TemplateDifficulty.BEGINNER,
            platform=Platform.INSTAGRAM,
            video_format=CapCutVideoFormat.INSTAGRAM_STORY,
            duration=60.0,
            scenes=[morning_scene, lifestyle_montage, inspiration_scene],
            trending_score=8.7,
            tags=["lifestyle", "aesthetic", "routine", "inspiration", "beautiful"],
            requirements={
                "lifestyle_footage": True,
                "good_lighting": True,
                "aesthetic_appeal": True
            }
        )
    
    def _create_tech_review_template(self) -> VideoTemplate:
        """Create tech product review template"""
        
        # Quick specs
        specs_scene = TemplateScene(
            scene_id="specs",
            title="Tech Specs",
            description="Quick specs overview",
            start_time=0.0,
            end_time=10.0,
            asset_slots=[
                TemplateAssetSlot(
                    slot_id="product_hero",
                    asset_type=CapCutAssetType.IMAGE,
                    title="Product Hero Shot",
                    description="Clean product shot"
                ),
                TemplateAssetSlot(
                    slot_id="specs_graphic",
                    asset_type=CapCutAssetType.IMAGE,
                    title="Specs Graphic",
                    description="Specifications overlay",
                    position=(0.0, 0.6),
                    size=(1.0, 0.4)
                )
            ],
            text_overlays=[
                {
                    "text": "{{PRODUCT_NAME}} Review 📱",
                    "position": "top_center",
                    "style": "tech_blue"
                }
            ]
        )
        
        # Hands-on demo
        demo_scene = TemplateScene(
            scene_id="demo",
            title="Hands-on Demo",
            description="Product demonstration",
            start_time=10.0,
            end_time=35.0,
            asset_slots=[
                TemplateAssetSlot(
                    slot_id="demo_video",
                    asset_type=CapCutAssetType.VIDEO,
                    title="Demo Video",
                    description="Hands-on demonstration",
                    duration=25.0
                ),
                TemplateAssetSlot(
                    slot_id="feature_highlight",
                    asset_type=CapCutAssetType.IMAGE,
                    title="Key Feature",
                    description="Highlight key feature",
                    position=(0.65, 0.05),
                    size=(0.3, 0.3)
                )
            ],
            transitions=["tech_slide", "zoom"],
            effects=["highlight_feature", "tech_grid"]
        )
        
        # Verdict
        verdict_scene = TemplateScene(
            scene_id="verdict",
            title="Final Verdict",
            description="Review conclusion",
            start_time=35.0,
            end_time=45.0,
            asset_slots=[
                TemplateAssetSlot(
                    slot_id="rating_graphic",
                    asset_type=CapCutAssetType.IMAGE,
                    title="Rating Graphic",
                    description="Score/rating display"
                )
            ],
            text_overlays=[
                {
                    "text": "VERDICT: {{RATING}}/10 ⭐",
                    "position": "center",
                    "style": "bold_tech_blue",
                    "animation": "score_reveal"
                },
                {
                    "text": "Worth the upgrade? 🤔",
                    "position": "bottom_center",
                    "style": "medium_white"
                }
            ]
        )
        
        return VideoTemplate(
            template_id="tech_review_comprehensive",
            title="Tech Product Review",
            description="Comprehensive tech review template",
            category=CapCutTemplateCategory.PRODUCT_SHOWCASE,
            industry=TemplateIndustry.TECHNOLOGY,
            style=TemplateStyle.PROFESSIONAL,
            difficulty=TemplateDifficulty.INTERMEDIATE,
            platform=Platform.YOUTUBE_SHORTS,
            video_format=CapCutVideoFormat.YOUTUBE_SHORTS,
            duration=45.0,
            scenes=[specs_scene, demo_scene, verdict_scene],
            trending_score=8.1,
            tags=["tech", "review", "gadget", "specs", "rating"],
            requirements={
                "product_video": True,
                "specifications": True,
                "rating_system": True
            }
        )
    
    def _create_fashion_haul_template(self) -> VideoTemplate:
        """Create fashion haul template"""
        
        intro_scene = TemplateScene(
            scene_id="intro",
            title="Haul Introduction",
            description="Introduce the haul",
            start_time=0.0,
            end_time=5.0,
            asset_slots=[
                TemplateAssetSlot(
                    slot_id="shopping_bags",
                    asset_type=CapCutAssetType.IMAGE,
                    title="Shopping Bags",
                    description="Shopping bags/haul preview"
                )
            ],
            text_overlays=[
                {
                    "text": "MASSIVE {{STORE_NAME}} HAUL! 🛍️",
                    "position": "center",
                    "style": "fashion_pink",
                    "animation": "bounce"
                }
            ]
        )
        
        try_on_scene = TemplateScene(
            scene_id="try_on",
            title="Try-On Session",
            description="Show items being worn",
            start_time=5.0,
            end_time=50.0,
            asset_slots=[
                TemplateAssetSlot(
                    slot_id="try_on_video",
                    asset_type=CapCutAssetType.VIDEO,
                    title="Try-On Video",
                    description="Video of trying on clothes",
                    duration=45.0
                ),
                TemplateAssetSlot(
                    slot_id="price_tag",
                    asset_type=CapCutAssetType.IMAGE,
                    title="Price Tag",
                    description="Price information overlay",
                    position=(0.05, 0.8),
                    size=(0.3, 0.15)
                )
            ],
            text_overlays=[
                {
                    "text": "Size: {{SIZE}} | ${{PRICE}}",
                    "position": "bottom_left",
                    "style": "price_tag"
                }
            ],
            transitions=["outfit_change", "mirror_flip"],
            effects=["fashion_filter", "style_highlight"]
        )
        
        favorites_scene = TemplateScene(
            scene_id="favorites",
            title="Favorites Roundup",
            description="Show favorite pieces",
            start_time=50.0,
            end_time=60.0,
            asset_slots=[
                TemplateAssetSlot(
                    slot_id="favorite_outfit",
                    asset_type=CapCutAssetType.IMAGE,
                    title="Favorite Outfit",
                    description="Best outfit from haul"
                )
            ],
            text_overlays=[
                {
                    "text": "My favorite find! 😍",
                    "position": "center",
                    "style": "fashion_script",
                    "animation": "heart_pulse"
                },
                {
                    "text": "Which was your fave? 💖",
                    "position": "bottom_center",
                    "style": "fashion_casual"
                }
            ]
        )
        
        return VideoTemplate(
            template_id="fashion_haul_trendy",
            title="Fashion Haul",
            description="Trendy fashion haul template",
            category=CapCutTemplateCategory.LIFESTYLE,
            industry=TemplateIndustry.FASHION,
            style=TemplateStyle.TRENDY,
            difficulty=TemplateDifficulty.BEGINNER,
            platform=Platform.TIKTOK,
            video_format=CapCutVideoFormat.TIKTOK_VERTICAL,
            duration=60.0,
            scenes=[intro_scene, try_on_scene, favorites_scene],
            trending_score=9.1,
            tags=["fashion", "haul", "try_on", "style", "shopping"],
            requirements={
                "try_on_footage": True,
                "price_information": True,
                "good_lighting": True
            }
        )
    
    def _create_food_recipe_template(self) -> VideoTemplate:
        """Create food recipe template"""
        
        ingredients_scene = TemplateScene(
            scene_id="ingredients",
            title="Ingredients",
            description="Show ingredients needed",
            start_time=0.0,
            end_time=8.0,
            asset_slots=[
                TemplateAssetSlot(
                    slot_id="ingredients_flat_lay",
                    asset_type=CapCutAssetType.IMAGE,
                    title="Ingredients Layout",
                    description="Flat lay of all ingredients"
                )
            ],
            text_overlays=[
                {
                    "text": "{{RECIPE_NAME}} Recipe 👨‍🍳",
                    "position": "top_center",
                    "style": "food_orange"
                },
                {
                    "text": "You'll need:",
                    "position": "bottom_left",
                    "style": "food_list"
                }
            ]
        )
        
        cooking_scene = TemplateScene(
            scene_id="cooking",
            title="Cooking Process",
            description="Step-by-step cooking",
            start_time=8.0,
            end_time=45.0,
            asset_slots=[
                TemplateAssetSlot(
                    slot_id="cooking_video",
                    asset_type=CapCutAssetType.VIDEO,
                    title="Cooking Video",
                    description="Time-lapse cooking process",
                    duration=37.0
                ),
                TemplateAssetSlot(
                    slot_id="technique_close_up",
                    asset_type=CapCutAssetType.IMAGE,
                    title="Technique Close-up",
                    description="Key technique demonstration",
                    position=(0.6, 0.1),
                    size=(0.35, 0.35)
                )
            ],
            transitions=["cooking_cut", "sizzle"],
            effects=["time_lapse", "steam", "sizzle_sound"]
        )
        
        final_dish_scene = TemplateScene(
            scene_id="final_dish",
            title="Final Dish",
            description="Show completed recipe",
            start_time=45.0,
            end_time=60.0,
            asset_slots=[
                TemplateAssetSlot(
                    slot_id="final_dish",
                    asset_type=CapCutAssetType.IMAGE,
                    title="Final Dish",
                    description="Beautiful shot of completed dish"
                ),
                TemplateAssetSlot(
                    slot_id="taste_test",
                    asset_type=CapCutAssetType.VIDEO,
                    title="Taste Test",
                    description="Reaction to tasting",
                    duration=5.0,
                    required=False
                )
            ],
            text_overlays=[
                {
                    "text": "Bon appétit! 🍽️",
                    "position": "center",
                    "style": "food_elegant",
                    "animation": "chef_kiss"
                },
                {
                    "text": "Save this recipe! 📌",
                    "position": "bottom_center",
                    "style": "food_call_to_action"
                }
            ]
        )
        
        return VideoTemplate(
            template_id="quick_recipe_tutorial",
            title="Quick Recipe Tutorial",
            description="Fast-paced recipe tutorial template",
            category=CapCutTemplateCategory.TUTORIAL,
            industry=TemplateIndustry.FOOD,
            style=TemplateStyle.DYNAMIC,
            difficulty=TemplateDifficulty.INTERMEDIATE,
            platform=Platform.TIKTOK,
            video_format=CapCutVideoFormat.TIKTOK_VERTICAL,
            duration=60.0,
            scenes=[ingredients_scene, cooking_scene, final_dish_scene],
            trending_score=8.9,
            tags=["recipe", "cooking", "food", "tutorial", "quick"],
            requirements={
                "cooking_footage": True,
                "ingredients_photo": True,
                "final_dish_photo": True
            }
        )
    
    def get_template(self, template_id: str) -> Optional[VideoTemplate]:
        """Get template by ID"""
        return self.templates.get(template_id)
    
    def list_templates(
        self,
        category: Optional[CapCutTemplateCategory] = None,
        industry: Optional[TemplateIndustry] = None,
        platform: Optional[Platform] = None,
        style: Optional[TemplateStyle] = None,
        difficulty: Optional[TemplateDifficulty] = None,
        min_trending_score: float = 0.0
    ) -> List[VideoTemplate]:
        """List templates with filters"""
        
        filtered_templates = list(self.templates.values())
        
        if category:
            filtered_templates = [t for t in filtered_templates if t.category == category]
        
        if industry:
            filtered_templates = [t for t in filtered_templates if t.industry == industry or t.industry == TemplateIndustry.GENERAL]
        
        if platform:
            filtered_templates = [t for t in filtered_templates if t.is_compatible_with_platform(platform)]
        
        if style:
            filtered_templates = [t for t in filtered_templates if t.style == style]
        
        if difficulty:
            filtered_templates = [t for t in filtered_templates if t.difficulty == difficulty]
        
        if min_trending_score > 0:
            filtered_templates = [t for t in filtered_templates if t.trending_score >= min_trending_score]
        
        # Sort by trending score
        filtered_templates.sort(key=lambda t: t.trending_score, reverse=True)
        
        return filtered_templates
    
    def get_trending_templates(self, limit: int = 10) -> List[VideoTemplate]:
        """Get top trending templates"""
        templates = list(self.templates.values())
        templates.sort(key=lambda t: t.trending_score, reverse=True)
        return templates[:limit]
    
    def get_recommended_templates(
        self,
        industry: TemplateIndustry,
        platform: Platform,
        difficulty: TemplateDifficulty = TemplateDifficulty.BEGINNER
    ) -> List[VideoTemplate]:
        """Get recommended templates for specific use case"""
        
        return self.list_templates(
            industry=industry,
            platform=platform,
            difficulty=difficulty,
            min_trending_score=7.0
        )[:5]
    
    def add_template(self, template: VideoTemplate):
        """Add new template to library"""
        self.templates[template.template_id] = template
        logger.info(f"Added new template: {template.template_id}")
    
    def update_template_stats(
        self,
        template_id: str,
        usage_increment: int = 1,
        success: bool = True
    ):
        """Update template usage statistics"""
        
        if template_id in self.templates:
            template = self.templates[template_id]
            template.usage_count += usage_increment
            
            # Update success rate
            if success:
                current_successes = template.success_rate * (template.usage_count - usage_increment)
                new_successes = current_successes + usage_increment
                template.success_rate = new_successes / template.usage_count
            else:
                current_successes = template.success_rate * (template.usage_count - usage_increment)
                template.success_rate = current_successes / template.usage_count
            
            template.updated_at = time.time()
            
            logger.info(f"Updated stats for template {template_id}: usage={template.usage_count}, success_rate={template.success_rate:.2f}")


# Global template library instance
_template_library: Optional[ViralTemplateLibrary] = None


def get_template_library() -> ViralTemplateLibrary:
    """Get global template library instance"""
    global _template_library
    if _template_library is None:
        _template_library = ViralTemplateLibrary()
    return _template_library