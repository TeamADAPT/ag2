"""
Database Utilities
This module provides common utility functions for database operations.
"""

import asyncio
import functools
import logging
from typing import Any, Callable, TypeVar, Optional
from datetime import datetime, timedelta
import json

# Type variable for generic function return type
T = TypeVar('T')

logger = logging.getLogger(__name__)

def retry_with_backoff(
    max_retries: int = 3,
    base_delay: float = 1.0,
    max_delay: float = 10.0,
    exponential: bool = True
) -> Callable:
    """
    Decorator for retrying async functions with exponential backoff.
    
    Args:
        max_retries: Maximum number of retry attempts
        base_delay: Initial delay between retries in seconds
        max_delay: Maximum delay between retries in seconds
        exponential: Whether to use exponential backoff
        
    Returns:
        Callable: Decorated function
    """
    def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
        @functools.wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> Any:
            retries = 0
            while True:
                try:
                    return await func(*args, **kwargs)
                except Exception as e:
                    retries += 1
                    if retries > max_retries:
                        logger.error(
                            f"Max retries ({max_retries}) exceeded for {func.__name__}: {str(e)}"
                        )
                        raise
                    
                    # Calculate delay
                    if exponential:
                        delay = min(base_delay * (2 ** (retries - 1)), max_delay)
                    else:
                        delay = base_delay
                    
                    logger.warning(
                        f"Retry {retries}/{max_retries} for {func.__name__} "
                        f"after {delay}s: {str(e)}"
                    )
                    
                    await asyncio.sleep(delay)
        return wrapper
    return decorator

def sanitize_field_name(field: str) -> str:
    """
    Sanitize field names for database operations.
    
    Args:
        field: Field name to sanitize
        
    Returns:
        str: Sanitized field name
    """
    # Remove special characters and spaces
    sanitized = ''.join(c if c.isalnum() else '_' for c in field)
    
    # Ensure it starts with a letter
    if sanitized[0].isdigit():
        sanitized = f"f_{sanitized}"
    
    return sanitized.lower()

def serialize_value(value: Any) -> str:
    """
    Serialize a value for database storage.
    
    Args:
        value: Value to serialize
        
    Returns:
        str: Serialized value
    """
    if isinstance(value, (datetime, timedelta)):
        return value.isoformat()
    elif isinstance(value, (dict, list)):
        return json.dumps(value)
    else:
        return str(value)

def deserialize_value(value: str, target_type: Optional[type] = None) -> Any:
    """
    Deserialize a value from database storage.
    
    Args:
        value: Value to deserialize
        target_type: Optional target type for deserialization
        
    Returns:
        Any: Deserialized value
    """
    if not value:
        return None
    
    if target_type:
        if target_type == datetime:
            return datetime.fromisoformat(value)
        elif target_type == timedelta:
            return timedelta.fromisoformat(value)
        elif target_type in (dict, list):
            return json.loads(value)
        else:
            return target_type(value)
    
    # Try to guess the type
    try:
        # Try JSON first
        return json.loads(value)
    except json.JSONDecodeError:
        # Try datetime
        try:
            return datetime.fromisoformat(value)
        except ValueError:
            # Return as string
            return value

def build_query_string(
    conditions: dict,
    operator: str = 'AND'
) -> tuple[str, dict]:
    """
    Build a SQL query string from conditions.
    
    Args:
        conditions: Query conditions
        operator: Logical operator to join conditions
        
    Returns:
        tuple[str, dict]: Query string and parameters
    """
    params = {}
    query_parts = []
    
    for i, (field, value) in enumerate(conditions.items(), 1):
        param_name = f"p{i}"
        
        if isinstance(value, (list, tuple)):
            # Handle IN conditions
            params.update({f"{param_name}_{j}": v for j, v in enumerate(value)})
            placeholders = [f"${param_name}_{j}" for j in range(len(value))]
            query_parts.append(f"{field} IN ({','.join(placeholders)})")
        elif value is None:
            # Handle NULL conditions
            query_parts.append(f"{field} IS NULL")
        else:
            # Handle standard conditions
            params[param_name] = value
            query_parts.append(f"{field} = ${param_name}")
    
    return f" {operator} ".join(query_parts), params

def build_update_string(
    updates: dict
) -> tuple[str, dict]:
    """
    Build a SQL update string from field updates.
    
    Args:
        updates: Field updates
        
    Returns:
        tuple[str, dict]: Update string and parameters
    """
    params = {}
    update_parts = []
    
    for i, (field, value) in enumerate(updates.items(), 1):
        param_name = f"p{i}"
        params[param_name] = value
        update_parts.append(f"{field} = ${param_name}")
    
    return ", ".join(update_parts), params

