"""
Conversation State Model — Persistent FSM storage.

WHY THIS EXISTS:
- In-memory FSM state is lost on server restart
- Multi-instance deployments would have state conflicts
- Conversation continuity is critical for multi-step flows

This replaces the in-memory FSM_STATE dict with database persistence.
"""
from sqlalchemy import Column, Integer, String, DateTime, Text
from sqlalchemy.sql import func
from sqlalchemy.types import JSON
from app.db.base import Base


class ConversationState(Base):
    """
    Persists FSM conversation state per Telegram chat.
    
    Schema:
        chat_id: Telegram chat identifier (unique)
        state: Current FSM step (e.g., "await_product", "await_quantity")
        payload: JSON blob with collected data (product, quantity, customer, etc.)
        updated_at: Last activity timestamp (for cleanup/expiry)
    
    Lifecycle:
        1. Created on first FSM interaction
        2. Updated on every state transition
        3. Deleted/reset on flow completion or cancellation
        4. Can be expired after 24h inactivity (future cleanup job)
    """
    __tablename__ = "conversation_states"

    id = Column(Integer, primary_key=True, index=True)
    chat_id = Column(String(64), unique=True, nullable=False, index=True)
    state = Column(String(64), nullable=False, default="idle")
    payload = Column(JSON, nullable=True, default=dict)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    def __repr__(self):
        return f"<ConversationState chat_id={self.chat_id} state={self.state}>"
