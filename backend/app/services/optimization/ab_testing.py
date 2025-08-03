import asyncio
import logging
from typing import Dict, List, Optional, Tuple, Any, Union
from datetime import datetime, timedelta
import json
import numpy as np
from dataclasses import dataclass
from sqlalchemy.orm import Session
from sqlalchemy import and_, desc
import scipy.stats as stats
from enum import Enum

from app.models.analytics import ABTestExperiment, ABTestVariant, ExperimentStatus, PlatformType
from app.models.content import Video
from app.models.brand import Brand
from app.core.config import settings
from app.db.session import SessionLocal
from app.services.ai.providers import get_text_service

logger = logging.getLogger(__name__)

class VariantType(str, Enum):
    HOOK = "hook"
    CTA = "cta"
    TEXT_OVERLAY = "text_overlay"
    AUDIO = "audio"
    FILTER = "filter"
    TIMING = "timing"
    COLOR_GRADING = "color_grading"

@dataclass
class VariationConfig:
    """Configuration for variant generation"""
    element_type: VariantType
    variation_count: int = 3
    preserve_brand_voice: bool = True
    target_audience: Optional[str] = None
    platform_specific: bool = True
    creativity_level: float = 0.7  # 0.0 = conservative, 1.0 = very creative

@dataclass
class ABTestConfig:
    """Configuration for A/B test setup"""
    test_name: str
    hypothesis: str
    success_metrics: List[str]
    traffic_split: Dict[str, float]
    minimum_sample_size: int
    confidence_level: float = 0.95
    statistical_power: float = 0.8
    planned_duration_days: int = 7
    auto_winner_selection: bool = True

@dataclass
class StatisticalResult:
    """Statistical analysis result"""
    is_significant: bool
    p_value: float
    confidence_interval: Tuple[float, float]
    effect_size: float
    winner_variant: Optional[str]
    improvement_percent: float

