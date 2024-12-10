"""
Model Context Manager for AATS
Handles context windows, memory management, and conversation history
"""

import asyncio
import logging
from typing import Any, Dict, List, Optional, Set, Union, Deque
from datetime import datetime, timedelta
import json
from collections import deque

from .model_manager import ModelType
from ..config.settings.agent_model_config import MODEL_CAPABILITIES
from ..integration.databases.utils import db_utils

class ContextWindow:
    """Context window management"""
    def __init__(
        self,
        max_tokens: int,
        model_type: ModelType,
        retention_strategy: str = "sliding"
    ):
        self.max_tokens = max_tokens
        self.model_type = model_type
        self.retention_strategy = retention_strategy
        self.current_tokens = 0
        self.messages: Deque[Dict[str, Any]] = deque()
        self.metadata: Dict[str, Any] = {
            "created_at": datetime.now().isoformat(),
            "last_updated": None,
            "total_messages": 0,
            "dropped_messages": 0
        }

    def add_message(
        self,
        message: Dict[str, Any],
        token_count: int
    ) -> bool:
        """
        Add message to context window
        
        Args:
            message: Message to add
            token_count: Number of tokens in message
            
        Returns:
            bool: True if message was added successfully
        """
        if self.current_tokens + token_count > self.max_tokens:
            if self.retention_strategy == "sliding":
                # Remove oldest messages until there's space
                while (self.current_tokens + token_count > self.max_tokens and
                       self.messages):
                    removed = self.messages.popleft()
                    self.current_tokens -= removed.get("token_count", 0)
                    self.metadata["dropped_messages"] += 1
            else:
                return False

        self.messages.append({
            **message,
            "token_count": token_count,
            "timestamp": datetime.now().isoformat()
        })
        self.current_tokens += token_count
        self.metadata["total_messages"] += 1
        self.metadata["last_updated"] = datetime.now().isoformat()
        return True

    def get_context(
        self,
        max_tokens: Optional[int] = None,
        filter_func: Optional[callable] = None
    ) -> List[Dict[str, Any]]:
        """Get messages from context window"""
        if max_tokens is None:
            max_tokens = self.max_tokens

        messages = list(self.messages)
        if filter_func:
            messages = list(filter(filter_func, messages))

        # Return messages up to max_tokens
        result = []
        current_tokens = 0
        for message in reversed(messages):
            token_count = message.get("token_count", 0)
            if current_tokens + token_count > max_tokens:
                break
            result.append(message)
            current_tokens += token_count

        return list(reversed(result))

class ConversationMemory:
    """Conversation memory management"""
    def __init__(
        self,
        max_conversations: int = 100,
        retention_hours: int = 24
    ):
        self.max_conversations = max_conversations
        self.retention_hours = retention_hours
        self.conversations: Dict[str, List[Dict[str, Any]]] = {}
        self.metadata: Dict[str, Dict[str, Any]] = {}

    def add_conversation(
        self,
        conversation_id: str,
        messages: List[Dict[str, Any]]
    ) -> None:
        """Add conversation to memory"""
        self.conversations[conversation_id] = messages
        self.metadata[conversation_id] = {
            "created_at": datetime.now().isoformat(),
            "last_updated": datetime.now().isoformat(),
            "message_count": len(messages)
        }

        # Enforce conversation limit
        if len(self.conversations) > self.max_conversations:
            oldest = min(
                self.metadata.items(),
                key=lambda x: datetime.fromisoformat(x[1]["created_at"])
            )[0]
            del self.conversations[oldest]
            del self.metadata[oldest]

    def get_conversation(
        self,
        conversation_id: str
    ) -> Optional[List[Dict[str, Any]]]:
        """Get conversation from memory"""
        if conversation_id not in self.conversations:
            return None

        # Check retention period
        created_at = datetime.fromisoformat(
            self.metadata[conversation_id]["created_at"]
        )
        if datetime.now() - created_at > timedelta(hours=self.retention_hours):
            del self.conversations[conversation_id]
            del self.metadata[conversation_id]
            return None

        return self.conversations[conversation_id]

