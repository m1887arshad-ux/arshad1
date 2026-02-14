"""
CANONICAL PRODUCT RESOLUTION SERVICE

Purpose: Map user input text (any variant) to canonical product model
- Prevents raw user text from appearing in invoices
- Handles aliases, typos, and case variations
- Returns standardized product data with pricing

Architecture:
1. Normalize user input (lowercase, strip, remove fillers)
2. Search inventory by exact match, then fuzzy match
3. Return canonical product model or None
4. Track confidence score

Product Model:
{
    "product_id": int,           # Database ID
    "canonical_name": str,       # Official name for invoices
    "display_name": str,         # User-friendly name
    "price_per_unit": Decimal,   # Deterministic pricing
    "stock_quantity": Decimal,   # Current stock
    "requires_prescription": bool,
    "confidence": float          # 0.0 to 1.0
}
"""
import re
import logging
from typing import Optional, Dict, Any
from decimal import Decimal
from sqlalchemy.orm import Session
from sqlalchemy import func
from app.models.inventory import Inventory

logger = logging.getLogger(__name__)


# Common filler words to remove during normalization
NOISE_WORDS = {
    "hai", "kya", "ka", "ki", "ke", "chahiye", "dena", "dedo", "do", "lo", 
    "give", "please", "bhai", "sir", "ma'am", "order", "pack", "tablet", 
    "tablets", "strip", "strips", "bottle", "bottles", "?", "!"
}


def normalize_product_input(user_text: str) -> str:
    """
    Normalize user input for product matching
    
    Handles:
    - Case insensitivity
    - Extra whitespace
    - Filler words
    - Punctuation
    
    Examples:
        "Dolo 650 hai kya?" -> "dolo 650"
        "PARACETAMOL chahiye" -> "paracetamol"
        "dolo-650" -> "dolo 650"
    """
    if not user_text:
        return ""
    
    # Lowercase
    text = user_text.lower().strip()
    
    # Remove punctuation except digits and letters
    text = re.sub(r'[^\w\s]', ' ', text)
    
    # Split and remove noise words
    words = text.split()
    cleaned = [w for w in words if w not in NOISE_WORDS and len(w) > 0]
    
    return " ".join(cleaned)


def calculate_match_confidence(user_input: str, product_name: str) -> float:
    """
    Calculate confidence score for product match
    
    Returns: 0.0 to 1.0
    - 1.0 = exact match
    - 0.9+ = very close (contains or contained by)
    - 0.7+ = partial match (significant word overlap)
    - 0.5+ = weak match
    - <0.5 = poor match
    """
    user_norm = normalize_product_input(user_input)
    product_norm = normalize_product_input(product_name)
    
    if not user_norm or not product_norm:
        return 0.0
    
    # Exact match
    if user_norm == product_norm:
        return 1.0
    
    # One contains the other (e.g., "dolo" matches "dolo 650")
    if user_norm in product_norm:
        return 0.95
    if product_norm in user_norm:
        return 0.92
    
    # Word overlap
    user_words = set(user_norm.split())
    product_words = set(product_norm.split())
    
    if not user_words or not product_words:
        return 0.0
    
    intersection = user_words & product_words
    union = user_words | product_words
    
    # Jaccard similarity
    jaccard = len(intersection) / len(union) if union else 0.0
    
    # Boost if key medical terms match
    if intersection:
        return min(0.7 + (jaccard * 0.2), 0.95)
    
    return jaccard * 0.6  # Lower score for no word matches


