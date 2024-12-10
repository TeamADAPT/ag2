"""
API Gateway Agent Implementation
This agent handles API management, routing, and security.
"""

from typing import Any, Dict, List, Optional, Set, Union
import asyncio
import logging
from datetime import datetime
import json
import jwt
import hashlib
import re

from ..base_agent import BaseAgent, AgentConfig
from ...config.settings.base_config import config
from ...integration.databases.utils import db_utils

class ApiMethod(str):
    """API method definitions"""
    GET = "GET"
    POST = "POST"
    PUT = "PUT"
    DELETE = "DELETE"
    PATCH = "PATCH"
    OPTIONS = "OPTIONS"
    HEAD = "HEAD"

class ApiVersion(str):
    """API version definitions"""
    V1 = "v1"
    V2 = "v2"
    LATEST = "latest"
    BETA = "beta"
    STABLE = "stable"

class ApiGatewayAgent(BaseAgent):
    """
    API Gateway Agent responsible for handling API management,
    routing, and security.
    """

    def __init__(self):
        super().__init__(AgentConfig(
            name="ApiGateway",
            description="Handles API management and routing",
            capabilities=[
                "api_routing",
                "request_validation",
                "rate_limiting",
                "authentication"
            ],
            required_tools=[
                "api_router",
                "request_validator",
                "rate_limiter"
            ],
            max_concurrent_tasks=50,
            priority_level=2
        ))
        self.routes: Dict[str, Dict] = {}
        self.rate_limits: Dict[str, Dict] = {}
        self.api_keys: Dict[str, Dict] = {}
        self.request_logs: List[Dict] = []

    async def initialize(self) -> bool:
        """Initialize the API Gateway Agent"""
        try:
            self.logger.info("Initializing API Gateway Agent...")
            
            # Initialize routes
            await self._initialize_routes()
            
            # Initialize rate limiting
            await self._initialize_rate_limiting()
            
            # Initialize authentication
            await self._initialize_authentication()
            
            self.logger.info("API Gateway Agent initialized successfully")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to initialize API Gateway Agent: {str(e)}")
            return False

    async def _initialize_routes(self) -> None:
        """Initialize API routes"""
        try:
            # Set up route structure
            self.routes = {
                ApiVersion.V1: {
                    "endpoints": {},
                    "middleware": [],
                    "documentation": {}
                },
                ApiVersion.V2: {
                    "endpoints": {},
                    "middleware": [],
                    "documentation": {}
                },
                ApiVersion.LATEST: {
                    "endpoints": {},
                    "middleware": [],
                    "documentation": {}
                }
            }
            
            # Load stored routes
            stored_routes = await db_utils.get_agent_state(
                self.id,
                "api_routes"
            )
            
            if stored_routes:
                self._merge_routes(stored_routes)
                
            # Initialize default middleware
            await self._initialize_middleware()
                
        except Exception as e:
            raise Exception(f"Failed to initialize routes: {str(e)}")

    async def _initialize_rate_limiting(self) -> None:
        """Initialize rate limiting"""
        try:
            # Set up rate limit configuration
            self.rate_limits = {
                "default": {
                    "requests_per_second": 10,
                    "burst": 20,
                    "window_seconds": 60
                },
                "authenticated": {
                    "requests_per_second": 50,
                    "burst": 100,
                    "window_seconds": 60
                },
                "internal": {
                    "requests_per_second": 100,
                    "burst": 200,
                    "window_seconds": 60
                }
            }
            
            # Load custom rate limits
            custom_limits = await db_utils.get_agent_state(
                self.id,
                "rate_limits"
            )
            
            if custom_limits:
                self.rate_limits.update(custom_limits)
                
        except Exception as e:
            raise Exception(f"Failed to initialize rate limiting: {str(e)}")

    async def _initialize_authentication(self) -> None:
        """Initialize authentication system"""
        try:
            # Set up authentication configuration
            self.auth_config = {
                "jwt": {
                    "enabled": True,
                    "algorithm": "HS256",
                    "expiration_hours": 24,
                    "refresh_enabled": True
                },
                "api_keys": {
                    "enabled": True,
                    "expiration_days": 90,
                    "rotation_enabled": True
                },
                "oauth": {
                    "enabled": False,
                    "providers": []
                }
            }
            
            # Load API keys
            stored_keys = await db_utils.get_agent_state(
                self.id,
                "api_keys"
            )
            
            if stored_keys:
                self.api_keys = stored_keys
                
        except Exception as e:
            raise Exception(f"Failed to initialize authentication: {str(e)}")

    async def _initialize_middleware(self) -> None:
        """Initialize API middleware"""
        try:
            # Set up default middleware
            default_middleware = [
                {
                    "name": "request_validation",
                    "enabled": True,
                    "order": 1
                },
                {
                    "name": "authentication",
                    "enabled": True,
                    "order": 2
                },
                {
                    "name": "rate_limiting",
                    "enabled": True,
                    "order": 3
                },
                {
                    "name": "logging",
                    "enabled": True,
                    "order": 4
                }
            ]
            
            # Apply middleware to all versions
            for version in self.routes:
                self.routes[version]["middleware"] = default_middleware
                
        except Exception as e:
            raise Exception(f"Failed to initialize middleware: {str(e)}")

    async def process_task(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process API gateway tasks
        
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
                'route_request': self._handle_route_request,
                'manage_routes': self._handle_route_management,
                'authentication': self._handle_authentication,
                'rate_limiting': self._handle_rate_limiting,
                'api_documentation': self._handle_documentation
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

    async def _handle_route_request(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """Handle API route request"""
        method = task.get('method')
        path = task.get('path')
        version = task.get('version', ApiVersion.LATEST)
        headers = task.get('headers', {})
        body = task.get('body')
        
        try:
            # Apply middleware
            middleware_result = await self._apply_middleware(
                method,
                path,
                version,
                headers,
                body
            )
            
            if not middleware_result['success']:
                return middleware_result
            
            # Route request
            route_result = await self._route_request(
                method,
                path,
                version,
                middleware_result['processed_request']
            )
            
            return {
                'success': True,
                'method': method,
                'path': path,
                'version': version,
                'result': route_result,
                'timestamp': datetime.now().isoformat()
            }
            
        except Exception as e:
            raise Exception(f"Request routing failed: {str(e)}")

    async def _handle_route_management(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """Handle route management tasks"""
        operation = task.get('operation')
        version = task.get('version')
        route_data = task.get('route')
        
        try:
            if operation == "add":
                result = await self._add_route(
                    version,
                    route_data
                )
            elif operation == "update":
                result = await self._update_route(
                    version,
                    route_data
                )
            elif operation == "delete":
                result = await self._delete_route(
                    version,
                    route_data
                )
            else:
                raise ValueError(f"Unknown route operation: {operation}")
            
            return {
                'success': True,
                'operation': operation,
                'result': result,
                'timestamp': datetime.now().isoformat()
            }
            
        except Exception as e:
            raise Exception(f"Route management failed: {str(e)}")

    async def _apply_middleware(
        self,
        method: str,
        path: str,
        version: str,
        headers: Dict[str, str],
        body: Any
    ) -> Dict[str, Any]:
        """Apply middleware to request"""
        try:
            request = {
                "method": method,
                "path": path,
                "version": version,
                "headers": headers,
                "body": body,
                "timestamp": datetime.now().isoformat()
            }
            
            # Get middleware chain
            middleware_chain = self.routes[version]["middleware"]
            
            # Apply middleware in order
            for middleware in sorted(middleware_chain, key=lambda x: x["order"]):
                if not middleware["enabled"]:
                    continue
                    
                handler = getattr(
                    self,
                    f"_apply_{middleware['name']}_middleware"
                )
                result = await handler(request)
                
                if not result["success"]:
                    return result
                    
                request = result["processed_request"]
            
            return {
                "success": True,
                "processed_request": request
            }
            
        except Exception as e:
            raise Exception(f"Middleware application failed: {str(e)}")

    async def _apply_request_validation_middleware(
        self,
        request: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Apply request validation middleware"""
        try:
            # Validate method
            if request["method"] not in ApiMethod.__dict__.values():
                return {
                    "success": False,
                    "error": f"Invalid method: {request['method']}"
                }
            
            # Validate path
            if not self._validate_path(request["path"]):
                return {
                    "success": False,
                    "error": f"Invalid path: {request['path']}"
                }
            
            # Validate version
            if request["version"] not in ApiVersion.__dict__.values():
                return {
                    "success": False,
                    "error": f"Invalid version: {request['version']}"
                }
            
            return {
                "success": True,
                "processed_request": request
            }
            
        except Exception as e:
            raise Exception(f"Request validation failed: {str(e)}")

    async def _apply_authentication_middleware(
        self,
        request: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Apply authentication middleware"""
        try:
            # Get authentication token
            auth_header = request["headers"].get("Authorization")
            if not auth_header:
                return {
                    "success": False,
                    "error": "Missing authentication"
                }
            
            # Validate token
            auth_result = await self._validate_authentication(auth_header)
            if not auth_result["success"]:
                return auth_result
            
            # Add authentication info to request
            request["auth"] = auth_result["auth_info"]
            
            return {
                "success": True,
                "processed_request": request
            }
            
        except Exception as e:
            raise Exception(f"Authentication failed: {str(e)}")

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
            event_type="api_gateway_task",
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
        self.logger.error(f"Error in API Gateway Agent: {error_details}")
        
        # Store error for analysis
        await self._store_error(error_details)
        
        # Handle API implications
        await self._handle_api_error(error_details)

    async def _store_error(self, error_details: Dict[str, Any]) -> None:
        """Store error details for analysis"""
        await db_utils.record_event(
            event_type="api_gateway_error",
            data=error_details
        )

    async def _handle_api_error(self, error_details: Dict[str, Any]) -> None:
        """Handle API implications of errors"""
        try:
            # Check for API-related errors
            if any(term in str(error_details).lower() 
                  for term in ["api", "route", "request", "authentication"]):
                # Create API event
                await db_utils.record_event(
                    event_type="api_failure",
                    data=error_details
                )
                
                # Update error statistics
                await self._update_error_stats(error_details)
            
        except Exception as e:
            self.logger.error(f"Failed to handle API error: {str(e)}")
