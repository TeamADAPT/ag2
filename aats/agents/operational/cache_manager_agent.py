"""
Cache Manager Agent Implementation
This agent handles caching strategies and cache management across the system.
"""

from typing import Any, Dict, List, Optional, Set, Union
import asyncio
import logging
from datetime import datetime, timedelta
import json
import hashlib

from ..base_agent import BaseAgent, AgentConfig
from ...config.settings.base_config import config
from ...integration.databases.utils import db_utils

class CacheStrategy(str):
    """Cache strategy definitions"""
    LRU = "lru"  # Least Recently Used
    LFU = "lfu"  # Least Frequently Used
    FIFO = "fifo"  # First In First Out
    TTL = "ttl"  # Time To Live
    ADAPTIVE = "adaptive"  # Adaptive caching

class CacheLevel(str):
    """Cache level definitions"""
    L1 = "l1"  # Memory cache
    L2 = "l2"  # Redis cache
    L3 = "l3"  # Distributed cache

class CacheManagerAgent(BaseAgent):
    """
    Cache Manager Agent responsible for handling caching strategies
    and cache management across the system.
    """

    def __init__(self):
        super().__init__(AgentConfig(
            name="CacheManager",
            description="Handles caching and cache management",
            capabilities=[
                "cache_management",
                "strategy_optimization",
                "invalidation_control",
                "performance_monitoring"
            ],
            required_tools=[
                "cache_controller",
                "strategy_optimizer",
                "performance_monitor"
            ],
            max_concurrent_tasks=10,
            priority_level=2
        ))
        self.cache_config: Dict[str, Dict] = {}
        self.cache_stats: Dict[str, Dict] = {}
        self.invalidation_rules: Dict[str, Dict] = {}
        self.cache_metrics: Dict[str, List[Dict]] = {}

    async def initialize(self) -> bool:
        """Initialize the Cache Manager Agent"""
        try:
            self.logger.info("Initializing Cache Manager Agent...")
            
            # Initialize cache configuration
            await self._initialize_cache_config()
            
            # Initialize cache statistics
            await self._initialize_cache_stats()
            
            # Initialize invalidation rules
            await self._initialize_invalidation_rules()
            
            self.logger.info("Cache Manager Agent initialized successfully")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to initialize Cache Manager Agent: {str(e)}")
            return False

    async def _initialize_cache_config(self) -> None:
        """Initialize cache configuration"""
        try:
            # Set up cache configuration
            self.cache_config = {
                CacheLevel.L1: {
                    "strategy": CacheStrategy.LRU,
                    "max_size_mb": 256,
                    "ttl_seconds": 300,
                    "enabled": True
                },
                CacheLevel.L2: {
                    "strategy": CacheStrategy.LFU,
                    "max_size_mb": 1024,
                    "ttl_seconds": 3600,
                    "enabled": True
                },
                CacheLevel.L3: {
                    "strategy": CacheStrategy.ADAPTIVE,
                    "max_size_mb": 4096,
                    "ttl_seconds": 86400,
                    "enabled": True
                }
            }
            
            # Load custom configuration
            custom_config = await db_utils.get_agent_state(
                self.id,
                "cache_config"
            )
            
            if custom_config:
                self._merge_config(custom_config)
                
        except Exception as e:
            raise Exception(f"Failed to initialize cache configuration: {str(e)}")

    async def _initialize_cache_stats(self) -> None:
        """Initialize cache statistics"""
        try:
            # Set up statistics tracking
            self.cache_stats = {
                cache_level: {
                    "hits": 0,
                    "misses": 0,
                    "evictions": 0,
                    "size_bytes": 0,
                    "items": 0,
                    "last_cleanup": None
                }
                for cache_level in CacheLevel.__dict__.keys()
                if not cache_level.startswith('_')
            }
            
            # Load stored statistics
            stored_stats = await db_utils.get_agent_state(
                self.id,
                "cache_stats"
            )
            
            if stored_stats:
                self._merge_stats(stored_stats)
                
        except Exception as e:
            raise Exception(f"Failed to initialize cache statistics: {str(e)}")

    async def _initialize_invalidation_rules(self) -> None:
        """Initialize cache invalidation rules"""
        try:
            # Set up invalidation rules
            self.invalidation_rules = {
                "time_based": {
                    "enabled": True,
                    "check_interval_seconds": 60,
                    "rules": {
                        "expired": "ttl_seconds > 0",
                        "stale": "last_access < now() - stale_threshold"
                    }
                },
                "event_based": {
                    "enabled": True,
                    "events": {
                        "data_update": ["related_keys", "pattern_match"],
                        "config_change": ["config_keys"],
                        "system_alert": ["affected_keys"]
                    }
                },
                "size_based": {
                    "enabled": True,
                    "thresholds": {
                        "memory_percent": 80,
                        "items_count": 1000000
                    }
                }
            }
            
            # Load custom rules
            custom_rules = await db_utils.get_agent_state(
                self.id,
                "invalidation_rules"
            )
            
            if custom_rules:
                self._merge_rules(custom_rules)
                
        except Exception as e:
            raise Exception(f"Failed to initialize invalidation rules: {str(e)}")

    async def process_task(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process cache management tasks
        
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
                'cache_operation': self._handle_cache_operation,
                'strategy_management': self._handle_strategy_management,
                'invalidation': self._handle_invalidation,
                'monitoring': self._handle_monitoring,
                'optimization': self._handle_optimization
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

    async def _handle_cache_operation(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """Handle cache operation tasks"""
        operation = task.get('operation')
        key = task.get('key')
        value = task.get('value')
        level = task.get('level', CacheLevel.L1)
        options = task.get('options', {})
        
        try:
            if operation == "get":
                result = await self._get_cached_value(
                    key,
                    level,
                    options
                )
            elif operation == "set":
                result = await self._set_cached_value(
                    key,
                    value,
                    level,
                    options
                )
            elif operation == "delete":
                result = await self._delete_cached_value(
                    key,
                    level
                )
            else:
                raise ValueError(f"Unknown cache operation: {operation}")
            
            return {
                'success': True,
                'operation': operation,
                'result': result,
                'timestamp': datetime.now().isoformat()
            }
            
        except Exception as e:
            raise Exception(f"Cache operation failed: {str(e)}")

    async def _handle_strategy_management(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """Handle cache strategy management tasks"""
        operation = task.get('operation')
        level = task.get('level')
        strategy = task.get('strategy')
        parameters = task.get('parameters', {})
        
        try:
            if operation == "update":
                result = await self._update_strategy(
                    level,
                    strategy,
                    parameters
                )
            elif operation == "analyze":
                result = await self._analyze_strategy(
                    level,
                    strategy
                )
            elif operation == "optimize":
                result = await self._optimize_strategy(
                    level,
                    strategy,
                    parameters
                )
            else:
                raise ValueError(f"Unknown strategy operation: {operation}")
            
            return {
                'success': True,
                'operation': operation,
                'result': result,
                'timestamp': datetime.now().isoformat()
            }
            
        except Exception as e:
            raise Exception(f"Strategy management failed: {str(e)}")

    async def _get_cached_value(
        self,
        key: str,
        level: str,
        options: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Get value from cache"""
        try:
            # Generate cache key
            cache_key = self._generate_cache_key(key)
            
            # Check cache level configuration
            if not self.cache_config[level]["enabled"]:
                return {
                    "found": False,
                    "reason": "Cache level disabled"
                }
            
            # Get from cache
            cached_data = await self._get_from_cache(
                cache_key,
                level
            )
            
            if cached_data:
                # Update statistics
                await self._update_cache_stats(
                    level,
                    "hits"
                )
                
                return {
                    "found": True,
                    "value": cached_data["value"],
                    "metadata": cached_data["metadata"]
                }
            
            # Update statistics
            await self._update_cache_stats(
                level,
                "misses"
            )
            
            return {
                "found": False,
                "reason": "Cache miss"
            }
            
        except Exception as e:
            raise Exception(f"Cache get operation failed: {str(e)}")

    async def _set_cached_value(
        self,
        key: str,
        value: Any,
        level: str,
        options: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Set value in cache"""
        try:
            # Generate cache key
            cache_key = self._generate_cache_key(key)
            
            # Check cache level configuration
            if not self.cache_config[level]["enabled"]:
                return {
                    "stored": False,
                    "reason": "Cache level disabled"
                }
            
            # Prepare cache entry
            cache_entry = {
                "key": cache_key,
                "value": value,
                "metadata": {
                    "created_at": datetime.now().isoformat(),
                    "ttl": options.get(
                        "ttl_seconds",
                        self.cache_config[level]["ttl_seconds"]
                    ),
                    "size_bytes": len(str(value))
                }
            }
            
            # Check size limits
            if not self._check_size_limits(level, cache_entry):
                # Trigger cleanup if needed
                await self._cleanup_cache(level)
            
            # Store in cache
            await self._store_in_cache(
                cache_entry,
                level
            )
            
            # Update statistics
            await self._update_cache_stats(
                level,
                "items",
                1
            )
            
            return {
                "stored": True,
                "metadata": cache_entry["metadata"]
            }
            
        except Exception as e:
            raise Exception(f"Cache set operation failed: {str(e)}")

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
            event_type="cache_task",
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
        self.logger.error(f"Error in Cache Manager Agent: {error_details}")
        
        # Store error for analysis
        await self._store_error(error_details)
        
        # Handle cache implications
        await self._handle_cache_error(error_details)

    async def _store_error(self, error_details: Dict[str, Any]) -> None:
        """Store error details for analysis"""
        await db_utils.record_event(
            event_type="cache_error",
            data=error_details
        )

    async def _handle_cache_error(self, error_details: Dict[str, Any]) -> None:
        """Handle cache implications of errors"""
        try:
            # Check for cache-related errors
            if any(term in str(error_details).lower() 
                  for term in ["cache", "memory", "storage", "eviction"]):
                # Create cache event
                await db_utils.record_event(
                    event_type="cache_failure",
                    data=error_details
                )
                
                # Trigger cache maintenance
                await self._trigger_cache_maintenance(error_details)
            
        except Exception as e:
            self.logger.error(f"Failed to handle cache error: {str(e)}")
