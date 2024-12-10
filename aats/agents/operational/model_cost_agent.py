"""
Model Cost Agent Implementation
This agent handles cost tracking, budgeting, and optimization
"""

import asyncio
import logging
from typing import Any, Dict, List, Optional, Set, Union, Callable
from datetime import datetime, timedelta
import json
import pandas as pd
import numpy as np
from dataclasses import dataclass
from enum import Enum
from decimal import Decimal

from ..base_agent import BaseAgent, AgentConfig
from ...config.settings.base_config import config
from ...integration.databases.utils import db_utils
from .model_connectivity_agent import ModelType, ModelProvider

class CostMetric(str, Enum):
    """Cost metric definitions"""
    TOKEN_COST = "token_cost"
    REQUEST_COST = "request_cost"
    STORAGE_COST = "storage_cost"
    BANDWIDTH_COST = "bandwidth_cost"
    TOTAL_COST = "total_cost"

class BudgetPeriod(str, Enum):
    """Budget period definitions"""
    HOURLY = "hourly"
    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"
    QUARTERLY = "quarterly"
    YEARLY = "yearly"

@dataclass
class CostConfig:
    """Cost configuration"""
    model_type: str
    token_rate: Decimal
    request_rate: Decimal
    storage_rate: Optional[Decimal] = None
    bandwidth_rate: Optional[Decimal] = None
    minimum_charge: Optional[Decimal] = None
    volume_discounts: Optional[Dict[int, Decimal]] = None

