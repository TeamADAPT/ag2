"""
MongoDB Database Adapter
This module provides the MongoDB-specific implementation of the base database adapter.
"""

import os
from typing import Any, Dict, List, Optional, Union, Tuple
import logging
from datetime import datetime

import motor.motor_asyncio
from pymongo import IndexModel, ASCENDING, DESCENDING
from pymongo.errors import ServerSelectionTimeoutError
from dotenv import load_dotenv

from .base_adapter import BaseAdapter
from .utils import retry_with_backoff

# Load environment variables
load_dotenv(f".env.{os.getenv('ENVIRONMENT', 'development')}")

class MongoDBAdapter(BaseAdapter):
    """MongoDB adapter implementation"""
    
    def __init__(self):
        super().__init__()
        self.client = None
        self.db = None
        self._uri = self._build_uri()
        
    def _build_uri(self) -> str:
        """Build MongoDB connection URI from environment variables"""
        return (
            f"mongodb://{os.getenv('MONGODB_USER')}:{os.getenv('MONGODB_PASSWORD')}"
            f"@{os.getenv('MONGODB_URI').split('://')[1]}"
        )
    
    @retry_with_backoff(max_retries=3, base_delay=1)
    async def connect(self) -> bool:
        """
        Establish connection to MongoDB.
        
        Returns:
            bool: True if connection successful, False otherwise
        """
        try:
            if not self.client:
                self.client = motor.motor_asyncio.AsyncIOMotorClient(
                    self._uri,
                    serverSelectionTimeoutMS=5000,
                    connectTimeoutMS=5000,
                    socketTimeoutMS=5000,
                    maxPoolSize=100,
                    minPoolSize=10,
                    maxIdleTimeMS=300000,
                    waitQueueTimeoutMS=5000
                )
                
                # Verify connection
                await self.client.admin.command('ping')
                
                # Get database
                db_name = self._uri.split('/')[-1]
                self.db = self.client[db_name]
                
                self._initialized = True
                self.logger.info("MongoDB connection established")
            return True
            
        except ServerSelectionTimeoutError:
            self.logger.error("MongoDB server selection timeout")
            return False
        except Exception as e:
            self.logger.error(f"Failed to connect to MongoDB: {str(e)}")
            return False
    
    async def disconnect(self) -> bool:
        """
        Close MongoDB connection.
        
        Returns:
            bool: True if disconnection successful, False otherwise
        """
        try:
            if self.client:
                self.client.close()
                self.client = None
                self.db = None
                self._initialized = False
                self.logger.info("MongoDB connection closed")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to disconnect from MongoDB: {str(e)}")
            return False
    
    async def execute(
        self,
        query: str,
        params: Optional[Dict[str, Any]] = None
    ) -> Any:
        """
        Execute a MongoDB command.
        
        Args:
            query: Command to execute
            params: Command parameters
            
        Returns:
            Any: Command result
        """
        try:
            result = await self.db.command(query, **params if params else {})
            return result
            
        except Exception as e:
            self.logger.error(f"Failed to execute MongoDB command: {str(e)}")
            raise
    
    async def create_collection(
        self,
        name: str,
        schema: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        Create a new collection in MongoDB.
        
        Args:
            name: Collection name
            schema: Collection schema/validator
            
        Returns:
            bool: True if creation successful, False otherwise
        """
        try:
            if schema:
                await self.db.create_collection(
                    name,
                    validator=schema.get("validator"),
                    validationLevel=schema.get("validationLevel", "strict"),
                    validationAction=schema.get("validationAction", "error")
                )
            else:
                await self.db.create_collection(name)
                
            self.logger.info(f"Created MongoDB collection: {name}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to create MongoDB collection: {str(e)}")
            return False
    
    async def create_index(
        self,
        collection: str,
        index: Union[str, Tuple[str, int]]
    ) -> bool:
        """
        Create an index on a MongoDB collection.
        
        Args:
            collection: Collection name
            index: Index definition
            
        Returns:
            bool: True if creation successful, False otherwise
        """
        try:
            coll = self.db[collection]
            
            if isinstance(index, tuple):
                field, order = index
                index_model = IndexModel(
                    [(field, ASCENDING if order == 1 else DESCENDING)],
                    name=f"{collection}_{field}_idx"
                )
            else:
                index_model = IndexModel(
                    [(index, ASCENDING)],
                    name=f"{collection}_{index}_idx"
                )
            
            await coll.create_indexes([index_model])
            self.logger.info(f"Created MongoDB index: {index_model.document['name']}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to create MongoDB index: {str(e)}")
            return False
    
    async def create_stream(self, name: str) -> bool:
        """
        Create a new change stream in MongoDB.
        
        Args:
            name: Collection name to stream
            
        Returns:
            bool: True if creation successful, False otherwise
        """
        try:
            # MongoDB change streams are created on demand
            # We'll verify the collection exists
            if name not in await self.db.list_collection_names():
                await self.create_collection(name)
            
            # Test change stream creation
            coll = self.db[name]
            async with coll.watch() as stream:
                self.logger.info(f"Created MongoDB change stream for: {name}")
                return True
            
        except Exception as e:
            self.logger.error(f"Failed to create MongoDB change stream: {str(e)}")
            return False
    
    async def create_channel(self, name: str) -> bool:
        """
        Create a new pub/sub channel in MongoDB.
        
        Args:
            name: Channel name
            
        Returns:
            bool: True if creation successful, False otherwise
        """
        try:
            # MongoDB doesn't have built-in pub/sub
            # We'll implement it using a capped collection
            await self.db.create_collection(
                f"{name}_channel",
                capped=True,
                size=100000,
                max=1000
            )
            self.logger.info(f"Created MongoDB pub/sub channel: {name}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to create MongoDB pub/sub channel: {str(e)}")
            return False
    
    async def insert(
        self,
        collection: str,
        data: Union[Dict[str, Any], List[Dict[str, Any]]]
    ) -> bool:
        """
        Insert documents into a MongoDB collection.
        
        Args:
            collection: Collection name
            data: Document(s) to insert
            
        Returns:
            bool: True if insertion successful, False otherwise
        """
        try:
            coll = self.db[collection]
            
            if isinstance(data, dict):
                await coll.insert_one(data)
            else:
                await coll.insert_many(data)
                
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to insert into MongoDB: {str(e)}")
            return False
    
    async def find(
        self,
        collection: str,
        query: Dict[str, Any],
        projection: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """
        Find documents in a MongoDB collection.
        
        Args:
            collection: Collection name
            query: Query criteria
            projection: Fields to return
            
        Returns:
            List[Dict[str, Any]]: Query results
        """
        try:
            coll = self.db[collection]
            cursor = coll.find(query, projection)
            return await cursor.to_list(length=None)
            
        except Exception as e:
            self.logger.error(f"Failed to query MongoDB: {str(e)}")
            return []
    
    async def update(
        self,
        collection: str,
        query: Dict[str, Any],
        update: Dict[str, Any]
    ) -> bool:
        """
        Update documents in a MongoDB collection.
        
        Args:
            collection: Collection name
            query: Query criteria
            update: Update operations
            
        Returns:
            bool: True if update successful, False otherwise
        """
        try:
            coll = self.db[collection]
            
            # Ensure update has proper operators
            if not any(key.startswith('$') for key in update):
                update = {'$set': update}
            
            result = await coll.update_many(query, update)
            return result.modified_count > 0
            
        except Exception as e:
            self.logger.error(f"Failed to update MongoDB: {str(e)}")
            return False
    
    async def delete(
        self,
        collection: str,
        query: Dict[str, Any]
    ) -> bool:
        """
        Delete documents from a MongoDB collection.
        
        Args:
            collection: Collection name
            query: Query criteria
            
        Returns:
            bool: True if deletion successful, False otherwise
        """
        try:
            coll = self.db[collection]
            result = await coll.delete_many(query)
            return result.deleted_count > 0
            
        except Exception as e:
            self.logger.error(f"Failed to delete from MongoDB: {str(e)}")
            return False
    
    async def aggregate(
        self,
        collection: str,
        pipeline: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        Perform aggregation operations in MongoDB.
        
        Args:
            collection: Collection name
            pipeline: Aggregation pipeline
            
        Returns:
            List[Dict[str, Any]]: Aggregation results
        """
        try:
            coll = self.db[collection]
            cursor = coll.aggregate(pipeline)
            return await cursor.to_list(length=None)
            
        except Exception as e:
            self.logger.error(f"Failed to perform MongoDB aggregation: {str(e)}")
            return []
