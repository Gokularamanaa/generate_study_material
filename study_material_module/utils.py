import logging
import re
from .config import LOG_LEVEL

def setup_logging():
    """Sets up the standard logging configuration for the module."""
    logging.basicConfig(
        level=getattr(logging, LOG_LEVEL.upper(), logging.INFO),
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        handlers=[
            logging.StreamHandler()
        ]
    )
    # Reduce noise from external libraries
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("google").setLevel(logging.WARNING)

def slugify(text: str) -> str:
    """
    Converts a string to a safe filename slug.
    Replaces spaces and special characters with underscores, keeping alpha-numeric.
    """
    text = text.strip()
    # Replace spaces with underscores
    text = re.sub(r'\s+', '_', text)
    # Remove any characters that aren't alphanumeric or underscores
    text = re.sub(r'[^\w\-]', '', text)
    return text
