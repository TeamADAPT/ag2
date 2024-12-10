"""
Model Security Agent Implementation
This agent handles security, access control, and protection of model interactions
"""

import asyncio
import logging
from typing import Any, Dict, List, Optional, Set, Union, Callable
from datetime import datetime, timedelta
import json
import hashlib
import hmac
import jwt
from dataclasses import dataclass
from enum import Enum
import re
from cryptography.fernet import Fernet
import aiohttp
import ssl

from ..base_agent import BaseAgent, AgentConfig
from ...config.settings.base_config import config
from ...integration.databases.utils import db_utils
from .model_connectivity_agent import ModelType, ModelProvider

class SecurityLevel(str, Enum):
    """Security level definitions"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"

class AccessType(str, Enum):
    """Access type definitions"""
    READ = "read"
    WRITE = "write"
    EXECUTE = "execute"
    ADMIN = "admin"

class ThreatLevel(str, Enum):
    """Threat level definitions"""
    INFO = "info"
    WARNING = "warning"
    ALERT = "alert"
    CRITICAL = "critical"

@dataclass
class SecurityPolicy:
    """Security policy definition"""
    model_type: str
    security_level: SecurityLevel
    access_controls: Dict[str, List[AccessType]]
    encryption_required: bool
    audit_logging: bool
    rate_limiting: Dict[str, int]
    ip_whitelist: Optional[List[str]] = None
    custom_rules: Optional[Dict[str, Any]] = None

class ModelSecurityAgent(BaseAgent):
    """
    Model Security Agent responsible for ensuring secure
    model interactions and access control.
    """

    def __init__(self):
        super().__init__(AgentConfig(
            name="ModelSecurity",
            description="Handles model security and access control",
            capabilities=[
                "access_control",
                "threat_detection",
                "encryption",
                "audit_logging",
                "security_monitoring"
            ],
            required_tools=[
                "security_manager",
                "access_controller",
                "threat_detector"
            ],
            max_concurrent_tasks=5,
            priority_level=1
        ))
        self.security_policies: Dict[str, SecurityPolicy] = {}
        self.active_sessions: Dict[str, Dict] = {}
        self.security_logs: Dict[str, List] = {}
        self.threat_registry: Dict[str, Dict] = {}
        self.encryption_key: Optional[bytes] = None

    async def initialize(self) -> bool:
        """Initialize the Model Security Agent"""
        try:
            self.logger.info("Initializing Model Security Agent...")
            
            # Initialize security policies
            await self._initialize_security_policies()
            
            # Initialize encryption
            await self._initialize_encryption()
            
            # Initialize threat detection
            await self._initialize_threat_detection()
            
            # Start security tasks
            self._start_security_tasks()
            
            self.logger.info("Model Security Agent initialized successfully")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to initialize Model Security Agent: {str(e)}")
            return False

    async def _initialize_security_policies(self) -> None:
        """Initialize security policies"""
        try:
            # Define default security policies
            self.security_policies = {
                ModelType.LLAMA: SecurityPolicy(
                    model_type=ModelType.LLAMA,
                    security_level=SecurityLevel.HIGH,
                    access_controls={
                        "default": [AccessType.READ],
                        "developer": [AccessType.READ, AccessType.EXECUTE],
                        "admin": [AccessType.READ, AccessType.WRITE, AccessType.EXECUTE, AccessType.ADMIN]
                    },
                    encryption_required=True,
                    audit_logging=True,
                    rate_limiting={
                        "default": 100,  # requests per minute
                        "developer": 500,
                        "admin": 1000
                    }
                ),
                ModelType.CLAUDE: SecurityPolicy(
                    model_type=ModelType.CLAUDE,
                    security_level=SecurityLevel.CRITICAL,
                    access_controls={
                        "default": [AccessType.READ],
                        "developer": [AccessType.READ, AccessType.EXECUTE],
                        "admin": [AccessType.READ, AccessType.WRITE, AccessType.EXECUTE, AccessType.ADMIN]
                    },
                    encryption_required=True,
                    audit_logging=True,
                    rate_limiting={
                        "default": 50,
                        "developer": 200,
                        "admin": 500
                    },
                    ip_whitelist=["10.0.0.0/8", "172.16.0.0/12", "192.168.0.0/16"]
                ),
                ModelType.MISTRAL: SecurityPolicy(
                    model_type=ModelType.MISTRAL,
                    security_level=SecurityLevel.HIGH,
                    access_controls={
                        "default": [AccessType.READ],
                        "developer": [AccessType.READ, AccessType.EXECUTE],
                        "admin": [AccessType.READ, AccessType.WRITE, AccessType.EXECUTE, AccessType.ADMIN]
                    },
                    encryption_required=True,
                    audit_logging=True,
                    rate_limiting={
                        "default": 60,
                        "developer": 300,
                        "admin": 600
                    }
                )
            }
            
            # Load custom policies
            custom_policies = await db_utils.get_agent_state(
                self.id,
                "security_policies"
            )
            
            if custom_policies:
                self._merge_security_policies(custom_policies)
                
        except Exception as e:
            raise Exception(f"Failed to initialize security policies: {str(e)}")

    async def _initialize_encryption(self) -> None:
        """Initialize encryption"""
        try:
            # Generate or load encryption key
            stored_key = await db_utils.get_agent_state(
                self.id,
                "encryption_key"
            )
            
            if stored_key:
                self.encryption_key = stored_key
            else:
                self.encryption_key = Fernet.generate_key()
                await db_utils.record_state(
                    self.id,
                    "encryption_key",
                    self.encryption_key
                )
            
            # Initialize encryption handler
            self.fernet = Fernet(self.encryption_key)
            
            # Initialize SSL context
            self.ssl_context = ssl.create_default_context()
            
        except Exception as e:
            raise Exception(f"Failed to initialize encryption: {str(e)}")

    async def _initialize_threat_detection(self) -> None:
        """Initialize threat detection"""
        try:
            # Initialize threat patterns
            self.threat_patterns = {
                "injection": r"(?i)(select|insert|update|delete|drop|union|exec|eval)",
                "xss": r"(?i)(<script|javascript:|vbscript:|expression\()",
                "path_traversal": r"(?i)(\.\.\/|\.\.\\)",
                "command_injection": r"(?i)(\||;|`|\$\(|\))",
                "sensitive_data": r"(?i)(password|secret|key|token|credential)"
            }
            
            # Initialize threat scoring
            self.threat_scoring = {
                "injection": 8,
                "xss": 7,
                "path_traversal": 8,
                "command_injection": 9,
                "sensitive_data": 6
            }
            
            # Initialize threat thresholds
            self.threat_thresholds = {
                ThreatLevel.INFO: 3,
                ThreatLevel.WARNING: 5,
                ThreatLevel.ALERT: 7,
                ThreatLevel.CRITICAL: 9
            }
            
        except Exception as e:
            raise Exception(f"Failed to initialize threat detection: {str(e)}")

    def _start_security_tasks(self) -> None:
        """Start security tasks"""
        asyncio.create_task(self._monitor_security())
        asyncio.create_task(self._scan_threats())
        asyncio.create_task(self._audit_access())

    async def validate_request(
        self,
        model_type: str,
        request_data: Dict[str, Any],
        context: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """
        Validate model request security
        
        Args:
            model_type: Type of model
            request_data: Request data to validate
            context: Optional request context
            
        Returns:
            Dictionary containing validation results
        """
        try:
            # Get security policy
            policy = self.security_policies.get(model_type)
            if not policy:
                return {
                    "valid": False,
                    "error": f"No security policy for model: {model_type}"
                }
            
            # Validate access
            access_result = await self._validate_access(
                policy,
                request_data,
                context or {}
            )
            if not access_result["valid"]:
                return access_result
            
            # Check rate limits
            rate_result = await self._check_rate_limits(
                policy,
                context or {}
            )
            if not rate_result["valid"]:
                return rate_result
            
            # Scan for threats
            threat_result = await self._scan_for_threats(
                request_data
            )
            if threat_result["threats_found"]:
                return {
                    "valid": False,
                    "error": "Security threats detected",
                    "threats": threat_result["threats"]
                }
            
            # Log request
            if policy.audit_logging:
                await self._log_security_event(
                    "request_validation",
                    {
                        "model_type": model_type,
                        "request": request_data,
                        "context": context,
                        "result": "valid"
                    }
                )
            
            return {
                "valid": True,
                "session_id": access_result["session_id"]
            }
            
        except Exception as e:
            self.logger.error(f"Request validation failed: {str(e)}")
            return {
                "valid": False,
                "error": str(e)
            }

    async def encrypt_data(
        self,
        data: Any,
        options: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """
        Encrypt sensitive data
        
        Args:
            data: Data to encrypt
            options: Optional encryption options
            
        Returns:
            Dictionary containing encrypted data
        """
        try:
            # Prepare data for encryption
            data_str = (
                json.dumps(data)
                if isinstance(data, (dict, list))
                else str(data)
            )
            
            # Encrypt data
            encrypted_data = self.fernet.encrypt(
                data_str.encode()
            )
            
            # Generate metadata
            metadata = {
                "timestamp": datetime.now().isoformat(),
                "encryption_version": "1.0",
                "options": options or {}
            }
            
            return {
                "success": True,
                "encrypted_data": encrypted_data,
                "metadata": metadata
            }
            
        except Exception as e:
            self.logger.error(f"Data encryption failed: {str(e)}")
            return {
                "success": False,
                "error": str(e)
            }

    async def decrypt_data(
        self,
        encrypted_data: bytes,
        options: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """
        Decrypt encrypted data
        
        Args:
            encrypted_data: Data to decrypt
            options: Optional decryption options
            
        Returns:
            Dictionary containing decrypted data
        """
        try:
            # Decrypt data
            decrypted_data = self.fernet.decrypt(encrypted_data)
            
            # Parse decrypted data
            try:
                parsed_data = json.loads(decrypted_data)
            except json.JSONDecodeError:
                parsed_data = decrypted_data.decode()
            
            return {
                "success": True,
                "decrypted_data": parsed_data
            }
            
        except Exception as e:
            self.logger.error(f"Data decryption failed: {str(e)}")
            return {
                "success": False,
                "error": str(e)
            }

    async def _monitor_security(self) -> None:
        """Monitor security continuously"""
        while True:
            try:
                current_time = datetime.now()
                
                # Check active sessions
                for session_id, session in list(self.active_sessions.items()):
                    # Check session expiry
                    if current_time > session["expires_at"]:
                        await self._terminate_session(session_id)
                    
                    # Check for suspicious activity
                    if await self._detect_suspicious_activity(session):
                        await self._handle_suspicious_activity(session)
                
                # Wait before next check
                await asyncio.sleep(60)  # Check every minute
                
            except Exception as e:
                self.logger.error(f"Error in security monitoring: {str(e)}")
                await asyncio.sleep(60)

    async def _scan_threats(self) -> None:
        """Scan for security threats"""
        while True:
            try:
                # Scan security logs
                threats = await self._analyze_security_logs()
                
                if threats:
                    # Update threat registry
                    await self._update_threat_registry(threats)
                    
                    # Handle detected threats
                    await self._handle_threats(threats)
                
                # Wait before next scan
                await asyncio.sleep(300)  # Scan every 5 minutes
                
            except Exception as e:
                self.logger.error(f"Error in threat scanning: {str(e)}")
                await asyncio.sleep(300)

    async def _audit_access(self) -> None:
        """Audit access patterns"""
        while True:
            try:
                # Generate access audit
                audit_results = await self._generate_access_audit()
                
                # Check for policy violations
                violations = self._check_policy_violations(
                    audit_results
                )
                
                if violations:
                    await self._handle_policy_violations(violations)
                
                # Store audit results
                await self._store_audit_results(audit_results)
                
                # Wait before next audit
                await asyncio.sleep(3600)  # Audit every hour
                
            except Exception as e:
                self.logger.error(f"Error in access auditing: {str(e)}")
                await asyncio.sleep(3600)

# Global security agent instance
security_agent = ModelSecurityAgent()
