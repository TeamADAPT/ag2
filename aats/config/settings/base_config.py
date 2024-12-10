"""
Base Configuration for AATS
This module contains all default settings and configurations
"""

from typing import Dict, Any
import os
from pathlib import Path

# Base Paths
BASE_DIR = Path(__file__).resolve().parent.parent.parent
DATA_DIR = BASE_DIR / "data"
LOGS_DIR = BASE_DIR / "logs"
CACHE_DIR = BASE_DIR / "cache"

# Environment Settings
ENV = os.getenv("ENVIRONMENT", "development")
DEBUG = os.getenv("DEBUG", "true").lower() == "true"
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")

# Database Configurations
DATABASES = {
    "postgres": {
        "host": os.getenv("POSTGRES_HOST", "localhost"),
        "port": int(os.getenv("POSTGRES_PORT", "5432")),
        "database": os.getenv("POSTGRES_DB", "aats_main"),
        "user": os.getenv("POSTGRES_USER", "postgres"),
        "password": os.getenv("POSTGRES_PASSWORD", ""),
        "min_connections": 5,
        "max_connections": 20,
        "connection_timeout": 30,
        "schemas": {
            "agent_state": "agent_state",
            "model_data": "model_data",
            "metrics": "metrics",
            "audit": "audit"
        }
    },
    "mongodb": {
        "uri": os.getenv("MONGODB_URI", "mongodb://localhost:27017"),
        "database": os.getenv("MONGODB_DB", "aats_main"),
        "min_pool_size": 5,
        "max_pool_size": 20,
        "collections": {
            "agent_state": "agent_state",
            "model_cache": "model_cache",
            "metrics": "metrics",
            "audit_logs": "audit_logs"
        }
    },
    "redis": {
        "host": os.getenv("REDIS_HOST", "localhost"),
        "port": int(os.getenv("REDIS_PORT", "6379")),
        "db_mapping": {
            "cache": 0,
            "rate_limiting": 1,
            "session_state": 2
        },
        "max_connections": 20,
        "socket_timeout": 5
    },
    "neo4j": {
        "uri": os.getenv("NEO4J_URI", "bolt://localhost:7687"),
        "user": os.getenv("NEO4J_USER", "neo4j"),
        "password": os.getenv("NEO4J_PASSWORD", "password"),
        "max_connection_lifetime": 3600,
        "max_connection_pool_size": 50
    }
}

# Message Broker Configurations
MESSAGE_BROKERS = {
    "kafka": {
        "bootstrap_servers": os.getenv("KAFKA_BROKERS", "localhost:9092").split(","),
        "client_id": "aats_agent",
        "group_id": "aats_agent_group",
        "topics": {
            "agent_events": "agent-events",
            "model_events": "model-events",
            "system_events": "system-events"
        },
        "num_partitions": 3,
        "replication_factor": 1
    },
    "rabbitmq": {
        "host": os.getenv("RABBITMQ_HOST", "localhost"),
        "port": int(os.getenv("RABBITMQ_PORT", "5672")),
        "virtual_host": os.getenv("RABBITMQ_VHOST", "/"),
        "username": os.getenv("RABBITMQ_USER", "guest"),
        "password": os.getenv("RABBITMQ_PASSWORD", "guest"),
        "exchanges": {
            "agent_events": "agent.events",
            "model_events": "model.events",
            "system_events": "system.events"
        }
    }
}

# Model Provider Configurations
MODEL_PROVIDERS = {
    "azure": {
        "api_version": "2023-05-15",
        "endpoint": os.getenv("AZURE_OPENAI_ENDPOINT"),
        "api_key": os.getenv("AZURE_OPENAI_API_KEY"),
        "deployment_map": {
            "gpt-4": "gpt-4",
            "gpt-35-turbo": "gpt-35-turbo",
            "text-embedding-ada-002": "text-embedding-ada-002"
        },
        "default_parameters": {
            "temperature": 0.7,
            "max_tokens": 1000,
            "top_p": 0.95
        }
    },
    "anthropic": {
        "api_key": os.getenv("ANTHROPIC_API_KEY"),
        "api_version": "2023-06-01",
        "models": {
            "claude-2": {
                "max_tokens": 100000,
                "default_temperature": 0.7
            },
            "claude-instant": {
                "max_tokens": 50000,
                "default_temperature": 0.7
            }
        }
    },
    "mistral": {
        "api_key": os.getenv("MISTRAL_API_KEY"),
        "api_version": "2023-12-01",
        "models": {
            "mistral-medium": {
                "max_tokens": 32000,
                "default_temperature": 0.7
            },
            "mistral-small": {
                "max_tokens": 32000,
                "default_temperature": 0.7
            }
        }
    }
}

# Agent Configurations
AGENT_CONFIG = {
    "max_concurrent_tasks": 5,
    "task_timeout": 300,
    "retry_attempts": 3,
    "retry_delay": 5,
    "state_persistence": True,
    "monitoring_enabled": True,
    "logging_enabled": True
}

