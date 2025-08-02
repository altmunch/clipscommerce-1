"""
AI Orchestration Service

Coordinates all AI features and services to provide comprehensive
viral content creation workflows, brand assimilation, and optimization.
"""

import asyncio
import json
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple, Union
import logging

from app.core.config import settings
from app.services.ai.brand_assimilation import BrandAssimilationService, get_brand_assimilation_service
from app.services.ai.viral_content import ViralContentService, get_viral_content_service, Platform
from app.services.ai.blueprint_architect import BlueprintArchitectService, get_blueprint_service
from app.services.ai.conversion_catalyst import ConversionCatalystService, get_conversion_catalyst_service
from app.services.ai.video_generation import AIVideoGenerationService, get_video_generation_service
from app.services.ai.performance_analyzer import PerformanceAnalysisService, get_performance_analysis_service
from app.services.ai.trend_analyzer import TrendAnalysisService, get_trend_analysis_service
from app.services.ai.vector_db import VectorService, get_vector_service
from app.services.ai.monitoring import AIMonitoringService, get_monitoring_service

logger = logging.getLogger(__name__)


class WorkflowType(str, Enum):
    """Types of AI workflows"""
    BRAND_ONBOARDING = "brand_onboarding"
    VIRAL_CONTENT_CREATION = "viral_content_creation"
    VIDEO_PRODUCTION = "video_production"
    CONTENT_OPTIMIZATION = "content_optimization"
    PERFORMANCE_ANALYSIS = "performance_analysis"
    TREND_ANALYSIS = "trend_analysis"
    COMPREHENSIVE_CAMPAIGN = "comprehensive_campaign"


class WorkflowStatus(str, Enum):
    """Workflow execution status"""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    PAUSED = "paused"
    CANCELLED = "cancelled"


@dataclass
class WorkflowStep:
    """Individual step in a workflow"""
    step_id: str
    name: str
    description: str
    service_name: str
    operation: str
    inputs: Dict[str, Any]
    outputs: Dict[str, Any] = field(default_factory=dict)
    status: WorkflowStatus = WorkflowStatus.PENDING
    error_message: Optional[str] = None
    execution_time: float = 0.0
    started_at: Optional[float] = None
    completed_at: Optional[float] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "step_id": self.step_id,
            "name": self.name,
            "description": self.description,
            "service_name": self.service_name,
            "operation": self.operation,
            "inputs": self.inputs,
            "outputs": self.outputs,
            "status": self.status,
            "error_message": self.error_message,
            "execution_time": self.execution_time,
            "started_at": self.started_at,
            "completed_at": self.completed_at
        }


@dataclass
class AIWorkflow:
    """Complete AI workflow definition and execution"""
    workflow_id: str
    name: str
    description: str
    workflow_type: WorkflowType
    steps: List[WorkflowStep]
    status: WorkflowStatus = WorkflowStatus.PENDING
    created_at: float = field(default_factory=time.time)
    started_at: Optional[float] = None
    completed_at: Optional[float] = None
    total_execution_time: float = 0.0
    results: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def get_completion_percentage(self) -> float:
        """Calculate workflow completion percentage"""
        if not self.steps:
            return 0.0
        
        completed_steps = sum(1 for step in self.steps if step.status == WorkflowStatus.COMPLETED)
        return (completed_steps / len(self.steps)) * 100
    
    def get_current_step(self) -> Optional[WorkflowStep]:
        """Get currently executing step"""
        for step in self.steps:
            if step.status == WorkflowStatus.IN_PROGRESS:
                return step
        return None
    
    def get_next_step(self) -> Optional[WorkflowStep]:
        """Get next pending step"""
        for step in self.steps:
            if step.status == WorkflowStatus.PENDING:
                return step
        return None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "workflow_id": self.workflow_id,
            "name": self.name,
            "description": self.description,
            "workflow_type": self.workflow_type,
            "steps": [step.to_dict() for step in self.steps],
            "status": self.status,
            "created_at": self.created_at,
            "started_at": self.started_at,
            "completed_at": self.completed_at,
            "total_execution_time": self.total_execution_time,
            "completion_percentage": self.get_completion_percentage(),
            "results": self.results,
            "metadata": self.metadata
        }


