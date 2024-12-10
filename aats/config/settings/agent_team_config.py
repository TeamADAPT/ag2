"""
Team Configuration for AATS
This module defines agent team structure, relationships, and coordination
"""

from typing import Dict, Any, List
from enum import Enum

class AgentRole(str, Enum):
    """Agent role definitions"""
    STRATEGIC = "strategic"
    TACTICAL = "tactical"
    OPERATIONAL = "operational"

class AgentPriority(str, Enum):
    """Agent priority levels"""
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"

# Team Structure
TEAM_STRUCTURE = {
    "strategic": {
        "project_manager": {
            "role": AgentRole.STRATEGIC,
            "priority": AgentPriority.CRITICAL,
            "supervises": [
                "resource_optimizer",
                "security_officer",
                "data_architect",
                "integration_specialist",
                "quality_assurance",
                "knowledge_manager",
                "compliance_monitor"
            ],
            "coordinates_with": ["communication_coordinator"],
            "responsibilities": [
                "project oversight",
                "resource allocation",
                "strategic planning",
                "team coordination"
            ]
        },
        "resource_optimizer": {
            "role": AgentRole.STRATEGIC,
            "priority": AgentPriority.HIGH,
            "supervises": [
                "model_performance_agent",
                "model_cost_agent",
                "cache_manager_agent"
            ],
            "coordinates_with": ["project_manager", "data_architect"],
            "responsibilities": [
                "resource optimization",
                "performance tuning",
                "capacity planning"
            ]
        },
        "security_officer": {
            "role": AgentRole.STRATEGIC,
            "priority": AgentPriority.CRITICAL,
            "supervises": [
                "model_security_agent",
                "data_compliance_agent"
            ],
            "coordinates_with": ["compliance_monitor", "project_manager"],
            "responsibilities": [
                "security oversight",
                "access control",
                "threat monitoring"
            ]
        },
        "data_architect": {
            "role": AgentRole.STRATEGIC,
            "priority": AgentPriority.HIGH,
            "supervises": [
                "database_controller_agent",
                "data_integration_agent",
                "data_pipeline_agent"
            ],
            "coordinates_with": ["integration_specialist", "resource_optimizer"],
            "responsibilities": [
                "data architecture",
                "schema design",
                "data flow optimization"
            ]
        },
        "integration_specialist": {
            "role": AgentRole.STRATEGIC,
            "priority": AgentPriority.HIGH,
            "supervises": [
                "api_gateway_agent",
                "message_broker_agent",
                "atlassian_integration_agent"
            ],
            "coordinates_with": ["data_architect", "project_manager"],
            "responsibilities": [
                "system integration",
                "api management",
                "service coordination"
            ]
        },
        "quality_assurance": {
            "role": AgentRole.STRATEGIC,
            "priority": AgentPriority.HIGH,
            "supervises": [
                "model_testing_agent",
                "data_validation_agent"
            ],
            "coordinates_with": ["knowledge_manager", "project_manager"],
            "responsibilities": [
                "quality control",
                "testing oversight",
                "validation management"
            ]
        },
        "knowledge_manager": {
            "role": AgentRole.STRATEGIC,
            "priority": AgentPriority.MEDIUM,
            "supervises": [
                "model_documentation_agent",
                "search_specialist_agent"
            ],
            "coordinates_with": ["quality_assurance", "project_manager"],
            "responsibilities": [
                "knowledge management",
                "documentation oversight",
                "information organization"
            ]
        },
        "compliance_monitor": {
            "role": AgentRole.STRATEGIC,
            "priority": AgentPriority.HIGH,
            "supervises": [
                "data_compliance_agent",
                "model_versioning_agent"
            ],
            "coordinates_with": ["security_officer", "project_manager"],
            "responsibilities": [
                "compliance monitoring",
                "policy enforcement",
                "audit management"
            ]
        }
    },
    "tactical": {
        "communication_coordinator": {
            "role": AgentRole.TACTICAL,
            "priority": AgentPriority.HIGH,
            "coordinates_with": ["project_manager", "all_operational"],
            "responsibilities": [
                "inter-agent communication",
                "message routing",
                "coordination facilitation"
            ]
        }
    },
    "operational": {
        "model_agents": {
            "model_connectivity_agent": {
                "role": AgentRole.OPERATIONAL,
                "priority": AgentPriority.CRITICAL,
                "coordinates_with": [
                    "model_selection_agent",
                    "model_performance_agent"
                ],
                "responsibilities": [
                    "model connection management",
                    "api interaction",
                    "request handling"
                ]
            },
            "model_selection_agent": {
                "role": AgentRole.OPERATIONAL,
                "priority": AgentPriority.HIGH,
                "coordinates_with": [
                    "model_connectivity_agent",
                    "model_performance_agent"
                ],
                "responsibilities": [
                    "model selection",
                    "routing optimization",
                    "fallback management"
                ]
            },
            "model_performance_agent": {
                "role": AgentRole.OPERATIONAL,
                "priority": AgentPriority.HIGH,
                "coordinates_with": [
                    "model_selection_agent",
                    "model_cost_agent"
                ],
                "responsibilities": [
                    "performance monitoring",
                    "optimization",
                    "metrics tracking"
                ]
            }
        },
        "data_agents": {
            "database_controller_agent": {
                "role": AgentRole.OPERATIONAL,
                "priority": AgentPriority.CRITICAL,
                "coordinates_with": [
                    "data_integration_agent",
                    "data_pipeline_agent"
                ],
                "responsibilities": [
                    "database operations",
                    "data persistence",
                    "query optimization"
                ]
            },
            "data_extraction_agent": {
                "role": AgentRole.OPERATIONAL,
                "priority": AgentPriority.MEDIUM,
                "coordinates_with": [
                    "data_transformation_agent",
                    "data_validation_agent"
                ],
                "responsibilities": [
                    "data extraction",
                    "source processing",
                    "content parsing"
                ]
            }
        }
    }
}

