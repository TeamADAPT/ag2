"""
Data Integration Agent Implementation
This agent coordinates data flow and integration between different systems
"""

import asyncio
import logging
from typing import Any, Dict, List, Optional, Set, Union
from datetime import datetime
import json
import pandas as pd
import numpy as np
from pathlib import Path
import aiohttp
import aiokafka
import aio_pika
import motor.motor_asyncio
import asyncpg
import redis.asyncio as redis
import neo4j
from minio import Minio

from ..base_agent import BaseAgent, AgentConfig
from ...config.settings.base_config import config
from ...integration.databases.utils import db_utils

class IntegrationType(str):
    """Integration type definitions"""
    ETL = "etl"
    STREAMING = "streaming"
    BATCH = "batch"
    REALTIME = "realtime"
    HYBRID = "hybrid"
    CUSTOM = "custom"

class SystemType(str):
    """System type definitions"""
    DATABASE = "database"
    MESSAGING = "messaging"
    STORAGE = "storage"
    API = "api"
    FILE = "file"
    CUSTOM = "custom"

class DataIntegrationAgent(BaseAgent):
    """
    Data Integration Agent responsible for coordinating data flow
    and integration between different systems.
    """

    def __init__(self):
        super().__init__(AgentConfig(
            name="DataIntegrator",
            description="Handles data integration and flow coordination",
            capabilities=[
                "data_flow_management",
                "system_integration",
                "format_conversion",
                "pipeline_orchestration",
                "error_handling"
            ],
            required_tools=[
                "flow_manager",
                "system_connector",
                "pipeline_orchestrator"
            ],
            max_concurrent_tasks=5,
            priority_level=2
        ))
        self.integration_stats: Dict[str, Dict] = {}
        self.integration_methods: Dict[str, callable] = {}
        self.system_connections: Dict[str, Any] = {}
        self.active_pipelines: Dict[str, Dict] = {}

    async def initialize(self) -> bool:
        """Initialize the Data Integration Agent"""
        try:
            self.logger.info("Initializing Data Integration Agent...")
            
            # Initialize integration methods
            await self._initialize_integration_methods()
            
            # Initialize system connections
            await self._initialize_system_connections()
            
            # Initialize integration stats
            await self._initialize_integration_stats()
            
            # Start monitoring tasks
            self._start_monitoring_tasks()
            
            self.logger.info("Data Integration Agent initialized successfully")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to initialize Data Integration Agent: {str(e)}")
            return False

    async def _initialize_integration_methods(self) -> None:
        """Initialize integration methods"""
        try:
            self.integration_methods = {
                IntegrationType.ETL: {
                    "extract": self._extract_data,
                    "transform": self._transform_data,
                    "load": self._load_data
                },
                IntegrationType.STREAMING: {
                    "produce": self._produce_stream,
                    "consume": self._consume_stream,
                    "process": self._process_stream
                },
                IntegrationType.BATCH: {
                    "collect": self._collect_batch,
                    "process": self._process_batch,
                    "distribute": self._distribute_batch
                },
                IntegrationType.REALTIME: {
                    "sync": self._sync_realtime,
                    "replicate": self._replicate_realtime,
                    "monitor": self._monitor_realtime
                },
                IntegrationType.HYBRID: {
                    "coordinate": self._coordinate_hybrid,
                    "balance": self._balance_hybrid,
                    "optimize": self._optimize_hybrid
                }
            }
            
            # Initialize integration configurations
            self.integration_configs = {
                "etl": {
                    "batch_size": 1000,
                    "timeout": 3600,
                    "retry_limit": 3
                },
                "streaming": {
                    "buffer_size": 1024,
                    "flush_interval": 60,
                    "max_retries": 5
                },
                "batch": {
                    "max_size": 10000,
                    "interval": 3600,
                    "parallel_jobs": 3
                }
            }
            
        except Exception as e:
            raise Exception(f"Failed to initialize integration methods: {str(e)}")

    async def _initialize_system_connections(self) -> None:
        """Initialize system connections"""
        try:
            # Initialize database connections
            self.system_connections[SystemType.DATABASE] = {
                "postgres": await self._init_postgres_connection(),
                "mongodb": await self._init_mongodb_connection(),
                "redis": await self._init_redis_connection(),
                "neo4j": await self._init_neo4j_connection()
            }
            
            # Initialize messaging systems
            self.system_connections[SystemType.MESSAGING] = {
                "kafka": await self._init_kafka_connection(),
                "rabbitmq": await self._init_rabbitmq_connection()
            }
            
            # Initialize storage systems
            self.system_connections[SystemType.STORAGE] = {
                "minio": await self._init_minio_connection(),
                "local": Path(config.storage.local_path)
            }
            
            # Initialize API clients
            self.system_connections[SystemType.API] = {
                "rest": aiohttp.ClientSession(),
                "graphql": aiohttp.ClientSession()
            }
            
        except Exception as e:
            raise Exception(f"Failed to initialize system connections: {str(e)}")

    async def _initialize_integration_stats(self) -> None:
        """Initialize integration statistics"""
        try:
            self.integration_stats = {
                integration_type: {
                    "operations_performed": 0,
                    "successful_operations": 0,
                    "failed_operations": 0,
                    "data_volume": 0,
                    "average_duration": 0.0,
                    "last_operation": None
                }
                for integration_type in IntegrationType.__dict__.keys()
                if not integration_type.startswith('_')
            }
            
            # Load historical stats
            stored_stats = await db_utils.get_agent_state(
                self.id,
                "integration_stats"
            )
            
            if stored_stats:
                self._merge_stats(stored_stats)
                
        except Exception as e:
            raise Exception(f"Failed to initialize integration stats: {str(e)}")

    def _start_monitoring_tasks(self) -> None:
        """Start monitoring tasks"""
        asyncio.create_task(self._monitor_integrations())
        asyncio.create_task(self._monitor_connections())
        asyncio.create_task(self._monitor_pipelines())

    async def integrate_data(
        self,
        source: Dict[str, Any],
        target: Dict[str, Any],
        integration_type: str,
        method: str,
        options: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """
        Integrate data between systems
        
        Args:
            source: Source system configuration
            target: Target system configuration
            integration_type: Type of integration
            method: Integration method
            options: Optional integration options
            
        Returns:
            Dictionary containing integration results
        """
        try:
            # Validate integration type
            if integration_type not in self.integration_methods:
                return {
                    "success": False,
                    "error": f"Invalid integration type: {integration_type}"
                }
            
            # Get integration method
            integrator = self.integration_methods[integration_type].get(method)
            if not integrator:
                return {
                    "success": False,
                    "error": f"Invalid method: {method}"
                }
            
            # Perform integration
            start_time = datetime.now()
            result = await integrator(
                source,
                target,
                options or {}
            )
            duration = (datetime.now() - start_time).total_seconds()
            
            # Update statistics
            await self._update_integration_stats(
                integration_type,
                True,
                duration,
                result.get("data_volume", 0)
            )
            
            return {
                "success": True,
                "integration_type": integration_type,
                "method": method,
                "result": result,
                "duration": duration
            }
            
        except Exception as e:
            self.logger.error(f"Data integration failed: {str(e)}")
            # Update statistics
            await self._update_integration_stats(
                integration_type,
                False,
                0.0,
                0
            )
            return {
                "success": False,
                "error": str(e)
            }

    async def create_pipeline(
        self,
        pipeline_config: Dict[str, Any],
        options: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """
        Create data integration pipeline
        
        Args:
            pipeline_config: Pipeline configuration
            options: Optional pipeline options
            
        Returns:
            Dictionary containing pipeline creation results
        """
        try:
            # Generate pipeline ID
            pipeline_id = f"pipeline_{datetime.now().timestamp()}"
            
            # Initialize pipeline
            pipeline = {
                "id": pipeline_id,
                "config": pipeline_config,
                "status": "initializing",
                "created_at": datetime.now().isoformat(),
                "stats": {
                    "operations": 0,
                    "errors": 0,
                    "data_volume": 0
                }
            }
            
            # Validate pipeline configuration
            validation = await self._validate_pipeline_config(pipeline_config)
            if not validation["valid"]:
                return {
                    "success": False,
                    "error": validation["error"]
                }
            
            # Set up pipeline components
            components = await self._setup_pipeline_components(
                pipeline_config,
                options or {}
            )
            
            pipeline["components"] = components
            pipeline["status"] = "ready"
            
            # Store pipeline
            self.active_pipelines[pipeline_id] = pipeline
            
            return {
                "success": True,
                "pipeline_id": pipeline_id,
                "status": "ready"
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
        Execute data integration pipeline
        
        Args:
            pipeline_id: Pipeline identifier
            options: Optional execution options
            
        Returns:
            Dictionary containing pipeline execution results
        """
        try:
            # Get pipeline
            pipeline = self.active_pipelines.get(pipeline_id)
            if not pipeline:
                return {
                    "success": False,
                    "error": f"Pipeline not found: {pipeline_id}"
                }
            
            # Update pipeline status
            pipeline["status"] = "running"
            
            # Execute pipeline components
            results = []
            for component in pipeline["components"]:
                component_result = await self._execute_pipeline_component(
                    component,
                    options or {}
                )
                results.append(component_result)
                
                if not component_result["success"]:
                    # Handle component failure
                    await self._handle_pipeline_failure(
                        pipeline,
                        component,
                        component_result
                    )
                    return {
                        "success": False,
                        "error": f"Component failed: {component['id']}",
                        "results": results
                    }
            
            # Update pipeline status and stats
            pipeline["status"] = "completed"
            pipeline["stats"]["operations"] += len(results)
            pipeline["stats"]["data_volume"] += sum(
                r.get("data_volume", 0) for r in results
            )
            
            return {
                "success": True,
                "pipeline_id": pipeline_id,
                "results": results
            }
            
        except Exception as e:
            self.logger.error(f"Pipeline execution failed: {str(e)}")
            return {
                "success": False,
                "error": str(e)
            }

    async def _extract_data(
        self,
        source: Dict[str, Any],
        target: Dict[str, Any],
        options: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Extract data from source system"""
        try:
            # Get source system type
            system_type = source.get("type")
            if not system_type:
                raise ValueError("Source system type not specified")
            
            # Get system connection
            connection = self.system_connections[system_type].get(
                source.get("system")
            )
            if not connection:
                raise ValueError(f"System not found: {source.get('system')}")
            
            # Extract data based on system type
            if system_type == SystemType.DATABASE:
                data = await self._extract_from_database(
                    connection,
                    source,
                    options
                )
            elif system_type == SystemType.MESSAGING:
                data = await self._extract_from_messaging(
                    connection,
                    source,
                    options
                )
            elif system_type == SystemType.STORAGE:
                data = await self._extract_from_storage(
                    connection,
                    source,
                    options
                )
            else:
                raise ValueError(f"Unsupported system type: {system_type}")
            
            return {
                "success": True,
                "data": data,
                "data_volume": len(data)
            }
            
        except Exception as e:
            raise Exception(f"Data extraction failed: {str(e)}")

    async def _update_integration_stats(
        self,
        integration_type: str,
        success: bool,
        duration: float,
        data_volume: int
    ) -> None:
        """Update integration statistics"""
        try:
            stats = self.integration_stats[integration_type]
            
            # Update counters
            stats["operations_performed"] += 1
            if success:
                stats["successful_operations"] += 1
            else:
                stats["failed_operations"] += 1
            
            # Update data volume
            stats["data_volume"] += data_volume
            
            # Update average duration
            total_operations = stats["operations_performed"]
            current_avg = stats["average_duration"]
            stats["average_duration"] = (
                (current_avg * (total_operations - 1) + duration) /
                total_operations
            )
            
            stats["last_operation"] = datetime.now().isoformat()
            
            # Store metrics
            await db_utils.record_metric(
                agent_id=self.id,
                metric_type="data_integration",
                value=duration,
                tags={
                    "integration_type": integration_type,
                    "success": success,
                    "data_volume": data_volume
                }
            )
            
        except Exception as e:
            self.logger.error(f"Failed to update integration stats: {str(e)}")

# Global data integrator instance
data_integrator = DataIntegrationAgent()
