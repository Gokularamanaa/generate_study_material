import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv(override=True)

# Base directory of the project
BASE_DIR = Path(__file__).resolve().parent.parent

# API Keys
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "").strip()
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY", "").strip()
GROK_API_KEY = os.getenv("GROK_API_KEY", "").strip() or os.getenv("XAI_API_KEY", "").strip()

# Provider selection ('gemini', 'openrouter', 'grok' or auto-detect)
LLM_PROVIDER = os.getenv("LLM_PROVIDER", "").strip().lower()

# Model selection
LLM_MODEL = os.getenv("LLM_MODEL", "").strip()

# Gemini parameters
_raw_model = os.getenv("GEMINI_MODEL", "gemini-2.0-flash").strip()
if _raw_model in ("gemini-2.5-flash", "gemini-2.5-pro", "gemini-1.0-pro"):
    GEMINI_MODEL = "gemini-2.0-flash"
else:
    GEMINI_MODEL = _raw_model

def get_active_provider() -> str:
    """
    Determines the active LLM provider.
    Priority: Explicit LLM_PROVIDER > GEMINI_API_KEY > OPENROUTER_API_KEY > GROK_API_KEY.
    """
    provider = os.getenv("LLM_PROVIDER", LLM_PROVIDER).strip().lower()
    if provider in ("gemini", "openrouter", "grok", "xai"):
        return "grok" if provider == "xai" else provider

    gemini_key = os.getenv("GEMINI_API_KEY", GEMINI_API_KEY).strip()
    openrouter_key = os.getenv("OPENROUTER_API_KEY", OPENROUTER_API_KEY).strip()
    grok_key = (os.getenv("GROK_API_KEY") or os.getenv("XAI_API_KEY") or GROK_API_KEY).strip()

    if gemini_key:
        return "gemini"
    if openrouter_key:
        return "openrouter"
    if grok_key:
        return "grok"
    return "gemini"


def get_default_model(provider: str) -> str:
    if provider == "gemini":
        if LLM_MODEL and not "/" in LLM_MODEL:
            return LLM_MODEL
        return GEMINI_MODEL or "gemini-2.0-flash"
    elif provider == "openrouter":
        if LLM_MODEL and "/" in LLM_MODEL:
            return LLM_MODEL
        return "meta-llama/llama-3.3-70b-instruct"
    elif provider == "grok":
        if LLM_MODEL and "grok" in LLM_MODEL.lower():
            return LLM_MODEL
        return "grok-2-latest"
    return LLM_MODEL or "gemini-2.0-flash"


OUTPUT_DIR = Path(os.getenv("OUTPUT_DIR", BASE_DIR / "output"))
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
