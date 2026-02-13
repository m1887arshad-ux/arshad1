"""Intent Schema - Strict JSON structure for LLM output validation.

The LLM is FORCED to output ONLY this schema.
Any deviation triggers fallback logic.
"""

from enum import Enum
from typing import Optional
from pydantic import BaseModel, Field, field_validator, model_validator


class IntentType(str, Enum):
    """Allowed intents - FIXED, cannot be extended by LLM."""
    CHECK_STOCK = "check_stock"
    CREATE_INVOICE = "create_invoice"
    GET_INVOICE = "get_invoice"
    APPROVE_INVOICE = "approve_invoice"
    UNKNOWN = "unknown"


class ContentType(str, Enum):
    """High-level message classification."""
    BUSINESS_ACTION = "business_action"
    GREETING = "greeting"
    MEDICAL_QUERY = "medical_query"
    INFORMATIONAL = "informational"
    ABUSIVE = "abusive"
    UNKNOWN = "unknown"


class ConfidenceLevel(str, Enum):
    """Confidence in the parsed intent."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class Entities(BaseModel):
    """Structured entities extracted from the message."""
    product: Optional[str] = None
    quantity: Optional[float] = None
    customer: Optional[str] = None

    @field_validator("product", "customer")
    @classmethod
    def strip_strings(cls, v: Optional[str]) -> Optional[str]:
        """Clean whitespace from extracted strings.
        
        Validation rules:
        - Returns None if not provided
        - Returns None if empty after strip
        - Returns None if less than 2 characters (too short to be real name/product)
        - Returns None if more than 100 characters (unrealistic)
        """
        if not v:
            return None
        v_stripped = v.strip()
        # Reject empty strings or names that are too short/long
        if len(v_stripped) < 2 or len(v_stripped) > 100:
            return None
        return v_stripped

    @field_validator("quantity")
    @classmethod
    def validate_quantity(cls, v: Optional[float]) -> Optional[float]:
        """Ensure quantity is positive and realistic.
        
        Validation rules:
        - Returns None if not provided
        - Returns None if zero or negative
        - Returns None if greater than 100,000 (clearly unrealistic order)
        - Returns None if non-integer when represented (fractional tablets don't make sense)
        """
        if v is not None:
            # Reject zero or negative
            if v <= 0:
                return None
            # Reject unrealistic quantities
            if v > 100000:
                return None
            # Reject fractional quantities (e.g., 3.7 tablets)
            # Allow only integers for pharmacy context
            if v != int(v):
                return None
        return v


class ParsedIntent(BaseModel):
    """Validated output from LLM.

    This is the ONLY structure the LLM is allowed to return.
    Fields:
        normalized_text: Clean English interpretation
        content_type: High-level content classification
        intent: Business intent (null if not a business_action)
        entities: Structured entities (product, quantity, customer)
        confidence: LLM's confidence in this parse
    """
    normalized_text: str = ""
    content_type: ContentType = ContentType.UNKNOWN
    intent: Optional[IntentType] = None
    entities: Entities = Field(default_factory=Entities)
    confidence: ConfidenceLevel = ConfidenceLevel.MEDIUM

    @model_validator(mode="after")
    def align_intent_with_content(self):
        """If not a business_action, force intent to None."""
        if self.content_type != ContentType.BUSINESS_ACTION:
            self.intent = None
        return self

    def to_dict(self):
        """Convert to dictionary for backend compatibility."""
        intent_value = self.intent.value if self.intent else IntentType.UNKNOWN.value
        if self.content_type != ContentType.BUSINESS_ACTION:
            intent_value = IntentType.UNKNOWN.value

        return {
            "normalized_text": self.normalized_text,
            "content_type": self.content_type.value,
            "intent": intent_value,
            "product": self.entities.product,
            "quantity": self.entities.quantity,
            "customer": self.entities.customer,
            "confidence": self.confidence.value
        }

    def is_high_confidence(self) -> bool:
        """Check if parsing confidence is high enough."""
        return self.confidence == ConfidenceLevel.HIGH

    def is_actionable(self) -> bool:
        """Check if intent has enough info to proceed."""
        if not self.intent or self.intent == IntentType.UNKNOWN:
            return False
        if self.intent == IntentType.CHECK_STOCK and not self.entities.product:
            return False
        if self.intent == IntentType.CREATE_INVOICE and not self.entities.customer:
            return False
        return True
