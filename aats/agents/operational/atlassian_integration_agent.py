"""
Enhanced Atlassian Integration Agent Implementation
This agent handles integration with Jira and Confluence systems,
with specific support for vision processing documentation
"""

import asyncio
import logging
from typing import Any, Dict, List, Optional, Set, Union, Callable
from datetime import datetime, timedelta
import json
import os
from dataclasses import dataclass
from enum import Enum
from atlassian import Jira, Confluence
import aiohttp
import yaml
import markdown
from pathlib import Path

from ..base_agent import BaseAgent, AgentConfig
from ...config.settings.base_config import config
from ...integration.databases.utils import db_utils

class ContentType(str, Enum):
    """Content type definitions"""
    ISSUE = "issue"
    PAGE = "page"
    COMMENT = "comment"
    ATTACHMENT = "attachment"
    DASHBOARD = "dashboard"

class ContentStatus(str, Enum):
    """Content status definitions"""
    PENDING = "pending"
    MIGRATING = "migrating"
    COMPLETED = "completed"
    FAILED = "failed"
    VERIFIED = "verified"

class SystemType(str, Enum):
    """System type definitions"""
    JIRA = "jira"
    CONFLUENCE = "confluence"

class TeamSpace(str, Enum):
    """Team space definitions"""
    NOVA_VISION = "NOVA-VISION"
    NOVA_ARCHITECTURE = "Nova Architecture"
    VISION_PROCESSING = "Vision Processing"

@dataclass
class ContentItem:
    """Content item definition"""
    id: str
    type: ContentType
    system: SystemType
    title: str
    content: str
    metadata: Dict[str, Any]
    status: ContentStatus
    created_at: datetime
    updated_at: datetime
    team_tag: str
    source_path: Optional[str] = None
    target_id: Optional[str] = None

