import os
import logging
from typing import Optional

logger = logging.getLogger(__name__)

try:
    from groq import Groq
except ImportError:
    Groq = None # Handle case where package isn't installed yet (resilience)

def get_groq_client() -> Optional['Groq']:
    """
    Attempts to return a Groq client.
    Returns None if:
    - The API key is missing.
    - The 'groq' library is not installed.
    - Initialization fails for any reason.
    
    This function NEVER raises an exception, ensuring infrastructure safety.
    """
    if Groq is None:
        logger.debug("Groq library not installed or import failed.")
        return None

    api_key = os.getenv("GROQ_API_KEY")
    use_groq = os.getenv("USE_GROQ", "false").lower() == "true"

    if not use_groq:
        return None

    if not api_key:
        logger.warning("USE_GROQ is true, but GROQ_API_KEY is missing. Falling back to deterministic instra-structure.")
        return None

    try:
        client = Groq(api_key=api_key)
        return client
    except Exception as e:
        logger.error(f"Failed to initialize Groq client: {e}. Falling back to deterministic instra-structure.")
        return None
