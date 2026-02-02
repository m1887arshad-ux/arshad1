from sqlalchemy import Column, Integer, String, ForeignKey, Numeric, DateTime
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.db.base import Base


class Invoice(Base):
    __tablename__ = "invoices"

    id = Column(Integer, primary_key=True, index=True)
    customer_id = Column(Integer, ForeignKey("customers.id", ondelete="CASCADE"), nullable=False)
    amount = Column(Numeric(12, 2), nullable=False)
    status = Column(String(32), default="draft")  # draft, sent, paid
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    customer = relationship("Customer", backref="invoices")
