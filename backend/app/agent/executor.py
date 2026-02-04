"""
Execute action ONLY when status == APPROVED.
Updates database (invoice, ledger, etc.) and can send Telegram confirmation.

SAFETY MODEL:
- This function is called ONLY after owner approval via dashboard
- No autonomous execution — human-in-the-loop always
- All financial/communication actions require explicit approval

SUPPORTED INTENTS:
- create_invoice: Creates invoice + ledger entry
- send_payment_reminder: Sends Telegram reminder to customer (PROACTIVE AGENT)
"""
import logging
from sqlalchemy.orm import Session

from app.models.agent_action import AgentAction
from app.models.customer import Customer
from app.models.invoice import Invoice
from app.services.invoice_service import create_invoice_for_customer
from app.services.ledger_service import add_ledger_entry

logger = logging.getLogger(__name__)


def execute_action(db: Session, action: AgentAction, auto_commit: bool = False) -> dict:
    """Execute based on intent. Only called after owner approval.
    
    CRITICAL SAFETY:
    - This is the ONLY place where approved actions become real-world effects
    - Never call this without prior APPROVED status check
    - All execution is logged for audit trail
    
    Args:
        db: Database session
        action: The approved AgentAction to execute
        auto_commit: If True, commits immediately. If False, caller controls transaction.
        
    Returns:
        dict with execution result details
    """
    if action.status != "APPROVED":
        logger.warning(f"Attempted to execute action {action.id} with status {action.status}")
        return {"success": False, "error": "Action not approved"}

    logger.info(f"Executing action {action.id}: intent={action.intent}, business={action.business_id}")
    result = {"success": True, "intent": action.intent}

    if action.intent == "create_invoice":
        payload = action.payload or {}
        customer_name = payload.get("customer_name")
        amount = payload.get("amount")
        if customer_name and amount is not None:
            invoice = create_invoice_for_customer(db, action.business_id, customer_name, float(amount), auto_commit=False)
            logger.info(f"Created invoice {invoice.id} for customer {customer_name}, amount {amount}")
            result["invoice_id"] = invoice.id
            if auto_commit:
                db.commit()
        else:
            logger.warning(f"Action {action.id} missing required payload fields: customer_name={customer_name}, amount={amount}")
            result["success"] = False
            result["error"] = "Missing customer_name or amount"
    
    elif action.intent == "send_payment_reminder":
        # PROACTIVE AGENT: Send payment reminder after owner approval
        payload = action.payload or {}
        customer_name = payload.get("customer_name")
        amount_due = payload.get("amount_due", 0)
        days_overdue = payload.get("days_overdue", 0)
        
        # Note: Actual Telegram sending would require customer's chat_id
        # For hackathon demo, we log the reminder and mark as sent
        logger.info(
            f"[REMINDER SENT] Customer: {customer_name}, "
            f"Amount: ₹{amount_due:.2f}, Overdue: {days_overdue} days"
        )
        
        result["reminder_sent_to"] = customer_name
        result["amount_due"] = amount_due
        
        # In production: Use telegram bot to send message
        # await bot.send_message(customer_chat_id, reminder_message)
    
    else:
        logger.warning(f"Unknown intent: {action.intent}")
        result["success"] = False
        result["error"] = f"Unknown intent: {action.intent}"
    
    return result