class WorkflowBuilder:
    """Builder for creating AI workflows"""
    
    @staticmethod
    def create_brand_onboarding_workflow(
        brand_name: str,
        website_url: str,
        industry: str,
        target_audience: str
    ) -> AIWorkflow:
        """Create brand onboarding workflow"""
        
        workflow_id = f"brand_onboarding_{brand_name}_{int(time.time())}"
        
        steps = [
            WorkflowStep(
                step_id="scrape_website",
                name="Website Content Scraping",
                description="Extract and analyze website content",
                service_name="brand_assimilation",
                operation="scrape_website",
                inputs={"website_url": website_url}
            ),
            WorkflowStep(
                step_id="analyze_brand",
                name="Brand Analysis",
                description="Analyze brand identity and positioning",
                service_name="brand_assimilation",
                operation="analyze_brand_identity",
                inputs={"brand_name": brand_name, "industry": industry}
            ),
            WorkflowStep(
                step_id="extract_voice",
                name="Brand Voice Extraction",
                description="Extract brand voice and tone characteristics",
                service_name="brand_assimilation",
                operation="extract_brand_voice",
                inputs={"brand_name": brand_name}
            ),
            WorkflowStep(
                step_id="identify_pillars",
                name="Content Pillars Identification",
                description="Identify key content pillars for the brand",
                service_name="brand_assimilation",
                operation="identify_content_pillars",
                inputs={"brand_name": brand_name, "industry": industry}
            ),
            WorkflowStep(
                step_id="create_brand_kit",
                name="Brand Kit Creation",
                description="Generate comprehensive brand kit",
                service_name="brand_assimilation",
                operation="create_brand_kit",
                inputs={"brand_name": brand_name, "target_audience": target_audience}
            ),
            WorkflowStep(
                step_id="setup_vector_db",
                name="Brand Knowledge Base Setup",
                description="Create vector database with brand information",
                service_name="vector_db",
                operation="create_brand_knowledge_base",
                inputs={"brand_name": brand_name}
            )
        ]
        
        return AIWorkflow(
            workflow_id=workflow_id,
            name=f"Brand Onboarding - {brand_name}",
            description=f"Complete brand onboarding process for {brand_name}",
            workflow_type=WorkflowType.BRAND_ONBOARDING,
            steps=steps,
            metadata={
                "brand_name": brand_name,
                "website_url": website_url,
                "industry": industry,
                "target_audience": target_audience
            }
        )
    
    @staticmethod
    def create_viral_content_workflow(
        brand_name: str,
        content_pillar: str,
        platform: Platform,
        target_audience: str,
        brand_voice: Dict[str, Any]
    ) -> AIWorkflow:
        """Create viral content creation workflow"""
        
        workflow_id = f"viral_content_{brand_name}_{platform}_{int(time.time())}"
        
        steps = [
            WorkflowStep(
                step_id="trend_analysis",
                name="Trend Analysis",
                description="Analyze current trends for opportunities",
                service_name="trend_analyzer",
                operation="comprehensive_trend_analysis",
                inputs={
                    "brand_name": brand_name,
                    "industry": "general",
                    "target_audience": target_audience,
                    "platforms": [platform],
                    "brand_voice": brand_voice
                }
            ),
            WorkflowStep(
                step_id="generate_hooks",
                name="Viral Hook Generation",
                description="Generate viral hooks for content",
                service_name="viral_content",
                operation="generate_viral_hooks",
                inputs={
                    "brand_name": brand_name,
                    "content_pillar": content_pillar,
                    "platform": platform,
                    "target_audience": target_audience
                }
            ),
            WorkflowStep(
                step_id="create_blueprint",
                name="Video Blueprint Creation",
                description="Create detailed video production blueprint",
                service_name="blueprint_architect",
                operation="create_blueprint",
                inputs={
                    "brand_name": brand_name,
                    "platform": platform,
                    "target_duration": 60.0 if platform == Platform.TIKTOK else 90.0
                }
            ),
            WorkflowStep(
                step_id="optimize_conversion",
                name="Conversion Optimization",
                description="Optimize content for maximum conversion",
                service_name="conversion_catalyst",
                operation="create_conversion_optimization",
                inputs={
                    "brand_name": brand_name,
                    "platform": platform,
                    "target_audience": target_audience,
                    "brand_voice": brand_voice
                }
            ),
            WorkflowStep(
                step_id="predict_performance",
                name="Performance Prediction",
                description="Predict content performance and ROI",
                service_name="performance_analyzer",
                operation="predict_content_performance",
                inputs={
                    "platform": platform,
                    "brand_name": brand_name
                }
            )
        ]
        
        return AIWorkflow(
            workflow_id=workflow_id,
            name=f"Viral Content Creation - {brand_name}",
            description=f"Complete viral content creation for {brand_name} on {platform}",
            workflow_type=WorkflowType.VIRAL_CONTENT_CREATION,
            steps=steps,
            metadata={
                "brand_name": brand_name,
                "content_pillar": content_pillar,
                "platform": platform,
                "target_audience": target_audience
            }
        )
    
    @staticmethod
    def create_video_production_workflow(
        brand_name: str,
        video_concept: str,
        platform: Platform,
        style: str = "professional",
        quality: str = "medium"
    ) -> AIWorkflow:
        """Create video production workflow"""
        
        workflow_id = f"video_production_{brand_name}_{int(time.time())}"
        
        steps = [
            WorkflowStep(
                step_id="create_script",
                name="Script Generation",
                description="Generate detailed video script",
                service_name="blueprint_architect",
                operation="generate_script",
                inputs={
                    "brand_name": brand_name,
                    "video_concept": video_concept,
                    "platform": platform
                }
            ),
            WorkflowStep(
                step_id="create_shot_list",
                name="Shot List Creation",
                description="Create detailed shot list and production plan",
                service_name="blueprint_architect",
                operation="generate_shot_list",
                inputs={
                    "brand_name": brand_name,
                    "platform": platform
                }
            ),
            WorkflowStep(
                step_id="create_video_project",
                name="AI Video Project Setup",
                description="Set up AI video generation project",
                service_name="video_generation",
                operation="create_video_project",
                inputs={
                    "style": style,
                    "quality": quality
                }
            ),
            WorkflowStep(
                step_id="generate_videos",
                name="AI Video Generation",
                description="Generate video segments using AI",
                service_name="video_generation",
                operation="generate_project_videos",
                inputs={}
            ),
            WorkflowStep(
                step_id="create_timeline",
                name="Editing Timeline",
                description="Create editing timeline with transitions",
                service_name="video_generation",
                operation="generate_editing_timeline",
                inputs={}
            )
        ]
        
        return AIWorkflow(
            workflow_id=workflow_id,
            name=f"Video Production - {brand_name}",
            description=f"Complete AI video production for {brand_name}",
            workflow_type=WorkflowType.VIDEO_PRODUCTION,
            steps=steps,
            metadata={
                "brand_name": brand_name,
                "video_concept": video_concept,
                "platform": platform,
                "style": style,
                "quality": quality
            }
        )
    
    @staticmethod
    def create_comprehensive_campaign_workflow(
        brand_name: str,
        campaign_goals: List[str],
        platforms: List[Platform],
        target_audience: str,
        budget: float
    ) -> AIWorkflow:
        """Create comprehensive marketing campaign workflow"""
        
        workflow_id = f"campaign_{brand_name}_{int(time.time())}"
        
        steps = [
            # Phase 1: Analysis and Strategy
            WorkflowStep(
                step_id="trend_analysis",
                name="Multi-Platform Trend Analysis",
                description="Analyze trends across all target platforms",
                service_name="trend_analyzer",
                operation="comprehensive_trend_analysis",
                inputs={
                    "brand_name": brand_name,
                    "platforms": platforms,
                    "target_audience": target_audience
                }
            ),
            WorkflowStep(
                step_id="competitor_analysis",
                name="Competitive Intelligence",
                description="Analyze competitors and identify opportunities",
                service_name="performance_analyzer",
                operation="analyze_competitors",
                inputs={
                    "brand_name": brand_name,
                    "platforms": platforms
                }
            ),
            
            # Phase 2: Content Creation
            WorkflowStep(
                step_id="content_strategy",
                name="Content Strategy Development",
                description="Develop comprehensive content strategy",
                service_name="viral_content",
                operation="create_content_strategy",
                inputs={
                    "brand_name": brand_name,
                    "platforms": platforms,
                    "campaign_goals": campaign_goals
                }
            ),
            WorkflowStep(
                step_id="batch_content_creation",
                name="Batch Content Creation",
                description="Create multiple pieces of content",
                service_name="viral_content",
                operation="batch_create_content",
                inputs={
                    "brand_name": brand_name,
                    "platforms": platforms,
                    "quantity": 10  # Create 10 pieces of content
                }
            ),
            
            # Phase 3: Optimization
            WorkflowStep(
                step_id="conversion_optimization",
                name="Multi-Platform Conversion Optimization",
                description="Optimize content for conversions across platforms",
                service_name="conversion_catalyst",
                operation="batch_optimize_content",
                inputs={
                    "brand_name": brand_name,
                    "platforms": platforms,
                    "target_audience": target_audience
                }
            ),
            WorkflowStep(
                step_id="brand_consistency_check",
                name="Brand Consistency Validation",
                description="Ensure all content aligns with brand guidelines",
                service_name="vector_db",
                operation="batch_brand_consistency_check",
                inputs={
                    "brand_name": brand_name
                }
            ),
            
            # Phase 4: Production Planning
            WorkflowStep(
                step_id="production_planning",
                name="Production Planning",
                description="Plan video production for selected content",
                service_name="blueprint_architect",
                operation="batch_create_blueprints",
                inputs={
                    "brand_name": brand_name,
                    "platforms": platforms
                }
            ),
            
            # Phase 5: Performance Prediction
            WorkflowStep(
                step_id="campaign_prediction",
                name="Campaign Performance Prediction",
                description="Predict campaign performance and ROI",
                service_name="performance_analyzer",
                operation="predict_campaign_performance",
                inputs={
                    "brand_name": brand_name,
                    "platforms": platforms,
                    "budget": budget
                }
            )
        ]
        
        return AIWorkflow(
            workflow_id=workflow_id,
            name=f"Comprehensive Campaign - {brand_name}",
            description=f"Complete marketing campaign for {brand_name} across {len(platforms)} platforms",
            workflow_type=WorkflowType.COMPREHENSIVE_CAMPAIGN,
            steps=steps,
            metadata={
                "brand_name": brand_name,
                "campaign_goals": campaign_goals,
                "platforms": [p.value for p in platforms],
                "target_audience": target_audience,
                "budget": budget
            }
        )


