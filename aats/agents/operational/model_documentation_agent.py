"""
Model Documentation Agent Implementation
This agent handles documentation generation and maintenance
"""

import asyncio
import logging
from typing import Any, Dict, List, Optional, Set, Union, Callable
from datetime import datetime, timedelta
import json
import yaml
from dataclasses import dataclass
from enum import Enum
import markdown
import mdx_math
import docutils
from docutils.core import publish_parts
import jinja2
import graphviz

from ..base_agent import BaseAgent, AgentConfig
from ...config.settings.base_config import config
from ...integration.databases.utils import db_utils
from .model_connectivity_agent import ModelType, ModelProvider

class DocumentType(str, Enum):
    """Document type definitions"""
    API = "api"
    USAGE = "usage"
    TECHNICAL = "technical"
    INTEGRATION = "integration"
    REFERENCE = "reference"
    TUTORIAL = "tutorial"

class DocumentFormat(str, Enum):
    """Document format definitions"""
    MARKDOWN = "markdown"
    HTML = "html"
    PDF = "pdf"
    RST = "rst"
    DOCX = "docx"

class DocumentStatus(str, Enum):
    """Document status definitions"""
    DRAFT = "draft"
    REVIEW = "review"
    PUBLISHED = "published"
    ARCHIVED = "archived"
    DEPRECATED = "deprecated"

@dataclass
class Document:
    """Document definition"""
    id: str
    type: DocumentType
    format: DocumentFormat
    title: str
    content: str
    metadata: Dict[str, Any]
    version: str
    status: DocumentStatus
    created_at: datetime
    updated_at: datetime
    author: str
    reviewers: List[str]
    tags: List[str]