class AtlassianIntegrationAgent(BaseAgent):
    """
    Enhanced Atlassian Integration Agent responsible for managing
    Jira and Confluence integration with vision processing support.
    """

    def __init__(self):
        super().__init__(AgentConfig(
            name="AtlassianIntegration",
            description="Handles Atlassian system integration with vision processing support",
            capabilities=[
                "content_migration",
                "issue_tracking",
                "documentation_management",
                "workflow_automation",
                "system_monitoring",
                "vision_processing_support"
            ],
            required_tools=[
                "content_migrator",
                "issue_tracker",
                "doc_manager",
                "vision_processor"
            ],
            max_concurrent_tasks=5,
            priority_level=1
        ))
        self.content_items: Dict[str, ContentItem] = {}
        self.migration_status: Dict[str, Dict] = {}
        self.jira_client: Optional[Jira] = None
        self.confluence_client: Optional[Confluence] = None
        self.vision_space_structure = {
            "Vision Processing": {
                "Core Implementation": [],
                "LLM Integration": [],
                "Monitoring": [],
                "Examples": []
            }
        }

    async def initialize(self) -> bool:
        """Initialize the Atlassian Integration Agent"""
        try:
            self.logger.info("Initializing Atlassian Integration Agent...")
            
            # Initialize credentials
            await self._initialize_credentials()
            
            # Initialize clients
            await self._initialize_clients()
            
            # Initialize content tracking
            await self._initialize_content_tracking()
            
            # Initialize vision processing space
            await self._initialize_vision_space()
            
            # Start integration tasks
            self._start_integration_tasks()
            
            self.logger.info("Atlassian Integration Agent initialized successfully")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to initialize Atlassian Integration Agent: {str(e)}")
            return False

    async def _initialize_vision_space(self) -> None:
        """Initialize vision processing space"""
        try:
            # Create vision space if not exists
            space = await self.confluence_client.get_space(TeamSpace.NOVA_VISION)
            if not space:
                await self.confluence_client.create_space(
                    name=TeamSpace.NOVA_VISION,
                    key="VISION",
                    description="Vision Processing Documentation"
                )
            
            # Create space structure
            parent_page = await self._create_or_get_page(
                space=TeamSpace.NOVA_VISION,
                title="Vision Processing",
                parent_title=TeamSpace.NOVA_ARCHITECTURE
            )
            
            for section, subsections in self.vision_space_structure.items():
                section_page = await self._create_or_get_page(
                    space=TeamSpace.NOVA_VISION,
                    title=section,
                    parent_id=parent_page["id"]
                )
                
                for subsection in subsections:
                    await self._create_or_get_page(
                        space=TeamSpace.NOVA_VISION,
                        title=subsection,
                        parent_id=section_page["id"]
                    )
            
        except Exception as e:
            raise Exception(f"Failed to initialize vision space: {str(e)}")

    async def migrate_vision_content(
        self,
        content_path: str,
        content_type: str,
        options: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """
        Migrate vision processing content
        
        Args:
            content_path: Path to content
            content_type: Type of content
            options: Optional migration options
            
        Returns:
            Dictionary containing migration results
        """
        try:
            # Validate content type
            if content_type not in ContentType:
                return {
                    "success": False,
                    "error": f"Invalid content type: {content_type}"
                }
            
            # Read content
            content = await self._read_content(content_path)
            
            # Add vision processing metadata
            metadata = self._extract_metadata(content)
            metadata.update({
                "prefix": "[VISION]",
                "team_tag": "Team: Vision",
                "component": "Vision Processing"
            })
            
            # Create content item
            content_id = f"vision_content_{datetime.now().timestamp()}"
            content_item = ContentItem(
                id=content_id,
                type=content_type,
                system=SystemType.CONFLUENCE,
                title=self._extract_title(content, content_path),
                content=content,
                metadata=metadata,
                status=ContentStatus.PENDING,
                created_at=datetime.now(),
                updated_at=datetime.now(),
                team_tag="[VISION]",
                source_path=content_path
            )
            
            # Store content item
            self.content_items[content_id] = content_item
            
            # Start migration
            migration_result = await self._migrate_vision_content_item(
                content_item,
                options or {}
            )
            
            if migration_result["success"]:
                content_item.status = ContentStatus.COMPLETED
                content_item.target_id = migration_result["target_id"]
            else:
                content_item.status = ContentStatus.FAILED
            
            return migration_result
            
        except Exception as e:
            self.logger.error(f"Vision content migration failed: {str(e)}")
            return {
                "success": False,
                "error": str(e)
            }

    async def create_vision_issue(
        self,
        issue_data: Dict[str, Any],
        options: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """
        Create vision processing issue
        
        Args:
            issue_data: Issue data
            options: Optional issue options
            
        Returns:
            Dictionary containing issue creation results
        """
        try:
            # Add vision processing metadata
            issue_data.update({
                "project": "NOVA-VISION",
                "labels": ["vision-processing"],
                "components": ["Vision Processing"],
                "summary": f"[VISION] {issue_data['summary']}"
            })
            
            # Create issue
            issue = await self.jira_client.create_issue(
                fields=issue_data
            )
            
            # Configure workflow
            if options and options.get("configure_workflow", True):
                await self._configure_vision_workflow(issue.key)
            
            return {
                "success": True,
                "issue_key": issue.key,
                "issue_id": issue.id
            }
            
        except Exception as e:
            self.logger.error(f"Vision issue creation failed: {str(e)}")
            return {
                "success": False,
                "error": str(e)
            }

    async def setup_vision_automation(
        self,
        options: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """
        Setup vision processing automation rules
        
        Args:
            options: Optional automation options
            
        Returns:
            Dictionary containing automation setup results
        """
        try:
            # Define automation rules
            automation_rules = {
                "update_status_on_commit": {
                    "trigger": "git_commit",
                    "conditions": ["contains_vision_tag"],
                    "actions": ["update_issue_status"]
                },
                "notify_on_doc_change": {
                    "trigger": "confluence_update",
                    "conditions": ["vision_space"],
                    "actions": ["notify_team"]
                },
                "track_implementation": {
                    "trigger": "issue_update",
                    "conditions": ["vision_component"],
                    "actions": ["update_dashboard"]
                }
            }
            
            # Create automation rules
            for rule_id, rule in automation_rules.items():
                await self._create_automation_rule(
                    rule_id,
                    rule,
                    options or {}
                )
            
            return {
                "success": True,
                "rules_created": list(automation_rules.keys())
            }
            
        except Exception as e:
            self.logger.error(f"Vision automation setup failed: {str(e)}")
            return {
                "success": False,
                "error": str(e)
            }

    async def verify_vision_migration(
        self,
        content_id: str,
        options: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """
        Verify vision content migration
        
        Args:
            content_id: Content identifier
            options: Optional verification options
            
        Returns:
            Dictionary containing verification results
        """
        try:
            # Get content item
            content_item = self.content_items.get(content_id)
            if not content_item:
                return {
                    "success": False,
                    "error": f"Content not found: {content_id}"
                }
            
            # Verify content
            verification_result = await self._verify_vision_content(
                content_item,
                options or {}
            )
            
            if verification_result["success"]:
                content_item.status = ContentStatus.VERIFIED
            
            return verification_result
            
        except Exception as e:
            self.logger.error(f"Vision content verification failed: {str(e)}")
            return {
                "success": False,
                "error": str(e)
            }

    async def _monitor_vision_migration(self) -> None:
        """Monitor vision content migration"""
        while True:
            try:
                # Check migration status
                vision_content = [
                    content_id
                    for content_id, content in self.content_items.items()
                    if content.team_tag == "[VISION]"
                ]
                
                for content_id in vision_content:
                    content = self.content_items[content_id]
                    
                    if content.status == ContentStatus.COMPLETED:
                        # Verify migration
                        await self.verify_vision_migration(content_id)
                
                # Wait before next check
                await asyncio.sleep(300)  # Check every 5 minutes
                
            except Exception as e:
                self.logger.error(f"Error in vision migration monitoring: {str(e)}")
                await asyncio.sleep(300)

# Global integration agent instance
integration_agent = AtlassianIntegrationAgent()