# Communication Patterns
COMMUNICATION_PATTERNS = {
    "synchronous": {
        "priority": AgentPriority.CRITICAL,
        "timeout": 30,  # seconds
        "retry_attempts": 3
    },
    "asynchronous": {
        "priority": AgentPriority.MEDIUM,
        "message_ttl": 3600,  # seconds
        "delivery_guarantee": "at_least_once"
    },
    "broadcast": {
        "priority": AgentPriority.LOW,
        "delivery_mode": "fire_and_forget"
    }
}

# Coordination Rules
COORDINATION_RULES = {
    "task_delegation": {
        "max_delegation_depth": 3,
        "delegation_timeout": 300,  # seconds
        "require_acceptance": True
    },
    "conflict_resolution": {
        "strategy": "priority_based",
        "escalation_threshold": 2,
        "resolution_timeout": 60  # seconds
    },
    "resource_sharing": {
        "max_concurrent_users": 5,
        "lock_timeout": 30,  # seconds
        "priority_queue": True
    }
}

# Team Monitoring
TEAM_MONITORING = {
    "metrics": {
        "collection_interval": 60,  # seconds
        "aggregation_window": 300,  # seconds
        "retention_period": 86400  # seconds
    },
    "alerts": {
        "coordination_failure": {
            "threshold": 3,
            "window": 300,  # seconds
            "priority": AgentPriority.HIGH
        },
        "communication_failure": {
            "threshold": 5,
            "window": 300,  # seconds
            "priority": AgentPriority.CRITICAL
        }
    },
    "health_checks": {
        "interval": 30,  # seconds
        "timeout": 5,  # seconds
        "unhealthy_threshold": 3
    }
}

# Team Performance Targets
TEAM_PERFORMANCE = {
    "response_time": {
        "p50": 1.0,  # seconds
        "p95": 3.0,
        "p99": 5.0
    },
    "throughput": {
        "min_rate": 100,  # tasks per second
        "target_rate": 500,
        "max_rate": 1000
    },
    "success_rate": {
        "min": 0.95,
        "target": 0.99,
        "critical": 0.90
    }
}

# Team Scaling Rules
TEAM_SCALING = {
    "auto_scaling": {
        "enabled": True,
        "min_instances": 1,
        "max_instances": 5,
        "scale_up_threshold": 0.8,
        "scale_down_threshold": 0.2
    },
    "load_balancing": {
        "strategy": "least_loaded",
        "health_weight": 0.3,
        "capacity_weight": 0.7
    }
}

# Team Recovery Procedures
TEAM_RECOVERY = {
    "agent_failure": {
        "max_restart_attempts": 3,
        "restart_delay": 5,  # seconds
        "fallback_mode": "degraded"
    },
    "coordination_failure": {
        "reset_timeout": 30,  # seconds
        "recovery_mode": "consensus",
        "quorum_size": 0.6
    }
}

# Human in the Loop Settings
HITL_SETTINGS = {
    "intervention_points": {
        "critical_decisions": True,
        "error_resolution": True,
        "quality_control": True
    },
    "approval_requirements": {
        "strategic_changes": True,
        "resource_allocation": True,
        "security_updates": True
    },
    "notification_rules": {
        "channels": ["slack", "email", "dashboard"],
        "urgency_levels": {
            "low": {"delay": 3600},  # 1 hour
            "medium": {"delay": 300},  # 5 minutes
            "high": {"delay": 0}  # immediate
        }
    }
}

# Development Settings
if __debug__:
    # Reduce timeouts and thresholds
    for pattern in COMMUNICATION_PATTERNS.values():
        if "timeout" in pattern:
            pattern["timeout"] = min(pattern["timeout"], 5)
    
    # Enable additional monitoring
    TEAM_MONITORING["debug"] = {
        "trace_communications": True,
        "log_decisions": True,
        "performance_profiling": True
    }

# Testing Settings
if __name__ == "__main__":
    # Mock coordination for testing
    COORDINATION_RULES["task_delegation"]["require_acceptance"] = False
    COORDINATION_RULES["conflict_resolution"]["strategy"] = "first_come"
    
    # Disable actual scaling
    TEAM_SCALING["auto_scaling"]["enabled"] = False

# Production Settings
if not __debug__:
    # Stricter monitoring
    TEAM_MONITORING["alerts"]["coordination_failure"]["threshold"] = 2
    TEAM_MONITORING["alerts"]["communication_failure"]["threshold"] = 3
    
    # Higher performance targets
    TEAM_PERFORMANCE["success_rate"]["min"] = 0.98
    TEAM_PERFORMANCE["success_rate"]["target"] = 0.995
