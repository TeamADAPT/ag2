#!/bin/bash

# AATS Test Environment Setup Script
# This script sets up the test environment including databases and dependencies

# Exit on error
set -e

# Print commands before execution
set -x

echo "Setting up AATS test environment..."

# Function to check command status
check_status() {
    if [ $? -eq 0 ]; then
        echo "✓ $1 completed successfully"
    else
        echo "✗ $1 failed"
        exit 1
    fi
}

# Function to wait for service
wait_for_service() {
    echo "Waiting for $1 to be ready..."
    timeout=${2:-300}
    elapsed=0
    while ! $3 && [ $elapsed -lt $timeout ]; do
        sleep 5
        elapsed=$((elapsed + 5))
    done
    if [ $elapsed -ge $timeout ]; then
        echo "Timeout waiting for $1"
        exit 1
    fi
    echo "✓ $1 is ready"
}

# Create test directories
echo "Creating test directories..."
mkdir -p test_data/postgres
mkdir -p test_data/mongodb
mkdir -p test_data/neo4j
mkdir -p test_data/redis
check_status "Test directories creation"

# Setup PostgreSQL
echo "Setting up PostgreSQL..."
docker run -d \
    --name aats_test_postgres \
    -e POSTGRES_DB=aats_test \
    -e POSTGRES_USER=aats_test \
    -e POSTGRES_PASSWORD=aats_test \
    -v $(pwd)/test_data/postgres:/var/lib/postgresql/data \
    -p 5432:5432 \
    postgres:latest

wait_for_service "PostgreSQL" 60 "pg_isready -h localhost -p 5432 -U aats_test"
check_status "PostgreSQL setup"

# Setup MongoDB
echo "Setting up MongoDB..."
docker run -d \
    --name aats_test_mongodb \
    -e MONGODB_DATABASE=aats_test \
    -e MONGODB_USERNAME=aats_test \
    -e MONGODB_PASSWORD=aats_test \
    -v $(pwd)/test_data/mongodb:/data/db \
    -p 27017:27017 \
    mongo:latest

wait_for_service "MongoDB" 60 "mongosh --eval 'db.runCommand({ ping: 1 })' localhost:27017/aats_test"
check_status "MongoDB setup"

# Setup Neo4j
echo "Setting up Neo4j..."
docker run -d \
    --name aats_test_neo4j \
    -e NEO4J_AUTH=neo4j/aats_test \
    -v $(pwd)/test_data/neo4j:/data \
    -p 7474:7474 \
    -p 7687:7687 \
    neo4j:latest

wait_for_service "Neo4j" 60 "curl -s http://localhost:7474 > /dev/null"
check_status "Neo4j setup"

# Setup Redis
echo "Setting up Redis..."
docker run -d \
    --name aats_test_redis \
    -v $(pwd)/test_data/redis:/data \
    -p 6379:6379 \
    redis:latest

wait_for_service "Redis" 60 "redis-cli ping"
check_status "Redis setup"

# Create test environment file
echo "Creating test environment file..."
cat > .env.test << EOL
# Test Environment Configuration

# System
ENVIRONMENT=test
LOG_LEVEL=debug
DEBUG=true

# PostgreSQL
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_DB=aats_test
POSTGRES_USER=aats_test
POSTGRES_PASSWORD=aats_test

# MongoDB
MONGODB_URI=mongodb://aats_test:aats_test@localhost:27017/aats_test
MONGODB_USER=aats_test
MONGODB_PASSWORD=aats_test

# Neo4j
NEO4J_URI=bolt://localhost:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=aats_test

# Redis
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_PASSWORD=

# Test Settings
TEST_TIMEOUT=30
TEST_PARALLEL=true
TEST_COVERAGE=true
EOL
check_status "Test environment file creation"

# Install test dependencies
echo "Installing test dependencies..."
pip install -r requirements.txt
pip install pytest pytest-asyncio pytest-cov pytest-xdist pytest-timeout
check_status "Test dependencies installation"

# Initialize test databases
echo "Initializing test databases..."
python aats/scripts/init_databases.py --env test
check_status "Test database initialization"

# Run database health checks
echo "Running database health checks..."
python - << EOL
import asyncio
from aats.integration.databases.db_factory import db_factory, DatabaseType

async def check_health():
    for db_type in DatabaseType:
        adapter = await db_factory.get_adapter(db_type)
        if not adapter:
            raise Exception(f"Failed to get adapter for {db_type}")
        
        health = await adapter.health_check()
        if health["status"] != "healthy":
            raise Exception(f"Unhealthy database {db_type}: {health}")
    
    print("All database health checks passed")

asyncio.run(check_health())
EOL
check_status "Database health checks"

echo "Test environment setup completed successfully!"
echo "
Next Steps:
1. Run tests: pytest -v aats/tests/
2. Run with coverage: pytest --cov=aats aats/tests/
3. Run parallel tests: pytest -n auto aats/tests/
"

# Final status check
if [ $? -eq 0 ]; then
    echo "✓ Test environment setup successful"
    exit 0
else
    echo "✗ Test environment setup failed"
    exit 1
fi
