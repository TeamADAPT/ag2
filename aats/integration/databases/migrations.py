"""
Database Migrations
This module handles database schema migrations and data transformations.
"""

import asyncio
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime
import json

from .db_factory import db_factory, DatabaseType
from .schema import get_schema, get_indexes
from .utils import retry_with_backoff

logger = logging.getLogger(__name__)

class Migration:
    """Base class for database migrations"""
    
    def __init__(
        self,
        version: str,
        description: str,
        db_type: DatabaseType
    ):
        self.version = version
        self.description = description
        self.db_type = db_type
        self.created_at = datetime.now()
    
    async def up(self) -> bool:
        """
        Apply migration.
        Must be implemented by subclasses.
        
        Returns:
            bool: True if successful
        """
        raise NotImplementedError
    
    async def down(self) -> bool:
        """
        Rollback migration.
        Must be implemented by subclasses.
        
        Returns:
            bool: True if successful
        """
        raise NotImplementedError

class MigrationManager:
    """Manages database migrations"""
    
    def __init__(self):
        self.migrations: Dict[DatabaseType, List[Migration]] = {
            db_type: [] for db_type in DatabaseType
        }
        self._applied_versions: Dict[DatabaseType, set] = {
            db_type: set() for db_type in DatabaseType
        }
    
    async def initialize(self) -> bool:
        """
        Initialize migration tracking tables.
        
        Returns:
            bool: True if successful
        """
        try:
            # Create migration tracking tables in each database
            for db_type in DatabaseType:
                adapter = await db_factory.get_adapter(db_type)
                if not adapter:
                    continue
                
                if db_type == DatabaseType.POSTGRES:
                    await adapter.execute("""
                        CREATE TABLE IF NOT EXISTS migrations (
                            version VARCHAR(50) PRIMARY KEY,
                            description TEXT,
                            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                            applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                        )
                    """)
                
                elif db_type == DatabaseType.MONGODB:
                    await adapter.create_collection(
                        "migrations",
                        {
                            "validator": {
                                "$jsonSchema": {
                                    "bsonType": "object",
                                    "required": ["version", "description", "applied_at"],
                                    "properties": {
                                        "version": {"bsonType": "string"},
                                        "description": {"bsonType": "string"},
                                        "applied_at": {"bsonType": "date"}
                                    }
                                }
                            }
                        }
                    )
                
                elif db_type == DatabaseType.NEO4J:
                    await adapter.execute("""
                        CREATE CONSTRAINT migration_version IF NOT EXISTS
                        FOR (m:Migration) REQUIRE m.version IS UNIQUE
                    """)
                
                elif db_type == DatabaseType.REDIS:
                    # Redis uses a hash to track migrations
                    await adapter.create_collection("migrations")
                
                # Load applied migrations
                await self._load_applied_migrations(db_type)
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to initialize migrations: {str(e)}")
            return False
    
    async def _load_applied_migrations(self, db_type: DatabaseType):
        """Load applied migration versions from database"""
        try:
            adapter = await db_factory.get_adapter(db_type)
            if not adapter:
                return
            
            if db_type == DatabaseType.POSTGRES:
                result = await adapter.execute(
                    "SELECT version FROM migrations"
                )
                self._applied_versions[db_type] = {
                    row["version"] for row in result
                }
            
            elif db_type == DatabaseType.MONGODB:
                result = await adapter.find(
                    "migrations",
                    {},
                    {"version": 1}
                )
                self._applied_versions[db_type] = {
                    doc["version"] for doc in result
                }
            
            elif db_type == DatabaseType.NEO4J:
                result = await adapter.execute(
                    "MATCH (m:Migration) RETURN m.version"
                )
                self._applied_versions[db_type] = {
                    row["m.version"] for row in result
                }
            
            elif db_type == DatabaseType.REDIS:
                result = await adapter.execute(
                    "HKEYS",
                    {"key": "migrations"}
                )
                self._applied_versions[db_type] = set(result or [])
            
        except Exception as e:
            logger.error(
                f"Failed to load applied migrations for {db_type}: {str(e)}"
            )
    
    def register_migration(self, migration: Migration):
        """Register a new migration"""
        self.migrations[migration.db_type].append(migration)
    
    async def apply_migrations(
        self,
        db_type: Optional[DatabaseType] = None,
        target_version: Optional[str] = None
    ) -> bool:
        """
        Apply pending migrations.
        
        Args:
            db_type: Optional database type to migrate
            target_version: Optional version to migrate to
            
        Returns:
            bool: True if successful
        """
        try:
            db_types = [db_type] if db_type else DatabaseType
            
            for current_db in db_types:
                # Sort migrations by version
                pending = sorted(
                    [
                        m for m in self.migrations[current_db]
                        if m.version not in self._applied_versions[current_db]
                    ],
                    key=lambda x: x.version
                )
                
                if target_version:
                    # Filter migrations up to target version
                    pending = [
                        m for m in pending
                        if m.version <= target_version
                    ]
                
                for migration in pending:
                    logger.info(
                        f"Applying migration {migration.version} "
                        f"for {current_db}: {migration.description}"
                    )
                    
                    if await migration.up():
                        # Record successful migration
                        await self._record_migration(current_db, migration)
                        self._applied_versions[current_db].add(migration.version)
                    else:
                        logger.error(
                            f"Failed to apply migration {migration.version} "
                            f"for {current_db}"
                        )
                        return False
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to apply migrations: {str(e)}")
            return False
    
    async def rollback_migrations(
        self,
        db_type: Optional[DatabaseType] = None,
        target_version: Optional[str] = None
    ) -> bool:
        """
        Rollback migrations.
        
        Args:
            db_type: Optional database type to rollback
            target_version: Optional version to rollback to
            
        Returns:
            bool: True if successful
        """
        try:
            db_types = [db_type] if db_type else DatabaseType
            
            for current_db in db_types:
                # Sort migrations in reverse order
                applied = sorted(
                    [
                        m for m in self.migrations[current_db]
                        if m.version in self._applied_versions[current_db]
                    ],
                    key=lambda x: x.version,
                    reverse=True
                )
                
                if target_version:
                    # Filter migrations after target version
                    applied = [
                        m for m in applied
                        if m.version > target_version
                    ]
                
                for migration in applied:
                    logger.info(
                        f"Rolling back migration {migration.version} "
                        f"for {current_db}"
                    )
                    
                    if await migration.down():
                        # Remove migration record
                        await self._remove_migration(current_db, migration)
                        self._applied_versions[current_db].remove(
                            migration.version
                        )
                    else:
                        logger.error(
                            f"Failed to roll back migration {migration.version} "
                            f"for {current_db}"
                        )
                        return False
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to roll back migrations: {str(e)}")
            return False
    
    @retry_with_backoff()
    async def _record_migration(
        self,
        db_type: DatabaseType,
        migration: Migration
    ):
        """Record a successful migration"""
        try:
            adapter = await db_factory.get_adapter(db_type)
            if not adapter:
                return
            
            migration_data = {
                "version": migration.version,
                "description": migration.description,
                "applied_at": datetime.now()
            }
            
            if db_type == DatabaseType.POSTGRES:
                await adapter.execute(
                    """
                    INSERT INTO migrations (version, description, applied_at)
                    VALUES ($1, $2, $3)
                    """,
                    {"values": list(migration_data.values())}
                )
            
            elif db_type == DatabaseType.MONGODB:
                await adapter.insert("migrations", migration_data)
            
            elif db_type == DatabaseType.NEO4J:
                await adapter.execute(
                    """
                    CREATE (m:Migration {
                        version: $version,
                        description: $description,
                        applied_at: datetime($applied_at)
                    })
                    """,
                    migration_data
                )
            
            elif db_type == DatabaseType.REDIS:
                await adapter.execute(
                    "HSET",
                    {
                        "key": "migrations",
                        "field": migration.version,
                        "value": json.dumps(migration_data)
                    }
                )
            
        except Exception as e:
            logger.error(
                f"Failed to record migration {migration.version}: {str(e)}"
            )
            raise
    
    @retry_with_backoff()
    async def _remove_migration(
        self,
        db_type: DatabaseType,
        migration: Migration
    ):
        """Remove a migration record"""
        try:
            adapter = await db_factory.get_adapter(db_type)
            if not adapter:
                return
            
            if db_type == DatabaseType.POSTGRES:
                await adapter.execute(
                    "DELETE FROM migrations WHERE version = $1",
                    {"values": [migration.version]}
                )
            
            elif db_type == DatabaseType.MONGODB:
                await adapter.delete(
                    "migrations",
                    {"version": migration.version}
                )
            
            elif db_type == DatabaseType.NEO4J:
                await adapter.execute(
                    """
                    MATCH (m:Migration {version: $version})
                    DELETE m
                    """,
                    {"version": migration.version}
                )
            
            elif db_type == DatabaseType.REDIS:
                await adapter.execute(
                    "HDEL",
                    {
                        "key": "migrations",
                        "field": migration.version
                    }
                )
            
        except Exception as e:
            logger.error(
                f"Failed to remove migration {migration.version}: {str(e)}"
            )
            raise

