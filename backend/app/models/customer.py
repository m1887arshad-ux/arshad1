from sqlalchemy import Column, Integer, String, ForeignKey
from sqlalchemy.orm import relationship
from app.db.base import Base


class Customer(Base):
    __tablename__ = "customers"

    id = Column(Integer, primary_key=True, index=True)
    business_id = Column(Integer, ForeignKey("businesses.id", ondelete="CASCADE"), nullable=False)
    name = Column(String(255), nullable=False)
    phone = Column(String(64), nullable=True)

    business = relationship("Business", backref="customers")