class ABTestingService:
    """Automated A/B testing and variant generation service"""
    
    def __init__(self):
        self.ai_provider = None
    
    async def _initialize(self):
        """Initialize async components"""
        if self.ai_provider is None:
            self.ai_provider = await get_text_service()
        self.variant_generators = {
            VariantType.HOOK: HookVariantGenerator(),
            VariantType.CTA: CTAVariantGenerator(),
            VariantType.TEXT_OVERLAY: TextOverlayVariantGenerator(),
            VariantType.AUDIO: AudioVariantGenerator(),
            VariantType.FILTER: FilterVariantGenerator(),
            VariantType.TIMING: TimingVariantGenerator(),
            VariantType.COLOR_GRADING: ColorGradingVariantGenerator()
        }
        
        # Statistical analysis configuration
        self.min_sample_size = 100
        self.alpha = 0.05  # Significance level
        self.power = 0.8   # Statistical power
    
    async def create_ab_test(
        self,
        original_video_id: int,
        brand_id: int,
        campaign_id: int,
        test_config: ABTestConfig,
        variation_configs: List[VariationConfig]
    ) -> ABTestExperiment:
        """
        Create a new A/B test with automatically generated variants
        
        Args:
            original_video_id: ID of the original video to test
            brand_id: Brand ID
            campaign_id: Campaign ID  
            test_config: A/B test configuration
            variation_configs: List of variation configurations
            
        Returns:
            Created A/B test experiment
        """
        await self._initialize()
        try:
            db = SessionLocal()
            
            # Create experiment
            experiment = ABTestExperiment(
                campaign_id=campaign_id,
                brand_id=brand_id,
                name=test_config.test_name,
                hypothesis=test_config.hypothesis,
                status=ExperimentStatus.DRAFT,
                traffic_split=test_config.traffic_split,
                success_metrics=test_config.success_metrics,
                minimum_sample_size=test_config.minimum_sample_size,
                confidence_level=test_config.confidence_level,
                statistical_power=test_config.statistical_power,
                planned_duration_days=test_config.planned_duration_days
            )
            
            db.add(experiment)
            db.flush()  # Get the experiment ID
            
            # Create control variant (original video)
            control_variant = ABTestVariant(
                experiment_id=experiment.id,
                video_id=original_video_id,
                variant_name="control",
                variant_type="original",
                description="Original video (control group)",
                modifications={}
            )
            db.add(control_variant)
            
            # Generate test variants
            variants = await self._generate_variants(
                original_video_id, 
                experiment.id, 
                variation_configs,
                brand_id
            )
            
            for variant in variants:
                db.add(variant)
            
            db.commit()
            
            logger.info(f"Created A/B test '{test_config.test_name}' with {len(variants) + 1} variants")
            
            return experiment
            
        except Exception as e:
            logger.error(f"Error creating A/B test: {e}")
            db.rollback()
            raise
        finally:
            db.close()
    
    async def _generate_variants(
        self,
        original_video_id: int,
        experiment_id: int,
        variation_configs: List[VariationConfig],
        brand_id: int
    ) -> List[ABTestVariant]:
        """Generate variants based on configuration"""
        variants = []
        
        # Get original video data
        original_video = await self._get_video_data(original_video_id)
        brand_info = await self._get_brand_info(brand_id)
        
        variant_counter = 1
        
        for config in variation_configs:
            generator = self.variant_generators.get(config.element_type)
            if not generator:
                logger.warning(f"No generator available for {config.element_type}")
                continue
            
            # Generate variations
            variations = await generator.generate_variations(
                original_video, 
                config, 
                brand_info
            )
            
            for i, variation in enumerate(variations):
                variant = ABTestVariant(
                    experiment_id=experiment_id,
                    video_id=original_video_id,  # Will be updated when variant video is created
                    variant_name=f"variant_{variant_counter}",
                    variant_type=config.element_type.value,
                    description=variation['description'],
                    modifications=variation['modifications'],
                    generation_prompt=variation.get('prompt', '')
                )
                
                variants.append(variant)
                variant_counter += 1
        
        return variants
    
    async def start_experiment(self, experiment_id: int) -> ABTestExperiment:
        """Start an A/B test experiment"""
        try:
            db = SessionLocal()
            
            experiment = db.query(ABTestExperiment).filter(
                ABTestExperiment.id == experiment_id
            ).first()
            
            if not experiment:
                raise ValueError(f"Experiment {experiment_id} not found")
            
            if experiment.status != ExperimentStatus.DRAFT:
                raise ValueError(f"Cannot start experiment in status {experiment.status}")
            
            # Validate experiment setup
            await self._validate_experiment(experiment)
            
            # Start the experiment
            experiment.status = ExperimentStatus.RUNNING
            experiment.start_date = datetime.now()
            experiment.end_date = datetime.now() + timedelta(days=experiment.planned_duration_days)
            
            db.commit()
            
            logger.info(f"Started A/B test experiment {experiment_id}")
            
            return experiment
            
        except Exception as e:
            logger.error(f"Error starting experiment: {e}")
            db.rollback()
            raise
        finally:
            db.close()
    
    async def analyze_experiment(self, experiment_id: int) -> Dict[str, Any]:
        """Analyze A/B test results and determine statistical significance"""
        try:
            db = SessionLocal()
            
            experiment = db.query(ABTestExperiment).filter(
                ABTestExperiment.id == experiment_id
            ).first()
            
            if not experiment:
                raise ValueError(f"Experiment {experiment_id} not found")
            
            # Get all variants with their performance data
            variants = db.query(ABTestVariant).filter(
                ABTestVariant.experiment_id == experiment_id
            ).all()
            
            if len(variants) < 2:
                raise ValueError("Need at least 2 variants for analysis")
            
            # Perform statistical analysis
            analysis_results = {}
            
            for metric in experiment.success_metrics:
                metric_analysis = await self._analyze_metric(variants, metric)
                analysis_results[metric] = metric_analysis
            
            # Determine overall winner
            winner_analysis = await self._determine_winner(variants, experiment.success_metrics)
            
            # Update experiment with results
            experiment.statistical_significance = winner_analysis.get('max_significance', 0.0)
            experiment.winner_variant = winner_analysis.get('winner_variant')
            experiment.confidence_interval = winner_analysis.get('confidence_interval')
            experiment.results_summary = {
                'analysis_date': datetime.now().isoformat(),
                'metric_results': analysis_results,
                'winner_analysis': winner_analysis,
                'sample_sizes': {v.variant_name: v.impressions for v in variants}
            }
            
            # Auto-complete if significant results and minimum sample size reached
            if (winner_analysis.get('is_significant', False) and 
                all(v.impressions >= experiment.minimum_sample_size for v in variants)):
                
                if experiment.planned_duration_days <= 0:  # Auto-completion enabled
                    experiment.status = ExperimentStatus.COMPLETED
                    logger.info(f"Auto-completed experiment {experiment_id} - significant results detected")
            
            db.commit()
            
            return {
                'experiment_id': experiment_id,
                'status': experiment.status.value,
                'analysis_results': analysis_results,
                'winner_analysis': winner_analysis,
                'recommendations': await self._generate_experiment_recommendations(experiment, variants)
            }
            
        except Exception as e:
            logger.error(f"Error analyzing experiment: {e}")
            raise
        finally:
            db.close()
    
    async def _analyze_metric(self, variants: List[ABTestVariant], metric: str) -> Dict[str, Any]:
        """Analyze a specific metric across variants"""
        # Get control variant (usually first or named 'control')
        control = next((v for v in variants if v.variant_name == 'control'), variants[0])
        
        results = {
            'metric': metric,
            'control_value': self._get_metric_value(control, metric),
            'variants': []
        }
        
        for variant in variants:
            if variant.variant_name == 'control':
                continue
            
            # Perform statistical test
            stat_result = await self._perform_statistical_test(control, variant, metric)
            
            variant_result = {
                'variant_name': variant.variant_name,
                'value': self._get_metric_value(variant, metric),
                'improvement': stat_result.improvement_percent,
                'is_significant': stat_result.is_significant,
                'p_value': stat_result.p_value,
                'confidence_interval': stat_result.confidence_interval,
                'sample_size': variant.impressions
            }
            
            results['variants'].append(variant_result)
        
        return results
    
    async def _perform_statistical_test(
        self, 
        control: ABTestVariant, 
        variant: ABTestVariant, 
        metric: str
    ) -> StatisticalResult:
        """Perform statistical test between control and variant"""
        
        # Get metric values
        control_value = self._get_metric_value(control, metric)
        variant_value = self._get_metric_value(variant, metric)
        
        control_n = control.impressions
        variant_n = variant.impressions
        
        if control_n < 30 or variant_n < 30:
            # Insufficient sample size
            return StatisticalResult(
                is_significant=False,
                p_value=1.0,
                confidence_interval=(0.0, 0.0),
                effect_size=0.0,
                winner_variant=None,
                improvement_percent=0.0
            )
        
        # Choose appropriate test based on metric type
        if metric in ['conversion_rate', 'click_through_rate', 'engagement_rate']:
            # Proportion test
            return await self._proportion_test(control, variant, metric)
        else:
            # Mean test
            return await self._mean_test(control, variant, metric)
    
    async def _proportion_test(
        self, 
        control: ABTestVariant, 
        variant: ABTestVariant, 
        metric: str
    ) -> StatisticalResult:
        """Perform proportion test (for rates/percentages)"""
        
        # Get counts and sample sizes
        if metric == 'conversion_rate':
            control_successes = control.conversions
            variant_successes = variant.conversions
        elif metric == 'click_through_rate':
            control_successes = control.clicks  
            variant_successes = variant.clicks
        elif metric == 'engagement_rate':
            control_successes = int(control.engagement_rate * control.impressions)
            variant_successes = int(variant.engagement_rate * variant.impressions)
        else:
            control_successes = 0
            variant_successes = 0
        
        control_n = control.impressions
        variant_n = variant.impressions
        
        # Perform two-proportion z-test
        count = np.array([control_successes, variant_successes])
        nobs = np.array([control_n, variant_n])
        
        try:
            stat, p_value = stats.proportions_ztest(count, nobs)
            
            # Calculate proportions
            p1 = control_successes / control_n if control_n > 0 else 0
            p2 = variant_successes / variant_n if variant_n > 0 else 0
            
            # Calculate confidence interval for difference
            se = np.sqrt(p1 * (1 - p1) / control_n + p2 * (1 - p2) / variant_n)
            diff = p2 - p1
            margin_error = stats.norm.ppf(0.975) * se
            ci_lower = diff - margin_error
            ci_upper = diff + margin_error
            
            # Calculate improvement percentage
            improvement = ((p2 - p1) / p1 * 100) if p1 > 0 else 0
            
            # Effect size (Cohen's h for proportions)
            effect_size = 2 * (np.arcsin(np.sqrt(p2)) - np.arcsin(np.sqrt(p1)))
            
            return StatisticalResult(
                is_significant=p_value < self.alpha,
                p_value=p_value,
                confidence_interval=(ci_lower, ci_upper),
                effect_size=abs(effect_size),
                winner_variant=variant.variant_name if p2 > p1 and p_value < self.alpha else None,
                improvement_percent=improvement
            )
            
        except Exception as e:
            logger.error(f"Error in proportion test: {e}")
            return StatisticalResult(
                is_significant=False,
                p_value=1.0,
                confidence_interval=(0.0, 0.0),
                effect_size=0.0,
                winner_variant=None,
                improvement_percent=0.0
            )
    
    async def _mean_test(
        self, 
        control: ABTestVariant, 
        variant: ABTestVariant, 
        metric: str
    ) -> StatisticalResult:
        """Perform t-test for means"""
        
        # For simplicity, we'll use sample statistics
        # In production, you'd want the raw data points
        
        control_mean = self._get_metric_value(control, metric)
        variant_mean = self._get_metric_value(variant, metric)
        
        # Estimate standard deviations (simplified)
        control_std = control_mean * 0.3  # Rough estimate
        variant_std = variant_mean * 0.3
        
        control_n = control.impressions
        variant_n = variant.impressions
        
        # Welch's t-test (unequal variances)
        try:
            se1 = control_std / np.sqrt(control_n)
            se2 = variant_std / np.sqrt(variant_n)
            se_diff = np.sqrt(se1**2 + se2**2)
            
            t_stat = (variant_mean - control_mean) / se_diff
            
            # Degrees of freedom (Welch-Satterthwaite equation)
            df = (se1**2 + se2**2)**2 / (se1**4 / (control_n - 1) + se2**4 / (variant_n - 1))
            
            p_value = 2 * (1 - stats.t.cdf(abs(t_stat), df))
            
            # Confidence interval
            margin_error = stats.t.ppf(0.975, df) * se_diff
            ci_lower = (variant_mean - control_mean) - margin_error
            ci_upper = (variant_mean - control_mean) + margin_error
            
            # Improvement percentage
            improvement = ((variant_mean - control_mean) / control_mean * 100) if control_mean > 0 else 0
            
            # Effect size (Cohen's d)
            pooled_std = np.sqrt(((control_n - 1) * control_std**2 + (variant_n - 1) * variant_std**2) / (control_n + variant_n - 2))
            effect_size = abs(variant_mean - control_mean) / pooled_std if pooled_std > 0 else 0
            
            return StatisticalResult(
                is_significant=p_value < self.alpha,
                p_value=p_value,
                confidence_interval=(ci_lower, ci_upper),
                effect_size=effect_size,
                winner_variant=variant.variant_name if variant_mean > control_mean and p_value < self.alpha else None,
                improvement_percent=improvement
            )
            
        except Exception as e:
            logger.error(f"Error in mean test: {e}")
            return StatisticalResult(
                is_significant=False,
                p_value=1.0,
                confidence_interval=(0.0, 0.0),
                effect_size=0.0,
                winner_variant=None,
                improvement_percent=0.0
            )
    
    def _get_metric_value(self, variant: ABTestVariant, metric: str) -> float:
        """Extract metric value from variant"""
        if metric == 'conversion_rate':
            return variant.conversion_rate
        elif metric == 'click_through_rate':
            return variant.clicks / variant.impressions if variant.impressions > 0 else 0
        elif metric == 'engagement_rate':
            return variant.engagement_rate
        elif metric == 'cost_per_result':
            return variant.cost_per_result or 0
        else:
            return 0.0
    
    async def _determine_winner(
        self, 
        variants: List[ABTestVariant], 
        success_metrics: List[str]
    ) -> Dict[str, Any]:
        """Determine overall experiment winner"""
        
        # Score each variant across all metrics
        variant_scores = {}
        significance_results = {}
        
        control = next((v for v in variants if v.variant_name == 'control'), variants[0])
        
        for variant in variants:
            if variant.variant_name == 'control':
                continue
            
            total_score = 0
            significant_improvements = 0
            
            for metric in success_metrics:
                stat_result = await self._perform_statistical_test(control, variant, metric)
                
                # Score based on improvement and significance
                if stat_result.is_significant and stat_result.improvement_percent > 0:
                    score = stat_result.improvement_percent * (1 + stat_result.effect_size)
                    significant_improvements += 1
                else:
                    score = 0
                
                total_score += score
                significance_results[f"{variant.variant_name}_{metric}"] = stat_result
            
            variant_scores[variant.variant_name] = {
                'total_score': total_score,
                'significant_improvements': significant_improvements,
                'avg_improvement': total_score / len(success_metrics)
            }
        
        # Find winner
        winner = None
        max_score = 0
        max_significance = 0
        
        for variant_name, score_data in variant_scores.items():
            if (score_data['significant_improvements'] > 0 and 
                score_data['total_score'] > max_score):
                winner = variant_name
                max_score = score_data['total_score']
                max_significance = max(max_significance, score_data['significant_improvements'])
        
        return {
            'winner_variant': winner,
            'is_significant': max_significance > 0,
            'max_significance': max_significance,
            'variant_scores': variant_scores,
            'statistical_results': {k: {
                'is_significant': v.is_significant,
                'p_value': v.p_value,
                'improvement_percent': v.improvement_percent
            } for k, v in significance_results.items()}
        }
    
    async def _validate_experiment(self, experiment: ABTestExperiment) -> bool:
        """Validate experiment setup before starting"""
        
        # Check if we have variants
        db = SessionLocal()
        try:
            variant_count = db.query(ABTestVariant).filter(
                ABTestVariant.experiment_id == experiment.id
            ).count()
            
            if variant_count < 2:
                raise ValueError("Need at least 2 variants (including control)")
            
            # Validate traffic split
            total_split = sum(experiment.traffic_split.values())
            if abs(total_split - 100.0) > 0.01:
                raise ValueError("Traffic split must sum to 100%")
            
            # Check if variants match traffic split
            if len(experiment.traffic_split) != variant_count:
                raise ValueError("Traffic split must include all variants")
            
            return True
            
        finally:
            db.close()
    
    async def _get_video_data(self, video_id: int) -> Dict[str, Any]:
        """Get video data for variant generation"""
        db = SessionLocal()
        try:
            video = db.query(Video).filter(Video.id == video_id).first()
            if not video:
                raise ValueError(f"Video {video_id} not found")
            
            return {
                'id': video.id,
                'script': getattr(video, 'script', ''),
                'hook': getattr(video, 'hook', ''),
                'cta': getattr(video, 'cta', ''),
                'style': getattr(video, 'style', {}),
                'metadata': getattr(video, 'metadata', {})
            }
        finally:
            db.close()
    
    async def _get_brand_info(self, brand_id: int) -> Dict[str, Any]:
        """Get brand information for variant generation"""
        db = SessionLocal()
        try:
            brand = db.query(Brand).filter(Brand.id == brand_id).first()
            if not brand:
                return {}
            
            return {
                'name': brand.name,
                'industry': getattr(brand, 'industry', ''),
                'brand_voice': getattr(brand, 'brand_voice', ''),
                'target_audience': getattr(brand, 'target_audience', ''),
                'guidelines': getattr(brand, 'guidelines', {})
            }
        finally:
            db.close()
    
    async def _generate_experiment_recommendations(
        self, 
        experiment: ABTestExperiment, 
        variants: List[ABTestVariant]
    ) -> List[str]:
        """Generate recommendations based on experiment results"""
        recommendations = []
        
        if experiment.winner_variant:
            winner = next((v for v in variants if v.variant_name == experiment.winner_variant), None)
            if winner:
                recommendations.append(f"Implement winning variant '{winner.variant_name}' - {winner.variant_type}")
                
                # Specific recommendations based on variant type
                if winner.variant_type == 'hook':
                    recommendations.append("Focus on hook optimization in future content")
                elif winner.variant_type == 'cta':
                    recommendations.append("Apply winning CTA strategy to other campaigns")
                elif winner.variant_type == 'text_overlay':
                    recommendations.append("Use similar text styling in future videos")
        
        # Sample size recommendations
        min_samples_reached = all(v.impressions >= experiment.minimum_sample_size for v in variants)
        if not min_samples_reached:
            recommendations.append("Increase sample size for more reliable results")
        
        # Duration recommendations
        if experiment.status == ExperimentStatus.RUNNING:
            days_running = (datetime.now() - experiment.start_date).days
            if days_running < 3:
                recommendations.append("Run test for at least 3-7 days for reliable results")
        
        return recommendations


