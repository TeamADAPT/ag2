# Database Integration Components

## Overview

The database integration components provide a unified interface for interacting with multiple database systems in the AATS (Autonomous Agent Team System). The system supports PostgreSQL, MongoDB, Neo4j, and Redis databases, each serving specific purposes in the overall architecture.

## Architecture

### Component Structure

```
databases/
├── base_adapter.py      # Abstract base class for database adapters
├── postgres_adapter.py  # PostgreSQL implementation
├── mongodb_adapter.py   # MongoDB implementation
├── neo4j_adapter.py     # Neo4j implementation
├── redis_adapter.py     # Redis implementation
├── db_factory.py        # Factory for creating database instances
├── schema.py           # Database schema definitions
├── migrations.py       # Database migration management
└── utils.py           # Shared utility functions
```

### Database Roles

1. **PostgreSQL**
   - Primary relational database
   - Stores structured data with strict schemas
   - Handles complex transactions and relationships
   - Used for: Agent states, tasks, system metrics

2. **MongoDB**
   - Document store for flexible data
   - Handles semi-structured and unstructured data
   - Efficient for large-scale data storage and retrieval
   - Used for: Agent logs, task history, system events

3. **Neo4j**
   - Graph database for relationship-heavy data
   - Manages complex agent interactions and relationships
   - Efficient for path finding and network analysis
   - Used for: Agent relationships, interaction patterns, knowledge graphs

4. **Redis**
   - In-memory cache and message broker
   - Handles real-time data and pub/sub messaging
   - Provides fast access to frequently used data
   - Used for: Caching, real-time events, session data

## Usage

### Basic Usage

```python
from aats.integration.databases.db_factory import db_factory, DatabaseType
from aats.agents.operational.database_controller_agent import db_controller

# Using the database controller (recommended)
async def store_agent_data(agent_data):
    return await db_controller.insert("agents", agent_data)

# Using specific database adapter
async def get_postgres_data():
    adapter = await db_factory.get_adapter(DatabaseType.POSTGRES)
    return await adapter.find("agents", {"status": "active"})
```

### Database Operations

1. **Insert Data**
```python
# Single insert
await db_controller.insert("agents", {
    "name": "Agent1",
    "type": "worker",
    "status": "active"
})

# Bulk insert
await db_controller.insert("agents", [
    {"name": "Agent1", "type": "worker"},
    {"name": "Agent2", "type": "manager"}
])
```

2. **Query Data**
```python
# Simple query
results = await db_controller.find("agents", {"type": "worker"})

# Query with projection
results = await db_controller.find(
    "agents",
    {"status": "active"},
    {"name": 1, "type": 1}
)
```

3. **Update Data**
```python
await db_controller.update(
    "agents",
    {"name": "Agent1"},
    {"status": "inactive"}
)
```

4. **Delete Data**
```python
await db_controller.delete("agents", {"status": "inactive"})
```

5. **Aggregation**
```python
results = await db_controller.aggregate("agents", [
    {"$group": {"_id": "$type", "count": {"$sum": 1}}}
])
```

### Schema Management

```python
from aats.integration.databases.schema import get_schema, validate_schema

# Get schema for a collection
schema = get_schema("postgres", "agents")

# Validate data against schema
is_valid = validate_schema("postgres", "agents", data)
```

### Migrations

```python
from aats.integration.databases.migrations import migration_manager

# Apply pending migrations
await migration_manager.apply_migrations()

# Rollback migrations
await migration_manager.rollback_migrations(target_version="0001")
```

## Testing

### Running Tests

```bash
# Setup test environment
./aats/scripts/setup_test_env.sh

# Run all tests
pytest aats/tests/

# Run specific test category
pytest aats/tests/integration/test_database_integration.py

# Run with coverage
pytest --cov=aats aats/tests/
```

### Test Environment

The test environment uses Docker containers for each database:
- PostgreSQL: localhost:5432
- MongoDB: localhost:27017
- Neo4j: localhost:7687
- Redis: localhost:6379

## Error Handling

The system provides comprehensive error handling:

```python
try:
    await db_controller.insert("agents", data)
except Exception as e:
    logger.error(f"Database operation failed: {str(e)}")
    # Handle error appropriately
```

## Monitoring

Database health and performance monitoring:

```python
# Check database health
health_status = await db_factory.health_check()

# Monitor specific metrics
metrics = await db_controller.get_metrics()
```

## Best Practices

1. **Use the Database Controller**
   - Always use `db_controller` instead of direct adapter access
   - Ensures consistent data synchronization across databases
   - Provides unified error handling and monitoring

2. **Schema Validation**
   - Always validate data against schemas before insertion
   - Use appropriate data types for each field
   - Keep schemas up to date with migrations

3. **Error Handling**
   - Implement proper error handling for all database operations
   - Log errors with appropriate context
   - Use retries with backoff for transient failures

4. **Performance**
   - Use bulk operations for multiple items
   - Implement appropriate indexes
   - Monitor query performance
   - Use caching when appropriate

5. **Security**
   - Never store credentials in code
   - Use environment variables for configuration
   - Implement proper access controls
   - Regularly rotate credentials

## Contributing

1. Follow the established code structure
2. Add tests for new functionality
3. Update documentation
4. Run tests before submitting changes
5. Follow coding standards and best practices

## Dependencies

- PostgreSQL: asyncpg
- MongoDB: motor
- Neo4j: neo4j-driver
- Redis: aioredis
- Shared: pytest, pytest-asyncio, pytest-cov

## License

See the LICENSE file in the root directory.
