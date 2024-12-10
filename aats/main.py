"""
Main entry point for AATS (Autonomous Agent Team System)
Initializes and coordinates the entire system.
"""

import asyncio
import logging
import signal
from typing import Dict, List, Optional
from pathlib import Path
import json

from config.settings.base_config import config
from agents.base_agent import BaseAgent, AgentConfig
from core.team_coordinator import TeamCoordinator
from core.monitoring.system_monitor import SystemMonitor
from hitl.interface.hitl_manager import HITLManager
from integration.databases.db_factory import DatabaseFactory, DatabaseType

class AATSSystem:
    """Main system coordinator for AATS"""
    
    def __init__(self):
        self.logger = self._setup_logging()
        self.team_coordinator = TeamCoordinator()
        self.hitl_manager = HITLManager()
        self.system_monitor = SystemMonitor(self.hitl_manager)
        self._shutdown_event = asyncio.Event()
        
    def _setup_logging(self) -> logging.Logger:
        """Configure system-wide logging"""
        logging.basicConfig(
            level=getattr(logging, config.logging.level),
            format=config.logging.format,
            handlers=[
                logging.StreamHandler() if config.logging.log_to_console else None,
                logging.FileHandler(config.logging.file) if config.logging.file else None
            ]
        )
        return logging.getLogger("AATS")

    async def initialize_system(self) -> None:
        """Initialize all system components"""
        self.logger.info("Initializing AATS system...")
        
        try:
            # Initialize databases
            await self._initialize_databases()
            
            # Initialize core services
            await self._initialize_core_services()
            
            # Initialize agents
            await self._initialize_agents()
            
            # Setup signal handlers
            self._setup_signal_handlers()
            
            self.logger.info("AATS system initialization complete")
            
        except Exception as e:
            self.logger.error(f"Failed to initialize AATS system: {str(e)}")
            raise

    async def _initialize_databases(self) -> None:
        """Initialize database connections"""
        self.logger.info("Initializing database connections...")
        
        try:
            # Initialize each database type
            for db_type in DatabaseType:
                await DatabaseFactory.get_database(db_type)
                self.logger.info(f"Initialized {db_type} connection")
            
            # Verify database health
            health_status = await DatabaseFactory.health_check_all()
            for db_type, status in health_status.items():
                if status["status"] != "healthy":
                    raise Exception(f"Database {db_type} is unhealthy: {status.get('error')}")
            
            self.logger.info("Database initialization complete")
            
        except Exception as e:
            self.logger.error(f"Database initialization failed: {str(e)}")
            raise

    async def _initialize_core_services(self) -> None:
        """Initialize core system services"""
        self.logger.info("Initializing core services...")
        
        # Initialize HITL interface
        await self.hitl_manager.initialize()
        
        # Initialize monitoring system
        await self.system_monitor.start_monitoring()
        
        self.logger.info("Core services initialization complete")

    async def _initialize_agents(self) -> None:
        """Initialize all system agents"""
        self.logger.info("Initializing agents...")
        
        # Initialize team coordinator
        await self.team_coordinator.initialize_team()
        
        self.logger.info(f"Agent initialization complete")

    def _setup_signal_handlers(self) -> None:
        """Setup system signal handlers"""
        for sig in (signal.SIGTERM, signal.SIGINT):
            signal.signal(sig, self._signal_handler)

    def _signal_handler(self, signum: int, frame) -> None:
        """Handle system signals"""
        self.logger.info(f"Received signal {signum}")
        if not self._shutdown_event.is_set():
            self._shutdown_event.set()

    async def start(self) -> None:
        """Start the AATS system"""
        if self._shutdown_event.is_set():
            self.logger.warning("System is already running")
            return

        self.logger.info("Starting AATS system...")

        try:
            # Start team coordinator
            await self.team_coordinator.start_team()
            
            # Wait for shutdown signal
            await self._shutdown_event.wait()
            
            # Graceful shutdown
            await self.shutdown()
            
        except Exception as e:
            self.logger.error(f"Error during system operation: {str(e)}")
            await self.shutdown()

    async def shutdown(self) -> None:
        """Gracefully shutdown the system"""
        if self._shutdown_event.is_set():
            return

        self.logger.info("Initiating system shutdown...")
        self._shutdown_event.set()

        try:
            # Stop monitoring
            await self.system_monitor.stop_monitoring()
            
            # Stop team coordinator
            await self.team_coordinator.stop_team()
            
            # Close database connections
            await DatabaseFactory.close_all()
            
            self.logger.info("System shutdown complete")
            
        except Exception as e:
            self.logger.error(f"Error during shutdown: {str(e)}")

    async def health_check(self) -> Dict:
        """Perform system-wide health check"""
        health_status = {
            "system_status": "healthy" if not self._shutdown_event.is_set() else "stopped",
            "components": {}
        }

        try:
            # Check database health
            health_status["databases"] = await DatabaseFactory.health_check_all()
            
            # Check agent health
            health_status["agents"] = await self.team_coordinator.get_team_status()
            
            # Check monitoring health
            health_status["monitoring"] = await self.system_monitor.health_check()
            
            # Overall status determination
            component_status = [
                status.get("status", "unhealthy") == "healthy"
                for component in health_status.values()
                for status in (component.values() if isinstance(component, dict) else [component])
            ]
            
            health_status["system_status"] = "healthy" if all(component_status) else "degraded"
            
        except Exception as e:
            health_status["system_status"] = "error"
            health_status["error"] = str(e)

        return health_status

def main():
    """Main entry point for the application"""
    # Create and initialize system
    system = AATSSystem()
    
    # Run the system
    try:
        asyncio.run(system.initialize_system())
        asyncio.run(system.start())
    except KeyboardInterrupt:
        asyncio.run(system.shutdown())
    except Exception as e:
        logging.error(f"System error: {str(e)}")
        asyncio.run(system.shutdown())
        raise

if __name__ == "__main__":
    main()
