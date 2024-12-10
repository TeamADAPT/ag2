#!/bin/bash

# AATS Development Environment Setup Script
# This script sets up the development environment for the AATS project

# Exit on error
set -e

# Print commands before execution
set -x

echo "Starting AATS development environment setup..."

# Create virtual environment if it doesn't exist
if [ ! -d "venv" ]; then
    echo "Creating Python virtual environment..."
    python3 -m venv venv
fi

# Activate virtual environment
source venv/bin/activate

# Upgrade pip
echo "Upgrading pip..."
pip install --upgrade pip

# Install core dependencies
echo "Installing core dependencies..."
pip install -r requirements.txt

# Install development dependencies
echo "Installing development dependencies..."
pip install black isort flake8 mypy pylint pre-commit

# Initialize git if not already initialized
if [ ! -d ".git" ]; then
    echo "Initializing git repository..."
    git init
fi

# Set up pre-commit hooks
echo "Setting up pre-commit hooks..."
pre-commit install

# Create necessary directories if they don't exist
echo "Creating project directories..."
mkdir -p aats/data
mkdir -p aats/logs
mkdir -p aats/config/local
mkdir -p aats/tests/data

# Set up database connections
echo "Setting up database connections..."

# PostgreSQL
if command -v psql &> /dev/null; then
    echo "Setting up PostgreSQL..."
    createdb -U postgres aats_dev || echo "Database might already exist"
    psql -U postgres -d aats_dev -c "CREATE EXTENSION IF NOT EXISTS vector;" || echo "Vector extension might already exist"
fi

# MongoDB
if command -v mongod &> /dev/null; then
    echo "Setting up MongoDB..."
    mongosh --eval "use aats_dev" || echo "MongoDB might not be running"
fi

# Redis
if command -v redis-cli &> /dev/null; then
    echo "Setting up Redis..."
    redis-cli ping || echo "Redis might not be running"
fi

# Neo4j
if command -v neo4j &> /dev/null; then
    echo "Setting up Neo4j..."
    neo4j start || echo "Neo4j might already be running"
fi

# Set up message brokers
echo "Setting up message brokers..."

# Kafka
if command -v kafka-topics.sh &> /dev/null; then
    echo "Setting up Kafka topics..."
    kafka-topics.sh --create --topic agent-events --bootstrap-server localhost:9092 --partitions 3 --replication-factor 1 || echo "Topics might already exist"
fi

# RabbitMQ
if command -v rabbitmqctl &> /dev/null; then
    echo "Setting up RabbitMQ..."
    rabbitmqctl add_vhost aats_dev || echo "VHost might already exist"
    rabbitmqctl set_permissions -p aats_dev guest ".*" ".*" ".*" || echo "Permissions might already be set"
fi

# Set up monitoring
echo "Setting up monitoring..."

# Prometheus
if [ -f "aats/config/monitoring/prometheus.yml" ]; then
    echo "Configuring Prometheus..."
    mkdir -p prometheus/data
    cp aats/config/monitoring/prometheus.yml prometheus/
fi

# Grafana
if [ -f "aats/config/monitoring/grafana-dashboards.json" ]; then
    echo "Configuring Grafana..."
    mkdir -p grafana/dashboards
    cp aats/config/monitoring/grafana-dashboards.json grafana/dashboards/
fi

# Set up logging
echo "Setting up logging..."
mkdir -p logs/app
mkdir -p logs/audit
mkdir -p logs/performance

# Create local configuration
echo "Creating local configuration..."
if [ ! -f "aats/config/local/config.yaml" ]; then
    cp aats/config/settings/base_config.py aats/config/local/config.yaml
fi

# Set up environment variables
echo "Setting up environment variables..."
if [ ! -f ".env" ]; then
    cp .env.example .env
    echo "Please update .env with your configuration"
fi

# Initialize Atlassian integration
echo "Setting up Atlassian integration..."
if [ -f "/data/chase/secrets/atlassian_credentials.md" ]; then
    echo "Configuring Atlassian credentials..."
    mkdir -p aats/config/secrets
    ln -s /data/chase/secrets/atlassian_credentials.md aats/config/secrets/atlassian_credentials.md
fi

# Set up model configurations
echo "Setting up model configurations..."
if [ ! -f "aats/config/settings/agent_model_config.py" ]; then
    cp aats/config/settings/agent_model_config.py.example aats/config/settings/agent_model_config.py
    echo "Please update agent_model_config.py with your model configurations"
fi

# Initialize test environment
echo "Setting up test environment..."
python aats/scripts/setup_test_env.sh

# Run initial tests
echo "Running initial tests..."
pytest aats/tests/

# Set up git hooks
echo "Setting up git hooks..."
cp aats/scripts/pre-commit-license-check.py .git/hooks/
cp aats/scripts/pre-commit-mypy-run.sh .git/hooks/
chmod +x .git/hooks/pre-commit-license-check.py
chmod +x .git/hooks/pre-commit-mypy-run.sh

# Final setup steps
echo "Running final setup steps..."

# Initialize databases
python aats/scripts/init_databases.py

# Build documentation
if command -v sphinx-build &> /dev/null; then
    echo "Building documentation..."
    cd docs && make html && cd ..
fi

echo "Setup complete! Please review any error messages above."
echo "Next steps:"
echo "1. Update .env with your configuration"
echo "2. Update agent_model_config.py with your model configurations"
echo "3. Start the development server with: python aats/main.py"

# Deactivate virtual environment
deactivate

echo "AATS development environment setup completed successfully!"
