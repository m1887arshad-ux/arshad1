"""
Telegram utility functions for business resolution and authentication.
"""
import logging
from sqlalchemy.orm import Session
from app.models.business import Business

logger = logging.getLogger(__name__)


def get_business_by_telegram_id(db: Session, chat_id: int) -> Business | None:
    """
    Resolve Business from Telegram chat_id with deterministic fallback.
    
    Resolution Strategy:
    1. Try explicit link: Business.telegram_chat_id == chat_id
    2. Fallback for single-business systems: First business (by ID)
    3. Return None if no businesses exist
    
    This matches the design assumption:
    - System supports one business per owner
    - telegram_chat_id is optional linking mechanism
    - Fallback enables usage without explicit linking step
    
    Args:
        db: Database session
        chat_id: Telegram chat ID from update.effective_chat.id
        
    Returns:
        Business record or None
        
    Thread Safety:
        Read-only query, safe for concurrent access
    """
    chat_id_str = str(chat_id)
    
    # STEP 1: Try explicit Telegram link (deterministic)
    business = (
        db.query(Business)
        .filter(Business.telegram_chat_id == chat_id_str)
        .order_by(Business.id)  # Deterministic if multiple matches (shouldn't happen)
        .first()
    )
    
    if business:
        logger.info(
            f"[TELEGRAM AUTH] Resolved business via telegram_chat_id: "
            f"chat_id={chat_id}, business_id={business.id}, name='{business.name}'"
        )
        return business
    
    # STEP 2: Fallback for single-business systems (deterministic)
    logger.warning(
        f"[TELEGRAM AUTH] No explicit telegram_chat_id link found for chat_id={chat_id}. "
        f"Attempting fallback to first business..."
    )
    
    business = (
        db.query(Business)
        .order_by(Business.id)  # Deterministic: always first by ID
        .first()
    )
    
    if business:
        logger.info(
            f"[TELEGRAM AUTH] Fallback successful: "
            f"chat_id={chat_id} -> business_id={business.id}, name='{business.name}' "
            f"(telegram_chat_id={business.telegram_chat_id or 'NULL'})"
        )
        return business
    
    # STEP 3: No businesses exist
    logger.error(
        f"[TELEGRAM AUTH] No businesses found in database. "
        f"chat_id={chat_id}. Owner must complete business setup first."
    )
    return None
