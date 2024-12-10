#!/bin/bash

# AATS Deployment with Atlassian Integration Script
# This script orchestrates the complete deployment of the AATS system
# with immediate Atlassian integration

# Exit on error
set -e

# Print commands before execution
set -x

echo "Starting AATS deployment with Atlassian integration..."

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

# Setup Atlassian credentials
echo "Setting up Atlassian credentials..."
if [ -f "/data/chase/secrets/atlassian_credentials.md" ]; then
    # Create secrets directory if it doesn't exist
    mkdir -p aats/config/secrets
    
    # Link credentials file
    ln -sf /data/chase/secrets/atlassian_credentials.md aats/config/secrets/atlassian_credentials.md
    
    # Extract and export credentials
    export ATLASSIAN_USERNAME=$(grep ATLASSIAN_USERNAME /data/chase/secrets/atlassian_credentials.md | cut -d: -f2 | tr -d ' ')
    export ATLASSIAN_API_TOKEN=$(grep ATLASSIAN_API_TOKEN /data/chase/secrets/atlassian_credentials.md | cut -d: -f2 | tr -d ' ')
    export ATLASSIAN_URL=$(grep ATLASSIAN_URL /data/chase/secrets/atlassian_credentials.md | cut -d: -f2,3 | tr -d ' ')
    export ATLASSIAN_AUTH=$(grep ATLASSIAN_AUTH /data/chase/secrets/atlassian_credentials.md | cut -d: -f2 | tr -d ' ')
    
    check_status "Atlassian credentials setup"
else
    echo "Error: Atlassian credentials file not found"
    exit 1
fi

# Verify Atlassian API access
echo "Verifying Atlassian API access..."
curl -s -H "Authorization: $ATLASSIAN_AUTH" \
     "${ATLASSIAN_URL}/rest/api/3/myself" > /dev/null
check_status "Atlassian API access verification"

# Run base deployment
echo "Running base deployment..."
./aats/scripts/deploy.sh
check_status "Base deployment"

# Initialize Atlassian integration
echo "Initializing Atlassian integration..."
python - << EOL
import asyncio
from aats.agents.operational.atlassian_integration_agent import integration_agent

async def init_atlassian():
    # Initialize agent
    success = await integration_agent.initialize()
    if not success:
        raise Exception("Failed to initialize Atlassian integration agent")
    
    # Setup vision space
    await integration_agent._initialize_vision_space()
    
    # Setup automation
    await integration_agent.setup_vision_automation()
    
    print("Atlassian integration initialized successfully")

asyncio.run(init_atlassian())
EOL
check_status "Atlassian integration initialization"

# Migrate project documentation
echo "Migrating project documentation..."
python - << EOL
import asyncio
from aats.agents.operational.atlassian_integration_agent import integration_agent

async def migrate_docs():
    # Migrate project documentation
    docs_to_migrate = [
        "project_overview.md",
        "project_detail.md",
        "aats/docs/SYSTEM_DETAILS.md",
        "aats/docs/memos/db_team_memo.md"
    ]
    
    for doc in docs_to_migrate:
        result = await integration_agent.migrate_vision_content(
            doc,
            "page",
            {"prefix": "[AATS]"}
        )
        if not result["success"]:
            raise Exception(f"Failed to migrate {doc}")
    
    print("Documentation migration completed successfully")

asyncio.run(migrate_docs())
EOL
check_status "Project documentation migration"

# Create Jira issues for deployment verification
echo "Creating deployment verification issues..."
python - << EOL
import asyncio
from aats.agents.operational.atlassian_integration_agent import integration_agent

async def create_verification_issues():
    verification_tasks = [
        "Verify Agent Deployment Status",
        "Verify Database Integration",
        "Verify Message Broker Setup",
        "Verify Monitoring Configuration",
        "Verify Documentation Migration"
    ]
    
    for task in verification_tasks:
        result = await integration_agent.create_vision_issue({
            "summary": task,
            "description": f"Verify the successful deployment of {task.lower()}",
            "issuetype": {"name": "Task"},
            "priority": {"name": "High"}
        })
        if not result["success"]:
            raise Exception(f"Failed to create verification issue: {task}")
    
    print("Verification issues created successfully")

asyncio.run(create_verification_issues())
EOL
check_status "Verification issue creation"

# Setup monitoring dashboards
echo "Setting up monitoring dashboards..."
python - << EOL
import asyncio
from aats.agents.operational.atlassian_integration_agent import integration_agent

async def setup_dashboards():
    # Create deployment status dashboard
    await integration_agent.confluence_client.create_page(
        space="AATS",
        title="AATS Deployment Status Dashboard",
        body="""
        <h1>AATS Deployment Status Dashboard</h1>
        <ac:structured-macro ac:name="jira">
            <ac:parameter ac:name="server">System JIRA</ac:parameter>
            <ac:parameter ac:name="jqlQuery">project = AATS AND labels = deployment-verification</ac:parameter>
        </ac:structured-macro>
        """,
        parent_id=None
    )
    
    print("Monitoring dashboards setup completed")

asyncio.run(setup_dashboards())
EOL
check_status "Monitoring dashboard setup"

# Verify complete deployment
echo "Verifying complete deployment..."
python - << EOL
import asyncio
from aats.agents.operational.atlassian_integration_agent import integration_agent

async def verify_deployment():
    # Verify content migration
    for content_id in integration_agent.content_items:
        result = await integration_agent.verify_vision_migration(content_id)
        if not result["success"]:
            raise Exception(f"Content verification failed for {content_id}")
    
    print("Deployment verification completed successfully")

asyncio.run(verify_deployment())
EOL
check_status "Deployment verification"

echo "Deployment with Atlassian integration completed successfully!"
echo "System is ready for immediate use"
echo "
Key Next Steps:
1. Access Confluence at: ${ATLASSIAN_URL}/wiki
2. Access Jira at: ${ATLASSIAN_URL}/jira
3. Review deployment status dashboard
4. Begin using the system for all operations
"

# Final status check
if [ $? -eq 0 ]; then
    echo "✓ AATS deployment with Atlassian integration successful"
    exit 0
else
    echo "✗ AATS deployment with Atlassian integration failed"
    exit 1
fi
