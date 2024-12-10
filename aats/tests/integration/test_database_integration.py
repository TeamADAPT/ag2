"""
Database Integration Tests
This module contains integration tests for database components.
"""

import pytest
import asyncio
from datetime import datetime
from typing import Dict, Any, List

from ...integration.databases.db_factory import db_factory, DatabaseType
from ...integration.databases.migrations import migration_manager
from ...agents.operational.database_controller_agent import db_controller

# Test data
TEST_AGENT = {
    "name": "TestAgent",
    "type": "test",
    "status": "active",
    "capabilities": {"test": True},
    "created_at": datetime.now(),
    "updated_at": datetime.now()
}

TEST_TASK = {
    "type": "test_task",
    "status": "pending",
    "priority": 1,
    "data": {"test": True},
    "created_at": datetime.now(),
    "updated_at": datetime.now()
}

@pytest.fixture
async def setup_databases():
    """Setup test databases"""
    # Initialize database factory
    for db_type in DatabaseType:
        adapter = await db_factory.get_adapter(db_type)
        assert adapter is not None, f"Failed to initialize {db_type} adapter"
    
    # Initialize and apply migrations
    assert await migration_manager.initialize(), "Failed to initialize migrations"
    assert await migration_manager.apply_migrations(), "Failed to apply migrations"
    
    yield
    
    # Cleanup
    await db_factory.close_all()

@pytest.fixture
async def setup_controller():
    """Setup database controller"""
    assert await db_controller.initialize(), "Failed to initialize database controller"
    yield
    await db_controller.cleanup()

@pytest.mark.asyncio
async def test_database_initialization(setup_databases):
    """Test database initialization"""
    for db_type in DatabaseType:
        adapter = await db_factory.get_adapter(db_type)
        assert adapter is not None
        
        # Check health
        health = await adapter.health_check()
        assert health["status"] == "healthy"

@pytest.mark.asyncio
async def test_schema_creation(setup_databases):
    """Test schema creation"""
    for db_type in DatabaseType:
        adapter = await db_factory.get_adapter(db_type)
        assert adapter is not None
        
        # Verify collections/tables exist
        if db_type == DatabaseType.POSTGRES:
            result = await adapter.execute(
                """
                SELECT table_name 
                FROM information_schema.tables 
                WHERE table_schema = 'public'
                """
            )
            tables = [row["table_name"] for row in result]
            assert "agents" in tables
            assert "tasks" in tables
            
        elif db_type == DatabaseType.MONGODB:
            collections = await adapter.execute("list_collection_names")
            assert "agent_states" in collections
            assert "task_history" in collections
            
        elif db_type == DatabaseType.NEO4J:
            result = await adapter.execute(
                "CALL db.labels() YIELD label"
            )
            labels = [row["label"] for row in result]
            assert "Agent" in labels
            assert "Task" in labels

@pytest.mark.asyncio
async def test_controller_operations(setup_controller):
    """Test database controller operations"""
    # Test insert
    assert await db_controller.insert("agents", TEST_AGENT)
    
    # Test find
    results = await db_controller.find("agents", {"name": "TestAgent"})
    assert len(results) == 1
    assert results[0]["name"] == "TestAgent"
    
    # Test update
    assert await db_controller.update(
        "agents",
        {"name": "TestAgent"},
        {"status": "inactive"}
    )
    
    results = await db_controller.find("agents", {"name": "TestAgent"})
    assert results[0]["status"] == "inactive"
    
    # Test delete
    assert await db_controller.delete("agents", {"name": "TestAgent"})
    results = await db_controller.find("agents", {"name": "TestAgent"})
    assert len(results) == 0

