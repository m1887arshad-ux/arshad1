"""
Rule-based decision: validate intent, require approval (ALWAYS), create AgentAction as DRAFT.
Trust: no execution here. Executor runs only after owner approval.
"""
import logging
from sqlalchemy.orm import Session

from app.agent.intent_parser import parse_message, ParsedIntent
from app.models.agent_action import AgentAction

logger = logging.getLogger(__name__)


def validate_and_create_draft(db: Session, business_id: int, raw_message: str, telegram_chat_id: str | None = None) -> AgentAction | None:
    """
    Parse message -> validate -> create AgentAction with status DRAFT.
    Approval is ALWAYS required; no autonomy.
    """
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
