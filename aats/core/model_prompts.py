"""
Model Prompt Manager for AATS
Handles prompt templates, optimization, and versioning for model interactions
"""

import asyncio
import logging
from typing import Any, Dict, List, Optional, Set, Union
from datetime import datetime
import json
import re
from pathlib import Path

from .model_manager import ModelType
from ..config.settings.agent_model_config import MODEL_CAPABILITIES
from ..integration.databases.utils import db_utils

class PromptTemplate:
    """Base class for prompt templates"""
    def __init__(
        self,
        template: str,
        variables: List[str],
        version: str = "1.0",
        model_type: Optional[ModelType] = None
    ):
        self.template = template
        self.variables = variables
        self.version = version
        self.model_type = model_type
        self._validate_template()

    def _validate_template(self) -> None:
        """Validate template format and variables"""
        # Check for required variables in template
        template_vars = set(re.findall(r'\{(\w+)\}', self.template))
        missing_vars = template_vars - set(self.variables)
        if missing_vars:
            raise ValueError(f"Template contains undefined variables: {missing_vars}")

    def format(self, **kwargs: Any) -> str:
        """Format template with provided variables"""
        missing_vars = set(self.variables) - set(kwargs.keys())
        if missing_vars:
            raise ValueError(f"Missing required variables: {missing_vars}")
        return self.template.format(**kwargs)

