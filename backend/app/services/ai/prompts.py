"""
AI Prompt Templates System

Manages prompt templates with versioning, optimization tracking, and A/B testing
for consistent and optimized AI interactions across all services.
"""

import json
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Union
import logging

from app.core.config import settings

logger = logging.getLogger(__name__)


class PromptType(str, Enum):
    """Types of prompts"""
    BRAND_ANALYSIS = "brand_analysis"
    BRAND_VOICE_ANALYSIS = "brand_voice_analysis"
    CONTENT_PILLARS_IDENTIFICATION = "content_pillars_identification"
    VIRAL_HOOK_GENERATION = "viral_hook_generation"
    VIRAL_SCORING = "viral_scoring"
    SCRIPT_GENERATION = "script_generation"
    SHOT_LIST_CREATION = "shot_list_creation"
    CAPTION_OPTIMIZATION = "caption_optimization"
    HASHTAG_RESEARCH = "hashtag_research"
    CTA_GENERATION = "cta_generation"
    PERFORMANCE_ANALYSIS = "performance_analysis"
    TREND_ANALYSIS = "trend_analysis"


@dataclass
class PromptMetrics:
    """Metrics for prompt performance tracking"""
    success_rate: float = 0.0
    average_latency: float = 0.0
    average_cost: float = 0.0
    usage_count: int = 0
    last_updated: float = field(default_factory=time.time)
    
    def update(self, success: bool, latency: float, cost: float):
        """Update metrics with new data point"""
        self.usage_count += 1
        self.success_rate = ((self.success_rate * (self.usage_count - 1)) + (1 if success else 0)) / self.usage_count
        self.average_latency = ((self.average_latency * (self.usage_count - 1)) + latency) / self.usage_count
        self.average_cost = ((self.average_cost * (self.usage_count - 1)) + cost) / self.usage_count
        self.last_updated = time.time()


@dataclass
class PromptTemplate:
    """Prompt template with metadata and versioning"""
    name: str
    template: str
    version: str
    description: str
    variables: List[str]
    provider: str = "openai"
    model: str = "gpt-4-turbo"
    max_tokens: int = 1000
    temperature: float = 0.7
    system_prompt: str = ""
    metrics: PromptMetrics = field(default_factory=PromptMetrics)
    created_at: float = field(default_factory=time.time)
    
    def format(self, **kwargs) -> str:
        """Format template with provided variables"""
        try:
            return self.template.format(**kwargs)
        except KeyError as e:
            raise ValueError(f"Missing required variable: {e}")
    
    def validate_variables(self, **kwargs) -> bool:
        """Validate that all required variables are provided"""
        missing_vars = [var for var in self.variables if var not in kwargs]
        if missing_vars:
            raise ValueError(f"Missing required variables: {missing_vars}")
        return True


