"""
Gemini Client module (re-exported from llm_client for backwards compatibility).
"""

from .llm_client import (
    generate_study_material_for_topic_async,
    LLMException as GeminiException,
    LLMConfigurationError as GeminiConfigurationError,
    LLMAuthenticationError as GeminiAuthenticationError,
    LLMModelNotFoundError as GeminiModelNotFoundError,
    LLMQuotaExceededError as GeminiQuotaExceededError,
    LLMGenerationError as GeminiGenerationError,
)

__all__ = [
    "generate_study_material_for_topic_async",
    "GeminiException",
    "GeminiConfigurationError",
    "GeminiAuthenticationError",
    "GeminiModelNotFoundError",
    "GeminiQuotaExceededError",
    "GeminiGenerationError",
]
