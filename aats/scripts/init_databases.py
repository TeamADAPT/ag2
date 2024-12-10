"""
Database Initialization Script
This script initializes all required databases and their schemas for the AATS system.
"""

import asyncio
import os
from typing import Dict, Any
import logging
from dotenv import load_dotenv

# Database adapters
from aats.integration.databases.postgres_adapter import PostgresAdapter
from aats.integration.databases.mongodb_adapter import MongoDBAdapter
from aats.integration.databases.neo4j_adapter import Neo4jAdapter
from aats.integration.databases.redis_adapter import RedisAdapter

# Load environment variables
load_dotenv(f".env.{os.getenv('ENVIRONMENT', 'development')}")

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class DatabaseInitializer:
    """Handles initialization of all database systems"""
    
    def __init__(self):
        self.postgres = PostgresAdapter()
        self.mongodb = MongoDBAdapter()
        self.neo4j = Neo4jAdapter()
        self.redis = RedisAdapter()
        
    async def init_postgres(self) -> bool:
        """Initialize PostgreSQL database"""
        try:
            logger.info("Initializing PostgreSQL...")
            
            # Create main tables
            tables = [
                """
                CREATE TABLE IF NOT EXISTS agents (
                    id SERIAL PRIMARY KEY,
                    name VARCHAR(255) NOT NULL,
                    type VARCHAR(50) NOT NULL,
                    status VARCHAR(50) NOT NULL,
                    capabilities JSONB,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
                """,
                """
                CREATE TABLE IF NOT EXISTS tasks (
                    id SERIAL PRIMARY KEY,
                    agent_id INTEGER REFERENCES agents(id),
                    type VARCHAR(50) NOT NULL,
                    status VARCHAR(50) NOT NULL,
                    priority INTEGER,
                    data JSONB,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
                """,
                """
                CREATE TABLE IF NOT EXISTS agent_interactions (
                    id SERIAL PRIMARY KEY,
                    source_agent_id INTEGER REFERENCES agents(id),
                    target_agent_id INTEGER REFERENCES agents(id),
                    interaction_type VARCHAR(50) NOT NULL,
                    data JSONB,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
                """,
                """
                CREATE TABLE IF NOT EXISTS system_metrics (
                    id SERIAL PRIMARY KEY,
                    metric_type VARCHAR(50) NOT NULL,
                    value FLOAT NOT NULL,
                    metadata JSONB,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
                """
            ]
            
            for table in tables:
                await self.postgres.execute(table)
            
            logger.info("PostgreSQL initialization completed")
            return True
            
        except Exception as e:
            logger.error(f"PostgreSQL initialization failed: {str(e)}")
            return False

    async def init_mongodb(self) -> bool:
        """Initialize MongoDB database"""
        try:
            logger.info("Initializing MongoDB...")
            
            # Create collections with validators
            collections = {
                "agent_states": {
                    "validator": {
                        "$jsonSchema": {
                            "bsonType": "object",
                            "required": ["agent_id", "state", "timestamp"],
                            "properties": {
                                "agent_id": {"bsonType": "string"},
                                "state": {"bsonType": "object"},
                                "timestamp": {"bsonType": "date"}
                            }
                        }
                    }
                },
                "task_history": {
                    "validator": {
                        "$jsonSchema": {
                            "bsonType": "object",
                            "required": ["task_id", "status", "timestamp"],
                            "properties": {
                                "task_id": {"bsonType": "string"},
                                "status": {"bsonType": "string"},
                                "timestamp": {"bsonType": "date"}
                            }
                        }
                    }
                },
                "system_logs": {
                    "validator": {
                        "$jsonSchema": {
                            "bsonType": "object",
                            "required": ["level", "message", "timestamp"],
                            "properties": {
                                "level": {"bsonType": "string"},
                                "message": {"bsonType": "string"},
                                "timestamp": {"bsonType": "date"}
                            }
                        }
                    }
                }
            }
            
            for name, schema in collections.items():
                await self.mongodb.create_collection(name, schema)
            
            # Create indexes
            indexes = {
                "agent_states": [
                    ("agent_id", 1),
                    ("timestamp", -1)
                ],
                "task_history": [
                    ("task_id", 1),
                    ("timestamp", -1)
                ],
                "system_logs": [
                    ("level", 1),
                    ("timestamp", -1)
                ]
            }
            
            for collection, idx_list in indexes.items():
                for idx in idx_list:
                    await self.mongodb.create_index(collection, idx)
            
            logger.info("MongoDB initialization completed")
            return True
            
        except Exception as e:
            logger.error(f"MongoDB initialization failed: {str(e)}")
            return False

    async def init_neo4j(self) -> bool:
        """Initialize Neo4j database"""
        try:
            logger.info("Initializing Neo4j...")
            
            # Create constraints
            constraints = [
                "CREATE CONSTRAINT agent_id IF NOT EXISTS FOR (a:Agent) REQUIRE a.id IS UNIQUE",
                "CREATE CONSTRAINT task_id IF NOT EXISTS FOR (t:Task) REQUIRE t.id IS UNIQUE"
            ]
            
            for constraint in constraints:
                await self.neo4j.execute(constraint)
            
            # Create indexes
            indexes = [
                "CREATE INDEX agent_type IF NOT EXISTS FOR (a:Agent) ON (a.type)",
                "CREATE INDEX task_status IF NOT EXISTS FOR (t:Task) ON (t.status)"
            ]
            
            for index in indexes:
                await self.neo4j.execute(index)
            
            logger.info("Neo4j initialization completed")
            return True
            
        except Exception as e:
            logger.error(f"Neo4j initialization failed: {str(e)}")
            return False

    async def init_redis(self) -> bool:
        """Initialize Redis database"""
        try:
            logger.info("Initializing Redis...")
            
            # Set up Redis streams
            streams = [
                "agent_events",
                "task_events",
                "system_events"
            ]
            
            for stream in streams:
                await self.redis.create_stream(stream)
            
            # Set up Redis pub/sub channels
            channels = [
                "agent_commands",
                "task_updates",
                "system_notifications"
            ]
            
            for channel in channels:
                await self.redis.create_channel(channel)
            
            logger.info("Redis initialization completed")
            return True
            
        except Exception as e:
            logger.error(f"Redis initialization failed: {str(e)}")
            return False

    async def initialize_all(self) -> Dict[str, bool]:
        """Initialize all databases"""
        results = {
            "postgres": await self.init_postgres(),
            "mongodb": await self.init_mongodb(),
            "neo4j": await self.init_neo4j(),
            "redis": await self.init_redis()
        }
        
        success = all(results.values())
        status = "completed successfully" if success else "failed"
        logger.info(f"Database initialization {status}")
        
        if not success:
            failed = [db for db, result in results.items() if not result]
            logger.error(f"Failed to initialize: {', '.join(failed)}")
        
        return results

async def main():
    """Main initialization function"""
    initializer = DatabaseInitializer()
    results = await initializer.initialize_all()
    
    if not all(results.values()):
        raise Exception("Database initialization failed")

if __name__ == "__main__":
    asyncio.run(main())