class ModelContextManager:
    """
    Model Context Manager responsible for handling context windows,
    memory management, and conversation history.
    """

    def __init__(self):
        self.logger = logging.getLogger("ModelContextManager")
        self.context_windows: Dict[str, ContextWindow] = {}
        self.conversation_memory = ConversationMemory()
        self.context_stats: Dict[str, Dict] = {}

    async def initialize(self) -> bool:
        """Initialize the Model Context Manager"""
        try:
            self.logger.info("Initializing Model Context Manager...")
            
            # Initialize context windows
            await self._initialize_context_windows()
            
            # Initialize statistics tracking
            await self._initialize_stats_tracking()
            
            # Start maintenance tasks
            self._start_maintenance_tasks()
            
            self.logger.info("Model Context Manager initialized successfully")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to initialize Model Context Manager: {str(e)}")
            return False

    async def _initialize_context_windows(self) -> None:
        """Initialize context windows for each model type"""
        try:
            for model_type in ModelType:
                capabilities = MODEL_CAPABILITIES[model_type]
                self.context_windows[model_type] = ContextWindow(
                    max_tokens=capabilities["context_window"],
                    model_type=model_type
                )
                
            # Initialize context statistics
            self.context_stats = {
                model_type: {
                    "total_messages": 0,
                    "total_tokens": 0,
                    "dropped_messages": 0,
                    "window_utilization": 0.0
                }
                for model_type in ModelType
            }
            
        except Exception as e:
            raise Exception(f"Failed to initialize context windows: {str(e)}")

    async def _initialize_stats_tracking(self) -> None:
        """Initialize statistics tracking"""
        try:
            # Load historical stats
            stored_stats = await db_utils.get_agent_state(
                "context_manager",
                "context_stats"
            )
            
            if stored_stats:
                self.context_stats.update(stored_stats)
                
        except Exception as e:
            raise Exception(f"Failed to initialize stats tracking: {str(e)}")

    def _start_maintenance_tasks(self) -> None:
        """Start maintenance tasks"""
        asyncio.create_task(self._run_context_maintenance())
        asyncio.create_task(self._run_memory_maintenance())

    async def add_to_context(
        self,
        model_type: ModelType,
        message: Dict[str, Any],
        token_count: int
    ) -> bool:
        """
        Add message to model's context window
        
        Args:
            model_type: Type of the model
            message: Message to add
            token_count: Number of tokens in message
            
        Returns:
            bool: True if message was added successfully
        """
        try:
            if model_type not in self.context_windows:
                raise ValueError(f"Unknown model type: {model_type}")
            
            window = self.context_windows[model_type]
            success = window.add_message(message, token_count)
            
            if success:
                # Update statistics
                stats = self.context_stats[model_type]
                stats["total_messages"] += 1
                stats["total_tokens"] += token_count
                stats["window_utilization"] = (
                    window.current_tokens / window.max_tokens
                )
                
                # Store metrics
                await self._store_context_metrics(
                    model_type,
                    message,
                    token_count
                )
            
            return success
            
        except Exception as e:
            self.logger.error(f"Failed to add to context: {str(e)}")
            return False

    async def get_context(
        self,
        model_type: ModelType,
        max_tokens: Optional[int] = None,
        filter_func: Optional[callable] = None
    ) -> List[Dict[str, Any]]:
        """
        Get context for model
        
        Args:
            model_type: Type of the model
            max_tokens: Optional maximum tokens to return
            filter_func: Optional filter function for messages
            
        Returns:
            List of context messages
        """
        try:
            if model_type not in self.context_windows:
                raise ValueError(f"Unknown model type: {model_type}")
            
            window = self.context_windows[model_type]
            return window.get_context(max_tokens, filter_func)
            
        except Exception as e:
            self.logger.error(f"Failed to get context: {str(e)}")
            return []

    async def store_conversation(
        self,
        conversation_id: str,
        messages: List[Dict[str, Any]]
    ) -> None:
        """
        Store conversation in memory
        
        Args:
            conversation_id: Unique conversation identifier
            messages: List of conversation messages
        """
        try:
            self.conversation_memory.add_conversation(
                conversation_id,
                messages
            )
            
            # Store conversation
            await self._store_conversation(
                conversation_id,
                messages
            )
            
        except Exception as e:
            self.logger.error(f"Failed to store conversation: {str(e)}")

    async def get_conversation(
        self,
        conversation_id: str
    ) -> Optional[List[Dict[str, Any]]]:
        """
        Get conversation from memory
        
        Args:
            conversation_id: Conversation identifier
            
        Returns:
            Optional list of conversation messages
        """
        try:
            return self.conversation_memory.get_conversation(conversation_id)
            
        except Exception as e:
            self.logger.error(f"Failed to get conversation: {str(e)}")
            return None

    async def _run_context_maintenance(self) -> None:
        """Run context maintenance tasks"""
        while True:
            try:
                for model_type, window in self.context_windows.items():
                    # Clean up old messages
                    current_time = datetime.now()
                    retention_limit = current_time - timedelta(hours=24)
                    
                    messages = window.get_context()
                    updated_messages = [
                        msg for msg in messages
                        if datetime.fromisoformat(msg["timestamp"]) > retention_limit
                    ]
                    
                    # Reset window with retained messages
                    window.messages.clear()
                    window.current_tokens = 0
                    for message in updated_messages:
                        window.add_message(
                            message,
                            message["token_count"]
                        )
                
                # Wait before next maintenance
                await asyncio.sleep(3600)  # Run every hour
                
            except Exception as e:
                self.logger.error(f"Error in context maintenance: {str(e)}")
                await asyncio.sleep(3600)

    async def _run_memory_maintenance(self) -> None:
        """Run memory maintenance tasks"""
        while True:
            try:
                # Clean up old conversations
                current_time = datetime.now()
                retention_limit = current_time - timedelta(
                    hours=self.conversation_memory.retention_hours
                )
                
                for conv_id in list(self.conversation_memory.conversations.keys()):
                    created_at = datetime.fromisoformat(
                        self.conversation_memory.metadata[conv_id]["created_at"]
                    )
                    if created_at < retention_limit:
                        del self.conversation_memory.conversations[conv_id]
                        del self.conversation_memory.metadata[conv_id]
                
                # Wait before next maintenance
                await asyncio.sleep(3600)  # Run every hour
                
            except Exception as e:
                self.logger.error(f"Error in memory maintenance: {str(e)}")
                await asyncio.sleep(3600)

    async def _store_context_metrics(
        self,
        model_type: ModelType,
        message: Dict[str, Any],
        token_count: int
    ) -> None:
        """Store context metrics"""
        try:
            await db_utils.record_metric(
                agent_id="context_manager",
                metric_type="context_usage",
                value=token_count,
                tags={
                    "model": model_type,
                    "message_type": message.get("type", "unknown"),
                    "window_utilization": self.context_stats[model_type]["window_utilization"]
                }
            )
            
        except Exception as e:
            self.logger.error(f"Failed to store context metrics: {str(e)}")

    async def _store_conversation(
        self,
        conversation_id: str,
        messages: List[Dict[str, Any]]
    ) -> None:
        """Store conversation"""
        try:
            await db_utils.record_event(
                event_type="conversation_stored",
                data={
                    "conversation_id": conversation_id,
                    "message_count": len(messages),
                    "timestamp": datetime.now().isoformat()
                }
            )
            
        except Exception as e:
            self.logger.error(f"Failed to store conversation: {str(e)}")

# Global context manager instance
context_manager = ModelContextManager()
