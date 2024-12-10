"""
Model Cost Manager for AATS
Handles cost tracking, budgeting, and optimization for model usage
"""

import asyncio
import logging
from typing import Any, Dict, List, Optional, Set, Union
from datetime import datetime, timedelta
import json
from decimal import Decimal

from .model_manager import ModelType
from ..config.settings.agent_model_config import MODEL_CAPABILITIES
from ..integration.databases.utils import db_utils

class CostThresholds:
    """Cost threshold definitions"""
    WARNING = 0.8  # 80% of budget
    CRITICAL = 0.95  # 95% of budget
    EMERGENCY = 0.99  # 99% of budget

class BudgetPeriod(str):
    """Budget period definitions"""
    HOURLY = "hourly"
    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"

class ModelCostManager:
    """
    Model Cost Manager responsible for tracking and optimizing
    model usage costs across the system.
    """

    def __init__(self):
        self.logger = logging.getLogger("ModelCostManager")
        self.cost_tracking: Dict[str, Dict] = {}
        self.budgets: Dict[str, Dict] = {}
        self.cost_history: List[Dict] = []
        self.optimization_rules: Dict[str, Any] = {}

    async def initialize(self) -> bool:
        """Initialize the Model Cost Manager"""
        try:
            self.logger.info("Initializing Model Cost Manager...")
            
            # Initialize cost tracking
            await self._initialize_cost_tracking()
            
            # Initialize budgets
            await self._initialize_budgets()
            
            # Initialize optimization rules
            await self._initialize_optimization_rules()
            
            # Start monitoring tasks
            self._start_monitoring_tasks()
            
            self.logger.info("Model Cost Manager initialized successfully")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to initialize Model Cost Manager: {str(e)}")
            return False

    async def _initialize_cost_tracking(self) -> None:
        """Initialize cost tracking system"""
        try:
            # Initialize cost tracking for each model
            for model_type in ModelType:
                self.cost_tracking[model_type] = {
                    "total_cost": Decimal("0.0"),
                    "token_count": 0,
                    "request_count": 0,
                    "average_cost_per_request": Decimal("0.0"),
                    "cost_history": [],
                    "last_updated": None
                }
            
            # Load historical costs
            stored_costs = await db_utils.get_agent_state(
                "cost_manager",
                "cost_tracking"
            )
            
            if stored_costs:
                self._merge_costs(stored_costs)
                
        except Exception as e:
            raise Exception(f"Failed to initialize cost tracking: {str(e)}")

    async def _initialize_budgets(self) -> None:
        """Initialize budget management"""
        try:
            # Set up default budgets
            self.budgets = {
                BudgetPeriod.HOURLY: {
                    "limit": Decimal("10.0"),
                    "used": Decimal("0.0"),
                    "remaining": Decimal("10.0"),
                    "reset_time": None
                },
                BudgetPeriod.DAILY: {
                    "limit": Decimal("200.0"),
                    "used": Decimal("0.0"),
                    "remaining": Decimal("200.0"),
                    "reset_time": None
                },
                BudgetPeriod.WEEKLY: {
                    "limit": Decimal("1000.0"),
                    "used": Decimal("0.0"),
                    "remaining": Decimal("1000.0"),
                    "reset_time": None
                },
                BudgetPeriod.MONTHLY: {
                    "limit": Decimal("3000.0"),
                    "used": Decimal("0.0"),
                    "remaining": Decimal("3000.0"),
                    "reset_time": None
                }
            }
            
            # Load custom budgets
            custom_budgets = await db_utils.get_agent_state(
                "cost_manager",
                "budgets"
            )
            
            if custom_budgets:
                self._merge_budgets(custom_budgets)
                
            # Initialize reset times
            self._initialize_budget_reset_times()
            
        except Exception as e:
            raise Exception(f"Failed to initialize budgets: {str(e)}")

    async def _initialize_optimization_rules(self) -> None:
        """Initialize cost optimization rules"""
        try:
            self.optimization_rules = {
                "token_reduction": {
                    "enabled": True,
                    "max_reduction": 0.2,  # Maximum 20% reduction
                    "priority_threshold": 0.8  # Apply to non-priority requests
                },
                "model_switching": {
                    "enabled": True,
                    "cost_threshold": 0.9,  # Switch at 90% of budget
                    "performance_threshold": 0.7  # Maintain 70% performance
                },
                "caching": {
                    "enabled": True,
                    "ttl_seconds": 3600,
                    "similarity_threshold": 0.95
                },
                "batching": {
                    "enabled": True,
                    "max_batch_size": 10,
                    "max_wait_ms": 100
                }
            }
            
            # Load custom rules
            custom_rules = await db_utils.get_agent_state(
                "cost_manager",
                "optimization_rules"
            )
            
            if custom_rules:
                self.optimization_rules.update(custom_rules)
                
        except Exception as e:
            raise Exception(f"Failed to initialize optimization rules: {str(e)}")

    def _start_monitoring_tasks(self) -> None:
        """Start cost monitoring tasks"""
        asyncio.create_task(self._monitor_costs())
        asyncio.create_task(self._monitor_budgets())
        asyncio.create_task(self._run_optimizations())

    async def record_cost(
        self,
        model_type: ModelType,
        token_count: int,
        cost: Decimal
    ) -> None:
        """
        Record cost for model usage
        
        Args:
            model_type: Type of the model
            token_count: Number of tokens used
            cost: Cost of the request
        """
        try:
            tracking = self.cost_tracking[model_type]
            
            # Update tracking
            tracking["total_cost"] += cost
            tracking["token_count"] += token_count
            tracking["request_count"] += 1
            tracking["average_cost_per_request"] = (
                tracking["total_cost"] / tracking["request_count"]
            )
            tracking["last_updated"] = datetime.now().isoformat()
            
            # Update history
            tracking["cost_history"].append({
                "timestamp": datetime.now().isoformat(),
                "token_count": token_count,
                "cost": str(cost)
            })
            
            # Maintain history size
            if len(tracking["cost_history"]) > 1000:
                tracking["cost_history"] = tracking["cost_history"][-1000:]
            
            # Update budgets
            await self._update_budgets(cost)
            
            # Store metrics
            await self._store_cost_metrics(
                model_type,
                token_count,
                cost
            )
            
        except Exception as e:
            self.logger.error(f"Failed to record cost: {str(e)}")

    async def check_budget(
        self,
        model_type: ModelType,
        estimated_cost: Decimal
    ) -> Dict[str, Any]:
        """
        Check if request is within budget
        
        Args:
            model_type: Type of the model
            estimated_cost: Estimated cost of request
            
        Returns:
            Dictionary containing budget check results
        """
        try:
            results = {}
            
            for period, budget in self.budgets.items():
                remaining = budget["remaining"]
                
                if remaining < estimated_cost:
                    results[period] = {
                        "allowed": False,
                        "reason": "Budget exceeded",
                        "remaining": str(remaining)
                    }
                    continue
                
                # Check thresholds
                usage_ratio = (
                    (budget["used"] + estimated_cost) /
                    budget["limit"]
                )
                
                if usage_ratio >= CostThresholds.EMERGENCY:
                    results[period] = {
                        "allowed": False,
                        "reason": "Emergency threshold exceeded",
                        "usage_ratio": float(usage_ratio)
                    }
                elif usage_ratio >= CostThresholds.CRITICAL:
                    results[period] = {
                        "allowed": True,
                        "warning": "Critical threshold reached",
                        "usage_ratio": float(usage_ratio)
                    }
                elif usage_ratio >= CostThresholds.WARNING:
                    results[period] = {
                        "allowed": True,
                        "warning": "Warning threshold reached",
                        "usage_ratio": float(usage_ratio)
                    }
                else:
                    results[period] = {
                        "allowed": True,
                        "usage_ratio": float(usage_ratio)
                    }
            
            return results
            
        except Exception as e:
            self.logger.error(f"Failed to check budget: {str(e)}")
            return {"error": str(e)}

    async def optimize_request(
        self,
        model_type: ModelType,
        request: Dict[str, Any],
        estimated_cost: Decimal
    ) -> Dict[str, Any]:
        """
        Optimize request for cost efficiency
        
        Args:
            model_type: Type of the model
            request: Request details
            estimated_cost: Estimated cost of request
            
        Returns:
            Dictionary containing optimized request
        """
        try:
            optimized_request = request.copy()
            
            # Check if optimization is needed
            budget_check = await self.check_budget(
                model_type,
                estimated_cost
            )
            
            needs_optimization = any(
                check.get("warning") is not None
                for check in budget_check.values()
            )
            
            if not needs_optimization:
                return {
                    "optimized": False,
                    "request": optimized_request
                }
            
            # Apply optimizations
            if self.optimization_rules["token_reduction"]["enabled"]:
                optimized_request = await self._optimize_tokens(
                    optimized_request
                )
            
            if self.optimization_rules["model_switching"]["enabled"]:
                alternative_model = await self._find_cheaper_model(
                    model_type,
                    estimated_cost
                )
                if alternative_model:
                    return {
                        "optimized": True,
                        "switch_model": alternative_model,
                        "request": optimized_request
                    }
            
            return {
                "optimized": True,
                "request": optimized_request
            }
            
        except Exception as e:
            self.logger.error(f"Failed to optimize request: {str(e)}")
            return {
                "optimized": False,
                "request": request,
                "error": str(e)
            }

    async def get_cost_report(
        self,
        period: Optional[str] = None,
        model_type: Optional[ModelType] = None
    ) -> Dict[str, Any]:
        """
        Get cost usage report
        
        Args:
            period: Optional time period to report
            model_type: Optional specific model to report
            
        Returns:
            Dictionary containing cost report
        """
        try:
            report = {
                "timestamp": datetime.now().isoformat(),
                "total_cost": Decimal("0.0"),
                "models": {},
                "budgets": {}
            }
            
            # Get model costs
            models = [model_type] if model_type else ModelType
            for model in models:
                tracking = self.cost_tracking[model]
                report["models"][model] = {
                    "total_cost": str(tracking["total_cost"]),
                    "token_count": tracking["token_count"],
                    "request_count": tracking["request_count"],
                    "average_cost": str(tracking["average_cost_per_request"])
                }
                report["total_cost"] += tracking["total_cost"]
            
            # Get budget status
            periods = [period] if period else BudgetPeriod
            for p in periods:
                budget = self.budgets[p]
                report["budgets"][p] = {
                    "limit": str(budget["limit"]),
                    "used": str(budget["used"]),
                    "remaining": str(budget["remaining"]),
                    "reset_time": budget["reset_time"]
                }
            
            report["total_cost"] = str(report["total_cost"])
            return report
            
        except Exception as e:
            self.logger.error(f"Failed to generate cost report: {str(e)}")
            return {"error": str(e)}

    async def _monitor_costs(self) -> None:
        """Monitor costs continuously"""
        while True:
            try:
                current_time = datetime.now()
                
                for model_type, tracking in self.cost_tracking.items():
                    # Calculate recent costs
                    recent_costs = [
                        Decimal(h["cost"])
                        for h in tracking["cost_history"]
                        if (current_time - datetime.fromisoformat(h["timestamp"])) <=
                        timedelta(hours=1)
                    ]
                    
                    if recent_costs:
                        hourly_cost = sum(recent_costs)
                        
                        # Check for cost anomalies
                        if hourly_cost > self.budgets[BudgetPeriod.HOURLY]["limit"]:
                            await self._handle_cost_anomaly(
                                model_type,
                                hourly_cost
                            )
                
                # Wait before next check
                await asyncio.sleep(300)  # Check every 5 minutes
                
            except Exception as e:
                self.logger.error(f"Error in cost monitoring: {str(e)}")
                await asyncio.sleep(300)

    async def _monitor_budgets(self) -> None:
        """Monitor budgets continuously"""
        while True:
            try:
                current_time = datetime.now()
                
                for period, budget in self.budgets.items():
                    # Check if budget needs reset
                    if budget["reset_time"] and current_time >= datetime.fromisoformat(
                        budget["reset_time"]
                    ):
                        await self._reset_budget(period)
                    
                    # Check budget thresholds
                    usage_ratio = budget["used"] / budget["limit"]
                    
                    if usage_ratio >= CostThresholds.EMERGENCY:
                        await self._handle_budget_emergency(period)
                    elif usage_ratio >= CostThresholds.CRITICAL:
                        await self._handle_budget_critical(period)
                    elif usage_ratio >= CostThresholds.WARNING:
                        await self._handle_budget_warning(period)
                
                # Wait before next check
                await asyncio.sleep(60)  # Check every minute
                
            except Exception as e:
                self.logger.error(f"Error in budget monitoring: {str(e)}")
                await asyncio.sleep(60)

    async def _run_optimizations(self) -> None:
        """Run cost optimizations continuously"""
        while True:
            try:
                # Analyze cost patterns
                patterns = await self._analyze_cost_patterns()
                
                # Update optimization rules
                await self._update_optimization_rules(patterns)
                
                # Wait before next optimization
                await asyncio.sleep(3600)  # Run every hour
                
            except Exception as e:
                self.logger.error(f"Error in optimization: {str(e)}")
                await asyncio.sleep(3600)

    async def _store_cost_metrics(
        self,
        model_type: ModelType,
        token_count: int,
        cost: Decimal
    ) -> None:
        """Store cost metrics"""
        try:
            await db_utils.record_metric(
                agent_id="cost_manager",
                metric_type="model_cost",
                value=float(cost),
                tags={
                    "model": model_type,
                    "token_count": token_count,
                    "cost_per_token": float(cost / token_count)
                }
            )
            
        except Exception as e:
            self.logger.error(f"Failed to store cost metrics: {str(e)}")

# Global cost manager instance
cost_manager = ModelCostManager()
