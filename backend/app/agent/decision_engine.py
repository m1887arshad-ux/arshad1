"""
Rule-based decision: validate intent, require approval (ALWAYS), create AgentAction as DRAFT.
Trust: no execution here. Executor runs only after owner approval.
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
) -> AgentAction | None:
    """
    Create AgentAction with status DRAFT from explicit parameters or parsed message.
    Approval is ALWAYS required; no autonomy.
    
    Args:
        db: Database session
        business_id: Business ID
        raw_message: Original user message
        telegram_chat_id: Telegram chat ID for linking
        intent: Explicit intent (e.g., "create_invoice")
        product: Product name
        quantity: Product quantity
        customer: Customer name
    """
    
    # If explicit parameters provided (from FSM), use them directly
    if intent == "create_invoice" and product and quantity and customer:
        # Look up product price from inventory
        item = db.query(Inventory).filter(
            Inventory.business_id == business_id,
            Inventory.item_name.ilike(f"%{product}%")
        ).first()
        
        # Default price if not found (hackathon fallback)
        unit_price = 50.0  # Default ₹50 per unit
        if item and hasattr(item, 'price') and item.price:
            unit_price = float(item.price)
        
        amount = quantity * unit_price
        
        payload = {
            "customer_name": customer,
            "product": product,
            "quantity": quantity,
            "amount": amount,
            "action_type": "Invoice",
            "channel": "Telegram",
        }
        
        action = AgentAction(
            business_id=business_id,
            intent=intent,
            payload=payload,
            status="DRAFT",
            explanation=f"Invoice for {customer}: {int(quantity)} × {product} = ₹{amount:.2f}",
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
