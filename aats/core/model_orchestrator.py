"""
Model Orchestrator for AATS
Coordinates model usage across agents and handles load balancing and optimization
"""

import asyncio
import logging
from typing import Any, Dict, List, Optional, Set, Tuple
from datetime import datetime, timedelta
import json

from .model_manager import model_manager, ModelType
from .model_interface import ModelInterface
from ..config.settings.agent_model_config import (
    MODEL_CAPABILITIES,
    AGENT_MODEL_CONFIG
)
from ..integration.databases.utils import db_utils

class LoadBalancingStrategy(str):
    """Load balancing strategy definitions"""
    ROUND_ROBIN = "round_robin"
    LEAST_LOADED = "least_loaded"
    RESPONSE_TIME = "response_time"
    COST_OPTIMIZED = "cost_optimized"
    ADAPTIVE = "adaptive"

class ModelOrchestrator:
    """
    Model Orchestrator responsible for coordinating model usage
    and optimizing resource utilization across agents.
    """

    def __init__(self):
        self.logger = logging.getLogger("ModelOrchestrator")
        self.active_models: Dict[str, Dict] = {}
        self.model_loads: Dict[str, Dict] = {}
        self.agent_assignments: Dict[str, Dict] = {}
        self.load_balancing_stats: Dict[str, List] = {}
        self.optimization_history: List[Dict] = []

    async def initialize(self) -> bool:
        """Initialize the Model Orchestrator"""
        try:
            self.logger.info("Initializing Model Orchestrator...")
            
            # Initialize load tracking
            await self._initialize_load_tracking()
            
            # Initialize agent assignments
            await self._initialize_agent_assignments()
            
            # Initialize optimization system
            await self._initialize_optimization()
            
            # Start monitoring tasks
            self._start_monitoring_tasks()
            
            self.logger.info("Model Orchestrator initialized successfully")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to initialize Model Orchestrator: {str(e)}")
            return False

    async def _initialize_load_tracking(self) -> None:
        """Initialize load tracking system"""
        try:
            # Initialize load tracking for each model
            for model_type in ModelType:
                self.model_loads[model_type] = {
                    "current_load": 0,
                    "max_load": self._get_model_capacity(model_type),
                    "request_count": 0,
                    "error_count": 0,
                    "average_latency": 0
                }
            
            # Initialize load balancing stats
            self.load_balancing_stats = {
                strategy: []
                for strategy in LoadBalancingStrategy.__dict__.keys()
                if not strategy.startswith('_')
            }
            
        except Exception as e:
            raise Exception(f"Failed to initialize load tracking: {str(e)}")

    async def _initialize_agent_assignments(self) -> None:
        """Initialize agent model assignments"""
        try:
            # Initialize assignments for each tier
            for tier, agents in AGENT_MODEL_CONFIG.items():
                for agent_name, config in agents.items():
                    self.agent_assignments[agent_name] = {
                        "primary_model": config["primary_model"],
                        "secondary_model": config["secondary_model"],
                        "current_model": config["primary_model"],
                        "last_switch": None,
                        "switch_count": 0
                    }
            
            # Load stored assignments
            stored_assignments = await db_utils.get_agent_state(
                "model_orchestrator",
                "agent_assignments"
            )
            
            if stored_assignments:
                self._merge_assignments(stored_assignments)
                
        except Exception as e:
            raise Exception(f"Failed to initialize agent assignments: {str(e)}")

    async def _initialize_optimization(self) -> None:
        """Initialize optimization system"""
        try:
            # Set up optimization parameters
            self.optimization_config = {
                "load_threshold": 0.8,  # 80% load triggers optimization
                "error_threshold": 0.05,  # 5% error rate triggers optimization
                "latency_threshold": 1000,  # 1 second latency threshold
                "check_interval": 60,  # Check every minute
                "optimization_window": 3600  # Consider last hour for optimization
            }
            
            # Initialize optimization history
            self.optimization_history = []
            
        except Exception as e:
            raise Exception(f"Failed to initialize optimization: {str(e)}")

    def _start_monitoring_tasks(self) -> None:
        """Start background monitoring tasks"""
        asyncio.create_task(self._monitor_model_loads())
        asyncio.create_task(self._monitor_performance())
        asyncio.create_task(self._optimize_assignments())

    async def get_model_for_request(
        self,
        agent_name: str,
        task_type: Optional[str] = None,
        strategy: Optional[str] = None
    ) -> ModelType:
        """
        Get appropriate model for a request
        
        Args:
            agent_name: Name of the requesting agent
            task_type: Optional task type for specialized selection
            strategy: Optional load balancing strategy
            
        Returns:
            Selected model type
        """
        try:
            # Get agent's assigned models
            assignment = self.agent_assignments.get(agent_name)
            if not assignment:
                raise ValueError(f"No model assignment for agent: {agent_name}")
            
            # Check if task requires specific model
            if task_type:
                model = await self._get_task_specific_model(
                    agent_name,
                    task_type,
                    assignment
                )
                if model:
                    return model
            
            # Apply load balancing strategy
            strategy = strategy or LoadBalancingStrategy.ADAPTIVE
            model = await self._apply_load_balancing(
                agent_name,
                assignment,
                strategy
            )
            
            return model
            
        except Exception as e:
            self.logger.error(f"Failed to get model for request: {str(e)}")
            # Return primary model as fallback
            return assignment["primary_model"]

    async def update_model_load(
        self,
        model_type: ModelType,
        request_count: int = 1,
        error_count: int = 0,
        latency: Optional[float] = None
    ) -> None:
        """Update model load statistics"""
        try:
            if model_type in self.model_loads:
                load_stats = self.model_loads[model_type]
                
                # Update request and error counts
                load_stats["request_count"] += request_count
                load_stats["error_count"] += error_count
                
                # Update latency
                if latency is not None:
                    current_avg = load_stats["average_latency"]
                    total_requests = load_stats["request_count"]
                    load_stats["average_latency"] = (
                        (current_avg * (total_requests - 1) + latency) /
                        total_requests
                    )
                
                # Update current load
                load_stats["current_load"] = self._calculate_current_load(
                    load_stats
                )
                
                # Store metrics
                await self._store_load_metrics(model_type, load_stats)
                
        except Exception as e:
            self.logger.error(f"Failed to update model load: {str(e)}")

    async def optimize_assignments(
        self,
        force: bool = False
    ) -> Dict[str, Any]:
        """
        Optimize model assignments across agents
        
        Args:
            force: Force optimization regardless of thresholds
            
        Returns:
            Dictionary containing optimization results
        """
        try:
            optimization_needed = force or await self._check_optimization_needed()
            
            if not optimization_needed:
                return {
                    "optimized": False,
                    "reason": "Optimization not needed"
                }
            
            # Collect performance data
            performance_data = await self._collect_performance_data()
            
            # Generate optimization plan
            optimization_plan = await self._generate_optimization_plan(
                performance_data
            )
            
            # Apply optimization
            results = await self._apply_optimization(optimization_plan)
            
            # Record optimization
            await self._record_optimization(results)
            
            return results
            
        except Exception as e:
            self.logger.error(f"Failed to optimize assignments: {str(e)}")
            return {
                "optimized": False,
                "error": str(e)
            }

    async def _monitor_model_loads(self) -> None:
        """Monitor model loads continuously"""
        while True:
            try:
                for model_type in self.model_loads:
                    # Get current metrics
                    metrics = await model_manager.get_model_stats(model_type)
                    
                    # Update load tracking
                    await self.update_model_load(
                        model_type,
                        request_count=metrics.get("request_count", 0),
                        error_count=metrics.get("error_count", 0),
                        latency=metrics.get("average_latency")
                    )
                
                # Wait before next check
                await asyncio.sleep(60)
                
            except Exception as e:
                self.logger.error(f"Error in load monitoring: {str(e)}")
                await asyncio.sleep(60)

    async def _monitor_performance(self) -> None:
        """Monitor model performance continuously"""
        while True:
            try:
                performance_issues = []
                
                for model_type, load_stats in self.model_loads.items():
                    # Check for performance issues
                    if load_stats["error_count"] / load_stats["request_count"] > 0.05:
                        performance_issues.append({
                            "model": model_type,
                            "issue": "high_error_rate",
                            "value": load_stats["error_count"] / load_stats["request_count"]
                        })
                    
                    if load_stats["average_latency"] > 1000:
                        performance_issues.append({
                            "model": model_type,
                            "issue": "high_latency",
                            "value": load_stats["average_latency"]
                        })
                
                if performance_issues:
                    # Handle performance issues
                    await self._handle_performance_issues(performance_issues)
                
                # Wait before next check
                await asyncio.sleep(300)
                
            except Exception as e:
                self.logger.error(f"Error in performance monitoring: {str(e)}")
                await asyncio.sleep(300)

    async def _optimize_assignments(self) -> None:
        """Optimize assignments periodically"""
        while True:
            try:
                # Check if optimization needed
                if await self._check_optimization_needed():
                    await self.optimize_assignments()
                
                # Wait before next check
                await asyncio.sleep(3600)
                
            except Exception as e:
                self.logger.error(f"Error in assignment optimization: {str(e)}")
                await asyncio.sleep(3600)

    def _get_model_capacity(self, model_type: ModelType) -> int:
        """Get model's maximum capacity"""
        # Add actual capacity calculation based on model type
        base_capacity = 100  # Default base capacity
        
        capacities = {
            ModelType.CLAUDE_35_SONNET: base_capacity * 2,
            ModelType.LLAMA_32_90B: base_capacity * 1.5,
            ModelType.COHERE_COMMAND: base_capacity * 1.8,
            ModelType.MISTRAL_LARGE: base_capacity * 1.6,
            ModelType.PHI_35_VISION: base_capacity * 1.4,
            ModelType.PHI_35_MEDIUM: base_capacity * 1.2,
            ModelType.PHI_35_MOE: base_capacity * 1.3,
            ModelType.GROK_BETA: base_capacity * 1.7
        }
        
        return capacities.get(model_type, base_capacity)

    def _calculate_current_load(self, load_stats: Dict[str, Any]) -> float:
        """Calculate current load percentage"""
        max_load = load_stats["max_load"]
        if max_load == 0:
            return 1.0
            
        current_requests = load_stats["request_count"]
        error_penalty = load_stats["error_count"] * 0.1
        latency_factor = min(1.0, load_stats["average_latency"] / 1000)
        
        load = (current_requests + error_penalty) * (1 + latency_factor)
        return min(1.0, load / max_load)

    async def _store_load_metrics(
        self,
        model_type: ModelType,
        load_stats: Dict[str, Any]
    ) -> None:
        """Store load metrics"""
        try:
            await db_utils.record_metric(
                agent_id="model_orchestrator",
                metric_type="model_load",
                value=load_stats["current_load"],
                tags={
                    "model": model_type,
                    "request_count": load_stats["request_count"],
                    "error_count": load_stats["error_count"],
                    "average_latency": load_stats["average_latency"]
                }
            )
            
        except Exception as e:
            self.logger.error(f"Failed to store load metrics: {str(e)}")

    async def _handle_performance_issues(
        self,
        issues: List[Dict[str, Any]]
    ) -> None:
        """Handle detected performance issues"""
        try:
            for issue in issues:
                # Log issue
                self.logger.warning(
                    f"Performance issue detected: {issue['issue']} "
                    f"for model {issue['model']} "
                    f"(value: {issue['value']})"
                )
                
                # Store issue
                await db_utils.record_event(
                    event_type="performance_issue",
                    data=issue
                )
                
                # Take corrective action
                await self._take_corrective_action(issue)
                
        except Exception as e:
            self.logger.error(f"Failed to handle performance issues: {str(e)}")

    async def _take_corrective_action(
        self,
        issue: Dict[str, Any]
    ) -> None:
        """Take corrective action for performance issue"""
        try:
            model_type = issue["model"]
            issue_type = issue["issue"]
            
            if issue_type == "high_error_rate":
                # Switch affected agents to backup models
                affected_agents = self._get_agents_using_model(model_type)
                for agent_name in affected_agents:
                    await self._switch_to_backup_model(agent_name)
                    
            elif issue_type == "high_latency":
                # Reduce load on affected model
                await self._reduce_model_load(model_type)
                
        except Exception as e:
            self.logger.error(f"Failed to take corrective action: {str(e)}")

    def _get_agents_using_model(self, model_type: ModelType) -> List[str]:
        """Get list of agents currently using a model"""
        return [
            agent_name
            for agent_name, assignment in self.agent_assignments.items()
            if assignment["current_model"] == model_type
        ]

    async def _switch_to_backup_model(self, agent_name: str) -> None:
        """Switch agent to backup model"""
        try:
            assignment = self.agent_assignments[agent_name]
            current_model = assignment["current_model"]
            backup_model = (
                assignment["secondary_model"]
                if current_model == assignment["primary_model"]
                else assignment["primary_model"]
            )
            
            # Update assignment
            assignment["current_model"] = backup_model
            assignment["last_switch"] = datetime.now().isoformat()
            assignment["switch_count"] += 1
            
            # Record switch
            await db_utils.record_event(
                event_type="model_switch",
                data={
                    "agent_name": agent_name,
                    "from_model": current_model,
                    "to_model": backup_model,
                    "reason": "performance_issue"
                }
            )
            
        except Exception as e:
            self.logger.error(f"Failed to switch to backup model: {str(e)}")

    async def _reduce_model_load(self, model_type: ModelType) -> None:
        """Reduce load on a model"""
        try:
            # Get current load distribution
            load_distribution = await self._get_load_distribution()
            
            # Find less loaded models
            available_models = [
                m for m in load_distribution
                if m != model_type and
                load_distribution[m] < 0.7  # 70% load threshold
            ]
            
            if not available_models:
                return
            
            # Redistribute some load
            agents_to_move = self._get_agents_using_model(model_type)[:len(available_models)]
            
            for agent_name, new_model in zip(agents_to_move, available_models):
                await self._switch_to_backup_model(agent_name)
                
        except Exception as e:
            self.logger.error(f"Failed to reduce model load: {str(e)}")
