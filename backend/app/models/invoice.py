from sqlalchemy import Column, Integer, String, ForeignKey, Numeric, DateTime
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.db.base import Base


class Invoice(Base):
    __tablename__ = "invoices"

    id = Column(Integer, primary_key=True, index=True)
    customer_id = Column(Integer, ForeignKey("customers.id", ondelete="CASCADE"), nullable=False)
    base_amount = Column(Numeric(12, 2), nullable=False)  # Amount before tax
    gst_rate = Column(Numeric(5, 4), nullable=False, default=0.18)  # GST rate (18% default)
    gst_amount = Column(Numeric(12, 2), nullable=False)  # Calculated GST amount
    amount = Column(Numeric(12, 2), nullable=False)  # Total amount (base + GST)
    status = Column(String(32), default="draft")  # draft, sent, paid
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    customer = relationship("Customer", backref="invoices")
