"""
Model Metrics Collector for AATS
Gathers and analyzes performance metrics from models across the system
"""

import asyncio
import logging
from typing import Any, Dict, List, Optional, Set, Union
from datetime import datetime, timedelta
import json
import statistics
from dataclasses import dataclass

from .model_manager import ModelType
from ..config.settings.agent_model_config import MODEL_CAPABILITIES
from ..integration.databases.utils import db_utils

@dataclass
class MetricThresholds:
    """Metric threshold definitions"""
    latency_ms: float = 1000.0  # Maximum acceptable latency
    error_rate: float = 0.05    # Maximum acceptable error rate
    token_cost: float = 0.001   # Cost per token threshold
    memory_usage_mb: float = 1024.0  # Memory usage threshold
    concurrent_requests: int = 100  # Maximum concurrent requests

class MetricType(str):
    """Metric type definitions"""
    LATENCY = "latency"
    ERROR_RATE = "error_rate"
    TOKEN_USAGE = "token_usage"
    COST = "cost"
    MEMORY = "memory"
    THROUGHPUT = "throughput"

class ModelMetricsCollector:
    """
    Model Metrics Collector responsible for gathering and analyzing
    performance metrics from models across the system.
    """

    def __init__(self):
        self.logger = logging.getLogger("ModelMetricsCollector")
        self.metrics: Dict[str, Dict] = {}
        self.thresholds = MetricThresholds()
        self.alerts: List[Dict] = []
        self.analysis_history: List[Dict] = []

    async def initialize(self) -> bool:
        """Initialize the Model Metrics Collector"""
        try:
            self.logger.info("Initializing Model Metrics Collector...")
            
            # Initialize metrics storage
            await self._initialize_metrics_storage()
            
            # Initialize analysis system
            await self._initialize_analysis()
            
            # Start collection tasks
            self._start_collection_tasks()
            
            self.logger.info("Model Metrics Collector initialized successfully")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to initialize Model Metrics Collector: {str(e)}")
            return False

    async def _initialize_metrics_storage(self) -> None:
        """Initialize metrics storage system"""
        try:
            # Initialize metrics structure for each model
            for model_type in ModelType:
                self.metrics[model_type] = {
                    MetricType.LATENCY: {
                        "current": 0,
                        "average": 0,
                        "min": None,
                        "max": None,
                        "history": []
                    },
                    MetricType.ERROR_RATE: {
                        "current": 0,
                        "total_requests": 0,
                        "total_errors": 0,
                        "history": []
                    },
                    MetricType.TOKEN_USAGE: {
                        "total": 0,
                        "per_request": 0,
                        "history": []
                    },
                    MetricType.COST: {
                        "total": 0,
                        "per_request": 0,
                        "history": []
                    },
                    MetricType.MEMORY: {
                        "current": 0,
                        "peak": 0,
                        "history": []
                    },
                    MetricType.THROUGHPUT: {
                        "current": 0,
                        "average": 0,
                        "peak": 0,
                        "history": []
                    }
                }
            
            # Load historical metrics
            await self._load_historical_metrics()
            
        except Exception as e:
            raise Exception(f"Failed to initialize metrics storage: {str(e)}")

    async def _initialize_analysis(self) -> None:
        """Initialize analysis system"""
        try:
            # Set up analysis parameters
            self.analysis_config = {
                "window_size": 3600,  # Analysis window in seconds
                "sample_interval": 60,  # Sampling interval in seconds
                "trend_threshold": 0.1,  # Significant trend threshold
                "anomaly_std_dev": 2.0,  # Standard deviations for anomaly detection
                "correlation_threshold": 0.7  # Correlation significance threshold
            }
            
            # Initialize analysis history
            self.analysis_history = []
            
        except Exception as e:
            raise Exception(f"Failed to initialize analysis: {str(e)}")

    def _start_collection_tasks(self) -> None:
        """Start metric collection tasks"""
        asyncio.create_task(self._collect_performance_metrics())
        asyncio.create_task(self._collect_resource_metrics())
        asyncio.create_task(self._analyze_metrics())

    async def record_metrics(
        self,
        model_type: ModelType,
        metrics: Dict[str, Any]
    ) -> None:
        """
        Record metrics for a model
        
        Args:
            model_type: Type of the model
            metrics: Dictionary of metrics to record
        """
        try:
            timestamp = datetime.now()
            
            # Update current metrics
            model_metrics = self.metrics[model_type]
            
            # Update latency metrics
            if "latency" in metrics:
                latency = metrics["latency"]
                latency_metrics = model_metrics[MetricType.LATENCY]
                latency_metrics["current"] = latency
                latency_metrics["history"].append({
                    "value": latency,
                    "timestamp": timestamp.isoformat()
                })
                
                # Update min/max
                if latency_metrics["min"] is None:
                    latency_metrics["min"] = latency
                else:
                    latency_metrics["min"] = min(latency_metrics["min"], latency)
                    
                if latency_metrics["max"] is None:
                    latency_metrics["max"] = latency
                else:
                    latency_metrics["max"] = max(latency_metrics["max"], latency)
                
                # Update average
                latency_metrics["average"] = statistics.mean(
                    [h["value"] for h in latency_metrics["history"][-100:]]
                )
            
            # Update error metrics
            if "error" in metrics:
                error_metrics = model_metrics[MetricType.ERROR_RATE]
                error_metrics["total_requests"] += 1
                if metrics["error"]:
                    error_metrics["total_errors"] += 1
                
                error_metrics["current"] = (
                    error_metrics["total_errors"] /
                    error_metrics["total_requests"]
                )
                
                error_metrics["history"].append({
                    "value": error_metrics["current"],
                    "timestamp": timestamp.isoformat()
                })
            
            # Update token usage metrics
            if "tokens" in metrics:
                token_metrics = model_metrics[MetricType.TOKEN_USAGE]
                tokens = metrics["tokens"]
                token_metrics["total"] += tokens
                token_metrics["per_request"] = (
                    token_metrics["total"] /
                    model_metrics[MetricType.ERROR_RATE]["total_requests"]
                )
                
                token_metrics["history"].append({
                    "value": tokens,
                    "timestamp": timestamp.isoformat()
                })
            
            # Store metrics
            await self._store_metrics(model_type, metrics, timestamp)
            
            # Check for alerts
            await self._check_alerts(model_type)
            
        except Exception as e:
            self.logger.error(f"Failed to record metrics: {str(e)}")

    async def get_model_performance(
        self,
        model_type: ModelType,
        metric_types: Optional[List[str]] = None,
        time_range: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Get performance metrics for a model
        
        Args:
            model_type: Type of the model
            metric_types: Optional list of specific metrics to retrieve
            time_range: Optional time range in seconds
            
        Returns:
            Dictionary of performance metrics
        """
        try:
            if model_type not in self.metrics:
                raise ValueError(f"Unknown model type: {model_type}")
            
            model_metrics = self.metrics[model_type]
            
            # Filter metrics by type if specified
            if metric_types:
                metrics = {
                    metric_type: model_metrics[metric_type]
                    for metric_type in metric_types
                    if metric_type in model_metrics
                }
            else:
                metrics = model_metrics.copy()
            
            # Filter by time range if specified
            if time_range:
                cutoff = datetime.now() - timedelta(seconds=time_range)
                for metric_type in metrics:
                    metrics[metric_type]["history"] = [
                        h for h in metrics[metric_type]["history"]
                        if datetime.fromisoformat(h["timestamp"]) > cutoff
                    ]
            
            return metrics
            
        except Exception as e:
            self.logger.error(f"Failed to get model performance: {str(e)}")
            return {}

    async def analyze_trends(
        self,
        model_type: ModelType,
        metric_type: str,
        window_size: int = 3600
    ) -> Dict[str, Any]:
        """
        Analyze trends for a specific metric
        
        Args:
            model_type: Type of the model
            metric_type: Type of metric to analyze
            window_size: Analysis window in seconds
            
        Returns:
            Dictionary containing trend analysis
        """
        try:
            metrics = await self.get_model_performance(
                model_type,
                [metric_type],
                window_size
            )
            
            if not metrics or metric_type not in metrics:
                return {}
            
            history = metrics[metric_type]["history"]
            if not history:
                return {}
            
            # Calculate basic statistics
            values = [h["value"] for h in history]
            stats = {
                "mean": statistics.mean(values),
                "median": statistics.median(values),
                "std_dev": statistics.stdev(values) if len(values) > 1 else 0,
                "min": min(values),
                "max": max(values)
            }
            
            # Detect trend
            trend = self._detect_trend(values)
            
            # Detect anomalies
            anomalies = self._detect_anomalies(
                values,
                stats["mean"],
                stats["std_dev"]
            )
            
            return {
                "statistics": stats,
                "trend": trend,
                "anomalies": anomalies,
                "window_size": window_size,
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            self.logger.error(f"Failed to analyze trends: {str(e)}")
            return {}

    async def _collect_performance_metrics(self) -> None:
        """Collect performance metrics continuously"""
        while True:
            try:
                for model_type in ModelType:
                    # Collect current performance metrics
                    metrics = await self._get_current_metrics(model_type)
                    
                    # Record metrics
                    await self.record_metrics(model_type, metrics)
                
                # Wait before next collection
                await asyncio.sleep(60)
                
            except Exception as e:
                self.logger.error(f"Error in performance collection: {str(e)}")
                await asyncio.sleep(60)

    async def _collect_resource_metrics(self) -> None:
        """Collect resource usage metrics continuously"""
        while True:
            try:
                for model_type in ModelType:
                    # Collect resource metrics
                    metrics = await self._get_resource_metrics(model_type)
                    
                    # Update memory metrics
                    memory_metrics = self.metrics[model_type][MetricType.MEMORY]
                    memory_metrics["current"] = metrics.get("memory_usage", 0)
                    memory_metrics["peak"] = max(
                        memory_metrics["peak"],
                        memory_metrics["current"]
                    )
                    
                    memory_metrics["history"].append({
                        "value": memory_metrics["current"],
                        "timestamp": datetime.now().isoformat()
                    })
                
                # Wait before next collection
                await asyncio.sleep(300)
                
            except Exception as e:
                self.logger.error(f"Error in resource collection: {str(e)}")
                await asyncio.sleep(300)

    async def _analyze_metrics(self) -> None:
        """Analyze metrics continuously"""
        while True:
            try:
                analysis_results = {}
                
                for model_type in ModelType:
                    # Analyze each metric type
                    model_analysis = {}
                    for metric_type in MetricType:
                        analysis = await self.analyze_trends(
                            model_type,
                            metric_type
                        )
                        model_analysis[metric_type] = analysis
                    
                    analysis_results[model_type] = model_analysis
                
                # Store analysis results
                await self._store_analysis(analysis_results)
                
                # Update analysis history
                self.analysis_history.append({
                    "results": analysis_results,
                    "timestamp": datetime.now().isoformat()
                })
                
                # Maintain history size
                if len(self.analysis_history) > 100:
                    self.analysis_history = self.analysis_history[-100:]
                
                # Wait before next analysis
                await asyncio.sleep(3600)
                
            except Exception as e:
                self.logger.error(f"Error in metrics analysis: {str(e)}")
                await asyncio.sleep(3600)

    def _detect_trend(self, values: List[float]) -> Dict[str, Any]:
        """Detect trend in values"""
        if len(values) < 2:
            return {"type": "insufficient_data"}
        
        # Calculate simple linear regression
        n = len(values)
        x = list(range(n))
        slope = (
            (n * sum(i * v for i, v in enumerate(values)) - sum(x) * sum(values)) /
            (n * sum(i * i for i in x) - sum(x) * sum(x))
        )
        
        # Determine trend type and strength
        trend_strength = abs(slope)
        if trend_strength < self.analysis_config["trend_threshold"]:
            trend_type = "stable"
        else:
            trend_type = "increasing" if slope > 0 else "decreasing"
        
        return {
            "type": trend_type,
            "strength": trend_strength,
            "slope": slope
        }

    def _detect_anomalies(
        self,
        values: List[float],
        mean: float,
        std_dev: float
    ) -> List[Dict[str, Any]]:
        """Detect anomalies in values"""
        anomalies = []
        threshold = self.analysis_config["anomaly_std_dev"] * std_dev
        
        for i, value in enumerate(values):
            if abs(value - mean) > threshold:
                anomalies.append({
                    "index": i,
                    "value": value,
                    "deviation": abs(value - mean) / std_dev
                })
        
        return anomalies

# Global metrics collector instance
metrics_collector = ModelMetricsCollector()
