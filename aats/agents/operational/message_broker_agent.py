"""
Message Broker Agent Implementation
This agent handles message routing and communication between agents.
"""

from typing import Any, Dict, List, Optional, Set, Union
import asyncio
import logging
from datetime import datetime
import json
import uuid

from ..base_agent import BaseAgent, AgentConfig
from ...config.settings.base_config import config
from ...integration.databases.utils import db_utils

class MessageType(str):
    """Message type definitions"""
    COMMAND = "command"
    EVENT = "event"
    QUERY = "query"
    RESPONSE = "response"
    BROADCAST = "broadcast"

class MessagePriority(int):
    """Message priority levels"""
    LOW = 0
    MEDIUM = 1
    HIGH = 2
    CRITICAL = 3

class MessageBrokerAgent(BaseAgent):
    """
    Message Broker Agent responsible for handling message routing
    and communication between agents.
    """

    def __init__(self):
        super().__init__(AgentConfig(
            name="MessageBroker",
            description="Handles message routing and communication",
            capabilities=[
                "message_routing",
                "pub_sub_management",
                "queue_management",
                "protocol_handling"
            ],
            required_tools=[
                "message_router",
                "queue_manager",
                "protocol_handler"
            ],
            max_concurrent_tasks=20,
            priority_level=2
        ))
        self.message_queues: Dict[str, List[Dict]] = {}
        self.subscriptions: Dict[str, Set[str]] = {}
        self.routing_table: Dict[str, Dict] = {}
        self.message_history: List[Dict] = []

    async def initialize(self) -> bool:
        """Initialize the Message Broker Agent"""
        try:
            self.logger.info("Initializing Message Broker Agent...")
            
            # Initialize message queues
            await self._initialize_queues()
            
            # Initialize subscriptions
            await self._initialize_subscriptions()
            
            # Initialize routing
            await self._initialize_routing()
            
            self.logger.info("Message Broker Agent initialized successfully")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to initialize Message Broker Agent: {str(e)}")
            return False

    async def _initialize_queues(self) -> None:
        """Initialize message queues"""
        try:
            # Set up queue structure
            self.message_queues = {
                MessagePriority.CRITICAL: [],
                MessagePriority.HIGH: [],
                MessagePriority.MEDIUM: [],
                MessagePriority.LOW: []
            }
            
            # Set up dead letter queue
            self.dead_letter_queue = []
            
            # Load pending messages
            pending_messages = await db_utils.get_agent_state(
                self.id,
                "pending_messages"
            )
            
            if pending_messages:
                for message in pending_messages:
                    priority = message.get('priority', MessagePriority.MEDIUM)
                    self.message_queues[priority].append(message)
                    
        except Exception as e:
            raise Exception(f"Failed to initialize queues: {str(e)}")

    async def _initialize_subscriptions(self) -> None:
        """Initialize message subscriptions"""
        try:
            # Set up subscription registry
            self.subscriptions = {
                "commands": set(),
                "events": set(),
                "queries": set(),
                "broadcasts": set()
            }
            
            # Load stored subscriptions
            stored_subs = await db_utils.get_agent_state(
                self.id,
                "subscriptions"
            )
            
            if stored_subs:
                for topic, subscribers in stored_subs.items():
                    if topic in self.subscriptions:
                        self.subscriptions[topic].update(subscribers)
                        
        except Exception as e:
            raise Exception(f"Failed to initialize subscriptions: {str(e)}")

    async def _initialize_routing(self) -> None:
        """Initialize message routing"""
        try:
            # Set up routing table
            self.routing_table = {
                MessageType.COMMAND: {},
                MessageType.EVENT: {},
                MessageType.QUERY: {},
                MessageType.RESPONSE: {},
                MessageType.BROADCAST: {}
            }
            
            # Load routing rules
            stored_rules = await db_utils.get_agent_state(
                self.id,
                "routing_rules"
            )
            
            if stored_rules:
                self.routing_table.update(stored_rules)
                
        except Exception as e:
            raise Exception(f"Failed to initialize routing: {str(e)}")

    async def process_task(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process message broker tasks
        
        Args:
            task: Dictionary containing task details
            
        Returns:
            Dictionary containing the task result
        """
        try:
            task_type = task.get('type', 'unknown')
            self.logger.info(f"Processing task of type: {task_type}")

            # Handle different types of tasks
            handlers = {
                'route_message': self._handle_message_routing,
                'subscription': self._handle_subscription,
                'queue_management': self._handle_queue_management,
                'protocol_handling': self._handle_protocol_handling,
                'message_query': self._handle_message_query
            }

            handler = handlers.get(task_type, self._handle_unknown_task)
            result = await handler(task)

            # Log task completion
            await self._log_task_completion(task, result)

            return result

        except Exception as e:
            self.logger.error(f"Error processing task: {str(e)}")
            await self.handle_error(e, task)
            return {
                'success': False,
                'error': str(e),
                'task_id': task.get('id'),
                'timestamp': datetime.now().isoformat()
            }

    async def _handle_message_routing(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """Handle message routing tasks"""
        message = task.get('message')
        routing_options = task.get('routing_options', {})
        
        try:
            # Validate message
            validation = await self._validate_message(message)
            if not validation['valid']:
                return {
                    'success': False,
                    'errors': validation['errors'],
                    'timestamp': datetime.now().isoformat()
                }
            
            # Route message
            routing_result = await self._route_message(
                message,
                routing_options
            )
            
            return {
                'success': True,
                'message_id': message.get('id'),
                'routing_result': routing_result,
                'timestamp': datetime.now().isoformat()
            }
            
        except Exception as e:
            raise Exception(f"Message routing failed: {str(e)}")

    async def _handle_subscription(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """Handle subscription tasks"""
        operation = task.get('operation')
        topic = task.get('topic')
        subscriber = task.get('subscriber')
        
        try:
            if operation == "subscribe":
                result = await self._add_subscription(
                    topic,
                    subscriber
                )
            elif operation == "unsubscribe":
                result = await self._remove_subscription(
                    topic,
                    subscriber
                )
            else:
                raise ValueError(f"Unknown subscription operation: {operation}")
            
            return {
                'success': True,
                'operation': operation,
                'result': result,
                'timestamp': datetime.now().isoformat()
            }
            
        except Exception as e:
            raise Exception(f"Subscription handling failed: {str(e)}")

    async def _handle_queue_management(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """Handle queue management tasks"""
        operation = task.get('operation')
        queue_name = task.get('queue')
        parameters = task.get('parameters', {})
        
        try:
            if operation == "create":
                result = await self._create_queue(
                    queue_name,
                    parameters
                )
            elif operation == "delete":
                result = await self._delete_queue(queue_name)
            elif operation == "purge":
                result = await self._purge_queue(queue_name)
            else:
                raise ValueError(f"Unknown queue operation: {operation}")
            
            return {
                'success': True,
                'operation': operation,
                'result': result,
                'timestamp': datetime.now().isoformat()
            }
            
        except Exception as e:
            raise Exception(f"Queue management failed: {str(e)}")

    async def _route_message(
        self,
        message: Dict[str, Any],
        routing_options: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Route message to appropriate destinations"""
        try:
            message_type = message.get('type')
            priority = message.get('priority', MessagePriority.MEDIUM)
            
            # Get routing rules
            rules = self.routing_table.get(message_type, {})
            
            # Apply routing rules
            destinations = await self._apply_routing_rules(
                message,
                rules,
                routing_options
            )
            
            # Queue message for each destination
            delivery_status = {}
            for destination in destinations:
                status = await self._queue_message(
                    message,
                    destination,
                    priority
                )
                delivery_status[destination] = status
            
            # Update message history
            await self._update_message_history(
                message,
                destinations,
                delivery_status
            )
            
            return {
                "message_id": message.get('id'),
                "destinations": destinations,
                "delivery_status": delivery_status
            }
            
        except Exception as e:
            raise Exception(f"Message routing failed: {str(e)}")

    async def _apply_routing_rules(
        self,
        message: Dict[str, Any],
        rules: Dict[str, Any],
        options: Dict[str, Any]
    ) -> List[str]:
        """Apply routing rules to determine message destinations"""
        destinations = set()
        
        try:
            # Check direct routing
            if 'destination' in message:
                destinations.add(message['destination'])
            
            # Check topic subscriptions
            if 'topic' in message:
                subscribers = self.subscriptions.get(message['topic'], set())
                destinations.update(subscribers)
            
            # Apply routing rules
            for rule_name, rule in rules.items():
                if await self._evaluate_rule(message, rule):
                    rule_destinations = rule.get('destinations', [])
                    destinations.update(rule_destinations)
            
            # Apply routing options
            if options.get('broadcast', False):
                destinations.update(
                    self.subscriptions.get('broadcasts', set())
                )
            
            return list(destinations)
            
        except Exception as e:
            raise Exception(f"Failed to apply routing rules: {str(e)}")

    async def _queue_message(
        self,
        message: Dict[str, Any],
        destination: str,
        priority: int
    ) -> Dict[str, Any]:
        """Queue message for delivery"""
        try:
            # Prepare message for queuing
            queued_message = {
                **message,
                "destination": destination,
                "queued_at": datetime.now().isoformat(),
                "attempts": 0,
                "status": "queued"
            }
            
            # Add to appropriate queue
            self.message_queues[priority].append(queued_message)
            
            # Update queue metrics
            await self._update_queue_metrics(priority)
            
            return {
                "status": "queued",
                "queue": priority,
                "position": len(self.message_queues[priority])
            }
            
        except Exception as e:
            raise Exception(f"Failed to queue message: {str(e)}")

    async def _log_task_completion(
        self,
        task: Dict[str, Any],
        result: Dict[str, Any]
    ) -> None:
        """Log task completion"""
        event = {
            "timestamp": datetime.now().isoformat(),
            "task": task,
            "result": result,
            "success": result.get('success', False)
        }
        
        # Store event
        await db_utils.record_event(
            event_type="message_broker_task",
            data=event
        )

    async def handle_error(
        self,
        error: Exception,
        task: Optional[Dict[str, Any]] = None
    ) -> None:
        """Handle errors during task processing"""
        self.state.error_count += 1
        
        error_details = {
            'error_type': type(error).__name__,
            'error_message': str(error),
            'task_id': task.get('id') if task else None,
            'timestamp': datetime.now().isoformat()
        }
        
        # Log error
        self.logger.error(f"Error in Message Broker Agent: {error_details}")
        
        # Store error for analysis
        await self._store_error(error_details)
        
        # Handle message implications
        await self._handle_message_error(error_details)

    async def _store_error(self, error_details: Dict[str, Any]) -> None:
        """Store error details for analysis"""
        await db_utils.record_event(
            event_type="message_broker_error",
            data=error_details
        )

    async def _handle_message_error(self, error_details: Dict[str, Any]) -> None:
        """Handle message implications of errors"""
        try:
            # Check for message-related errors
            if any(term in str(error_details).lower() 
                  for term in ["message", "routing", "queue", "delivery"]):
                # Create message event
                await db_utils.record_event(
                    event_type="message_failure",
                    data=error_details
                )
                
                # Move failed message to dead letter queue
                if 'task_id' in error_details:
                    await self._move_to_dead_letter_queue(
                        error_details['task_id'],
                        error_details
                    )
            
        except Exception as e:
            self.logger.error(f"Failed to handle message error: {str(e)}")
