"""
ENTITY EXTRACTOR WITH CONFIDENCE SCORING

Purpose: Extract entities (product, quantity, customer) with confidence scores
- Enables intelligent question skipping
- Reduces redundant questions
- Maintains conversation context

Confidence Levels:
- high (0.8+): Auto-fill, skip question
- medium (0.5-0.8): Confirm with user
- low (<0.5): Must ask

Entity Model:
{
    "product": {
        "value": str,
        "confidence": float,
        "source": "deterministic" | "llm" | "context"
    },
    "quantity": {
        "value": float,
        "confidence": float,
        "source": str
    },
    "customer": {
        "value": str,
        "confidence": float,
        "source": str
    }
}
"""
import re
import logging
from typing import Optional, Dict, Any
from decimal import Decimal

logger = logging.getLogger(__name__)


# Hindi/English number mappings
NUMBER_WORDS = {
    # English
    "one": 1, "two": 2, "three": 3, "four": 4, "five": 5,
    "six": 6, "seven": 7, "eight": 8, "nine": 9, "ten": 10,
    "eleven": 11, "twelve": 12, "fifteen": 15, "twenty": 20,
    "thirty": 30, "forty": 40, "fifty": 50, "hundred": 100,
    
    # Hindi/Hinglish
    "ek": 1, "do": 2, "teen": 3, "char": 4, "paanch": 5, "panch": 5,
    "chhe": 6, "saat": 7, "aath": 8, "aat": 8, "nau": 9, "das": 10,
    "gyarah": 11, "barah": 12, "pandrah": 15, "bees": 20,
    "tees": 30, "chalis": 40, "pachas": 50, "sau": 100,
    
    # Common phrases
    "only one": 1, "sirf ek": 1, "bas ek": 1,
    "half dozen": 6, "dozen": 12, "derzen": 12
}

# Self-reference keywords (for customer extraction)
SELF_REFERENCES = {
    "mujhe", "mere liye", "mera", "apne liye", "khud", 
    "myself", "me", "for me", "mere"
}


def extract_quantity_with_confidence(
    text: str,
    context: Optional[Dict] = None
) -> Dict[str, Any]:
    """
    Extract quantity from text with confidence score
    
    Returns:
    {
        "value": float or None,
        "confidence": float (0.0 to 1.0),
        "source": "numeric" | "word" | "context" | None
    }
    """
    if not text:
        return {"value": None, "confidence": 0.0, "source": None}
    
    text_lower = text.lower().strip()
    
    # Try numeric extraction (highest confidence)
    numeric_match = re.search(r'\b(\d+(?:\.\d+)?)\b', text_lower)
    if numeric_match:
        try:
            value = float(numeric_match.group(1))
            
            # Sanity check
            if value <= 0:
                logger.warning(f"[QuantityExtractor] Invalid quantity: {value}")
                return {"value": None, "confidence": 0.0, "source": None}
            
            if value > 10000:
                logger.warning(f"[QuantityExtractor] Suspiciously high quantity: {value}")
                return {"value": value, "confidence": 0.5, "source": "numeric"}
            
            return {
                "value": value,
                "confidence": 0.95,  # High confidence for numeric
                "source": "numeric"
            }
        except ValueError:
            pass
    
    # Try word-based extraction (medium confidence)
    # Use word boundaries to prevent false matches (e.g., "done" shouldn't match "one")
    for word, num in NUMBER_WORDS.items():
        # Check if word appears as a complete word, not substring
        pattern = r'\b' + re.escape(word) + r'\b'
        if re.search(pattern, text_lower):
            return {
                "value": float(num),
                "confidence": 0.85,  # Medium-high confidence for words
                "source": "word"
            }
    
    # Try context (low confidence)
    if context and context.get("last_quantity"):
        return {
            "value": float(context["last_quantity"]),
            "confidence": 0.4,  # Low confidence from context
            "source": "context"
        }
    
    return {"value": None, "confidence": 0.0, "source": None}