class PromptRegistry:
    """Registry for managing prompt templates"""
    
    def __init__(self):
        self.templates: Dict[str, Dict[str, PromptTemplate]] = {}
        self._initialize_default_templates()
    
    def _initialize_default_templates(self):
        """Initialize default prompt templates"""
        
        # Brand Analysis Template
        self.register_template(PromptTemplate(
            name="brand_analysis",
            template="""Analyze the following website content and extract key brand information.

Website Content:
{website_content}

Please provide a structured analysis covering:

1. Brand Name: The primary brand name
2. Industry: What industry/sector is this brand in?
3. Target Audience: Who is their primary target audience?
4. Value Proposition: What unique value do they offer?
5. Key Messages: What are their main marketing messages?
6. Competitors: Who are their likely competitors?

Format your response as:
Brand Name: [brand name]
Industry: [industry]
Target Audience: [target audience description]
Value Proposition: [unique value proposition]
Key Messages: [key marketing messages]
Competitors: [list of competitors]

Be concise and focus on the most important information.""",
            version="1.0",
            description="Analyzes website content to extract brand identity information",
            variables=["website_content"],
            max_tokens=800,
            temperature=0.3,
            system_prompt="You are an expert brand strategist analyzing website content to extract key brand information."
        ))
        
        # Brand Voice Analysis Template
        self.register_template(PromptTemplate(
            name="brand_voice_analysis",
            template="""Analyze the following brand content to determine the brand's voice and tone characteristics.

Brand Content:
{brand_content}

Please analyze and provide:

1. Overall Tone: (e.g., professional, casual, friendly, authoritative)
2. Personality Traits: List 3-5 key personality traits
3. Communication Style: How they communicate with their audience
4. Formality Level: Scale from 1 (very casual) to 5 (very formal)
5. Language Dos: What language patterns they should use
6. Language Don'ts: What they should avoid
7. Sample Phrases: 3-5 phrases that exemplify their voice

Format your response clearly with headers for each section.""",
            version="1.0",
            description="Analyzes brand content to determine voice and tone characteristics",
            variables=["brand_content"],
            max_tokens=600,
            temperature=0.4,
            system_prompt="You are an expert brand voice analyst. Focus on identifying consistent patterns in tone, style, and personality."
        ))
        
        # Content Pillars Identification Template
        self.register_template(PromptTemplate(
            name="content_pillars_identification",
            template="""Based on the following website content, identify 3-5 content pillars that would work well for this brand's social media and marketing strategy.

Website Content:
{website_content}

Content pillars should be:
- Broad enough for multiple content pieces
- Aligned with the brand's expertise and offerings
- Engaging for their target audience
- Suitable for various content formats (video, posts, articles)

For each pillar, provide:
1. Pillar Name: Clear, concise name
2. Description: What this pillar covers
3. Content Types: Types of content that fit (video, blog, infographic, etc.)
4. Keywords: 3-5 relevant keywords
5. Target Audience: Who this pillar appeals to most

Format each pillar clearly with these sections.""",
            version="1.0",
            description="Identifies content pillars for brand's content strategy",
            variables=["website_content"],
            max_tokens=700,
            temperature=0.4,
            system_prompt="You are a content strategist expert at identifying engaging content themes for brands."
        ))
        
        # Viral Hook Generation Template
        self.register_template(PromptTemplate(
            name="viral_hook_generation",
            template="""Generate viral hooks for social media content based on the following parameters:

Brand: {brand_name}
Industry: {industry}
Content Pillar: {content_pillar}
Target Audience: {target_audience}

Create 5 different viral hooks that:
- Grab attention in the first 3 seconds
- Are relevant to the brand and audience
- Use proven viral patterns (curiosity, controversy, emotion, etc.)
- Are platform-appropriate for {platform}

Viral patterns to consider:
- "3 mistakes you're making..."
- "The truth about..."
- "What nobody tells you about..."
- "I tried X for 30 days..."
- "Why everyone is wrong about..."

For each hook, provide:
1. Hook text
2. Viral pattern used
3. Expected emotion (curiosity, surprise, fear, etc.)
4. Estimated viral score (1-10)

Format clearly with numbers for each hook.""",
            version="1.0",
            description="Generates viral hooks for social media content",
            variables=["brand_name", "industry", "content_pillar", "target_audience", "platform"],
            max_tokens=800,
            temperature=0.8,
            system_prompt="You are a viral content expert who understands what makes content spread on social media."
        ))
        
        # Viral Scoring Template
        self.register_template(PromptTemplate(
            name="viral_scoring",
            template="""Score the viral potential of this content hook on a scale of 1-10.

Hook: {hook}
Platform: {platform}
Target Audience: {target_audience}

Evaluate based on these criteria:
1. Attention-grabbing power (1-10)
2. Emotional impact (1-10)
3. Curiosity/intrigue factor (1-10)
4. Shareability potential (1-10)
5. Platform appropriateness (1-10)
6. Trend alignment (1-10)

Provide:
- Overall viral score (1-10)
- Breakdown of each criteria score
- Key strengths
- Areas for improvement
- Suggestions to increase viral potential

Be honest and critical in your assessment.""",
            version="1.0",
            description="Scores content hooks for viral potential",
            variables=["hook", "platform", "target_audience"],
            max_tokens=500,
            temperature=0.3,
            system_prompt="You are a social media analytics expert who can predict content performance."
        ))
        
        # Script Generation Template
        self.register_template(PromptTemplate(
            name="script_generation",
            template="""Create a detailed video script based on the following brief:

Hook: {hook}
Brand: {brand_name}
Duration: {duration} seconds
Platform: {platform}
Call-to-Action: {cta}

Brand Voice Guidelines:
{brand_voice}

Create a script that includes:
1. Opening Hook (first 3 seconds)
2. Main Content (problem/solution/story)
3. Value Delivery
4. Call-to-Action
5. Closing

For each section, provide:
- Spoken content (what to say)
- Visual direction (what to show)
- Timing (seconds)
- Emotional tone

Keep the total duration to {duration} seconds.
Make it engaging, on-brand, and conversion-focused.

Format with clear sections and timing markers.""",
            version="1.0",
            description="Generates detailed video scripts with timing and visual direction",
            variables=["hook", "brand_name", "duration", "platform", "cta", "brand_voice"],
            max_tokens=1200,
            temperature=0.6,
            system_prompt="You are a professional video script writer who creates engaging, conversion-focused content."
        ))
        
        # Shot List Creation Template
        self.register_template(PromptTemplate(
            name="shot_list_creation",
            template="""Create a detailed shot list for this video script:

Script:
{script}

Video Duration: {duration} seconds
Platform: {platform}
Brand: {brand_name}

Create a shot-by-shot breakdown including:
1. Shot number
2. Duration (seconds)
3. Shot type (close-up, wide shot, medium shot, etc.)
4. Camera angle
5. Visual description
6. Audio/dialogue
7. Props/elements needed
8. Lighting notes
9. Transition to next shot

Consider:
- Platform-specific requirements ({platform} format)
- Visual storytelling flow
- Brand consistency
- Production feasibility
- Engagement optimization

Format as a numbered list with all details for each shot.""",
            version="1.0",
            description="Creates detailed shot lists for video production",
            variables=["script", "duration", "platform", "brand_name"],
            max_tokens=1000,
            temperature=0.4,
            system_prompt="You are a professional video director creating detailed shot lists for production teams."
        ))
        
        # Caption Optimization Template
        self.register_template(PromptTemplate(
            name="caption_optimization",
            template="""Optimize this social media caption for maximum engagement:

Original Caption: {original_caption}
Platform: {platform}
Brand: {brand_name}
Target Audience: {target_audience}
Content Type: {content_type}

Brand Voice:
{brand_voice}

Create an optimized caption that:
- Maintains brand voice
- Increases engagement potential
- Includes relevant hashtags
- Has a clear call-to-action
- Is platform-appropriate
- Uses engaging formatting

Provide:
1. Optimized caption
2. Hashtag recommendations (5-10)
3. Explanation of changes made
4. Expected engagement improvements

Keep platform character limits in mind.""",
            version="1.0",
            description="Optimizes social media captions for engagement",
            variables=["original_caption", "platform", "brand_name", "target_audience", "content_type", "brand_voice"],
            max_tokens=600,
            temperature=0.6,
            system_prompt="You are a social media expert focused on optimizing content for maximum engagement."
        ))
        
        # Performance Analysis Template
        self.register_template(PromptTemplate(
            name="performance_analysis",
            template="""Analyze the performance data and provide insights and recommendations:

Content Performance Data:
{performance_data}

Brand: {brand_name}
Time Period: {time_period}
Platform: {platform}

Analyze:
1. Top performing content patterns
2. Engagement trends
3. Audience behavior insights
4. Content type performance
5. Posting time optimization
6. Hashtag effectiveness

Provide:
- Key insights (3-5 bullet points)
- Performance trends
- Content recommendations
- Optimization opportunities
- Predicted performance improvements
- Action items for next period

Be specific and actionable in your recommendations.""",
            version="1.0",
            description="Analyzes content performance and provides optimization insights",
            variables=["performance_data", "brand_name", "time_period", "platform"],
            max_tokens=800,
            temperature=0.3,
            system_prompt="You are a data analyst expert at interpreting social media performance metrics and providing actionable insights."
        ))
        
        # Trend Analysis Template
        self.register_template(PromptTemplate(
            name="trend_analysis",
            template="""Analyze trending topics and identify opportunities for {brand_name}.

Industry: {industry}
Target Audience: {target_audience}
Current Trends: {trends_data}
Brand Voice: {brand_voice}

Analysis Requirements:
1. Trend relevance to brand and industry
2. Opportunity assessment (effort vs. impact)
3. Content creation recommendations
4. Hashtag and keyword suggestions
5. Platform-specific strategies
6. Timing and urgency considerations
7. Risk assessment
8. Expected outcomes

Provide detailed analysis with specific action items for each relevant trend.""",
            version="1.0",
            description="Analyzes trends and identifies brand opportunities",
            variables=["brand_name", "industry", "target_audience", "trends_data", "brand_voice"],
            max_tokens=1000,
            temperature=0.4,
            system_prompt="You are a trend analysis expert who identifies viral opportunities and strategic brand positioning."
        ))
        
        # Competitor Analysis Template
        self.register_template(PromptTemplate(
            name="competitor_analysis",
            template="""Analyze competitor performance and identify strategic opportunities.

Brand: {brand_name}
Industry: {industry}
Competitor Data: {competitor_data}
Own Performance: {own_performance_data}

Analysis Focus:
1. Competitive positioning assessment
2. Content gap identification
3. Strategy differentiation opportunities
4. Performance benchmarking
5. Audience overlap analysis
6. Successful competitor tactics
7. Market positioning recommendations
8. Strategic advantages to leverage

Provide comprehensive competitive intelligence with actionable recommendations.""",
            version="1.0",
            description="Provides competitive analysis and strategic recommendations",
            variables=["brand_name", "industry", "competitor_data", "own_performance_data"],
            max_tokens=900,
            temperature=0.3,
            system_prompt="You are a competitive intelligence analyst expert at identifying market opportunities and strategic positioning."
        ))
        
        # Brand Voice Extraction Template
        self.register_template(PromptTemplate(
            name="brand_voice_extraction",
            template="""Analyze the brand's website and content to extract brand voice characteristics.

Brand: {brand_name}
Website Content: {website_content}
Industry: {industry}

Extract and define:
1. Tone and personality traits
2. Communication style preferences
3. Key messaging themes
4. Language patterns and vocabulary
5. Emotional positioning
6. Value propositions
7. Brand do's and don'ts
8. Target audience communication approach

Format as a comprehensive brand voice guide with specific examples and guidelines.""",
            version="1.0",
            description="Extracts brand voice characteristics from website content",
            variables=["brand_name", "website_content", "industry"],
            max_tokens=800,
            temperature=0.3,
            system_prompt="You are a brand voice specialist expert at identifying and codifying brand communication patterns."
        ))
        
        # Content Optimization Template
        self.register_template(PromptTemplate(
            name="content_optimization",
            template="""Optimize this content for maximum engagement and brand alignment.

Original Content: {original_content}
Brand: {brand_name}
Platform: {platform}
Target Audience: {target_audience}
Goals: {optimization_goals}
Brand Voice: {brand_voice}

Optimization Areas:
1. Hook and opening optimization
2. Structure and flow improvement
3. Engagement enhancement tactics
4. Call-to-action optimization
5. Hashtag strategy
6. Platform-specific adjustments
7. Brand voice alignment
8. Audience targeting refinement

Provide optimized version with detailed explanation of changes and expected impact.""",
            version="1.0",
            description="Optimizes content for engagement and brand alignment",
            variables=["original_content", "brand_name", "platform", "target_audience", "optimization_goals", "brand_voice"],
            max_tokens=800,
            temperature=0.5,
            system_prompt="You are a content optimization expert specializing in viral social media content and brand alignment."
        ))
        
        # Viral Pattern Analysis Template
        self.register_template(PromptTemplate(
            name="viral_pattern_analysis",
            template="""Analyze viral content patterns and generate similar content concepts.

Viral Content Examples: {viral_examples}
Brand: {brand_name}
Industry: {industry}
Target Platform: {platform}

Pattern Analysis:
1. Common viral elements identification
2. Emotional triggers analysis
3. Structural patterns
4. Timing and context factors
5. Audience psychology insights
6. Shareability factors
7. Platform-specific viral mechanics
8. Replication strategies for brand

Generate 5 content concepts that apply these viral patterns while maintaining brand authenticity.""",
            version="1.0",
            description="Analyzes viral patterns and generates content concepts",
            variables=["viral_examples", "brand_name", "industry", "platform"],
            max_tokens=900,
            temperature=0.6,
            system_prompt="You are a viral content expert who understands the psychology and mechanics behind viral social media content."
        ))
    
    def register_template(self, template: PromptTemplate):
        """Register a new prompt template"""
        if template.name not in self.templates:
            self.templates[template.name] = {}
        
        self.templates[template.name][template.version] = template
        logger.info(f"Registered prompt template: {template.name} v{template.version}")
    
    def get_template(self, name: str, version: str = None) -> Optional[PromptTemplate]:
        """Get a specific prompt template"""
        if name not in self.templates:
            return None
        
        if version:
            return self.templates[name].get(version)
        else:
            # Return latest version
            versions = list(self.templates[name].keys())
            if versions:
                latest_version = max(versions)
                return self.templates[name][latest_version]
        
        return None
    
    def list_templates(self) -> List[str]:
        """List all available template names"""
        return list(self.templates.keys())
    
    def get_template_versions(self, name: str) -> List[str]:
        """Get all versions of a template"""
        return list(self.templates.get(name, {}).keys())
    
    def update_metrics(self, name: str, version: str, success: bool, latency: float, cost: float):
        """Update template metrics"""
        template = self.get_template(name, version)
        if template:
            template.metrics.update(success, latency, cost)
    
    def get_best_performing_template(self, name: str) -> Optional[PromptTemplate]:
        """Get the best performing version of a template"""
        if name not in self.templates:
            return None
        
        best_template = None
        best_score = 0
        
        for template in self.templates[name].values():
            # Score based on success rate and usage
            score = template.metrics.success_rate * (1 + min(template.metrics.usage_count / 100, 1))
            if score > best_score:
                best_score = score
                best_template = template
        
        return best_template or self.get_template(name)  # Fallback to latest


