"""
Data Validation Agent Implementation
This agent handles data validation, quality checks, and schema compliance
"""

import asyncio
import logging
from typing import Any, Dict, List, Optional, Set, Union
from datetime import datetime
import json
import pandas as pd
import numpy as np
from pydantic import BaseModel, ValidationError, validator
import jsonschema
from jsonschema import validate, ValidationError as JsonSchemaError
import cerberus
import great_expectations as ge
from pandera import DataFrameSchema, Column, Check
import re
from email_validator import validate_email, EmailNotValidError

from ..base_agent import BaseAgent, AgentConfig
from ...config.settings.base_config import config
from ...integration.databases.utils import db_utils

class ValidationType(str):
    """Validation type definitions"""
    SCHEMA = "schema"
    QUALITY = "quality"
    INTEGRITY = "integrity"
    FORMAT = "format"
    BUSINESS_RULES = "business_rules"
    COMPLIANCE = "compliance"

class ValidationLevel(str):
    """Validation level definitions"""
    STRICT = "strict"
    LENIENT = "lenient"
    WARNING = "warning"
    ERROR = "error"

class DataValidationAgent(BaseAgent):
    """
    Data Validation Agent responsible for ensuring data quality,
    integrity, and compliance.
    """

    def __init__(self):
        super().__init__(AgentConfig(
            name="DataValidator",
            description="Handles data validation and quality checks",
            capabilities=[
                "schema_validation",
                "quality_checks",
                "integrity_validation",
                "format_validation",
                "rule_validation"
            ],
            required_tools=[
                "schema_validator",
                "quality_checker",
                "rule_engine"
            ],
            max_concurrent_tasks=5,
            priority_level=2
        ))
        self.validation_stats: Dict[str, Dict] = {}
        self.validation_methods: Dict[str, callable] = {}
        self.validation_schemas: Dict[str, Any] = {}

    async def initialize(self) -> bool:
        """Initialize the Data Validation Agent"""
        try:
            self.logger.info("Initializing Data Validation Agent...")
            
            # Initialize validation methods
            await self._initialize_validation_methods()
            
            # Initialize validation schemas
            await self._initialize_validation_schemas()
            
            # Initialize validation stats
            await self._initialize_validation_stats()
            
            self.logger.info("Data Validation Agent initialized successfully")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to initialize Data Validation Agent: {str(e)}")
            return False

    async def _initialize_validation_methods(self) -> None:
        """Initialize validation methods"""
        try:
            self.validation_methods = {
                ValidationType.SCHEMA: {
                    "json_schema": self._validate_json_schema,
                    "pydantic": self._validate_pydantic,
                    "pandera": self._validate_pandera
                },
                ValidationType.QUALITY: {
                    "completeness": self._check_completeness,
                    "accuracy": self._check_accuracy,
                    "consistency": self._check_consistency
                },
                ValidationType.INTEGRITY: {
                    "referential": self._check_referential_integrity,
                    "uniqueness": self._check_uniqueness,
                    "constraints": self._check_constraints
                },
                ValidationType.FORMAT: {
                    "email": self._validate_email_format,
                    "date": self._validate_date_format,
                    "numeric": self._validate_numeric_format
                },
                ValidationType.BUSINESS_RULES: {
                    "custom_rules": self._validate_custom_rules,
                    "domain_rules": self._validate_domain_rules,
                    "logic_rules": self._validate_logic_rules
                },
                ValidationType.COMPLIANCE: {
                    "gdpr": self._check_gdpr_compliance,
                    "hipaa": self._check_hipaa_compliance,
                    "pci": self._check_pci_compliance
                }
            }
            
            # Initialize validation configurations
            self.validation_configs = {
                "schema": {
                    "strict_mode": True,
                    "coerce_types": False
                },
                "quality": {
                    "completeness_threshold": 0.95,
                    "accuracy_threshold": 0.99
                },
                "integrity": {
                    "check_foreign_keys": True,
                    "enforce_constraints": True
                }
            }
            
        except Exception as e:
            raise Exception(f"Failed to initialize validation methods: {str(e)}")

    async def _initialize_validation_schemas(self) -> None:
        """Initialize validation schemas"""
        try:
            # Initialize base schemas
            self.validation_schemas = {
                "common": {
                    "email": {
                        "type": "string",
                        "pattern": r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
                    },
                    "date": {
                        "type": "string",
                        "format": "date"
                    },
                    "numeric": {
                        "type": "number"
                    }
                },
                "custom": {}
            }
            
            # Load custom schemas
            custom_schemas = await db_utils.get_agent_state(
                self.id,
                "validation_schemas"
            )
            
            if custom_schemas:
                self.validation_schemas["custom"].update(custom_schemas)
                
        except Exception as e:
            raise Exception(f"Failed to initialize validation schemas: {str(e)}")

    async def _initialize_validation_stats(self) -> None:
        """Initialize validation statistics"""
        try:
            self.validation_stats = {
                validation_type: {
                    "validations_performed": 0,
                    "passed_validations": 0,
                    "failed_validations": 0,
                    "average_duration": 0.0,
                    "last_validation": None
                }
                for validation_type in ValidationType.__dict__.keys()
                if not validation_type.startswith('_')
            }
            
            # Load historical stats
            stored_stats = await db_utils.get_agent_state(
                self.id,
                "validation_stats"
            )
            
            if stored_stats:
                self._merge_stats(stored_stats)
                
        except Exception as e:
            raise Exception(f"Failed to initialize validation stats: {str(e)}")

    async def validate_data(
        self,
        data: Any,
        validation_type: str,
        method: str,
        options: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """
        Validate data using specified method
        
        Args:
            data: Input data to validate
            validation_type: Type of validation
            method: Validation method
            options: Optional validation options
            
        Returns:
            Dictionary containing validation results
        """
        try:
            # Validate validation type
            if validation_type not in self.validation_methods:
                return {
                    "valid": False,
                    "error": f"Invalid validation type: {validation_type}"
                }
            
            # Get validation method
            validator = self.validation_methods[validation_type].get(method)
            if not validator:
                return {
                    "valid": False,
                    "error": f"Invalid method: {method}"
                }
            
            # Perform validation
            start_time = datetime.now()
            result = await validator(
                data,
                options or {}
            )
            duration = (datetime.now() - start_time).total_seconds()
            
            # Update statistics
            await self._update_validation_stats(
                validation_type,
                result["valid"],
                duration
            )
            
            return {
                "valid": result["valid"],
                "validation_type": validation_type,
                "method": method,
                "details": result["details"],
                "duration": duration
            }
            
        except Exception as e:
            self.logger.error(f"Data validation failed: {str(e)}")
            # Update statistics
            await self._update_validation_stats(
                validation_type,
                False,
                0.0
            )
            return {
                "valid": False,
                "error": str(e)
            }

    async def validate_schema(
        self,
        data: Any,
        schema: Dict[str, Any],
        options: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """
        Validate data against schema
        
        Args:
            data: Input data
            schema: Validation schema
            options: Optional validation options
            
        Returns:
            Dictionary containing validation results
        """
        try:
            # Determine schema type
            schema_type = options.get('schema_type', 'json_schema')
            
            # Get validator
            validator = self.validation_methods[ValidationType.SCHEMA].get(schema_type)
            if not validator:
                return {
                    "valid": False,
                    "error": f"Invalid schema type: {schema_type}"
                }
            
            # Validate schema
            result = await validator(
                data,
                schema,
                options
            )
            
            return {
                "valid": result["valid"],
                "schema_type": schema_type,
                "details": result["details"]
            }
            
        except Exception as e:
            self.logger.error(f"Schema validation failed: {str(e)}")
            return {
                "valid": False,
                "error": str(e)
            }

    async def check_quality(
        self,
        data: pd.DataFrame,
        checks: List[str],
        options: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """
        Perform quality checks on data
        
        Args:
            data: Input DataFrame
            checks: List of quality checks to perform
            options: Optional check options
            
        Returns:
            Dictionary containing quality check results
        """
        try:
            results = {}
            
            for check in checks:
                checker = self.validation_methods[ValidationType.QUALITY].get(check)
                if checker:
                    check_result = await checker(
                        data,
                        options or {}
                    )
                    results[check] = check_result
            
            # Calculate overall quality score
            quality_score = np.mean([
                result["score"]
                for result in results.values()
                if "score" in result
            ])
            
            return {
                "valid": quality_score >= options.get('threshold', 0.8),
                "quality_score": quality_score,
                "checks": results
            }
            
        except Exception as e:
            self.logger.error(f"Quality check failed: {str(e)}")
            return {
                "valid": False,
                "error": str(e)
            }

    async def _validate_json_schema(
        self,
        data: Any,
        schema: Dict[str, Any],
        options: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Validate using JSON Schema"""
        try:
            # Validate schema
            validate(instance=data, schema=schema)
            
            return {
                "valid": True,
                "details": {
                    "schema_format": "json_schema",
                    "validation_success": True
                }
            }
            
        except JsonSchemaError as e:
            return {
                "valid": False,
                "details": {
                    "schema_format": "json_schema",
                    "validation_success": False,
                    "error": str(e)
                }
            }

    async def _check_completeness(
        self,
        data: pd.DataFrame,
        options: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Check data completeness"""
        try:
            # Calculate completeness metrics
            total_cells = data.size
            missing_cells = data.isnull().sum().sum()
            completeness_ratio = 1 - (missing_cells / total_cells)
            
            # Check against threshold
            threshold = options.get(
                'completeness_threshold',
                self.validation_configs["quality"]["completeness_threshold"]
            )
            
            return {
                "valid": completeness_ratio >= threshold,
                "score": completeness_ratio,
                "details": {
                    "total_cells": total_cells,
                    "missing_cells": missing_cells,
                    "completeness_ratio": completeness_ratio,
                    "threshold": threshold
                }
            }
            
        except Exception as e:
            raise Exception(f"Completeness check failed: {str(e)}")

    async def _update_validation_stats(
        self,
        validation_type: str,
        success: bool,
        duration: float
    ) -> None:
        """Update validation statistics"""
        try:
            stats = self.validation_stats[validation_type]
            
            # Update counters
            stats["validations_performed"] += 1
            if success:
                stats["passed_validations"] += 1
            else:
                stats["failed_validations"] += 1
            
            # Update average duration
            total_validations = stats["validations_performed"]
            current_avg = stats["average_duration"]
            stats["average_duration"] = (
                (current_avg * (total_validations - 1) + duration) /
                total_validations
            )
            
            stats["last_validation"] = datetime.now().isoformat()
            
            # Store metrics
            await db_utils.record_metric(
                agent_id=self.id,
                metric_type="data_validation",
                value=duration,
                tags={
                    "validation_type": validation_type,
                    "success": success
                }
            )
            
        except Exception as e:
            self.logger.error(f"Failed to update validation stats: {str(e)}")

# Global data validator instance
data_validator = DataValidationAgent()
