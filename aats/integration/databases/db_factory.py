"""
Database Factory
This module provides a factory for creating and managing database adapters.
"""

from typing import Dict, Optional, Type, Union
import logging
from enum import Enum

from .base_adapter import BaseAdapter
from .postgres_adapter import PostgresAdapter
from .mongodb_adapter import MongoDBAdapter
from .neo4j_adapter import Neo4jAdapter
from .redis_adapter import RedisAdapter

class DatabaseType(str, Enum):
    """Supported database types"""
    POSTGRES = "postgres"
    MONGODB = "mongodb"
    NEO4J = "neo4j"
    REDIS = "redis"

class DatabaseFactory:
    """Factory for creating and managing database adapters"""
    
    _instance = None
    _adapters: Dict[DatabaseType, BaseAdapter] = {}
    _adapter_classes: Dict[DatabaseType, Type[BaseAdapter]] = {
        DatabaseType.POSTGRES: PostgresAdapter,
        DatabaseType.MONGODB: MongoDBAdapter,
        DatabaseType.NEO4J: Neo4jAdapter,
        DatabaseType.REDIS: RedisAdapter
    }
    
    def __new__(cls):
        """Ensure singleton instance"""
        if cls._instance is None:
            cls._instance = super(DatabaseFactory, cls).__new__(cls)
            cls._instance.logger = logging.getLogger(cls.__name__)
        return cls._instance
    
    async def get_adapter(
        self,
        db_type: Union[DatabaseType, str]
    ) -> Optional[BaseAdapter]:
        """
        Get a database adapter instance.
        Creates a new instance if one doesn't exist.
        
        Args:
            db_type: Type of database adapter to get
            
        Returns:
            BaseAdapter: Database adapter instance
        """
        try:
            # Convert string to enum if needed
            if isinstance(db_type, str):
                db_type = DatabaseType(db_type.lower())
            
            # Create adapter if it doesn't exist
            if db_type not in self._adapters:
                adapter_class = self._adapter_classes.get(db_type)
                if not adapter_class:
                    raise ValueError(f"Unsupported database type: {db_type}")
                
                adapter = adapter_class()
                await adapter.connect()
                self._adapters[db_type] = adapter
            
            return self._adapters[db_type]
            
        except Exception as e:
            self.logger.error(f"Failed to get database adapter: {str(e)}")
            return None
    
    async def close_all(self) -> bool:
        """
        Close all database connections.
        
        Returns:
            bool: True if all connections closed successfully
        """
        success = True
        for db_type, adapter in self._adapters.items():
            try:
                await adapter.disconnect()
                self.logger.info(f"Closed {db_type} connection")
            except Exception as e:
                self.logger.error(f"Failed to close {db_type} connection: {str(e)}")
                success = False
        
        self._adapters.clear()
        return success
    
    async def health_check(self) -> Dict[str, Dict[str, Any]]:
        """
        Check health status of all database connections.
        
        Returns:
            Dict[str, Dict[str, Any]]: Health status for each database
        """
        status = {}
        for db_type, adapter in self._adapters.items():
            try:
                status[db_type] = await adapter.health_check()
            except Exception as e:
                status[db_type] = {
                    "status": "unhealthy",
                    "error": str(e)
                }
        return status
    
    def get_supported_databases(self) -> List[str]:
        """
        Get list of supported database types.
        
        Returns:
            List[str]: List of supported database types
        """
        return [db_type.value for db_type in DatabaseType]
    
    async def initialize_databases(self) -> bool:
        """
        Initialize all supported databases.
        
        Returns:
            bool: True if all databases initialized successfully
        """
        success = True
        for db_type in DatabaseType:
            try:
                adapter = await self.get_adapter(db_type)
                if not adapter:
                    success = False
                    continue
                
                self.logger.info(f"Initialized {db_type} database")
                
            except Exception as e:
                self.logger.error(f"Failed to initialize {db_type} database: {str(e)}")
                success = False
        
        return success
    
    async def cleanup_databases(self) -> bool:
        """
        Clean up all database connections and resources.
        
        Returns:
            bool: True if cleanup successful
        """
        try:
            # Close all connections
            await self.close_all()
            
            # Clear adapter instances
            self._adapters.clear()
            
            self.logger.info("Database cleanup completed")
            return True
            
        except Exception as e:
            self.logger.error(f"Database cleanup failed: {str(e)}")
            return False

# Global database factory instance
db_factory = DatabaseFactory()
