"""
Search Specialist Agent Implementation
This agent handles search operations and information retrieval across the system.
"""

from typing import Any, Dict, List, Optional, Set, Union
import asyncio
import logging
from datetime import datetime
import json
from pathlib import Path
import re

from ..base_agent import BaseAgent, AgentConfig
from ...config.settings.base_config import config
from ...integration.databases.utils import db_utils

class SearchType(str):
    """Search type definitions"""
    EXACT = "exact"
    FUZZY = "fuzzy"
    SEMANTIC = "semantic"
    REGEX = "regex"
    VECTOR = "vector"

class SearchScope(str):
    """Search scope definitions"""
    ALL = "all"
    CODE = "code"
    DOCS = "docs"
    KNOWLEDGE = "knowledge"
    LOGS = "logs"

class SearchSpecialistAgent(BaseAgent):
    """
    Search Specialist Agent responsible for handling search operations
    and information retrieval across the system.
    """

    def __init__(self):
        super().__init__(AgentConfig(
            name="SearchSpecialist",
            description="Handles search and information retrieval",
            capabilities=[
                "search_operations",
                "information_retrieval",
                "index_management",
                "query_optimization"
            ],
            required_tools=[
                "search_engine",
                "index_manager",
                "query_optimizer"
            ],
            max_concurrent_tasks=10,
            priority_level=2
        ))
        self.search_indexes: Dict[str, Dict] = {}
        self.query_cache: Dict[str, Dict] = {}
        self.search_history: List[Dict] = []
        self.optimization_rules: Dict[str, Dict] = {}

    async def initialize(self) -> bool:
        """Initialize the Search Specialist Agent"""
        try:
            self.logger.info("Initializing Search Specialist Agent...")
            
            # Initialize search indexes
            await self._initialize_indexes()
            
            # Initialize query optimization
            await self._initialize_optimization()
            
            # Initialize caching system
            await self._initialize_caching()
            
            self.logger.info("Search Specialist Agent initialized successfully")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to initialize Search Specialist Agent: {str(e)}")
            return False

    async def _initialize_indexes(self) -> None:
        """Initialize search indexes"""
        try:
            # Set up index structure
            self.search_indexes = {
                SearchScope.CODE: {
                    "type": "inverted_index",
                    "fields": ["content", "filename", "language", "path"],
                    "analyzer": "code"
                },
                SearchScope.DOCS: {
                    "type": "inverted_index",
                    "fields": ["content", "title", "tags", "path"],
                    "analyzer": "text"
                },
                SearchScope.KNOWLEDGE: {
                    "type": "vector_index",
                    "fields": ["content", "metadata", "relationships"],
                    "analyzer": "semantic"
                },
                SearchScope.LOGS: {
                    "type": "time_series_index",
                    "fields": ["message", "level", "timestamp", "source"],
                    "analyzer": "log"
                }
            }
            
            # Load index data
            for scope in SearchScope.__dict__.keys():
                if not scope.startswith('_'):
                    await self._load_index_data(scope)
                    
        except Exception as e:
            raise Exception(f"Failed to initialize indexes: {str(e)}")

    async def _initialize_optimization(self) -> None:
        """Initialize query optimization"""
        try:
            # Set up optimization rules
            self.optimization_rules = {
                "caching": {
                    "enabled": True,
                    "ttl_seconds": 3600,
                    "max_size": 1000
                },
                "query_rewrite": {
                    "enabled": True,
                    "max_expansions": 10,
                    "use_synonyms": True
                },
                "result_ranking": {
                    "enabled": True,
                    "factors": {
                        "relevance": 0.6,
                        "recency": 0.2,
                        "popularity": 0.2
                    }
                },
                "performance": {
                    "timeout_ms": 5000,
                    "max_results": 100,
                    "batch_size": 20
                }
            }
            
            # Load custom rules
            custom_rules = await db_utils.get_agent_state(
                self.id,
                "optimization_rules"
            )
            
            if custom_rules:
                self._merge_rules(custom_rules)
                
        except Exception as e:
            raise Exception(f"Failed to initialize optimization: {str(e)}")

    async def _initialize_caching(self) -> None:
        """Initialize caching system"""
        try:
            # Clear existing cache
            self.query_cache = {}
            
            # Load recent cache entries
            recent_cache = await db_utils.get_agent_state(
                self.id,
                "query_cache"
            )
            
            if recent_cache:
                # Filter out expired entries
                current_time = datetime.now().timestamp()
                ttl = self.optimization_rules["caching"]["ttl_seconds"]
                
                valid_entries = {
                    key: value
                    for key, value in recent_cache.items()
                    if current_time - value["timestamp"] < ttl
                }
                
                self.query_cache.update(valid_entries)
                
        except Exception as e:
            raise Exception(f"Failed to initialize caching: {str(e)}")

    async def process_task(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process search tasks
        
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
                'search': self._handle_search,
                'index_management': self._handle_index_management,
                'query_optimization': self._handle_query_optimization,
                'cache_management': self._handle_cache_management,
                'analytics': self._handle_search_analytics
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

    async def _handle_search(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """Handle search tasks"""
        query = task.get('query')
        search_type = task.get('search_type', SearchType.EXACT)
        scope = task.get('scope', SearchScope.ALL)
        options = task.get('options', {})
        
        try:
            # Check cache
            cache_key = self._generate_cache_key(query, search_type, scope, options)
            cached_result = await self._check_cache(cache_key)
            
            if cached_result:
                return {
                    'success': True,
                    'results': cached_result,
                    'source': 'cache',
                    'timestamp': datetime.now().isoformat()
                }
            
            # Optimize query
            optimized_query = await self._optimize_query(
                query,
                search_type,
                scope
            )
            
            # Execute search
            results = await self._execute_search(
                optimized_query,
                search_type,
                scope,
                options
            )
            
            # Cache results
            await self._cache_results(cache_key, results)
            
            return {
                'success': True,
                'results': results,
                'source': 'search',
                'timestamp': datetime.now().isoformat()
            }
            
        except Exception as e:
            raise Exception(f"Search operation failed: {str(e)}")

    async def _handle_index_management(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """Handle index management tasks"""
        operation = task.get('operation')
        scope = task.get('scope')
        data = task.get('data')
        
        try:
            if operation == "update":
                result = await self._update_index(
                    scope,
                    data
                )
            elif operation == "rebuild":
                result = await self._rebuild_index(scope)
            elif operation == "optimize":
                result = await self._optimize_index(scope)
            else:
                raise ValueError(f"Unknown index operation: {operation}")
            
            return {
                'success': True,
                'operation': operation,
                'result': result,
                'timestamp': datetime.now().isoformat()
            }
            
        except Exception as e:
            raise Exception(f"Index management failed: {str(e)}")

    async def _execute_search(
        self,
        query: Dict[str, Any],
        search_type: str,
        scope: str,
        options: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Execute search operation"""
        try:
            results = []
            
            # Get relevant indexes
            indexes = self._get_relevant_indexes(scope)
            
            # Execute search on each index
            for index_name, index_config in indexes.items():
                index_results = await self._search_index(
                    index_name,
                    index_config,
                    query,
                    search_type,
                    options
                )
                results.extend(index_results)
            
            # Rank results
            ranked_results = await self._rank_results(
                results,
                query,
                options
            )
            
            # Apply pagination
            page_size = options.get('page_size', 20)
            page = options.get('page', 1)
            paginated_results = self._paginate_results(
                ranked_results,
                page,
                page_size
            )
            
            return paginated_results
            
        except Exception as e:
            raise Exception(f"Search execution failed: {str(e)}")

    async def _search_index(
        self,
        index_name: str,
        index_config: Dict[str, Any],
        query: Dict[str, Any],
        search_type: str,
        options: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Search within a specific index"""
        try:
            # Prepare search parameters
            search_params = {
                "index": index_name,
                "query": query,
                "type": search_type,
                "analyzer": index_config["analyzer"],
                "fields": index_config["fields"],
                "options": options
            }
            
            # Execute search
            if index_config["type"] == "vector_index":
                results = await self._vector_search(search_params)
            elif index_config["type"] == "time_series_index":
                results = await self._time_series_search(search_params)
            else:
                results = await self._text_search(search_params)
            
            return results
            
        except Exception as e:
            raise Exception(f"Index search failed: {str(e)}")

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
            event_type="search_task",
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
        self.logger.error(f"Error in Search Specialist Agent: {error_details}")
        
        # Store error for analysis
        await self._store_error(error_details)
        
        # Handle search implications
        await self._handle_search_error(error_details)

    async def _store_error(self, error_details: Dict[str, Any]) -> None:
        """Store error details for analysis"""
        await db_utils.record_event(
            event_type="search_error",
            data=error_details
        )

    async def _handle_search_error(self, error_details: Dict[str, Any]) -> None:
        """Handle search implications of errors"""
        try:
            # Check for search-related errors
            if any(term in str(error_details).lower() 
                  for term in ["search", "query", "index", "cache"]):
                # Create search event
                await db_utils.record_event(
                    event_type="search_failure",
                    data=error_details
                )
                
                # Update error statistics
                await self._update_error_stats(error_details)
            
        except Exception as e:
            self.logger.error(f"Failed to handle search error: {str(e)}")