class AIOrchestrator:
    """Main AI orchestration engine"""
    
    def __init__(self):
        self.services = {}
        self.active_workflows: Dict[str, AIWorkflow] = {}
        self.workflow_history: List[AIWorkflow] = []
        self.monitoring_service = None
    
    async def initialize(self):
        """Initialize all AI services"""
        logger.info("Initializing AI Orchestrator services...")
        
        try:
            # Initialize all services
            self.services = {
                "brand_assimilation": await get_brand_assimilation_service(),
                "viral_content": await get_viral_content_service(),
                "blueprint_architect": await get_blueprint_service(),
                "conversion_catalyst": await get_conversion_catalyst_service(),
                "video_generation": await get_video_generation_service(),
                "performance_analyzer": await get_performance_analysis_service(),
                "trend_analyzer": await get_trend_analysis_service(),
                "vector_db": await get_vector_service(),
                "monitoring": get_monitoring_service()
            }
            
            self.monitoring_service = self.services["monitoring"]
            logger.info("AI Orchestrator initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize AI Orchestrator: {e}")
            raise
    
    async def execute_workflow(self, workflow: AIWorkflow) -> AIWorkflow:
        """Execute a complete workflow"""
        
        logger.info(f"Starting workflow execution: {workflow.workflow_id}")
        
        workflow.status = WorkflowStatus.IN_PROGRESS
        workflow.started_at = time.time()
        self.active_workflows[workflow.workflow_id] = workflow
        
        try:
            for step in workflow.steps:
                # Execute step
                step_result = await self._execute_step(step, workflow)
                
                if not step_result:
                    # Step failed
                    workflow.status = WorkflowStatus.FAILED
                    break
                
                # Update workflow results with step outputs
                workflow.results[step.step_id] = step.outputs
            
            # Mark workflow as completed if all steps succeeded
            if all(step.status == WorkflowStatus.COMPLETED for step in workflow.steps):
                workflow.status = WorkflowStatus.COMPLETED
                logger.info(f"Workflow completed successfully: {workflow.workflow_id}")
            
        except Exception as e:
            logger.error(f"Workflow execution failed: {workflow.workflow_id}, Error: {e}")
            workflow.status = WorkflowStatus.FAILED
        
        finally:
            workflow.completed_at = time.time()
            workflow.total_execution_time = workflow.completed_at - workflow.started_at
            
            # Move to history
            self.workflow_history.append(workflow)
            if workflow.workflow_id in self.active_workflows:
                del self.active_workflows[workflow.workflow_id]
        
        return workflow
    
    async def _execute_step(self, step: WorkflowStep, workflow: AIWorkflow) -> bool:
        """Execute individual workflow step"""
        
        logger.info(f"Executing step: {step.step_id} in workflow {workflow.workflow_id}")
        
        step.status = WorkflowStatus.IN_PROGRESS
        step.started_at = time.time()
        
        try:
            # Get the appropriate service
            service = self.services.get(step.service_name)
            if not service:
                raise ValueError(f"Service not found: {step.service_name}")
            
            # Prepare inputs (may include outputs from previous steps)
            inputs = self._prepare_step_inputs(step, workflow)
            
            # Execute the operation
            result = await self._call_service_operation(service, step.operation, inputs)
            
            # Store outputs
            step.outputs = result if isinstance(result, dict) else {"result": result}
            step.status = WorkflowStatus.COMPLETED
            
            return True
            
        except Exception as e:
            logger.error(f"Step execution failed: {step.step_id}, Error: {e}")
            step.error_message = str(e)
            step.status = WorkflowStatus.FAILED
            return False
        
        finally:
            step.completed_at = time.time()
            step.execution_time = step.completed_at - step.started_at
    
    def _prepare_step_inputs(self, step: WorkflowStep, workflow: AIWorkflow) -> Dict[str, Any]:
        """Prepare inputs for step execution, including previous step outputs"""
        
        inputs = step.inputs.copy()
        
        # Add outputs from previous steps where needed
        for prev_step in workflow.steps:
            if prev_step.step_id == step.step_id:
                break  # Don't include future steps
            
            if prev_step.status == WorkflowStatus.COMPLETED and prev_step.outputs:
                # Add previous step outputs with step prefix to avoid conflicts
                for key, value in prev_step.outputs.items():
                    prefixed_key = f"{prev_step.step_id}_{key}"
                    inputs[prefixed_key] = value
                
                # Also add direct outputs for common patterns
                if prev_step.step_id == "scrape_website" and "website_content" in prev_step.outputs:
                    inputs["website_content"] = prev_step.outputs["website_content"]
                elif prev_step.step_id == "extract_voice" and "brand_voice" in prev_step.outputs:
                    inputs["brand_voice"] = prev_step.outputs["brand_voice"]
                elif prev_step.step_id == "generate_hooks" and "hooks" in prev_step.outputs:
                    inputs["hooks"] = prev_step.outputs["hooks"]
        
        return inputs
    
    async def _call_service_operation(self, service: Any, operation: str, inputs: Dict[str, Any]) -> Any:
        """Call service operation with monitoring"""
        
        operation_start = time.time()
        
        try:
            # Map operation names to actual service methods
            method_map = {
                # Brand Assimilation Service
                "scrape_website": "scrape_website",
                "analyze_brand_identity": "analyze_brand_identity", 
                "extract_brand_voice": "extract_brand_voice",
                "identify_content_pillars": "identify_content_pillars",
                "create_brand_kit": "create_brand_kit",
                
                # Viral Content Service
                "generate_viral_hooks": "generate_viral_hooks",
                "create_content_strategy": "create_content_strategy",
                "batch_create_content": "batch_create_viral_content",
                
                # Blueprint Architect Service
                "create_blueprint": "create_blueprint",
                "generate_script": "generate_script",
                "generate_shot_list": "generate_shot_list",
                "batch_create_blueprints": "batch_create_blueprints",
                
                # Conversion Catalyst Service
                "create_conversion_optimization": "create_conversion_optimization",
                "batch_optimize_content": "batch_optimize_content",
                
                # Video Generation Service
                "create_video_project": "create_video_project",
                "generate_project_videos": "generate_project_videos",
                "generate_editing_timeline": "generate_editing_timeline",
                
                # Performance Analyzer Service
                "predict_content_performance": "predict_content_performance",
                "analyze_competitors": "analyze_competitors",
                "predict_campaign_performance": "predict_campaign_performance",
                
                # Trend Analyzer Service
                "comprehensive_trend_analysis": "comprehensive_trend_analysis",
                
                # Vector DB Service
                "create_brand_knowledge_base": "create_brand_knowledge_base",
                "batch_brand_consistency_check": "batch_brand_consistency_check"
            }
            
            method_name = method_map.get(operation)
            if not method_name:
                raise ValueError(f"Operation not mapped: {operation}")
            
            method = getattr(service, method_name, None)
            if not method:
                raise ValueError(f"Method not found: {method_name} on service {type(service).__name__}")
            
            # Call the method with appropriate parameters
            if asyncio.iscoroutinefunction(method):
                if inputs:
                    result = await method(**inputs)
                else:
                    result = await method()
            else:
                if inputs:
                    result = method(**inputs)
                else:
                    result = method()
            
            # Record successful operation
            if self.monitoring_service:
                self.monitoring_service.record_ai_call(
                    service_name=type(service).__name__,
                    model_name="orchestrator",
                    operation=operation,
                    input_tokens=0,  # Would need to calculate actual tokens
                    output_tokens=0,
                    cost=0.0,  # Would need to calculate actual cost
                    latency=time.time() - operation_start,
                    success=True,
                    metadata={"orchestrated": True}
                )
            
            return result
            
        except Exception as e:
            # Record failed operation
            if self.monitoring_service:
                self.monitoring_service.record_ai_call(
                    service_name=type(service).__name__,
                    model_name="orchestrator",
                    operation=operation,
                    input_tokens=0,
                    output_tokens=0,
                    cost=0.0,
                    latency=time.time() - operation_start,
                    success=False,
                    error_message=str(e),
                    metadata={"orchestrated": True}
                )
            
            raise
    
    def get_workflow_status(self, workflow_id: str) -> Optional[Dict[str, Any]]:
        """Get workflow status and progress"""
        
        # Check active workflows
        if workflow_id in self.active_workflows:
            return self.active_workflows[workflow_id].to_dict()
        
        # Check workflow history
        for workflow in self.workflow_history:
            if workflow.workflow_id == workflow_id:
                return workflow.to_dict()
        
        return None
    
    def list_active_workflows(self) -> List[Dict[str, Any]]:
        """List all active workflows"""
        return [workflow.to_dict() for workflow in self.active_workflows.values()]
    
    def get_workflow_history(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Get workflow execution history"""
        return [workflow.to_dict() for workflow in self.workflow_history[-limit:]]
    
    async def pause_workflow(self, workflow_id: str) -> bool:
        """Pause an active workflow"""
        if workflow_id in self.active_workflows:
            workflow = self.active_workflows[workflow_id]
            workflow.status = WorkflowStatus.PAUSED
            logger.info(f"Workflow paused: {workflow_id}")
            return True
        return False
    
    async def resume_workflow(self, workflow_id: str) -> bool:
        """Resume a paused workflow"""
        if workflow_id in self.active_workflows:
            workflow = self.active_workflows[workflow_id]
            if workflow.status == WorkflowStatus.PAUSED:
                workflow.status = WorkflowStatus.IN_PROGRESS
                logger.info(f"Workflow resumed: {workflow_id}")
                # Continue execution from current step
                await self.execute_workflow(workflow)
                return True
        return False
    
    async def cancel_workflow(self, workflow_id: str) -> bool:
        """Cancel an active workflow"""
        if workflow_id in self.active_workflows:
            workflow = self.active_workflows[workflow_id]
            workflow.status = WorkflowStatus.CANCELLED
            workflow.completed_at = time.time()
            
            # Move to history
            self.workflow_history.append(workflow)
            del self.active_workflows[workflow_id]
            
            logger.info(f"Workflow cancelled: {workflow_id}")
            return True
        return False
    
    def get_system_status(self) -> Dict[str, Any]:
        """Get overall system status"""
        
        active_count = len(self.active_workflows)
        total_completed = len([w for w in self.workflow_history if w.status == WorkflowStatus.COMPLETED])
        total_failed = len([w for w in self.workflow_history if w.status == WorkflowStatus.FAILED])
        
        return {
            "orchestrator_status": "healthy",
            "services_initialized": len(self.services),
            "active_workflows": active_count,
            "total_workflows_completed": total_completed,
            "total_workflows_failed": total_failed,
            "success_rate": total_completed / max(total_completed + total_failed, 1),
            "available_workflow_types": [wt.value for wt in WorkflowType],
            "monitoring_enabled": self.monitoring_service is not None
        }


class AIOrchestrationService:
    """Main service interface for AI orchestration"""
    
    def __init__(self):
        self.orchestrator = AIOrchestrator()
        self.initialized = False
    
    async def initialize(self):
        """Initialize the orchestration service"""
        if not self.initialized:
            await self.orchestrator.initialize()
            self.initialized = True
    
    async def create_and_execute_brand_onboarding(
        self,
        brand_name: str,
        website_url: str,
        industry: str,
        target_audience: str
    ) -> Dict[str, Any]:
        """Create and execute brand onboarding workflow"""
        
        await self.initialize()
        
        workflow = WorkflowBuilder.create_brand_onboarding_workflow(
            brand_name, website_url, industry, target_audience
        )
        
        executed_workflow = await self.orchestrator.execute_workflow(workflow)
        return executed_workflow.to_dict()
    
    async def create_and_execute_viral_content(
        self,
        brand_name: str,
        content_pillar: str,
        platform: Platform,
        target_audience: str,
        brand_voice: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """Create and execute viral content creation workflow"""
        
        await self.initialize()
        
        workflow = WorkflowBuilder.create_viral_content_workflow(
            brand_name, content_pillar, platform, target_audience, brand_voice or {}
        )
        
        executed_workflow = await self.orchestrator.execute_workflow(workflow)
        return executed_workflow.to_dict()
    
    async def create_and_execute_video_production(
        self,
        brand_name: str,
        video_concept: str,
        platform: Platform,
        style: str = "professional",
        quality: str = "medium"
    ) -> Dict[str, Any]:
        """Create and execute video production workflow"""
        
        await self.initialize()
        
        workflow = WorkflowBuilder.create_video_production_workflow(
            brand_name, video_concept, platform, style, quality
        )
        
        executed_workflow = await self.orchestrator.execute_workflow(workflow)
        return executed_workflow.to_dict()
    
    async def create_and_execute_comprehensive_campaign(
        self,
        brand_name: str,
        campaign_goals: List[str],
        platforms: List[Platform],
        target_audience: str,
        budget: float
    ) -> Dict[str, Any]:
        """Create and execute comprehensive campaign workflow"""
        
        await self.initialize()
        
        workflow = WorkflowBuilder.create_comprehensive_campaign_workflow(
            brand_name, campaign_goals, platforms, target_audience, budget
        )
        
        executed_workflow = await self.orchestrator.execute_workflow(workflow)
        return executed_workflow.to_dict()
    
    async def get_workflow_status(self, workflow_id: str) -> Optional[Dict[str, Any]]:
        """Get workflow status"""
        await self.initialize()
        return self.orchestrator.get_workflow_status(workflow_id)
    
    async def list_workflows(self) -> Dict[str, Any]:
        """List all workflows"""
        await self.initialize()
        return {
            "active_workflows": self.orchestrator.list_active_workflows(),
            "workflow_history": self.orchestrator.get_workflow_history(),
            "system_status": self.orchestrator.get_system_status()
        }
    
    async def control_workflow(self, workflow_id: str, action: str) -> Dict[str, Any]:
        """Control workflow execution (pause/resume/cancel)"""
        await self.initialize()
        
        success = False
        
        if action == "pause":
            success = await self.orchestrator.pause_workflow(workflow_id)
        elif action == "resume":
            success = await self.orchestrator.resume_workflow(workflow_id)
        elif action == "cancel":
            success = await self.orchestrator.cancel_workflow(workflow_id)
        else:
            return {"error": f"Invalid action: {action}"}
        
        return {
            "workflow_id": workflow_id,
            "action": action,
            "success": success,
            "status": self.orchestrator.get_workflow_status(workflow_id)
        }


# Global service instance
_orchestration_service: Optional[AIOrchestrationService] = None


async def get_orchestration_service() -> AIOrchestrationService:
    """Get global orchestration service instance"""
    global _orchestration_service
    if _orchestration_service is None:
        _orchestration_service = AIOrchestrationService()
    return _orchestration_service