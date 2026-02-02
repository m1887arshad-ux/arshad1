from sqlalchemy import Column, Integer, ForeignKey, Numeric, DateTime, String
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.db.base import Base


class Ledger(Base):
    __tablename__ = "ledger"

    id = Column(Integer, primary_key=True, index=True)
    customer_id = Column(Integer, ForeignKey("customers.id", ondelete="CASCADE"), nullable=False)
    debit = Column(Numeric(12, 2), default=0)
    credit = Column(Numeric(12, 2), default=0)
    description = Column(String(512), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    customer = relationship("Customer", backref="ledger_entries")