class ModelDocumentationAgent(BaseAgent):
    """
    Model Documentation Agent responsible for managing
    model documentation.
    """

    def __init__(self):
        super().__init__(AgentConfig(
            name="ModelDocumentation",
            description="Handles model documentation management",
            capabilities=[
                "documentation_generation",
                "documentation_maintenance",
                "version_tracking",
                "format_conversion",
                "search_indexing"
            ],
            required_tools=[
                "doc_generator",
                "doc_maintainer",
                "doc_indexer"
            ],
            max_concurrent_tasks=5,
            priority_level=2
        ))
        self.documents: Dict[str, Document] = {}
        self.templates: Dict[str, str] = {}
        self.search_index: Dict[str, List[str]] = {}
        self.doc_history: Dict[str, List] = {}

    async def initialize(self) -> bool:
        """Initialize the Model Documentation Agent"""
        try:
            self.logger.info("Initializing Model Documentation Agent...")
            
            # Initialize document templates
            await self._initialize_templates()
            
            # Initialize search indexing
            await self._initialize_search_index()
            
            # Initialize document tracking
            await self._initialize_document_tracking()
            
            # Start documentation tasks
            self._start_documentation_tasks()
            
            self.logger.info("Model Documentation Agent initialized successfully")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to initialize Model Documentation Agent: {str(e)}")
            return False

    async def _initialize_templates(self) -> None:
        """Initialize document templates"""
        try:
            # Initialize Jinja2 environment
            self.jinja_env = jinja2.Environment(
                loader=jinja2.FileSystemLoader("templates"),
                autoescape=True
            )
            
            # Load document templates
            self.templates = {
                DocumentType.API: {
                    "markdown": await self._load_template("api.md.j2"),
                    "html": await self._load_template("api.html.j2"),
                    "rst": await self._load_template("api.rst.j2")
                },
                DocumentType.USAGE: {
                    "markdown": await self._load_template("usage.md.j2"),
                    "html": await self._load_template("usage.html.j2"),
                    "rst": await self._load_template("usage.rst.j2")
                },
                DocumentType.TECHNICAL: {
                    "markdown": await self._load_template("technical.md.j2"),
                    "html": await self._load_template("technical.html.j2"),
                    "rst": await self._load_template("technical.rst.j2")
                }
            }
            
            # Initialize template helpers
            self.template_helpers = {
                "format_code": self._format_code_block,
                "create_link": self._create_document_link,
                "insert_image": self._insert_image
            }
            
        except Exception as e:
            raise Exception(f"Failed to initialize templates: {str(e)}")

    async def _initialize_search_index(self) -> None:
        """Initialize search indexing"""
        try:
            # Initialize search configurations
            self.search_configs = {
                "index_fields": [
                    "title",
                    "content",
                    "metadata.description",
                    "tags"
                ],
                "excluded_terms": [
                    "the",
                    "and",
                    "or",
                    "in",
                    "on",
                    "at"
                ],
                "min_term_length": 3,
                "max_term_length": 50
            }
            
            # Initialize index structures
            self.search_index = {
                "terms": {},
                "documents": {},
                "metadata": {}
            }
            
            # Load existing index
            stored_index = await db_utils.get_agent_state(
                self.id,
                "search_index"
            )
            
            if stored_index:
                self.search_index = stored_index
                
        except Exception as e:
            raise Exception(f"Failed to initialize search index: {str(e)}")

    async def _initialize_document_tracking(self) -> None:
        """Initialize document tracking"""
        try:
            # Initialize document versioning
            self.doc_versions = {}
            
            # Initialize document status tracking
            self.doc_status = {
                status: set()
                for status in DocumentStatus
            }
            
            # Initialize review tracking
            self.review_tracking = {
                "pending": set(),
                "in_progress": set(),
                "completed": set()
            }
            
            # Load document history
            stored_history = await db_utils.get_agent_state(
                self.id,
                "doc_history"
            )
            
            if stored_history:
                self.doc_history = stored_history
                
        except Exception as e:
            raise Exception(f"Failed to initialize document tracking: {str(e)}")

    def _start_documentation_tasks(self) -> None:
        """Start documentation tasks"""
        asyncio.create_task(self._update_documentation())
        asyncio.create_task(self._maintain_index())
        asyncio.create_task(self._review_documents())

    async def generate_documentation(
        self,
        model_type: str,
        doc_type: str,
        format: str,
        options: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """
        Generate model documentation
        
        Args:
            model_type: Type of model
            doc_type: Type of documentation
            format: Output format
            options: Optional generation options
            
        Returns:
            Dictionary containing generated documentation
        """
        try:
            # Validate inputs
            if doc_type not in DocumentType:
                return {
                    "success": False,
                    "error": f"Invalid document type: {doc_type}"
                }
            
            if format not in DocumentFormat:
                return {
                    "success": False,
                    "error": f"Invalid format: {format}"
                }
            
            # Get template
            template = self.templates.get(doc_type, {}).get(format)
            if not template:
                return {
                    "success": False,
                    "error": f"Template not found for {doc_type} in {format}"
                }
            
            # Gather documentation data
            doc_data = await self._gather_doc_data(
                model_type,
                doc_type,
                options or {}
            )
            
            # Generate documentation
            content = await self._generate_content(
                template,
                doc_data,
                format
            )
            
            # Create document
            document = Document(
                id=f"doc_{datetime.now().timestamp()}",
                type=doc_type,
                format=format,
                title=doc_data["title"],
                content=content,
                metadata=doc_data["metadata"],
                version="1.0.0",
                status=DocumentStatus.DRAFT,
                created_at=datetime.now(),
                updated_at=datetime.now(),
                author="ModelDocumentationAgent",
                reviewers=[],
                tags=doc_data.get("tags", [])
            )
            
            # Store document
            self.documents[document.id] = document
            
            # Index document
            await self._index_document(document)
            
            return {
                "success": True,
                "document_id": document.id,
                "content": content
            }
            
        except Exception as e:
            self.logger.error(f"Documentation generation failed: {str(e)}")
            return {
                "success": False,
                "error": str(e)
            }

    async def update_documentation(
        self,
        document_id: str,
        updates: Dict[str, Any],
        options: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """
        Update existing documentation
        
        Args:
            document_id: Document identifier
            updates: Updates to apply
            options: Optional update options
            
        Returns:
            Dictionary containing update results
        """
        try:
            # Get document
            document = self.documents.get(document_id)
            if not document:
                return {
                    "success": False,
                    "error": f"Document not found: {document_id}"
                }
            
            # Create new version
            new_version = await self._create_document_version(
                document,
                updates
            )
            
            # Apply updates
            for field, value in updates.items():
                if hasattr(document, field):
                    setattr(document, field, value)
            
            document.updated_at = datetime.now()
            document.version = new_version
            
            # Re-index document
            await self._index_document(document)
            
            # Store update in history
            await self._store_document_update(
                document_id,
                updates,
                new_version
            )
            
            return {
                "success": True,
                "document_id": document_id,
                "version": new_version
            }
            
        except Exception as e:
            self.logger.error(f"Documentation update failed: {str(e)}")
            return {
                "success": False,
                "error": str(e)
            }

    async def search_documentation(
        self,
        query: str,
        filters: Optional[Dict] = None,
        options: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """
        Search documentation
        
        Args:
            query: Search query
            filters: Optional search filters
            options: Optional search options
            
        Returns:
            Dictionary containing search results
        """
        try:
            # Process query
            processed_query = await self._process_search_query(query)
            
            # Apply filters
            filtered_docs = await self._apply_search_filters(
                self.documents,
                filters or {}
            )
            
            # Search documents
            results = []
            for doc_id, document in filtered_docs.items():
                score = await self._calculate_search_score(
                    processed_query,
                    document
                )
                
                if score > 0:
                    results.append({
                        "document_id": doc_id,
                        "title": document.title,
                        "type": document.type,
                        "score": score,
                        "snippet": await self._generate_search_snippet(
                            document,
                            processed_query
                        )
                    })
            
            # Sort results by score
            results.sort(key=lambda x: x["score"], reverse=True)
            
            # Apply pagination
            page_size = options.get("page_size", 10)
            page = options.get("page", 1)
            paginated_results = results[
                (page - 1) * page_size:
                page * page_size
            ]
            
            return {
                "success": True,
                "results": paginated_results,
                "total": len(results),
                "page": page,
                "pages": (len(results) + page_size - 1) // page_size
            }
            
        except Exception as e:
            self.logger.error(f"Documentation search failed: {str(e)}")
            return {
                "success": False,
                "error": str(e)
            }

    async def _update_documentation(self) -> None:
        """Update documentation continuously"""
        while True:
            try:
                # Check each document
                for doc_id, document in self.documents.items():
                    # Check if update is needed
                    if await self._needs_update(document):
                        # Generate update
                        updates = await self._generate_doc_updates(document)
                        
                        if updates:
                            # Apply update
                            await self.update_documentation(
                                doc_id,
                                updates
                            )
                
                # Wait before next update
                await asyncio.sleep(3600)  # Update every hour
                
            except Exception as e:
                self.logger.error(f"Error in documentation update: {str(e)}")
                await asyncio.sleep(3600)

    async def _maintain_index(self) -> None:
        """Maintain search index"""
        while True:
            try:
                # Optimize index
                await self._optimize_search_index()
                
                # Clean up old entries
                await self._cleanup_search_index()
                
                # Update index statistics
                await self._update_index_stats()
                
                # Wait before next maintenance
                await asyncio.sleep(86400)  # Maintain daily
                
            except Exception as e:
                self.logger.error(f"Error in index maintenance: {str(e)}")
                await asyncio.sleep(86400)

    async def _review_documents(self) -> None:
        """Review documents"""
        while True:
            try:
                # Check documents needing review
                for doc_id in self.review_tracking["pending"]:
                    document = self.documents.get(doc_id)
                    if document:
                        # Perform review
                        review_result = await self._review_document(document)
                        
                        # Handle review result
                        await self._handle_review_result(
                            doc_id,
                            review_result
                        )
                
                # Wait before next review
                await asyncio.sleep(3600)  # Review every hour
                
            except Exception as e:
                self.logger.error(f"Error in document review: {str(e)}")
                await asyncio.sleep(3600)

# Global documentation agent instance
documentation_agent = ModelDocumentationAgent()