class PromptManager:
    """
    Prompt Manager responsible for handling prompt templates,
    optimization, and versioning.
    """

    def __init__(self):
        self.logger = logging.getLogger("PromptManager")
        self.templates: Dict[str, Dict[str, PromptTemplate]] = {}
        self.template_versions: Dict[str, List[str]] = {}
        self.optimization_history: List[Dict] = []
        self.usage_stats: Dict[str, Dict] = {}

    async def initialize(self) -> bool:
        """Initialize the Prompt Manager"""
        try:
            self.logger.info("Initializing Prompt Manager...")
            
            # Initialize template storage
            await self._initialize_templates()
            
            # Initialize optimization system
            await self._initialize_optimization()
            
            # Initialize usage tracking
            await self._initialize_usage_tracking()
            
            self.logger.info("Prompt Manager initialized successfully")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to initialize Prompt Manager: {str(e)}")
            return False

    async def _initialize_templates(self) -> None:
        """Initialize prompt templates"""
        try:
            # Initialize base templates
            self.templates = {
                # Strategic agent templates
                "project_manager": {
                    "task_planning": PromptTemplate(
                        template=(
                            "As a Project Manager, analyze the following task:\n"
                            "{task_description}\n\n"
                            "Consider these constraints:\n"
                            "{constraints}\n\n"
                            "Generate a detailed plan including:\n"
                            "1. Task breakdown\n"
                            "2. Resource allocation\n"
                            "3. Timeline estimates\n"
                            "4. Risk assessment"
                        ),
                        variables=["task_description", "constraints"],
                        model_type=ModelType.CLAUDE_35_SONNET
                    ),
                    "resource_allocation": PromptTemplate(
                        template=(
                            "Optimize resource allocation for:\n"
                            "Task: {task_name}\n"
                            "Available resources: {resources}\n"
                            "Constraints: {constraints}\n"
                            "Priority: {priority}\n\n"
                            "Provide allocation strategy considering:\n"
                            "1. Resource capabilities\n"
                            "2. Task requirements\n"
                            "3. Efficiency optimization\n"
                            "4. Risk mitigation"
                        ),
                        variables=["task_name", "resources", "constraints", "priority"],
                        model_type=ModelType.GROK_BETA
                    )
                },
                
                # Security templates
                "security_officer": {
                    "threat_analysis": PromptTemplate(
                        template=(
                            "Perform security analysis for:\n"
                            "System: {system_name}\n"
                            "Context: {context}\n"
                            "Current state: {current_state}\n\n"
                            "Analyze potential threats considering:\n"
                            "1. Vulnerability assessment\n"
                            "2. Attack vectors\n"
                            "3. Risk levels\n"
                            "4. Mitigation strategies"
                        ),
                        variables=["system_name", "context", "current_state"],
                        model_type=ModelType.CLAUDE_35_SONNET
                    ),
                    "policy_enforcement": PromptTemplate(
                        template=(
                            "Evaluate policy compliance for:\n"
                            "Policy: {policy_name}\n"
                            "Target: {target}\n"
                            "Current state: {current_state}\n\n"
                            "Provide assessment including:\n"
                            "1. Compliance status\n"
                            "2. Violations found\n"
                            "3. Required actions\n"
                            "4. Enforcement recommendations"
                        ),
                        variables=["policy_name", "target", "current_state"],
                        model_type=ModelType.PHI_35_MOE
                    )
                },
                
                # Data architecture templates
                "data_architect": {
                    "schema_design": PromptTemplate(
                        template=(
                            "Design data schema for:\n"
                            "System: {system_name}\n"
                            "Requirements: {requirements}\n"
                            "Constraints: {constraints}\n\n"
                            "Provide schema design including:\n"
                            "1. Entity relationships\n"
                            "2. Data types\n"
                            "3. Indexing strategy\n"
                            "4. Performance considerations"
                        ),
                        variables=["system_name", "requirements", "constraints"],
                        model_type=ModelType.LLAMA_32_90B
                    ),
                    "data_modeling": PromptTemplate(
                        template=(
                            "Create data model for:\n"
                            "Domain: {domain}\n"
                            "Requirements: {requirements}\n"
                            "Constraints: {constraints}\n\n"
                            "Provide model including:\n"
                            "1. Entity definitions\n"
                            "2. Relationships\n"
                            "3. Constraints\n"
                            "4. Optimization strategies"
                        ),
                        variables=["domain", "requirements", "constraints"],
                        model_type=ModelType.COHERE_COMMAND
                    )
                },
                
                # Quality assurance templates
                "quality_assurance": {
                    "test_planning": PromptTemplate(
                        template=(
                            "Design test strategy for:\n"
                            "Component: {component_name}\n"
                            "Requirements: {requirements}\n"
                            "Constraints: {constraints}\n\n"
                            "Provide test plan including:\n"
                            "1. Test scenarios\n"
                            "2. Coverage requirements\n"
                            "3. Test priorities\n"
                            "4. Resource needs"
                        ),
                        variables=["component_name", "requirements", "constraints"],
                        model_type=ModelType.COHERE_COMMAND
                    ),
                    "quality_analysis": PromptTemplate(
                        template=(
                            "Analyze quality metrics for:\n"
                            "Component: {component_name}\n"
                            "Metrics: {metrics}\n"
                            "Thresholds: {thresholds}\n\n"
                            "Provide analysis including:\n"
                            "1. Quality assessment\n"
                            "2. Issue identification\n"
                            "3. Improvement recommendations\n"
                            "4. Priority actions"
                        ),
                        variables=["component_name", "metrics", "thresholds"],
                        model_type=ModelType.MISTRAL_LARGE
                    )
                }
            }
            
            # Load custom templates
            custom_templates = await self._load_custom_templates()
            self._merge_templates(custom_templates)
            
            # Initialize version tracking
            for category, templates in self.templates.items():
                self.template_versions[category] = []
                for template_name, template in templates.items():
                    self.template_versions[category].append({
                        "name": template_name,
                        "version": template.version,
                        "timestamp": datetime.now().isoformat()
                    })
                    
        except Exception as e:
            raise Exception(f"Failed to initialize templates: {str(e)}")

    async def _initialize_optimization(self) -> None:
        """Initialize optimization system"""
        try:
            # Set up optimization parameters
            self.optimization_config = {
                "min_samples": 100,  # Minimum samples before optimization
                "success_threshold": 0.8,  # Success rate threshold
                "improvement_threshold": 0.05,  # Minimum improvement required
                "max_variations": 3,  # Maximum template variations to test
                "test_window": 3600  # Testing window in seconds
            }
            
            # Initialize optimization history
            self.optimization_history = []
            
        except Exception as e:
            raise Exception(f"Failed to initialize optimization: {str(e)}")

    async def _initialize_usage_tracking(self) -> None:
        """Initialize usage tracking system"""
        try:
            # Initialize usage statistics
            for category in self.templates:
                self.usage_stats[category] = {}
                for template_name in self.templates[category]:
                    self.usage_stats[category][template_name] = {
                        "total_uses": 0,
                        "successful_uses": 0,
                        "average_tokens": 0,
                        "average_latency": 0,
                        "error_rate": 0
                    }
            
            # Load historical stats
            stored_stats = await db_utils.get_agent_state(
                "prompt_manager",
                "usage_stats"
            )
            
            if stored_stats:
                self._merge_stats(stored_stats)
                
        except Exception as e:
            raise Exception(f"Failed to initialize usage tracking: {str(e)}")

    async def get_prompt(
        self,
        category: str,
        template_name: str,
        variables: Dict[str, Any]
    ) -> str:
        """
        Get formatted prompt from template
        
        Args:
            category: Template category
            template_name: Name of the template
            variables: Variables for template formatting
            
        Returns:
            Formatted prompt string
        """
        try:
            if category not in self.templates:
                raise ValueError(f"Unknown template category: {category}")
                
            category_templates = self.templates[category]
            if template_name not in category_templates:
                raise ValueError(f"Unknown template: {template_name}")
                
            template = category_templates[template_name]
            prompt = template.format(**variables)
            
            # Update usage statistics
            await self._update_usage_stats(category, template_name)
            
            return prompt
            
        except Exception as e:
            self.logger.error(f"Failed to get prompt: {str(e)}")
            raise

    async def optimize_template(
        self,
        category: str,
        template_name: str
    ) -> Optional[PromptTemplate]:
        """
        Optimize template based on usage statistics
        
        Args:
            category: Template category
            template_name: Name of the template
            
        Returns:
            Optional optimized template
        """
        try:
            stats = self.usage_stats[category][template_name]
            
            # Check if optimization is needed
            if stats["total_uses"] < self.optimization_config["min_samples"]:
                return None
                
            if stats["error_rate"] < (1 - self.optimization_config["success_threshold"]):
                return None
            
            # Generate template variations
            variations = await self._generate_variations(
                category,
                template_name
            )
            
            # Test variations
            results = await self._test_variations(variations)
            
            # Select best variation
            best_variation = await self._select_best_variation(results)
            
            if best_variation:
                # Update template
                await self._update_template(
                    category,
                    template_name,
                    best_variation
                )
                
                return best_variation
            
            return None
            
        except Exception as e:
            self.logger.error(f"Failed to optimize template: {str(e)}")
            return None

    async def record_usage(
        self,
        category: str,
        template_name: str,
        metrics: Dict[str, Any]
    ) -> None:
        """
        Record template usage metrics
        
        Args:
            category: Template category
            template_name: Name of the template
            metrics: Usage metrics
        """
        try:
            stats = self.usage_stats[category][template_name]
            
            # Update statistics
            stats["total_uses"] += 1
            if metrics.get("success", False):
                stats["successful_uses"] += 1
            
            # Update averages
            current_count = stats["total_uses"]
            stats["average_tokens"] = (
                (stats["average_tokens"] * (current_count - 1) +
                 metrics.get("tokens", 0)) / current_count
            )
            
            stats["average_latency"] = (
                (stats["average_latency"] * (current_count - 1) +
                 metrics.get("latency", 0)) / current_count
            )
            
            stats["error_rate"] = (
                (stats["total_uses"] - stats["successful_uses"]) /
                stats["total_uses"]
            )
            
            # Store metrics
            await self._store_usage_metrics(
                category,
                template_name,
                metrics
            )
            
        except Exception as e:
            self.logger.error(f"Failed to record usage: {str(e)}")

    async def _load_custom_templates(self) -> Dict[str, Dict[str, PromptTemplate]]:
        """Load custom templates from storage"""
        try:
            stored_templates = await db_utils.get_agent_state(
                "prompt_manager",
                "custom_templates"
            )
            
            if not stored_templates:
                return {}
            
            custom_templates = {}
            for category, templates in stored_templates.items():
                custom_templates[category] = {}
                for name, template_data in templates.items():
                    custom_templates[category][name] = PromptTemplate(
                        template=template_data["template"],
                        variables=template_data["variables"],
                        version=template_data["version"],
                        model_type=template_data.get("model_type")
                    )
            
            return custom_templates
            
        except Exception as e:
            self.logger.error(f"Failed to load custom templates: {str(e)}")
            return {}

    def _merge_templates(
        self,
        new_templates: Dict[str, Dict[str, PromptTemplate]]
    ) -> None:
        """Merge new templates with existing ones"""
        for category, templates in new_templates.items():
            if category not in self.templates:
                self.templates[category] = {}
            self.templates[category].update(templates)

    async def _store_usage_metrics(
        self,
        category: str,
        template_name: str,
        metrics: Dict[str, Any]
    ) -> None:
        """Store template usage metrics"""
        try:
            await db_utils.record_metric(
                agent_id="prompt_manager",
                metric_type="template_usage",
                value=metrics.get("latency", 0),
                tags={
                    "category": category,
                    "template": template_name,
                    "success": metrics.get("success", False),
                    "tokens": metrics.get("tokens", 0)
                }
            )
            
        except Exception as e:
            self.logger.error(f"Failed to store usage metrics: {str(e)}")

# Global prompt manager instance
prompt_manager = PromptManager()