class CreateInitialSchema(Migration):
    """Initial schema creation migration"""
    
    def __init__(self, db_type: DatabaseType):
        super().__init__(
            "0001",
            "Create initial schema",
            db_type
        )
    
    async def up(self) -> bool:
        """Create initial schema"""
        try:
            adapter = await db_factory.get_adapter(self.db_type)
            if not adapter:
                return False
            
            # Create collections/tables
            for collection, schema in get_schema(
                self.db_type.value,
                None
            ).items():
                await adapter.create_collection(collection, schema)
            
            # Create indexes
            for collection, indexes in get_indexes(
                self.db_type.value,
                None
            ).items():
                for index in indexes:
                    await adapter.create_index(collection, index)
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to create initial schema: {str(e)}")
            return False
    
    async def down(self) -> bool:
        """Drop initial schema"""
        try:
            adapter = await db_factory.get_adapter(self.db_type)
            if not adapter:
                return False
            
            # Drop collections/tables
            for collection in get_schema(self.db_type.value, None).keys():
                if self.db_type == DatabaseType.POSTGRES:
                    await adapter.execute(f"DROP TABLE IF EXISTS {collection}")
                elif self.db_type == DatabaseType.MONGODB:
                    await adapter.execute(
                        "drop_collection",
                        {"name": collection}
                    )
                elif self.db_type == DatabaseType.NEO4J:
                    await adapter.execute(
                        f"MATCH (n:{collection}) DETACH DELETE n"
                    )
                elif self.db_type == DatabaseType.REDIS:
                    await adapter.execute("DEL", {"key": collection})
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to drop initial schema: {str(e)}")
            return False

# Global migration manager instance
migration_manager = MigrationManager()

# Register initial migrations
for db_type in DatabaseType:
    migration_manager.register_migration(CreateInitialSchema(db_type))