# Monitoring Configurations
MONITORING = {
    "prometheus": {
        "enabled": True,
        "host": "localhost",
        "port": 9090,
        "metrics_path": "/metrics",
        "scrape_interval": "15s",
        "evaluation_interval": "15s"
    },
    "grafana": {
        "enabled": True,
        "host": "localhost",
        "port": 3000,
        "admin_user": os.getenv("GRAFANA_ADMIN_USER", "admin"),
        "admin_password": os.getenv("GRAFANA_ADMIN_PASSWORD", "admin")
    },
    "alertmanager": {
        "enabled": True,
        "host": "localhost",
        "port": 9093,
        "resolve_timeout": "5m"
    }
}

# Logging Configuration
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "standard": {
            "format": "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
        },
        "json": {
            "class": "pythonjsonlogger.jsonlogger.JsonFormatter",
            "format": "%(asctime)s %(name)s %(levelname)s %(message)s"
        }
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "standard",
            "level": LOG_LEVEL
        },
        "file": {
            "class": "logging.handlers.RotatingFileHandler",
            "filename": str(LOGS_DIR / "aats.log"),
            "maxBytes": 10485760,  # 10MB
            "backupCount": 5,
            "formatter": "json",
            "level": LOG_LEVEL
        }
    },
    "loggers": {
        "": {
            "handlers": ["console", "file"],
            "level": LOG_LEVEL
        }
    }
}

# Security Configurations
SECURITY = {
    "jwt": {
        "secret_key": os.getenv("JWT_SECRET_KEY", "your-secret-key"),
        "algorithm": "HS256",
        "access_token_expire_minutes": 30
    },
    "api_keys": {
        "header_name": "X-API-Key",
        "key_prefix": "aats_"
    },
    "cors": {
        "allowed_origins": ["*"],
        "allowed_methods": ["*"],
        "allowed_headers": ["*"]
    },
    "rate_limiting": {
        "enabled": True,
        "default_rate": "100/minute"
    }
}

# Cache Configuration
CACHING = {
    "default_ttl": 3600,
    "max_size": 1000,
    "enabled": True,
    "backend": "redis"
}

# Task Queue Configuration
TASK_QUEUE = {
    "broker": "kafka",
    "result_backend": "redis",
    "task_serializer": "json",
    "result_serializer": "json",
    "accept_content": ["json"],
    "enable_utc": True,
    "task_track_started": True,
    "task_time_limit": 3600,
    "worker_concurrency": 4
}

# Model Cost Configuration
MODEL_COSTS = {
    "gpt-4": {
        "input_cost_per_1k": 0.03,
        "output_cost_per_1k": 0.06
    },
    "gpt-35-turbo": {
        "input_cost_per_1k": 0.0015,
        "output_cost_per_1k": 0.002
    },
    "claude-2": {
        "input_cost_per_1k": 0.011,
        "output_cost_per_1k": 0.033
    },
    "claude-instant": {
        "input_cost_per_1k": 0.00163,
        "output_cost_per_1k": 0.00551
    },
    "mistral-medium": {
        "input_cost_per_1k": 0.007,
        "output_cost_per_1k": 0.007
    },
    "mistral-small": {
        "input_cost_per_1k": 0.002,
        "output_cost_per_1k": 0.002
    }
}

# Feature Flags
FEATURES = {
    "enable_model_caching": True,
    "enable_rate_limiting": True,
    "enable_cost_tracking": True,
    "enable_performance_monitoring": True,
    "enable_auto_scaling": True,
    "enable_feedback_collection": True
}

# Integration Settings
INTEGRATIONS = {
    "atlassian": {
        "jira_url": os.getenv("JIRA_URL"),
        "confluence_url": os.getenv("CONFLUENCE_URL"),
        "username": os.getenv("ATLASSIAN_USERNAME"),
        "api_token": os.getenv("ATLASSIAN_API_TOKEN"),
        "project_key": os.getenv("JIRA_PROJECT_KEY", "AATS")
    }
}

# Development Settings
if ENV == "development":
    DEBUG = True
    LOG_LEVEL = "DEBUG"
    FEATURES["enable_auto_scaling"] = False

# Testing Settings
if ENV == "testing":
    DATABASES = {
        "postgres": {**DATABASES["postgres"], "database": "aats_test"},
        "mongodb": {**DATABASES["mongodb"], "database": "aats_test"},
        "redis": {**DATABASES["redis"], "db_mapping": {"cache": 10, "rate_limiting": 11, "session_state": 12}},
        "neo4j": {**DATABASES["neo4j"], "database": "aats_test"}
    }
    DEBUG = True
    LOG_LEVEL = "DEBUG"
    FEATURES["enable_cost_tracking"] = False

# Production Settings
if ENV == "production":
    DEBUG = False
    LOG_LEVEL = "INFO"
    SECURITY["cors"]["allowed_origins"] = ["https://api.aats.ai"]
    FEATURES["enable_auto_scaling"] = True
