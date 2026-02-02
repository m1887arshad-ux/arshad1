from sqlalchemy import Column, Integer, String, ForeignKey, Boolean
from sqlalchemy.orm import relationship
from app.db.base import Base


class Business(Base):
    __tablename__ = "businesses"

    id = Column(Integer, primary_key=True, index=True)
    owner_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    name = Column(String(255), nullable=False)
    preferred_language = Column(String(64), default="en")
    telegram_chat_id = Column(String(64), nullable=True)  # link Telegram to this business
    # Owner control panel settings
    require_approval_invoices = Column(Boolean, default=True)
    whatsapp_notifications = Column(Boolean, default=True)
    agent_actions_enabled = Column(Boolean, default=False)

    owner = relationship("User", backref="businesses")
