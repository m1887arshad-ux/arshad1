"""Intent Schema - Strict JSON structure for LLM output validation.

The LLM is FORCED to output ONLY this schema.
Any deviation triggers fallback logic.
"""

from enum import Enum
from typing import Optional
from pydantic import BaseModel, Field, field_validator


class IntentType(str, Enum):
    """Allowed intents - FIXED, cannot be extended by LLM."""
    CHECK_STOCK = "check_stock"
    CREATE_INVOICE = "create_invoice"
    GET_INVOICE = "get_invoice"
    APPROVE_INVOICE = "approve_invoice"
    UNKNOWN = "unknown"


class ConfidenceLevel(str, Enum):
    """Confidence in the parsed intent."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class ParsedIntent(BaseModel):
    """Validated output from LLM.
    
    This is the ONLY structure the LLM is allowed to return.
    Fields:
        intent: One of the predefined intent types
        product: Medicine/item name (null if not mentioned)
        quantity: Numeric quantity (null if not mentioned)
        customer: Customer name (null if not mentioned)
        confidence: LLM's confidence in this parse
    """
    intent: IntentType
    product: Optional[str] = None
    quantity: Optional[float] = None
    customer: Optional[str] = None
    confidence: ConfidenceLevel = ConfidenceLevel.MEDIUM

    @field_validator('product', 'customer')
    @classmethod
    def strip_strings(cls, v: Optional[str]) -> Optional[str]:
        """Clean whitespace from extracted strings."""
        return v.strip() if v else None

    @field_validator('quantity')
    @classmethod
    def validate_quantity(cls, v: Optional[float]) -> Optional[float]:
        """Ensure quantity is positive if present."""
        if v is not None and v <= 0:
            return None
        return v

    def to_dict(self):
        """Convert to dictionary for backend compatibility."""
        return {
            "intent": self.intent.value,
            "product": self.product,
            "quantity": self.quantity,
            "customer": self.customer,
            "confidence": self.confidence.value
        }

    def is_high_confidence(self) -> bool:
        """Check if parsing confidence is high enough."""
        return self.confidence == ConfidenceLevel.HIGH

    def is_actionable(self) -> bool:
        """Check if intent has enough info to proceed."""
        if self.intent == IntentType.UNKNOWN:
            return False
        if self.intent == IntentType.CHECK_STOCK and not self.product:
            return False
        if self.intent == IntentType.CREATE_INVOICE and not self.customer:
            return False
        return True
