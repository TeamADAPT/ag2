"""
Model Configuration for AATS
This module contains model-specific settings and configurations
"""

from typing import Dict, Any
import os

# Model Selection Criteria
MODEL_SELECTION_CRITERIA = {
    "default": {
        "primary_model": "gpt-4",
        "fallback_model": "gpt-35-turbo",
        "selection_factors": {
            "performance_weight": 0.3,
            "cost_weight": 0.2,
            "reliability_weight": 0.3,
            "latency_weight": 0.2
        }
    },
    "code_generation": {
        "primary_model": "claude-2",
        "fallback_model": "gpt-4",
        "selection_factors": {
            "performance_weight": 0.4,
            "cost_weight": 0.1,
            "reliability_weight": 0.3,
            "latency_weight": 0.2
        }
    },
    "text_analysis": {
        "primary_model": "mistral-medium",
        "fallback_model": "claude-instant",
        "selection_factors": {
            "performance_weight": 0.3,
            "cost_weight": 0.3,
            "reliability_weight": 0.2,
            "latency_weight": 0.2
        }
    }
}

# Model Capabilities
MODEL_CAPABILITIES = {
    "gpt-4": {
        "max_tokens": 8192,
        "supports_functions": True,
        "supports_vision": True,
        "strengths": [
            "complex reasoning",
            "code generation",
            "creative writing",
            "analysis"
        ],
        "optimal_use_cases": [
            "system design",
            "code review",
            "technical writing",
            "problem solving"
        ],
        "limitations": [
            "higher latency",
            "higher cost",
            "token limit constraints"
        ]
    },
    "gpt-35-turbo": {
        "max_tokens": 4096,
        "supports_functions": True,
        "supports_vision": False,
        "strengths": [
            "fast responses",
            "general knowledge",
            "basic coding",
            "conversation"
        ],
        "optimal_use_cases": [
            "quick queries",
            "basic assistance",
            "data processing",
            "simple automation"
        ],
        "limitations": [
            "less precise",
            "simpler reasoning",
            "no vision support"
        ]
    },
    "claude-2": {
        "max_tokens": 100000,
        "supports_functions": True,
        "supports_vision": False,
        "strengths": [
            "long context",
            "code generation",
            "technical analysis",
            "documentation"
        ],
        "optimal_use_cases": [
            "large document analysis",
            "complex coding tasks",
            "technical writing",
            "research"
        ],
        "limitations": [
            "no vision support",
            "higher cost",
            "variable latency"
        ]
    },
    "claude-instant": {
        "max_tokens": 50000,
        "supports_functions": True,
        "supports_vision": False,
        "strengths": [
            "fast responses",
            "cost effective",
            "decent accuracy",
            "good comprehension"
        ],
        "optimal_use_cases": [
            "content moderation",
            "data processing",
            "basic analysis",
            "quick responses"
        ],
        "limitations": [
            "less sophisticated",
            "no vision support",
            "simpler tasks only"
        ]
    },
    "mistral-medium": {
        "max_tokens": 32000,
        "supports_functions": True,
        "supports_vision": False,
        "strengths": [
            "balanced performance",
            "consistent results",
            "good reasoning",
            "efficient processing"
        ],
        "optimal_use_cases": [
            "text analysis",
            "content generation",
            "data processing",
            "general tasks"
        ],
        "limitations": [
            "no vision support",
            "medium context length",
            "general purpose"
        ]
    },
    "mistral-small": {
        "max_tokens": 32000,
        "supports_functions": True,
        "supports_vision": False,
        "strengths": [
            "fast execution",
            "cost effective",
            "efficient",
            "consistent"
        ],
        "optimal_use_cases": [
            "simple tasks",
            "quick processing",
            "basic analysis",
            "data handling"
        ],
        "limitations": [
            "simpler tasks only",
            "less sophisticated",
            "basic capabilities"
        ]
    }
}

# Model Performance Thresholds
MODEL_PERFORMANCE_THRESHOLDS = {
    "latency": {
        "excellent": 1.0,  # seconds
        "good": 2.0,
        "acceptable": 3.0,
        "poor": 5.0
    },
    "error_rate": {
        "excellent": 0.01,  # 1%
        "good": 0.03,
        "acceptable": 0.05,
        "poor": 0.10
    },
    "success_rate": {
        "excellent": 0.99,  # 99%
        "good": 0.95,
        "acceptable": 0.90,
        "poor": 0.85
    },
    "token_efficiency": {
        "excellent": 0.90,  # 90% useful tokens
        "good": 0.80,
        "acceptable": 0.70,
        "poor": 0.60
    }
}

