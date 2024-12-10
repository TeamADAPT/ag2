"""
Base Agent Implementation for AATS
Provides core functionality for all agents in the system
"""

import asyncio
import logging
from typing import Any, Dict, List, Optional, Set
from datetime import datetime
import json
from dataclasses import dataclass

from ..core.model_interface import create_model_interface, ModelInterface
from ..integration.databases.utils import db_utils

@dataclass
class AgentConfig:
    """Agent configuration class"""
    name: str
    description: str
    capabilities: List[str]
    required_tools: List[str]
    max_concurrent_tasks: int
    priority_level: int

class AgentState:
    """Agent state tracking"""
    def __init__(self):
        self.active: bool = False
        self.busy: bool = False
        self.error_count: int = 0
        self.task_count: int = 0
        self.last_active: Optional[datetime] = None
        self.current_task: Optional[Dict] = None
        self.performance_metrics: Dict[str, Any] = {}

class BaseAgent:
    """
    Base Agent class providing core functionality for all agents
    """

    def __init__(self, config: AgentConfig):
        self.config = config
        self.logger = logging.getLogger(f"Agent_{config.name}")
        self.state = AgentState()
        self.task_history: List[Dict] = []
        self.model_interface: Optional[ModelInterface] = None
        self.hitl_manager = None  # Set by team coordinator
        self.system_monitor = None  # Set by team coordinator

    async def initialize(self) -> bool:
        """Initialize the agent"""
        try:
            self.logger.info(f"Initializing agent {self.config.name}...")
            
            # Initialize model interface
            self.model_interface = create_model_interface(
                self.config.name,
                self._get_agent_tier()
            )
            await self.model_interface.initialize()
            
            # Initialize state
            self.state.active = True
            self.state.last_active = datetime.now()
            
            # Initialize performance tracking
            await self._initialize_performance_tracking()
            
            self.logger.info(f"Agent {self.config.name} initialized successfully")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to initialize agent: {str(e)}")
            return False

    async def process_task(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process a task (to be implemented by specific agents)
        
        Args:
            task: Dictionary containing task details
            
        Returns:
            Dictionary containing the task result
        """
        raise NotImplementedError("Agents must implement process_task method")

    async def handle_error(
        self,
        error: Exception,
        task: Optional[Dict[str, Any]] = None
    ) -> None:
        """
        Handle agent errors
        
        Args:
            error: The error that occurred
            task: Optional task that caused the error
        """
        self.state.error_count += 1
        
        error_details = {
            'error_type': type(error).__name__,
            'error_message': str(error),
            'agent_name': self.config.name,
            'task_id': task.get('id') if task else None,
            'timestamp': datetime.now().isoformat()
        }
        
        # Log error
        self.logger.error(f"Error in agent {self.config.name}: {error_details}")
        
        # Store error for analysis
        await self._store_error(error_details)
        
        # Notify HITL if needed
        if self.hitl_manager and self._should_notify_hitl(error_details):
            await self._notify_hitl(error_details)

    async def get_status(self) -> Dict[str, Any]:
        """Get agent status"""
        try:
            status = {
                "name": self.config.name,
                "active": self.state.active,
                "busy": self.state.busy,
                "error_count": self.state.error_count,
                "task_count": self.state.task_count,
                "last_active": self.state.last_active.isoformat() if self.state.last_active else None,
                "current_task": self.state.current_task,
                "performance_metrics": self.state.performance_metrics
            }
            
            # Add model metrics if available
            if self.model_interface:
                status["model_metrics"] = await self.model_interface.get_performance_metrics()
            
            return status
            
        except Exception as e:
            self.logger.error(f"Failed to get agent status: {str(e)}")
            return {
                "name": self.config.name,
                "error": str(e)
            }

    async def update_state(self, updates: Dict[str, Any]) -> None:
        """Update agent state"""
        try:
            for key, value in updates.items():
                if hasattr(self.state, key):
                    setattr(self.state, key, value)
            
            # Record state update
            await self._record_state_update(updates)
            
        except Exception as e:
            self.logger.error(f"Failed to update agent state: {str(e)}")

    async def generate_response(
        self,
        prompt: str,
        task_type: Optional[str] = None,
        parameters: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """
        Generate response using model interface
        
        Args:
            prompt: Input prompt for the model
            task_type: Optional task type for model selection
            parameters: Optional model parameters
            
        Returns:
            Dictionary containing model response
        """
        try:
            if not self.model_interface:
                raise Exception("Model interface not initialized")
            
            response = await self.model_interface.generate_response(
                prompt,
                task_type,
                parameters
            )
            
            # Update performance metrics
            await self._update_performance_metrics(response)
            
            return response
            
        except Exception as e:
            self.logger.error(f"Failed to generate response: {str(e)}")
            await self.handle_error(e)
            raise

    async def _initialize_performance_tracking(self) -> None:
        """Initialize performance tracking"""
        try:
            self.state.performance_metrics = {
                "response_time": {
                    "average": 0,
                    "min": None,
                    "max": None
                },
                "success_rate": {
                    "total": 0,
                    "successful": 0,
                    "rate": 1.0
                },
                "resource_usage": {
                    "cpu": 0,
                    "memory": 0
                }
            }
            
        except Exception as e:
            self.logger.error(f"Failed to initialize performance tracking: {str(e)}")

    async def _store_error(self, error_details: Dict[str, Any]) -> None:
        """Store error details"""
        try:
            await db_utils.record_event(
                event_type="agent_error",
                data=error_details
            )
            
        except Exception as e:
            self.logger.error(f"Failed to store error: {str(e)}")

    async def _notify_hitl(self, error_details: Dict[str, Any]) -> None:
        """Notify HITL system of error"""
        try:
            if self.hitl_manager:
                await self.hitl_manager.notify_error(
                    agent_name=self.config.name,
                    error_details=error_details
                )
                
        except Exception as e:
            self.logger.error(f"Failed to notify HITL: {str(e)}")

    def _should_notify_hitl(self, error_details: Dict[str, Any]) -> bool:
        """Determine if HITL should be notified"""
        # Add logic to determine HITL notification criteria
        return (
            self.state.error_count >= 3 or
            "critical" in str(error_details).lower() or
            error_details.get('task_id') is not None
        )

    def _get_agent_tier(self) -> str:
        """Get agent's tier based on class module path"""
        module_path = self.__class__.__module__
        if "strategic" in module_path:
            return "strategic"
        elif "operational" in module_path:
            return "operational"
        elif "tactical" in module_path:
            return "tactical"
        else:
            return "unknown"

    async def _record_state_update(self, updates: Dict[str, Any]) -> None:
        """Record state update"""
        try:
            event = {
                "timestamp": datetime.now().isoformat(),
                "agent_name": self.config.name,
                "updates": updates
            }
            
            await db_utils.record_event(
                event_type="agent_state_update",
                data=event
            )
            
        except Exception as e:
            self.logger.error(f"Failed to record state update: {str(e)}")

    async def _update_performance_metrics(
        self,
        response: Dict[str, Any]
    ) -> None:
        """Update performance metrics"""
        try:
            metrics = self.state.performance_metrics
            
            # Update response time metrics
            duration = response.get("duration", 0)
            avg_time = metrics["response_time"]["average"]
            total_tasks = self.state.task_count
            
            metrics["response_time"]["average"] = (
                (avg_time * total_tasks + duration) / (total_tasks + 1)
            )
            
            if metrics["response_time"]["min"] is None:
                metrics["response_time"]["min"] = duration
            else:
                metrics["response_time"]["min"] = min(
                    metrics["response_time"]["min"],
                    duration
                )
                
            if metrics["response_time"]["max"] is None:
                metrics["response_time"]["max"] = duration
            else:
                metrics["response_time"]["max"] = max(
                    metrics["response_time"]["max"],
                    duration
                )
            
            # Update success rate
            metrics["success_rate"]["total"] += 1
            if response.get("success", False):
                metrics["success_rate"]["successful"] += 1
            
            metrics["success_rate"]["rate"] = (
                metrics["success_rate"]["successful"] /
                metrics["success_rate"]["total"]
            )
            
            # Store metrics
            await db_utils.record_metric(
                agent_id=self.config.name,
                metric_type="performance",
                value=duration,
                tags={
                    "success": response.get("success", False),
                    "model": response.get("model")
                }
            )
            
        except Exception as e:
            self.logger.error(f"Failed to update performance metrics: {str(e)}")
