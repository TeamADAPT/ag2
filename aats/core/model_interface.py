"""
Model Interface for AATS
Provides standardized interface for agents to interact with LLM models
"""

import asyncio
import logging
from typing import Any, Dict, List, Optional, Union
from datetime import datetime
import json
import aiohttp
import backoff

from .model_manager import model_manager, ModelType
from ..config.settings.agent_model_config import MODEL_CAPABILITIES
from ..integration.databases.utils import db_utils

class ModelRequestError(Exception):
    """Exception raised for model request errors"""
    pass

class ModelResponseError(Exception):
    """Exception raised for model response errors"""
    pass

class ModelInterface:
    """
    Model Interface responsible for handling interactions
    between agents and LLM models.
    """

    def __init__(self, agent_name: str, agent_tier: str):
        self.logger = logging.getLogger(f"ModelInterface_{agent_name}")
        self.agent_name = agent_name
        self.agent_tier = agent_tier
        self.primary_model: Optional[ModelType] = None
        self.secondary_model: Optional[ModelType] = None
        self.request_history: List[Dict] = []
        self.performance_metrics: Dict[str, Any] = {
            "total_requests": 0,
            "total_tokens": 0,
            "average_latency": 0,
            "error_count": 0
        }

    async def initialize(self) -> bool:
        """Initialize the Model Interface"""
        try:
            self.logger.info(f"Initializing Model Interface for {self.agent_name}...")
            
            # Get assigned models
            models = await model_manager.get_model_for_agent(
                self.agent_name,
                self.agent_tier
            )
            self.primary_model, self.secondary_model = models
            
            # Load models
            await model_manager.load_model(self.primary_model, self.agent_name)
            await model_manager.load_model(self.secondary_model, self.agent_name)
            
            self.logger.info("Model Interface initialized successfully")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to initialize Model Interface: {str(e)}")
            return False

    @backoff.on_exception(
        backoff.expo,
        (ModelRequestError, aiohttp.ClientError),
        max_tries=3
    )
    async def generate_response(
        self,
        prompt: str,
        task_type: Optional[str] = None,
        parameters: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """
        Generate response from model
        
        Args:
            prompt: Input prompt for the model
            task_type: Optional task type for model selection
            parameters: Optional model parameters
            
        Returns:
            Dictionary containing model response
        """
        try:
            start_time = datetime.now()
            
            # Select appropriate model
            model = await self._select_model(task_type)
            
            # Prepare request
            request = await self._prepare_request(
                model,
                prompt,
                parameters
            )
            
            # Send request to model
            response = await self._send_request(
                model,
                request
            )
            
            # Process response
            processed_response = await self._process_response(
                model,
                response
            )
            
            # Update metrics
            duration = (datetime.now() - start_time).total_seconds()
            await self._update_metrics(model, request, response, duration)
            
            return processed_response
            
        except Exception as e:
            self.logger.error(f"Failed to generate response: {str(e)}")
            await self._handle_error(e, prompt, task_type)
            raise ModelResponseError(str(e))

    async def switch_model(
        self,
        task_type: Optional[str] = None,
        force_secondary: bool = False
    ) -> bool:
        """
        Switch between primary and secondary models
        
        Args:
            task_type: Optional task type for model selection
            force_secondary: Force switch to secondary model
            
        Returns:
            bool: True if switch was successful
        """
        try:
            if force_secondary:
                from_model = self.primary_model
                to_model = self.secondary_model
            else:
                # Get optimal model for task
                to_model = await self._get_optimal_model(task_type)
                from_model = (
                    self.primary_model
                    if to_model != self.primary_model
                    else self.secondary_model
                )
            
            # Perform switch
            success = await model_manager.switch_model(
                self.agent_name,
                from_model,
                to_model
            )
            
            if success:
                self.primary_model = to_model
                self.secondary_model = from_model
            
            return success
            
        except Exception as e:
            self.logger.error(f"Failed to switch models: {str(e)}")
            return False

    async def get_performance_metrics(self) -> Dict[str, Any]:
        """Get interface performance metrics"""
        try:
            metrics = self.performance_metrics.copy()
            
            # Add model-specific metrics
            for model in [self.primary_model, self.secondary_model]:
                if model:
                    model_stats = await model_manager.get_model_stats(model)
                    metrics[f"{model}_stats"] = model_stats
            
            return metrics
            
        except Exception as e:
            self.logger.error(f"Failed to get metrics: {str(e)}")
            return {}

    async def _select_model(
        self,
        task_type: Optional[str]
    ) -> ModelType:
        """Select appropriate model for task"""
        try:
            if task_type:
                # Get optimal model for task type
                model = await self._get_optimal_model(task_type)
            else:
                # Use primary model by default
                model = self.primary_model
            
            return model
            
        except Exception as e:
            raise Exception(f"Model selection failed: {str(e)}")

    async def _prepare_request(
        self,
        model: ModelType,
        prompt: str,
        parameters: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """Prepare model request"""
        try:
            # Get model capabilities
            capabilities = MODEL_CAPABILITIES[model]
            
            # Prepare base request
            request = {
                "prompt": prompt,
                "max_tokens": min(
                    parameters.get("max_tokens", 1000),
                    capabilities["context_window"]
                ),
                "temperature": parameters.get("temperature", 0.7),
                "top_p": parameters.get("top_p", 1.0),
                "frequency_penalty": parameters.get("frequency_penalty", 0.0),
                "presence_penalty": parameters.get("presence_penalty", 0.0)
            }
            
            # Add model-specific parameters
            request.update(self._get_model_specific_params(model, parameters))
            
            return request
            
        except Exception as e:
            raise Exception(f"Request preparation failed: {str(e)}")

    async def _send_request(
        self,
        model: ModelType,
        request: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Send request to model"""
        try:
            # Get model endpoint
            endpoint = self._get_model_endpoint(model)
            
            # Send request
            async with aiohttp.ClientSession() as session:
                async with session.post(endpoint, json=request) as response:
                    if response.status != 200:
                        raise ModelRequestError(
                            f"Model request failed: {response.status}"
                        )
                    
                    return await response.json()
                    
        except Exception as e:
            raise Exception(f"Request sending failed: {str(e)}")

    async def _process_response(
        self,
        model: ModelType,
        response: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Process model response"""
        try:
            # Extract relevant information
            processed = {
                "content": response.get("choices", [{}])[0].get("text", ""),
                "model": model,
                "usage": response.get("usage", {}),
                "timestamp": datetime.now().isoformat()
            }
            
            # Add to request history
            self.request_history.append({
                "model": model,
                "response": processed,
                "timestamp": processed["timestamp"]
            })
            
            return processed
            
        except Exception as e:
            raise Exception(f"Response processing failed: {str(e)}")

    async def _update_metrics(
        self,
        model: ModelType,
        request: Dict[str, Any],
        response: Dict[str, Any],
        duration: float
    ) -> None:
        """Update performance metrics"""
        try:
            # Update interface metrics
            self.performance_metrics["total_requests"] += 1
            self.performance_metrics["total_tokens"] += response.get(
                "usage", {}
            ).get("total_tokens", 0)
            
            # Update average latency
            current_avg = self.performance_metrics["average_latency"]
            current_count = self.performance_metrics["total_requests"]
            self.performance_metrics["average_latency"] = (
                (current_avg * (current_count - 1) + duration) / current_count
            )
            
            # Store metrics
            await db_utils.record_metric(
                agent_id=self.agent_name,
                metric_type="model_performance",
                value=duration,
                tags={
                    "model": model,
                    "task_type": request.get("task_type")
                }
            )
            
        except Exception as e:
            self.logger.error(f"Failed to update metrics: {str(e)}")

    async def _handle_error(
        self,
        error: Exception,
        prompt: str,
        task_type: Optional[str]
    ) -> None:
        """Handle model errors"""
        try:
            # Update error count
            self.performance_metrics["error_count"] += 1
            
            # Log error
            error_details = {
                "error_type": type(error).__name__,
                "error_message": str(error),
                "prompt": prompt,
                "task_type": task_type,
                "timestamp": datetime.now().isoformat()
            }
            
            await db_utils.record_event(
                event_type="model_error",
                data=error_details
            )
            
            # Try switching models if appropriate
            if isinstance(error, ModelRequestError):
                await self.switch_model(
                    task_type=task_type,
                    force_secondary=True
                )
                
        except Exception as e:
            self.logger.error(f"Error handling failed: {str(e)}")

    def _get_model_specific_params(
        self,
        model: ModelType,
        parameters: Optional[Dict]
    ) -> Dict[str, Any]:
        """Get model-specific parameters"""
        params = {}
        
        if model == ModelType.CLAUDE_35_SONNET:
            params.update({
                "stop_sequences": parameters.get("stop_sequences", []),
                "stream": parameters.get("stream", False)
            })
        elif model == ModelType.COHERE_COMMAND:
            params.update({
                "truncate": parameters.get("truncate", "END"),
                "return_likelihoods": parameters.get("return_likelihoods", "NONE")
            })
        
        return params

    def _get_model_endpoint(self, model: ModelType) -> str:
        """Get model API endpoint"""
        # Add actual endpoint configuration
        endpoints = {
            ModelType.CLAUDE_35_SONNET: "https://api.anthropic.com/v1/complete",
            ModelType.COHERE_COMMAND: "https://api.cohere.ai/v1/generate",
            # Add other model endpoints
        }
        
        return endpoints.get(model, "")

# Model interface factory
def create_model_interface(
    agent_name: str,
    agent_tier: str
) -> ModelInterface:
    """Create model interface for an agent"""
    return ModelInterface(agent_name, agent_tier)