# Model Usage Quotas
MODEL_USAGE_QUOTAS = {
    "gpt-4": {
        "tokens_per_minute": 10000,
        "requests_per_minute": 50,
        "daily_token_limit": 1000000,
        "cost_limit_daily": 100.00
    },
    "gpt-35-turbo": {
        "tokens_per_minute": 20000,
        "requests_per_minute": 100,
        "daily_token_limit": 2000000,
        "cost_limit_daily": 50.00
    },
    "claude-2": {
        "tokens_per_minute": 15000,
        "requests_per_minute": 60,
        "daily_token_limit": 1500000,
        "cost_limit_daily": 75.00
    },
    "claude-instant": {
        "tokens_per_minute": 25000,
        "requests_per_minute": 120,
        "daily_token_limit": 2500000,
        "cost_limit_daily": 40.00
    },
    "mistral-medium": {
        "tokens_per_minute": 20000,
        "requests_per_minute": 80,
        "daily_token_limit": 2000000,
        "cost_limit_daily": 60.00
    },
    "mistral-small": {
        "tokens_per_minute": 30000,
        "requests_per_minute": 150,
        "daily_token_limit": 3000000,
        "cost_limit_daily": 30.00
    }
}

# Model Prompt Templates
MODEL_PROMPT_TEMPLATES = {
    "system_role": {
        "default": "You are a helpful AI assistant.",
        "code": "You are an expert software developer.",
        "analysis": "You are a data analysis expert.",
        "writing": "You are a professional technical writer."
    },
    "task_prefix": {
        "code": "Write code to accomplish the following:",
        "analysis": "Analyze the following data:",
        "explanation": "Explain the following concept:",
        "summary": "Provide a summary of:"
    },
    "response_format": {
        "code": "```{language}\n{code}\n```",
        "json": "```json\n{content}\n```",
        "markdown": "```markdown\n{content}\n```"
    }
}

# Model Context Settings
MODEL_CONTEXT_SETTINGS = {
    "token_buffer": 100,  # Reserve tokens for system messages
    "max_history_tokens": 1000,  # Maximum tokens to keep in conversation history
    "truncation_method": "sliding_window",  # How to truncate long conversations
    "context_window_overlap": 100  # Tokens to overlap when using sliding window
}

# Model Retry Settings
MODEL_RETRY_SETTINGS = {
    "max_retries": 3,
    "retry_delay": 1,  # seconds
    "backoff_factor": 2,
    "retry_on_errors": [
        "rate_limit_error",
        "timeout_error",
        "server_error",
        "connection_error"
    ]
}

# Model Fallback Chain
MODEL_FALLBACK_CHAIN = {
    "gpt-4": ["gpt-35-turbo", "claude-2", "mistral-medium"],
    "gpt-35-turbo": ["mistral-medium", "claude-instant", "mistral-small"],
    "claude-2": ["gpt-4", "mistral-medium", "gpt-35-turbo"],
    "claude-instant": ["mistral-small", "gpt-35-turbo", "mistral-medium"],
    "mistral-medium": ["gpt-35-turbo", "claude-instant", "mistral-small"],
    "mistral-small": ["claude-instant", "gpt-35-turbo", "mistral-medium"]
}

# Model Security Settings
MODEL_SECURITY_SETTINGS = {
    "input_validation": {
        "max_input_length": 10000,
        "allowed_mime_types": ["text/plain", "application/json"],
        "sanitize_input": True,
        "block_keywords": ["sudo", "rm -rf", "DROP TABLE"]
    },
    "output_validation": {
        "sanitize_output": True,
        "max_output_length": 50000,
        "content_filtering": True,
        "pii_detection": True
    }
}

# Development Settings
if os.getenv("ENVIRONMENT") == "development":
    # Reduce quotas for development
    for model in MODEL_USAGE_QUOTAS:
        MODEL_USAGE_QUOTAS[model] = {
            k: v // 10 if isinstance(v, int) else v / 10
            for k, v in MODEL_USAGE_QUOTAS[model].items()
        }
    
    # Add development-specific prompt templates
    MODEL_PROMPT_TEMPLATES["system_role"]["debug"] = "You are in development mode."

# Testing Settings
if os.getenv("ENVIRONMENT") == "testing":
    # Use mock models for testing
    MODEL_SELECTION_CRITERIA["default"]["primary_model"] = "mock-model"
    MODEL_SELECTION_CRITERIA["default"]["fallback_model"] = "mock-model-fallback"
    
    # Disable actual API calls
    for model in MODEL_CAPABILITIES:
        MODEL_CAPABILITIES[model]["mock_responses"] = True

# Production Settings
if os.getenv("ENVIRONMENT") == "production":
    # Enforce stricter security
    MODEL_SECURITY_SETTINGS["input_validation"]["sanitize_input"] = True
    MODEL_SECURITY_SETTINGS["output_validation"]["content_filtering"] = True
    
    # Enable all production monitoring
    for model in MODEL_CAPABILITIES:
        MODEL_CAPABILITIES[model]["monitoring_enabled"] = True