class ModelCostAgent(BaseAgent):
    """
    Model Cost Agent responsible for managing model
    usage costs and budgets.
    """

    def __init__(self):
        super().__init__(AgentConfig(
            name="ModelCost",
            description="Handles model cost management",
            capabilities=[
                "cost_tracking",
                "budget_management",
                "cost_optimization",
                "usage_analysis",
                "reporting"
            ],
            required_tools=[
                "cost_tracker",
                "budget_manager",
                "cost_optimizer"
            ],
            max_concurrent_tasks=5,
            priority_level=2
        ))
        self.cost_configs: Dict[str, CostConfig] = {}
        self.budgets: Dict[str, Dict[str, Decimal]] = {}
        self.cost_history: Dict[str, List] = {}
        self.usage_metrics: Dict[str, Dict] = {}

    async def initialize(self) -> bool:
        """Initialize the Model Cost Agent"""
        try:
            self.logger.info("Initializing Model Cost Agent...")
            
            # Initialize cost configurations
            await self._initialize_cost_configs()
            
            # Initialize budgets
            await self._initialize_budgets()
            
            # Initialize usage tracking
            await self._initialize_usage_tracking()
            
            # Start monitoring tasks
            self._start_monitoring_tasks()
            
            self.logger.info("Model Cost Agent initialized successfully")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to initialize Model Cost Agent: {str(e)}")
            return False

    async def _initialize_cost_configs(self) -> None:
        """Initialize cost configurations"""
        try:
            # Define cost configurations for each model
            self.cost_configs = {
                ModelType.LLAMA: CostConfig(
                    model_type=ModelType.LLAMA,
                    token_rate=Decimal("0.0001"),  # per token
                    request_rate=Decimal("0.01"),   # per request
                    volume_discounts={
                        1000000: Decimal("0.00008"),  # >1M tokens
                        5000000: Decimal("0.00006"),  # >5M tokens
                        10000000: Decimal("0.00004")  # >10M tokens
                    }
                ),
                ModelType.CLAUDE: CostConfig(
                    model_type=ModelType.CLAUDE,
                    token_rate=Decimal("0.0002"),
                    request_rate=Decimal("0.02"),
                    minimum_charge=Decimal("0.01"),
                    volume_discounts={
                        1000000: Decimal("0.00015"),
                        5000000: Decimal("0.0001")
                    }
                ),
                ModelType.MISTRAL: CostConfig(
                    model_type=ModelType.MISTRAL,
                    token_rate=Decimal("0.00012"),
                    request_rate=Decimal("0.015"),
                    volume_discounts={
                        1000000: Decimal("0.0001"),
                        5000000: Decimal("0.00008")
                    }
                )
            }
            
            # Load custom configurations
            custom_configs = await db_utils.get_agent_state(
                self.id,
                "cost_configs"
            )
            
            if custom_configs:
                self._merge_cost_configs(custom_configs)
                
        except Exception as e:
            raise Exception(f"Failed to initialize cost configs: {str(e)}")

    async def _initialize_budgets(self) -> None:
        """Initialize budgets"""
        try:
            # Initialize budget periods
            self.budgets = {
                period: {
                    model_type: Decimal("0")
                    for model_type in ModelType
                }
                for period in BudgetPeriod
            }
            
            # Set default budgets
            self.budgets[BudgetPeriod.MONTHLY] = {
                ModelType.LLAMA: Decimal("1000.00"),
                ModelType.CLAUDE: Decimal("2000.00"),
                ModelType.MISTRAL: Decimal("1500.00")
            }
            
            # Calculate derived budgets
            await self._calculate_derived_budgets()
            
            # Load stored budgets
            stored_budgets = await db_utils.get_agent_state(
                self.id,
                "budgets"
            )
            
            if stored_budgets:
                self._merge_budgets(stored_budgets)
                
        except Exception as e:
            raise Exception(f"Failed to initialize budgets: {str(e)}")

    async def _initialize_usage_tracking(self) -> None:
        """Initialize usage tracking"""
        try:
            # Initialize usage metrics
            self.usage_metrics = {
                model_type: {
                    "tokens": {
                        "input": 0,
                        "output": 0,
                        "total": 0
                    },
                    "requests": {
                        "successful": 0,
                        "failed": 0,
                        "total": 0
                    },
                    "costs": {
                        metric: Decimal("0")
                        for metric in CostMetric
                    }
                }
                for model_type in ModelType
            }
            
            # Initialize tracking periods
            self.tracking_periods = {
                BudgetPeriod.HOURLY: [],
                BudgetPeriod.DAILY: [],
                BudgetPeriod.WEEKLY: [],
                BudgetPeriod.MONTHLY: []
            }
            
        except Exception as e:
            raise Exception(f"Failed to initialize usage tracking: {str(e)}")

    def _start_monitoring_tasks(self) -> None:
        """Start monitoring tasks"""
        asyncio.create_task(self._monitor_costs())
        asyncio.create_task(self._monitor_budgets())
        asyncio.create_task(self._optimize_costs())

    async def track_cost(
        self,
        model_type: str,
        usage_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Track model usage cost
        
        Args:
            model_type: Type of model
            usage_data: Usage data including tokens and requests
            
        Returns:
            Dictionary containing cost tracking results
        """
        try:
            # Get cost configuration
            config = self.cost_configs.get(model_type)
            if not config:
                return {
                    "success": False,
                    "error": f"Unknown model type: {model_type}"
                }
            
            # Calculate costs
            token_cost = self._calculate_token_cost(
                config,
                usage_data.get("tokens", {})
            )
            
            request_cost = self._calculate_request_cost(
                config,
                usage_data.get("requests", {})
            )
            
            total_cost = token_cost + request_cost
            
            # Apply volume discounts
            total_cost = self._apply_volume_discounts(
                config,
                total_cost,
                usage_data
            )
            
            # Update usage metrics
            self._update_usage_metrics(
                model_type,
                usage_data,
                {
                    CostMetric.TOKEN_COST: token_cost,
                    CostMetric.REQUEST_COST: request_cost,
                    CostMetric.TOTAL_COST: total_cost
                }
            )
            
            # Check budget
            if not await self._check_budget(model_type, total_cost):
                return {
                    "success": False,
                    "error": "Budget exceeded",
                    "costs": {
                        "token_cost": str(token_cost),
                        "request_cost": str(request_cost),
                        "total_cost": str(total_cost)
                    }
                }
            
            # Store cost record
            await self._store_cost_record(
                model_type,
                usage_data,
                total_cost
            )
            
            return {
                "success": True,
                "costs": {
                    "token_cost": str(token_cost),
                    "request_cost": str(request_cost),
                    "total_cost": str(total_cost)
                }
            }
            
        except Exception as e:
            self.logger.error(f"Cost tracking failed: {str(e)}")
            return {
                "success": False,
                "error": str(e)
            }

    async def get_cost_analysis(
        self,
        model_type: str,
        period: str,
        metrics: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Get cost analysis for a model
        
        Args:
            model_type: Type of model
            period: Analysis period
            metrics: Optional list of metrics to analyze
            
        Returns:
            Dictionary containing cost analysis
        """
        try:
            # Get usage data for period
            usage_data = await self._get_period_usage(
                model_type,
                period
            )
            
            if not usage_data:
                return {
                    "success": False,
                    "error": "No usage data found for period"
                }
            
            # Calculate metrics
            metrics_to_analyze = metrics or list(CostMetric)
            analysis = {}
            
            for metric in metrics_to_analyze:
                analysis[metric] = await self._analyze_cost_metric(
                    model_type,
                    metric,
                    usage_data
                )
            
            # Generate insights
            insights = await self._generate_cost_insights(
                model_type,
                analysis
            )
            
            return {
                "success": True,
                "period": period,
                "analysis": analysis,
                "insights": insights
            }
            
        except Exception as e:
            self.logger.error(f"Cost analysis failed: {str(e)}")
            return {
                "success": False,
                "error": str(e)
            }

    async def optimize_costs(
        self,
        model_type: str,
        target_reduction: Optional[float] = None,
        options: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """
        Optimize model usage costs
        
        Args:
            model_type: Type of model
            target_reduction: Optional target cost reduction percentage
            options: Optional optimization options
            
        Returns:
            Dictionary containing optimization results
        """
        try:
            # Get current costs
            current_costs = await self._get_current_costs(model_type)
            
            # Generate optimization strategies
            strategies = await self._generate_optimization_strategies(
                model_type,
                current_costs,
                target_reduction,
                options or {}
            )
            
            # Evaluate strategies
            evaluations = await self._evaluate_optimization_strategies(
                strategies,
                current_costs
            )
            
            # Select best strategy
            best_strategy = await self._select_optimization_strategy(
                evaluations
            )
            
            # Generate implementation plan
            implementation_plan = await self._generate_implementation_plan(
                best_strategy
            )
            
            return {
                "success": True,
                "current_costs": current_costs,
                "selected_strategy": best_strategy,
                "implementation_plan": implementation_plan,
                "projected_savings": str(best_strategy["projected_savings"])
            }
            
        except Exception as e:
            self.logger.error(f"Cost optimization failed: {str(e)}")
            return {
                "success": False,
                "error": str(e)
            }

    async def _monitor_costs(self) -> None:
        """Monitor costs continuously"""
        while True:
            try:
                current_time = datetime.now()
                
                # Check each model's costs
                for model_type in ModelType:
                    # Get recent costs
                    recent_costs = await self._get_recent_costs(
                        model_type,
                        minutes=60
                    )
                    
                    if recent_costs:
                        # Check for cost anomalies
                        anomalies = self._detect_cost_anomalies(
                            recent_costs
                        )
                        
                        if anomalies:
                            await self._handle_cost_anomalies(
                                model_type,
                                anomalies
                            )
                
                # Wait before next check
                await asyncio.sleep(300)  # Check every 5 minutes
                
            except Exception as e:
                self.logger.error(f"Error in cost monitoring: {str(e)}")
                await asyncio.sleep(300)

    async def _monitor_budgets(self) -> None:
        """Monitor budgets"""
        while True:
            try:
                # Check each period's budget
                for period in BudgetPeriod:
                    for model_type in ModelType:
                        # Get period usage
                        usage = await self._get_period_usage(
                            model_type,
                            period
                        )
                        
                        # Check against budget
                        budget = self.budgets[period][model_type]
                        if usage > budget * Decimal("0.8"):  # 80% threshold
                            await self._handle_budget_warning(
                                model_type,
                                period,
                                usage,
                                budget
                            )
                
                # Wait before next check
                await asyncio.sleep(3600)  # Check every hour
                
            except Exception as e:
                self.logger.error(f"Error in budget monitoring: {str(e)}")
                await asyncio.sleep(3600)

    async def _optimize_costs(self) -> None:
        """Optimize costs periodically"""
        while True:
            try:
                # Check each model's optimization needs
                for model_type in ModelType:
                    if await self._needs_cost_optimization(model_type):
                        # Perform optimization
                        await self.optimize_costs(
                            model_type,
                            target_reduction=0.1  # 10% target reduction
                        )
                
                # Wait before next optimization
                await asyncio.sleep(86400)  # Optimize daily
                
            except Exception as e:
                self.logger.error(f"Error in cost optimization: {str(e)}")
                await asyncio.sleep(86400)

# Global cost agent instance
cost_agent = ModelCostAgent()