# Variant Generator Classes

class BaseVariantGenerator:
    """Base class for variant generators"""
    
    def __init__(self):
        self.ai_provider = None
    
    async def _initialize(self):
        """Initialize async components"""
        if self.ai_provider is None:
            self.ai_provider = await get_text_service()
    
    async def generate_variations(
        self, 
        original_video: Dict[str, Any], 
        config: VariationConfig,
        brand_info: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Generate variations of a specific element"""
        raise NotImplementedError


class HookVariantGenerator(BaseVariantGenerator):
    """Generate hook variations for first 3 seconds"""
    
    async def generate_variations(
        self, 
        original_video: Dict[str, Any], 
        config: VariationConfig,
        brand_info: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        
        original_hook = original_video.get('hook', '')
        variations = []
        
        # Generate hook variations using AI
        prompt = f"""
        Create {config.variation_count} different hook variations for a video ad.
        
        Original hook: "{original_hook}"
        Brand: {brand_info.get('name', 'Unknown')}
        Industry: {brand_info.get('industry', 'General')}
        Target audience: {brand_info.get('target_audience', 'General')}
        Brand voice: {brand_info.get('brand_voice', 'Professional')}
        
        Generate variations that:
        1. Capture attention in the first 3 seconds
        2. Maintain brand voice consistency
        3. Are optimized for {config.target_audience or 'the target audience'}
        4. Test different psychological triggers (curiosity, urgency, social proof, etc.)
        
        Return as JSON array with structure:
        [
          {{
            "hook_text": "Hook variation text",
            "description": "Brief description of the approach",
            "psychological_trigger": "curiosity/urgency/social_proof/etc",
            "estimated_impact": "high/medium/low"
          }}
        ]
        """
        
        try:
            response = await self.ai_provider.generate_text(prompt)
            hook_variations = json.loads(response)
            
            for i, hook_var in enumerate(hook_variations):
                variations.append({
                    'description': f"Hook variation {i+1}: {hook_var.get('description')}",
                    'modifications': {
                        'element': 'hook',
                        'original_hook': original_hook,
                        'new_hook': hook_var.get('hook_text'),
                        'trigger_type': hook_var.get('psychological_trigger'),
                        'estimated_impact': hook_var.get('estimated_impact')
                    },
                    'prompt': prompt
                })
                
        except Exception as e:
            logger.error(f"Error generating hook variations: {e}")
            # Fallback to template-based variations
            variations = self._generate_hook_templates(original_hook, config.variation_count)
        
        return variations[:config.variation_count]
    
    def _generate_hook_templates(self, original_hook: str, count: int) -> List[Dict[str, Any]]:
        """Fallback template-based hook generation"""
        templates = [
            "Wait, did you know that {hook}?",
            "This might surprise you: {hook}",
            "Here's something most people don't realize: {hook}",
            "You won't believe what happens when {hook}",
            "The secret that changed everything: {hook}"
        ]
        
        variations = []
        for i in range(min(count, len(templates))):
            variations.append({
                'description': f"Template hook variation {i+1}",
                'modifications': {
                    'element': 'hook',
                    'original_hook': original_hook,
                    'new_hook': templates[i].format(hook=original_hook),
                    'template_used': templates[i]
                }
            })
        
        return variations


class CTAVariantGenerator(BaseVariantGenerator):
    """Generate call-to-action variations"""
    
    async def generate_variations(
        self, 
        original_video: Dict[str, Any], 
        config: VariationConfig,
        brand_info: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        
        original_cta = original_video.get('cta', '')
        variations = []
        
        # CTA variation templates
        cta_styles = [
            {'style': 'urgency', 'examples': ['Act now!', 'Limited time!', 'Don\'t wait!']},
            {'style': 'curiosity', 'examples': ['Learn more', 'Discover how', 'See for yourself']},
            {'style': 'social_proof', 'examples': ['Join thousands', 'See why others choose', 'Join the community']},
            {'style': 'direct', 'examples': ['Shop now', 'Get started', 'Buy today']},
            {'style': 'benefit', 'examples': ['Save money', 'Get results', 'Transform your life']}
        ]
        
        for i, style in enumerate(cta_styles[:config.variation_count]):
            variations.append({
                'description': f"{style['style'].title()} CTA variation",
                'modifications': {
                    'element': 'cta',
                    'original_cta': original_cta,
                    'new_cta': style['examples'][0],
                    'cta_style': style['style'],
                    'timing': 'end'  # Default to end of video
                }
            })
        
        return variations


class TextOverlayVariantGenerator(BaseVariantGenerator):
    """Generate text overlay variations"""
    
    async def generate_variations(
        self, 
        original_video: Dict[str, Any], 
        config: VariationConfig,
        brand_info: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        
        variations = []
        
        # Text overlay style variations
        styles = [
            {'style': 'bold_large', 'description': 'Large, bold text overlay'},
            {'style': 'subtle_elegant', 'description': 'Subtle, elegant text styling'},
            {'style': 'animated_popup', 'description': 'Animated popup text'},
            {'style': 'minimal_clean', 'description': 'Minimal, clean text design'}
        ]
        
        for i, style in enumerate(styles[:config.variation_count]):
            variations.append({
                'description': style['description'],
                'modifications': {
                    'element': 'text_overlay',
                    'style_type': style['style'],
                    'font_size': 'large' if 'large' in style['style'] else 'medium',
                    'animation': 'popup' if 'animated' in style['style'] else 'none',
                    'positioning': 'center'
                }
            })
        
        return variations


class AudioVariantGenerator(BaseVariantGenerator):
    """Generate audio variations"""
    
    async def generate_variations(
        self, 
        original_video: Dict[str, Any], 
        config: VariationConfig,
        brand_info: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        
        variations = []
        
        audio_styles = [
            {'style': 'upbeat', 'description': 'Upbeat, energetic background music'},
            {'style': 'calm', 'description': 'Calm, relaxing background music'},
            {'style': 'trending', 'description': 'Current trending audio'},
            {'style': 'voiceover', 'description': 'Professional voiceover narration'}
        ]
        
        for i, style in enumerate(audio_styles[:config.variation_count]):
            variations.append({
                'description': style['description'],
                'modifications': {
                    'element': 'audio',
                    'audio_style': style['style'],
                    'volume_level': 0.7,
                    'sync_timing': True
                }
            })
        
        return variations


class FilterVariantGenerator(BaseVariantGenerator):
    """Generate filter/effect variations"""
    
    async def generate_variations(
        self, 
        original_video: Dict[str, Any], 
        config: VariationConfig,
        brand_info: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        
        variations = []
        
        filters = [
            {'filter': 'vivid', 'description': 'Enhanced colors and contrast'},
            {'filter': 'warm', 'description': 'Warm color temperature'},
            {'filter': 'cool', 'description': 'Cool color temperature'},
            {'filter': 'vintage', 'description': 'Vintage film look'}
        ]
        
        for i, filter_style in enumerate(filters[:config.variation_count]):
            variations.append({
                'description': filter_style['description'],
                'modifications': {
                    'element': 'filter',
                    'filter_type': filter_style['filter'],
                    'intensity': 0.6
                }
            })
        
        return variations


class TimingVariantGenerator(BaseVariantGenerator):
    """Generate timing variations"""
    
    async def generate_variations(
        self, 
        original_video: Dict[str, Any], 
        config: VariationConfig,
        brand_info: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        
        variations = []
        
        timing_styles = [
            {'style': 'fast_cuts', 'description': 'Faster scene transitions'},
            {'style': 'slow_burn', 'description': 'Slower, more deliberate pacing'},
            {'style': 'rhythm_sync', 'description': 'Synced to music rhythm'}
        ]
        
        for i, style in enumerate(timing_styles[:config.variation_count]):
            variations.append({
                'description': style['description'],
                'modifications': {
                    'element': 'timing',
                    'pacing_style': style['style'],
                    'cut_frequency': 'high' if 'fast' in style['style'] else 'low'
                }
            })
        
        return variations


class ColorGradingVariantGenerator(BaseVariantGenerator):
    """Generate color grading variations"""
    
    async def generate_variations(
        self, 
        original_video: Dict[str, Any], 
        config: VariationConfig,
        brand_info: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        
        variations = []
        
        color_grades = [
            {'grade': 'high_contrast', 'description': 'High contrast, dramatic look'},
            {'grade': 'soft_pastel', 'description': 'Soft, pastel color palette'},
            {'grade': 'cinematic', 'description': 'Cinematic color grading'},
            {'grade': 'natural', 'description': 'Natural, true-to-life colors'}
        ]
        
        for i, grade in enumerate(color_grades[:config.variation_count]):
            variations.append({
                'description': grade['description'],
                'modifications': {
                    'element': 'color_grading',
                    'grading_style': grade['grade'],
                    'intensity': 0.7
                }
            })
        
        return variations