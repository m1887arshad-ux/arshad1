"""Inventory read/update. Used by executor when approved actions affect stock."""
from sqlalchemy.orm import Session
from decimal import Decimal

from app.models.inventory import Inventory


def get_or_create_item(db: Session, business_id: int, item_name: str) -> Inventory:
    item = db.query(Inventory).filter(Inventory.business_id == business_id, Inventory.item_name == item_name).first()
    if item:
        return item
    item = Inventory(business_id=business_id, item_name=item_name.strip(), quantity=Decimal("0"))
    db.add(item)
    db.commit()
    db.refresh(item)
    return item


def adjust_quantity(db: Session, business_id: int, item_name: str, delta: float) -> Inventory:
    """Adjust inventory by delta. Called only after owner approval."""
    item = get_or_create_item(db, business_id, item_name)
    item.quantity = Decimal(str(float(item.quantity) + delta))
    db.commit()
    db.refresh(item)
    return item
