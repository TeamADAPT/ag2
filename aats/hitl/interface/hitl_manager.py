"""
HITL (Human-In-The-Loop) Manager for AATS
Handles human interaction and oversight for the agent team.
"""

import asyncio
import logging
from typing import Any, Dict, List, Optional, Set, Callable
from datetime import datetime
from enum import Enum
import json

from ...config.settings.agent_team_config import HITL_INTEGRATION
from ...config.settings.base_config import config

class ApprovalStatus(str, Enum):
    """Status of HITL approval requests"""
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    TIMEOUT = "timeout"

class NotificationPriority(str, Enum):
    """Priority levels for HITL notifications"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"

class HITLRequest:
    """Represents a request requiring human intervention"""
    def __init__(
        self,
        request_id: str,
        request_type: str,
        description: str,
        priority: NotificationPriority,
        data: Dict[str, Any],
        timeout: int = 300  # Default 5 minutes
    ):
        self.request_id = request_id
        self.request_type = request_type
        self.description = description
        self.priority = priority
        self.data = data
        self.timeout = timeout
        self.status = ApprovalStatus.PENDING
        self.created_at = datetime.now()
        self.responded_at: Optional[datetime] = None
        self.response: Optional[Dict[str, Any]] = None
        self.feedback: Optional[str] = None

class HITLManager:
    """
    Manages human-in-the-loop interactions for the agent team.
    Provides interfaces for approval requests, notifications,
    and monitoring of agent activities.
    """

    def __init__(self):
        self.logger = logging.getLogger("HITLManager")
        self.pending_requests: Dict[str, HITLRequest] = {}
        self.notification_handlers: Dict[str, List[Callable]] = {}
        self.monitoring_data: Dict[str, List[Dict[str, Any]]] = {}
        self.active_sessions: Set[str] = set()
        self._request_counter = 0
        self._initialize_notification_handlers()

    def _initialize_notification_handlers(self) -> None:
        """Initialize handlers for different notification types"""
        # Setup handlers for required notification types
        for notification_type in HITL_INTEGRATION["notification_required"]:
            self.notification_handlers[notification_type] = []

    async def request_approval(
        self,
        request_type: str,
        description: str,
        data: Dict[str, Any],
        priority: NotificationPriority = NotificationPriority.MEDIUM,
        timeout: int = 300
    ) -> Dict[str, Any]:
        """
        Request human approval for a specific action
        
        Args:
            request_type: Type of request requiring approval
            description: Human-readable description of the request
            data: Additional data relevant to the request
            priority: Priority level of the request
            timeout: Time in seconds to wait for response
            
        Returns:
            Dictionary containing approval status and any feedback
        """
        # Validate request type
        if request_type not in HITL_INTEGRATION["approval_required"]:
            raise ValueError(f"Invalid approval request type: {request_type}")

        # Create request
        request_id = self._generate_request_id()
        request = HITLRequest(
            request_id=request_id,
            request_type=request_type,
            description=description,
            priority=priority,
            data=data,
            timeout=timeout
        )
        
        self.pending_requests[request_id] = request
        
        # Notify human operators
        await self._notify_operators(request)
        
        # Wait for response
        try:
            response = await self._wait_for_response(request)
            return response
        except asyncio.TimeoutError:
            request.status = ApprovalStatus.TIMEOUT
            return {
                "status": ApprovalStatus.TIMEOUT,
                "request_id": request_id,
                "message": "Request timed out waiting for human approval"
            }

    async def submit_response(
        self,
        request_id: str,
        approved: bool,
        feedback: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Submit human response to an approval request
        
        Args:
            request_id: ID of the request being responded to
            approved: Whether the request is approved
            feedback: Optional feedback or explanation
            
        Returns:
            Dictionary containing the updated request status
        """
        if request_id not in self.pending_requests:
            raise ValueError(f"Invalid request ID: {request_id}")

        request = self.pending_requests[request_id]
        request.status = ApprovalStatus.APPROVED if approved else ApprovalStatus.REJECTED
        request.responded_at = datetime.now()
        request.feedback = feedback
        
        response = {
            "status": request.status,
            "request_id": request_id,
            "feedback": feedback,
            "response_time": (request.responded_at - request.created_at).total_seconds()
        }
        
        request.response = response
        
        # Log the response
        await self._log_response(request)
        
        return response

    async def send_notification(
        self,
        notification_type: str,
        message: str,
        data: Dict[str, Any],
        priority: NotificationPriority = NotificationPriority.MEDIUM
    ) -> None:
        """
        Send a notification to human operators
        
        Args:
            notification_type: Type of notification
            message: Notification message
            data: Additional data relevant to the notification
            priority: Priority level of the notification
        """
        if notification_type not in HITL_INTEGRATION["notification_required"]:
            raise ValueError(f"Invalid notification type: {notification_type}")

        notification = {
            "id": self._generate_notification_id(),
            "type": notification_type,
            "message": message,
            "data": data,
            "priority": priority,
            "timestamp": datetime.now().isoformat()
        }

        # Execute notification handlers
        for handler in self.notification_handlers.get(notification_type, []):
            try:
                await handler(notification)
            except Exception as e:
                self.logger.error(f"Error in notification handler: {str(e)}")

        # Log notification
        await self._log_notification(notification)

    async def register_monitoring(
        self,
        monitoring_type: str,
        callback: Callable[[Dict[str, Any]], None]
    ) -> None:
        """
        Register a callback for monitoring specific activities
        
        Args:
            monitoring_type: Type of activity to monitor
            callback: Callback function to handle monitoring data
        """
        if monitoring_type not in HITL_INTEGRATION["monitoring_required"]:
            raise ValueError(f"Invalid monitoring type: {monitoring_type}")

        if monitoring_type not in self.notification_handlers:
            self.notification_handlers[monitoring_type] = []
            
        self.notification_handlers[monitoring_type].append(callback)

    async def submit_monitoring_data(
        self,
        monitoring_type: str,
        data: Dict[str, Any]
    ) -> None:
        """
        Submit data for human monitoring
        
        Args:
            monitoring_type: Type of monitoring data
            data: Monitoring data to submit
        """
        if monitoring_type not in HITL_INTEGRATION["monitoring_required"]:
            raise ValueError(f"Invalid monitoring type: {monitoring_type}")

        monitoring_entry = {
            "timestamp": datetime.now().isoformat(),
            "type": monitoring_type,
            "data": data
        }

        # Store monitoring data
        if monitoring_type not in self.monitoring_data:
            self.monitoring_data[monitoring_type] = []
        self.monitoring_data[monitoring_type].append(monitoring_entry)

        # Execute monitoring callbacks
        for handler in self.notification_handlers.get(monitoring_type, []):
            try:
                await handler(monitoring_entry)
            except Exception as e:
                self.logger.error(f"Error in monitoring handler: {str(e)}")

    async def get_monitoring_data(
        self,
        monitoring_type: str,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None
    ) -> List[Dict[str, Any]]:
        """
        Retrieve monitoring data for a specific type and time range
        
        Args:
            monitoring_type: Type of monitoring data to retrieve
            start_time: Optional start time for filtering data
            end_time: Optional end time for filtering data
            
        Returns:
            List of monitoring data entries
        """
        if monitoring_type not in self.monitoring_data:
            return []

        data = self.monitoring_data[monitoring_type]
        
        if start_time or end_time:
            filtered_data = []
            for entry in data:
                entry_time = datetime.fromisoformat(entry["timestamp"])
                if start_time and entry_time < start_time:
                    continue
                if end_time and entry_time > end_time:
                    continue
                filtered_data.append(entry)
            return filtered_data
            
        return data

    def _generate_request_id(self) -> str:
        """Generate a unique request ID"""
        self._request_counter += 1
        return f"req_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{self._request_counter}"

    def _generate_notification_id(self) -> str:
        """Generate a unique notification ID"""
        return f"notif_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{id(datetime.now())}"

    async def _notify_operators(self, request: HITLRequest) -> None:
        """Notify human operators of a new request"""
        notification = {
            "type": "approval_request",
            "request_id": request.request_id,
            "request_type": request.request_type,
            "description": request.description,
            "priority": request.priority,
            "created_at": request.created_at.isoformat(),
            "timeout": request.timeout
        }

        # TODO: Implement actual notification delivery (e.g., Slack, email, etc.)
        self.logger.info(f"New approval request: {json.dumps(notification, indent=2)}")

    async def _wait_for_response(self, request: HITLRequest) -> Dict[str, Any]:
        """Wait for human response to a request"""
        try:
            # Wait for status change or timeout
            timeout = request.timeout if request.timeout > 0 else 300
            end_time = datetime.now().timestamp() + timeout
            
            while datetime.now().timestamp() < end_time:
                if request.status != ApprovalStatus.PENDING:
                    return request.response or {
                        "status": request.status,
                        "request_id": request.request_id
                    }
                await asyncio.sleep(1)
                
            raise asyncio.TimeoutError()
            
        except asyncio.TimeoutError:
            request.status = ApprovalStatus.TIMEOUT
            return {
                "status": ApprovalStatus.TIMEOUT,
                "request_id": request.request_id,
                "message": "Request timed out waiting for human approval"
            }

    async def _log_response(self, request: HITLRequest) -> None:
        """Log human response to a request"""
        log_entry = {
            "timestamp": datetime.now().isoformat(),
            "request_id": request.request_id,
            "request_type": request.request_type,
            "status": request.status,
            "response_time": (request.responded_at - request.created_at).total_seconds(),
            "feedback": request.feedback
        }
        
        # TODO: Implement actual logging (e.g., to database or file)
        self.logger.info(f"Request response logged: {json.dumps(log_entry, indent=2)}")

    async def _log_notification(self, notification: Dict[str, Any]) -> None:
        """Log a sent notification"""
        # TODO: Implement actual logging (e.g., to database or file)
        self.logger.info(f"Notification logged: {json.dumps(notification, indent=2)}")
