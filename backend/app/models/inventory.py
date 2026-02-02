from sqlalchemy import Column, Integer, String, ForeignKey, Numeric
from sqlalchemy.orm import relationship
from app.db.base import Base


class Inventory(Base):
    __tablename__ = "inventory"

    id = Column(Integer, primary_key=True, index=True)
    business_id = Column(Integer, ForeignKey("businesses.id", ondelete="CASCADE"), nullable=False)
    item_name = Column(String(255), nullable=False)
    quantity = Column(Numeric(12, 2), default=0)

    business = relationship("Business", backref="inventory_items")
