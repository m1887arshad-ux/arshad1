from sqlalchemy import Column, Integer, String, ForeignKey, Numeric, Boolean, Date
from sqlalchemy.orm import relationship
from app.db.base import Base


class Inventory(Base):
    """
    Pharmacy Inventory Model.
    
    COMPLIANCE NOTE:
    - requires_prescription: If True, invoice creation MUST go through owner approval
    - This is a minimal pharmacy-specific safety rule
    - No OCR/upload logic — just a boolean flag checked during draft creation
    """
    __tablename__ = "inventory"

    id = Column(Integer, primary_key=True, index=True)
    business_id = Column(Integer, ForeignKey("businesses.id", ondelete="CASCADE"), nullable=False)
    item_name = Column(String(255), nullable=False)
    quantity = Column(Numeric(12, 2), default=0)
    price = Column(Numeric(10, 2), default=50.0)  # ₹ per unit
    disease = Column(String(512), nullable=True)  # What the medicine treats
    requires_prescription = Column(Boolean, default=False)  # Pharmacy compliance flag

    business = relationship("Business", backref="inventory_items")
