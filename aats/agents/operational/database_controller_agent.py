"""
Database Controller Agent
This agent manages all database operations and coordinates between different databases.
"""

import asyncio
import logging
from typing import Dict, Any, List, Optional, Union
from datetime import datetime

from ...integration.databases.db_factory import db_factory, DatabaseType
from ...integration.databases.schema import validate_schema
from ...integration.databases.migrations import migration_manager
from ..base_agent import BaseAgent, AgentConfig

class DatabaseControllerAgent(BaseAgent):
    """
    Agent responsible for managing database operations across all databases.
    Handles data synchronization, migrations, and query optimization.
    """
    
    def __init__(self):
        super().__init__(AgentConfig(
            name="DatabaseController",
            description="Manages database operations and coordination",
            capabilities=[
                "data_synchronization",
                "schema_management",
                "query_optimization",
                "data_migration",
                "health_monitoring"
            ],
            required_tools=[
                "postgres_adapter",
                "mongodb_adapter",
                "neo4j_adapter",
                "redis_adapter"
            ],
            max_concurrent_tasks=10,
            priority_level=1
        ))
        self._initialized = False
        self._sync_tasks: Dict[str, asyncio.Task] = {}
        self._health_check_interval = 300  # 5 minutes
    
    async def initialize(self) -> bool:
        """
        Initialize database connections and run migrations.
        
        Returns:
            bool: True if initialization successful
        """
        try:
            # Initialize database factory
            for db_type in DatabaseType:
                adapter = await db_factory.get_adapter(db_type)
                if not adapter:
                    self.logger.error(f"Failed to initialize {db_type} adapter")
                    return False
            
            # Initialize migration manager
            if not await migration_manager.initialize():
                self.logger.error("Failed to initialize migration manager")
                return False
            
            # Apply pending migrations
            if not await migration_manager.apply_migrations():
                self.logger.error("Failed to apply migrations")
                return False
            
            # Start background tasks
            self._start_background_tasks()
            
            self._initialized = True
            self.logger.info("Database controller initialized successfully")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to initialize database controller: {str(e)}")
            return False
    
    def _start_background_tasks(self):
        """Start background monitoring and maintenance tasks"""
        asyncio.create_task(self._monitor_database_health())
        asyncio.create_task(self._sync_data())
    
    async def _monitor_database_health(self):
        """Monitor database health status"""
        while True:
            try:
                health_status = await db_factory.health_check()
                
                # Log any unhealthy databases
                for db_type, status in health_status.items():
                    if status["status"] != "healthy":
                        self.logger.error(
                            f"Unhealthy database {db_type}: {status['error']}"
                        )
                
                await asyncio.sleep(self._health_check_interval)
                
            except Exception as e:
                self.logger.error(f"Error in health monitoring: {str(e)}")
                await asyncio.sleep(60)  # Retry after 1 minute
    
    async def _sync_data(self):
        """Synchronize data between databases"""
        while True:
            try:
                # Sync critical data between databases
                for collection in ["agents", "tasks", "system_metrics"]:
                    await self._sync_collection(collection)
                
                await asyncio.sleep(60)  # Sync every minute
                
            except Exception as e:
                self.logger.error(f"Error in data synchronization: {str(e)}")
                await asyncio.sleep(60)
    
    async def _sync_collection(self, collection: str):
        """
        Synchronize a collection across databases.
        
        Args:
            collection: Collection name to synchronize
        """
        try:
            # Get primary data from PostgreSQL
            postgres = await db_factory.get_adapter(DatabaseType.POSTGRES)
            if not postgres:
                return
            
            data = await postgres.find(collection, {})
            
            # Sync to other databases
            for db_type in [
                DatabaseType.MONGODB,
                DatabaseType.NEO4J,
                DatabaseType.REDIS
            ]:
                adapter = await db_factory.get_adapter(db_type)
                if not adapter:
                    continue
                
                # Clear existing data
                await adapter.delete(collection, {})
                
                # Insert new data
                if data:
                    await adapter.insert(collection, data)
            
        except Exception as e:
            self.logger.error(
                f"Failed to sync collection {collection}: {str(e)}"
            )
    
    async def insert(
        self,
        collection: str,
        data: Union[Dict[str, Any], List[Dict[str, Any]]],
        db_type: Optional[DatabaseType] = None
    ) -> bool:
        """
        Insert data into database(s).
        
        Args:
            collection: Collection name
            data: Data to insert
            db_type: Optional specific database to insert into
            
        Returns:
            bool: True if insertion successful
        """
        try:
            # Validate data against schema
            if isinstance(data, dict):
                items = [data]
            else:
                items = data
            
            for item in items:
                if not validate_schema(
                    db_type.value if db_type else "postgres",
                    collection,
                    item
                ):
                    raise ValueError(f"Invalid data format for {collection}")
            
            # Insert into specified database or all databases
            if db_type:
                adapter = await db_factory.get_adapter(db_type)
                if not adapter:
                    return False
                
                return await adapter.insert(collection, data)
            else:
                # Insert into all databases
                success = True
                for current_db in DatabaseType:
                    adapter = await db_factory.get_adapter(current_db)
                    if not adapter:
                        success = False
                        continue
                    
                    if not await adapter.insert(collection, data):
                        success = False
                
                return success
            
        except Exception as e:
            self.logger.error(f"Failed to insert data: {str(e)}")
            return False
    
    async def find(
        self,
        collection: str,
        query: Dict[str, Any],
        projection: Optional[Dict[str, Any]] = None,
        db_type: Optional[DatabaseType] = None
    ) -> List[Dict[str, Any]]:
        """
        Find documents in database(s).
        
        Args:
            collection: Collection name
            query: Query criteria
            projection: Optional fields to return
            db_type: Optional specific database to query
            
        Returns:
            List[Dict[str, Any]]: Query results
        """
        try:
            if db_type:
                adapter = await db_factory.get_adapter(db_type)
                if not adapter:
                    return []
                
                return await adapter.find(collection, query, projection)
            else:
                # Query primary database (PostgreSQL)
                adapter = await db_factory.get_adapter(DatabaseType.POSTGRES)
                if not adapter:
                    return []
                
                return await adapter.find(collection, query, projection)
            
        except Exception as e:
            self.logger.error(f"Failed to query data: {str(e)}")
            return []
    
    async def update(
        self,
        collection: str,
        query: Dict[str, Any],
        update: Dict[str, Any],
        db_type: Optional[DatabaseType] = None
    ) -> bool:
        """
        Update documents in database(s).
        
        Args:
            collection: Collection name
            query: Query criteria
            update: Update operations
            db_type: Optional specific database to update
            
        Returns:
            bool: True if update successful
        """
        try:
            if db_type:
                adapter = await db_factory.get_adapter(db_type)
                if not adapter:
                    return False
                
                return await adapter.update(collection, query, update)
            else:
                # Update all databases
                success = True
                for current_db in DatabaseType:
                    adapter = await db_factory.get_adapter(current_db)
                    if not adapter:
                        success = False
                        continue
                    
                    if not await adapter.update(collection, query, update):
                        success = False
                
                return success
            
        except Exception as e:
            self.logger.error(f"Failed to update data: {str(e)}")
            return False
    
    async def delete(
        self,
        collection: str,
        query: Dict[str, Any],
        db_type: Optional[DatabaseType] = None
    ) -> bool:
        """
        Delete documents from database(s).
        
        Args:
            collection: Collection name
            query: Query criteria
            db_type: Optional specific database to delete from
            
        Returns:
            bool: True if deletion successful
        """
        try:
            if db_type:
                adapter = await db_factory.get_adapter(db_type)
                if not adapter:
                    return False
                
                return await adapter.delete(collection, query)
            else:
                # Delete from all databases
                success = True
                for current_db in DatabaseType:
                    adapter = await db_factory.get_adapter(current_db)
                    if not adapter:
                        success = False
                        continue
                    
                    if not await adapter.delete(collection, query):
                        success = False
                
                return success
            
        except Exception as e:
            self.logger.error(f"Failed to delete data: {str(e)}")
            return False
    
    async def aggregate(
        self,
        collection: str,
        pipeline: List[Dict[str, Any]],
        db_type: Optional[DatabaseType] = None
    ) -> List[Dict[str, Any]]:
        """
        Perform aggregation operations.
        
        Args:
            collection: Collection name
            pipeline: Aggregation pipeline
            db_type: Optional specific database to query
            
        Returns:
            List[Dict[str, Any]]: Aggregation results
        """
        try:
            if db_type:
                adapter = await db_factory.get_adapter(db_type)
                if not adapter:
                    return []
                
                return await adapter.aggregate(collection, pipeline)
            else:
                # Use MongoDB for aggregation (best suited for complex queries)
                adapter = await db_factory.get_adapter(DatabaseType.MONGODB)
                if not adapter:
                    return []
                
                return await adapter.aggregate(collection, pipeline)
            
        except Exception as e:
            self.logger.error(f"Failed to perform aggregation: {str(e)}")
            return []
    
    async def cleanup(self) -> bool:
        """
        Clean up database connections and resources.
        
        Returns:
            bool: True if cleanup successful
        """
        try:
            # Cancel background tasks
            for task in self._sync_tasks.values():
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    pass
            
            # Close database connections
            if not await db_factory.close_all():
                return False
            
            self._initialized = False
            self.logger.info("Database controller cleaned up successfully")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to clean up database controller: {str(e)}")
            return False

# Global database controller instance
db_controller = DatabaseControllerAgent()