def resolve_product(
    db: Session,
    business_id: int,
    user_input: str,
    min_confidence: float = 0.7
) -> Optional[Dict[str, Any]]:
    """
    Resolve user input to canonical product model
    
    Args:
        db: Database session
        business_id: Business ID to filter inventory
        user_input: Raw user text (e.g., "dolo", "paracetamol 500", "dolo 650 hai kya")
        min_confidence: Minimum confidence threshold (default 0.7)
    
    Returns:
        Canonical product model dict or None
        {
            "product_id": int,
            "canonical_name": str,
            "display_name": str,
            "price_per_unit": Decimal,
            "stock_quantity": Decimal,
            "requires_prescription": bool,
            "disease": str,
            "confidence": float
        }
    """
    if not user_input or not user_input.strip():
        logger.warning(f"[ProductResolver] Empty input for business_id={business_id}")
        return None
    
    normalized = normalize_product_input(user_input)
    
    if not normalized:
        logger.warning(f"[ProductResolver] Input normalized to empty: '{user_input}'")
        return None
    
    # Query all inventory items for this business
    items = db.query(Inventory).filter(
        Inventory.business_id == business_id
    ).all()
    
    if not items:
        logger.warning(f"[ProductResolver] No inventory for business_id={business_id}")
        return None
    
    # Find best match
    best_match = None
    best_confidence = 0.0
    second_best_match = None
    second_best_confidence = 0.0
    
    for item in items:
        confidence = calculate_match_confidence(user_input, item.item_name)
        
        if confidence > best_confidence:
            # Shift current best to second best
            second_best_match = best_match
            second_best_confidence = best_confidence
            # Set new best
            best_confidence = confidence
            best_match = item
        elif confidence > second_best_confidence:
            # Update second best
            second_best_confidence = confidence
            second_best_match = item
    
    # Check if confidence meets threshold
    if not best_match or best_confidence < min_confidence:
        logger.warning(
            f"[ProductResolver] No match above threshold {min_confidence} "
            f"for '{user_input}'. Best: {best_match.item_name if best_match else 'None'} "
            f"({best_confidence:.2f}), "
            f"Second: {second_best_match.item_name if second_best_match else 'None'} "
            f"({second_best_confidence:.2f})"
        )
        return None
    
    # AMBIGUITY DETECTION: If top 2 matches are too close, REJECT (prevent mismatch)
    # Example: If user says "Dolo" and both Dolo 650 and Paracetamol have 0.7+ confidence
    if second_best_match and (best_confidence - second_best_confidence) < 0.1:
        logger.warning(
            f"[ProductResolver] AMBIGUOUS MATCH for '{user_input}': "
            f"Top 2 scores too close! Best='{best_match.item_name}' ({best_confidence:.2f}) "
            f"vs Second='{second_best_match.item_name}' ({second_best_confidence:.2f}). "
            f"Rejecting to prevent mismatch."
        )
        return None
    
    logger.info(
        f"[ProductResolver] Matched '{user_input}' → '{best_match.item_name}' "
        f"(product_id={best_match.id}, confidence: {best_confidence:.2f})"
    )
    
    # CRITICAL: Validate product_id before returning
    if not best_match.id or not isinstance(best_match.id, int):
        logger.error(
            f"[ProductResolver] CRITICAL: Invalid product_id for '{best_match.item_name}'! "
            f"ID: {best_match.id}, Type: {type(best_match.id)}"
        )
        return None
    
    # Return canonical model with GUARANTEED product_id
    result = {
        "product_id": int(best_match.id),  # Force int
        "canonical_name": best_match.item_name,  # NEVER raw user input
        "display_name": best_match.item_name,
        "price_per_unit": Decimal(str(best_match.price)),
        "stock_quantity": Decimal(str(best_match.quantity)),
        "requires_prescription": best_match.requires_prescription,
        "disease": best_match.disease or "General use",
        "confidence": best_confidence
    }
    
    # Final validation
    assert result["product_id"] is not None, "product_id must not be None"
    assert result["product_id"] > 0, "product_id must be positive"
    
    return result


def resolve_multiple_products(
    db: Session,
    business_id: int,
    user_input: str,
    min_confidence: float = 0.5,
    max_results: int = 5
) -> list:
    """
    Resolve user input to multiple possible products (for disambiguation)
    
    Use case: When user asks "paracetamol hai?" and there are multiple brands
    
    Returns: List of product models sorted by confidence (highest first)
    """
    if not user_input or not user_input.strip():
        return []
    
    items = db.query(Inventory).filter(
        Inventory.business_id == business_id
    ).all()
    
    if not items:
        return []
    
    # Calculate confidence for all items
    matches = []
    for item in items:
        confidence = calculate_match_confidence(user_input, item.item_name)
        
        if confidence >= min_confidence:
            matches.append({
                "product_id": item.id,
                "canonical_name": item.item_name,
                "display_name": item.item_name,
                "price_per_unit": Decimal(str(item.price)),
                "stock_quantity": Decimal(str(item.quantity)),
                "requires_prescription": item.requires_prescription,
                "disease": item.disease or "General use",
                "confidence": confidence
            })
    
    # Sort by confidence descending
    matches.sort(key=lambda x: x["confidence"], reverse=True)
    
    return matches[:max_results]
