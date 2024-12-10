#!/bin/bash

# AATS Base Deployment Script
# This script handles the core deployment of the AATS system

# Exit on error
set -e

# Print commands before execution
set -x

echo "Starting AATS deployment..."

# Check if environment is specified
if [ -z "$ENVIRONMENT" ]; then
    export ENVIRONMENT=development
fi

echo "Deploying in $ENVIRONMENT environment..."

# Create required directories
mkdir -p logs/deployment
mkdir -p data/temp

# Load environment variables
if [ -f .env.$ENVIRONMENT ]; then
    source .env.$ENVIRONMENT
else
    echo "Environment file .env.$ENVIRONMENT not found"
    exit 1
fi

# Function to check command status
check_status() {
    if [ $? -eq 0 ]; then
        echo "✓ $1 completed successfully"
    else
        echo "✗ $1 failed"
        exit 1
    fi
}

# Install dependencies
echo "Installing dependencies..."
pip install -r aats/requirements.txt
check_status "Dependencies installation"

# Initialize databases
echo "Initializing databases..."
python aats/scripts/init_databases.py
check_status "Database initialization"

# Deploy core components
echo "Deploying core components..."

# Deploy model manager
echo "Deploying model manager..."
python - << EOL
from aats.core.model_manager import ModelManager
manager = ModelManager()
manager.initialize()
print("Model manager initialized successfully")
EOL
check_status "Model manager deployment"

# Deploy team coordinator
echo "Deploying team coordinator..."
python - << EOL
from aats.core.team_coordinator import TeamCoordinator
coordinator = TeamCoordinator()
coordinator.initialize()
print("Team coordinator initialized successfully")
EOL
check_status "Team coordinator deployment"

# Deploy monitoring system
echo "Deploying monitoring system..."
python - << EOL
from aats.core.monitoring.system_monitor import SystemMonitor
monitor = SystemMonitor()
monitor.initialize()
print("System monitor initialized successfully")
EOL
check_status "Monitoring system deployment"

# Deploy HITL interface
echo "Deploying HITL interface..."
python - << EOL
from aats.hitl.interface.hitl_manager import HITLManager
hitl = HITLManager()
hitl.initialize()
print("HITL interface initialized successfully")
EOL
check_status "HITL interface deployment"

# Deploy strategic agents
echo "Deploying strategic agents..."
for agent in project_manager resource_optimizer security_officer data_architect integration_specialist quality_assurance knowledge_manager compliance_monitor; do
    python - << EOL
from aats.agents.strategic.${agent}_agent import $(echo ${agent} | sed -r 's/(^|_)([a-z])/\U\2/g')Agent
agent = $(echo ${agent} | sed -r 's/(^|_)([a-z])/\U\2/g')Agent()
agent.initialize()
print("${agent} agent initialized successfully")
EOL
    check_status "${agent} agent deployment"
done

# Deploy tactical agents
echo "Deploying tactical agents..."
for agent in communication_coordinator; do
    python - << EOL
from aats.agents.tactical.${agent}_agent import $(echo ${agent} | sed -r 's/(^|_)([a-z])/\U\2/g')Agent
agent = $(echo ${agent} | sed -r 's/(^|_)([a-z])/\U\2/g')Agent()
agent.initialize()
print("${agent} agent initialized successfully")
EOL
    check_status "${agent} agent deployment"
done

# Deploy operational agents
echo "Deploying operational agents..."
for agent in database_controller message_broker search_specialist api_gateway cache_manager file_processor data_extraction data_transformation data_validation data_enrichment data_integration data_orchestration data_pipeline data_monitoring data_optimization data_recovery data_archival data_compliance model_connectivity model_selection model_performance model_cost model_security model_testing model_versioning model_documentation model_feedback; do
    python - << EOL
from aats.agents.operational.${agent}_agent import $(echo ${agent} | sed -r 's/(^|_)([a-z])/\U\2/g')Agent
agent = $(echo ${agent} | sed -r 's/(^|_)([a-z])/\U\2/g')Agent()
agent.initialize()
print("${agent} agent initialized successfully")
EOL
    check_status "${agent} agent deployment"
done

# Setup monitoring
echo "Setting up monitoring..."
if [ "$ENABLE_MONITORING" = true ]; then
    # Configure Prometheus
    cp aats/config/monitoring/prometheus.yml /etc/prometheus/prometheus.yml
    
    # Configure Grafana
    cp aats/config/monitoring/grafana-dashboards.json /etc/grafana/provisioning/dashboards/
    cp aats/config/monitoring/alertmanager.yml /etc/alertmanager/alertmanager.yml
    
    # Configure alert templates
    cp aats/config/monitoring/templates/custom.tmpl /etc/alertmanager/templates/
    
    check_status "Monitoring setup"
fi

# Verify deployment
echo "Verifying deployment..."
python - << EOL
import sys
from aats.core.team_coordinator import TeamCoordinator

def verify_deployment():
    coordinator = TeamCoordinator()
    status = coordinator.verify_deployment()
    if not status["success"]:
        print("Deployment verification failed:", status["error"])
        sys.exit(1)
    print("Deployment verification successful")

verify_deployment()
EOL
check_status "Deployment verification"

echo "AATS deployment completed successfully!"

# Final status check
if [ $? -eq 0 ]; then
    echo "✓ AATS deployment successful"
    exit 0
else
    echo "✗ AATS deployment failed"
    exit 1
fi
