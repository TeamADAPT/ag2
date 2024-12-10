"""
Model Versioning Manager for AATS
Handles model version control, compatibility checks, and migration strategies
"""

import asyncio
import logging
from typing import Any, Dict, List, Optional, Set, Union, Tuple
from datetime import datetime, timedelta
import json
import semver
from dataclasses import dataclass

from .model_manager import ModelType
from ..config.settings.agent_model_config import MODEL_CAPABILITIES
from ..integration.databases.utils import db_utils

@dataclass
class VersionInfo:
    """Version information"""
    version: str
    release_date: str
    changes: List[str]
    breaking_changes: List[str]
    compatibility: Dict[str, List[str]]
    requirements: Dict[str, Any]

class MigrationStrategy(str):
    """Migration strategy types"""
    DIRECT = "direct"
    GRADUAL = "gradual"
    PARALLEL = "parallel"
    ROLLBACK = "rollback"

class ModelVersionManager:
    """
    Model Version Manager responsible for handling version control,
    compatibility checks, and migration strategies.
    """

    def __init__(self):
        self.logger = logging.getLogger("ModelVersionManager")
        self.version_registry: Dict[str, Dict[str, VersionInfo]] = {}
        self.active_versions: Dict[str, str] = {}
        self.migration_history: List[Dict] = []
        self.compatibility_matrix: Dict[str, Dict[str, bool]] = {}

    async def initialize(self) -> bool:
        """Initialize the Model Version Manager"""
        try:
            self.logger.info("Initializing Model Version Manager...")
            
            # Initialize version registry
            await self._initialize_version_registry()
            
            # Initialize compatibility matrix
            await self._initialize_compatibility_matrix()
            
            # Initialize migration tracking
            await self._initialize_migration_tracking()
            
            # Start version monitoring
            self._start_version_monitoring()
            
            self.logger.info("Model Version Manager initialized successfully")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to initialize Model Version Manager: {str(e)}")
            return False

    async def _initialize_version_registry(self) -> None:
        """Initialize version registry"""
        try:
            # Initialize registry for each model type
            for model_type in ModelType:
                self.version_registry[model_type] = {}
                
                # Add base version info
                base_version = VersionInfo(
                    version="1.0.0",
                    release_date=datetime.now().isoformat(),
                    changes=["Initial version"],
                    breaking_changes=[],
                    compatibility={
                        "min_python": "3.8.0",
                        "supported_platforms": ["linux", "darwin", "win32"]
                    },
                    requirements={
                        "memory": "8GB",
                        "disk_space": "10GB",
                        "cpu_cores": 4
                    }
                )
                
                self.version_registry[model_type]["1.0.0"] = base_version
                self.active_versions[model_type] = "1.0.0"
            
            # Load stored versions
            stored_versions = await db_utils.get_agent_state(
                "version_manager",
                "version_registry"
            )
            
            if stored_versions:
                self._merge_versions(stored_versions)
                
        except Exception as e:
            raise Exception(f"Failed to initialize version registry: {str(e)}")

    async def _initialize_compatibility_matrix(self) -> None:
        """Initialize compatibility matrix"""
        try:
            # Initialize matrix for each model type
            for model_type in ModelType:
                self.compatibility_matrix[model_type] = {}
                versions = self.version_registry[model_type].keys()
                
                for version in versions:
                    self.compatibility_matrix[model_type][version] = {
                        other_version: self._check_version_compatibility(
                            version,
                            other_version
                        )
                        for other_version in versions
                    }
            
            # Load stored compatibility data
            stored_matrix = await db_utils.get_agent_state(
                "version_manager",
                "compatibility_matrix"
            )
            
            if stored_matrix:
                self._merge_compatibility(stored_matrix)
                
        except Exception as e:
            raise Exception(f"Failed to initialize compatibility matrix: {str(e)}")

    async def _initialize_migration_tracking(self) -> None:
        """Initialize migration tracking"""
        try:
            # Set up migration tracking parameters
            self.migration_config = {
                "max_parallel_migrations": 3,
                "timeout_minutes": 60,
                "retry_attempts": 3,
                "backup_required": True,
                "validation_required": True
            }
            
            # Load migration history
            stored_history = await db_utils.get_agent_state(
                "version_manager",
                "migration_history"
            )
            
            if stored_history:
                self.migration_history = stored_history
                
        except Exception as e:
            raise Exception(f"Failed to initialize migration tracking: {str(e)}")

    def _start_version_monitoring(self) -> None:
        """Start version monitoring tasks"""
        asyncio.create_task(self._monitor_versions())
        asyncio.create_task(self._check_compatibility())
        asyncio.create_task(self._cleanup_migrations())

    async def register_version(
        self,
        model_type: ModelType,
        version_info: VersionInfo
    ) -> Dict[str, Any]:
        """
        Register new model version
        
        Args:
            model_type: Type of the model
            version_info: Version information
            
        Returns:
            Dictionary containing registration result
        """
        try:
            # Validate version format
            if not self._validate_version_format(version_info.version):
                return {
                    "registered": False,
                    "error": "Invalid version format"
                }
            
            # Check if version already exists
            if version_info.version in self.version_registry[model_type]:
                return {
                    "registered": False,
                    "error": "Version already exists"
                }
            
            # Add to registry
            self.version_registry[model_type][version_info.version] = version_info
            
            # Update compatibility matrix
            await self._update_compatibility_matrix(
                model_type,
                version_info.version
            )
            
            # Store version info
            await self._store_version_info(
                model_type,
                version_info
            )
            
            return {
                "registered": True,
                "version": version_info.version
            }
            
        except Exception as e:
            self.logger.error(f"Version registration failed: {str(e)}")
            return {
                "registered": False,
                "error": str(e)
            }

    async def check_compatibility(
        self,
        model_type: ModelType,
        source_version: str,
        target_version: str
    ) -> Dict[str, Any]:
        """
        Check compatibility between versions
        
        Args:
            model_type: Type of the model
            source_version: Source version
            target_version: Target version
            
        Returns:
            Dictionary containing compatibility check results
        """
        try:
            # Validate versions
            if not all(self._validate_version_format(v) 
                      for v in [source_version, target_version]):
                return {
                    "compatible": False,
                    "error": "Invalid version format"
                }
            
            # Check compatibility matrix
            matrix = self.compatibility_matrix[model_type]
            if source_version not in matrix or target_version not in matrix:
                return {
                    "compatible": False,
                    "error": "Version not found"
                }
            
            compatible = matrix[source_version][target_version]
            
            if not compatible:
                # Get breaking changes
                breaking_changes = self._get_breaking_changes(
                    model_type,
                    source_version,
                    target_version
                )
                
                return {
                    "compatible": False,
                    "breaking_changes": breaking_changes
                }
            
            return {
                "compatible": True
            }
            
        except Exception as e:
            self.logger.error(f"Compatibility check failed: {str(e)}")
            return {
                "compatible": False,
                "error": str(e)
            }

    async def plan_migration(
        self,
        model_type: ModelType,
        source_version: str,
        target_version: str,
        strategy: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Plan version migration
        
        Args:
            model_type: Type of the model
            source_version: Source version
            target_version: Target version
            strategy: Optional migration strategy
            
        Returns:
            Dictionary containing migration plan
        """
        try:
            # Check compatibility
            compatibility = await self.check_compatibility(
                model_type,
                source_version,
                target_version
            )
            
            if not compatibility["compatible"]:
                return {
                    "planned": False,
                    "error": "Incompatible versions",
                    "details": compatibility
                }
            
            # Determine migration strategy
            if not strategy:
                strategy = self._determine_migration_strategy(
                    model_type,
                    source_version,
                    target_version
                )
            
            # Generate migration steps
            steps = await self._generate_migration_steps(
                model_type,
                source_version,
                target_version,
                strategy
            )
            
            # Estimate migration impact
            impact = await self._estimate_migration_impact(
                model_type,
                steps
            )
            
            return {
                "planned": True,
                "strategy": strategy,
                "steps": steps,
                "impact": impact,
                "estimated_duration": self._estimate_duration(steps)
            }
            
        except Exception as e:
            self.logger.error(f"Migration planning failed: {str(e)}")
            return {
                "planned": False,
                "error": str(e)
            }

    async def execute_migration(
        self,
        model_type: ModelType,
        migration_plan: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Execute version migration
        
        Args:
            model_type: Type of the model
            migration_plan: Migration plan to execute
            
        Returns:
            Dictionary containing migration results
        """
        try:
            # Validate plan
            if not self._validate_migration_plan(migration_plan):
                return {
                    "success": False,
                    "error": "Invalid migration plan"
                }
            
            # Create backup if required
            if self.migration_config["backup_required"]:
                backup = await self._create_backup(model_type)
                if not backup["success"]:
                    return {
                        "success": False,
                        "error": "Backup failed",
                        "details": backup
                    }
            
            # Execute migration steps
            results = []
            for step in migration_plan["steps"]:
                step_result = await self._execute_migration_step(
                    model_type,
                    step
                )
                results.append(step_result)
                
                if not step_result["success"]:
                    # Rollback if any step fails
                    await self._rollback_migration(
                        model_type,
                        results
                    )
                    return {
                        "success": False,
                        "error": "Migration step failed",
                        "failed_step": step,
                        "results": results
                    }
            
            # Validate migration if required
            if self.migration_config["validation_required"]:
                validation = await self._validate_migration(
                    model_type,
                    migration_plan,
                    results
                )
                if not validation["valid"]:
                    await self._rollback_migration(
                        model_type,
                        results
                    )
                    return {
                        "success": False,
                        "error": "Migration validation failed",
                        "details": validation
                    }
            
            # Update active version
            self.active_versions[model_type] = migration_plan["steps"][-1]["target_version"]
            
            # Record migration
            await self._record_migration(
                model_type,
                migration_plan,
                results
            )
            
            return {
                "success": True,
                "results": results
            }
            
        except Exception as e:
            self.logger.error(f"Migration execution failed: {str(e)}")
            return {
                "success": False,
                "error": str(e)
            }

    async def _monitor_versions(self) -> None:
        """Monitor versions continuously"""
        while True:
            try:
                for model_type in ModelType:
                    # Check for new versions
                    new_versions = await self._check_new_versions(model_type)
                    
                    if new_versions:
                        # Notify about new versions
                        await self._notify_new_versions(
                            model_type,
                            new_versions
                        )
                
                # Wait before next check
                await asyncio.sleep(3600)  # Check every hour
                
            except Exception as e:
                self.logger.error(f"Error in version monitoring: {str(e)}")
                await asyncio.sleep(3600)

    async def _check_compatibility(self) -> None:
        """Check version compatibility continuously"""
        while True:
            try:
                for model_type in ModelType:
                    # Update compatibility matrix
                    matrix_updates = await self._update_compatibility_matrix(
                        model_type,
                        None
                    )
                    
                    if matrix_updates:
                        # Store updated matrix
                        await self._store_compatibility_matrix(
                            model_type,
                            matrix_updates
                        )
                
                # Wait before next check
                await asyncio.sleep(86400)  # Check daily
                
            except Exception as e:
                self.logger.error(f"Error in compatibility check: {str(e)}")
                await asyncio.sleep(86400)

    async def _cleanup_migrations(self) -> None:
        """Clean up old migration records"""
        while True:
            try:
                current_time = datetime.now()
                retention_limit = current_time - timedelta(days=90)
                
                # Remove old migration records
                self.migration_history = [
                    record for record in self.migration_history
                    if datetime.fromisoformat(record["timestamp"]) > retention_limit
                ]
                
                # Store updated history
                await db_utils.record_state(
                    agent_id="version_manager",
                    state_type="migration_history",
                    state=self.migration_history
                )
                
                # Wait before next cleanup
                await asyncio.sleep(86400)  # Clean up daily
                
            except Exception as e:
                self.logger.error(f"Error in migration cleanup: {str(e)}")
                await asyncio.sleep(86400)

    def _validate_version_format(self, version: str) -> bool:
        """Validate semantic version format"""
        try:
            semver.VersionInfo.parse(version)
            return True
        except ValueError:
            return False

# Global version manager instance
version_manager = ModelVersionManager()
