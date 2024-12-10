"""
Model Security Manager for AATS
Handles authentication, authorization, and security policies for model access
"""

import asyncio
import logging
from typing import Any, Dict, List, Optional, Set, Union
from datetime import datetime, timedelta
import json
import hashlib
import secrets
import jwt
from dataclasses import dataclass

from .model_manager import ModelType
from ..config.settings.agent_model_config import MODEL_CAPABILITIES
from ..integration.databases.utils import db_utils

@dataclass
class SecurityPolicy:
    """Security policy definitions"""
    require_authentication: bool = True
    require_authorization: bool = True
    max_token_limit: int = 4096
    content_filtering: bool = True
    rate_limiting: bool = True
    audit_logging: bool = True

class AccessLevel(str):
    """Access level definitions"""
    READ = "read"
    WRITE = "write"
    ADMIN = "admin"
    SYSTEM = "system"

class SecurityEvent(str):
    """Security event types"""
    AUTH_SUCCESS = "auth_success"
    AUTH_FAILURE = "auth_failure"
    ACCESS_DENIED = "access_denied"
    POLICY_VIOLATION = "policy_violation"
    SECURITY_ALERT = "security_alert"

class ModelSecurityManager:
    """
    Model Security Manager responsible for handling authentication,
    authorization, and security policies.
    """

    def __init__(self):
        self.logger = logging.getLogger("ModelSecurityManager")
        self.security_policies: Dict[str, SecurityPolicy] = {}
        self.access_tokens: Dict[str, Dict] = {}
        self.security_events: List[Dict] = []
        self.blocked_entities: Set[str] = set()
        self.jwt_secret: str = secrets.token_hex(32)

    async def initialize(self) -> bool:
        """Initialize the Model Security Manager"""
        try:
            self.logger.info("Initializing Model Security Manager...")
            
            # Initialize security policies
            await self._initialize_security_policies()
            
            # Initialize access control
            await self._initialize_access_control()
            
            # Initialize security monitoring
            await self._initialize_security_monitoring()
            
            # Start security tasks
            self._start_security_tasks()
            
            self.logger.info("Model Security Manager initialized successfully")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to initialize Model Security Manager: {str(e)}")
            return False

    async def _initialize_security_policies(self) -> None:
        """Initialize security policies"""
        try:
            # Set up base policies for each model type
            for model_type in ModelType:
                self.security_policies[model_type] = SecurityPolicy(
                    require_authentication=True,
                    require_authorization=True,
                    max_token_limit=MODEL_CAPABILITIES[model_type]["context_window"],
                    content_filtering=True,
                    rate_limiting=True,
                    audit_logging=True
                )
            
            # Load custom policies
            custom_policies = await db_utils.get_agent_state(
                "security_manager",
                "security_policies"
            )
            
            if custom_policies:
                self._merge_policies(custom_policies)
                
        except Exception as e:
            raise Exception(f"Failed to initialize security policies: {str(e)}")

    async def _initialize_access_control(self) -> None:
        """Initialize access control system"""
        try:
            # Set up access control parameters
            self.access_control = {
                "token_expiry": timedelta(hours=24),
                "max_failed_attempts": 3,
                "lockout_duration": timedelta(minutes=30),
                "rate_limits": {
                    AccessLevel.READ: 100,   # requests per minute
                    AccessLevel.WRITE: 50,
                    AccessLevel.ADMIN: 200,
                    AccessLevel.SYSTEM: 500
                }
            }
            
            # Initialize rate limiting
            self.rate_limits = {
                access_level: {
                    "count": 0,
                    "reset_time": datetime.now() + timedelta(minutes=1)
                }
                for access_level in AccessLevel.__dict__.keys()
                if not access_level.startswith('_')
            }
            
        except Exception as e:
            raise Exception(f"Failed to initialize access control: {str(e)}")

    async def _initialize_security_monitoring(self) -> None:
        """Initialize security monitoring system"""
        try:
            # Set up monitoring parameters
            self.monitoring_config = {
                "event_retention_days": 90,
                "alert_thresholds": {
                    "auth_failures": 5,
                    "access_denials": 10,
                    "policy_violations": 3
                },
                "scan_interval": 300  # 5 minutes
            }
            
            # Initialize event tracking
            self.event_counts = {
                SecurityEvent.AUTH_FAILURE: 0,
                SecurityEvent.ACCESS_DENIED: 0,
                SecurityEvent.POLICY_VIOLATION: 0
            }
            
        except Exception as e:
            raise Exception(f"Failed to initialize security monitoring: {str(e)}")

    def _start_security_tasks(self) -> None:
        """Start security monitoring tasks"""
        asyncio.create_task(self._monitor_security_events())
        asyncio.create_task(self._cleanup_expired_tokens())
        asyncio.create_task(self._update_security_policies())

    async def authenticate(
        self,
        credentials: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Authenticate access request
        
        Args:
            credentials: Authentication credentials
            
        Returns:
            Dictionary containing authentication result
        """
        try:
            # Validate credentials
            if not self._validate_credentials(credentials):
                await self._handle_auth_failure(credentials)
                return {
                    "authenticated": False,
                    "error": "Invalid credentials"
                }
            
            # Generate access token
            token = self._generate_token(credentials)
            
            # Store token
            self.access_tokens[token] = {
                "user": credentials.get("user"),
                "access_level": self._get_access_level(credentials),
                "created_at": datetime.now().isoformat(),
                "expires_at": (
                    datetime.now() + self.access_control["token_expiry"]
                ).isoformat()
            }
            
            # Log authentication
            await self._log_security_event(
                SecurityEvent.AUTH_SUCCESS,
                {"user": credentials.get("user")}
            )
            
            return {
                "authenticated": True,
                "token": token,
                "expires_at": self.access_tokens[token]["expires_at"]
            }
            
        except Exception as e:
            self.logger.error(f"Authentication failed: {str(e)}")
            return {
                "authenticated": False,
                "error": str(e)
            }

    async def authorize(
        self,
        token: str,
        model_type: ModelType,
        request: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Authorize model access request
        
        Args:
            token: Access token
            model_type: Type of model to access
            request: Request details
            
        Returns:
            Dictionary containing authorization result
        """
        try:
            # Validate token
            token_info = self._validate_token(token)
            if not token_info:
                return {
                    "authorized": False,
                    "error": "Invalid or expired token"
                }
            
            # Check access level
            if not self._check_access_level(
                token_info["access_level"],
                model_type,
                request
            ):
                await self._log_security_event(
                    SecurityEvent.ACCESS_DENIED,
                    {
                        "user": token_info["user"],
                        "model": model_type,
                        "request": request
                    }
                )
                return {
                    "authorized": False,
                    "error": "Insufficient access level"
                }
            
            # Check rate limits
            if not await self._check_rate_limit(
                token_info["access_level"]
            ):
                return {
                    "authorized": False,
                    "error": "Rate limit exceeded"
                }
            
            # Check security policies
            policy_check = await self._check_security_policies(
                model_type,
                request
            )
            if not policy_check["compliant"]:
                await self._log_security_event(
                    SecurityEvent.POLICY_VIOLATION,
                    {
                        "user": token_info["user"],
                        "model": model_type,
                        "violations": policy_check["violations"]
                    }
                )
                return {
                    "authorized": False,
                    "error": "Security policy violation",
                    "violations": policy_check["violations"]
                }
            
            return {
                "authorized": True,
                "token_info": token_info
            }
            
        except Exception as e:
            self.logger.error(f"Authorization failed: {str(e)}")
            return {
                "authorized": False,
                "error": str(e)
            }

    async def validate_request(
        self,
        model_type: ModelType,
        request: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Validate request against security policies
        
        Args:
            model_type: Type of model
            request: Request details
            
        Returns:
            Dictionary containing validation result
        """
        try:
            policy = self.security_policies[model_type]
            violations = []
            
            # Check token limit
            if len(request.get("prompt", "")) > policy.max_token_limit:
                violations.append({
                    "type": "token_limit",
                    "message": "Token limit exceeded"
                })
            
            # Check content filtering
            if policy.content_filtering:
                content_issues = await self._check_content(
                    request.get("prompt", "")
                )
                if content_issues:
                    violations.append({
                        "type": "content_filtering",
                        "issues": content_issues
                    })
            
            return {
                "valid": len(violations) == 0,
                "violations": violations
            }
            
        except Exception as e:
            self.logger.error(f"Request validation failed: {str(e)}")
            return {
                "valid": False,
                "error": str(e)
            }

    async def _monitor_security_events(self) -> None:
        """Monitor security events continuously"""
        while True:
            try:
                current_time = datetime.now()
                
                # Check event thresholds
                for event_type, count in self.event_counts.items():
                    threshold = self.monitoring_config["alert_thresholds"].get(
                        event_type
                    )
                    if threshold and count >= threshold:
                        await self._handle_security_alert(
                            event_type,
                            count
                        )
                
                # Reset counts periodically
                if current_time.minute == 0:  # Reset every hour
                    self.event_counts = {
                        event_type: 0
                        for event_type in SecurityEvent
                    }
                
                # Wait before next check
                await asyncio.sleep(
                    self.monitoring_config["scan_interval"]
                )
                
            except Exception as e:
                self.logger.error(f"Error in security monitoring: {str(e)}")
                await asyncio.sleep(
                    self.monitoring_config["scan_interval"]
                )

    async def _cleanup_expired_tokens(self) -> None:
        """Clean up expired access tokens"""
        while True:
            try:
                current_time = datetime.now()
                
                # Remove expired tokens
                expired_tokens = [
                    token for token, info in self.access_tokens.items()
                    if datetime.fromisoformat(info["expires_at"]) < current_time
                ]
                
                for token in expired_tokens:
                    del self.access_tokens[token]
                
                # Wait before next cleanup
                await asyncio.sleep(3600)  # Clean up every hour
                
            except Exception as e:
                self.logger.error(f"Error in token cleanup: {str(e)}")
                await asyncio.sleep(3600)

    async def _update_security_policies(self) -> None:
        """Update security policies periodically"""
        while True:
            try:
                # Load updated policies
                updated_policies = await db_utils.get_agent_state(
                    "security_manager",
                    "security_policies"
                )
                
                if updated_policies:
                    self._merge_policies(updated_policies)
                
                # Wait before next update
                await asyncio.sleep(3600)  # Update every hour
                
            except Exception as e:
                self.logger.error(f"Error in policy update: {str(e)}")
                await asyncio.sleep(3600)

    async def _log_security_event(
        self,
        event_type: str,
        details: Dict[str, Any]
    ) -> None:
        """Log security event"""
        try:
            event = {
                "type": event_type,
                "details": details,
                "timestamp": datetime.now().isoformat()
            }
            
            # Update event counts
            if event_type in self.event_counts:
                self.event_counts[event_type] += 1
            
            # Store event
            self.security_events.append(event)
            
            # Maintain event history size
            if len(self.security_events) > 1000:
                self.security_events = self.security_events[-1000:]
            
            # Store event in database
            await db_utils.record_event(
                event_type="security_event",
                data=event
            )
            
        except Exception as e:
            self.logger.error(f"Failed to log security event: {str(e)}")

# Global security manager instance
security_manager = ModelSecurityManager()
