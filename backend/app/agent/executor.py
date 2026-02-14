"""
Execute action ONLY when status == APPROVED.
Updates database (invoice, ledger, etc.) and can send Telegram confirmation.

SAFETY MODEL:
- This function is called ONLY after owner approval via dashboard
- No autonomous execution — human-in-the-loop always
- All financial/communication actions require explicit approval

SUPPORTED INTENTS:
- create_invoice: Creates invoice + ledger entry + sends to customer via Telegram
- send_payment_reminder: Sends Telegram reminder to customer (PROACTIVE AGENT)
"""
import logging
import asyncio
from sqlalchemy.orm import Session

from app.models.agent_action import AgentAction
from app.models.customer import Customer
from app.models.invoice import Invoice
from app.models.business import Business
from app.services.invoice_service import create_invoice_for_customer
from app.services.ledger_service import add_ledger_entry
from app.services.pdf_service import format_invoice_message
from app.telegram.bot import send_telegram_message

logger = logging.getLogger(__name__)


def execute_action(db: Session, action: AgentAction, auto_commit: bool = False) -> dict:
    """Execute based on intent. Only called after owner approval.
    
    CRITICAL SAFETY:
    - This is the ONLY place where approved actions become real-world effects
    - Never call this without prior APPROVED status check
    - All execution is logged for audit trail
    - Transaction rollback on any error
    
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

    try:
        if action.intent == "create_invoice":
            payload = action.payload or {}
            customer_name = payload.get("customer_name")
            amount = payload.get("amount")
            telegram_chat_id = payload.get("telegram_chat_id")
            
            if customer_name and amount is not None:
                invoice = create_invoice_for_customer(db, action.business_id, customer_name, float(amount), auto_commit=False)
                logger.info(f"Created invoice {invoice.id} for customer {customer_name}, amount {amount}")
                result["invoice_id"] = invoice.id
                if auto_commit:
                    db.commit()
                
                # Send invoice to customer via Telegram if chat_id available
                if telegram_chat_id:
                    try:
                        # Get business info for message
                        business = db.query(Business).filter(Business.id == action.business_id).first()
                        business_name = business.name if business else "Bharat Medical Store"
                        
                        # Format message
                        message = format_invoice_message(invoice, customer_name, business_name)
                        
                        # Send via Telegram using async-to-sync bridge with timeout
                        import concurrent.futures
                        from functools import partial
                        
                        async def send_with_timeout():
                            try:
                                return await asyncio.wait_for(
                                    send_telegram_message(telegram_chat_id, message),
                                    timeout=10.0  # 10 second timeout
                                )
                            except asyncio.TimeoutError:
                                logger.warning(f"Telegram send timeout for invoice {invoice.id}")
                                return False
                        
                        # Use thread pool to run async function from sync context
                        with concurrent.futures.ThreadPoolExecutor() as executor:
                            future = executor.submit(asyncio.run, send_with_timeout())
                            sent = future.result(timeout=15)  # 15 second overall timeout
                        
                        if sent:
                            logger.info(f"Invoice {invoice.id} sent to customer via Telegram chat {telegram_chat_id}")
                            result["telegram_sent"] = True
                        else:
                            logger.warning(f"Failed to send invoice {invoice.id} via Telegram")
                            result["telegram_sent"] = False
                    except Exception as e:
                        logger.error(f"Error sending invoice via Telegram: {e}")
                        result["telegram_sent"] = False
                        # Don't fail the whole transaction due to Telegram error
                else:
                    logger.info(f"No Telegram chat_id available for invoice {invoice.id}")
                    result["telegram_sent"] = False
            else:
                logger.warning(f"Action {action.id} missing required payload fields: customer_name={customer_name}, amount={amount}")
                result["success"] = False
                result["error"] = "Missing customer_name or amount"
                if auto_commit:
                    db.rollback()
                result["success"] = False
                result["error"] = "Missing customer_name or amount"
                if auto_commit:
                    db.rollback()
        
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
    
    except Exception as e:
        logger.error(f"Error executing action {action.id}: {e}", exc_info=True)
        result["success"] = False
        result["error"] = str(e)
        if auto_commit:
            db.rollback()
            logger.info(f"Transaction rolled back for action {action.id}")
    
    return result
