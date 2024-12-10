"""
Data Orchestration Agent Implementation
This agent coordinates data workflows and pipelines across all data agents
"""

import asyncio
import logging
from typing import Any, Dict, List, Optional, Set, Union, Callable
from datetime import datetime
import json
import networkx as nx
from dataclasses import dataclass
import yaml
import uuid
from enum import Enum

from ..base_agent import BaseAgent, AgentConfig
from ...config.settings.base_config import config
from ...integration.databases.utils import db_utils
from .file_processor_agent import file_processor
from .data_extraction_agent import data_extractor
from .data_transformation_agent import data_transformer
from .data_validation_agent import data_validator
from .data_enrichment_agent import data_enricher
from .data_integration_agent import data_integrator

class WorkflowState(str, Enum):
    """Workflow state definitions"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    PAUSED = "paused"
    CANCELLED = "cancelled"

class StepType(str, Enum):
    """Workflow step type definitions"""
    PROCESS = "process"
    EXTRACT = "extract"
    TRANSFORM = "transform"
    VALIDATE = "validate"
    ENRICH = "enrich"
    INTEGRATE = "integrate"

@dataclass
class WorkflowStep:
    """Workflow step definition"""
    id: str
    type: str
    agent: str
    method: str
    params: Dict[str, Any]
    dependencies: List[str]
    retry_policy: Dict[str, Any]
    timeout: int
    state: str = WorkflowState.PENDING
    result: Optional[Dict] = None

class DataOrchestrationAgent(BaseAgent):
    """
    Data Orchestration Agent responsible for coordinating
    data workflows and pipelines.
    """

    def __init__(self):
        super().__init__(AgentConfig(
            name="DataOrchestrator",
            description="Handles data workflow orchestration",
            capabilities=[
                "workflow_management",
                "pipeline_orchestration",
                "agent_coordination",
                "error_handling",
                "monitoring"
            ],
            required_tools=[
                "workflow_manager",
                "pipeline_orchestrator",
                "coordinator"
            ],
            max_concurrent_tasks=10,
            priority_level=1
        ))
        self.workflows: Dict[str, Dict] = {}
        self.active_pipelines: Dict[str, Dict] = {}
        self.agent_registry: Dict[str, Any] = {}
        self.workflow_history: List[Dict] = []

    async def initialize(self) -> bool:
        """Initialize the Data Orchestration Agent"""
        try:
            self.logger.info("Initializing Data Orchestration Agent...")
            
            # Initialize agent registry
            await self._initialize_agent_registry()
            
            # Initialize workflow engine
            await self._initialize_workflow_engine()
            
            # Initialize monitoring system
            await self._initialize_monitoring()
            
            # Start orchestration tasks
            self._start_orchestration_tasks()
            
            self.logger.info("Data Orchestration Agent initialized successfully")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to initialize Data Orchestration Agent: {str(e)}")
            return False

    async def _initialize_agent_registry(self) -> None:
        """Initialize agent registry"""
        try:
            self.agent_registry = {
                StepType.PROCESS: file_processor,
                StepType.EXTRACT: data_extractor,
                StepType.TRANSFORM: data_transformer,
                StepType.VALIDATE: data_validator,
                StepType.ENRICH: data_enricher,
                StepType.INTEGRATE: data_integrator
            }
            
            # Initialize agent capabilities map
            self.agent_capabilities = {}
            for agent_type, agent in self.agent_registry.items():
                self.agent_capabilities[agent_type] = agent.config.capabilities
                
        except Exception as e:
            raise Exception(f"Failed to initialize agent registry: {str(e)}")

    async def _initialize_workflow_engine(self) -> None:
        """Initialize workflow engine"""
        try:
            # Initialize workflow configurations
            self.workflow_configs = {
                "max_concurrent_workflows": 10,
                "max_retries": 3,
                "default_timeout": 3600,
                "checkpoint_interval": 300
            }
            
            # Initialize workflow graph
            self.workflow_graph = nx.DiGraph()
            
            # Load stored workflows
            stored_workflows = await db_utils.get_agent_state(
                self.id,
                "workflows"
            )
            
            if stored_workflows:
                await self._restore_workflows(stored_workflows)
                
        except Exception as e:
            raise Exception(f"Failed to initialize workflow engine: {str(e)}")

    async def _initialize_monitoring(self) -> None:
        """Initialize monitoring system"""
        try:
            # Initialize monitoring configurations
            self.monitoring_configs = {
                "metrics_interval": 60,
                "health_check_interval": 300,
                "alert_thresholds": {
                    "error_rate": 0.1,
                    "latency": 1000,
                    "queue_size": 100
                }
            }
            
            # Initialize monitoring metrics
            self.monitoring_metrics = {
                "workflows": {
                    "total": 0,
                    "active": 0,
                    "completed": 0,
                    "failed": 0
                },
                "steps": {
                    "total": 0,
                    "successful": 0,
                    "failed": 0,
                    "average_duration": 0.0
                }
            }
            
        except Exception as e:
            raise Exception(f"Failed to initialize monitoring: {str(e)}")

    def _start_orchestration_tasks(self) -> None:
        """Start orchestration tasks"""
        asyncio.create_task(self._monitor_workflows())
        asyncio.create_task(self._monitor_agents())
        asyncio.create_task(self._cleanup_workflows())

    async def create_workflow(
        self,
        workflow_config: Dict[str, Any],
        options: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """
        Create a new workflow
        
        Args:
            workflow_config: Workflow configuration
            options: Optional workflow options
            
        Returns:
            Dictionary containing workflow creation results
        """
        try:
            # Generate workflow ID
            workflow_id = str(uuid.uuid4())
            
            # Parse and validate workflow configuration
            workflow = await self._parse_workflow_config(
                workflow_id,
                workflow_config,
                options or {}
            )
            
            # Build workflow graph
            graph = await self._build_workflow_graph(workflow)
            
            # Initialize workflow state
            workflow["state"] = WorkflowState.PENDING
            workflow["created_at"] = datetime.now().isoformat()
            workflow["graph"] = graph
            workflow["metrics"] = {
                "steps_total": len(workflow["steps"]),
                "steps_completed": 0,
                "duration": 0.0
            }
            
            # Store workflow
            self.workflows[workflow_id] = workflow
            
            # Update monitoring metrics
            self.monitoring_metrics["workflows"]["total"] += 1
            
            return {
                "success": True,
                "workflow_id": workflow_id,
                "state": workflow["state"]
            }
            
        except Exception as e:
            self.logger.error(f"Workflow creation failed: {str(e)}")
            return {
                "success": False,
                "error": str(e)
            }

    async def execute_workflow(
        self,
        workflow_id: str,
        options: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """
        Execute a workflow
        
        Args:
            workflow_id: Workflow identifier
            options: Optional execution options
            
        Returns:
            Dictionary containing workflow execution results
        """
        try:
            # Get workflow
            workflow = self.workflows.get(workflow_id)
            if not workflow:
                return {
                    "success": False,
                    "error": f"Workflow not found: {workflow_id}"
                }
            
            # Check workflow state
            if workflow["state"] != WorkflowState.PENDING:
                return {
                    "success": False,
                    "error": f"Invalid workflow state: {workflow['state']}"
                }
            
            # Update workflow state
            workflow["state"] = WorkflowState.RUNNING
            workflow["started_at"] = datetime.now().isoformat()
            
            # Execute workflow steps
            execution_order = self._get_execution_order(workflow["graph"])
            results = []
            
            for step_id in execution_order:
                step = workflow["steps"][step_id]
                
                # Check dependencies
                if not await self._check_dependencies(step, results):
                    workflow["state"] = WorkflowState.FAILED
                    return {
                        "success": False,
                        "error": f"Dependency check failed for step: {step_id}",
                        "results": results
                    }
                
                # Execute step
                step_result = await self._execute_step(
                    step,
                    workflow,
                    options or {}
                )
                results.append(step_result)
                
                if not step_result["success"]:
                    # Handle step failure
                    await self._handle_step_failure(
                        workflow,
                        step,
                        step_result
                    )
                    return {
                        "success": False,
                        "error": f"Step failed: {step_id}",
                        "results": results
                    }
                
                # Update workflow metrics
                workflow["metrics"]["steps_completed"] += 1
            
            # Update workflow state and metrics
            workflow["state"] = WorkflowState.COMPLETED
            workflow["completed_at"] = datetime.now().isoformat()
            workflow["metrics"]["duration"] = (
                datetime.fromisoformat(workflow["completed_at"]) -
                datetime.fromisoformat(workflow["started_at"])
            ).total_seconds()
            
            # Update monitoring metrics
            self.monitoring_metrics["workflows"]["completed"] += 1
            
            return {
                "success": True,
                "workflow_id": workflow_id,
                "results": results
            }
            
        except Exception as e:
            self.logger.error(f"Workflow execution failed: {str(e)}")
            workflow["state"] = WorkflowState.FAILED
            return {
                "success": False,
                "error": str(e)
            }

    async def _execute_step(
        self,
        step: WorkflowStep,
        workflow: Dict[str, Any],
        options: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Execute workflow step"""
        try:
            # Get agent for step
            agent = self.agent_registry.get(step.type)
            if not agent:
                raise ValueError(f"Invalid step type: {step.type}")
            
            # Update step state
            step.state = WorkflowState.RUNNING
            
            # Execute step with timeout
            start_time = datetime.now()
            result = await asyncio.wait_for(
                agent.__getattribute__(step.method)(
                    **step.params,
                    **options
                ),
                timeout=step.timeout
            )
            duration = (datetime.now() - start_time).total_seconds()
            
            # Update step state and result
            step.state = WorkflowState.COMPLETED
            step.result = result
            
            # Update monitoring metrics
            self.monitoring_metrics["steps"]["successful"] += 1
            self.monitoring_metrics["steps"]["average_duration"] = (
                (self.monitoring_metrics["steps"]["average_duration"] *
                 (self.monitoring_metrics["steps"]["total"] - 1) +
                 duration) /
                self.monitoring_metrics["steps"]["total"]
            )
            
            return {
                "success": True,
                "step_id": step.id,
                "result": result,
                "duration": duration
            }
            
        except Exception as e:
            self.logger.error(f"Step execution failed: {str(e)}")
            step.state = WorkflowState.FAILED
            self.monitoring_metrics["steps"]["failed"] += 1
            return {
                "success": False,
                "step_id": step.id,
                "error": str(e)
            }

    async def _monitor_workflows(self) -> None:
        """Monitor workflows continuously"""
        while True:
            try:
                current_time = datetime.now()
                
                for workflow_id, workflow in self.workflows.items():
                    if workflow["state"] == WorkflowState.RUNNING:
                        # Check for timeouts
                        started_at = datetime.fromisoformat(
                            workflow["started_at"]
                        )
                        if (current_time - started_at).total_seconds() > workflow["timeout"]:
                            await self._handle_workflow_timeout(workflow)
                        
                        # Check for stuck steps
                        await self._check_stuck_steps(workflow)
                
                # Wait before next check
                await asyncio.sleep(60)  # Check every minute
                
            except Exception as e:
                self.logger.error(f"Error in workflow monitoring: {str(e)}")
                await asyncio.sleep(60)

    async def _monitor_agents(self) -> None:
        """Monitor agent health continuously"""
        while True:
            try:
                for agent_type, agent in self.agent_registry.items():
                    # Check agent health
                    health = await agent.get_status()
                    
                    if not health.get("active", False):
                        self.logger.warning(
                            f"Agent {agent_type} is not active"
                        )
                        # Handle agent failure
                        await self._handle_agent_failure(
                            agent_type,
                            agent,
                            health
                        )
                
                # Wait before next check
                await asyncio.sleep(300)  # Check every 5 minutes
                
            except Exception as e:
                self.logger.error(f"Error in agent monitoring: {str(e)}")
                await asyncio.sleep(300)

    async def _cleanup_workflows(self) -> None:
        """Clean up completed workflows"""
        while True:
            try:
                current_time = datetime.now()
                retention_limit = current_time - timedelta(days=7)
                
                # Move old workflows to history
                completed_workflows = [
                    workflow_id
                    for workflow_id, workflow in self.workflows.items()
                    if (workflow["state"] in [WorkflowState.COMPLETED, WorkflowState.FAILED] and
                        datetime.fromisoformat(workflow["completed_at"]) < retention_limit)
                ]
                
                for workflow_id in completed_workflows:
                    workflow = self.workflows.pop(workflow_id)
                    self.workflow_history.append(workflow)
                
                # Trim history if needed
                if len(self.workflow_history) > 1000:
                    self.workflow_history = self.workflow_history[-1000:]
                
                # Wait before next cleanup
                await asyncio.sleep(3600)  # Clean up every hour
                
            except Exception as e:
                self.logger.error(f"Error in workflow cleanup: {str(e)}")
                await asyncio.sleep(3600)

# Global data orchestrator instance
data_orchestrator = DataOrchestrationAgent()
