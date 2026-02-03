"""Groq API Client - Secure wrapper for LLM calls.

Handles:
- API authentication
- Request/response
- Timeout and error handling
- NO streaming
- NO logging of sensitive data
"""

import json
import logging
from typing import Optional
from groq import Groq, APIError, APITimeoutError, RateLimitError

from app.core.config import settings

# Configure logging (NEVER log API keys)
logger = logging.getLogger(__name__)


class GroqClient:
    """Minimal, secure wrapper for Groq API.
    
    Enforces:
    - Model: llama-3.3-70b-versatile (current stable model)
    - Temperature: 0 (deterministic)
    - Max tokens: Limited to prevent abuse
    - Timeout: 10 seconds max
    """
    
    MODEL = "llama-3.3-70b-versatile"
    TEMPERATURE = 0
    MAX_TOKENS = 256  # Intent JSON is small
    TIMEOUT_SECONDS = 3  # Fast response for better UX
    
    def __init__(self):
        """Initialize Groq client with API key from environment."""
        api_key = settings.GROQ_API_KEY
        
        if not api_key:
            logger.warning(
                "⚠️ GROQ_API_KEY not found in environment. "
                "LLM intent parsing will be DISABLED. "
                "Add your key to backend/.env file."
            )
            self.client = None
        else:
            try:
                self.client = Groq(api_key=api_key)
                logger.info("✅ Groq client initialized successfully")
            except Exception as e:
                logger.error(f"❌ Failed to initialize Groq client: {e}")
                self.client = None
    
    def is_available(self) -> bool:
        """Check if Groq client is ready to use."""
        return self.client is not None
    
    def extract_intent(self, prompt: str, max_retries: int = 2) -> Optional[str]:
        """Call Groq LLM to extract intent as JSON with retry logic.
        
        Args:
            prompt: Complete prompt with system instructions + user message
            max_retries: Number of retries for transient failures
            
        Returns:
            Raw JSON string from LLM, or None if error
            
        Raises:
            No exceptions - always returns None on error for graceful fallback
        """
        if not self.is_available():
            logger.debug("Groq client not available - skipping LLM call")
            return None
        
        for attempt in range(max_retries + 1):
            try:
                response = self.client.chat.completions.create(
                    model=self.MODEL,
                    messages=[
                        {
                            "role": "user",
                            "content": prompt
                        }
                    ],
                    temperature=self.TEMPERATURE,
                    max_tokens=self.MAX_TOKENS,
                    stream=False  # No streaming - we need complete JSON
                )
                
                # Extract response content
                if response.choices and len(response.choices) > 0:
                    content = response.choices[0].message.content
                    logger.debug(f"LLM response received: {len(content)} chars (attempt {attempt+1})")
                    return content
                else:
                    logger.warning("LLM returned empty response")
                    return None
                    
            except APITimeoutError as e:
                if attempt < max_retries:
                    wait_time = 0.5 * (2 ** attempt)  # Exponential backoff: 0.5s, 1s
                    logger.warning(f"⏱️ Groq timeout, retry {attempt+1}/{max_retries} after {wait_time}s")
                    import time
                    time.sleep(wait_time)
                else:
                    logger.warning(f"⏱️ Groq API timeout after {max_retries} retries")
                    return None
                
            except RateLimitError as e:
                if attempt < max_retries:
                    wait_time = 1.0 * (2 ** attempt)  # Exponential backoff: 1s, 2s
                    logger.warning(f"⚠️ Groq rate limit, retry {attempt+1}/{max_retries} after {wait_time}s")
                    import time
                    time.sleep(wait_time)
                else:
                    logger.warning("⚠️ Groq API rate limit exceeded after retries")
                    return None
                
            except APIError as e:
                logger.error(f"❌ Groq API error (permanent): {e}")
                return None  # Don't retry permanent errors
                
            except Exception as e:
                logger.error(f"❌ Unexpected error calling Groq: {e}")
                return None
        
        return None


# Singleton instance
_groq_client: Optional[GroqClient] = None


def get_groq_client() -> GroqClient:
    """Get or create singleton Groq client instance.
    
    Returns:
        Shared GroqClient instance
    """
    global _groq_client
    if _groq_client is None:
        _groq_client = GroqClient()
    return _groq_client
