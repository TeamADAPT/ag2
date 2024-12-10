"""
Data Architect Agent Implementation
This agent manages data structures, schemas, and data relationships across the system.
"""

from typing import Any, Dict, List, Optional, Set, Union
import asyncio
import logging
from datetime import datetime
import json
from pathlib import Path

from ..base_agent import BaseAgent, AgentConfig
from ...config.settings.base_config import config
from ...integration.databases.utils import db_utils
from ...integration.databases.schema import (
    POSTGRES_SCHEMAS,
    MONGODB_SCHEMAS,
    NEO4J_SCHEMAS,
    initialize_schemas
)

class SchemaType(str):
    """Schema type definitions"""
    RELATIONAL = "relational"
    DOCUMENT = "document"
    GRAPH = "graph"
    CACHE = "cache"

class DataOperation(str):
    """Data operation types"""
    CREATE = "create"
    READ = "read"
    UPDATE = "update"
    DELETE = "delete"
    MIGRATE = "migrate"
    VALIDATE = "validate"

class DataArchitectAgent(BaseAgent):
    """
    Data Architect Agent responsible for managing data structures,
    schemas, and data relationships across the system.
    """

    def __init__(self):
        super().__init__(AgentConfig(
            name="DataArchitect",
            description="Manages data structures and schemas",
            capabilities=[
                "schema_management",
                "data_modeling",
                "relationship_mapping",
                "data_validation"
            ],
            required_tools=[
                "schema_validator",
                "data_modeler",
                "relationship_mapper"
            ],
            max_concurrent_tasks=5,
            priority_level=1
        ))
        self.schemas: Dict[str, Dict] = {}
        self.relationships: Dict[str, List[Dict]] = {}
        self.validations: Dict[str, Dict] = {}
        self.schema_versions: Dict[str, str] = {}

    async def initialize(self) -> bool:
        """Initialize the Data Architect Agent"""
        try:
            self.logger.info("Initializing Data Architect Agent...")
            
            # Initialize schemas
            await self._initialize_schemas()
            
            # Initialize relationships
            await self._initialize_relationships()
            
            # Initialize validations
            await self._initialize_validations()
            
            self.logger.info("Data Architect Agent initialized successfully")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to initialize Data Architect Agent: {str(e)}")
            return False

    async def _initialize_schemas(self) -> None:
        """Initialize data schemas"""
        try:
            # Load base schemas
            self.schemas = {
                "postgres": POSTGRES_SCHEMAS,
                "mongodb": MONGODB_SCHEMAS,
                "neo4j": NEO4J_SCHEMAS
            }
            
            # Load custom schemas
            custom_schemas = await db_utils.get_agent_state(
                self.id,
                "custom_schemas"
            )
            
            if custom_schemas:
                for db_type, schemas in custom_schemas.items():
                    if db_type in self.schemas:
                        self.schemas[db_type].update(schemas)
                    else:
                        self.schemas[db_type] = schemas
            
            # Initialize schema versions
            for db_type in self.schemas:
                version = await self._get_schema_version(db_type)
                self.schema_versions[db_type] = version
                
        except Exception as e:
            raise Exception(f"Failed to initialize schemas: {str(e)}")

    async def _initialize_relationships(self) -> None:
        """Initialize data relationships"""
        try:
            # Load base relationships
            self.relationships = {
                "entity": [],  # Entity relationships
                "schema": [],  # Schema relationships
                "cross_db": []  # Cross-database relationships
            }
            
            # Load stored relationships
            stored_relationships = await db_utils.get_agent_state(
                self.id,
                "data_relationships"
            )
            
            if stored_relationships:
                self.relationships.update(stored_relationships)
                
        except Exception as e:
            raise Exception(f"Failed to initialize relationships: {str(e)}")

    async def _initialize_validations(self) -> None:
        """Initialize data validations"""
        try:
            # Set up validation rules
            self.validations = {
                "type_validation": {
                    "enabled": True,
                    "strict": True
                },
                "relationship_validation": {
                    "enabled": True,
                    "check_integrity": True
                },
                "schema_validation": {
                    "enabled": True,
                    "enforce_constraints": True
                }
            }
            
            # Load custom validations
            custom_validations = await db_utils.get_agent_state(
                self.id,
                "validation_rules"
            )
            
            if custom_validations:
                self.validations.update(custom_validations)
                
        except Exception as e:
            raise Exception(f"Failed to initialize validations: {str(e)}")

    async def process_task(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process data architecture tasks
        
        Args:
            task: Dictionary containing task details
            
        Returns:
            Dictionary containing the task result
        """
        try:
            task_type = task.get('type', 'unknown')
            self.logger.info(f"Processing task of type: {task_type}")

            # Handle different types of tasks
            handlers = {
                'schema_management': self._handle_schema_management,
                'data_modeling': self._handle_data_modeling,
                'relationship_mapping': self._handle_relationship_mapping,
                'data_validation': self._handle_data_validation,
                'schema_migration': self._handle_schema_migration
            }

            handler = handlers.get(task_type, self._handle_unknown_task)
            result = await handler(task)

            # Log task completion
            await self._log_task_completion(task, result)

            return result

        except Exception as e:
            self.logger.error(f"Error processing task: {str(e)}")
            await self.handle_error(e, task)
            return {
                'success': False,
                'error': str(e),
                'task_id': task.get('id'),
                'timestamp': datetime.now().isoformat()
            }

    async def _handle_schema_management(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """Handle schema management tasks"""
        operation = task.get('operation')
        schema_type = task.get('schema_type')
        schema_data = task.get('schema')
        
        try:
            if operation == DataOperation.CREATE:
                result = await self._create_schema(
                    schema_type,
                    schema_data
                )
            elif operation == DataOperation.UPDATE:
                result = await self._update_schema(
                    schema_type,
                    schema_data
                )
            elif operation == DataOperation.DELETE:
                result = await self._delete_schema(
                    schema_type,
                    schema_data
                )
            else:
                raise ValueError(f"Unknown schema operation: {operation}")
            
            return {
                'success': True,
                'operation': operation,
                'result': result,
                'timestamp': datetime.now().isoformat()
            }
            
        except Exception as e:
            raise Exception(f"Schema management failed: {str(e)}")

    async def _handle_data_modeling(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """Handle data modeling tasks"""
        model_type = task.get('model_type')
        model_data = task.get('model')
        
        try:
            # Validate model
            validation = await self._validate_data_model(
                model_type,
                model_data
            )
            
            if not validation['valid']:
                return {
                    'success': False,
                    'errors': validation['errors'],
                    'timestamp': datetime.now().isoformat()
                }
            
            # Create or update model
            model = await self._create_data_model(
                model_type,
                model_data
            )
            
            return {
                'success': True,
                'model': model,
                'timestamp': datetime.now().isoformat()
            }
            
        except Exception as e:
            raise Exception(f"Data modeling failed: {str(e)}")

    async def _handle_relationship_mapping(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """Handle relationship mapping tasks"""
        relationship_type = task.get('relationship_type')
        source = task.get('source')
        target = task.get('target')
        properties = task.get('properties', {})
        
        try:
            # Validate relationship
            validation = await self._validate_relationship(
                relationship_type,
                source,
                target
            )
            
            if not validation['valid']:
                return {
                    'success': False,
                    'errors': validation['errors'],
                    'timestamp': datetime.now().isoformat()
                }
            
            # Create relationship
            relationship = await self._create_relationship(
                relationship_type,
                source,
                target,
                properties
            )
            
            return {
                'success': True,
                'relationship': relationship,
                'timestamp': datetime.now().isoformat()
            }
            
        except Exception as e:
            raise Exception(f"Relationship mapping failed: {str(e)}")

    async def _handle_data_validation(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """Handle data validation tasks"""
        validation_type = task.get('validation_type')
        data = task.get('data')
        schema = task.get('schema')
        
        try:
            # Perform validation
            validation = await self._validate_data(
                validation_type,
                data,
                schema
            )
            
            return {
                'success': True,
                'validation': validation,
                'timestamp': datetime.now().isoformat()
            }
            
        except Exception as e:
            raise Exception(f"Data validation failed: {str(e)}")

    async def _handle_schema_migration(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """Handle schema migration tasks"""
        source_schema = task.get('source_schema')
        target_schema = task.get('target_schema')
        migration_strategy = task.get('strategy', 'safe')
        
        try:
            # Validate migration
            validation = await self._validate_schema_migration(
                source_schema,
                target_schema
            )
            
            if not validation['valid']:
                return {
                    'success': False,
                    'errors': validation['errors'],
                    'timestamp': datetime.now().isoformat()
                }
            
            # Generate migration plan
            plan = await self._generate_migration_plan(
                source_schema,
                target_schema,
                migration_strategy
            )
            
            # Execute migration
            result = await self._execute_schema_migration(plan)
            
            return {
                'success': True,
                'migration': result,
                'timestamp': datetime.now().isoformat()
            }
            
        except Exception as e:
            raise Exception(f"Schema migration failed: {str(e)}")

    async def _create_schema(
        self,
        schema_type: str,
        schema_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Create new schema"""
        # Validate schema
        validation = await self._validate_schema_definition(
            schema_type,
            schema_data
        )
        
        if not validation['valid']:
            raise ValueError(f"Invalid schema: {validation['errors']}")
        
        # Add schema
        if schema_type not in self.schemas:
            self.schemas[schema_type] = {}
            
        schema_name = schema_data.get('name')
        self.schemas[schema_type][schema_name] = schema_data
        
        # Update version
        new_version = await self._increment_schema_version(schema_type)
        
        # Store schema
        await db_utils.record_event(
            event_type="schema_created",
            data={
                "type": schema_type,
                "name": schema_name,
                "version": new_version,
                "schema": schema_data
            }
        )
        
        return {
            "name": schema_name,
            "type": schema_type,
            "version": new_version,
            "schema": schema_data
        }

    async def _validate_schema_definition(
        self,
        schema_type: str,
        schema_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Validate schema definition"""
        errors = []
        
        # Check required fields
        required_fields = ['name', 'fields']
        for field in required_fields:
            if field not in schema_data:
                errors.append(f"Missing required field: {field}")
        
        if errors:
            return {
                "valid": False,
                "errors": errors
            }
        
        # Validate fields
        fields = schema_data.get('fields', {})
        for field_name, field_def in fields.items():
            field_errors = await self._validate_field_definition(
                field_name,
                field_def,
                schema_type
            )
            errors.extend(field_errors)
        
        return {
            "valid": len(errors) == 0,
            "errors": errors
        }

    async def _validate_field_definition(
        self,
        field_name: str,
        field_def: Dict[str, Any],
        schema_type: str
    ) -> List[str]:
        """Validate field definition"""
        errors = []
        
        # Check required field properties
        required_props = ['type']
        for prop in required_props:
            if prop not in field_def:
                errors.append(f"Field {field_name}: Missing required property: {prop}")
        
        # Validate field type
        if 'type' in field_def:
            valid_types = self._get_valid_types(schema_type)
            if field_def['type'] not in valid_types:
                errors.append(
                    f"Field {field_name}: Invalid type: {field_def['type']}"
                )
        
        return errors

    def _get_valid_types(self, schema_type: str) -> Set[str]:
        """Get valid field types for schema type"""
        base_types = {
            "string", "integer", "float", "boolean",
            "date", "datetime", "array", "object"
        }
        
        if schema_type == SchemaType.RELATIONAL:
            return base_types | {
                "serial", "text", "varchar", "numeric",
                "timestamp", "json", "jsonb"
            }
        elif schema_type == SchemaType.DOCUMENT:
            return base_types | {"objectId", "binary"}
        elif schema_type == SchemaType.GRAPH:
            return base_types | {"node", "relationship"}
        else:
            return base_types

    async def _log_task_completion(
        self,
        task: Dict[str, Any],
        result: Dict[str, Any]
    ) -> None:
        """Log task completion"""
        event = {
            "timestamp": datetime.now().isoformat(),
            "task": task,
            "result": result,
            "success": result.get('success', False)
        }
        
        # Store event
        await db_utils.record_event(
            event_type="data_architect_task",
            data=event
        )

    async def handle_error(
        self,
        error: Exception,
        task: Optional[Dict[str, Any]] = None
    ) -> None:
        """Handle errors during task processing"""
        self.state.error_count += 1
        
        error_details = {
            'error_type': type(error).__name__,
            'error_message': str(error),
            'task_id': task.get('id') if task else None,
            'timestamp': datetime.now().isoformat()
        }
        
        # Log error
        self.logger.error(f"Error in Data Architect Agent: {error_details}")
        
        # Store error for analysis
        await self._store_error(error_details)
        
        # Handle data implications
        await self._handle_data_error(error_details)

    async def _store_error(self, error_details: Dict[str, Any]) -> None:
        """Store error details for analysis"""
        await db_utils.record_event(
            event_type="data_architect_error",
            data=error_details
        )

    async def _handle_data_error(self, error_details: Dict[str, Any]) -> None:
        """Handle data implications of errors"""
        try:
            # Check for data-related errors
            if any(term in str(error_details).lower() 
                  for term in ["schema", "data", "validation", "relationship"]):
                # Create data event
                await db_utils.record_event(
                    event_type="data_error",
                    data=error_details
                )
                
                # Trigger validation check
                await self._validate_affected_schemas(
                    error_details
                )
            
        except Exception as e:
            self.logger.error(f"Failed to handle data error: {str(e)}")