def extract_customer_with_confidence(
    text: str,
    context: Optional[Dict] = None,
    default_owner_name: str = "Owner"
) -> Dict[str, Any]:
    """
    Extract customer name from text with confidence score
    
    Returns:
    {
        "value": str or None,
        "confidence": float (0.0 to 1.0),
        "source": "self" | "name" | "pattern" | "context" | "default"
    }
    """
    if not text:
        # Return None when no text provided
        return {
            "value": None,
            "confidence": 0.0,
            "source": "none"
        }
    
    text_lower = text.lower().strip()
    
    # Check for self-references (high confidence)
    # Use word boundaries to avoid false matches
    for self_ref in SELF_REFERENCES:
        pattern = r'\b' + re.escape(self_ref) + r'\b'
        if re.search(pattern, text_lower):
            return {
                "value": default_owner_name,
                "confidence": 0.9,
                "source": "self"
            }
    
    # Check for "X ko" pattern (medium-high confidence)
    ko_match = re.search(r'(\w+)\s+ko\b', text, re.IGNORECASE)
    if ko_match:
        name = ko_match.group(1).capitalize()
        return {
            "value": name,
            "confidence": 0.85,
            "source": "pattern"
        }
    
    # Check for "for X" pattern
    for_match = re.search(r'for\s+(\w+)', text, re.IGNORECASE)
    if for_match:
        name = for_match.group(1).capitalize()
        return {
            "value": name,
            "confidence": 0.8,
            "source": "pattern"
        }
    
    # Check if text is just a name (single/double word, capitalized)
    words = text.strip().split()
    if len(words) > 0 and len(words) <= 2:
        # Check if it looks like a name (starts with capital)
        if len(words[0]) > 0 and words[0][0].isupper():
            name = " ".join(words)
            return {
                "value": name,
                "confidence": 0.7,
                "source": "name"
            }
    
    # Check context (low confidence)
    if context and context.get("last_customer"):
        return {
            "value": context["last_customer"],
            "confidence": 0.4,
            "source": "context"
        }
    
    # No customer found - return None
    return {
        "value": None,
        "confidence": 0.0,
        "source": "none"
    }


def extract_product_with_confidence(
    text: str,
    context: Optional[Dict] = None
) -> Dict[str, Any]:
    """
    Extract product name from text with confidence score
    
    Note: This returns RAW user input. Must be resolved to canonical
    product via product_resolver.resolve_product()
    
    Returns:
    {
        "value": str or None,  # Raw user input
        "confidence": float (0.0 to 1.0),
        "source": "extraction" | "context" | None
    }
    """
    if not text:
        return {"value": None, "confidence": 0.0, "source": None}
    
    text_stripped = text.strip()
    
    # Remove common filler words
    noise_words = {
        "hai", "kya", "ka", "ki", "ke", "chahiye", "dedo", "dena", "do", 
        "lo", "order", "give", "please", "bhai", "available", "stock",
        "check", "milega", "?", "!"
    }
    
    words = text_stripped.split()
    cleaned_words = [w for w in words if w.lower() not in noise_words]
    
    # If we have cleaned words, extract product
    if cleaned_words:
        # Prefer capitalized words or words with digits (medicine names)
        medicine_like = [
            w for w in cleaned_words 
            if len(w) > 2 and (w[0].isupper() or any(c.isdigit() for c in w))
        ]
        
        if medicine_like:
            product = " ".join(medicine_like)
            return {
                "value": product,
                "confidence": 0.8,  # Medium-high confidence
                "source": "extraction"
            }
        
        # Otherwise use first few meaningful words (but filter out very short words)
        if len(cleaned_words) <= 3:
            # Filter out single-char and two-char words that are likely not products
            substantial_words = [w for w in cleaned_words if len(w) > 2]
            if substantial_words:
                product = " ".join(substantial_words)
                return {
                    "value": product,
                    "confidence": 0.6,  # Medium confidence
                    "source": "extraction"
                }
            # If all words are too short, use them anyway but with lower confidence
            elif cleaned_words:
                product = " ".join(cleaned_words)
                return {
                    "value": product,
                    "confidence": 0.4,  # Low confidence - suspicious input
                    "source": "extraction"
                }
    
    # Try context (low confidence)
    if context and context.get("last_product"):
        return {
            "value": context["last_product"],
            "confidence": 0.4,
            "source": "context"
        }
    
    return {"value": None, "confidence": 0.0, "source": None}


def extract_all_entities(
    text: str,
    context: Optional[Dict] = None,
    default_owner_name: str = "Owner"
) -> Dict[str, Dict[str, Any]]:
    """
    Extract all entities (product, quantity, customer) from text
    
    Returns:
    {
        "product": {"value": str, "confidence": float, "source": str},
        "quantity": {"value": float, "confidence": float, "source": str},
        "customer": {"value": str, "confidence": float, "source": str}
    }
    """
    return {
        "product": extract_product_with_confidence(text, context),
        "quantity": extract_quantity_with_confidence(text, context),
        "customer": extract_customer_with_confidence(text, context, default_owner_name)
    }


def should_skip_question(entity_confidence: float, threshold: float = 0.8) -> bool:
    """
    Decide if we should skip asking for this entity
    
    Args:
        entity_confidence: Confidence score (0.0 to 1.0)
        threshold: Threshold for auto-skip (default 0.8)
    
    Returns:
        True if confidence is high enough to skip question
    """
    return entity_confidence >= threshold
