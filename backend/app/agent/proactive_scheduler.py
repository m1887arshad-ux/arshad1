"""
Proactive Agent — Background Payment Reminder Scanner.

AUTONOMY PROOF:
This is the ONE proactive behavior that demonstrates agent autonomy.
It runs periodically without user prompting, but NEVER executes autonomously.

SAFETY MODEL:
1. Agent SCANS ledger for unpaid invoices > 30 days
2. Agent CREATES a DRAFT AgentAction of type "send_payment_reminder"
3. Owner REVIEWS and APPROVES/REJECTS via dashboard
4. ONLY after approval, reminder is sent via Telegram

This proves the agent can:
- Act proactively (not just react to commands)
- Identify business-relevant situations
- Propose actions without executing them
- Maintain human-in-the-loop safety

NO AUTO-EXECUTION. NO AUTONOMOUS FINANCIAL ACTIONS.
"""
import logging
import asyncio
from datetime import datetime, timedelta
from typing import List, Dict
from sqlalchemy.orm import Session

from app.db.session import SessionLocal
from app.models.ledger import Ledger
from app.models.customer import Customer
from app.models.business import Business
from app.models.agent_action import AgentAction

logger = logging.getLogger(__name__)

# Configuration
OVERDUE_DAYS = 30  # Invoices unpaid for this many days trigger reminder
SCAN_INTERVAL_SECONDS = 3600  # Run every 1 hour (3600 seconds)


def get_overdue_customers(db: Session, business_id: int) -> List[Dict]:
    """
    Scan ledger for customers with unpaid balances older than OVERDUE_DAYS.
    
    Logic:
    - Sum all debits (invoices) and credits (payments) per customer
    - If net balance > 0 and oldest unpaid entry > 30 days, flag for reminder
    
    Returns:
        List of dicts: [{customer_id, customer_name, amount_due, days_overdue}]
    """
    cutoff_date = datetime.utcnow() - timedelta(days=OVERDUE_DAYS)
    
    # Get all customers for this business with outstanding balances
    overdue_customers = []
    
    customers = db.query(Customer).filter(Customer.business_id == business_id).all()
    
    for customer in customers:
        # Calculate net balance from ledger
        ledger_entries = db.query(Ledger).filter(Ledger.customer_id == customer.id).all()
        
        if not ledger_entries:
            continue
        
        total_debit = sum(float(e.debit or 0) for e in ledger_entries)
        total_credit = sum(float(e.credit or 0) for e in ledger_entries)
        balance = total_debit - total_credit
        
        if balance <= 0:
            continue  # No outstanding amount
        
        # Find oldest unpaid entry
        oldest_debit = min(
            (e.created_at for e in ledger_entries if e.debit and e.debit > 0),
            default=None
        )
        
        if oldest_debit and oldest_debit < cutoff_date:
            days_overdue = (datetime.utcnow() - oldest_debit).days
            overdue_customers.append({
                "customer_id": customer.id,
                "customer_name": customer.name,
                "amount_due": balance,
                "days_overdue": days_overdue,
                "phone": customer.phone,
            })
    
    return overdue_customers


def create_reminder_draft(db: Session, business_id: int, customer_data: Dict) -> AgentAction | None:
    """
    Create a DRAFT AgentAction for sending payment reminder.
    
    SAFETY: This does NOT send the reminder. It only creates a draft
    that the owner must approve via the dashboard.
    
    Returns:
        AgentAction if created, None if duplicate exists
    """
    # Check if a pending reminder already exists for this customer
    existing = db.query(AgentAction).filter(
        AgentAction.business_id == business_id,
        AgentAction.intent == "send_payment_reminder",
        AgentAction.status.in_(["DRAFT", "APPROVED"]),
        AgentAction.payload["customer_id"].astext == str(customer_data["customer_id"])
    ).first()
    
    if existing:
        logger.debug(f"Reminder draft already exists for customer {customer_data['customer_name']}")
        return None
    
    # Create new draft
    action = AgentAction(
        business_id=business_id,
        intent="send_payment_reminder",
        payload={
            "customer_id": customer_data["customer_id"],
            "customer_name": customer_data["customer_name"],
            "amount_due": customer_data["amount_due"],
            "days_overdue": customer_data["days_overdue"],
            "phone": customer_data.get("phone"),
        },
        status="DRAFT",
        explanation=(
            f"⏰ PROACTIVE AGENT: Customer '{customer_data['customer_name']}' has "
            f"₹{customer_data['amount_due']:.2f} outstanding for {customer_data['days_overdue']} days. "
            f"Approve to send payment reminder via Telegram."
        ),
    )
    db.add(action)
    db.commit()
    db.refresh(action)
    
    logger.info(
        f"[ProactiveAgent] Created reminder draft #{action.id} for "
        f"{customer_data['customer_name']} (₹{customer_data['amount_due']:.2f})"
    )
    return action


def scan_and_create_reminders() -> int:
    """
    Main scanner function. Called periodically by background task.
    
    Flow:
    1. Get all businesses
    2. For each business, find overdue customers
    3. Create DRAFT reminder actions (not executed)
    4. Return count of new drafts created
    
    Returns:
        Number of new reminder drafts created
    """
    db = SessionLocal()
    drafts_created = 0
    
    try:
        businesses = db.query(Business).all()
        
        for business in businesses:
            logger.debug(f"[ProactiveAgent] Scanning business: {business.name}")
            
            overdue = get_overdue_customers(db, business.id)
            
            for customer_data in overdue:
                draft = create_reminder_draft(db, business.id, customer_data)
                if draft:
                    drafts_created += 1
        
        if drafts_created > 0:
            logger.info(f"[ProactiveAgent] Created {drafts_created} new payment reminder drafts")
        else:
            logger.debug("[ProactiveAgent] No new reminders needed")
            
    except Exception as e:
        logger.error(f"[ProactiveAgent] Scanner error: {e}")
    finally:
        db.close()
    
    return drafts_created


# ============================================================================
# BACKGROUND TASK — Runs in asyncio loop alongside FastAPI
# ============================================================================

_scheduler_running = False


async def _reminder_scheduler_loop():
    """
    Async background loop that runs the scanner periodically.
    
    Design choices:
    - Simple asyncio.sleep loop (no external scheduler dependency)
    - Runs in same process as FastAPI (no Redis/Celery needed)
    - Graceful shutdown on server stop
    """
    global _scheduler_running
    _scheduler_running = True
    
    logger.info(f"[ProactiveAgent] Scheduler started. Interval: {SCAN_INTERVAL_SECONDS}s")
    
    # Initial delay to let server fully start
    await asyncio.sleep(10)
    
    while _scheduler_running:
        try:
            # Run scanner in thread pool to avoid blocking event loop
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(None, scan_and_create_reminders)
        except Exception as e:
            logger.error(f"[ProactiveAgent] Scheduler error: {e}")
        
        await asyncio.sleep(SCAN_INTERVAL_SECONDS)


def start_reminder_scheduler():
    """Start the background reminder scheduler. Called from FastAPI lifespan."""
    try:
        asyncio.create_task(_reminder_scheduler_loop())
        logger.info("[ProactiveAgent] Payment reminder scheduler initialized")
    except Exception as e:
        logger.error(f"[ProactiveAgent] Failed to start scheduler: {e}")


def stop_reminder_scheduler():
    """Stop the scheduler gracefully. Called from FastAPI shutdown."""
    global _scheduler_running
    _scheduler_running = False
    logger.info("[ProactiveAgent] Scheduler stopped")
