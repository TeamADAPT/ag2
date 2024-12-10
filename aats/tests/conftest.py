"""
PyTest Configuration and Fixtures
This module provides shared test fixtures and configuration.
"""

import os
import asyncio
import logging
from typing import AsyncGenerator, Generator
import pytest
from dotenv import load_dotenv

from ..integration.databases.db_factory import db_factory, DatabaseType
from ..integration.databases.migrations import migration_manager
from ..agents.operational.database_controller_agent import db_controller

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)8s] %(message)s (%(filename)s:%(lineno)s)',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)

# Load test environment variables
load_dotenv(".env.test")

@pytest.fixture(scope="session")
def event_loop() -> Generator[asyncio.AbstractEventLoop, None, None]:
    """Create an event loop for the test session"""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()

@pytest.fixture(scope="session")
async def database_factory() -> AsyncGenerator[None, None]:
    """Initialize database factory for testing"""
    try:
        # Initialize adapters
        for db_type in DatabaseType:
            adapter = await db_factory.get_adapter(db_type)
            assert adapter is not None, f"Failed to initialize {db_type} adapter"
            
            # Verify connection
            health = await adapter.health_check()
            assert health["status"] == "healthy", f"Unhealthy {db_type}: {health}"
        
        yield
        
        # Cleanup
        await db_factory.close_all()
        
    except Exception as e:
        logger.error(f"Database factory fixture failed: {str(e)}")
        raise

@pytest.fixture(scope="session")
async def migration_manager_fixture() -> AsyncGenerator[None, None]:
    """Initialize migration manager for testing"""
    try:
        # Initialize manager
        assert await migration_manager.initialize(), "Failed to initialize migrations"
        
        # Apply migrations
        assert await migration_manager.apply_migrations(), "Failed to apply migrations"
        
        yield
        
        # Rollback migrations
        assert await migration_manager.rollback_migrations(), "Failed to rollback migrations"
        
    except Exception as e:
        logger.error(f"Migration manager fixture failed: {str(e)}")
        raise

@pytest.fixture(scope="session")
async def database_controller() -> AsyncGenerator[None, None]:
    """Initialize database controller for testing"""
    try:
        # Initialize controller
        assert await db_controller.initialize(), "Failed to initialize database controller"
        
        yield
        
        # Cleanup
        await db_controller.cleanup()
        
    except Exception as e:
        logger.error(f"Database controller fixture failed: {str(e)}")
        raise

@pytest.fixture(autouse=True)
async def cleanup_databases() -> AsyncGenerator[None, None]:
    """Clean up test data after each test"""
    yield
    
    try:
        # Clean up each database
        for db_type in DatabaseType:
            adapter = await db_factory.get_adapter(db_type)
            if not adapter:
                continue
            
            if db_type == DatabaseType.POSTGRES:
                # Delete all data from tables
                tables = await adapter.execute(
                    """
                    SELECT table_name 
                    FROM information_schema.tables 
                    WHERE table_schema = 'public'
                    """
                )
                for table in tables:
                    await adapter.execute(f"TRUNCATE TABLE {table['table_name']} CASCADE")
            
            elif db_type == DatabaseType.MONGODB:
                # Drop all collections
                collections = await adapter.execute("list_collection_names")
                for collection in collections:
                    if not collection.startswith("system."):
                        await adapter.execute("drop_collection", {"name": collection})
            
            elif db_type == DatabaseType.NEO4J:
                # Delete all nodes and relationships
                await adapter.execute("MATCH (n) DETACH DELETE n")
            
            elif db_type == DatabaseType.REDIS:
                # Clear all keys
                await adapter.execute("FLUSHDB")
        
    except Exception as e:
        logger.error(f"Database cleanup failed: {str(e)}")
        raise

@pytest.fixture
def test_data() -> dict:
    """Provide test data for database operations"""
    return {
        "agent": {
            "name": "TestAgent",
            "type": "test",
            "status": "active",
            "capabilities": {"test": True}
        },
        "task": {
            "type": "test_task",
            "status": "pending",
            "priority": 1,
            "data": {"test": True}
        },
        "metrics": {
            "type": "test_metric",
            "value": 100.0,
            "metadata": {"test": True}
        }
    }

@pytest.fixture
def mock_env_vars(monkeypatch: pytest.MonkeyPatch) -> None:
    """Set up mock environment variables for testing"""
    env_vars = {
        "ENVIRONMENT": "test",
        "LOG_LEVEL": "DEBUG",
        "POSTGRES_HOST": "localhost",
        "POSTGRES_PORT": "5432",
        "POSTGRES_DB": "aats_test",
        "POSTGRES_USER": "aats_test",
        "POSTGRES_PASSWORD": "aats_test",
        "MONGODB_URI": "mongodb://aats_test:aats_test@localhost:27017/aats_test",
        "NEO4J_URI": "bolt://localhost:7687",
        "NEO4J_USER": "neo4j",
        "NEO4J_PASSWORD": "aats_test",
        "REDIS_HOST": "localhost",
        "REDIS_PORT": "6379"
    }
    
    for key, value in env_vars.items():
        monkeypatch.setenv(key, value)

@pytest.fixture
async def mock_database_error() -> AsyncGenerator[None, None]:
    """Simulate database errors for testing error handling"""
    # Save original execute methods
    original_methods = {}
    for db_type in DatabaseType:
        adapter = await db_factory.get_adapter(db_type)
        if adapter:
            original_methods[db_type] = adapter.execute
    
    # Replace with error-raising method
    async def mock_execute(*args, **kwargs):
        raise Exception("Simulated database error")
    
    for db_type in DatabaseType:
        adapter = await db_factory.get_adapter(db_type)
        if adapter:
            adapter.execute = mock_execute
    
    yield
    
    # Restore original methods
    for db_type in DatabaseType:
        adapter = await db_factory.get_adapter(db_type)
        if adapter:
            adapter.execute = original_methods[db_type]

@pytest.fixture
def performance_threshold() -> dict:
    """Define performance thresholds for testing"""
    return {
        "query_time": 1.0,  # seconds
        "bulk_insert_time": 5.0,  # seconds
        "connection_time": 2.0,  # seconds
        "memory_usage": 100 * 1024 * 1024  # 100MB
    }

@pytest.fixture
def concurrent_operations() -> int:
    """Define number of concurrent operations for testing"""
    return 10

@pytest.fixture(autouse=True)
def mock_time(monkeypatch: pytest.MonkeyPatch) -> None:
    """Mock time-related functions for consistent testing"""
    from time import time
    
    class MockTime:
        def __init__(self):
            self.current_time = time()
        
        def __call__(self):
            return self.current_time
        
        def sleep(self, seconds):
            self.current_time += seconds
    
    mock_time = MockTime()
    monkeypatch.setattr("time.time", mock_time)
    monkeypatch.setattr("time.sleep", mock_time.sleep)
    monkeypatch.setattr("asyncio.sleep", lambda x: x)

def pytest_configure(config):
    """Configure pytest with custom markers"""
    config.addinivalue_line(
        "markers",
        "integration: mark test as integration test"
    )
    config.addinivalue_line(
        "markers",
        "performance: mark test as performance test"
    )
    config.addinivalue_line(
        "markers",
        "concurrent: mark test as concurrency test"
    )

def pytest_collection_modifyitems(items):
    """Modify test items to add markers based on path"""
    for item in items:
        if "integration" in str(item.fspath):
            item.add_marker(pytest.mark.integration)
        if "performance" in str(item.fspath):
            item.add_marker(pytest.mark.performance)
        if "concurrent" in str(item.fspath):
            item.add_marker(pytest.mark.concurrent)
