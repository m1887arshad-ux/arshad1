import re
import logging
from typing import Optional

from .intent_schema import IntentType, ConfidenceLevel

logger = logging.getLogger(__name__)

STOCK_KEYWORDS = [
    r'\b(stock|available|hai kya|milega|mil jayega)\b',
    r'\b(kya .+ (stock|available|hai))\b',
]

INVOICE_KEYWORDS = [
    r'\b(bill|invoice|bana|create|order)\b',
    r'\b(ka bill|ko bill)\b',
]

APPROVE_KEYWORDS = [
    r'\b(approve|yes|haan|theek|ok|confirm)\b',
]

def parse_message_fallback(message: str) -> dict:
    message_lower = message.lower().strip()
    
    logger.debug(f"Fallback parsing: {message[:50]}...")
    
    # Try to detect intent from keywords
    intent = _detect_intent_keyword(message_lower)
    
    # Extract entities based on intent
    product = None
    quantity = None
    customer = None
    confidence = ConfidenceLevel.MEDIUM
    
    if intent == IntentType.CHECK_STOCK:
        product = _extract_product_name(message)
        confidence = ConfidenceLevel.HIGH if product else ConfidenceLevel.MEDIUM
        
    elif intent == IntentType.CREATE_INVOICE:
        customer = _extract_customer_name(message)
        quantity = _extract_amount(message)
        confidence = ConfidenceLevel.HIGH if customer else ConfidenceLevel.MEDIUM
        
    elif intent == IntentType.APPROVE_INVOICE:
        confidence = ConfidenceLevel.HIGH
    
    # If business intent found, mark as business_action
    # Otherwise default to unknown (LLM will refine classification)
    content_type = "business_action" if intent != IntentType.UNKNOWN else "unknown"
    
    result = {
        "normalized_text": message,
        "content_type": content_type,
        "intent": intent.value,
        "product": product,
        "quantity": quantity,
        "customer": customer,
        "confidence": confidence.value,
        "source": "fallback"  # Audit: came from keyword fallback, not LLM
    }
    
    logger.info(f"🔄 Fallback parsed: intent={result['intent']}")
    return result


def _detect_intent_keyword(message: str) -> IntentType:
    """Detect intent from keyword patterns.
    
    Args:
        message: Lowercase message text
        
    Returns:
        Detected IntentType
    """
    # Check for stock queries
    for pattern in STOCK_KEYWORDS:
        if re.search(pattern, message, re.IGNORECASE):
            return IntentType.CHECK_STOCK
    
    # Check for approve keywords
    for pattern in APPROVE_KEYWORDS:
        if re.search(pattern, message, re.IGNORECASE):
            return IntentType.APPROVE_INVOICE
    
    # Check for invoice creation
    for pattern in INVOICE_KEYWORDS:
        if re.search(pattern, message, re.IGNORECASE):
            return IntentType.CREATE_INVOICE
    
    # Default to unknown
    return IntentType.UNKNOWN


def _extract_product_name(message: str) -> Optional[str]:
    """Extract product/medicine name from message.
    
    Uses simple heuristics:
    - First capitalized word(s)
    - Word after "kya" or before "stock"
    
    Args:
        message: Original message text
        
    Returns:
        Extracted product name or None
    """
    # Pattern: "kya X stock mein hai"
    match = re.search(r'kya\s+(\w+(?:\s+\w+)?)\s+(?:stock|available)', message, re.IGNORECASE)
    if match:
        return match.group(1).strip()
    
    # Pattern: "X available hai kya"
    match = re.search(r'(\w+(?:\s+\w+)?)\s+(?:available|stock)', message, re.IGNORECASE)
    if match:
        return match.group(1).strip()
    
    # Look for capitalized words (might be medicine names)
    words = message.split()
    for word in words:
        if word and word[0].isupper() and len(word) > 2:
            return word
    
    return None


def _extract_customer_name(message: str) -> Optional[str]:
    """Extract customer name from message.
    
    Pattern: "X ko bill" or "X ka bill"
    
    Args:
        message: Original message text
        
    Returns:
        Extracted customer name or None
    """
    # Pattern: "Name ko/ka bill"
    match = re.search(r'(\w+)\s+(ko|ka)\s+(?:bill|invoice)', message, re.IGNORECASE)
    if match:
        return match.group(1).strip()
    
    # Look for capitalized words (might be customer names)
    words = message.split()
    for word in words:
        if word and word[0].isupper() and len(word) > 2:
            # Skip common keywords
            if word.lower() not in ['stock', 'bill', 'invoice', 'order']:
                return word
    
    return None


def _extract_amount(message: str) -> Optional[float]:
    """Extract numeric amount from message.
    
    Pattern: Numbers followed by "ka" or "rupees"
    
    Args:
        message: Original message text
        
    Returns:
        Extracted amount or None
    """
    # Pattern: "500 ka bill" or "500 rupees"
    match = re.search(r'(\d+(?:\.\d+)?)\s*(?:ka|rupees|rs|/-)?', message, re.IGNORECASE)
    if match:
        try:
            return float(match.group(1))
        except ValueError:
            pass
    
    return None
