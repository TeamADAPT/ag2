"""
Compliance Monitor Agent Implementation
This agent ensures system compliance with standards, regulations, and policies.
"""

from typing import Any, Dict, List, Optional, Set, Union
import asyncio
import logging
from datetime import datetime, timedelta
import json
from pathlib import Path

from ..base_agent import BaseAgent, AgentConfig
from ...config.settings.base_config import config
from ...integration.databases.utils import db_utils

class ComplianceType(str):
    """Compliance type definitions"""
    SECURITY = "security"
    PRIVACY = "privacy"
    OPERATIONAL = "operational"
    REGULATORY = "regulatory"
    STANDARDS = "standards"

class ComplianceStatus(str):
    """Compliance status definitions"""
    COMPLIANT = "compliant"
    NON_COMPLIANT = "non_compliant"
    PENDING = "pending"
    EXEMPTED = "exempted"
    INVESTIGATING = "investigating"

class ComplianceMonitorAgent(BaseAgent):
    """
    Compliance Monitor Agent responsible for ensuring system compliance
    with standards, regulations, and policies.
    """

    def __init__(self):
        super().__init__(AgentConfig(
            name="ComplianceMonitor",
            description="Monitors and ensures system compliance",
            capabilities=[
                "compliance_monitoring",
                "policy_enforcement",
                "audit_management",
                "regulation_tracking"
            ],
            required_tools=[
                "compliance_checker",
                "policy_manager",
                "audit_logger"
            ],
            max_concurrent_tasks=5,
            priority_level=1
        ))
        self.compliance_policies: Dict[str, Dict] = {}
        self.compliance_status: Dict[str, Dict] = {}
        self.audit_records: List[Dict] = []
        self.exemptions: Dict[str, Dict] = {}

    async def initialize(self) -> bool:
        """Initialize the Compliance Monitor Agent"""
        try:
            self.logger.info("Initializing Compliance Monitor Agent...")
            
            # Initialize compliance policies
            await self._initialize_compliance_policies()
            
            # Initialize compliance status
            await self._initialize_compliance_status()
            
            # Initialize audit system
            await self._initialize_audit_system()
            
            self.logger.info("Compliance Monitor Agent initialized successfully")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to initialize Compliance Monitor Agent: {str(e)}")
            return False

    async def _initialize_compliance_policies(self) -> None:
        """Initialize compliance policies"""
        try:
            # Set up base policies
            self.compliance_policies = {
                ComplianceType.SECURITY: {
                    "access_control": {
                        "mfa_required": True,
                        "password_policy": {
                            "min_length": 12,
                            "complexity_required": True,
                            "expiration_days": 90
                        },
                        "session_policy": {
                            "timeout_minutes": 30,
                            "max_concurrent": 3
                        }
                    },
                    "data_protection": {
                        "encryption_required": True,
                        "key_rotation_days": 180,
                        "secure_transmission": True
                    },
                    "audit_logging": {
                        "enabled": True,
                        "retention_days": 365,
                        "detailed_logging": True
                    }
                },
                ComplianceType.PRIVACY: {
                    "data_handling": {
                        "data_minimization": True,
                        "retention_policy": {
                            "max_days": 730,
                            "secure_deletion": True
                        },
                        "consent_required": True
                    },
                    "data_access": {
                        "purpose_limitation": True,
                        "access_logging": True,
                        "user_rights": {
                            "access": True,
                            "rectification": True,
                            "erasure": True
                        }
                    }
                },
                ComplianceType.OPERATIONAL: {
                    "availability": {
                        "uptime_target": 99.9,
                        "backup_required": True,
                        "disaster_recovery": True
                    },
                    "performance": {
                        "response_time_ms": 200,
                        "throughput_min": 1000,
                        "resource_utilization": 80
                    },
                    "monitoring": {
                        "health_checks": True,
                        "alerting": True,
                        "metrics_collection": True
                    }
                }
            }
            
            # Load custom policies
            custom_policies = await db_utils.get_agent_state(
                self.id,
                "compliance_policies"
            )
            
            if custom_policies:
                self._merge_policies(custom_policies)
                
        except Exception as e:
            raise Exception(f"Failed to initialize compliance policies: {str(e)}")

    async def _initialize_compliance_status(self) -> None:
        """Initialize compliance status tracking"""
        try:
            # Set up status tracking
            self.compliance_status = {
                compliance_type: {
                    "status": ComplianceStatus.PENDING,
                    "last_check": None,
                    "violations": [],
                    "exemptions": []
                }
                for compliance_type in ComplianceType.__dict__.keys()
                if not compliance_type.startswith('_')
            }
            
            # Load stored status
            stored_status = await db_utils.get_agent_state(
                self.id,
                "compliance_status"
            )
            
            if stored_status:
                self._merge_status(stored_status)
                
        except Exception as e:
            raise Exception(f"Failed to initialize compliance status: {str(e)}")

    async def _initialize_audit_system(self) -> None:
        """Initialize audit system"""
        try:
            # Set up audit configuration
            self.audit_config = {
                "enabled": True,
                "detailed_logging": True,
                "retention_days": 365,
                "alert_on_violation": True,
                "periodic_review": True,
                "review_interval_days": 30
            }
            
            # Load recent audit records
            recent_records = await db_utils.get_agent_metrics(
                self.id,
                metric_type="compliance_audit",
                start_time=datetime.now() - timedelta(days=30)
            )
            
            self.audit_records.extend(recent_records)
            
        except Exception as e:
            raise Exception(f"Failed to initialize audit system: {str(e)}")

    async def process_task(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process compliance monitoring tasks
        
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
                'compliance_check': self._handle_compliance_check,
                'policy_enforcement': self._handle_policy_enforcement,
                'audit_management': self._handle_audit_management,
                'violation_response': self._handle_violation_response,
                'exemption_management': self._handle_exemption_management
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

    async def _handle_compliance_check(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """Handle compliance check tasks"""
        compliance_type = task.get('compliance_type')
        target = task.get('target')
        check_params = task.get('parameters', {})
        
        try:
            # Perform compliance check
            check_result = await self._check_compliance(
                compliance_type,
                target,
                check_params
            )
            
            # Update compliance status
            await self._update_compliance_status(
                compliance_type,
                check_result
            )
            
            # Handle violations if any
            if not check_result['compliant']:
                await self._handle_violations(
                    compliance_type,
                    check_result['violations']
                )
            
            return {
                'success': True,
                'compliance_type': compliance_type,
                'result': check_result,
                'timestamp': datetime.now().isoformat()
            }
            
        except Exception as e:
            raise Exception(f"Compliance check failed: {str(e)}")

    async def _handle_policy_enforcement(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """Handle policy enforcement tasks"""
        policy_type = task.get('policy_type')
        action = task.get('action')
        parameters = task.get('parameters', {})
        
        try:
            # Validate policy action
            validation = await self._validate_policy_action(
                policy_type,
                action,
                parameters
            )
            
            if not validation['valid']:
                return {
                    'success': False,
                    'errors': validation['errors'],
                    'timestamp': datetime.now().isoformat()
                }
            
            # Enforce policy
            enforcement_result = await self._enforce_policy(
                policy_type,
                action,
                parameters
            )
            
            return {
                'success': True,
                'policy_type': policy_type,
                'result': enforcement_result,
                'timestamp': datetime.now().isoformat()
            }
            
        except Exception as e:
            raise Exception(f"Policy enforcement failed: {str(e)}")

    async def _handle_audit_management(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """Handle audit management tasks"""
        audit_type = task.get('audit_type')
        scope = task.get('scope', [])
        parameters = task.get('parameters', {})
        
        try:
            # Perform audit
            audit_result = await self._perform_audit(
                audit_type,
                scope,
                parameters
            )
            
            # Generate audit report
            report = await self._generate_audit_report(
                audit_type,
                audit_result
            )
            
            # Store audit record
            await self._store_audit_record(
                audit_type,
                report
            )
            
            return {
                'success': True,
                'audit_type': audit_type,
                'report': report,
                'timestamp': datetime.now().isoformat()
            }
            
        except Exception as e:
            raise Exception(f"Audit management failed: {str(e)}")

    async def _check_compliance(
        self,
        compliance_type: str,
        target: str,
        parameters: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Check compliance against policies"""
        try:
            # Get applicable policies
            policies = self.compliance_policies.get(compliance_type, {})
            
            violations = []
            exemptions = []
            
            # Check each policy
            for policy_name, policy_rules in policies.items():
                # Check for exemptions
                if await self._check_exemption(target, policy_name):
                    exemptions.append(policy_name)
                    continue
                
                # Validate against policy rules
                validation = await self._validate_against_rules(
                    target,
                    policy_rules,
                    parameters
                )
                
                if not validation['valid']:
                    violations.append({
                        "policy": policy_name,
                        "violations": validation['violations']
                    })
            
            return {
                "compliant": len(violations) == 0,
                "violations": violations,
                "exemptions": exemptions,
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            raise Exception(f"Compliance check failed: {str(e)}")

    async def _validate_against_rules(
        self,
        target: str,
        rules: Dict[str, Any],
        parameters: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Validate target against policy rules"""
        violations = []
        
        try:
            for rule_name, rule_value in rules.items():
                if isinstance(rule_value, dict):
                    # Recursive check for nested rules
                    nested_validation = await self._validate_against_rules(
                        target,
                        rule_value,
                        parameters
                    )
                    if not nested_validation['valid']:
                        violations.extend(nested_validation['violations'])
                else:
                    # Check simple rule
                    if not await self._check_rule(
                        target,
                        rule_name,
                        rule_value,
                        parameters
                    ):
                        violations.append({
                            "rule": rule_name,
                            "expected": rule_value,
                            "actual": parameters.get(rule_name)
                        })
            
            return {
                "valid": len(violations) == 0,
                "violations": violations
            }
            
        except Exception as e:
            raise Exception(f"Rule validation failed: {str(e)}")

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
            event_type="compliance_task",
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
        self.logger.error(f"Error in Compliance Monitor Agent: {error_details}")
        
        # Store error for analysis
        await self._store_error(error_details)
        
        # Handle compliance implications
        await self._handle_compliance_error(error_details)

    async def _store_error(self, error_details: Dict[str, Any]) -> None:
        """Store error details for analysis"""
        await db_utils.record_event(
            event_type="compliance_error",
            data=error_details
        )

    async def _handle_compliance_error(self, error_details: Dict[str, Any]) -> None:
        """Handle compliance implications of errors"""
        try:
            # Check for compliance-related errors
            if any(term in str(error_details).lower() 
                  for term in ["compliance", "policy", "regulation", "audit"]):
                # Create compliance event
                await db_utils.record_event(
                    event_type="compliance_failure",
                    data=error_details
                )
                
                # Update compliance status
                await self._update_compliance_status_on_error(
                    error_details
                )
            
        except Exception as e:
            self.logger.error(f"Failed to handle compliance error: {str(e)}")