class QueryBuilder:
    """Builder for constructing database queries"""
    
    def __init__(self):
        self.select_fields = []
        self.from_table = None
        self.join_clauses = []
        self.where_conditions = []
        self.group_by = []
        self.having_conditions = []
        self.order_by = []
        self.limit_value = None
        self.offset_value = None
        self.parameters = {}
        self.param_counter = 0
    
    def select(self, *fields: str) -> 'QueryBuilder':
        """Add fields to SELECT clause"""
        self.select_fields.extend(fields)
        return self
    
    def from_(self, table: str) -> 'QueryBuilder':
        """Set FROM clause"""
        self.from_table = table
        return self
    
    def join(
        self,
        table: str,
        condition: str,
        join_type: str = 'INNER'
    ) -> 'QueryBuilder':
        """Add JOIN clause"""
        self.join_clauses.append(f"{join_type} JOIN {table} ON {condition}")
        return self
    
    def where(self, condition: str, value: Any = None) -> 'QueryBuilder':
        """Add WHERE condition"""
        if value is not None:
            self.param_counter += 1
            param_name = f"p{self.param_counter}"
            self.parameters[param_name] = value
            condition = condition.replace('?', f"${param_name}")
        self.where_conditions.append(condition)
        return self
    
    def group_by_(self, *fields: str) -> 'QueryBuilder':
        """Add GROUP BY clause"""
        self.group_by.extend(fields)
        return self
    
    def having(self, condition: str) -> 'QueryBuilder':
        """Add HAVING condition"""
        self.having_conditions.append(condition)
        return self
    
    def order_by_(self, field: str, direction: str = 'ASC') -> 'QueryBuilder':
        """Add ORDER BY clause"""
        self.order_by.append(f"{field} {direction}")
        return self
    
    def limit(self, value: int) -> 'QueryBuilder':
        """Set LIMIT clause"""
        self.limit_value = value
        return self
    
    def offset(self, value: int) -> 'QueryBuilder':
        """Set OFFSET clause"""
        self.offset_value = value
        return self
    
    def build(self) -> tuple[str, dict]:
        """
        Build the complete query.
        
        Returns:
            tuple[str, dict]: Query string and parameters
        """
        query_parts = []
        
        # SELECT
        select_clause = "SELECT"
        if self.select_fields:
            select_clause += f" {', '.join(self.select_fields)}"
        else:
            select_clause += " *"
        query_parts.append(select_clause)
        
        # FROM
        if self.from_table:
            query_parts.append(f"FROM {self.from_table}")
        
        # JOIN
        if self.join_clauses:
            query_parts.extend(self.join_clauses)
        
        # WHERE
        if self.where_conditions:
            query_parts.append(
                f"WHERE {' AND '.join(self.where_conditions)}"
            )
        
        # GROUP BY
        if self.group_by:
            query_parts.append(f"GROUP BY {', '.join(self.group_by)}")
        
        # HAVING
        if self.having_conditions:
            query_parts.append(
                f"HAVING {' AND '.join(self.having_conditions)}"
            )
        
        # ORDER BY
        if self.order_by:
            query_parts.append(f"ORDER BY {', '.join(self.order_by)}")
        
        # LIMIT
        if self.limit_value is not None:
            query_parts.append(f"LIMIT {self.limit_value}")
        
        # OFFSET
        if self.offset_value is not None:
            query_parts.append(f"OFFSET {self.offset_value}")
        
        return " ".join(query_parts), self.parameters

class ConnectionPool:
    """
    Generic connection pool for database connections.
    Implements connection pooling with configurable pool size and connection lifetime.
    """
    
    def __init__(
        self,
        min_size: int = 1,
        max_size: int = 10,
        max_lifetime: int = 3600,
        acquire_timeout: int = 30
    ):
        self.min_size = min_size
        self.max_size = max_size
        self.max_lifetime = max_lifetime
        self.acquire_timeout = acquire_timeout
        self.pool: asyncio.Queue = asyncio.Queue(maxsize=max_size)
        self.size = 0
        self._closed = False
        self._lock = asyncio.Lock()
    
    async def acquire(self) -> Any:
        """
        Acquire a connection from the pool.
        
        Returns:
            Any: Database connection
        """
        if self._closed:
            raise RuntimeError("Connection pool is closed")
        
        async with self._lock:
            # Try to get an existing connection
            try:
                conn = self.pool.get_nowait()
                if await self._is_connection_valid(conn):
                    return conn
                else:
                    await self._close_connection(conn)
                    self.size -= 1
            except asyncio.QueueEmpty:
                pass
            
            # Create new connection if pool isn't full
            if self.size < self.max_size:
                conn = await self._create_connection()
                self.size += 1
                return conn
            
            # Wait for a connection to become available
            try:
                async with asyncio.timeout(self.acquire_timeout):
                    while True:
                        conn = await self.pool.get()
                        if await self._is_connection_valid(conn):
                            return conn
                        else:
                            await self._close_connection(conn)
                            self.size -= 1
                            
                            if self.size < self.max_size:
                                conn = await self._create_connection()
                                self.size += 1
                                return conn
            except asyncio.TimeoutError:
                raise TimeoutError("Timeout waiting for connection")
    
    async def release(self, conn: Any):
        """
        Release a connection back to the pool.
        
        Args:
            conn: Database connection to release
        """
        if self._closed:
            await self._close_connection(conn)
            return
        
        if await self._is_connection_valid(conn):
            await self.pool.put(conn)
        else:
            await self._close_connection(conn)
            self.size -= 1
    
    async def close(self):
        """Close all connections in the pool"""
        self._closed = True
        
        while True:
            try:
                conn = self.pool.get_nowait()
                await self._close_connection(conn)
                self.size -= 1
            except asyncio.QueueEmpty:
                break
    
    async def _create_connection(self) -> Any:
        """
        Create a new database connection.
        Must be implemented by subclasses.
        
        Returns:
            Any: New database connection
        """
        raise NotImplementedError
    
    async def _close_connection(self, conn: Any):
        """
        Close a database connection.
        Must be implemented by subclasses.
        
        Args:
            conn: Database connection to close
        """
        raise NotImplementedError
    
    async def _is_connection_valid(self, conn: Any) -> bool:
        """
        Check if a connection is valid.
        Must be implemented by subclasses.
        
        Args:
            conn: Database connection to check
            
        Returns:
            bool: True if connection is valid
        """
        raise NotImplementedError

class DatabaseError(Exception):
    """Base class for database errors"""
    pass

class ConnectionError(DatabaseError):
    """Error establishing database connection"""
    pass

class QueryError(DatabaseError):
    """Error executing database query"""
    pass

class TransactionError(DatabaseError):
    """Error in database transaction"""
    pass

class ValidationError(DatabaseError):
    """Error validating database operation"""
    pass
