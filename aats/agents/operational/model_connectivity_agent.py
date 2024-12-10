"""
Model Connectivity Agent Implementation
This agent handles integration and communication with online LLM models
"""

import asyncio
import logging
from typing import Any, Dict, List, Optional, Set, Union, Callable
from datetime import datetime
import json
import aiohttp
import os
from enum import Enum
from dataclasses import dataclass
import backoff
from asyncio import Semaphore

from ..base_agent import BaseAgent, AgentConfig
from ...config.settings.base_config import config
from ...integration.databases.utils import db_utils

class ModelProvider(str, Enum):
    """Model provider definitions"""
    AZURE = "azure"
    ANTHROPIC = "anthropic"
    MISTRAL = "mistral"

class ModelType(str, Enum):
    """Model type definitions"""
    LLAMA = "Meta-Llama-3-2-90B-Vision-Instruct"
    COHERE_COMMAND = "cohere-command-r"
    COHERE_COMMAND_PLUS = "cohere-command-r-plus"
    CLAUDE = "claude-3-5-sonnet-20241022"
    PIXTRAL = "pixtral-large-latest"
    MISTRAL = "mistral-large-latest"

@dataclass
class ModelConfig:
    """Model configuration"""
    provider: ModelProvider
    model_id: str
    endpoint: str
    api_key: str
    rate_limit: int
    concurrent_limit: int
    token_limit: Optional[int] = None
    context_window: Optional[int] = None

