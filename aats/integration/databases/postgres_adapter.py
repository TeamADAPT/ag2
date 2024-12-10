"""
PostgreSQL Database Adapter
This module provides the PostgreSQL-specific implementation of the base database adapter.
"""

import os
from typing import Any, Dict, List, Optional, Union, Tuple
import logging
import asyncio
from datetime import datetime

import asyncpg
from asyncpg.pool import Pool
from dotenv import load_dotenv

from .base_adapter import BaseAdapter
from .utils import retry_with_backoff

# Load environment variables
load_dotenv(f".env.{os.getenv('ENVIRONMENT', 'development')}")

class PostgresAdapter(BaseAdapter):
    """PostgreSQL adapter implementation"""
    
    def __init__(self):
        super().__init__()
        self.pool: Optional[Pool] = None
        self._dsn = self._build_dsn()
        
    def _build_dsn(self) -> str:
        """Build PostgreSQL connection string from environment variables"""
        return (
            f"postgresql://{os.getenv('POSTGRES_USER')}:{os.getenv('POSTGRES_PASSWORD')}"
            f"@{os.getenv('POSTGRES_HOST')}:{os.getenv('POSTGRES_PORT')}"
            f"/{os.getenv('POSTGRES_DB')}"
        )
    
    @retry_with_backoff(max_retries=3, base_delay=1)
    async def connect(self) -> bool:
        """
        Establish connection pool to PostgreSQL.
        
        Returns:
            bool: True if connection successful, False otherwise
        """
        try:
            if not self.pool:
                self.pool = await asyncpg.create_pool(
                    dsn=self._dsn,
                    min_size=5,
                    max_size=20,
                    command_timeout=60,
                    max_queries=50000,
                    max_cached_statement_lifetime=300,
                    max_inactive_connection_lifetime=300
                )
                self._initialized = True
                self.logger.info("PostgreSQL connection pool established")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to connect to PostgreSQL: {str(e)}")
            return False
    
    async def disconnect(self) -> bool:
        """
        Close PostgreSQL connection pool.
        
        Returns:
            bool: True if disconnection successful, False otherwise
        """
        try:
            if self.pool:
                await self.pool.close()
                self.pool = None
                self._initialized = False
                self.logger.info("PostgreSQL connection pool closed")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to disconnect from PostgreSQL: {str(e)}")
            return False
    
    async def execute(
        self,
        query: str,
        params: Optional[Dict[str, Any]] = None
    ) -> Any:
        """
        Execute a PostgreSQL query.
        
        Args:
            query: SQL query to execute
            params: Optional query parameters
            
        Returns:
            Any: Query result
        """
        try:
            async with self.pool.acquire() as conn:
                async with conn.transaction():
                    if params:
                        result = await conn.execute(query, *params.values())
                    else:
                        result = await conn.execute(query)
                    return result
                    
        except Exception as e:
            self.logger.error(f"Failed to execute PostgreSQL query: {str(e)}")
            raise
    
    async def create_collection(
        self,
        name: str,
        schema: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        Create a new table in PostgreSQL.
        
        Args:
            name: Table name
            schema: Table schema definition
            
        Returns:
            bool: True if creation successful, False otherwise
        """
        try:
            if not schema:
                raise ValueError("Schema is required for PostgreSQL table creation")
                
            # Convert schema to PostgreSQL table definition
            columns = []
            for column_name, column_def in schema.items():
                columns.append(f"{column_name} {column_def}")
            
            query = f"""
            CREATE TABLE IF NOT EXISTS {name} (
                {', '.join(columns)}
            )
            """
            
            await self.execute(query)
            self.logger.info(f"Created PostgreSQL table: {name}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to create PostgreSQL table: {str(e)}")
            return False
    
    async def create_index(
        self,
        collection: str,
        index: Union[str, Tuple[str, int]]
    ) -> bool:
        """
        Create an index on a PostgreSQL table.
        
        Args:
            collection: Table name
            index: Index definition
            
        Returns:
            bool: True if creation successful, False otherwise
        """
        try:
            if isinstance(index, tuple):
                field, order = index
                direction = "ASC" if order == 1 else "DESC"
                index_name = f"{collection}_{field}_idx"
                query = f"""
                CREATE INDEX IF NOT EXISTS {index_name}
                ON {collection} ({field} {direction})
                """
            else:
                index_name = f"{collection}_{index}_idx"
                query = f"""
                CREATE INDEX IF NOT EXISTS {index_name}
                ON {collection} ({index})
                """
            
            await self.execute(query)
            self.logger.info(f"Created PostgreSQL index: {index_name}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to create PostgreSQL index: {str(e)}")
            return False
    
    async def create_stream(self, name: str) -> bool:
        """
        Create a new notification channel in PostgreSQL.
        
        Args:
            name: Channel name
            
        Returns:
            bool: True if creation successful, False otherwise
        """
        try:
            # PostgreSQL uses LISTEN/NOTIFY for streaming
            # We'll create a function and trigger for change notifications
            queries = [
                f"""
                CREATE OR REPLACE FUNCTION notify_{name}_changes()
                RETURNS trigger AS $$
                BEGIN
                    PERFORM pg_notify(
                        '{name}_channel',
                        json_build_object(
                            'operation', TG_OP,
                            'record', row_to_json(NEW)
                        )::text
                    );
                    RETURN NEW;
                END;
                $$ LANGUAGE plpgsql;
                """,
                f"""
                DROP TRIGGER IF EXISTS {name}_notify_trigger
                ON {name};
                """,
                f"""
                CREATE TRIGGER {name}_notify_trigger
                AFTER INSERT OR UPDATE OR DELETE ON {name}
                FOR EACH ROW EXECUTE FUNCTION notify_{name}_changes();
                """
            ]
            
            for query in queries:
                await self.execute(query)
                
            self.logger.info(f"Created PostgreSQL notification channel: {name}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to create PostgreSQL notification channel: {str(e)}")
            return False
    
    async def create_channel(self, name: str) -> bool:
        """
        Create a new pub/sub channel in PostgreSQL.
        
        Args:
            name: Channel name
            
        Returns:
            bool: True if creation successful, False otherwise
        """
        try:
            # PostgreSQL uses LISTEN/NOTIFY for pub/sub
            async with self.pool.acquire() as conn:
                await conn.add_listener(name, self._channel_callback)
            self.logger.info(f"Created PostgreSQL pub/sub channel: {name}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to create PostgreSQL pub/sub channel: {str(e)}")
            return False
    
    async def _channel_callback(
        self,
        connection: asyncpg.Connection,
        pid: int,
        channel: str,
        payload: str
    ):
        """Callback for PostgreSQL notifications"""
        self.logger.debug(f"Received notification on channel {channel}: {payload}")
    
    async def insert(
        self,
        collection: str,
        data: Union[Dict[str, Any], List[Dict[str, Any]]]
    ) -> bool:
        """
        Insert data into a PostgreSQL table.
        
        Args:
            collection: Table name
            data: Data to insert
            
        Returns:
            bool: True if insertion successful, False otherwise
        """
        try:
            if isinstance(data, dict):
                data = [data]
                
            # Prepare the INSERT statement
            columns = data[0].keys()
            placeholders = [
                f"({','.join(f'${i}' for i in range(j*len(columns)+1, (j+1)*len(columns)+1))})"
                for j in range(len(data))
            ]
            
            query = f"""
            INSERT INTO {collection} ({','.join(columns)})
            VALUES {','.join(placeholders)}
            """
            
            # Flatten the values for asyncpg
            values = [v for d in data for v in d.values()]
            
            await self.execute(query, {"values": values})
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to insert into PostgreSQL: {str(e)}")
            return False
    
    async def find(
        self,
        collection: str,
        query: Dict[str, Any],
        projection: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """
        Find documents in a PostgreSQL table.
        
        Args:
            collection: Table name
            query: Query criteria
            projection: Fields to return
            
        Returns:
            List[Dict[str, Any]]: Query results
        """
        try:
            # Build WHERE clause
            conditions = []
            values = []
            for i, (key, value) in enumerate(query.items(), 1):
                conditions.append(f"{key} = ${i}")
                values.append(value)
            
            # Build SELECT clause
            select_fields = "*"
            if projection:
                select_fields = ",".join(
                    field for field, include in projection.items() if include
                )
            
            query_str = f"""
            SELECT {select_fields}
            FROM {collection}
            {"WHERE " + " AND ".join(conditions) if conditions else ""}
            """
            
            async with self.pool.acquire() as conn:
                results = await conn.fetch(query_str, *values)
                return [dict(row) for row in results]
                
        except Exception as e:
            self.logger.error(f"Failed to query PostgreSQL: {str(e)}")
            return []
    
    async def update(
        self,
        collection: str,
        query: Dict[str, Any],
        update: Dict[str, Any]
    ) -> bool:
        """
        Update documents in a PostgreSQL table.
        
        Args:
            collection: Table name
            query: Query criteria
            update: Update operations
            
        Returns:
            bool: True if update successful, False otherwise
        """
        try:
            # Build SET clause
            set_values = []
            values = []
            for i, (key, value) in enumerate(update.items(), 1):
                set_values.append(f"{key} = ${i}")
                values.append(value)
            
            # Build WHERE clause
            conditions = []
            for i, (key, value) in enumerate(query.items(), len(values) + 1):
                conditions.append(f"{key} = ${i}")
                values.append(value)
            
            query_str = f"""
            UPDATE {collection}
            SET {', '.join(set_values)}
            {"WHERE " + " AND ".join(conditions) if conditions else ""}
            """
            
            await self.execute(query_str, {"values": values})
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to update PostgreSQL: {str(e)}")
            return False
    
    async def delete(
        self,
        collection: str,
        query: Dict[str, Any]
    ) -> bool:
        """
        Delete documents from a PostgreSQL table.
        
        Args:
            collection: Table name
            query: Query criteria
            
        Returns:
            bool: True if deletion successful, False otherwise
        """
        try:
            # Build WHERE clause
            conditions = []
            values = []
            for i, (key, value) in enumerate(query.items(), 1):
                conditions.append(f"{key} = ${i}")
                values.append(value)
            
            query_str = f"""
            DELETE FROM {collection}
            {"WHERE " + " AND ".join(conditions) if conditions else ""}
            """
            
            await self.execute(query_str, {"values": values})
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to delete from PostgreSQL: {str(e)}")
            return False
    
    async def aggregate(
        self,
        collection: str,
        pipeline: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        Perform aggregation operations in PostgreSQL.
        
        Args:
            collection: Table name
            pipeline: Aggregation pipeline
            
        Returns:
            List[Dict[str, Any]]: Aggregation results
        """
        try:
            # Convert MongoDB-style pipeline to PostgreSQL
            query_parts = ["SELECT"]
            
            for stage in pipeline:
                if "$group" in stage:
                    group_fields = []
                    agg_fields = []
                    
                    for field, value in stage["$group"].items():
                        if field == "_id":
                            if isinstance(value, str):
                                group_fields.append(value.replace("$", ""))
                            elif isinstance(value, dict):
                                # Handle complex grouping
                                pass
                        else:
                            # Handle aggregation operators
                            if isinstance(value, dict):
                                op = list(value.keys())[0]
                                field_name = value[op].replace("$", "")
                                
                                if op == "$sum":
                                    agg_fields.append(f"SUM({field_name}) as {field}")
                                elif op == "$avg":
                                    agg_fields.append(f"AVG({field_name}) as {field}")
                                elif op == "$min":
                                    agg_fields.append(f"MIN({field_name}) as {field}")
                                elif op == "$max":
                                    agg_fields.append(f"MAX({field_name}) as {field}")
                    
                    select_fields = group_fields + agg_fields
                    query_parts[0] = f"SELECT {', '.join(select_fields)}"
                    if group_fields:
                        query_parts.append(f"GROUP BY {', '.join(group_fields)}")
                
                elif "$match" in stage:
                    conditions = []
                    for field, value in stage["$match"].items():
                        if isinstance(value, dict):
                            # Handle operators
                            for op, val in value.items():
                                if op == "$gt":
                                    conditions.append(f"{field} > {val}")
                                elif op == "$gte":
                                    conditions.append(f"{field} >= {val}")
                                elif op == "$lt":
                                    conditions.append(f"{field} < {val}")
                                elif op == "$lte":
                                    conditions.append(f"{field} <= {val}")
                                elif op == "$ne":
                                    conditions.append(f"{field} != {val}")
                        else:
                            conditions.append(f"{field} = {value}")
                    
                    if conditions:
                        query_parts.append(f"WHERE {' AND '.join(conditions)}")
                
                elif "$sort" in stage:
                    sort_fields = []
                    for field, direction in stage["$sort"].items():
                        sort_fields.append(
                            f"{field} {'ASC' if direction == 1 else 'DESC'}"
                        )
                    
                    if sort_fields:
                        query_parts.append(f"ORDER BY {', '.join(sort_fields)}")
                
                elif "$limit" in stage:
                    query_parts.append(f"LIMIT {stage['$limit']}")
            
            # Add FROM clause after SELECT
            query_parts.insert(1, f"FROM {collection}")
            
            # Execute the query
            query_str = " ".join(query_parts)
            async with self.pool.acquire() as conn:
                results = await conn.fetch(query_str)
                return [dict(row) for row in results]
                
        except Exception as e:
            self.logger.error(f"Failed to perform PostgreSQL aggregation: {str(e)}")
            return []
