"""
Intent Parser - Deterministic First, LLM Fallback

Architecture:
1. Check meta intents (cancel, help)
2. Check query intents (stock, symptom) → These reset order flow
3. Check transaction intents (only if in ordering mode)
4. Fallback to LLM for ambiguous cases

Returns:
{
    "intent": str,
    "confidence": "high" | "medium" | "low",
    "entities": dict,
    "should_reset_flow": bool
}
"""
import re
import logging
from typing import Dict, Optional
from .conversation_state import (
    IntentType, 
    ConversationMode,
    QUERY_KEYWORDS,
    TRANSACTION_KEYWORDS
)

logger = logging.getLogger(__name__)


def parse_intent_deterministic(
    text: str, 
    current_mode: str, 
    context: dict
) -> dict:
    """Deterministic intent parsing with keyword matching"""
    text_lower = text.lower().strip()
    
    # === LAYER 1: META INTENTS (Always Highest Priority) ===
    if any(kw in text_lower for kw in QUERY_KEYWORDS["cancel"]):
        return {
            "intent": IntentType.CANCEL,
            "confidence": "high",
            "entities": {},
            "should_reset_flow": True
        }
    
    if any(kw in text_lower for kw in QUERY_KEYWORDS["help"]):
        return {
            "intent": IntentType.HELP,
            "confidence": "high",
            "entities": {},
            "should_reset_flow": False
        }
    
    # === LAYER 2: QUERY INTENTS (Reset Flow if Ordering) ===
    # Stock check
    if any(kw in text_lower for kw in QUERY_KEYWORDS["stock"]):
        product = extract_product_name(text_lower, text)
        should_reset = (current_mode == ConversationMode.ORDERING)
        return {
            "intent": IntentType.ASK_STOCK,
            "confidence": "high" if product else "medium",
            "entities": {"product": product},
            "should_reset_flow": should_reset
        }
    
    # Symptom queries
    if any(kw in text_lower for kw in QUERY_KEYWORDS["symptom"]):
        symptom = extract_symptom(text_lower)
        return {
            "intent": IntentType.ASK_SYMPTOM,
            "confidence": "high",
            "entities": {"symptom": symptom},
            "should_reset_flow": True  # Always reset for questions
        }
    
    # Price queries
    if any(kw in text_lower for kw in QUERY_KEYWORDS["price"]):
        product = extract_product_name(text_lower, text)
        return {
            "intent": IntentType.ASK_PRICE,
            "confidence": "medium",
            "entities": {"product": product},
            "should_reset_flow": True
        }
    
    # === LAYER 3: TRANSACTION INTENTS ===
    # Confirmation
    if any(kw in text_lower for kw in TRANSACTION_KEYWORDS["confirm"]):
        return {
            "intent": IntentType.CONFIRM_ORDER,
            "confidence": "high",
            "entities": {},
            "should_reset_flow": False
        }
    
    # Check for quantity (numeric patterns)
    # *** FIX: Accept quantity in STOCK_CONFIRMED or ORDERING mode ***
    quantity = extract_quantity(text_lower)
    if quantity and current_mode in [ConversationMode.ORDERING, ConversationMode.STOCK_CONFIRMED]:
        return {
            "intent": IntentType.PROVIDE_QUANTITY,
            "confidence": "high",
            "entities": {"quantity": quantity},
            "should_reset_flow": False
        }
    
    # Check for product + quantity pattern (e.g., "10 Dolo")
    product, qty = extract_product_and_quantity(text)
    if product and qty:
        return {
            "intent": IntentType.START_ORDER,
            "confidence": "high",
            "entities": {"product": product, "quantity": qty},
            "should_reset_flow": False
        }
    
    # Check for customer name (only if we have product + quantity)
    if current_mode == ConversationMode.ORDERING:
        if context.get("product") and context.get("quantity"):
            customer = extract_customer_name(text)
            if customer:
                return {
                    "intent": IntentType.PROVIDE_CUSTOMER,
                    "confidence": "medium",
                    "entities": {"customer": customer},
                    "should_reset_flow": False
                }
    
    # Check for order keywords
    if any(kw in text_lower for kw in TRANSACTION_KEYWORDS["order"]):
        product = extract_product_name(text_lower, text)
        return {
            "intent": IntentType.START_ORDER,
            "confidence": "medium",
            "entities": {"product": product},
            "should_reset_flow": False
        }
    
    # === FALLBACK ===
    return {
        "intent": IntentType.UNKNOWN,
        "confidence": "low",
        "entities": {},
        "should_reset_flow": False
    }


def extract_product_name(text_lower: str, original_text: str) -> Optional[str]:
    """Extract product name from text"""
    # Remove common keywords
    noise_words = ["hai", "kya", "available", "check", "stock", "milega", 
                   "chahiye", "de", "do", "bhai", "please", "?", "kitne", "ka"]
    
    words = original_text.split()
    cleaned_words = [w for w in words if w.lower() not in noise_words]
    
    if cleaned_words:
        # Try to find medicine-like words (capitalized or known patterns)
        for word in cleaned_words:
            if len(word) > 2 and (word[0].isupper() or any(char.isdigit() for char in word)):
                return word
        
        # Return first meaningful word
        return cleaned_words[0] if cleaned_words else None
    
    return None


def extract_symptom(text_lower: str) -> str:
    """Extract symptom from text"""
    for kw in QUERY_KEYWORDS["symptom"]:
        if kw in text_lower:
            return kw
    
    # Safety check: ensure split() returns non-empty list
    words = text_lower.split()
    return words[0] if words else text_lower  # First word as symptom, fallback to full text


def extract_quantity(text_lower: str) -> Optional[float]:
    """Extract quantity from text"""
    # Hindi/English number words
    number_map = {
        "ek": 1, "one": 1, "only one": 1,
        "do": 2, "two": 2,
        "teen": 3, "three": 3,
        "char": 4, "four": 4,
        "paanch": 5, "panch": 5, "five": 5,
        "das": 10, "ten": 10,
        "bees": 20, "twenty": 20,
        "pachas": 50, "fifty": 50,
    }
    
    # Use word boundaries to prevent false matches
    for word, num in number_map.items():
        pattern = r'\b' + re.escape(word) + r'\b'
        if re.search(pattern, text_lower):
            return float(num)
    
    # Extract numeric value
    match = re.search(r'(\d+(?:\.\d+)?)', text_lower)
    if match:
        return float(match.group(1))
    
    return None


def extract_product_and_quantity(text: str) -> tuple:
    """Extract both product and quantity from patterns like '10 Dolo'"""
    # Pattern: number + product name
    match = re.match(r'(\d+)\s+([A-Za-z0-9]+)', text.strip())
    if match:
        qty = float(match.group(1))
        product = match.group(2)
        return (product, qty)
    
    return (None, None)


def extract_customer_name(text: str) -> Optional[str]:
    """Extract customer name (simple heuristic)"""
    # If text is short and starts with capital, likely a name
    words = text.strip().split()
    if len(words) > 0 and len(words) <= 2 and len(words[0]) > 0 and words[0][0].isupper():
        return text.strip()
    
    # Check for "mujhe" (me)
    if "mujhe" in text.lower() or "mere" in text.lower():
        return "Self"
    
    return None
