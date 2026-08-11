import os
import re
import logging
import asyncio
import httpx
from tenacity import retry, stop_after_attempt, retry_if_exception, wait_exponential

from .config import (
    OPENAI_API_KEY,
    OPENROUTER_API_KEY,
    GROK_API_KEY,
    GEMINI_API_KEY,
    LLM_MODEL,
    GEMINI_MODEL,
    get_active_provider,
    get_default_model
)

logger = logging.getLogger(__name__)

PLACEHOLDER_API_KEYS = {
    "",
    "your_openai_api_key_here",
    "your_openrouter_api_key_here",
    "your_grok_api_key_here",
    "your_gemini_api_key_here",
    "your_api_key_here",
    "DEVELOPMENT_FALLBACK_KEY",
    "YOUR_API_KEY"
}


# --- Exception Hierarchy ---

class LLMException(Exception):
    """Base exception for all LLM API integration errors."""
    pass


class LLMConfigurationError(LLMException):
    """Raised when LLM configuration (e.g. API key or model) is missing or invalid."""
    pass


class LLMAuthenticationError(LLMException):
    """Raised when API key is rejected or unauthorized (401/403)."""
    pass


class LLMModelNotFoundError(LLMException):
    """Raised when the specified model is non-existent (404)."""
    pass


class LLMQuotaExceededError(LLMException):
    """Raised when API rate limit or quota is exceeded (429)."""
    pass


class LLMGenerationError(LLMException):
    """Raised when content generation fails after retries or returns empty content."""
    pass


# Backward compatibility aliases for Gemini exception types
GeminiException = LLMException
GeminiConfigurationError = LLMConfigurationError
GeminiAuthenticationError = LLMAuthenticationError
GeminiModelNotFoundError = LLMModelNotFoundError
GeminiQuotaExceededError = LLMQuotaExceededError
GeminiGenerationError = LLMGenerationError


# --- Helpers ---

def get_provider_and_key(provider: str = None) -> tuple[str, str]:
    """
    Returns (active_provider, api_key).
    Raises LLMConfigurationError if key is missing or placeholder.
    """
    active_provider = (provider or get_active_provider()).lower()
    
    if active_provider == "openai":
        api_key = os.getenv("OPENAI_API_KEY", OPENAI_API_KEY).strip()
        if not api_key or api_key in PLACEHOLDER_API_KEYS:
            raise LLMConfigurationError(
                "OpenAI API key is not configured or is a placeholder. "
                "Please set OPENAI_API_KEY in your environment or .env file."
            )
        return "openai", api_key

    elif active_provider == "openrouter":
        api_key = os.getenv("OPENROUTER_API_KEY", OPENROUTER_API_KEY).strip()
        if not api_key or api_key in PLACEHOLDER_API_KEYS:
            raise LLMConfigurationError(
                "OpenRouter API key is not configured or is a placeholder. "
                "Please set OPENROUTER_API_KEY in your environment or .env file."
            )
        return "openrouter", api_key
        
    elif active_provider in ("grok", "xai"):
        api_key = (os.getenv("GROK_API_KEY") or os.getenv("XAI_API_KEY") or GROK_API_KEY).strip()
        if not api_key or api_key in PLACEHOLDER_API_KEYS:
            raise LLMConfigurationError(
                "Grok / xAI API key is not configured or is a placeholder. "
                "Please set GROK_API_KEY or XAI_API_KEY in your environment or .env file."
            )
        return "grok", api_key
        
    elif active_provider == "gemini":
        api_key = os.getenv("GEMINI_API_KEY", GEMINI_API_KEY).strip()
        if not api_key or api_key in PLACEHOLDER_API_KEYS:
            raise LLMConfigurationError(
                "Gemini API key is not configured or is a placeholder. "
                "Please set GEMINI_API_KEY in your environment or .env file."
            )
        return "gemini", api_key
        
    else:
        raise LLMConfigurationError(f"Unsupported LLM provider: {active_provider}")


def is_retryable_exception(exception: Exception) -> bool:
    """
    Returns True for transient network/HTTP errors (429, 500, 502, 503, 504, Timeout).
    Returns False for non-retryable errors (401, 403, 404, 400).
    """
    if exception is None:
        return False
        
    if isinstance(exception, (LLMConfigurationError, LLMAuthenticationError, LLMModelNotFoundError)):
        return False
        
    if isinstance(exception, httpx.HTTPStatusError):
        code = exception.response.status_code
        if code in (401, 403, 404, 400):
            return False
        if code in (429, 500, 502, 503, 504):
            return True
            
    if isinstance(exception, (httpx.TimeoutException, httpx.NetworkError)):
        return True
        
    return True


