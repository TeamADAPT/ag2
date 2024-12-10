"""
Neo4j Database Adapter
This module provides the Neo4j-specific implementation of the base database adapter.
"""

import os
from typing import Any, Dict, List, Optional, Union, Tuple
import logging
from datetime import datetime
import json

from neo4j import AsyncGraphDatabase, AsyncDriver
from neo4j.exceptions import ServiceUnavailable
from dotenv import load_dotenv

from .base_adapter import BaseAdapter
from .utils import retry_with_backoff

# Load environment variables
load_dotenv(f".env.{os.getenv('ENVIRONMENT', 'development')}")

class Neo4jAdapter(BaseAdapter):
    """Neo4j adapter implementation"""
    
    def __init__(self):
        super().__init__()
        self.driver: Optional[AsyncDriver] = None
        self._uri = self._build_uri()
        
    def _build_uri(self) -> str:
        """Build Neo4j connection URI from environment variables"""
        return os.getenv('NEO4J_URI', 'bolt://localhost:7687')
    
    @retry_with_backoff(max_retries=3, base_delay=1)
    async def connect(self) -> bool:
        """
        Establish connection to Neo4j.
        
        Returns:
            bool: True if connection successful, False otherwise
        """
        try:
            if not self.driver:
                self.driver = AsyncGraphDatabase.driver(
                    self._uri,
                    auth=(
                        os.getenv('NEO4J_USER'),
                        os.getenv('NEO4J_PASSWORD')
                    ),
                    max_connection_lifetime=3600,
                    max_connection_pool_size=50,
                    connection_acquisition_timeout=60
                )
                
                # Verify connection
                async with self.driver.session() as session:
                    await session.run("RETURN 1")
                
                self._initialized = True
                self.logger.info("Neo4j connection established")
            return True
            
        except ServiceUnavailable:
            self.logger.error("Neo4j service unavailable")
            return False
        except Exception as e:
            self.logger.error(f"Failed to connect to Neo4j: {str(e)}")
            return False
    
    async def disconnect(self) -> bool:
        """
        Close Neo4j connection.
        
        Returns:
            bool: True if disconnection successful, False otherwise
        """
        try:
            if self.driver:
                await self.driver.close()
                self.driver = None
                self._initialized = False
                self.logger.info("Neo4j connection closed")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to disconnect from Neo4j: {str(e)}")
            return False
    
    async def execute(
        self,
        query: str,
        params: Optional[Dict[str, Any]] = None
    ) -> Any:
        """
        Execute a Cypher query.
        
        Args:
            query: Cypher query to execute
            params: Query parameters
            
        Returns:
            Any: Query result
        """
        try:
            async with self.driver.session() as session:
                result = await session.run(query, parameters=params or {})
                return await result.data()
                
        except Exception as e:
            self.logger.error(f"Failed to execute Neo4j query: {str(e)}")
            raise
    
    async def create_collection(
        self,
        name: str,
        schema: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        Create a new node label in Neo4j.
        
        Args:
            name: Node label name
            schema: Optional schema constraints
            
        Returns:
            bool: True if creation successful, False otherwise
        """
        try:
            # Neo4j doesn't require explicit collection creation
            # But we can create constraints if schema is provided
            if schema:
                constraints = []
                
                # Property existence constraints
                if "required" in schema:
                    for prop in schema["required"]:
                        constraints.append(
                            f"CREATE CONSTRAINT {name}_{prop}_exists "
                            f"IF NOT EXISTS FOR (n:{name}) "
                            f"REQUIRE n.{prop} IS NOT NULL"
                        )
                
                # Property uniqueness constraints
                if "unique" in schema:
                    for prop in schema["unique"]:
                        constraints.append(
                            f"CREATE CONSTRAINT {name}_{prop}_unique "
                            f"IF NOT EXISTS FOR (n:{name}) "
                            f"REQUIRE n.{prop} IS UNIQUE"
                        )
                
                # Property type constraints
                if "properties" in schema:
                    for prop, prop_schema in schema["properties"].items():
                        if "type" in prop_schema:
                            constraints.append(
                                f"CREATE CONSTRAINT {name}_{prop}_type "
                                f"IF NOT EXISTS FOR (n:{name}) "
                                f"REQUIRE n.{prop} IS {prop_schema['type']}"
                            )
                
                for constraint in constraints:
                    await self.execute(constraint)
            
            self.logger.info(f"Created Neo4j node label: {name}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to create Neo4j node label: {str(e)}")
            return False
    
    async def create_index(
        self,
        collection: str,
        index: Union[str, Tuple[str, int]]
    ) -> bool:
        """
        Create an index on a Neo4j node label.
        
        Args:
            collection: Node label name
            index: Property to index
            
        Returns:
            bool: True if creation successful, False otherwise
        """
        try:
            if isinstance(index, tuple):
                field, _ = index  # Neo4j doesn't support ASC/DESC in index creation
            else:
                field = index
            
            query = f"""
            CREATE INDEX {collection}_{field}_idx
            IF NOT EXISTS FOR (n:{collection})
            ON (n.{field})
            """
            
            await self.execute(query)
            self.logger.info(f"Created Neo4j index: {collection}_{field}_idx")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to create Neo4j index: {str(e)}")
            return False
    
    async def create_stream(self, name: str) -> bool:
        """
        Create a new change feed in Neo4j.
        
        Args:
            name: Node label to stream
            
        Returns:
            bool: True if creation successful, False otherwise
        """
        try:
            # Neo4j Enterprise Edition supports change data capture
            # For Community Edition, we'll implement a timestamp-based approach
            query = f"""
            CREATE CONSTRAINT {name}_timestamp_exists
            IF NOT EXISTS FOR (n:{name})
            REQUIRE n.timestamp IS NOT NULL
            """
            
            await self.execute(query)
            self.logger.info(f"Created Neo4j change feed for: {name}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to create Neo4j change feed: {str(e)}")
            return False
    
    async def create_channel(self, name: str) -> bool:
        """
        Create a new pub/sub channel in Neo4j.
        
        Args:
            name: Channel name
            
        Returns:
            bool: True if creation successful, False otherwise
        """
        try:
            # Neo4j doesn't have built-in pub/sub
            # We'll implement it using nodes and relationships
            query = """
            CREATE (c:Channel {name: $name, created_at: datetime()})
            RETURN c
            """
            
            await self.execute(query, {"name": name})
            self.logger.info(f"Created Neo4j pub/sub channel: {name}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to create Neo4j pub/sub channel: {str(e)}")
            return False
    
    async def insert(
        self,
        collection: str,
        data: Union[Dict[str, Any], List[Dict[str, Any]]]
    ) -> bool:
        """
        Create nodes in Neo4j.
        
        Args:
            collection: Node label
            data: Node properties
            
        Returns:
            bool: True if insertion successful, False otherwise
        """
        try:
            if isinstance(data, dict):
                data = [data]
            
            # Convert any non-primitive types to strings
            for item in data:
                for key, value in item.items():
                    if not isinstance(value, (str, int, float, bool, type(None))):
                        item[key] = json.dumps(value)
            
            query = f"""
            UNWIND $data AS item
            CREATE (n:{collection})
            SET n = item
            SET n.created_at = datetime()
            """
            
            await self.execute(query, {"data": data})
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to insert into Neo4j: {str(e)}")
            return False
    
    async def find(
        self,
        collection: str,
        query: Dict[str, Any],
        projection: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """
        Find nodes in Neo4j.
        
        Args:
            collection: Node label
            query: Match criteria
            projection: Properties to return
            
        Returns:
            List[Dict[str, Any]]: Query results
        """
        try:
            # Build match conditions
            conditions = []
            for key, value in query.items():
                if isinstance(value, (int, float, bool)):
                    conditions.append(f"n.{key} = {value}")
                else:
                    conditions.append(f"n.{key} = '{value}'")
            
            # Build return clause
            if projection:
                return_props = [
                    f"n.{prop}" for prop, include in projection.items() if include
                ]
                return_clause = f"RETURN {', '.join(return_props)}"
            else:
                return_clause = "RETURN n"
            
            cypher_query = f"""
            MATCH (n:{collection})
            {f"WHERE {' AND '.join(conditions)}" if conditions else ""}
            {return_clause}
            """
            
            result = await self.execute(cypher_query)
            return result
            
        except Exception as e:
            self.logger.error(f"Failed to query Neo4j: {str(e)}")
            return []
    
    async def update(
        self,
        collection: str,
        query: Dict[str, Any],
        update: Dict[str, Any]
    ) -> bool:
        """
        Update nodes in Neo4j.
        
        Args:
            collection: Node label
            query: Match criteria
            update: Properties to update
            
        Returns:
            bool: True if update successful, False otherwise
        """
        try:
            # Build match conditions
            conditions = []
            for key, value in query.items():
                if isinstance(value, (int, float, bool)):
                    conditions.append(f"n.{key} = {value}")
                else:
                    conditions.append(f"n.{key} = '{value}'")
            
            # Build set clause
            set_items = []
            for key, value in update.items():
                if isinstance(value, (int, float, bool)):
                    set_items.append(f"n.{key} = {value}")
                else:
                    set_items.append(f"n.{key} = '{value}'")
            
            cypher_query = f"""
            MATCH (n:{collection})
            {f"WHERE {' AND '.join(conditions)}" if conditions else ""}
            SET {', '.join(set_items)}
            SET n.updated_at = datetime()
            """
            
            await self.execute(cypher_query)
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to update Neo4j: {str(e)}")
            return False
    
    async def delete(
        self,
        collection: str,
        query: Dict[str, Any]
    ) -> bool:
        """
        Delete nodes from Neo4j.
        
        Args:
            collection: Node label
            query: Match criteria
            
        Returns:
            bool: True if deletion successful, False otherwise
        """
        try:
            # Build match conditions
            conditions = []
            for key, value in query.items():
                if isinstance(value, (int, float, bool)):
                    conditions.append(f"n.{key} = {value}")
                else:
                    conditions.append(f"n.{key} = '{value}'")
            
            cypher_query = f"""
            MATCH (n:{collection})
            {f"WHERE {' AND '.join(conditions)}" if conditions else ""}
            DETACH DELETE n
            """
            
            await self.execute(cypher_query)
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to delete from Neo4j: {str(e)}")
            return False
    
    async def aggregate(
        self,
        collection: str,
        pipeline: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        Perform aggregation operations in Neo4j.
        
        Args:
            collection: Node label
            pipeline: Aggregation pipeline
            
        Returns:
            List[Dict[str, Any]]: Aggregation results
        """
        try:
            # Convert MongoDB-style pipeline to Cypher
            match_clause = f"MATCH (n:{collection})"
            where_clause = ""
            with_clause = ""
            return_clause = "RETURN n"
            order_clause = ""
            limit_clause = ""
            
            for stage in pipeline:
                if "$match" in stage:
                    conditions = []
                    for field, value in stage["$match"].items():
                        if isinstance(value, dict):
                            for op, val in value.items():
                                if op == "$gt":
                                    conditions.append(f"n.{field} > {val}")
                                elif op == "$gte":
                                    conditions.append(f"n.{field} >= {val}")
                                elif op == "$lt":
                                    conditions.append(f"n.{field} < {val}")
                                elif op == "$lte":
                                    conditions.append(f"n.{field} <= {val}")
                                elif op == "$ne":
                                    conditions.append(f"n.{field} <> {val}")
                        else:
                            conditions.append(f"n.{field} = {value}")
                    
                    if conditions:
                        where_clause = f"WHERE {' AND '.join(conditions)}"
                
                elif "$group" in stage:
                    group_items = []
                    agg_items = []
                    
                    for field, value in stage["$group"].items():
                        if field == "_id":
                            if isinstance(value, str):
                                group_items.append(f"n.{value.replace('$', '')}")
                        else:
                            if isinstance(value, dict):
                                op = list(value.keys())[0]
                                field_name = value[op].replace("$", "")
                                
                                if op == "$sum":
                                    agg_items.append(f"sum(n.{field_name}) AS {field}")
                                elif op == "$avg":
                                    agg_items.append(f"avg(n.{field_name}) AS {field}")
                                elif op == "$min":
                                    agg_items.append(f"min(n.{field_name}) AS {field}")
                                elif op == "$max":
                                    agg_items.append(f"max(n.{field_name}) AS {field}")
                    
                    if group_items:
                        with_clause = f"WITH {', '.join(group_items)}"
                        if agg_items:
                            with_clause += f", {', '.join(agg_items)}"
                
                elif "$sort" in stage:
                    sort_items = []
                    for field, direction in stage["$sort"].items():
                        sort_items.append(
                            f"n.{field} {'ASC' if direction == 1 else 'DESC'}"
                        )
                    
                    if sort_items:
                        order_clause = f"ORDER BY {', '.join(sort_items)}"
                
                elif "$limit" in stage:
                    limit_clause = f"LIMIT {stage['$limit']}"
            
            # Combine all clauses
            cypher_query = " ".join(filter(None, [
                match_clause,
                where_clause,
                with_clause,
                return_clause,
                order_clause,
                limit_clause
            ]))
            
            result = await self.execute(cypher_query)
            return result
            
        except Exception as e:
            self.logger.error(f"Failed to perform Neo4j aggregation: {str(e)}")
            return []
