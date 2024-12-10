"""
Model Selection Agent Implementation
This agent handles intelligent model selection based on task requirements
"""

import asyncio
import logging
from typing import Any, Dict, List, Optional, Set, Union, Callable
from datetime import datetime
import json
from enum import Enum
from dataclasses import dataclass
import numpy as np
from sklearn.preprocessing import StandardScaler

from ..base_agent import BaseAgent, AgentConfig
from ...config.settings.base_config import config
from ...integration.databases.utils import db_utils
from .model_connectivity_agent import ModelType, ModelProvider

class TaskCategory(str, Enum):
    """Task category definitions"""
    ARCHITECTURE = "architecture"
    CODE = "code"
    SYSTEM = "system"
    VISUAL = "visual"
    ANALYSIS = "analysis"
    DOCUMENTATION = "documentation"

class TaskPriority(str, Enum):
    """Task priority definitions"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"

@dataclass
class ModelCapability:
    """Model capability definition"""
    model_type: str
    task_categories: List[TaskCategory]
    strengths: List[str]
    context_window: Optional[int]
    vision_capable: bool
    performance_score: float
    cost_per_token: float

class ModelSelectionAgent(BaseAgent):
    """
    Model Selection Agent responsible for selecting
    appropriate models for different tasks.
    """

    def __init__(self):
        super().__init__(AgentConfig(
            name="ModelSelection",
            description="Handles intelligent model selection",
            capabilities=[
                "task_analysis",
                "model_selection",
                "performance_tracking",
                "cost_optimization",
                "capability_matching"
            ],
            required_tools=[
                "task_analyzer",
                "model_matcher",
                "performance_tracker"
            ],
            max_concurrent_tasks=5,
            priority_level=2
        ))
        self.model_capabilities: Dict[str, ModelCapability] = {}
        self.selection_history: Dict[str, List] = {}
        self.performance_metrics: Dict[str, Dict] = {}
        self.task_patterns: Dict[str, Dict] = {}

    async def initialize(self) -> bool:
        """Initialize the Model Selection Agent"""
        try:
            self.logger.info("Initializing Model Selection Agent...")
            
            # Initialize model capabilities
            await self._initialize_model_capabilities()
            
            # Initialize performance tracking
            await self._initialize_performance_tracking()
            
            # Initialize task patterns
            await self._initialize_task_patterns()
            
            # Start monitoring tasks
            self._start_monitoring_tasks()
            
            self.logger.info("Model Selection Agent initialized successfully")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to initialize Model Selection Agent: {str(e)}")
            return False

    async def _initialize_model_capabilities(self) -> None:
        """Initialize model capabilities"""
        try:
            # Define model capabilities based on documentation
            self.model_capabilities = {
                ModelType.LLAMA: ModelCapability(
                    model_type=ModelType.LLAMA,
                    task_categories=[
                        TaskCategory.ARCHITECTURE,
                        TaskCategory.VISUAL,
                        TaskCategory.ANALYSIS
                    ],
                    strengths=[
                        "architecture_design",
                        "visual_understanding",
                        "technical_analysis"
                    ],
                    context_window=100000,
                    vision_capable=True,
                    performance_score=0.9,
                    cost_per_token=0.0001
                ),
                ModelType.CLAUDE: ModelCapability(
                    model_type=ModelType.CLAUDE,
                    task_categories=[
                        TaskCategory.CODE,
                        TaskCategory.ANALYSIS,
                        TaskCategory.DOCUMENTATION
                    ],
                    strengths=[
                        "code_generation",
                        "security_analysis",
                        "technical_writing"
                    ],
                    context_window=200000,
                    vision_capable=False,
                    performance_score=0.95,
                    cost_per_token=0.0002
                ),
                ModelType.COHERE_COMMAND: ModelCapability(
                    model_type=ModelType.COHERE_COMMAND,
                    task_categories=[
                        TaskCategory.SYSTEM,
                        TaskCategory.DOCUMENTATION
                    ],
                    strengths=[
                        "system_integration",
                        "documentation",
                        "api_design"
                    ],
                    context_window=128000,
                    vision_capable=False,
                    performance_score=0.85,
                    cost_per_token=0.00008
                ),
                ModelType.PIXTRAL: ModelCapability(
                    model_type=ModelType.PIXTRAL,
                    task_categories=[
                        TaskCategory.VISUAL,
                        TaskCategory.ANALYSIS
                    ],
                    strengths=[
                        "ui_ux_analysis",
                        "visual_design",
                        "image_understanding"
                    ],
                    context_window=128000,
                    vision_capable=True,
                    performance_score=0.88,
                    cost_per_token=0.00015
                ),
                ModelType.MISTRAL: ModelCapability(
                    model_type=ModelType.MISTRAL,
                    task_categories=[
                        TaskCategory.CODE,
                        TaskCategory.ANALYSIS
                    ],
                    strengths=[
                        "code_generation",
                        "technical_analysis",
                        "problem_solving"
                    ],
                    context_window=32768,
                    vision_capable=False,
                    performance_score=0.87,
                    cost_per_token=0.00012
                )
            }
            
        except Exception as e:
            raise Exception(f"Failed to initialize model capabilities: {str(e)}")

    async def _initialize_performance_tracking(self) -> None:
        """Initialize performance tracking"""
        try:
            # Initialize performance metrics for each model
            self.performance_metrics = {
                model_type: {
                    "success_rate": 0.0,
                    "average_latency": 0.0,
                    "error_rate": 0.0,
                    "cost_efficiency": 0.0,
                    "task_completion": 0.0,
                    "history": []
                }
                for model_type in ModelType
            }
            
            # Load historical metrics
            stored_metrics = await db_utils.get_agent_state(
                self.id,
                "performance_metrics"
            )
            
            if stored_metrics:
                self._merge_metrics(stored_metrics)
                
        except Exception as e:
            raise Exception(f"Failed to initialize performance tracking: {str(e)}")

    async def _initialize_task_patterns(self) -> None:
        """Initialize task patterns"""
        try:
            # Define common task patterns
            self.task_patterns = {
                TaskCategory.ARCHITECTURE: {
                    "keywords": [
                        "design",
                        "architecture",
                        "system",
                        "structure"
                    ],
                    "requirements": {
                        "vision_capable": True,
                        "min_context": 50000
                    }
                },
                TaskCategory.CODE: {
                    "keywords": [
                        "code",
                        "programming",
                        "implementation",
                        "function"
                    ],
                    "requirements": {
                        "vision_capable": False,
                        "min_context": 32000
                    }
                },
                TaskCategory.VISUAL: {
                    "keywords": [
                        "image",
                        "visual",
                        "ui",
                        "ux",
                        "design"
                    ],
                    "requirements": {
                        "vision_capable": True,
                        "min_context": 32000
                    }
                },
                TaskCategory.ANALYSIS: {
                    "keywords": [
                        "analyze",
                        "evaluate",
                        "assess",
                        "review"
                    ],
                    "requirements": {
                        "vision_capable": False,
                        "min_context": 32000
                    }
                }
            }
            
        except Exception as e:
            raise Exception(f"Failed to initialize task patterns: {str(e)}")

    def _start_monitoring_tasks(self) -> None:
        """Start monitoring tasks"""
        asyncio.create_task(self._monitor_performance())
        asyncio.create_task(self._analyze_patterns())
        asyncio.create_task(self._update_rankings())

    async def select_model(
        self,
        task_description: str,
        priority: str,
        options: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """
        Select appropriate model for a task
        
        Args:
            task_description: Description of the task
            priority: Task priority level
            options: Optional selection options
            
        Returns:
            Dictionary containing selected model and reasoning
        """
        try:
            # Analyze task
            task_analysis = await self._analyze_task(
                task_description,
                options or {}
            )
            
            # Get candidate models
            candidates = await self._get_candidate_models(
                task_analysis,
                priority
            )
            
            if not candidates:
                return {
                    "success": False,
                    "error": "No suitable models found for task"
                }
            
            # Rank candidates
            ranked_models = await self._rank_models(
                candidates,
                task_analysis,
                priority
            )
            
            # Select best model
            selected_model = ranked_models[0]
            
            # Update selection history
            await self._update_selection_history(
                task_description,
                selected_model,
                task_analysis
            )
            
            return {
                "success": True,
                "model": selected_model["model_type"],
                "confidence": selected_model["score"],
                "reasoning": selected_model["reasoning"]
            }
            
        except Exception as e:
            self.logger.error(f"Model selection failed: {str(e)}")
            return {
                "success": False,
                "error": str(e)
            }

    async def update_performance(
        self,
        model_type: str,
        task_result: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Update model performance metrics
        
        Args:
            model_type: Type of model
            task_result: Result of task execution
            
        Returns:
            Dictionary containing update status
        """
        try:
            # Get current metrics
            metrics = self.performance_metrics.get(model_type)
            if not metrics:
                return {
                    "success": False,
                    "error": f"Unknown model type: {model_type}"
                }
            
            # Update metrics
            metrics["success_rate"] = self._update_success_rate(
                metrics["success_rate"],
                task_result["success"]
            )
            
            metrics["average_latency"] = self._update_average(
                metrics["average_latency"],
                task_result["duration"]
            )
            
            metrics["error_rate"] = self._update_error_rate(
                metrics["error_rate"],
                task_result.get("error") is not None
            )
            
            metrics["cost_efficiency"] = self._calculate_cost_efficiency(
                task_result
            )
            
            metrics["task_completion"] = self._calculate_completion_rate(
                task_result
            )
            
            # Add to history
            metrics["history"].append({
                "timestamp": datetime.now().isoformat(),
                "result": task_result
            })
            
            # Store updated metrics
            await self._store_performance_metrics(
                model_type,
                metrics
            )
            
            return {
                "success": True,
                "metrics": metrics
            }
            
        except Exception as e:
            self.logger.error(f"Performance update failed: {str(e)}")
            return {
                "success": False,
                "error": str(e)
            }

    async def get_model_recommendations(
        self,
        task_category: str,
        count: int = 3
    ) -> Dict[str, Any]:
        """
        Get model recommendations for a task category
        
        Args:
            task_category: Category of task
            count: Number of recommendations to return
            
        Returns:
            Dictionary containing recommended models
        """
        try:
            # Get models for category
            category_models = [
                model for model, capability in self.model_capabilities.items()
                if task_category in capability.task_categories
            ]
            
            if not category_models:
                return {
                    "success": False,
                    "error": f"No models found for category: {task_category}"
                }
            
            # Rank models by performance
            ranked_models = await self._rank_by_performance(
                category_models,
                task_category
            )
            
            # Get top recommendations
            recommendations = ranked_models[:count]
            
            return {
                "success": True,
                "recommendations": [
                    {
                        "model": model["model_type"],
                        "score": model["score"],
                        "strengths": model["strengths"]
                    }
                    for model in recommendations
                ]
            }
            
        except Exception as e:
            self.logger.error(f"Recommendation generation failed: {str(e)}")
            return {
                "success": False,
                "error": str(e)
            }

    async def _monitor_performance(self) -> None:
        """Monitor model performance"""
        while True:
            try:
                # Analyze performance metrics
                for model_type in ModelType:
                    metrics = self.performance_metrics[model_type]
                    
                    # Check for performance degradation
                    if await self._check_performance_degradation(
                        model_type,
                        metrics
                    ):
                        await self._handle_performance_degradation(
                            model_type,
                            metrics
                        )
                
                # Wait before next check
                await asyncio.sleep(300)  # Check every 5 minutes
                
            except Exception as e:
                self.logger.error(f"Error in performance monitoring: {str(e)}")
                await asyncio.sleep(300)

    async def _analyze_patterns(self) -> None:
        """Analyze task and selection patterns"""
        while True:
            try:
                # Analyze selection history
                patterns = await self._analyze_selection_patterns()
                
                # Update task patterns
                if patterns:
                    await self._update_task_patterns(patterns)
                
                # Wait before next analysis
                await asyncio.sleep(3600)  # Analyze every hour
                
            except Exception as e:
                self.logger.error(f"Error in pattern analysis: {str(e)}")
                await asyncio.sleep(3600)

    async def _update_rankings(self) -> None:
        """Update model rankings"""
        while True:
            try:
                # Calculate new rankings
                rankings = await self._calculate_model_rankings()
                
                # Update model capabilities
                for model_type, ranking in rankings.items():
                    self.model_capabilities[model_type].performance_score = ranking["score"]
                
                # Store updated rankings
                await self._store_rankings(rankings)
                
                # Wait before next update
                await asyncio.sleep(3600)  # Update every hour
                
            except Exception as e:
                self.logger.error(f"Error in ranking update: {str(e)}")
                await asyncio.sleep(3600)

# Global selection agent instance
selection_agent = ModelSelectionAgent()
