"""Invoice creation. Used by executor after owner approval."""
from sqlalchemy.orm import Session
from decimal import Decimal

from app.models.customer import Customer
from app.models.invoice import Invoice
from app.services.ledger_service import add_ledger_entry


def get_or_create_customer(db: Session, business_id: int, name: str, phone: str | None = None) -> Customer:
    """Find customer by name under business or create."""
    name_clean = name.strip()
    c = db.query(Customer).filter(Customer.business_id == business_id, Customer.name == name_clean).first()
    if c:
        return c
    c = Customer(business_id=business_id, name=name_clean, phone=phone)
    db.add(c)
    db.commit()
    db.refresh(c)
    return c


def create_invoice_for_customer(db: Session, business_id: int, customer_name: str, amount: float, auto_commit: bool = False) -> Invoice:
    """Create invoice and ledger entry. Called only after owner approval.
    
    Args:
        auto_commit: If True, commits immediately. If False, caller must commit.
    """
    customer = get_or_create_customer(db, business_id, customer_name)
    inv = Invoice(customer_id=customer.id, amount=Decimal(str(amount)), status="draft")
    db.add(inv)
    if auto_commit:
        db.commit()
        db.refresh(inv)
    else:
        db.flush()  # Get ID without committing
    add_ledger_entry(db, customer.id, debit=Decimal(str(amount)), description=f"Invoice #{inv.id}")
    if auto_commit:
        db.commit()
    return inv
