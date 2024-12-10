"""
Data Pipeline Agent Implementation
This agent handles data processing pipeline creation and management
"""

import asyncio
import logging
from typing import Any, Dict, List, Optional, Set, Union, Callable
from datetime import datetime
import json
import yaml
import uuid
from enum import Enum
import networkx as nx
from dataclasses import dataclass
import dask.dataframe as dd
from prefect import Flow, task, Task
from prefect.engine.state import State

from ..base_agent import BaseAgent, AgentConfig
from ...config.settings.base_config import config
from ...integration.databases.utils import db_utils
from .data_orchestration_agent import data_orchestrator

class PipelineState(str, Enum):
    """Pipeline state definitions"""
    CREATED = "created"
    CONFIGURING = "configuring"
    READY = "ready"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"

class StageType(str, Enum):
    """Pipeline stage type definitions"""
    INPUT = "input"
    PROCESS = "process"
    TRANSFORM = "transform"
    VALIDATE = "validate"
    OUTPUT = "output"
    CUSTOM = "custom"

@dataclass
class PipelineStage:
    """Pipeline stage definition"""
    id: str
    type: StageType
    name: str
    config: Dict[str, Any]
    dependencies: List[str]
    retry_config: Dict[str, Any]
    timeout: int
    state: PipelineState = PipelineState.CREATED
    result: Optional[Dict] = None