class ModelConnectivityAgent(BaseAgent):
    """
    Model Connectivity Agent responsible for managing
    communication with online LLM models.
    """

    def __init__(self):
        super().__init__(AgentConfig(
            name="ModelConnectivity",
            description="Handles online LLM model connectivity",
            capabilities=[
                "model_communication",
                "rate_limiting",
                "error_handling",
                "request_optimization",
                "response_validation"
            ],
            required_tools=[
                "request_manager",
                "response_handler",
                "error_handler"
            ],
            max_concurrent_tasks=10,
            priority_level=1
        ))
        self.model_configs: Dict[str, ModelConfig] = {}
        self.rate_limiters: Dict[str, Semaphore] = {}
        self.request_history: Dict[str, List] = {}
        self.error_patterns: Dict[str, Dict] = {}

    async def initialize(self) -> bool:
        """Initialize the Model Connectivity Agent"""
        try:
            self.logger.info("Initializing Model Connectivity Agent...")
            
            # Initialize model configurations
            await self._initialize_model_configs()
            
            # Initialize rate limiters
            await self._initialize_rate_limiters()
            
            # Initialize error patterns
            await self._initialize_error_patterns()
            
            # Start monitoring tasks
            self._start_monitoring_tasks()
            
            self.logger.info("Model Connectivity Agent initialized successfully")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to initialize Model Connectivity Agent: {str(e)}")
            return False

    async def _initialize_model_configs(self) -> None:
        """Initialize model configurations"""
        try:
            # Azure/GitHub Models
            self.model_configs[ModelType.LLAMA] = ModelConfig(
                provider=ModelProvider.AZURE,
                model_id=ModelType.LLAMA,
                endpoint="https://models.inference.ai.azure.com/chat/completions",
                api_key=os.getenv("AZURE_API_KEY"),
                rate_limit=100,  # requests per minute
                concurrent_limit=10
            )
            
            self.model_configs[ModelType.COHERE_COMMAND] = ModelConfig(
                provider=ModelProvider.AZURE,
                model_id=ModelType.COHERE_COMMAND,
                endpoint="https://models.inference.ai.azure.com/chat/completions",
                api_key=os.getenv("AZURE_API_KEY"),
                rate_limit=100,
                concurrent_limit=10
            )
            
            # Anthropic Models
            self.model_configs[ModelType.CLAUDE] = ModelConfig(
                provider=ModelProvider.ANTHROPIC,
                model_id=ModelType.CLAUDE,
                endpoint="https://api.anthropic.com/v1/messages",
                api_key=os.getenv("ANTHROPIC_API_KEY"),
                rate_limit=50,
                concurrent_limit=5,
                context_window=200000
            )
            
            # Mistral Models
            self.model_configs[ModelType.PIXTRAL] = ModelConfig(
                provider=ModelProvider.MISTRAL,
                model_id=ModelType.PIXTRAL,
                endpoint="https://api.mistral.ai/v1/chat/completions",
                api_key=os.getenv("MISTRAL_API_KEY"),
                rate_limit=60,
                concurrent_limit=5
            )
            
            self.model_configs[ModelType.MISTRAL] = ModelConfig(
                provider=ModelProvider.MISTRAL,
                model_id=ModelType.MISTRAL,
                endpoint="https://api.mistral.ai/v1/chat/completions",
                api_key=os.getenv("MISTRAL_API_KEY"),
                rate_limit=60,
                concurrent_limit=5
            )
            
        except Exception as e:
            raise Exception(f"Failed to initialize model configs: {str(e)}")

    async def _initialize_rate_limiters(self) -> None:
        """Initialize rate limiters"""
        try:
            # Create rate limiters for each provider
            self.rate_limiters = {
                ModelProvider.AZURE: Semaphore(10),
                ModelProvider.ANTHROPIC: Semaphore(5),
                ModelProvider.MISTRAL: Semaphore(5)
            }
            
            # Initialize rate tracking
            self.rate_tracking = {
                provider: {
                    "requests": 0,
                    "last_reset": datetime.now(),
                    "window_size": 60  # seconds
                }
                for provider in ModelProvider
            }
            
        except Exception as e:
            raise Exception(f"Failed to initialize rate limiters: {str(e)}")

    async def _initialize_error_patterns(self) -> None:
        """Initialize error patterns"""
        try:
            self.error_patterns = {
                ModelProvider.AZURE: {
                    "unknown_model": "Invalid model ID",
                    "rate_limit": "Rate limit exceeded",
                    "token_limit": "Token limit exceeded"
                },
                ModelProvider.ANTHROPIC: {
                    "overloaded_error": "Service overloaded",
                    "rate_limit": "Rate limit exceeded",
                    "invalid_api_key": "Invalid API key"
                },
                ModelProvider.MISTRAL: {
                    "rate_limit": "Rate limit exceeded",
                    "invalid_request": "Invalid request format",
                    "token_limit": "Token limit exceeded"
                }
            }
            
        except Exception as e:
            raise Exception(f"Failed to initialize error patterns: {str(e)}")

    def _start_monitoring_tasks(self) -> None:
        """Start monitoring tasks"""
        asyncio.create_task(self._monitor_rate_limits())
        asyncio.create_task(self._monitor_errors())
        asyncio.create_task(self._cleanup_history())

    async def make_request(
        self,
        model_type: str,
        prompt: str,
        options: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """
        Make a request to an LLM model
        
        Args:
            model_type: Type of model to use
            prompt: Input prompt
            options: Optional request options
            
        Returns:
            Dictionary containing model response
        """
        try:
            # Get model configuration
            config = self.model_configs.get(model_type)
            if not config:
                return {
                    "success": False,
                    "error": f"Unknown model type: {model_type}"
                }
            
            # Check rate limits
            if not await self._check_rate_limit(config.provider):
                return {
                    "success": False,
                    "error": "Rate limit exceeded"
                }
            
            # Prepare request
            request_data = self._prepare_request(
                config,
                prompt,
                options or {}
            )
            
            # Make request with retries
            async with self.rate_limiters[config.provider]:
                response = await self._make_request_with_retries(
                    config,
                    request_data
                )
            
            # Validate response
            if not self._validate_response(response, config.provider):
                return {
                    "success": False,
                    "error": "Invalid response format"
                }
            
            # Update request history
            await self._update_request_history(
                config,
                prompt,
                response
            )
            
            return {
                "success": True,
                "response": response
            }
            
        except Exception as e:
            self.logger.error(f"Request failed: {str(e)}")
            return {
                "success": False,
                "error": str(e)
            }

    async def stream_response(
        self,
        model_type: str,
        prompt: str,
        options: Optional[Dict] = None
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """
        Stream response from an LLM model
        
        Args:
            model_type: Type of model to use
            prompt: Input prompt
            options: Optional streaming options
            
        Yields:
            Dictionary containing response chunks
        """
        try:
            # Get model configuration
            config = self.model_configs.get(model_type)
            if not config:
                yield {
                    "success": False,
                    "error": f"Unknown model type: {model_type}"
                }
                return
            
            # Prepare streaming request
            request_data = self._prepare_streaming_request(
                config,
                prompt,
                options or {}
            )
            
            # Make streaming request
            async with self.rate_limiters[config.provider]:
                async for chunk in self._stream_response_with_retries(
                    config,
                    request_data
                ):
                    yield {
                        "success": True,
                        "chunk": chunk
                    }
                    
        except Exception as e:
            self.logger.error(f"Streaming failed: {str(e)}")
            yield {
                "success": False,
                "error": str(e)
            }

    @backoff.on_exception(
        backoff.expo,
        (aiohttp.ClientError, TimeoutError),
        max_tries=3
    )
    async def _make_request_with_retries(
        self,
        config: ModelConfig,
        request_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Make request with retries"""
        async with aiohttp.ClientSession() as session:
            async with session.post(
                config.endpoint,
                headers=self._get_headers(config),
                json=request_data,
                timeout=30
            ) as response:
                if response.status != 200:
                    error = await response.text()
                    raise Exception(f"Request failed: {error}")
                return await response.json()

    async def _monitor_rate_limits(self) -> None:
        """Monitor rate limits"""
        while True:
            try:
                current_time = datetime.now()
                
                # Check each provider's rate tracking
                for provider, tracking in self.rate_tracking.items():
                    # Reset if window expired
                    if (current_time - tracking["last_reset"]).seconds >= tracking["window_size"]:
                        tracking["requests"] = 0
                        tracking["last_reset"] = current_time
                
                # Wait before next check
                await asyncio.sleep(1)  # Check every second
                
            except Exception as e:
                self.logger.error(f"Error in rate limit monitoring: {str(e)}")
                await asyncio.sleep(1)

    async def _monitor_errors(self) -> None:
        """Monitor errors"""
        while True:
            try:
                # Analyze error patterns
                for provider in ModelProvider:
                    provider_errors = [
                        error for error in self.request_history.get(provider, [])
                        if not error.get("success", False)
                    ]
                    
                    if provider_errors:
                        await self._analyze_error_patterns(
                            provider,
                            provider_errors
                        )
                
                # Wait before next analysis
                await asyncio.sleep(300)  # Analyze every 5 minutes
                
            except Exception as e:
                self.logger.error(f"Error in error monitoring: {str(e)}")
                await asyncio.sleep(300)

    async def _cleanup_history(self) -> None:
        """Clean up request history"""
        while True:
            try:
                current_time = datetime.now()
                
                # Keep last 24 hours of history
                for provider in self.request_history:
                    self.request_history[provider] = [
                        request for request in self.request_history[provider]
                        if (current_time - datetime.fromisoformat(request["timestamp"])).days < 1
                    ]
                
                # Wait before next cleanup
                await asyncio.sleep(3600)  # Clean up every hour
                
            except Exception as e:
                self.logger.error(f"Error in history cleanup: {str(e)}")
                await asyncio.sleep(3600)

# Global connectivity agent instance
connectivity_agent = ModelConnectivityAgent()
