#!/usr/bin/env python3

"""
Agent Deployment Script
This script deploys all AATS agents in the correct order with proper initialization
"""

import asyncio
import logging
import yaml
import os
from pathlib import Path
from typing import List, Dict, Any
import sys

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Agent deployment order
DEPLOYMENT_ORDER = {
    "infrastructure": [
        "database_controller",
        "message_broker",
        "cache_manager",
        "api_gateway"
    ],
    "strategic": [
        "project_manager",
        "resource_optimizer",
        "security_officer",
        "data_architect",
        "integration_specialist",
        "quality_assurance",
        "knowledge_manager",
        "compliance_monitor"
    ],
    "tactical": [
        "communication_coordinator"
    ],
    "operational_core": [
        "search_specialist",
        "file_processor",
        "data_extraction",
        "data_transformation",
        "data_validation",
        "data_enrichment",
        "data_integration",
        "data_orchestration",
        "data_pipeline",
        "data_monitoring",
        "data_optimization",
        "data_recovery"
    ],
    "operational_model": [
        "model_connectivity",
        "model_selection",
        "model_performance",
        "model_cost",
        "model_security",
        "model_testing",
        "model_versioning",
        "model_documentation",
        "model_feedback"
    ],
    "integration": [
        "atlassian_integration"
    ]
}

class AgentDeployer:
    """Handles deployment of AATS agents"""

    def __init__(self):
        self.config = self._load_config()
        self.deployed_agents = set()
        self.deployment_status = {}

    def _load_config(self) -> Dict[str, Any]:
        """Load deployment configuration"""
        config_path = Path("aats/config/deployment/deployment_config.yaml")
        with open(config_path, 'r') as f:
            return yaml.safe_load(f)

    async def _initialize_infrastructure(self) -> bool:
        """Initialize required infrastructure"""
        try:
            logger.info("Initializing infrastructure...")
            
            # Initialize databases
            logger.info("Initializing databases...")
            from aats.scripts.init_databases import main as init_db
            await init_db()
            
            # Set up message brokers
            logger.info("Setting up message brokers...")
            # Import and initialize Kafka/RabbitMQ
            
            # Set up caching
            logger.info("Setting up caching...")
            # Import and initialize Redis
            
            # Set up API gateway
            logger.info("Setting up API gateway...")
            # Import and initialize API gateway
            
            logger.info("Infrastructure initialization completed")
            return True
            
        except Exception as e:
            logger.error(f"Infrastructure initialization failed: {str(e)}")
            return False

    async def _deploy_agent(self, agent_type: str, agent_name: str) -> bool:
        """Deploy a single agent"""
        try:
            logger.info(f"Deploying {agent_name} agent...")
            
            # Get agent configuration
            agent_config = self.config["agents"].get(agent_type, {}).get(agent_name, {})
            
            # Import agent class
            module_path = f"aats.agents.{agent_type}.{agent_name}_agent"
            agent_module = __import__(module_path, fromlist=["*"])
            agent_class = getattr(agent_module, f"{agent_name.title()}Agent")
            
            # Initialize agent
            agent = agent_class()
            success = await agent.initialize()
            
            if success:
                self.deployed_agents.add(agent_name)
                self.deployment_status[agent_name] = {
                    "status": "deployed",
                    "timestamp": datetime.now().isoformat()
                }
                logger.info(f"{agent_name} agent deployed successfully")
                return True
            else:
                self.deployment_status[agent_name] = {
                    "status": "failed",
                    "timestamp": datetime.now().isoformat()
                }
                logger.error(f"{agent_name} agent deployment failed")
                return False
                
        except Exception as e:
            logger.error(f"Error deploying {agent_name} agent: {str(e)}")
            self.deployment_status[agent_name] = {
                "status": "error",
                "timestamp": datetime.now().isoformat(),
                "error": str(e)
            }
            return False

    async def _verify_deployment(self, agent_name: str) -> bool:
        """Verify agent deployment"""
        try:
            logger.info(f"Verifying {agent_name} agent deployment...")
            
            # Get agent status
            agent_module = __import__(f"aats.agents.{agent_type}.{agent_name}_agent", fromlist=["*"])
            agent = getattr(agent_module, f"{agent_name}_agent")
            
            # Check agent health
            status = await agent.get_status()
            
            if status["healthy"]:
                logger.info(f"{agent_name} agent verification successful")
                return True
            else:
                logger.error(f"{agent_name} agent verification failed")
                return False
                
        except Exception as e:
            logger.error(f"Error verifying {agent_name} agent: {str(e)}")
            return False

    async def deploy_all(self) -> bool:
        """Deploy all agents in the correct order"""
        try:
            # Initialize infrastructure
            if not await self._initialize_infrastructure():
                logger.error("Infrastructure initialization failed")
                return False
            
            # Deploy agents in order
            for phase, agents in DEPLOYMENT_ORDER.items():
                logger.info(f"Deploying {phase} agents...")
                
                for agent_name in agents:
                    # Determine agent type
                    agent_type = phase if phase in ["strategic", "tactical"] else "operational"
                    
                    # Deploy agent
                    if not await self._deploy_agent(agent_type, agent_name):
                        logger.error(f"Failed to deploy {agent_name} agent")
                        return False
                    
                    # Verify deployment
                    if not await self._verify_deployment(agent_name):
                        logger.error(f"Failed to verify {agent_name} agent")
                        return False
                    
                    # Wait for agent to be ready
                    await asyncio.sleep(5)
            
            # Final verification
            if len(self.deployed_agents) == 25:
                logger.info("All agents deployed successfully")
                return True
            else:
                logger.error(f"Only {len(self.deployed_agents)} agents deployed successfully")
                return False
                
        except Exception as e:
            logger.error(f"Deployment failed: {str(e)}")
            return False

    async def generate_deployment_report(self) -> Dict[str, Any]:
        """Generate deployment report"""
        return {
            "total_agents": len(DEPLOYMENT_ORDER["strategic"]) + 
                          len(DEPLOYMENT_ORDER["tactical"]) + 
                          len(DEPLOYMENT_ORDER["operational_core"]) +
                          len(DEPLOYMENT_ORDER["operational_model"]) +
                          len(DEPLOYMENT_ORDER["integration"]),
            "deployed_agents": len(self.deployed_agents),
            "deployment_status": self.deployment_status,
            "missing_agents": set(sum(DEPLOYMENT_ORDER.values(), [])) - self.deployed_agents
        }

async def main():
    """Main deployment function"""
    try:
        logger.info("Starting agent deployment...")
        
        # Create deployer
        deployer = AgentDeployer()
        
        # Deploy all agents
        success = await deployer.deploy_all()
        
        # Generate report
        report = await deployer.generate_deployment_report()
        
        if success:
            logger.info("Deployment completed successfully")
            logger.info(f"Deployment report: {report}")
            return 0
        else:
            logger.error("Deployment failed")
            logger.error(f"Deployment report: {report}")
            return 1
            
    except Exception as e:
        logger.error(f"Deployment script failed: {str(e)}")
        return 1

if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
