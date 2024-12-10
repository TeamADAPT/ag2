"""
System Monitor for AATS
Tracks agent performance, system health, and resource utilization.
"""

import asyncio
import logging
import psutil
import time
from typing import Dict, List, Optional, Set
from datetime import datetime
from collections import defaultdict
import json

from ...config.settings.agent_team_config import (
    PERFORMANCE_METRICS,
    SYSTEM_BOUNDARIES
)
from ...hitl.interface.hitl_manager import HITLManager, NotificationPriority

class MetricType:
    """Types of metrics tracked by the system"""
    PERFORMANCE = "performance"
    RESOURCE = "resource"
    HEALTH = "health"
    ERROR = "error"

class SystemMonitor:
    """
    Monitors system performance, health, and resource utilization.
    Provides real-time metrics and alerts for both agents and human operators.
    """

    def __init__(self, hitl_manager: HITLManager):
        self.logger = logging.getLogger("SystemMonitor")
        self.hitl_manager = hitl_manager
        self.metrics: Dict[str, Dict] = defaultdict(dict)
        self.alerts: List[Dict] = []
        self.active_agents: Set[str] = set()
        self._monitoring = False
        self._last_check = defaultdict(float)
        self._metric_history: Dict[str, List[Dict]] = defaultdict(list)

    async def start_monitoring(self) -> None:
        """Start the monitoring system"""
        if self._monitoring:
            return

        self._monitoring = True
        self.logger.info("Starting system monitoring")

        # Start monitoring tasks
        monitoring_tasks = [
            self._monitor_system_resources(),
            self._monitor_agent_performance(),
            self._monitor_system_health(),
            self._monitor_error_rates()
        ]

        # Run all monitoring tasks
        await asyncio.gather(*monitoring_tasks)

    async def stop_monitoring(self) -> None:
        """Stop the monitoring system"""
        self._monitoring = False
        self.logger.info("Stopping system monitoring")

    async def register_agent(self, agent_name: str) -> None:
        """Register an agent for monitoring"""
        self.active_agents.add(agent_name)
        self.metrics[MetricType.PERFORMANCE][agent_name] = {
            "response_time": [],
            "success_rate": 0,
            "task_count": 0,
            "error_count": 0
        }

    async def unregister_agent(self, agent_name: str) -> None:
        """Unregister an agent from monitoring"""
        self.active_agents.remove(agent_name)
        if agent_name in self.metrics[MetricType.PERFORMANCE]:
            del self.metrics[MetricType.PERFORMANCE][agent_name]

    async def record_metric(
        self,
        metric_type: str,
        metric_name: str,
        value: float,
        agent_name: Optional[str] = None
    ) -> None:
        """Record a metric value"""
        timestamp = datetime.now()
        
        metric_data = {
            "timestamp": timestamp.isoformat(),
            "value": value,
            "agent": agent_name
        }

        # Store metric
        if agent_name:
            if agent_name not in self.metrics[metric_type]:
                self.metrics[metric_type][agent_name] = {}
            self.metrics[metric_type][agent_name][metric_name] = value
        else:
            self.metrics[metric_type][metric_name] = value

        # Store in history
        history_key = f"{metric_type}.{metric_name}"
        if agent_name:
            history_key = f"{history_key}.{agent_name}"
        self._metric_history[history_key].append(metric_data)

        # Check thresholds
        await self._check_thresholds(metric_type, metric_name, value, agent_name)

    async def get_metrics(
        self,
        metric_type: Optional[str] = None,
        agent_name: Optional[str] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None
    ) -> Dict:
        """Get recorded metrics"""
        if metric_type and metric_type not in self.metrics:
            return {}

        result = {}
        metrics_to_check = [metric_type] if metric_type else self.metrics.keys()

        for mtype in metrics_to_check:
            if agent_name:
                if agent_name in self.metrics[mtype]:
                    result[mtype] = {
                        agent_name: self.metrics[mtype][agent_name]
                    }
            else:
                result[mtype] = self.metrics[mtype]

        # Apply time filtering if specified
        if start_time or end_time:
            filtered_result = {}
            for mtype in result:
                filtered_result[mtype] = {}
                for key, values in result[mtype].items():
                    if isinstance(values, list):
                        filtered_values = []
                        for value in values:
                            timestamp = datetime.fromisoformat(value["timestamp"])
                            if start_time and timestamp < start_time:
                                continue
                            if end_time and timestamp > end_time:
                                continue
                            filtered_values.append(value)
                        filtered_result[mtype][key] = filtered_values
                    else:
                        filtered_result[mtype][key] = values
            return filtered_result

        return result

    async def get_alerts(
        self,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None
    ) -> List[Dict]:
        """Get recorded alerts"""
        if not (start_time or end_time):
            return self.alerts

        filtered_alerts = []
        for alert in self.alerts:
            timestamp = datetime.fromisoformat(alert["timestamp"])
            if start_time and timestamp < start_time:
                continue
            if end_time and timestamp > end_time:
                continue
            filtered_alerts.append(alert)
        return filtered_alerts

    async def _monitor_system_resources(self) -> None:
        """Monitor system resource utilization"""
        while self._monitoring:
            try:
                # CPU usage
                cpu_percent = psutil.cpu_percent(interval=1)
                await self.record_metric(
                    MetricType.RESOURCE,
                    "cpu_usage",
                    cpu_percent
                )

                # Memory usage
                memory = psutil.virtual_memory()
                await self.record_metric(
                    MetricType.RESOURCE,
                    "memory_usage",
                    memory.percent
                )

                # Disk usage
                disk = psutil.disk_usage('/')
                await self.record_metric(
                    MetricType.RESOURCE,
                    "disk_usage",
                    disk.percent
                )

                # Network I/O
                network = psutil.net_io_counters()
                await self.record_metric(
                    MetricType.RESOURCE,
                    "network_bytes_sent",
                    network.bytes_sent
                )
                await self.record_metric(
                    MetricType.RESOURCE,
                    "network_bytes_recv",
                    network.bytes_recv
                )

                await asyncio.sleep(5)  # Check every 5 seconds

            except Exception as e:
                self.logger.error(f"Error monitoring system resources: {str(e)}")
                await asyncio.sleep(5)  # Wait before retrying

    async def _monitor_agent_performance(self) -> None:
        """Monitor individual agent performance"""
        while self._monitoring:
            try:
                for agent_name in self.active_agents:
                    # Calculate average response time
                    response_times = self.metrics[MetricType.PERFORMANCE][agent_name]["response_time"]
                    if response_times:
                        avg_response_time = sum(response_times) / len(response_times)
                        await self.record_metric(
                            MetricType.PERFORMANCE,
                            "avg_response_time",
                            avg_response_time,
                            agent_name
                        )

                    # Calculate success rate
                    task_count = self.metrics[MetricType.PERFORMANCE][agent_name]["task_count"]
                    error_count = self.metrics[MetricType.PERFORMANCE][agent_name]["error_count"]
                    if task_count > 0:
                        success_rate = (task_count - error_count) / task_count * 100
                        await self.record_metric(
                            MetricType.PERFORMANCE,
                            "success_rate",
                            success_rate,
                            agent_name
                        )

                await asyncio.sleep(10)  # Check every 10 seconds

            except Exception as e:
                self.logger.error(f"Error monitoring agent performance: {str(e)}")
                await asyncio.sleep(10)  # Wait before retrying

    async def _monitor_system_health(self) -> None:
        """Monitor overall system health"""
        while self._monitoring:
            try:
                # Check agent responsiveness
                for agent_name in self.active_agents:
                    last_response = self._last_check.get(f"response_{agent_name}", 0)
                    if time.time() - last_response > 60:  # No response in 1 minute
                        await self._create_alert(
                            "agent_unresponsive",
                            f"Agent {agent_name} is unresponsive",
                            NotificationPriority.HIGH
                        )

                # Check resource thresholds
                resource_metrics = self.metrics.get(MetricType.RESOURCE, {})
                
                # CPU check
                if resource_metrics.get("cpu_usage", 0) > SYSTEM_BOUNDARIES["resource_limits"]["max_cpu_usage"] * 100:
                    await self._create_alert(
                        "high_cpu_usage",
                        "CPU usage exceeds threshold",
                        NotificationPriority.HIGH
                    )

                # Memory check
                if resource_metrics.get("memory_usage", 0) > SYSTEM_BOUNDARIES["resource_limits"]["max_memory_usage"] * 100:
                    await self._create_alert(
                        "high_memory_usage",
                        "Memory usage exceeds threshold",
                        NotificationPriority.HIGH
                    )

                await asyncio.sleep(30)  # Check every 30 seconds

            except Exception as e:
                self.logger.error(f"Error monitoring system health: {str(e)}")
                await asyncio.sleep(30)  # Wait before retrying

    async def _monitor_error_rates(self) -> None:
        """Monitor error rates across the system"""
        while self._monitoring:
            try:
                for agent_name in self.active_agents:
                    error_count = self.metrics[MetricType.PERFORMANCE][agent_name]["error_count"]
                    task_count = self.metrics[MetricType.PERFORMANCE][agent_name]["task_count"]
                    
                    if task_count > 0:
                        error_rate = error_count / task_count * 100
                        if error_rate > 10:  # More than 10% error rate
                            await self._create_alert(
                                "high_error_rate",
                                f"High error rate detected for agent {agent_name}",
                                NotificationPriority.HIGH
                            )

                await asyncio.sleep(60)  # Check every minute

            except Exception as e:
                self.logger.error(f"Error monitoring error rates: {str(e)}")
                await asyncio.sleep(60)  # Wait before retrying

    async def _check_thresholds(
        self,
        metric_type: str,
        metric_name: str,
        value: float,
        agent_name: Optional[str] = None
    ) -> None:
        """Check if metric value exceeds defined thresholds"""
        try:
            if metric_type == MetricType.PERFORMANCE:
                thresholds = PERFORMANCE_METRICS.get(metric_name)
                if thresholds:
                    if value > thresholds.get("critical", float('inf')):
                        await self._create_alert(
                            f"critical_{metric_name}",
                            f"Critical {metric_name} threshold exceeded" + 
                            (f" for agent {agent_name}" if agent_name else ""),
                            NotificationPriority.CRITICAL
                        )
                    elif value > thresholds.get("high", float('inf')):
                        await self._create_alert(
                            f"high_{metric_name}",
                            f"High {metric_name} threshold exceeded" +
                            (f" for agent {agent_name}" if agent_name else ""),
                            NotificationPriority.HIGH
                        )

            elif metric_type == MetricType.RESOURCE:
                resource_limits = SYSTEM_BOUNDARIES["resource_limits"]
                threshold = resource_limits.get(f"max_{metric_name}", None)
                if threshold and value > threshold * 100:
                    await self._create_alert(
                        f"high_{metric_name}",
                        f"Resource limit exceeded for {metric_name}",
                        NotificationPriority.HIGH
                    )

        except Exception as e:
            self.logger.error(f"Error checking thresholds: {str(e)}")

    async def _create_alert(
        self,
        alert_type: str,
        message: str,
        priority: NotificationPriority
    ) -> None:
        """Create and handle a system alert"""
        alert = {
            "type": alert_type,
            "message": message,
            "priority": priority,
            "timestamp": datetime.now().isoformat()
        }

        # Store alert
        self.alerts.append(alert)

        # Notify HITL system
        await self.hitl_manager.send_notification(
            "system_alert",
            message,
            alert,
            priority
        )

        # Log alert
        self.logger.warning(f"System Alert: {json.dumps(alert, indent=2)}")
