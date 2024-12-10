"""
Model Performance Analyzer for AATS
Tracks and analyzes performance metrics, identifies bottlenecks,
and provides optimization recommendations
"""

import asyncio
import logging
from typing import Any, Dict, List, Optional, Set, Union, Tuple
from datetime import datetime, timedelta
import json
import statistics
from dataclasses import dataclass
import numpy as np
from collections import deque

from .model_manager import ModelType
from ..config.settings.agent_model_config import MODEL_CAPABILITIES
from ..integration.databases.utils import db_utils

@dataclass
class PerformanceThresholds:
    """Performance threshold definitions"""
    latency_ms: float = 1000.0  # Maximum acceptable latency
    error_rate: float = 0.05    # Maximum acceptable error rate
    throughput_rps: float = 10.0  # Minimum acceptable throughput
    success_rate: float = 0.95  # Minimum acceptable success rate
    token_rate: float = 100.0   # Minimum tokens per second

class PerformanceMetric(str):
    """Performance metric types"""
    LATENCY = "latency"
    THROUGHPUT = "throughput"
    ERROR_RATE = "error_rate"
    SUCCESS_RATE = "success_rate"
    TOKEN_RATE = "token_rate"
    MEMORY_USAGE = "memory_usage"
    CPU_USAGE = "cpu_usage"