class DataPipelineAgent(BaseAgent):
    """
    Data Pipeline Agent responsible for managing data
    processing pipelines.
    """

    def __init__(self):
        super().__init__(AgentConfig(
            name="DataPipeline",
            description="Handles data pipeline management",
            capabilities=[
                "pipeline_creation",
                "pipeline_execution",
                "pipeline_monitoring",
                "error_handling",
                "optimization"
            ],
            required_tools=[
                "pipeline_manager",
                "execution_engine",
                "monitor"
            ],
            max_concurrent_tasks=5,
            priority_level=2
        ))
        self.pipelines: Dict[str, Dict] = {}
        self.stage_registry: Dict[str, Callable] = {}
        self.pipeline_metrics: Dict[str, Dict] = {}
        self.active_flows: Dict[str, Flow] = {}

    async def initialize(self) -> bool:
        """Initialize the Data Pipeline Agent"""
        try:
            self.logger.info("Initializing Data Pipeline Agent...")
            
            # Initialize stage registry
            await self._initialize_stage_registry()
            
            # Initialize pipeline engine
            await self._initialize_pipeline_engine()
            
            # Initialize metrics tracking
            await self._initialize_metrics_tracking()
            
            # Start monitoring tasks
            self._start_monitoring_tasks()
            
            self.logger.info("Data Pipeline Agent initialized successfully")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to initialize Data Pipeline Agent: {str(e)}")
            return False

    async def _initialize_stage_registry(self) -> None:
        """Initialize pipeline stage registry"""
        try:
            # Register built-in stage types
            self.stage_registry = {
                StageType.INPUT: {
                    "file": self._stage_file_input,
                    "database": self._stage_db_input,
                    "stream": self._stage_stream_input
                },
                StageType.PROCESS: {
                    "filter": self._stage_filter,
                    "aggregate": self._stage_aggregate,
                    "join": self._stage_join
                },
                StageType.TRANSFORM: {
                    "map": self._stage_map,
                    "reduce": self._stage_reduce,
                    "window": self._stage_window
                },
                StageType.VALIDATE: {
                    "schema": self._stage_schema_validate,
                    "quality": self._stage_quality_validate,
                    "business": self._stage_business_validate
                },
                StageType.OUTPUT: {
                    "file": self._stage_file_output,
                    "database": self._stage_db_output,
                    "stream": self._stage_stream_output
                }
            }
            
            # Initialize stage configurations
            self.stage_configs = {
                "input": {
                    "batch_size": 1000,
                    "parallel_reads": 4
                },
                "process": {
                    "chunk_size": 10000,
                    "memory_limit": "4GB"
                },
                "output": {
                    "buffer_size": 1000,
                    "flush_interval": 60
                }
            }
            
        except Exception as e:
            raise Exception(f"Failed to initialize stage registry: {str(e)}")

    async def _initialize_pipeline_engine(self) -> None:
        """Initialize pipeline execution engine"""
        try:
            # Initialize pipeline configurations
            self.pipeline_configs = {
                "max_parallel_stages": 5,
                "default_timeout": 3600,
                "checkpoint_interval": 300,
                "retry_limit": 3
            }
            
            # Initialize execution engine settings
            self.engine_configs = {
                "scheduler": "dask",
                "executor": "prefect",
                "monitoring": "prometheus"
            }
            
            # Load stored pipelines
            stored_pipelines = await db_utils.get_agent_state(
                self.id,
                "pipelines"
            )
            
            if stored_pipelines:
                await self._restore_pipelines(stored_pipelines)
                
        except Exception as e:
            raise Exception(f"Failed to initialize pipeline engine: {str(e)}")

    async def _initialize_metrics_tracking(self) -> None:
        """Initialize metrics tracking"""
        try:
            self.pipeline_metrics = {
                "executions": {
                    "total": 0,
                    "successful": 0,
                    "failed": 0,
                    "average_duration": 0.0
                },
                "stages": {
                    "total": 0,
                    "successful": 0,
                    "failed": 0,
                    "average_duration": 0.0
                },
                "data": {
                    "total_volume": 0,
                    "processed_volume": 0,
                    "error_rate": 0.0
                }
            }
            
            # Load historical metrics
            stored_metrics = await db_utils.get_agent_state(
                self.id,
                "pipeline_metrics"
            )
            
            if stored_metrics:
                self._merge_metrics(stored_metrics)
                
        except Exception as e:
            raise Exception(f"Failed to initialize metrics tracking: {str(e)}")

    def _start_monitoring_tasks(self) -> None:
        """Start pipeline monitoring tasks"""
        asyncio.create_task(self._monitor_pipelines())
        asyncio.create_task(self._monitor_resources())
        asyncio.create_task(self._cleanup_pipelines())

    async def create_pipeline(
        self,
        pipeline_config: Dict[str, Any],
        options: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """
        Create a new pipeline
        
        Args:
            pipeline_config: Pipeline configuration
            options: Optional pipeline options
            
        Returns:
            Dictionary containing pipeline creation results
        """
        try:
            # Generate pipeline ID
            pipeline_id = str(uuid.uuid4())
            
            # Parse and validate pipeline configuration
            pipeline = await self._parse_pipeline_config(
                pipeline_id,
                pipeline_config,
                options or {}
            )
            
            # Create pipeline flow
            flow = await self._create_pipeline_flow(pipeline)
            
            # Initialize pipeline state
            pipeline["state"] = PipelineState.CREATED
            pipeline["created_at"] = datetime.now().isoformat()
            pipeline["flow"] = flow
            pipeline["metrics"] = {
                "stages_total": len(pipeline["stages"]),
                "stages_completed": 0,
                "data_processed": 0,
                "duration": 0.0
            }
            
            # Store pipeline
            self.pipelines[pipeline_id] = pipeline
            self.active_flows[pipeline_id] = flow
            
            # Update metrics
            self.pipeline_metrics["executions"]["total"] += 1
            
            return {
                "success": True,
                "pipeline_id": pipeline_id,
                "state": pipeline["state"]
            }
            
        except Exception as e:
            self.logger.error(f"Pipeline creation failed: {str(e)}")
            return {
                "success": False,
                "error": str(e)
            }

    async def execute_pipeline(
        self,
        pipeline_id: str,
        options: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """
        Execute a pipeline
        
        Args:
            pipeline_id: Pipeline identifier
            options: Optional execution options
            
        Returns:
            Dictionary containing pipeline execution results
        """
        try:
            # Get pipeline
            pipeline = self.pipelines.get(pipeline_id)
            if not pipeline:
                return {
                    "success": False,
                    "error": f"Pipeline not found: {pipeline_id}"
                }
            
            # Check pipeline state
            if pipeline["state"] not in [PipelineState.CREATED, PipelineState.READY]:
                return {
                    "success": False,
                    "error": f"Invalid pipeline state: {pipeline['state']}"
                }
            
            # Update pipeline state
            pipeline["state"] = PipelineState.RUNNING
            pipeline["started_at"] = datetime.now().isoformat()
            
            # Get pipeline flow
            flow = self.active_flows[pipeline_id]
            
            # Execute pipeline
            try:
                state = await self._execute_pipeline_flow(
                    flow,
                    pipeline,
                    options or {}
                )
                
                if state.is_successful():
                    pipeline["state"] = PipelineState.COMPLETED
                    self.pipeline_metrics["executions"]["successful"] += 1
                else:
                    pipeline["state"] = PipelineState.FAILED
                    self.pipeline_metrics["executions"]["failed"] += 1
                    
            except Exception as e:
                pipeline["state"] = PipelineState.FAILED
                self.pipeline_metrics["executions"]["failed"] += 1
                raise
            
            # Update pipeline metrics
            pipeline["completed_at"] = datetime.now().isoformat()
            pipeline["metrics"]["duration"] = (
                datetime.fromisoformat(pipeline["completed_at"]) -
                datetime.fromisoformat(pipeline["started_at"])
            ).total_seconds()
            
            return {
                "success": state.is_successful(),
                "pipeline_id": pipeline_id,
                "state": pipeline["state"],
                "result": state.result
            }
            
        except Exception as e:
            self.logger.error(f"Pipeline execution failed: {str(e)}")
            return {
                "success": False,
                "error": str(e)
            }

    async def _monitor_pipelines(self) -> None:
        """Monitor pipelines continuously"""
        while True:
            try:
                current_time = datetime.now()
                
                for pipeline_id, pipeline in self.pipelines.items():
                    if pipeline["state"] == PipelineState.RUNNING:
                        # Check for timeouts
                        started_at = datetime.fromisoformat(
                            pipeline["started_at"]
                        )
                        if (current_time - started_at).total_seconds() > pipeline["timeout"]:
                            await self._handle_pipeline_timeout(pipeline)
                        
                        # Check stage health
                        await self._check_stage_health(pipeline)
                        
                        # Update metrics
                        await self._update_pipeline_metrics(pipeline)
                
                # Wait before next check
                await asyncio.sleep(60)  # Check every minute
                
            except Exception as e:
                self.logger.error(f"Error in pipeline monitoring: {str(e)}")
                await asyncio.sleep(60)

    async def _monitor_resources(self) -> None:
        """Monitor resource usage"""
        while True:
            try:
                # Check system resources
                resources = await self._get_resource_usage()
                
                # Check thresholds
                if resources["memory_usage"] > 0.9:  # 90% memory usage
                    await self._handle_resource_pressure("memory")
                    
                if resources["cpu_usage"] > 0.8:  # 80% CPU usage
                    await self._handle_resource_pressure("cpu")
                
                # Wait before next check
                await asyncio.sleep(300)  # Check every 5 minutes
                
            except Exception as e:
                self.logger.error(f"Error in resource monitoring: {str(e)}")
                await asyncio.sleep(300)

    async def _cleanup_pipelines(self) -> None:
        """Clean up completed pipelines"""
        while True:
            try:
                current_time = datetime.now()
                retention_limit = current_time - timedelta(days=7)
                
                # Clean up old pipelines
                for pipeline_id in list(self.pipelines.keys()):
                    pipeline = self.pipelines[pipeline_id]
                    if (pipeline["state"] in [PipelineState.COMPLETED, PipelineState.FAILED] and
                        datetime.fromisoformat(pipeline["completed_at"]) < retention_limit):
                        # Archive pipeline data
                        await self._archive_pipeline(pipeline)
                        
                        # Remove from active tracking
                        del self.pipelines[pipeline_id]
                        if pipeline_id in self.active_flows:
                            del self.active_flows[pipeline_id]
                
                # Wait before next cleanup
                await asyncio.sleep(3600)  # Clean up every hour
                
            except Exception as e:
                self.logger.error(f"Error in pipeline cleanup: {str(e)}")
                await asyncio.sleep(3600)

# Global pipeline agent instance
pipeline_agent = DataPipelineAgent()
