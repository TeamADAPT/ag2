"""
Team Coordinator Module for AATS
Handles agent initialization and team coordination based on configuration.
"""

import asyncio
import logging
from typing import Dict, List, Optional, Set, Type
from collections import defaultdict

from ..config.settings.agent_team_config import (
    AGENT_TEAM_CONFIG,
    COMMUNICATION_RULES,
    TEAM_STRUCTURE,
    PERFORMANCE_METRICS,
    HITL_INTEGRATION,
    SYSTEM_BOUNDARIES,
    AgentTier,
    AgentRole,
    CommunicationPattern
)
from ..agents.base_agent import BaseAgent
from ..agents.strategic.project_manager_agent import ProjectManagerAgent
from ..agents.operational.database_controller_agent import DatabaseControllerAgent
from ..agents.tactical.communication_coordinator_agent import CommunicationCoordinatorAgent

class TeamCoordinator:
    """
    Coordinates the initialization and management of the agent team.
    """

    def __init__(self):
        self.logger = logging.getLogger("TeamCoordinator")
        self.agents: Dict[str, BaseAgent] = {}
        self.agent_tiers: Dict[AgentTier, Set[str]] = defaultdict(set)
        self.agent_roles: Dict[AgentRole, Set[str]] = defaultdict(set)
        self.communication_matrix: Dict[str, Set[str]] = defaultdict(set)
        self._initialized = False

    async def initialize_team(self) -> bool:
        """
        Initialize the entire agent team based on configuration.
        
        Returns:
            bool: True if initialization was successful, False otherwise.
        """
        try:
            self.logger.info("Initializing agent team...")

            # Initialize agents by tier
            await self._initialize_strategic_agents()
            await self._initialize_operational_agents()
            await self._initialize_tactical_agents()

            # Setup communication patterns
            self._setup_communication_patterns()

            # Validate team structure
            if not self._validate_team_structure():
                raise ValueError("Team structure validation failed")

            self._initialized = True
            self.logger.info("Agent team initialization complete")
            return True

        except Exception as e:
            self.logger.error(f"Failed to initialize agent team: {str(e)}")
            return False

    async def _initialize_strategic_agents(self) -> None:
        """Initialize strategic tier agents"""
        strategic_agents = {
            name: config for name, config in AGENT_TEAM_CONFIG.items()
            if config.tier == AgentTier.STRATEGIC
        }

        for name, config in strategic_agents.items():
            agent = self._create_agent_instance(name, config)
            if agent:
                self.agents[name] = agent
                self.agent_tiers[AgentTier.STRATEGIC].add(name)
                self.agent_roles[config.role].add(name)

    async def _initialize_operational_agents(self) -> None:
        """Initialize operational tier agents"""
        operational_agents = {
            name: config for name, config in AGENT_TEAM_CONFIG.items()
            if config.tier == AgentTier.OPERATIONAL
        }

        for name, config in operational_agents.items():
            agent = self._create_agent_instance(name, config)
            if agent:
                self.agents[name] = agent
                self.agent_tiers[AgentTier.OPERATIONAL].add(name)
                self.agent_roles[config.role].add(name)

    async def _initialize_tactical_agents(self) -> None:
        """Initialize tactical tier agents"""
        tactical_agents = {
            name: config for name, config in AGENT_TEAM_CONFIG.items()
            if config.tier == AgentTier.TACTICAL
        }

        for name, config in tactical_agents.items():
            agent = self._create_agent_instance(name, config)
            if agent:
                self.agents[name] = agent
                self.agent_tiers[AgentTier.TACTICAL].add(name)
                self.agent_roles[config.role].add(name)

    def _create_agent_instance(self, name: str, config: Dict) -> Optional[BaseAgent]:
        """Create an instance of a specific agent based on configuration"""
        agent_classes = {
            "ProjectManager": ProjectManagerAgent,
            "DatabaseController": DatabaseControllerAgent,
            "CommunicationCoordinator": CommunicationCoordinatorAgent,
            # Add other agent classes as they are implemented
        }

        agent_class = agent_classes.get(name)
        if agent_class:
            try:
                return agent_class()
            except Exception as e:
                self.logger.error(f"Failed to create agent {name}: {str(e)}")
                return None
        else:
            self.logger.warning(f"No implementation found for agent {name}")
            return None

    def _setup_communication_patterns(self) -> None:
        """Setup communication patterns between agents"""
        for name, config in AGENT_TEAM_CONFIG.items():
            if name not in self.agents:
                continue

            # Setup hierarchical communication
            if config.reports_to:
                self.communication_matrix[name].add(config.reports_to)
                self.communication_matrix[config.reports_to].add(name)

            # Setup peer-to-peer communication
            for peer in config.collaborates_with:
                self.communication_matrix[name].add(peer)
                self.communication_matrix[peer].add(name)

            # Setup broadcast capabilities
            if CommunicationPattern.BROADCAST in config.communication_patterns:
                for tier in COMMUNICATION_RULES["allowed_patterns"][config.tier]["can_communicate_with"]:
                    for agent in self.agent_tiers[tier]:
                        self.communication_matrix[name].add(agent)

    def _validate_team_structure(self) -> bool:
        """
        Validate the team structure meets all requirements
        
        Returns:
            bool: True if validation passes, False otherwise
        """
        try:
            # Validate tier distribution
            if not all(self.agent_tiers.values()):
                self.logger.error("Missing agents in one or more tiers")
                return False

            # Validate required roles
            required_roles = {AgentRole.COORDINATOR, AgentRole.EXECUTOR}
            if not all(role in self.agent_roles for role in required_roles):
                self.logger.error("Missing required agent roles")
                return False

            # Validate communication patterns
            if not self._validate_communication_patterns():
                return False

            # Validate hierarchical relationships
            if not self._validate_hierarchy():
                return False

            return True

        except Exception as e:
            self.logger.error(f"Team validation failed: {str(e)}")
            return False

    def _validate_communication_patterns(self) -> bool:
        """Validate communication patterns between agents"""
        for name, config in AGENT_TEAM_CONFIG.items():
            if name not in self.agents:
                continue

            # Validate each agent has at least one communication pattern
            if not config.communication_patterns:
                self.logger.error(f"Agent {name} has no communication patterns")
                return False

            # Validate communication rules compliance
            allowed_patterns = COMMUNICATION_RULES["allowed_patterns"][config.tier]["can_communicate_with"]
            for target in self.communication_matrix[name]:
                target_tier = AGENT_TEAM_CONFIG[target].tier
                if target_tier not in allowed_patterns:
                    self.logger.error(f"Invalid communication pattern: {name} -> {target}")
                    return False

        return True

    def _validate_hierarchy(self) -> bool:
        """Validate hierarchical relationships between agents"""
        for name, config in AGENT_TEAM_CONFIG.items():
            if name not in self.agents:
                continue

            # Validate reporting structure
            if config.reports_to and config.reports_to not in self.agents:
                self.logger.error(f"Agent {name} reports to non-existent agent {config.reports_to}")
                return False

            # Validate supervision structure
            for supervised in config.supervises:
                if supervised not in self.agents:
                    self.logger.error(f"Agent {name} supervises non-existent agent {supervised}")
                    return False

        return True

    async def start_team(self) -> None:
        """Start all agents in the team"""
        if not self._initialized:
            raise RuntimeError("Team must be initialized before starting")

        self.logger.info("Starting agent team...")
        start_tasks = []

        # Start agents in order of tier
        for tier in [AgentTier.STRATEGIC, AgentTier.OPERATIONAL, AgentTier.TACTICAL]:
            for agent_name in self.agent_tiers[tier]:
                agent = self.agents[agent_name]
                start_tasks.append(agent.start())

        await asyncio.gather(*start_tasks)
        self.logger.info("Agent team started successfully")

    async def stop_team(self) -> None:
        """Stop all agents in the team"""
        if not self._initialized:
            return

        self.logger.info("Stopping agent team...")
        stop_tasks = []

        # Stop agents in reverse order of tier
        for tier in [AgentTier.TACTICAL, AgentTier.OPERATIONAL, AgentTier.STRATEGIC]:
            for agent_name in self.agent_tiers[tier]:
                agent = self.agents[agent_name]
                stop_tasks.append(agent.stop())

        await asyncio.gather(*stop_tasks)
        self.logger.info("Agent team stopped successfully")

    async def get_team_status(self) -> Dict:
        """Get status of all agents in the team"""
        status = {
            "total_agents": len(self.agents),
            "active_agents": 0,
            "tiers": {tier.value: [] for tier in AgentTier},
            "roles": {role.value: [] for role in AgentRole}
        }

        for name, agent in self.agents.items():
            agent_status = await agent.health_check()
            config = AGENT_TEAM_CONFIG[name]
            
            if agent_status["status"] == "healthy":
                status["active_agents"] += 1
            
            status["tiers"][config.tier.value].append({
                "name": name,
                "status": agent_status
            })
            
            status["roles"][config.role.value].append({
                "name": name,
                "status": agent_status
            })

        return status
