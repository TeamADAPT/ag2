"""
Database Schema Definitions
This module defines the schemas for all database collections/tables used in the system.
"""

from typing import Dict, Any

# PostgreSQL Schemas
POSTGRES_SCHEMAS = {
    "agents": {
        "id": "SERIAL PRIMARY KEY",
        "name": "VARCHAR(255) NOT NULL",
        "type": "VARCHAR(50) NOT NULL",
        "status": "VARCHAR(50) NOT NULL",
        "capabilities": "JSONB",
        "created_at": "TIMESTAMP DEFAULT CURRENT_TIMESTAMP",
        "updated_at": "TIMESTAMP DEFAULT CURRENT_TIMESTAMP"
    },
    "tasks": {
        "id": "SERIAL PRIMARY KEY",
        "agent_id": "INTEGER REFERENCES agents(id)",
        "type": "VARCHAR(50) NOT NULL",
        "status": "VARCHAR(50) NOT NULL",
        "priority": "INTEGER",
        "data": "JSONB",
        "created_at": "TIMESTAMP DEFAULT CURRENT_TIMESTAMP",
        "updated_at": "TIMESTAMP DEFAULT CURRENT_TIMESTAMP"
    },
    "agent_interactions": {
        "id": "SERIAL PRIMARY KEY",
        "source_agent_id": "INTEGER REFERENCES agents(id)",
        "target_agent_id": "INTEGER REFERENCES agents(id)",
        "interaction_type": "VARCHAR(50) NOT NULL",
        "data": "JSONB",
        "created_at": "TIMESTAMP DEFAULT CURRENT_TIMESTAMP"
    },
    "system_metrics": {
        "id": "SERIAL PRIMARY KEY",
        "metric_type": "VARCHAR(50) NOT NULL",
        "value": "FLOAT NOT NULL",
        "metadata": "JSONB",
        "timestamp": "TIMESTAMP DEFAULT CURRENT_TIMESTAMP"
    }
}

# MongoDB Schemas
MONGODB_SCHEMAS = {
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
    },
    "model_metrics": {
        "validator": {
            "$jsonSchema": {
                "bsonType": "object",
                "required": ["model_id", "metrics", "timestamp"],
                "properties": {
                    "model_id": {"bsonType": "string"},
                    "metrics": {"bsonType": "object"},
                    "timestamp": {"bsonType": "date"}
                }
            }
        }
    }
}

# Neo4j Schemas
NEO4J_SCHEMAS = {
    "Agent": {
        "required": ["id", "name", "type"],
        "unique": ["id"],
        "properties": {
            "id": {"type": "STRING"},
            "name": {"type": "STRING"},
            "type": {"type": "STRING"},
            "status": {"type": "STRING"},
            "capabilities": {"type": "STRING"},  # JSON string
            "created_at": {"type": "DATETIME"},
            "updated_at": {"type": "DATETIME"}
        }
    },
    "Task": {
        "required": ["id", "type", "status"],
        "unique": ["id"],
        "properties": {
            "id": {"type": "STRING"},
            "type": {"type": "STRING"},
            "status": {"type": "STRING"},
            "priority": {"type": "INTEGER"},
            "data": {"type": "STRING"},  # JSON string
            "created_at": {"type": "DATETIME"},
            "updated_at": {"type": "DATETIME"}
        }
    },
    "Interaction": {
        "required": ["id", "type"],
        "unique": ["id"],
        "properties": {
            "id": {"type": "STRING"},
            "type": {"type": "STRING"},
            "data": {"type": "STRING"},  # JSON string
            "created_at": {"type": "DATETIME"}
        }
    }
}

# Redis Schemas (for documentation, Redis is schemaless)
REDIS_SCHEMAS = {
    "agent_cache": {
        "fields": {
            "id": "string",
            "name": "string",
            "type": "string",
            "status": "string",
            "capabilities": "hash",
            "created_at": "string",
            "updated_at": "string"
        },
        "ttl": 3600  # 1 hour
    },
    "task_cache": {
        "fields": {
            "id": "string",
            "agent_id": "string",
            "type": "string",
            "status": "string",
            "priority": "string",
            "data": "hash",
            "created_at": "string",
            "updated_at": "string"
        },
        "ttl": 1800  # 30 minutes
    },
    "interaction_cache": {
        "fields": {
            "id": "string",
            "source_agent_id": "string",
            "target_agent_id": "string",
            "type": "string",
            "data": "hash",
            "created_at": "string"
        },
        "ttl": 900  # 15 minutes
    },
    "metrics_cache": {
        "fields": {
            "id": "string",
            "type": "string",
            "value": "string",
            "metadata": "hash",
            "timestamp": "string"
        },
        "ttl": 300  # 5 minutes
    }
}

