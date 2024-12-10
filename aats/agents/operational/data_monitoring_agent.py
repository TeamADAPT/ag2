"""
Data Monitoring Agent Implementation
This agent handles monitoring, alerting, and reporting of data operations
"""

import asyncio
import logging
from typing import Any, Dict, List, Optional, Set, Union, Callable
from datetime import datetime, timedelta
import json
import pandas as pd
import numpy as np
from prometheus_client import Counter, Gauge, Histogram, Summary
import psutil
import aiohttp
from dataclasses import dataclass
from enum import Enum

from ..base_agent import BaseAgent, AgentConfig
from ...config.settings.base_config import config
from ...integration.databases.utils import db_utils

class MetricType(str, Enum):
    """Metric type definitions"""
    COUNTER = "counter"
    GAUGE = "gauge"
    HISTOGRAM = "histogram"
    SUMMARY = "summary"

class AlertSeverity(str, Enum):
    """Alert severity definitions"""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"

@dataclass
class AlertRule:
    """Alert rule definition"""
    name: str
    metric: str
    condition: str
    threshold: float
    severity: AlertSeverity
    cooldown: int
    description: str
    actions: List[str]

class DataMonitoringAgent(BaseAgent):
    """
    Data Monitoring Agent responsible for monitoring data
    operations and system health.
    """

    def __init__(self):
        super().__init__(AgentConfig(
            name="DataMonitor",
            description="Handles data operation monitoring",
            capabilities=[
                "metric_collection",
                "alert_management",
                "health_monitoring",
                "performance_tracking",
                "reporting"
            ],
            required_tools=[
                "metric_collector",
                "alert_manager",
                "reporter"
            ],
            max_concurrent_tasks=5,
            priority_level=2
        ))
        self.metrics: Dict[str, Dict] = {}
        self.alert_rules: Dict[str, AlertRule] = {}
        self.active_alerts: Dict[str, Dict] = {}
        self.metric_history: Dict[str, List] = {}

    async def initialize(self) -> bool:
        """Initialize the Data Monitoring Agent"""
        try:
            self.logger.info("Initializing Data Monitoring Agent...")
            
            # Initialize metrics collection
            await self._initialize_metrics()
            
            # Initialize alert rules
            await self._initialize_alert_rules()
            
            # Initialize monitoring system
            await self._initialize_monitoring()
            
            # Start monitoring tasks
            self._start_monitoring_tasks()
            
            self.logger.info("Data Monitoring Agent initialized successfully")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to initialize Data Monitoring Agent: {str(e)}")
            return False

    async def _initialize_metrics(self) -> None:
        """Initialize metrics collection"""
        try:
            # Initialize Prometheus metrics
            self.metrics = {
                # System metrics
                "system": {
                    "cpu_usage": Gauge(
                        "system_cpu_usage",
                        "System CPU usage percentage"
                    ),
                    "memory_usage": Gauge(
                        "system_memory_usage",
                        "System memory usage percentage"
                    ),
                    "disk_usage": Gauge(
                        "system_disk_usage",
                        "System disk usage percentage"
                    )
                },
                # Data operation metrics
                "operations": {
                    "total_operations": Counter(
                        "data_operations_total",
                        "Total number of data operations"
                    ),
                    "operation_duration": Histogram(
                        "data_operation_duration_seconds",
                        "Duration of data operations",
                        buckets=[0.1, 0.5, 1.0, 2.0, 5.0, 10.0, 30.0, 60.0]
                    ),
                    "operation_errors": Counter(
                        "data_operation_errors_total",
                        "Total number of data operation errors"
                    )
                },
                # Data volume metrics
                "data": {
                    "processed_bytes": Counter(
                        "data_processed_bytes_total",
                        "Total bytes of data processed"
                    ),
                    "processing_rate": Gauge(
                        "data_processing_rate_bytes",
                        "Current data processing rate in bytes per second"
                    ),
                    "error_rate": Gauge(
                        "data_error_rate",
                        "Current error rate in data processing"
                    )
                },
                # Performance metrics
                "performance": {
                    "latency": Summary(
                        "operation_latency_seconds",
                        "Operation latency in seconds"
                    ),
                    "throughput": Gauge(
                        "operation_throughput",
                        "Operations per second"
                    ),
                    "queue_size": Gauge(
                        "operation_queue_size",
                        "Number of operations in queue"
                    )
                }
            }
            
            # Initialize metric history
            self.metric_history = {
                metric_type: {
                    metric_name: []
                    for metric_name in metrics.keys()
                }
                for metric_type, metrics in self.metrics.items()
            }
            
        except Exception as e:
            raise Exception(f"Failed to initialize metrics: {str(e)}")

    async def _initialize_alert_rules(self) -> None:
        """Initialize alert rules"""
        try:
            # Define default alert rules
            self.alert_rules = {
                "high_cpu_usage": AlertRule(
                    name="High CPU Usage",
                    metric="system_cpu_usage",
                    condition=">=",
                    threshold=90.0,
                    severity=AlertSeverity.WARNING,
                    cooldown=300,
                    description="CPU usage is above 90%",
                    actions=["notify", "log"]
                ),
                "critical_memory_usage": AlertRule(
                    name="Critical Memory Usage",
                    metric="system_memory_usage",
                    condition=">=",
                    threshold=95.0,
                    severity=AlertSeverity.CRITICAL,
                    cooldown=300,
                    description="Memory usage is above 95%",
                    actions=["notify", "log", "scale"]
                ),
                "high_error_rate": AlertRule(
                    name="High Error Rate",
                    metric="data_error_rate",
                    condition=">=",
                    threshold=0.05,
                    severity=AlertSeverity.ERROR,
                    cooldown=600,
                    description="Error rate is above 5%",
                    actions=["notify", "log", "investigate"]
                ),
                "low_throughput": AlertRule(
                    name="Low Throughput",
                    metric="operation_throughput",
                    condition="<=",
                    threshold=10.0,
                    severity=AlertSeverity.WARNING,
                    cooldown=600,
                    description="Throughput is below 10 ops/sec",
                    actions=["notify", "log"]
                )
            }
            
            # Load custom alert rules
            custom_rules = await db_utils.get_agent_state(
                self.id,
                "alert_rules"
            )
            
            if custom_rules:
                self._merge_alert_rules(custom_rules)
                
        except Exception as e:
            raise Exception(f"Failed to initialize alert rules: {str(e)}")

    async def _initialize_monitoring(self) -> None:
        """Initialize monitoring system"""
        try:
            # Initialize monitoring configurations
            self.monitoring_configs = {
                "collection_interval": 60,  # seconds
                "retention_period": 7,      # days
                "batch_size": 1000,         # metrics per batch
                "alert_check_interval": 60  # seconds
            }
            
            # Initialize monitoring state
            self.monitoring_state = {
                "last_collection": None,
                "last_alert_check": None,
                "active_collectors": set(),
                "collection_errors": 0
            }
            
        except Exception as e:
            raise Exception(f"Failed to initialize monitoring: {str(e)}")

    def _start_monitoring_tasks(self) -> None:
        """Start monitoring tasks"""
        asyncio.create_task(self._collect_metrics())
        asyncio.create_task(self._check_alerts())
        asyncio.create_task(self._cleanup_metrics())

    async def collect_metrics(
        self,
        metric_types: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Collect current metrics
        
        Args:
            metric_types: Optional list of metric types to collect
            
        Returns:
            Dictionary containing collected metrics
        """
        try:
            # Determine which metrics to collect
            types_to_collect = metric_types or list(self.metrics.keys())
            
            # Collect metrics
            collected_metrics = {}
            for metric_type in types_to_collect:
                if metric_type in self.metrics:
                    metrics = await self._collect_metric_type(metric_type)
                    collected_metrics[metric_type] = metrics
            
            # Update metric history
            await self._update_metric_history(collected_metrics)
            
            return {
                "success": True,
                "timestamp": datetime.now().isoformat(),
                "metrics": collected_metrics
            }
            
        except Exception as e:
            self.logger.error(f"Metric collection failed: {str(e)}")
            return {
                "success": False,
                "error": str(e)
            }

    async def check_alerts(
        self,
        rules: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Check alert conditions
        
        Args:
            rules: Optional list of specific rules to check
            
        Returns:
            Dictionary containing alert check results
        """
        try:
            # Determine which rules to check
            rules_to_check = (
                [self.alert_rules[r] for r in rules]
                if rules
                else self.alert_rules.values()
            )
            
            # Check alert conditions
            alerts = []
            for rule in rules_to_check:
                alert = await self._check_alert_rule(rule)
                if alert:
                    alerts.append(alert)
            
            # Handle triggered alerts
            if alerts:
                await self._handle_alerts(alerts)
            
            return {
                "success": True,
                "alerts_triggered": len(alerts),
                "alerts": alerts
            }
            
        except Exception as e:
            self.logger.error(f"Alert check failed: {str(e)}")
            return {
                "success": False,
                "error": str(e)
            }

    async def generate_report(
        self,
        report_type: str,
        time_range: Optional[Dict] = None,
        options: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """
        Generate monitoring report
        
        Args:
            report_type: Type of report to generate
            time_range: Optional time range for the report
            options: Optional report options
            
        Returns:
            Dictionary containing report data
        """
        try:
            # Get report generator
            generator = self._get_report_generator(report_type)
            if not generator:
                return {
                    "success": False,
                    "error": f"Unknown report type: {report_type}"
                }
            
            # Generate report
            report = await generator(
                time_range or {"hours": 24},
                options or {}
            )
            
            return {
                "success": True,
                "report_type": report_type,
                "generated_at": datetime.now().isoformat(),
                "data": report
            }
            
        except Exception as e:
            self.logger.error(f"Report generation failed: {str(e)}")
            return {
                "success": False,
                "error": str(e)
            }

    async def _collect_metrics(self) -> None:
        """Collect metrics continuously"""
        while True:
            try:
                # Collect all metrics
                await self.collect_metrics()
                
                # Update last collection timestamp
                self.monitoring_state["last_collection"] = datetime.now()
                
                # Wait before next collection
                await asyncio.sleep(
                    self.monitoring_configs["collection_interval"]
                )
                
            except Exception as e:
                self.logger.error(f"Error in metric collection: {str(e)}")
                self.monitoring_state["collection_errors"] += 1
                await asyncio.sleep(
                    self.monitoring_configs["collection_interval"]
                )

    async def _check_alerts(self) -> None:
        """Check alerts continuously"""
        while True:
            try:
                # Check all alert rules
                await self.check_alerts()
                
                # Update last check timestamp
                self.monitoring_state["last_alert_check"] = datetime.now()
                
                # Wait before next check
                await asyncio.sleep(
                    self.monitoring_configs["alert_check_interval"]
                )
                
            except Exception as e:
                self.logger.error(f"Error in alert checking: {str(e)}")
                await asyncio.sleep(
                    self.monitoring_configs["alert_check_interval"]
                )

    async def _cleanup_metrics(self) -> None:
        """Clean up old metrics"""
        while True:
            try:
                current_time = datetime.now()
                retention_limit = current_time - timedelta(
                    days=self.monitoring_configs["retention_period"]
                )
                
                # Clean up old metrics from history
                for metric_type in self.metric_history:
                    for metric_name in self.metric_history[metric_type]:
                        self.metric_history[metric_type][metric_name] = [
                            m for m in self.metric_history[metric_type][metric_name]
                            if datetime.fromisoformat(m["timestamp"]) > retention_limit
                        ]
                
                # Wait before next cleanup
                await asyncio.sleep(3600)  # Clean up every hour
                
            except Exception as e:
                self.logger.error(f"Error in metric cleanup: {str(e)}")
                await asyncio.sleep(3600)

# Global monitoring agent instance
monitoring_agent = DataMonitoringAgent()
