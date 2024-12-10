"""
Model Error Handler for AATS
Manages error detection, recovery, and fallback strategies for model interactions
"""

import asyncio
import logging
from typing import Any, Dict, List, Optional, Set, Union, Callable
from datetime import datetime, timedelta
import json
import traceback
from enum import Enum

from .model_manager import ModelType
from ..config.settings.agent_model_config import MODEL_CAPABILITIES
from ..integration.databases.utils import db_utils

class ErrorSeverity(str, Enum):
    """Error severity levels"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"

class ErrorCategory(str, Enum):
    """Error category definitions"""
    API = "api"
    RATE_LIMIT = "rate_limit"
    CONTEXT = "context"
    TOKEN = "token"
    TIMEOUT = "timeout"
    VALIDATION = "validation"
    CONTENT = "content"
    SYSTEM = "system"

class ModelErrorHandler:
    """
    Model Error Handler responsible for managing error detection,
    recovery, and fallback strategies.
    """

    def __init__(self):
        self.logger = logging.getLogger("ModelErrorHandler")
        self.error_tracking: Dict[str, Dict] = {}
        self.recovery_strategies: Dict[str, Dict] = {}
        self.error_history: List[Dict] = []
        self.fallback_configs: Dict[str, Dict] = {}

    async def initialize(self) -> bool:
        """Initialize the Model Error Handler"""
        try:
            self.logger.info("Initializing Model Error Handler...")
            
            # Initialize error tracking
            await self._initialize_error_tracking()
            
            # Initialize recovery strategies
            await self._initialize_recovery_strategies()
            
            # Initialize fallback configurations
            await self._initialize_fallback_configs()
            
            # Start monitoring tasks
            self._start_monitoring_tasks()
            
            self.logger.info("Model Error Handler initialized successfully")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to initialize Model Error Handler: {str(e)}")
            return False

    async def _initialize_error_tracking(self) -> None:
        """Initialize error tracking system"""
        try:
            # Initialize tracking for each model
            for model_type in ModelType:
                self.error_tracking[model_type] = {
                    "total_errors": 0,
                    "error_rate": 0.0,
                    "error_counts": {
                        category: 0
                        for category in ErrorCategory
                    },
                    "severity_counts": {
                        severity: 0
                        for severity in ErrorSeverity
                    },
                    "recent_errors": [],
                    "last_error": None
                }
            
            # Load historical errors
            stored_errors = await db_utils.get_agent_state(
                "error_handler",
                "error_tracking"
            )
            
            if stored_errors:
                self._merge_error_tracking(stored_errors)
                
        except Exception as e:
            raise Exception(f"Failed to initialize error tracking: {str(e)}")

    async def _initialize_recovery_strategies(self) -> None:
        """Initialize recovery strategies"""
        try:
            self.recovery_strategies = {
                ErrorCategory.API: {
                    "max_retries": 3,
                    "retry_delay": 1.0,
                    "exponential_backoff": True,
                    "fallback_required": True
                },
                ErrorCategory.RATE_LIMIT: {
                    "max_retries": 5,
                    "retry_delay": 5.0,
                    "exponential_backoff": True,
                    "fallback_required": False
                },
                ErrorCategory.CONTEXT: {
                    "max_retries": 2,
                    "retry_delay": 0.5,
                    "context_reduction": 0.5,
                    "fallback_required": True
                },
                ErrorCategory.TOKEN: {
                    "max_retries": 2,
                    "retry_delay": 0.5,
                    "token_reduction": 0.3,
                    "fallback_required": True
                },
                ErrorCategory.TIMEOUT: {
                    "max_retries": 3,
                    "retry_delay": 2.0,
                    "timeout_increase": 1.5,
                    "fallback_required": True
                },
                ErrorCategory.VALIDATION: {
                    "max_retries": 2,
                    "retry_delay": 0.5,
                    "validation_relaxation": True,
                    "fallback_required": False
                },
                ErrorCategory.CONTENT: {
                    "max_retries": 2,
                    "retry_delay": 0.5,
                    "content_filtering": True,
                    "fallback_required": True
                },
                ErrorCategory.SYSTEM: {
                    "max_retries": 5,
                    "retry_delay": 5.0,
                    "system_check": True,
                    "fallback_required": True
                }
            }
            
            # Load custom strategies
            custom_strategies = await db_utils.get_agent_state(
                "error_handler",
                "recovery_strategies"
            )
            
            if custom_strategies:
                self._merge_strategies(custom_strategies)
                
        except Exception as e:
            raise Exception(f"Failed to initialize recovery strategies: {str(e)}")

    async def _initialize_fallback_configs(self) -> None:
        """Initialize fallback configurations"""
        try:
            self.fallback_configs = {
                ModelType.CLAUDE_35_SONNET: {
                    "fallback_models": [
                        ModelType.MISTRAL_LARGE,
                        ModelType.COHERE_COMMAND
                    ],
                    "fallback_threshold": 0.3,
                    "performance_threshold": 0.7
                },
                ModelType.LLAMA_32_90B: {
                    "fallback_models": [
                        ModelType.PHI_35_VISION,
                        ModelType.MISTRAL_LARGE
                    ],
                    "fallback_threshold": 0.3,
                    "performance_threshold": 0.7
                },
                ModelType.COHERE_COMMAND: {
                    "fallback_models": [
                        ModelType.PHI_35_MEDIUM,
                        ModelType.MISTRAL_LARGE
                    ],
                    "fallback_threshold": 0.3,
                    "performance_threshold": 0.7
                }
            }
            
            # Set default fallback config for other models
            default_fallback = {
                "fallback_models": [
                    ModelType.MISTRAL_LARGE,
                    ModelType.PHI_35_MEDIUM
                ],
                "fallback_threshold": 0.3,
                "performance_threshold": 0.7
            }
            
            for model_type in ModelType:
                if model_type not in self.fallback_configs:
                    self.fallback_configs[model_type] = default_fallback.copy()
                    
        except Exception as e:
            raise Exception(f"Failed to initialize fallback configs: {str(e)}")

    def _start_monitoring_tasks(self) -> None:
        """Start error monitoring tasks"""
        asyncio.create_task(self._monitor_errors())
        asyncio.create_task(self._analyze_error_patterns())

    async def handle_error(
        self,
        error: Exception,
        model_type: ModelType,
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Handle model error
        
        Args:
            error: The error that occurred
            model_type: Type of model that encountered error
            context: Error context information
            
        Returns:
            Dictionary containing error handling results
        """
        try:
            # Categorize error
            error_info = self._categorize_error(error)
            
            # Update error tracking
            await self._update_error_tracking(
                model_type,
                error_info
            )
            
            # Get recovery strategy
            strategy = self.recovery_strategies[error_info["category"]]
            
            # Attempt recovery
            recovery_result = await self._attempt_recovery(
                error_info,
                strategy,
                model_type,
                context
            )
            
            # Check if fallback needed
            if (not recovery_result["success"] and
                strategy["fallback_required"]):
                fallback_result = await self._handle_fallback(
                    model_type,
                    error_info,
                    context
                )
                recovery_result["fallback"] = fallback_result
            
            # Store error handling result
            await self._store_error_handling(
                error_info,
                recovery_result
            )
            
            return recovery_result
            
        except Exception as e:
            self.logger.error(f"Error handling failed: {str(e)}")
            return {
                "success": False,
                "error": str(e)
            }

    def _categorize_error(self, error: Exception) -> Dict[str, Any]:
        """Categorize error and determine severity"""
        error_info = {
            "error_type": type(error).__name__,
            "error_message": str(error),
            "timestamp": datetime.now().isoformat(),
            "stack_trace": traceback.format_exc()
        }
        
        # Determine category
        if "api" in str(error).lower():
            error_info["category"] = ErrorCategory.API
        elif "rate" in str(error).lower():
            error_info["category"] = ErrorCategory.RATE_LIMIT
        elif "context" in str(error).lower():
            error_info["category"] = ErrorCategory.CONTEXT
        elif "token" in str(error).lower():
            error_info["category"] = ErrorCategory.TOKEN
        elif "timeout" in str(error).lower():
            error_info["category"] = ErrorCategory.TIMEOUT
        elif "validation" in str(error).lower():
            error_info["category"] = ErrorCategory.VALIDATION
        elif "content" in str(error).lower():
            error_info["category"] = ErrorCategory.CONTENT
        else:
            error_info["category"] = ErrorCategory.SYSTEM
        
        # Determine severity
        if error_info["category"] in [ErrorCategory.API, ErrorCategory.SYSTEM]:
            error_info["severity"] = ErrorSeverity.HIGH
        elif error_info["category"] in [ErrorCategory.RATE_LIMIT, ErrorCategory.TIMEOUT]:
            error_info["severity"] = ErrorSeverity.MEDIUM
        else:
            error_info["severity"] = ErrorSeverity.LOW
        
        return error_info

    async def _attempt_recovery(
        self,
        error_info: Dict[str, Any],
        strategy: Dict[str, Any],
        model_type: ModelType,
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Attempt error recovery"""
        try:
            attempts = 0
            delay = strategy["retry_delay"]
            
            while attempts < strategy["max_retries"]:
                try:
                    # Apply recovery modifications
                    modified_context = await self._modify_context(
                        error_info["category"],
                        context,
                        strategy
                    )
                    
                    # Attempt retry
                    result = await self._retry_request(
                        model_type,
                        modified_context
                    )
                    
                    return {
                        "success": True,
                        "attempts": attempts + 1,
                        "result": result
                    }
                    
                except Exception as e:
                    attempts += 1
                    if strategy["exponential_backoff"]:
                        delay *= 2
                    await asyncio.sleep(delay)
            
            return {
                "success": False,
                "attempts": attempts,
                "error": "Max retries exceeded"
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }

    async def _handle_fallback(
        self,
        model_type: ModelType,
        error_info: Dict[str, Any],
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Handle fallback to alternative model"""
        try:
            fallback_config = self.fallback_configs[model_type]
            
            for fallback_model in fallback_config["fallback_models"]:
                try:
                    # Check fallback model availability
                    if not await self._check_model_availability(fallback_model):
                        continue
                    
                    # Attempt request with fallback model
                    result = await self._retry_request(
                        fallback_model,
                        context
                    )
                    
                    # Validate result quality
                    if await self._validate_fallback_result(
                        result,
                        fallback_config["performance_threshold"]
                    ):
                        return {
                            "success": True,
                            "model": fallback_model,
                            "result": result
                        }
                    
                except Exception:
                    continue
            
            return {
                "success": False,
                "error": "No suitable fallback models available"
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }

    async def _monitor_errors(self) -> None:
        """Monitor errors continuously"""
        while True:
            try:
                current_time = datetime.now()
                
                for model_type, tracking in self.error_tracking.items():
                    # Calculate error rates
                    recent_errors = [
                        error for error in tracking["recent_errors"]
                        if (current_time - datetime.fromisoformat(error["timestamp"])) <=
                        timedelta(hours=1)
                    ]
                    
                    if recent_errors:
                        # Update error rates
                        tracking["error_rate"] = len(recent_errors) / 100  # Assuming 100 requests/hour baseline
                        
                        # Check for error patterns
                        await self._check_error_patterns(
                            model_type,
                            recent_errors
                        )
                
                # Wait before next check
                await asyncio.sleep(300)  # Check every 5 minutes
                
            except Exception as e:
                self.logger.error(f"Error in error monitoring: {str(e)}")
                await asyncio.sleep(300)

    async def _analyze_error_patterns(self) -> None:
        """Analyze error patterns continuously"""
        while True:
            try:
                for model_type, tracking in self.error_tracking.items():
                    # Analyze patterns in recent errors
                    patterns = await self._find_error_patterns(
                        tracking["recent_errors"]
                    )
                    
                    if patterns:
                        # Update recovery strategies based on patterns
                        await self._update_recovery_strategies(patterns)
                        
                        # Store pattern analysis
                        await self._store_pattern_analysis(
                            model_type,
                            patterns
                        )
                
                # Wait before next analysis
                await asyncio.sleep(3600)  # Analyze every hour
                
            except Exception as e:
                self.logger.error(f"Error in pattern analysis: {str(e)}")
                await asyncio.sleep(3600)

    async def _store_error_handling(
        self,
        error_info: Dict[str, Any],
        handling_result: Dict[str, Any]
    ) -> None:
        """Store error handling results"""
        try:
            await db_utils.record_event(
                event_type="error_handling",
                data={
                    "error_info": error_info,
                    "handling_result": handling_result,
                    "timestamp": datetime.now().isoformat()
                }
            )
            
        except Exception as e:
            self.logger.error(f"Failed to store error handling: {str(e)}")

# Global error handler instance
error_handler = ModelErrorHandler()
