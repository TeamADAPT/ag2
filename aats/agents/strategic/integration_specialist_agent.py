"""
Integration Specialist Agent Implementation
This agent manages system integrations, API coordination, and service management.
"""

from typing import Any, Dict, List, Optional, Set, Union
import asyncio
import logging
from datetime import datetime
import json
import aiohttp
from pathlib import Path

from ..base_agent import BaseAgent, AgentConfig
from ...config.settings.base_config import config
from ...integration.databases.utils import db_utils

class IntegrationType(str):
    """Integration type definitions"""
    API = "api"
    SERVICE = "service"
    EVENT = "event"
    DATA = "data"

class IntegrationStatus(str):
    """Integration status definitions"""
    ACTIVE = "active"
    INACTIVE = "inactive"
    ERROR = "error"
    MAINTENANCE = "maintenance"

class IntegrationSpecialistAgent(BaseAgent):
    """
    Integration Specialist Agent responsible for managing system
    integrations and service coordination.
    """

    def __init__(self):
        super().__init__(AgentConfig(
            name="IntegrationSpecialist",
            description="Manages system integrations and service coordination",
            capabilities=[
                "api_management",
                "service_coordination",
                "integration_monitoring",
                "protocol_handling"
            ],
            required_tools=[
                "api_gateway",
                "service_registry",
                "protocol_handler"
            ],
            max_concurrent_tasks=5,
            priority_level=1
        ))
        self.integrations: Dict[str, Dict] = {}
        self.services: Dict[str, Dict] = {}
        self.endpoints: Dict[str, Dict] = {}
        self.protocols: Dict[str, Dict] = {}

    async def initialize(self) -> bool:
        """Initialize the Integration Specialist Agent"""
        try:
            self.logger.info("Initializing Integration Specialist Agent...")
            
            # Initialize integrations
            await self._initialize_integrations()
            
            # Initialize services
            await self._initialize_services()
            
            # Initialize protocols
            await self._initialize_protocols()
            
            self.logger.info("Integration Specialist Agent initialized successfully")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to initialize Integration Specialist Agent: {str(e)}")
            return False

    async def _initialize_integrations(self) -> None:
        """Initialize system integrations"""
        try:
            # Load base integrations
            self.integrations = {
                "apis": {
                    "internal": {},
                    "external": {}
                },
                "services": {
                    "core": {},
                    "auxiliary": {}
                },
                "events": {
                    "publishers": {},
                    "subscribers": {}
                }
            }
            
            # Load stored integrations
            stored_integrations = await db_utils.get_agent_state(
                self.id,
                "integrations"
            )
            
            if stored_integrations:
                for category, integrations in stored_integrations.items():
                    if category in self.integrations:
                        self.integrations[category].update(integrations)
                        
        except Exception as e:
            raise Exception(f"Failed to initialize integrations: {str(e)}")

    async def _initialize_services(self) -> None:
        """Initialize service registry"""
        try:
            # Load base services
            self.services = {
                "core": {
                    "database": {
                        "status": IntegrationStatus.ACTIVE,
                        "endpoints": ["postgres", "mongodb", "neo4j", "redis"],
                        "health_check": "/health"
                    },
                    "messaging": {
                        "status": IntegrationStatus.ACTIVE,
                        "endpoints": ["kafka", "rabbitmq"],
                        "health_check": "/health"
                    },
                    "monitoring": {
                        "status": IntegrationStatus.ACTIVE,
                        "endpoints": ["prometheus", "grafana"],
                        "health_check": "/health"
                    }
                },
                "auxiliary": {}
            }
            
            # Load stored services
            stored_services = await db_utils.get_agent_state(
                self.id,
                "services"
            )
            
            if stored_services:
                for category, services in stored_services.items():
                    if category in self.services:
                        self.services[category].update(services)
                        
        except Exception as e:
            raise Exception(f"Failed to initialize services: {str(e)}")

    async def _initialize_protocols(self) -> None:
        """Initialize communication protocols"""
        try:
            # Load base protocols
            self.protocols = {
                "http": {
                    "versions": ["1.1", "2"],
                    "security": ["TLS 1.2", "TLS 1.3"],
                    "methods": ["GET", "POST", "PUT", "DELETE"]
                },
                "grpc": {
                    "enabled": True,
                    "streaming": True,
                    "compression": True
                },
                "websocket": {
                    "enabled": True,
                    "compression": True,
                    "heartbeat": 30
                },
                "mqtt": {
                    "enabled": True,
                    "qos_levels": [0, 1, 2],
                    "retain": True
                }
            }
            
            # Load custom protocols
            custom_protocols = await db_utils.get_agent_state(
                self.id,
                "protocols"
            )
            
            if custom_protocols:
                self.protocols.update(custom_protocols)
                
        except Exception as e:
            raise Exception(f"Failed to initialize protocols: {str(e)}")

    async def process_task(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process integration tasks
        
        Args:
            task: Dictionary containing task details
            
        Returns:
            Dictionary containing the task result
        """
        try:
            task_type = task.get('type', 'unknown')
            self.logger.info(f"Processing task of type: {task_type}")

            # Handle different types of tasks
            handlers = {
                'api_management': self._handle_api_management,
                'service_coordination': self._handle_service_coordination,
                'protocol_handling': self._handle_protocol_handling,
                'integration_monitoring': self._handle_integration_monitoring,
                'endpoint_management': self._handle_endpoint_management
            }

            handler = handlers.get(task_type, self._handle_unknown_task)
            result = await handler(task)

            # Log task completion
            await self._log_task_completion(task, result)

            return result

        except Exception as e:
            self.logger.error(f"Error processing task: {str(e)}")
            await self.handle_error(e, task)
            return {
                'success': False,
                'error': str(e),
                'task_id': task.get('id'),
                'timestamp': datetime.now().isoformat()
            }

    async def _handle_api_management(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """Handle API management tasks"""
        operation = task.get('operation')
        api_type = task.get('api_type')
        api_data = task.get('api')
        
        try:
            if operation == "register":
                result = await self._register_api(
                    api_type,
                    api_data
                )
            elif operation == "update":
                result = await self._update_api(
                    api_type,
                    api_data
                )
            elif operation == "deregister":
                result = await self._deregister_api(
                    api_type,
                    api_data
                )
            else:
                raise ValueError(f"Unknown API operation: {operation}")
            
            return {
                'success': True,
                'operation': operation,
                'result': result,
                'timestamp': datetime.now().isoformat()
            }
            
        except Exception as e:
            raise Exception(f"API management failed: {str(e)}")

    async def _handle_service_coordination(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """Handle service coordination tasks"""
        operation = task.get('operation')
        service_type = task.get('service_type')
        service_data = task.get('service')
        
        try:
            if operation == "register":
                result = await self._register_service(
                    service_type,
                    service_data
                )
            elif operation == "update":
                result = await self._update_service(
                    service_type,
                    service_data
                )
            elif operation == "deregister":
                result = await self._deregister_service(
                    service_type,
                    service_data
                )
            else:
                raise ValueError(f"Unknown service operation: {operation}")
            
            return {
                'success': True,
                'operation': operation,
                'result': result,
                'timestamp': datetime.now().isoformat()
            }
            
        except Exception as e:
            raise Exception(f"Service coordination failed: {str(e)}")

    async def _handle_protocol_handling(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """Handle protocol handling tasks"""
        protocol = task.get('protocol')
        operation = task.get('operation')
        config = task.get('config')
        
        try:
            if operation == "configure":
                result = await self._configure_protocol(
                    protocol,
                    config
                )
            elif operation == "validate":
                result = await self._validate_protocol(
                    protocol,
                    config
                )
            else:
                raise ValueError(f"Unknown protocol operation: {operation}")
            
            return {
                'success': True,
                'operation': operation,
                'result': result,
                'timestamp': datetime.now().isoformat()
            }
            
        except Exception as e:
            raise Exception(f"Protocol handling failed: {str(e)}")

    async def _handle_integration_monitoring(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """Handle integration monitoring tasks"""
        integration_type = task.get('integration_type')
        target = task.get('target')
        
        try:
            # Check integration health
            health = await self._check_integration_health(
                integration_type,
                target
            )
            
            # Get metrics
            metrics = await self._get_integration_metrics(
                integration_type,
                target
            )
            
            return {
                'success': True,
                'health': health,
                'metrics': metrics,
                'timestamp': datetime.now().isoformat()
            }
            
        except Exception as e:
            raise Exception(f"Integration monitoring failed: {str(e)}")

    async def _register_api(
        self,
        api_type: str,
        api_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Register new API"""
        # Validate API data
        validation = await self._validate_api_definition(
            api_type,
            api_data
        )
        
        if not validation['valid']:
            raise ValueError(f"Invalid API definition: {validation['errors']}")
        
        # Add API
        category = "internal" if api_type == "internal" else "external"
        api_id = api_data.get('id')
        self.integrations["apis"][category][api_id] = {
            **api_data,
            "status": IntegrationStatus.ACTIVE,
            "registered_at": datetime.now().isoformat()
        }
        
        # Register endpoints
        await self._register_endpoints(
            api_id,
            api_data.get('endpoints', [])
        )
        
        # Store registration
        await db_utils.record_event(
            event_type="api_registered",
            data={
                "type": api_type,
                "id": api_id,
                "api": api_data
            }
        )
        
        return {
            "id": api_id,
            "type": api_type,
            "status": IntegrationStatus.ACTIVE
        }

    async def _register_service(
        self,
        service_type: str,
        service_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Register new service"""
        # Validate service data
        validation = await self._validate_service_definition(
            service_type,
            service_data
        )
        
        if not validation['valid']:
            raise ValueError(f"Invalid service definition: {validation['errors']}")
        
        # Add service
        category = "core" if service_type == "core" else "auxiliary"
        service_id = service_data.get('id')
        self.services[category][service_id] = {
            **service_data,
            "status": IntegrationStatus.ACTIVE,
            "registered_at": datetime.now().isoformat()
        }
        
        # Register endpoints
        await self._register_endpoints(
            service_id,
            service_data.get('endpoints', [])
        )
        
        # Store registration
        await db_utils.record_event(
            event_type="service_registered",
            data={
                "type": service_type,
                "id": service_id,
                "service": service_data
            }
        )
        
        return {
            "id": service_id,
            "type": service_type,
            "status": IntegrationStatus.ACTIVE
        }

    async def _check_integration_health(
        self,
        integration_type: str,
        target: str
    ) -> Dict[str, Any]:
        """Check integration health status"""
        try:
            if integration_type == IntegrationType.API:
                health = await self._check_api_health(target)
            elif integration_type == IntegrationType.SERVICE:
                health = await self._check_service_health(target)
            else:
                raise ValueError(f"Unknown integration type: {integration_type}")
            
            return health
            
        except Exception as e:
            return {
                "status": IntegrationStatus.ERROR,
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }

    async def _check_api_health(self, api_id: str) -> Dict[str, Any]:
        """Check API health status"""
        try:
            # Get API details
            api = None
            for category in ["internal", "external"]:
                if api_id in self.integrations["apis"][category]:
                    api = self.integrations["apis"][category][api_id]
                    break
            
            if not api:
                raise ValueError(f"API not found: {api_id}")
            
            # Check health endpoint
            health_endpoint = api.get('health_check')
            if health_endpoint:
                async with aiohttp.ClientSession() as session:
                    async with session.get(health_endpoint) as response:
                        health_data = await response.json()
                        return {
                            "status": IntegrationStatus.ACTIVE,
                            "data": health_data,
                            "timestamp": datetime.now().isoformat()
                        }
            
            return {
                "status": api.get('status', IntegrationStatus.INACTIVE),
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            return {
                "status": IntegrationStatus.ERROR,
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }

    async def _check_service_health(self, service_id: str) -> Dict[str, Any]:
        """Check service health status"""
        try:
            # Get service details
            service = None
            for category in ["core", "auxiliary"]:
                if service_id in self.services[category]:
                    service = self.services[category][service_id]
                    break
            
            if not service:
                raise ValueError(f"Service not found: {service_id}")
            
            # Check health endpoint
            health_endpoint = service.get('health_check')
            if health_endpoint:
                async with aiohttp.ClientSession() as session:
                    async with session.get(health_endpoint) as response:
                        health_data = await response.json()
                        return {
                            "status": IntegrationStatus.ACTIVE,
                            "data": health_data,
                            "timestamp": datetime.now().isoformat()
                        }
            
            return {
                "status": service.get('status', IntegrationStatus.INACTIVE),
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            return {
                "status": IntegrationStatus.ERROR,
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }

    async def _log_task_completion(
        self,
        task: Dict[str, Any],
        result: Dict[str, Any]
    ) -> None:
        """Log task completion"""
        event = {
            "timestamp": datetime.now().isoformat(),
            "task": task,
            "result": result,
            "success": result.get('success', False)
        }
        
        # Store event
        await db_utils.record_event(
            event_type="integration_task",
            data=event
        )

    async def handle_error(
        self,
        error: Exception,
        task: Optional[Dict[str, Any]] = None
    ) -> None:
        """Handle errors during task processing"""
        self.state.error_count += 1
        
        error_details = {
            'error_type': type(error).__name__,
            'error_message': str(error),
            'task_id': task.get('id') if task else None,
            'timestamp': datetime.now().isoformat()
        }
        
        # Log error
        self.logger.error(f"Error in Integration Specialist Agent: {error_details}")
        
        # Store error for analysis
        await self._store_error(error_details)
        
        # Handle integration implications
        await self._handle_integration_error(error_details)

    async def _store_error(self, error_details: Dict[str, Any]) -> None:
        """Store error details for analysis"""
        await db_utils.record_event(
            event_type="integration_error",
            data=error_details
        )

    async def _handle_integration_error(self, error_details: Dict[str, Any]) -> None:
        """Handle integration implications of errors"""
        try:
            # Check for integration-related errors
            if any(term in str(error_details).lower() 
                  for term in ["api", "service", "integration", "endpoint"]):
                # Create integration event
                await db_utils.record_event(
                    event_type="integration_failure",
                    data=error_details
                )
                
                # Update status
                await self._update_integration_status(
                    error_details
                )
            
        except Exception as e:
            self.logger.error(f"Failed to handle integration error: {str(e)}")
