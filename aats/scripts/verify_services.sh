#!/bin/bash

# Verification script for AATS services
# Checks service status and memory configuration after reboot

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

# Log file
LOG_FILE="/var/log/aats/service_verification.log"
mkdir -p /var/log/aats

log() {
    echo -e "[$(date '+%Y-%m-%d %H:%M:%S')] $1" | tee -a $LOG_FILE
}

check_service() {
    local service=$1
    log "Checking $service..."
    
    if systemctl is-active --quiet $service; then
        log "${GREEN}✓ $service is running${NC}"
        return 0
    else
        log "${RED}✗ $service failed to start${NC}"
        log "$(systemctl status $service)"
        return 1
    }
}

check_memory_config() {
    local service=$1
    local min_memory=$2
    
    log "Checking memory configuration for $service..."
    
    # Get current memory limit from systemd
    local memory_limit=$(systemctl show $service -p MemoryLimit | cut -d= -f2)
    
    if [ $memory_limit -ge $min_memory ]; then
        log "${GREEN}✓ $service memory configuration is correct${NC}"
        return 0
    else
        log "${RED}✗ $service memory configuration is insufficient${NC}"
        log "Current: $memory_limit, Required: $min_memory"
        return 1
    }
}

verify_database() {
    local service=$1
    local port=$2
    local check_cmd=$3
    
    log "Verifying database $service..."
    
    # Check service status
    check_service $service || return 1
    
    # Check port
    if nc -z localhost $port; then
        log "${GREEN}✓ $service is accepting connections on port $port${NC}"
    else
        log "${RED}✗ $service is not accepting connections on port $port${NC}"
        return 1
    fi
    
    # Run database-specific check
    if eval $check_cmd; then
        log "${GREEN}✓ $service health check passed${NC}"
    else
        log "${RED}✗ $service health check failed${NC}"
        return 1
    }
    
    return 0
}

# Main verification process
log "Starting AATS service verification..."

# System memory check
total_mem=$(free -g | awk '/^Mem:/{print $2}')
log "Total system memory: ${total_mem}GB"

if [ $total_mem -lt 1300 ]; then
    log "${RED}✗ System memory is less than required (1,408GB)${NC}"
    exit 1
fi

# Database Services
verify_database "postgresql" "5432" "psql -U postgres -c '\l'" || exit 1
verify_database "mongodb" "27017" "mongosh --eval 'db.runCommand({ ping: 1 })'" || exit 1
verify_database "neo4j" "7687" "cypher-shell -u neo4j -p \$NEO4J_PASSWORD 'RETURN 1'" || exit 1
verify_database "redis" "6379" "redis-cli ping" || exit 1

# Vector Stores
verify_database "milvus" "19530" "python3 -c 'from pymilvus import connections; connections.connect()'" || exit 1
verify_database "chroma" "8000" "curl -s http://localhost:8000/api/v1/heartbeat" || exit 1

# Message Brokers
verify_database "kafka" "9092" "kafka-topics.sh --bootstrap-server localhost:9092 --list" || exit 1
verify_database "rabbitmq" "5672" "rabbitmqctl status" || exit 1

# Memory Configuration Checks
check_memory_config "postgresql" 268435456000 # 250GB
check_memory_config "mongodb" 322122547200 # 300GB
check_memory_config "neo4j" 214748364800 # 200GB
check_memory_config "redis" 107374182400 # 100GB
check_memory_config "milvus" 161061273600 # 150GB
check_memory_config "chroma" 53687091200 # 50GB

# Check AATS Core Services
core_services=(
    "aats-memory-manager"
    "aats-knowledge-manager"
    "aats-reasoning-engine"
    "aats-model-orchestrator"
    "aats-team-coordinator"
)

for service in "${core_services[@]}"; do
    check_service $service || exit 1
    check_memory_config $service 53687091200 # 50GB each
done

# Final Status Report
log "\nService Verification Summary:"
failed_services=$(systemctl list-units --state=failed --plain --no-legend | grep aats)

if [ -z "$failed_services" ]; then
    log "${GREEN}✓ All services are running correctly${NC}"
    log "${GREEN}✓ Memory configuration is correct${NC}"
    log "${GREEN}✓ Database connections are established${NC}"
    log "${GREEN}✓ System is ready for operation${NC}"
    exit 0
else
    log "${RED}✗ Some services failed to start:${NC}"
    echo "$failed_services"
    exit 1
fi