def log_retry(retry_state):
    attempt = retry_state.attempt_number
    exc = retry_state.outcome.exception() if retry_state.outcome else None
    reason = str(exc) if exc else "Unknown error"
    if len(reason) > 200:
        reason = reason[:200] + "..."
    wait_time = retry_state.next_action.sleep if retry_state.next_action else 0.0
    logger.warning(
        f"LLM API request failed. Retrying (Attempt: {attempt}, Reason: '{reason}', Wait Time: {wait_time:.2f}s)"
    )


_llm_request_lock = asyncio.Lock()


# --- HTTP API Calls ---

@retry(
    stop=stop_after_attempt(2),
    wait=wait_exponential(multiplier=1, min=2, max=5),
    retry=retry_if_exception(is_retryable_exception),
    before_sleep=log_retry,
    reraise=True
)
async def call_openrouter_api(prompt: str, api_key: str, model_name: str) -> str:
    url = "https://openrouter.ai/api/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        "HTTP-Referer": "https://github.com/material_gen",
        "X-Title": "Study Material Generator"
    }
    payload = {
        "model": model_name,
        "messages": [
            {"role": "system", "content": "You are an expert university professor creating comprehensive study material."},
            {"role": "user", "content": prompt}
        ],
        "temperature": 0.2
    }
    
    async with httpx.AsyncClient(timeout=180.0) as client:
        response = await client.post(url, headers=headers, json=payload)
        
        if response.status_code == 401 or response.status_code == 403:
            raise LLMAuthenticationError(f"OpenRouter API Authentication Failed (HTTP {response.status_code}): {response.text}")
        elif response.status_code == 404:
            raise LLMModelNotFoundError(f"OpenRouter Model '{model_name}' Not Found (HTTP 404): {response.text}")
        elif response.status_code == 429:
            raise LLMQuotaExceededError(f"OpenRouter Rate Limit Exceeded (HTTP 429): {response.text}")
        elif response.status_code >= 400:
            raise LLMGenerationError(f"OpenRouter API Error (HTTP {response.status_code}): {response.text}")
            
        data = response.json()
        try:
            content = data["choices"][0]["message"]["content"]
            if not content or not str(content).strip():
                raise LLMGenerationError("OpenRouter API returned empty content.")
            return content
        except (KeyError, IndexError, TypeError) as e:
            raise LLMGenerationError(f"Failed to parse OpenRouter response: {str(e)} - Raw response: {data}")


async def call_grok_api(prompt: str, api_key: str, model_name: str) -> str:
    url = "https://api.x.ai/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    payload = {
        "model": model_name,
        "messages": [
            {"role": "system", "content": "You are an expert university professor creating comprehensive study material."},
            {"role": "user", "content": prompt}
        ],
        "temperature": 0.2
    }
    
    async with httpx.AsyncClient(timeout=180.0) as client:
        response = await client.post(url, headers=headers, json=payload)
        
        if response.status_code == 401 or response.status_code == 403:
            raise LLMAuthenticationError(f"Grok / xAI API Authentication Failed (HTTP {response.status_code}): {response.text}")
        elif response.status_code == 404:
            raise LLMModelNotFoundError(f"Grok Model '{model_name}' Not Found (HTTP 404): {response.text}")
        elif response.status_code == 429:
            raise LLMQuotaExceededError(f"Grok Rate Limit Exceeded (HTTP 429): {response.text}")
        elif response.status_code >= 400:
            raise LLMGenerationError(f"Grok API Error (HTTP {response.status_code}): {response.text}")
            
        data = response.json()
        try:
            content = data["choices"][0]["message"]["content"]
            if not content or not str(content).strip():
                raise LLMGenerationError("Grok API returned empty content.")
            return content
        except (KeyError, IndexError, TypeError) as e:
            raise LLMGenerationError(f"Failed to parse Grok response: {str(e)} - Raw response: {data}")


async def call_gemini_api(prompt: str, api_key: str, model_name: str) -> str:
    try:
        from google import genai
        from google.genai import types
        from google.genai.errors import APIError
    except ImportError:
        raise LLMConfigurationError("google-genai package is not installed.")
        
    target_model = model_name or GEMINI_MODEL or "gemini-2.0-flash"
    client = genai.Client(api_key=api_key)
    
    try:
        response = await client.aio.models.generate_content(
            model=target_model,
            contents=prompt,
            config=types.GenerateContentConfig(temperature=0.2)
        )
        if not response or not response.text:
            raise LLMGenerationError("Gemini API returned an empty text response.")
        return response.text
    except APIError as e:
        err_msg = str(e)
        code = getattr(e, "code", None)
        if code in (401, 403) or "API_KEY" in err_msg.upper():
            raise LLMAuthenticationError(f"Gemini API Authentication Failed: {err_msg}")
        elif code == 404 or "NOT_FOUND" in err_msg.upper():
            raise LLMModelNotFoundError(f"Gemini Model '{target_model}' Not Found: {err_msg}")
        elif code == 429 or "RESOURCE_EXHAUSTED" in err_msg.upper() or "QUOTA" in err_msg.upper():
            raise LLMQuotaExceededError(f"Gemini Rate Limit / Quota Exceeded: {err_msg}")
        else:
            raise LLMGenerationError(f"Gemini API Error: {err_msg}")
    except Exception as e:
        if isinstance(e, LLMException):
            raise e
        raise LLMGenerationError(f"Gemini API Call Failed: {str(e)}")


