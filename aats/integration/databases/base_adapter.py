"""
Base Database Adapter
This module provides the base adapter class that all specific database adapters must implement.
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Union, Tuple
import logging
from datetime import datetime

class BaseAdapter(ABC):
    """
    Abstract base class for database adapters.
    All specific database adapters must inherit from this class and implement its methods.
    """
    
    def __init__(self):
        self.logger = logging.getLogger(self.__class__.__name__)
        self._connection = None
        self._initialized = False
    
    @abstractmethod
    async def connect(self) -> bool:
        """
        Establish connection to the database.
        
        Returns:
            bool: True if connection successful, False otherwise
        """
        pass
    
    @abstractmethod
    async def disconnect(self) -> bool:
        """
        Close the database connection.
        
        Returns:
            bool: True if disconnection successful, False otherwise
        """
        pass
    
    @abstractmethod
    async def execute(self, query: str, params: Optional[Dict[str, Any]] = None) -> Any:
        """
        Execute a database query.
        
        Args:
            query: The query to execute
            params: Optional parameters for the query
            
        Returns:
            Any: Query result
        """
        pass
    
    @abstractmethod
    async def create_collection(
        self,
        name: str,
        schema: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        Create a new collection/table.
        
        Args:
            name: Name of the collection/table
            schema: Optional schema definition
            
        Returns:
            bool: True if creation successful, False otherwise
        """
        pass
    
    @abstractmethod
    async def create_index(
        self,
        collection: str,
        index: Union[str, Tuple[str, int]]
    ) -> bool:
        """
        Create an index on a collection/table.
        
        Args:
            collection: Name of the collection/table
            index: Index definition
            
        Returns:
            bool: True if creation successful, False otherwise
        """
        pass
    
    @abstractmethod
    async def create_stream(self, name: str) -> bool:
        """
        Create a new stream (for streaming databases).
        
        Args:
            name: Name of the stream
            
        Returns:
            bool: True if creation successful, False otherwise
        """
        pass
    
    @abstractmethod
    async def create_channel(self, name: str) -> bool:
        """
        Create a new pub/sub channel.
        
        Args:
            name: Name of the channel
            
        Returns:
            bool: True if creation successful, False otherwise
        """
        pass
    
    @abstractmethod
    async def insert(
        self,
        collection: str,
        data: Union[Dict[str, Any], List[Dict[str, Any]]]
    ) -> bool:
        """
        Insert data into a collection/table.
        
        Args:
            collection: Name of the collection/table
            data: Data to insert (single document or list of documents)
            
        Returns:
            bool: True if insertion successful, False otherwise
        """
        pass
    
    @abstractmethod
    async def find(
        self,
        collection: str,
        query: Dict[str, Any],
        projection: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """
        Find documents in a collection/table.
        
        Args:
            collection: Name of the collection/table
            query: Query criteria
            projection: Optional fields to return
            
        Returns:
            List[Dict[str, Any]]: List of matching documents
        """
        pass
    
    @abstractmethod
    async def update(
        self,
        collection: str,
        query: Dict[str, Any],
        update: Dict[str, Any]
    ) -> bool:
        """
        Update documents in a collection/table.
        
        Args:
            collection: Name of the collection/table
            query: Query criteria
            update: Update operations
            
        Returns:
            bool: True if update successful, False otherwise
        """
        pass
    
    @abstractmethod
    async def delete(
        self,
        collection: str,
        query: Dict[str, Any]
    ) -> bool:
        """
        Delete documents from a collection/table.
        
        Args:
            collection: Name of the collection/table
            query: Query criteria
            
        Returns:
            bool: True if deletion successful, False otherwise
        """
        pass
    
    @abstractmethod
    async def aggregate(
        self,
        collection: str,
        pipeline: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        Perform an aggregation operation.
        
        Args:
            collection: Name of the collection/table
            pipeline: Aggregation pipeline
            
        Returns:
            List[Dict[str, Any]]: Aggregation results
        """
        pass
    
    async def health_check(self) -> Dict[str, Any]:
        """
        Check the health status of the database connection.
        
        Returns:
            Dict[str, Any]: Health check results
        """
        try:
            start_time = datetime.now()
            is_connected = await self.connect() if not self._connection else True
            response_time = (datetime.now() - start_time).total_seconds()
            
            return {
                "status": "healthy" if is_connected else "unhealthy",
                "connected": is_connected,
                "response_time": response_time,
                "timestamp": datetime.now().isoformat()
            }
        except Exception as e:
            self.logger.error(f"Health check failed: {str(e)}")
            return {
                "status": "unhealthy",
                "connected": False,
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }
    
    async def __aenter__(self):
        """Async context manager entry"""
        await self.connect()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        await self.disconnect()
    
    def __repr__(self) -> str:
        """String representation"""
        return f"{self.__class__.__name__}(initialized={self._initialized})"
