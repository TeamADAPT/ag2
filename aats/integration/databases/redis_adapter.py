"""
Redis Database Adapter
This module provides the Redis-specific implementation of the base database adapter.
"""

import os
from typing import Any, Dict, List, Optional, Union, Tuple
import logging
from datetime import datetime
import json
import asyncio

import aioredis
from aioredis.client import Redis
from aioredis.exceptions import ConnectionError
from dotenv import load_dotenv

from .base_adapter import BaseAdapter
from .utils import retry_with_backoff

# Load environment variables
load_dotenv(f".env.{os.getenv('ENVIRONMENT', 'development')}")

class RedisAdapter(BaseAdapter):
    """Redis adapter implementation"""
    
    def __init__(self):
        super().__init__()
        self.client: Optional[Redis] = None
        self.pubsub = None
        self._uri = self._build_uri()
        self._channels: Dict[str, asyncio.Queue] = {}
        self._stream_consumers: Dict[str, asyncio.Task] = {}
        
    def _build_uri(self) -> str:
        """Build Redis connection URI from environment variables"""
        return (
            f"redis://:{os.getenv('REDIS_PASSWORD')}@"
            f"{os.getenv('REDIS_HOST')}:{os.getenv('REDIS_PORT')}/0"
        )
    
    @retry_with_backoff(max_retries=3, base_delay=1)
    async def connect(self) -> bool:
        """
        Establish connection to Redis.
        
        Returns:
            bool: True if connection successful, False otherwise
        """
        try:
            if not self.client:
                self.client = await aioredis.from_url(
                    self._uri,
                    encoding="utf-8",
                    decode_responses=True,
                    max_connections=50,
                    socket_timeout=5,
                    socket_connect_timeout=5
                )
                
                # Verify connection
                await self.client.ping()
                
                # Initialize pubsub
                self.pubsub = self.client.pubsub()
                
                self._initialized = True
                self.logger.info("Redis connection established")
            return True
            
        except ConnectionError:
            self.logger.error("Redis connection error")
            return False
        except Exception as e:
            self.logger.error(f"Failed to connect to Redis: {str(e)}")
            return False
    
    async def disconnect(self) -> bool:
        """
        Close Redis connection.
        
        Returns:
            bool: True if disconnection successful, False otherwise
        """
        try:
            if self.client:
                # Stop all stream consumers
                for task in self._stream_consumers.values():
                    task.cancel()
                    try:
                        await task
                    except asyncio.CancelledError:
                        pass
                
                # Close pubsub
                if self.pubsub:
                    await self.pubsub.close()
                
                # Close client
                await self.client.close()
                self.client = None
                self._initialized = False
                self.logger.info("Redis connection closed")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to disconnect from Redis: {str(e)}")
            return False
    
    async def execute(
        self,
        command: str,
        params: Optional[Dict[str, Any]] = None
    ) -> Any:
        """
        Execute a Redis command.
        
        Args:
            command: Redis command
            params: Command parameters
            
        Returns:
            Any: Command result
        """
        try:
            if params:
                result = await getattr(self.client, command)(*params.values())
            else:
                result = await getattr(self.client, command)()
            return result
            
        except Exception as e:
            self.logger.error(f"Failed to execute Redis command: {str(e)}")
            raise
    
    async def create_collection(
        self,
        name: str,
        schema: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        Create a new Redis hash.
        
        Args:
            name: Hash name
            schema: Optional schema (not used in Redis)
            
        Returns:
            bool: True if creation successful, False otherwise
        """
        try:
            # Redis doesn't require explicit collection creation
            # We'll create a metadata hash to track the collection
            metadata = {
                "name": name,
                "created_at": datetime.now().isoformat(),
                "type": "hash"
            }
            
            if schema:
                metadata["schema"] = json.dumps(schema)
            
            await self.client.hset(f"{name}:metadata", mapping=metadata)
            self.logger.info(f"Created Redis hash: {name}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to create Redis hash: {str(e)}")
            return False
    
    async def create_index(
        self,
        collection: str,
        index: Union[str, Tuple[str, int]]
    ) -> bool:
        """
        Create a Redis index.
        
        Args:
            collection: Hash name
            index: Field to index
            
        Returns:
            bool: True if creation successful, False otherwise
        """
        try:
            # Redis doesn't support traditional indexes
            # We'll create a sorted set for indexing
            if isinstance(index, tuple):
                field, _ = index
            else:
                field = index
            
            # Create index metadata
            await self.client.hset(
                f"{collection}:indexes",
                field,
                json.dumps({
                    "type": "sorted_set",
                    "created_at": datetime.now().isoformat()
                })
            )
            
            self.logger.info(f"Created Redis index: {collection}:{field}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to create Redis index: {str(e)}")
            return False
    
    async def create_stream(self, name: str) -> bool:
        """
        Create a new Redis stream.
        
        Args:
            name: Stream name
            
        Returns:
            bool: True if creation successful, False otherwise
        """
        try:
            # Create stream metadata
            await self.client.hset(
                f"{name}:stream:metadata",
                mapping={
                    "name": name,
                    "created_at": datetime.now().isoformat(),
                    "type": "stream"
                }
            )
            
            # Create consumer group
            try:
                await self.client.xgroup_create(
                    name,
                    "default_group",
                    mkstream=True
                )
            except Exception:
                # Group may already exist
                pass
            
            # Start stream consumer
            self._stream_consumers[name] = asyncio.create_task(
                self._consume_stream(name)
            )
            
            self.logger.info(f"Created Redis stream: {name}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to create Redis stream: {str(e)}")
            return False
    
    async def _consume_stream(self, stream: str):
        """Background task to consume stream messages"""
        try:
            while True:
                try:
                    # Read new messages
                    messages = await self.client.xread(
                        streams={stream: "$"},
                        count=100,
                        block=1000
                    )
                    
                    if messages:
                        for _, stream_messages in messages:
                            for message_id, fields in stream_messages:
                                # Process message
                                await self._process_stream_message(
                                    stream,
                                    message_id,
                                    fields
                                )
                                
                except Exception as e:
                    self.logger.error(
                        f"Error consuming Redis stream {stream}: {str(e)}"
                    )
                    await asyncio.sleep(1)
                    
        except asyncio.CancelledError:
            self.logger.info(f"Stopping Redis stream consumer for {stream}")
    
    async def _process_stream_message(
        self,
        stream: str,
        message_id: str,
        fields: Dict[str, Any]
    ):
        """Process a stream message"""
        try:
            # Add to message queue if exists
            if stream in self._channels:
                await self._channels[stream].put({
                    "id": message_id,
                    "data": fields
                })
            
        except Exception as e:
            self.logger.error(
                f"Error processing stream message {message_id}: {str(e)}"
            )
    
    async def create_channel(self, name: str) -> bool:
        """
        Create a new pub/sub channel in Redis.
        
        Args:
            name: Channel name
            
        Returns:
            bool: True if creation successful, False otherwise
        """
        try:
            # Create message queue for channel
            self._channels[name] = asyncio.Queue()
            
            # Subscribe to channel
            await self.pubsub.subscribe(name)
            
            # Start message handler
            asyncio.create_task(self._handle_messages(name))
            
            self.logger.info(f"Created Redis pub/sub channel: {name}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to create Redis pub/sub channel: {str(e)}")
            return False
    
    async def _handle_messages(self, channel: str):
        """Handle pub/sub messages"""
        try:
            while True:
                message = await self.pubsub.get_message(
                    ignore_subscribe_messages=True,
                    timeout=1.0
                )
                
                if message:
                    # Add to message queue
                    await self._channels[channel].put(message)
                
                await asyncio.sleep(0.1)
                
        except Exception as e:
            self.logger.error(
                f"Error handling messages for channel {channel}: {str(e)}"
            )
    
    async def insert(
        self,
        collection: str,
        data: Union[Dict[str, Any], List[Dict[str, Any]]]
    ) -> bool:
        """
        Insert data into Redis.
        
        Args:
            collection: Hash name
            data: Data to insert
            
        Returns:
            bool: True if insertion successful, False otherwise
        """
        try:
            if isinstance(data, dict):
                data = [data]
            
            pipe = self.client.pipeline()
            
            for item in data:
                # Generate ID if not provided
                if "_id" not in item:
                    item["_id"] = f"{collection}:{await self.client.incr(f'{collection}:id')}"
                
                # Convert non-string values to JSON
                processed_item = {
                    k: json.dumps(v) if not isinstance(v, str) else v
                    for k, v in item.items()
                }
                
                # Store in hash
                pipe.hset(item["_id"], mapping=processed_item)
                
                # Update indexes
                indexes = await self.client.hgetall(f"{collection}:indexes")
                for field in indexes:
                    if field in item:
                        pipe.zadd(
                            f"{collection}:index:{field}",
                            {item["_id"]: float(item[field])}
                            if isinstance(item[field], (int, float))
                            else {item["_id"]: 0}
                        )
            
            await pipe.execute()
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to insert into Redis: {str(e)}")
            return False
    
    async def find(
        self,
        collection: str,
        query: Dict[str, Any],
        projection: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """
        Find data in Redis.
        
        Args:
            collection: Hash name
            query: Query criteria
            projection: Fields to return
            
        Returns:
            List[Dict[str, Any]]: Query results
        """
        try:
            results = []
            
            # Get all keys for collection
            keys = await self.client.keys(f"{collection}:*")
            
            for key in keys:
                if ":metadata" in key or ":indexes" in key:
                    continue
                
                # Get hash data
                data = await self.client.hgetall(key)
                
                # Convert JSON values back to objects
                processed_data = {}
                for k, v in data.items():
                    try:
                        processed_data[k] = json.loads(v)
                    except json.JSONDecodeError:
                        processed_data[k] = v
                
                # Apply query filter
                matches = True
                for field, value in query.items():
                    if field not in processed_data or processed_data[field] != value:
                        matches = False
                        break
                
                if matches:
                    # Apply projection
                    if projection:
                        result = {
                            k: v for k, v in processed_data.items()
                            if k in projection and projection[k]
                        }
                    else:
                        result = processed_data
                    
                    results.append(result)
            
            return results
            
        except Exception as e:
            self.logger.error(f"Failed to query Redis: {str(e)}")
            return []
    
    async def update(
        self,
        collection: str,
        query: Dict[str, Any],
        update: Dict[str, Any]
    ) -> bool:
        """
        Update data in Redis.
        
        Args:
            collection: Hash name
            query: Query criteria
            update: Fields to update
            
        Returns:
            bool: True if update successful, False otherwise
        """
        try:
            # Find matching documents
            documents = await self.find(collection, query)
            
            if not documents:
                return False
            
            pipe = self.client.pipeline()
            
            for doc in documents:
                # Update fields
                for field, value in update.items():
                    doc[field] = value
                
                # Convert non-string values to JSON
                processed_doc = {
                    k: json.dumps(v) if not isinstance(v, str) else v
                    for k, v in doc.items()
                }
                
                # Update hash
                pipe.hset(doc["_id"], mapping=processed_doc)
                
                # Update indexes
                indexes = await self.client.hgetall(f"{collection}:indexes")
                for field in indexes:
                    if field in doc:
                        pipe.zadd(
                            f"{collection}:index:{field}",
                            {doc["_id"]: float(doc[field])}
                            if isinstance(doc[field], (int, float))
                            else {doc["_id"]: 0}
                        )
            
            await pipe.execute()
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to update Redis: {str(e)}")
            return False
    
    async def delete(
        self,
        collection: str,
        query: Dict[str, Any]
    ) -> bool:
        """
        Delete data from Redis.
        
        Args:
            collection: Hash name
            query: Query criteria
            
        Returns:
            bool: True if deletion successful, False otherwise
        """
        try:
            # Find matching documents
            documents = await self.find(collection, query)
            
            if not documents:
                return False
            
            pipe = self.client.pipeline()
            
            for doc in documents:
                # Delete hash
                pipe.delete(doc["_id"])
                
                # Remove from indexes
                indexes = await self.client.hgetall(f"{collection}:indexes")
                for field in indexes:
                    pipe.zrem(f"{collection}:index:{field}", doc["_id"])
            
            await pipe.execute()
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to delete from Redis: {str(e)}")
            return False
    
    async def aggregate(
        self,
        collection: str,
        pipeline: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        Perform aggregation operations in Redis.
        
        Args:
            collection: Hash name
            pipeline: Aggregation pipeline
            
        Returns:
            List[Dict[str, Any]]: Aggregation results
        """
        try:
            # Get all documents first
            documents = await self.find(collection, {})
            results = documents
            
            for stage in pipeline:
                if "$match" in stage:
                    # Filter documents
                    results = [
                        doc for doc in results
                        if all(
                            field in doc and doc[field] == value
                            for field, value in stage["$match"].items()
                        )
                    ]
                
                elif "$group" in stage:
                    grouped = {}
                    
                    for doc in results:
                        # Get group key
                        if "_id" in stage["$group"]:
                            if isinstance(stage["$group"]["_id"], str):
                                key = doc.get(
                                    stage["$group"]["_id"].replace("$", "")
                                )
                            else:
                                key = tuple(
                                    doc.get(k.replace("$", ""))
                                    for k in stage["$group"]["_id"].values()
                                )
                        else:
                            key = None
                        
                        if key not in grouped:
                            grouped[key] = {
                                "_id": key,
                                **{
                                    k: 0 for k in stage["$group"]
                                    if k != "_id"
                                }
                            }
                        
                        # Apply aggregation operators
                        for field, value in stage["$group"].items():
                            if field == "_id":
                                continue
                            
                            if isinstance(value, dict):
                                op = list(value.keys())[0]
                                field_name = value[op].replace("$", "")
                                
                                if op == "$sum":
                                    grouped[key][field] += doc.get(field_name, 0)
                                elif op == "$avg":
                                    # We'll need to track count for average
                                    if f"{field}_count" not in grouped[key]:
                                        grouped[key][f"{field}_count"] = 0
                                    grouped[key][field] += doc.get(field_name, 0)
                                    grouped[key][f"{field}_count"] += 1
                                elif op == "$min":
                                    val = doc.get(field_name)
                                    if val is not None:
                                        if grouped[key][field] == 0:
                                            grouped[key][field] = val
                                        else:
                                            grouped[key][field] = min(
                                                grouped[key][field],
                                                val
                                            )
                                elif op == "$max":
                                    val = doc.get(field_name)
                                    if val is not None:
                                        grouped[key][field] = max(
                                            grouped[key][field],
                                            val
                                        )
                    
                    # Calculate averages
                    for group in grouped.values():
                        for field in list(group.keys()):
                            if f"{field}_count" in group:
                                group[field] = (
                                    group[field] / group[f"{field}_count"]
                                )
                                del group[f"{field}_count"]
                    
                    results = list(grouped.values())
                
                elif "$sort" in stage:
                    # Sort results
                    for field, direction in reversed(stage["$sort"].items()):
                        results.sort(
                            key=lambda x: x.get(field, 0),
                            reverse=direction == -1
                        )
                
                elif "$limit" in stage:
                    results = results[:stage["$limit"]]
            
            return results
            
        except Exception as e:
            self.logger.error(f"Failed to perform Redis aggregation: {str(e)}")
            return []