@retry(
    stop=stop_after_attempt(2),
    wait=wait_exponential(multiplier=1, min=2, max=5),
    retry=retry_if_exception(is_retryable_exception),
    before_sleep=log_retry,
    reraise=True
)
async def call_openai_api(prompt: str, api_key: str, model_name: str) -> str:
    url = "https://api.openai.com/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    payload = {
        "model": model_name or "gpt-4o",
        "messages": [
            {"role": "system", "content": "You are an expert university professor creating comprehensive study material."},
            {"role": "user", "content": prompt}
        ],
        "temperature": 0.2
    }
    
    async with httpx.AsyncClient(timeout=180.0) as client:
        response = await client.post(url, headers=headers, json=payload)
        
        if response.status_code in (401, 403):
            raise LLMAuthenticationError(f"OpenAI API Authentication Failed (HTTP {response.status_code}): {response.text}")
        elif response.status_code == 404:
            raise LLMModelNotFoundError(f"OpenAI Model '{model_name}' Not Found (HTTP 404): {response.text}")
        elif response.status_code == 429:
            raise LLMQuotaExceededError(f"OpenAI Rate Limit / Quota Exceeded (HTTP 429): {response.text}")
        elif response.status_code >= 400:
            raise LLMGenerationError(f"OpenAI API Error (HTTP {response.status_code}): {response.text}")
            
        data = response.json()
        try:
            content = data["choices"][0]["message"]["content"]
            if not content or not str(content).strip():
                raise LLMGenerationError("OpenAI API returned empty content.")
            return content
        except (KeyError, IndexError, TypeError) as e:
            raise LLMGenerationError(f"Failed to parse OpenAI response: {str(e)} - Raw response: {data}")


async def _execute_provider_call(provider_name: str, api_key: str, model_name: str, prompt: str) -> str:
    if provider_name == "openai":
        return await call_openai_api(prompt, api_key, model_name)
    elif provider_name == "openrouter":
        return await call_openrouter_api(prompt, api_key, model_name)
    elif provider_name == "grok":
        return await call_grok_api(prompt, api_key, model_name)
    elif provider_name == "gemini":
        return await call_gemini_api(prompt, api_key, model_name)
    else:
        raise LLMConfigurationError(f"Unsupported provider: {provider_name}")


# --- Main Async Entry Point ---

async def generate_study_material_for_topic_async(prompt: str, model_name: str = None, provider: str = None) -> str:
    """
    Asynchronously calls the configured LLM provider (OpenAI, Gemini, OpenRouter, or Grok).
    If the primary provider fails due to rate limits, quota limits, or errors,
    automatically falls back to alternative available providers.
    Enforces sequential request execution using asyncio.Lock.
    """
    primary_provider, primary_key = get_provider_and_key(provider)
    primary_model = model_name or get_default_model(primary_provider)

    providers_to_try = [(primary_provider, primary_key, primary_model)]

    # Collect available fallback providers
    all_providers = ["openai", "gemini", "openrouter", "grok"]
    for p in all_providers:
        if p != primary_provider:
            try:
                p_name, p_key = get_provider_and_key(p)
                p_model = get_default_model(p_name)
                providers_to_try.append((p_name, p_key, p_model))
            except LLMConfigurationError:
                pass

    async with _llm_request_lock:
        last_exception = None
        for prov_name, prov_key, prov_model in providers_to_try:
            logger.info(f"Generating content using Provider: '{prov_name}' | Model: '{prov_model}'...")
            try:
                content = await _execute_provider_call(prov_name, prov_key, prov_model, prompt)
                if content and str(content).strip():
                    return content
            except Exception as e:
                last_exception = e
                logger.warning(
                    f"Provider '{prov_name}' (Model: '{prov_model}') failed: {type(e).__name__}: {str(e)}. "
                    f"Attempting fallback..."
                )

        if last_exception:
            raise last_exception
        raise LLMGenerationError("All configured LLM providers failed to generate content.")