@pytest.mark.asyncio
async def test_data_synchronization(setup_controller):
    """Test data synchronization between databases"""
    # Insert data through controller
    assert await db_controller.insert("agents", TEST_AGENT)
    
    # Verify data in each database
    for db_type in DatabaseType:
        adapter = await db_factory.get_adapter(db_type)
        assert adapter is not None
        
        results = await adapter.find("agents", {"name": "TestAgent"})
        assert len(results) == 1
        assert results[0]["name"] == "TestAgent"
    
    # Cleanup
    await db_controller.delete("agents", {"name": "TestAgent"})

@pytest.mark.asyncio
async def test_complex_queries(setup_controller):
    """Test complex query operations"""
    # Insert test data
    agents = [
        {**TEST_AGENT, "name": f"Agent{i}", "priority": i}
        for i in range(5)
    ]
    assert await db_controller.insert("agents", agents)
    
    # Test aggregation
    pipeline = [
        {"$group": {"_id": None, "avg_priority": {"$avg": "$priority"}}}
    ]
    results = await db_controller.aggregate("agents", pipeline)
    assert len(results) == 1
    assert results[0]["avg_priority"] == 2.0
    
    # Cleanup
    await db_controller.delete("agents", {"name": {"$regex": "^Agent"}})

@pytest.mark.asyncio
async def test_error_handling(setup_controller):
    """Test error handling"""
    # Test invalid schema
    invalid_agent = {
        "name": 123,  # Should be string
        "type": "test"
    }
    assert not await db_controller.insert("agents", invalid_agent)
    
    # Test invalid query
    with pytest.raises(Exception):
        await db_controller.find("invalid_collection", {})
    
    # Test invalid update
    assert not await db_controller.update(
        "agents",
        {"name": "NonexistentAgent"},
        {"invalid_field": "value"}
    )

@pytest.mark.asyncio
async def test_transaction_handling(setup_controller):
    """Test transaction handling"""
    # Insert related data
    assert await db_controller.insert("agents", TEST_AGENT)
    task = {**TEST_TASK, "agent_id": 1}  # Assuming auto-increment ID
    assert await db_controller.insert("tasks", task)
    
    # Verify relationship
    results = await db_controller.find("tasks", {"agent_id": 1})
    assert len(results) == 1
    assert results[0]["type"] == "test_task"
    
    # Cleanup
    await db_controller.delete("tasks", {"agent_id": 1})
    await db_controller.delete("agents", {"name": "TestAgent"})

@pytest.mark.asyncio
async def test_performance(setup_controller):
    """Test performance with bulk operations"""
    # Insert bulk data
    bulk_agents = [
        {**TEST_AGENT, "name": f"BulkAgent{i}"}
        for i in range(100)
    ]
    
    start_time = datetime.now()
    assert await db_controller.insert("agents", bulk_agents)
    end_time = datetime.now()
    
    # Verify insertion time
    insertion_time = (end_time - start_time).total_seconds()
    assert insertion_time < 5.0  # Should complete within 5 seconds
    
    # Verify all data
    results = await db_controller.find(
        "agents",
        {"name": {"$regex": "^BulkAgent"}}
    )
    assert len(results) == 100
    
    # Cleanup
    await db_controller.delete("agents", {"name": {"$regex": "^BulkAgent"}})

@pytest.mark.asyncio
async def test_concurrent_operations(setup_controller):
    """Test concurrent database operations"""
    async def insert_agent(i: int) -> bool:
        return await db_controller.insert(
            "agents",
            {**TEST_AGENT, "name": f"ConcurrentAgent{i}"}
        )
    
    # Run concurrent insertions
    tasks = [
        insert_agent(i)
        for i in range(10)
    ]
    results = await asyncio.gather(*tasks)
    assert all(results)
    
    # Verify all insertions
    agents = await db_controller.find(
        "agents",
        {"name": {"$regex": "^ConcurrentAgent"}}
    )
    assert len(agents) == 10
    
    # Cleanup
    await db_controller.delete(
        "agents",
        {"name": {"$regex": "^ConcurrentAgent"}}
    )

if __name__ == "__main__":
    pytest.main(["-v", __file__])
