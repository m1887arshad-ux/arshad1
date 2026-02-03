"""LLM-based Intent Parser - Primary parsing logic with validation.

Flow:
1. Receive user message
2. Build prompt with system instructions
3. Call Groq LLM
4. Parse and validate JSON response
5. Return structured intent or trigger fallback
"""

import json
import logging
from typing import Optional

from .groq_client import get_groq_client
from .prompts import build_prompt
from .intent_schema import ParsedIntent, IntentType
from .fallback import parse_message_fallback

logger = logging.getLogger(__name__)


def parse_message_with_ai(message: str, context: dict = None) -> dict:
    """Parse user message using Groq LLM with strict validation.
    
    This is the PRIMARY parsing function. It:
    1. Uses LLM for intelligent understanding with conversation context
    2. Validates output against strict schema
    3. Falls back to keyword matching on any failure
    
    Args:
        message: Raw user message (Hinglish/Hindi/English)
        context: Optional conversation context (last_product, last_customer, etc.)
        
    Returns:
        Dictionary with parsed intent and entities:
        {
            "intent": str,
            "product": str | None,
            "quantity": float | None,
            "customer": str | None,
            "confidence": str,
            "source": "llm" | "fallback"
        }
    """
    # Sanitize input
    message = message.strip()
    if not message:
        logger.debug("Empty message - returning unknown intent")
        return _unknown_intent("fallback")
    
    # Try LLM parsing first
    groq_client = get_groq_client()
    
    if not groq_client.is_available():
        logger.debug("LLM not available - using fallback")
        return parse_message_fallback(message)
    
    try:
        # Build prompt with context and call LLM
        prompt = build_prompt(message, context=context)
        logger.debug(f"Calling LLM for message: {message[:50]}... (context: {bool(context)})")
        
        llm_response = groq_client.extract_intent(prompt)
        
        if not llm_response:
            logger.debug("LLM returned None - using fallback")
            return parse_message_fallback(message)
        
        # Parse and validate JSON
        parsed_intent = _parse_and_validate_json(llm_response)
        
        if parsed_intent is None:
            logger.debug("LLM output invalid - using fallback")
            return parse_message_fallback(message)
        
        # Success - return validated LLM output
        result = parsed_intent.to_dict()
        result["source"] = "llm"
        logger.info(f"✅ LLM parsed: intent={result['intent']}, confidence={result['confidence']}")
        return result
        
    except Exception as e:
        logger.error(f"❌ Error in LLM parsing: {e}")
        return parse_message_fallback(message)


def _parse_and_validate_json(llm_response: str) -> Optional[ParsedIntent]:
    """Extract and validate JSON from LLM response.
    
    The LLM sometimes wraps JSON in markdown or adds explanation.
    This function:
    1. Extracts JSON object from response
    2. Validates against Pydantic schema
    3. Returns None if invalid
    
    Args:
        llm_response: Raw response string from LLM
        
    Returns:
        Validated ParsedIntent or None
    """
    try:
        # Try to extract JSON from response
        # Handle cases like: ```json\n{...}\n``` or just {...}
        response_clean = llm_response.strip()
        
        # Remove markdown code blocks if present
        if response_clean.startswith("```"):
            lines = response_clean.split("\n")
            # Remove first line (```json or ```)
            if lines[0].strip().startswith("```"):
                lines = lines[1:]
            # Remove last line (```)
            if lines and lines[-1].strip() == "```":
                lines = lines[:-1]
            response_clean = "\n".join(lines).strip()
        
        # Parse JSON
        data = json.loads(response_clean)
        
        # Validate against schema
        parsed = ParsedIntent(**data)
        
        return parsed
        
    except json.JSONDecodeError as e:
        logger.warning(f"Invalid JSON from LLM: {e}")
        return None
        
    except Exception as e:
        logger.warning(f"Schema validation failed: {e}")
        return None


def _unknown_intent(source: str = "fallback") -> dict:
    """Generate unknown intent response.
    
    Args:
        source: "llm" or "fallback"
        
    Returns:
        Unknown intent dictionary
    """
    return {
        "intent": IntentType.UNKNOWN.value,
        "product": None,
        "quantity": None,
        "customer": None,
        "confidence": "low",
        "source": source
    }
