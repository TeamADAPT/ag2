"""
Model Manager for AATS
Handles dynamic loading and switching of models for agents
"""

import asyncio
import logging
from typing import Any, Dict, List, Optional, Tuple
from datetime import datetime

from ..config.settings.agent_model_config import (
    ModelType,
    AGENT_MODEL_CONFIG,
    MODEL_CAPABILITIES
)
from ..integration.databases.utils import db_utils

class ModelLoadError(Exception):
    """Exception raised for model loading errors"""
    pass

class ModelSwitchError(Exception):
    """Exception raised for model switching errors"""
    pass

class ModelManager:
    """
    Model Manager responsible for handling model loading,
    switching, and optimization for agents.
    """

    def __init__(self):
        self.logger = logging.getLogger("ModelManager")
        self.active_models: Dict[str, Dict[str, Any]] = {}
        self.model_stats: Dict[str, Dict[str, Any]] = {}
        self.load_history: List[Dict[str, Any]] = []

    async def initialize(self) -> bool:
        """Initialize the Model Manager"""
        try:
            self.logger.info("Initializing Model Manager...")
            
            # Initialize model tracking
            await self._initialize_model_tracking()
            
            # Load model statistics
            await self._load_model_stats()
            
            self.logger.info("Model Manager initialized successfully")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to initialize Model Manager: {str(e)}")
            return False

    async def _initialize_model_tracking(self) -> None:
        """Initialize model tracking system"""
        try:
            # Set up tracking for each model type
            for model_type in ModelType:
                self.model_stats[model_type] = {
                    "total_calls": 0,
                    "total_tokens": 0,
                    "average_latency": 0,
                    "error_count": 0,
                    "last_used": None
                }
            
            # Load stored statistics
            stored_stats = await db_utils.get_agent_state(
                "model_manager",
                "model_stats"
            )
            
            if stored_stats:
                self.model_stats.update(stored_stats)
                
        except Exception as e:
            raise Exception(f"Failed to initialize model tracking: {str(e)}")

    async def _load_model_stats(self) -> None:
        """Load model statistics"""
        try:
            # Load recent statistics
            recent_stats = await db_utils.get_agent_metrics(
                agent_id="model_manager",
                metric_type="model_performance",
                start_time=datetime.now()
            )
            
            # Update tracking
            for stat in recent_stats:
                model_type = stat["model_type"]
                if model_type in self.model_stats:
                    self._update_model_stats(model_type, stat)
                    
        except Exception as e:
            raise Exception(f"Failed to load model stats: {str(e)}")

    async def get_model_for_agent(
        self,
        agent_name: str,
        agent_tier: str,
        task_type: Optional[str] = None
    ) -> Tuple[ModelType, ModelType]:
        """
        Get primary and secondary models for an agent
        
        Args:
            agent_name: Name of the agent
            agent_tier: Tier of the agent (strategic/operational/tactical)
            task_type: Optional task type for specialized model selection
            
        Returns:
            Tuple of (primary_model, secondary_model)
        """
        try:
            # Get agent's model configuration
            agent_config = AGENT_MODEL_CONFIG[agent_tier].get(agent_name)
            if not agent_config:
                raise ValueError(f"No model configuration found for agent: {agent_name}")
            
            primary_model = agent_config["primary_model"]
            secondary_model = agent_config["secondary_model"]
            
            # Check if task type requires different model
            if task_type:
                models = await self._get_models_for_task(
                    task_type,
                    primary_model,
                    secondary_model
                )
                primary_model, secondary_model = models
            
            # Validate models are available
            await self._validate_models(primary_model, secondary_model)
            
            return primary_model, secondary_model
            
        except Exception as e:
            raise Exception(f"Failed to get models for agent: {str(e)}")

    async def load_model(
        self,
        model_type: ModelType,
        agent_name: str
    ) -> bool:
        """
        Load a model for an agent
        
        Args:
            model_type: Type of model to load
            agent_name: Name of the agent loading the model
            
        Returns:
            bool: True if model loaded successfully
        """
        try:
            # Check if model is already loaded
            if self._is_model_loaded(model_type, agent_name):
                return True
            
            # Load model
            model_key = f"{model_type}_{agent_name}"
            self.active_models[model_key] = {
                "model_type": model_type,
                "agent_name": agent_name,
                "loaded_at": datetime.now().isoformat(),
                "call_count": 0
            }
            
            # Update statistics
            await self._record_model_load(model_type, agent_name)
            
            return True
            
        except Exception as e:
            raise ModelLoadError(f"Failed to load model {model_type}: {str(e)}")

    async def switch_model(
        self,
        agent_name: str,
        from_model: ModelType,
        to_model: ModelType
    ) -> bool:
        """
        Switch an agent's model
        
        Args:
            agent_name: Name of the agent
            from_model: Current model type
            to_model: Target model type
            
        Returns:
            bool: True if switch was successful
        """
        try:
            # Validate switch is possible
            if not await self._validate_model_switch(
                agent_name,
                from_model,
                to_model
            ):
                return False
            
            # Load new model
            await self.load_model(to_model, agent_name)
            
            # Update active models
            old_key = f"{from_model}_{agent_name}"
            if old_key in self.active_models:
                del self.active_models[old_key]
            
            # Record switch
            await self._record_model_switch(
                agent_name,
                from_model,
                to_model
            )
            
            return True
            
        except Exception as e:
            raise ModelSwitchError(f"Failed to switch models: {str(e)}")

    async def get_model_stats(
        self,
        model_type: Optional[ModelType] = None
    ) -> Dict[str, Any]:
        """
        Get model statistics
        
        Args:
            model_type: Optional specific model type to get stats for
            
        Returns:
            Dictionary of model statistics
        """
        try:
            if model_type:
                return self.model_stats.get(model_type, {})
            return self.model_stats
            
        except Exception as e:
            raise Exception(f"Failed to get model stats: {str(e)}")

    async def optimize_model_usage(
        self,
        agent_name: str,
        performance_metrics: Dict[str, Any]
    ) -> Optional[ModelType]:
        """
        Optimize model usage based on performance metrics
        
        Args:
            agent_name: Name of the agent
            performance_metrics: Dictionary of performance metrics
            
        Returns:
            Optional new model type to switch to
        """
        try:
            # Get current models
            current_models = await self._get_current_models(agent_name)
            if not current_models:
                return None
            
            # Analyze performance
            analysis = await self._analyze_performance(
                current_models,
                performance_metrics
            )
            
            # Determine if switch needed
            if analysis["switch_recommended"]:
                return analysis["recommended_model"]
            
            return None
            
        except Exception as e:
            self.logger.error(f"Model optimization failed: {str(e)}")
            return None

    def _is_model_loaded(
        self,
        model_type: ModelType,
        agent_name: str
    ) -> bool:
        """Check if model is already loaded for agent"""
        model_key = f"{model_type}_{agent_name}"
        return model_key in self.active_models

    async def _validate_models(
        self,
        primary_model: ModelType,
        secondary_model: ModelType
    ) -> None:
        """Validate models are available and compatible"""
        for model in [primary_model, secondary_model]:
            if model not in MODEL_CAPABILITIES:
                raise ValueError(f"Invalid model type: {model}")
            
            # Check model capabilities
            if not await self._check_model_availability(model):
                raise ModelLoadError(f"Model {model} is not available")

    async def _check_model_availability(
        self,
        model_type: ModelType
    ) -> bool:
        """Check if a model is available for use"""
        try:
            # Add actual model availability check here
            # For now, we assume all configured models are available
            return True
        except Exception:
            return False

    async def _record_model_load(
        self,
        model_type: ModelType,
        agent_name: str
    ) -> None:
        """Record model load event"""
        event = {
            "timestamp": datetime.now().isoformat(),
            "model_type": model_type,
            "agent_name": agent_name,
            "event_type": "model_load"
        }
        
        # Store event
        await db_utils.record_event(
            event_type="model_load",
            data=event
        )
        
        # Update load history
        self.load_history.append(event)

    async def _record_model_switch(
        self,
        agent_name: str,
        from_model: ModelType,
        to_model: ModelType
    ) -> None:
        """Record model switch event"""
        event = {
            "timestamp": datetime.now().isoformat(),
            "agent_name": agent_name,
            "from_model": from_model,
            "to_model": to_model,
            "event_type": "model_switch"
        }
        
        # Store event
        await db_utils.record_event(
            event_type="model_switch",
            data=event
        )

    def _update_model_stats(
        self,
        model_type: ModelType,
        stats: Dict[str, Any]
    ) -> None:
        """Update model statistics"""
        if model_type in self.model_stats:
            current_stats = self.model_stats[model_type]
            
            # Update counters
            current_stats["total_calls"] += stats.get("calls", 0)
            current_stats["total_tokens"] += stats.get("tokens", 0)
            current_stats["error_count"] += stats.get("errors", 0)
            
            # Update averages
            if stats.get("latency"):
                current_count = current_stats["total_calls"]
                current_avg = current_stats["average_latency"]
                new_latency = stats["latency"]
                
                current_stats["average_latency"] = (
                    (current_avg * current_count + new_latency) /
                    (current_count + 1)
                )
            
            # Update timestamp
            current_stats["last_used"] = datetime.now().isoformat()

    async def _get_models_for_task(
        self,
        task_type: str,
        default_primary: ModelType,
        default_secondary: ModelType
    ) -> Tuple[ModelType, ModelType]:
        """Get optimal models for a specific task type"""
        # Add task-specific model selection logic here
        # For now, return default models
        return default_primary, default_secondary

# Global model manager instance
model_manager = ModelManager()
