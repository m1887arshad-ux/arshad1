"""
AgentAction: draft created from Telegram, executed ONLY after owner approval.
Trust: no silent execution. Status flow: DRAFT -> APPROVED/REJECTED -> EXECUTED (if approved).
"""
from sqlalchemy import Column, Integer, String, ForeignKey, DateTime, Text
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from sqlalchemy.types import JSON
from app.db.base import Base


class AgentAction(Base):
    __tablename__ = "agent_actions"

    id = Column(Integer, primary_key=True, index=True)
    business_id = Column(Integer, ForeignKey("businesses.id", ondelete="CASCADE"), nullable=False)
    intent = Column(String(128), nullable=False)  # e.g. create_invoice, send_reminder
    payload = Column(JSON, nullable=True)  # structured entities: customer_name, amount, etc.
    status = Column(String(32), nullable=False, default="DRAFT")  # DRAFT | APPROVED | REJECTED | EXECUTED
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    # Optional: agent explanation for owner (future: from LLM)
    explanation = Column(Text, nullable=True)

    business = relationship("Business", backref="agent_actions")
