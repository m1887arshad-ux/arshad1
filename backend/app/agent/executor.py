"""
Execute action ONLY when status == APPROVED.
Updates database (invoice, ledger, etc.) and can send Telegram confirmation.
Trust: no silent execution; called explicitly from API after owner approval.
"""
import logging
from sqlalchemy.orm import Session

from app.models.agent_action import AgentAction
from app.models.customer import Customer
from app.models.invoice import Invoice
from app.services.invoice_service import create_invoice_for_customer
from app.services.ledger_service import add_ledger_entry

logger = logging.getLogger(__name__)


def execute_action(db: Session, action: AgentAction, auto_commit: bool = False) -> None:
    """Execute based on intent. Only called after owner approval.
    
    Args:
        auto_commit: If True, commits immediately. If False, caller controls transaction.
    """
    if action.status != "APPROVED":
        logger.warning(f"Attempted to execute action {action.id} with status {action.status}")
        return

    logger.info(f"Executing action {action.id}: intent={action.intent}, business={action.business_id}")

    if action.intent == "create_invoice":
        payload = action.payload or {}
        customer_name = payload.get("customer_name")
        amount = payload.get("amount")
        if customer_name and amount is not None:
            invoice = create_invoice_for_customer(db, action.business_id, customer_name, float(amount), auto_commit=False)
            logger.info(f"Created invoice {invoice.id} for customer {customer_name}, amount {amount}")
            if auto_commit:
                db.commit()
        else:
            logger.warning(f"Action {action.id} missing required payload fields: customer_name={customer_name}, amount={amount}")
    # Future: send_reminder, etc. — all rule-based, no AI