# Indexes
INDEXES = {
    "postgres": {
        "agents": [
            ("name", 1),
            ("type", 1),
            ("status", 1)
        ],
        "tasks": [
            ("agent_id", 1),
            ("type", 1),
            ("status", 1),
            ("priority", -1)
        ],
        "agent_interactions": [
            ("source_agent_id", 1),
            ("target_agent_id", 1),
            ("interaction_type", 1)
        ],
        "system_metrics": [
            ("metric_type", 1),
            ("timestamp", -1)
        ]
    },
    "mongodb": {
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
        ],
        "model_metrics": [
            ("model_id", 1),
            ("timestamp", -1)
        ]
    },
    "neo4j": {
        "Agent": [
            "name",
            "type",
            "status"
        ],
        "Task": [
            "type",
            "status",
            "priority"
        ],
        "Interaction": [
            "type"
        ]
    }
}

def get_schema(db_type: str, collection: str) -> Dict[str, Any]:
    """
    Get schema definition for a specific database and collection.
    
    Args:
        db_type: Database type (postgres, mongodb, neo4j, redis)
        collection: Collection/table name
        
    Returns:
        Dict[str, Any]: Schema definition
    """
    schemas = {
        "postgres": POSTGRES_SCHEMAS,
        "mongodb": MONGODB_SCHEMAS,
        "neo4j": NEO4J_SCHEMAS,
        "redis": REDIS_SCHEMAS
    }
    
    return schemas.get(db_type, {}).get(collection, {})

def get_indexes(db_type: str, collection: str) -> list:
    """
    Get index definitions for a specific database and collection.
    
    Args:
        db_type: Database type (postgres, mongodb, neo4j, redis)
        collection: Collection/table name
        
    Returns:
        list: List of index definitions
    """
    return INDEXES.get(db_type, {}).get(collection, [])

def validate_schema(db_type: str, collection: str, data: Dict[str, Any]) -> bool:
    """
    Validate data against schema.
    
    Args:
        db_type: Database type (postgres, mongodb, neo4j, redis)
        collection: Collection/table name
        data: Data to validate
        
    Returns:
        bool: True if valid, False otherwise
    """
    schema = get_schema(db_type, collection)
    
    if not schema:
        return True  # No schema to validate against
    
    if db_type == "mongodb":
        # MongoDB schema validation
        validator = schema.get("validator", {}).get("$jsonSchema", {})
        required = validator.get("required", [])
        properties = validator.get("properties", {})
        
        # Check required fields
        if not all(field in data for field in required):
            return False
        
        # Check property types
        for field, value in data.items():
            if field in properties:
                expected_type = properties[field]["bsonType"]
                if expected_type == "string" and not isinstance(value, str):
                    return False
                elif expected_type == "object" and not isinstance(value, dict):
                    return False
                elif expected_type == "date" and not isinstance(value, (str, datetime)):
                    return False
    
    elif db_type == "neo4j":
        # Neo4j schema validation
        required = schema.get("required", [])
        properties = schema.get("properties", {})
        
        # Check required fields
        if not all(field in data for field in required):
            return False
        
        # Check property types
        for field, value in data.items():
            if field in properties:
                expected_type = properties[field]["type"]
                if expected_type == "STRING" and not isinstance(value, str):
                    return False
                elif expected_type == "INTEGER" and not isinstance(value, int):
                    return False
                elif expected_type == "DATETIME" and not isinstance(value, (str, datetime)):
                    return False
    
    elif db_type == "postgres":
        # PostgreSQL schema validation
        for field, value in data.items():
            if field in schema:
                field_type = schema[field].split()[0]
                if field_type == "VARCHAR" and not isinstance(value, str):
                    return False
                elif field_type == "INTEGER" and not isinstance(value, int):
                    return False
                elif field_type == "FLOAT" and not isinstance(value, (int, float)):
                    return False
                elif field_type == "JSONB" and not isinstance(value, (dict, list)):
                    return False
                elif field_type == "TIMESTAMP" and not isinstance(value, (str, datetime)):
                    return False
    
    return True