class ModelPerformanceAnalyzer:
    """
    Model Performance Analyzer responsible for tracking and analyzing
    performance metrics across the system.
    """

    def __init__(self):
        self.logger = logging.getLogger("ModelPerformanceAnalyzer")
        self.performance_metrics: Dict[str, Dict] = {}
        self.bottlenecks: Dict[str, List[Dict]] = {}
        self.optimization_history: List[Dict] = []
        self.thresholds = PerformanceThresholds()
        self.analysis_window: int = 3600  # 1 hour analysis window

    async def initialize(self) -> bool:
        """Initialize the Model Performance Analyzer"""
        try:
            self.logger.info("Initializing Model Performance Analyzer...")
            
            # Initialize performance tracking
            await self._initialize_performance_tracking()
            
            # Initialize bottleneck detection
            await self._initialize_bottleneck_detection()
            
            # Initialize optimization tracking
            await self._initialize_optimization_tracking()
            
            # Start analysis tasks
            self._start_analysis_tasks()
            
            self.logger.info("Model Performance Analyzer initialized successfully")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to initialize Model Performance Analyzer: {str(e)}")
            return False

    async def _initialize_performance_tracking(self) -> None:
        """Initialize performance tracking system"""
        try:
            # Initialize metrics for each model
            for model_type in ModelType:
                self.performance_metrics[model_type] = {
                    PerformanceMetric.LATENCY: {
                        "current": 0.0,
                        "average": 0.0,
                        "min": None,
                        "max": None,
                        "history": deque(maxlen=1000)
                    },
                    PerformanceMetric.THROUGHPUT: {
                        "current": 0.0,
                        "average": 0.0,
                        "peak": 0.0,
                        "history": deque(maxlen=1000)
                    },
                    PerformanceMetric.ERROR_RATE: {
                        "current": 0.0,
                        "total_requests": 0,
                        "total_errors": 0,
                        "history": deque(maxlen=1000)
                    },
                    PerformanceMetric.SUCCESS_RATE: {
                        "current": 1.0,
                        "total_requests": 0,
                        "total_successes": 0,
                        "history": deque(maxlen=1000)
                    },
                    PerformanceMetric.TOKEN_RATE: {
                        "current": 0.0,
                        "average": 0.0,
                        "peak": 0.0,
                        "history": deque(maxlen=1000)
                    },
                    PerformanceMetric.MEMORY_USAGE: {
                        "current": 0.0,
                        "average": 0.0,
                        "peak": 0.0,
                        "history": deque(maxlen=1000)
                    },
                    PerformanceMetric.CPU_USAGE: {
                        "current": 0.0,
                        "average": 0.0,
                        "peak": 0.0,
                        "history": deque(maxlen=1000)
                    }
                }
            
            # Load historical metrics
            stored_metrics = await db_utils.get_agent_state(
                "performance_analyzer",
                "performance_metrics"
            )
            
            if stored_metrics:
                self._merge_metrics(stored_metrics)
                
        except Exception as e:
            raise Exception(f"Failed to initialize performance tracking: {str(e)}")

    async def _initialize_bottleneck_detection(self) -> None:
        """Initialize bottleneck detection system"""
        try:
            # Initialize bottleneck tracking for each model
            for model_type in ModelType:
                self.bottlenecks[model_type] = []
            
            # Set up detection thresholds
            self.bottleneck_thresholds = {
                PerformanceMetric.LATENCY: self.thresholds.latency_ms,
                PerformanceMetric.ERROR_RATE: self.thresholds.error_rate,
                PerformanceMetric.THROUGHPUT: self.thresholds.throughput_rps,
                PerformanceMetric.SUCCESS_RATE: self.thresholds.success_rate,
                PerformanceMetric.TOKEN_RATE: self.thresholds.token_rate
            }
            
        except Exception as e:
            raise Exception(f"Failed to initialize bottleneck detection: {str(e)}")

    async def _initialize_optimization_tracking(self) -> None:
        """Initialize optimization tracking system"""
        try:
            # Set up optimization parameters
            self.optimization_config = {
                "min_improvement": 0.1,  # 10% minimum improvement required
                "max_attempts": 3,       # Maximum optimization attempts
                "cooldown_period": 3600  # 1 hour between optimization attempts
            }
            
            # Initialize optimization history
            self.optimization_history = []
            
        except Exception as e:
            raise Exception(f"Failed to initialize optimization tracking: {str(e)}")

    def _start_analysis_tasks(self) -> None:
        """Start performance analysis tasks"""
        asyncio.create_task(self._analyze_performance())
        asyncio.create_task(self._detect_bottlenecks())
        asyncio.create_task(self._generate_optimizations())

    async def record_metrics(
        self,
        model_type: ModelType,
        metrics: Dict[str, Any]
    ) -> None:
        """
        Record performance metrics
        
        Args:
            model_type: Type of the model
            metrics: Dictionary of performance metrics
        """
        try:
            timestamp = datetime.now()
            tracking = self.performance_metrics[model_type]
            
            # Update latency metrics
            if "latency" in metrics:
                latency = metrics["latency"]
                latency_tracking = tracking[PerformanceMetric.LATENCY]
                latency_tracking["current"] = latency
                latency_tracking["history"].append({
                    "value": latency,
                    "timestamp": timestamp.isoformat()
                })
                
                # Update min/max
                if latency_tracking["min"] is None:
                    latency_tracking["min"] = latency
                else:
                    latency_tracking["min"] = min(latency_tracking["min"], latency)
                    
                if latency_tracking["max"] is None:
                    latency_tracking["max"] = latency
                else:
                    latency_tracking["max"] = max(latency_tracking["max"], latency)
                
                # Update average
                latency_tracking["average"] = statistics.mean(
                    [h["value"] for h in latency_tracking["history"]]
                )
            
            # Update throughput metrics
            if "requests_per_second" in metrics:
                throughput = metrics["requests_per_second"]
                throughput_tracking = tracking[PerformanceMetric.THROUGHPUT]
                throughput_tracking["current"] = throughput
                throughput_tracking["history"].append({
                    "value": throughput,
                    "timestamp": timestamp.isoformat()
                })
                
                # Update peak and average
                throughput_tracking["peak"] = max(
                    throughput_tracking["peak"],
                    throughput
                )
                throughput_tracking["average"] = statistics.mean(
                    [h["value"] for h in throughput_tracking["history"]]
                )
            
            # Update error rate metrics
            if "error" in metrics:
                error_tracking = tracking[PerformanceMetric.ERROR_RATE]
                error_tracking["total_requests"] += 1
                if metrics["error"]:
                    error_tracking["total_errors"] += 1
                
                error_tracking["current"] = (
                    error_tracking["total_errors"] /
                    error_tracking["total_requests"]
                )
                
                error_tracking["history"].append({
                    "value": error_tracking["current"],
                    "timestamp": timestamp.isoformat()
                })
            
            # Store metrics
            await self._store_performance_metrics(
                model_type,
                metrics,
                timestamp
            )
            
        except Exception as e:
            self.logger.error(f"Failed to record metrics: {str(e)}")

    async def analyze_performance(
        self,
        model_type: ModelType,
        time_window: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Analyze model performance
        
        Args:
            model_type: Type of the model
            time_window: Optional analysis window in seconds
            
        Returns:
            Dictionary containing performance analysis
        """
        try:
            window = time_window or self.analysis_window
            tracking = self.performance_metrics[model_type]
            current_time = datetime.now()
            cutoff_time = current_time - timedelta(seconds=window)
            
            analysis = {}
            
            # Analyze each metric
            for metric_type, metric_data in tracking.items():
                # Filter metrics within time window
                recent_metrics = [
                    h["value"] for h in metric_data["history"]
                    if datetime.fromisoformat(h["timestamp"]) > cutoff_time
                ]
                
                if recent_metrics:
                    metric_analysis = {
                        "current": metric_data["current"],
                        "average": statistics.mean(recent_metrics),
                        "std_dev": statistics.stdev(recent_metrics) if len(recent_metrics) > 1 else 0,
                        "trend": self._calculate_trend(recent_metrics),
                        "threshold_violations": self._check_threshold_violations(
                            metric_type,
                            recent_metrics
                        )
                    }
                    
                    if "min" in metric_data:
                        metric_analysis["min"] = metric_data["min"]
                    if "max" in metric_data:
                        metric_analysis["max"] = metric_data["max"]
                    if "peak" in metric_data:
                        metric_analysis["peak"] = metric_data["peak"]
                        
                    analysis[metric_type] = metric_analysis
            
            # Add overall assessment
            analysis["overall_health"] = self._assess_overall_health(analysis)
            analysis["bottlenecks"] = self._identify_bottlenecks(analysis)
            analysis["recommendations"] = await self._generate_recommendations(
                model_type,
                analysis
            )
            
            return analysis
            
        except Exception as e:
            self.logger.error(f"Failed to analyze performance: {str(e)}")
            return {"error": str(e)}

    async def detect_bottlenecks(
        self,
        model_type: ModelType
    ) -> List[Dict[str, Any]]:
        """
        Detect performance bottlenecks
        
        Args:
            model_type: Type of the model
            
        Returns:
            List of detected bottlenecks
        """
        try:
            tracking = self.performance_metrics[model_type]
            bottlenecks = []
            
            # Check each metric against thresholds
            for metric_type, threshold in self.bottleneck_thresholds.items():
                metric_data = tracking[metric_type]
                current_value = metric_data["current"]
                
                if self._is_bottleneck(metric_type, current_value, threshold):
                    bottleneck = {
                        "metric": metric_type,
                        "current_value": current_value,
                        "threshold": threshold,
                        "severity": self._calculate_severity(
                            metric_type,
                            current_value,
                            threshold
                        ),
                        "timestamp": datetime.now().isoformat()
                    }
                    bottlenecks.append(bottleneck)
            
            # Store bottlenecks
            if bottlenecks:
                self.bottlenecks[model_type].extend(bottlenecks)
                await self._store_bottlenecks(model_type, bottlenecks)
            
            return bottlenecks
            
        except Exception as e:
            self.logger.error(f"Failed to detect bottlenecks: {str(e)}")
            return []

    async def get_optimization_recommendations(
        self,
        model_type: ModelType
    ) -> List[Dict[str, Any]]:
        """
        Get optimization recommendations
        
        Args:
            model_type: Type of the model
            
        Returns:
            List of optimization recommendations
        """
        try:
            # Analyze recent performance
            analysis = await self.analyze_performance(model_type)
            
            # Generate recommendations
            recommendations = []
            
            # Check latency optimizations
            if analysis[PerformanceMetric.LATENCY]["current"] > self.thresholds.latency_ms:
                recommendations.append({
                    "type": "latency",
                    "priority": "high",
                    "suggestion": "Consider reducing request complexity or batch size",
                    "expected_improvement": "20-30% latency reduction"
                })
            
            # Check throughput optimizations
            if analysis[PerformanceMetric.THROUGHPUT]["current"] < self.thresholds.throughput_rps:
                recommendations.append({
                    "type": "throughput",
                    "priority": "medium",
                    "suggestion": "Implement request batching or increase concurrency",
                    "expected_improvement": "40-50% throughput increase"
                })
            
            # Check error rate optimizations
            if analysis[PerformanceMetric.ERROR_RATE]["current"] > self.thresholds.error_rate:
                recommendations.append({
                    "type": "reliability",
                    "priority": "high",
                    "suggestion": "Implement retry logic and error handling",
                    "expected_improvement": "50-60% error rate reduction"
                })
            
            # Store recommendations
            await self._store_recommendations(model_type, recommendations)
            
            return recommendations
            
        except Exception as e:
            self.logger.error(f"Failed to get optimization recommendations: {str(e)}")
            return []

    async def _analyze_performance(self) -> None:
        """Analyze performance continuously"""
        while True:
            try:
                for model_type in ModelType:
                    # Analyze performance
                    analysis = await self.analyze_performance(model_type)
                    
                    # Check for issues
                    if analysis["overall_health"] < 0.8:  # Below 80% health
                        await self._handle_performance_issues(
                            model_type,
                            analysis
                        )
                
                # Wait before next analysis
                await asyncio.sleep(300)  # Analyze every 5 minutes
                
            except Exception as e:
                self.logger.error(f"Error in performance analysis: {str(e)}")
                await asyncio.sleep(300)

    async def _detect_bottlenecks(self) -> None:
        """Detect bottlenecks continuously"""
        while True:
            try:
                for model_type in ModelType:
                    # Detect bottlenecks
                    bottlenecks = await self.detect_bottlenecks(model_type)
                    
                    if bottlenecks:
                        # Handle critical bottlenecks
                        critical_bottlenecks = [
                            b for b in bottlenecks
                            if b["severity"] == "critical"
                        ]
                        if critical_bottlenecks:
                            await self._handle_critical_bottlenecks(
                                model_type,
                                critical_bottlenecks
                            )
                
                # Wait before next detection
                await asyncio.sleep(60)  # Check every minute
                
            except Exception as e:
                self.logger.error(f"Error in bottleneck detection: {str(e)}")
                await asyncio.sleep(60)

    async def _generate_optimizations(self) -> None:
        """Generate optimization recommendations continuously"""
        while True:
            try:
                for model_type in ModelType:
                    # Generate recommendations
                    recommendations = await self.get_optimization_recommendations(
                        model_type
                    )
                    
                    if recommendations:
                        # Apply automatic optimizations
                        await self._apply_automatic_optimizations(
                            model_type,
                            recommendations
                        )
                
                # Wait before next generation
                await asyncio.sleep(3600)  # Generate every hour
                
            except Exception as e:
                self.logger.error(f"Error in optimization generation: {str(e)}")
                await asyncio.sleep(3600)

    async def _store_performance_metrics(
        self,
        model_type: ModelType,
        metrics: Dict[str, Any],
        timestamp: datetime
    ) -> None:
        """Store performance metrics"""
        try:
            await db_utils.record_metric(
                agent_id="performance_analyzer",
                metric_type="model_performance",
                value=metrics.get("latency", 0),
                tags={
                    "model": model_type,
                    "throughput": metrics.get("requests_per_second", 0),
                    "error_rate": metrics.get("error", False),
                    "timestamp": timestamp.isoformat()
                }
            )
            
        except Exception as e:
            self.logger.error(f"Failed to store performance metrics: {str(e)}")

# Global performance analyzer instance
performance_analyzer = ModelPerformanceAnalyzer()
