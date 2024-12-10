#!/bin/bash

# Script to install and enable AATS systemd services
# This script must be run as root

set -e

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo -e "${YELLOW}Installing AATS systemd services...${NC}"

# Create aats user and group if they don't exist
if ! id -u aats >/dev/null 2>&1; then
    useradd -r -s /bin/false aats
fi

# Create necessary directories
mkdir -p /etc/aats
mkdir -p /var/log/aats
chown -R aats:aats /var/log/aats

# Copy service files
cp /data/ax/projects/active/ag2/aats/config/systemd/aats-core.service /etc/systemd/system/

# Set permissions
chmod 644 /etc/systemd/system/aats-core.service

# Make verification script executable
chmod +x /data/ax/projects/active/ag2/aats/scripts/verify_services.sh

# Reload systemd
systemctl daemon-reload

# Enable services
echo -e "${YELLOW}Enabling services...${NC}"
systemctl enable aats-core.service

# Start services
echo -e "${YELLOW}Starting services...${NC}"
systemctl start aats-core.service

# Check status
if systemctl is-active --quiet aats-core.service; then
    echo -e "${GREEN}AATS services installed and running successfully${NC}"
else
    echo -e "${RED}Failed to start AATS services${NC}"
    systemctl status aats-core.service
    exit 1
fi

# Verify memory limits
echo -e "${YELLOW}Verifying memory configuration...${NC}"
if /data/ax/projects/active/ag2/aats/scripts/verify_services.sh; then
    echo -e "${GREEN}Memory configuration verified successfully${NC}"
else
    echo -e "${RED}Memory configuration verification failed${NC}"
    exit 1
fi

echo -e "${GREEN}Installation complete. Services are ready for system upgrade.${NC}"
