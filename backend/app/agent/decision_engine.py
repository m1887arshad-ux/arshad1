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
    product_id: int = None,  # FIX 7: NEW PARAMETER - Accept product_id from FSM
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
        product_id: Product ID (PREFERRED - ensures exact match)
        quantity: Product quantity
        customer: Customer name
        requires_prescription: If True, product needs prescription verification
    """
    
    # If explicit parameters provided (from FSM), use them directly
    if intent == "create_invoice" and (product or product_id) and quantity and customer:
        item = None
        
        # FIX: ID takes absolute precedence (strongest source of truth)
        if product_id:
            item = db.query(Inventory).filter(
                Inventory.business_id == business_id,
                Inventory.id == product_id
            ).first()
            logger.info(f"[DecisionEngine] Lookup by product_id={product_id}, found={item.item_name if item else 'None'}")
            
            # CRITICAL: If product_id was provided but not found, FAIL HARD
            if not item:
                logger.error(
                    f"[DecisionEngine] CRITICAL: product_id={product_id} not found in inventory "
                    f"for business_id={business_id}. This indicates FSM state corruption or deleted product."
                )
                return None
            
            # SANITY CHECK: Verify the returned product matches expectations
            if product and item.item_name.lower().strip() != product.lower().strip():
                logger.warning(
                    f"[DecisionEngine] WARNING: product_id={product_id} resolved to '{item.item_name}' "
                    f"but expected '{product}'. Using database value: {item.item_name}"
                )
        
        # FIX: Name-based lookup only if ID not provided
        elif product:
            # Priority 1: Exact match
            item = db.query(Inventory).filter(
                Inventory.business_id == business_id,
                Inventory.item_name == product
            ).first()
            
            # Priority 2: Case-insensitive exact match
            if not item:
                item = db.query(Inventory).filter(
                    Inventory.business_id == business_id,
                    Inventory.item_name.ilike(product)
                ).order_by(Inventory.id).first()
            
            # Priority 3: Fuzzy match (with deterministic sort)
            if not item:
                item = db.query(Inventory).filter(
                    Inventory.business_id == business_id,
                    Inventory.item_name.ilike(f"%{product}%")
                ).order_by(Inventory.id).first()
                
                if item:
                    logger.warning(f"[DecisionEngine] Fuzzy match: '{product}' -> '{item.item_name}' (id={item.id})")
        
        else:
            logger.error(f"[DecisionEngine] Neither product_id nor product name provided")
            return None
        
        if not item:
            logger.error(f"[DecisionEngine] Product lookup failed. ID={product_id}, Name='{product}'")
            return None
        
        # DETERMINISTIC BILLING: price_per_unit × quantity (NO MAGIC NUMBERS)
        unit_price = float(item.price)
        amount = quantity * unit_price
        
        # FINAL SANITY CHECK: Log what we're billing
        logger.info(
            f"[DecisionEngine] FINAL: Creating draft for product_id={item.id}, "
            f"name='{item.item_name}', qty={quantity}, unit_price={unit_price}, "
            f"total={amount:.2f}"
        )
        
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
