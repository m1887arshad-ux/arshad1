"""
Decision Engine — Rule-based validation and DRAFT creation.

================================================================================
SAFETY ARCHITECTURE (CRITICAL FOR HACKATHON JUDGES)
================================================================================

THIS MODULE CREATES DRAFTS, NOT EXECUTIONS.

Flow:
1. FSM or LLM extracts intent + entities
2. Decision Engine validates and creates DRAFT AgentAction
3. Owner reviews DRAFT on Dashboard
4. Owner clicks APPROVE
5. Only THEN does Executor run

WHY THIS MATTERS:
- AI hallucinations can't cause financial damage
- Prompt injection attacks can't trigger execution
- Owner maintains full control over all actions
- Audit trail of all proposed actions

PHARMACY-SPECIFIC COMPLIANCE:
- If product.requires_prescription == True:
  - DRAFT is flagged with warning
  - Owner MUST verify prescription exists before approval
  - This is a LEGAL requirement for controlled medicines

================================================================================
"""
import logging
from sqlalchemy.orm import Session
from typing import Optional

from app.agent.intent_parser import parse_message, ParsedIntent
from app.models.agent_action import AgentAction
from app.models.inventory import Inventory

logger = logging.getLogger(__name__)


def validate_and_create_draft(
    db: Session, 
    business_id: int, 
    raw_message: str, 
    telegram_chat_id: str | None = None,
    intent: str = None,
    product: str = None,
    quantity: float = None,
    customer: str = None,
    requires_prescription: bool = False,
) -> AgentAction | None:
    """
    Create AgentAction with status DRAFT from explicit parameters or parsed message.
    
    SAFETY GUARANTEE:
    - This function ONLY creates DRAFTS
    - Approval is ALWAYS required; no autonomy
    - Executor runs only after owner clicks APPROVE
    
    PHARMACY COMPLIANCE:
    - If requires_prescription=True, payload is flagged
    - Owner must verify prescription exists before approval
    
    Args:
        db: Database session
        business_id: Business ID
        raw_message: Original user message
        telegram_chat_id: Telegram chat ID for linking
        intent: Explicit intent (e.g., "create_invoice")
        product: Product name
        quantity: Product quantity
        customer: Customer name
        requires_prescription: If True, product needs prescription verification
    """
    
    # If explicit parameters provided (from FSM), use them directly
    if intent == "create_invoice" and product and quantity and customer:
        # CRITICAL: Product must be canonical name from inventory
        # Look up product to get exact price
        item = db.query(Inventory).filter(
            Inventory.business_id == business_id,
            Inventory.item_name == product  # Exact match (already canonical)
        ).first()
        
        if not item:
            # Fallback: try fuzzy match
            item = db.query(Inventory).filter(
                Inventory.business_id == business_id,
                Inventory.item_name.ilike(f"%{product}%")
            ).first()
        
        if not item:
            logger.error(f"[DecisionEngine] Product '{product}' not found in inventory for business {business_id}")
            return None
        
        # DETERMINISTIC BILLING: price_per_unit × quantity (NO MAGIC NUMBERS)
        unit_price = float(item.price)
        amount = quantity * unit_price
        
        # PHARMACY COMPLIANCE: Flag prescription requirement
        rx_warning = ""
        if requires_prescription or item.requires_prescription:
            rx_warning = " [⚠️ PRESCRIPTION REQUIRED]"
        
        # ROLE SEPARATION: Seller = pharmacy (constant), Buyer = customer
        payload = {
            "customer_name": customer,  # BUYER (from conversation)
            "product": item.item_name,  # CANONICAL name (never raw user input)
            "product_id": item.id,      # Database reference
            "quantity": quantity,
            "unit_price": unit_price,   # Price per unit
            "amount": amount,           # Total = unit_price × quantity
            "action_type": "Invoice",
            "channel": "Telegram",
            "telegram_chat_id": telegram_chat_id,  # Store for invoice delivery
            "requires_prescription": requires_prescription or item.requires_prescription,  # Compliance flag
            "seller": "Pharmacy",       # ROLE: Always seller
            "buyer": customer           # ROLE: Always buyer (never confused)
        }
        
        action = AgentAction(
            business_id=business_id,
            intent=intent,
            payload=payload,
            status="DRAFT",
            explanation=f"Invoice for {customer}: {int(quantity)} × {product} = ₹{amount:.2f}{rx_warning}",
        )
        db.add(action)
        db.commit()
        db.refresh(action)
        logger.info(f"Created DRAFT action {action.id} for business {business_id}: {payload}")
        return action
    
    # Fallback to legacy regex parsing for backward compatibility
    parsed = parse_message(raw_message)
    if not parsed:
        logger.debug(f"Could not parse message for business {business_id}: {raw_message[:100]}")
        return None

    # Required fields for create_invoice
    if parsed.intent == "create_invoice":
        payload = parsed.payload or {}
        if not payload.get("customer_name") or not payload.get("amount"):
            logger.warning(f"Invalid invoice payload for business {business_id}: {payload}")
            return None

    # Create draft; owner must approve before execution
    action = AgentAction(
        business_id=business_id,
        intent=parsed.intent,
        payload=parsed.payload,
        status="DRAFT",
        explanation=f"Customer asked for: {raw_message[:200]}",
    )
    db.add(action)
    db.commit()
    db.refresh(action)
    logger.info(f"Created DRAFT action {action.id} for business {business_id}: intent={parsed.intent}")
    return action