# Global registry instance
_prompt_registry: Optional[PromptRegistry] = None


def get_prompt_registry() -> PromptRegistry:
    """Get global prompt registry instance"""
    global _prompt_registry
    if _prompt_registry is None:
        _prompt_registry = PromptRegistry()
    return _prompt_registry


async def get_prompt_template(name: str, version: str = None) -> PromptTemplate:
    """Get a prompt template by name and version"""
    registry = get_prompt_registry()
    template = registry.get_template(name, version)
    
    if not template:
        raise ValueError(f"Prompt template '{name}' not found")
    
    return template


class PromptOptimizer:
    """Optimizes prompts through A/B testing and performance analysis"""
    
    def __init__(self):
        self.registry = get_prompt_registry()
        self.ab_tests: Dict[str, Dict[str, Any]] = {}
    
    def start_ab_test(self, template_name: str, variant_a: str, variant_b: str, traffic_split: float = 0.5):
        """Start an A/B test between two template versions"""
        self.ab_tests[template_name] = {
            "variant_a": variant_a,
            "variant_b": variant_b,
            "traffic_split": traffic_split,
            "start_time": time.time(),
            "metrics_a": {"requests": 0, "successes": 0, "total_cost": 0, "total_latency": 0},
            "metrics_b": {"requests": 0, "successes": 0, "total_cost": 0, "total_latency": 0}
        }
        
        logger.info(f"Started A/B test for {template_name}: {variant_a} vs {variant_b}")
    
    def get_test_variant(self, template_name: str) -> str:
        """Get which variant to use for this request"""
        if template_name not in self.ab_tests:
            return None
        
        test = self.ab_tests[template_name]
        import random
        
        if random.random() < test["traffic_split"]:
            return test["variant_a"]
        else:
            return test["variant_b"]
    
    def record_result(self, template_name: str, version: str, success: bool, cost: float, latency: float):
        """Record A/B test result"""
        if template_name not in self.ab_tests:
            return
        
        test = self.ab_tests[template_name]
        
        if version == test["variant_a"]:
            metrics = test["metrics_a"]
        elif version == test["variant_b"]:
            metrics = test["metrics_b"]
        else:
            return
        
        metrics["requests"] += 1
        if success:
            metrics["successes"] += 1
        metrics["total_cost"] += cost
        metrics["total_latency"] += latency
    
    def analyze_test_results(self, template_name: str) -> Dict[str, Any]:
        """Analyze A/B test results"""
        if template_name not in self.ab_tests:
            return {}
        
        test = self.ab_tests[template_name]
        metrics_a = test["metrics_a"]
        metrics_b = test["metrics_b"]
        
        def calculate_stats(metrics):
            if metrics["requests"] == 0:
                return {"success_rate": 0, "avg_cost": 0, "avg_latency": 0}
            
            return {
                "success_rate": metrics["successes"] / metrics["requests"],
                "avg_cost": metrics["total_cost"] / metrics["requests"],
                "avg_latency": metrics["total_latency"] / metrics["requests"],
                "total_requests": metrics["requests"]
            }
        
        stats_a = calculate_stats(metrics_a)
        stats_b = calculate_stats(metrics_b)
        
        # Determine winner
        winner = None
        if stats_a["success_rate"] > stats_b["success_rate"]:
            winner = test["variant_a"]
        elif stats_b["success_rate"] > stats_a["success_rate"]:
            winner = test["variant_b"]
        
        return {
            "template_name": template_name,
            "variant_a": test["variant_a"],
            "variant_b": test["variant_b"],
            "stats_a": stats_a,
            "stats_b": stats_b,
            "winner": winner,
            "test_duration_hours": (time.time() - test["start_time"]) / 3600,
            "statistical_significance": self._calculate_significance(stats_a, stats_b)
        }
    
    def _calculate_significance(self, stats_a: Dict, stats_b: Dict) -> bool:
        """Calculate if results are statistically significant (simplified)"""
        # This is a simplified significance test
        # In production, use proper statistical tests
        min_sample_size = 30
        min_difference = 0.05
        
        if (stats_a["total_requests"] < min_sample_size or 
            stats_b["total_requests"] < min_sample_size):
            return False
        
        diff = abs(stats_a["success_rate"] - stats_b["success_rate"])
        return diff > min_difference


# Global optimizer instance
_prompt_optimizer: Optional[PromptOptimizer] = None


def get_prompt_optimizer() -> PromptOptimizer:
    """Get global prompt optimizer instance"""
    global _prompt_optimizer
    if _prompt_optimizer is None:
        _prompt_optimizer = PromptOptimizer()
    return _prompt_optimizer