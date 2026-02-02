"""Records: read-only invoices, ledger, inventory for Owner Website."""
from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.orm import Session

from app.api.deps import get_db, get_current_user
from app.models.user import User
from app.models.business import Business
from app.models.invoice import Invoice
from app.models.ledger import Ledger
from app.models.inventory import Inventory
from app.models.customer import Customer

router = APIRouter()


def _get_business(db: Session, user: User) -> Business:
    b = db.query(Business).filter(Business.owner_id == user.id).first()
    if not b:
        raise HTTPException(status_code=404, detail="Business not set up")
    return b


@router.get("/invoices", response_model=list)
def list_invoices(
    search: str | None = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Read-only list of invoices. Owner Website Records tab."""
    business = _get_business(db, current_user)
    # Invoices via customers of this business
    q = (
        db.query(Invoice, Customer)
        .join(Customer, Invoice.customer_id == Customer.id)
        .filter(Customer.business_id == business.id)
    )
    if search:
        q = q.filter(Customer.name.ilike(f"%{search}%"))
    rows = q.order_by(Invoice.created_at.desc()).limit(100).all()
    return [
        {
            "id": inv.id,
            "date": inv.created_at.strftime("%d %b, %Y") if inv.created_at else "",
            "customer": f"{c.name}",
            "amount": f"₹ {inv.amount:,.2f}",
            "status": inv.status,
        }
        for inv, c in rows
    ]


@router.get("/ledger", response_model=list)
def list_ledger(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """Read-only ledger entries."""
    business = _get_business(db, current_user)
    rows = (
        db.query(Ledger, Customer)
        .join(Customer, Ledger.customer_id == Customer.id)
        .filter(Customer.business_id == business.id)
        .order_by(Ledger.created_at.desc())
        .limit(100)
        .all()
    )
    return [
        {
            "id": l.id,
            "date": l.created_at.strftime("%d %b") if l.created_at else "",
            "description": l.description or "",
            "debit": f"₹ {l.debit}" if l.debit else "-",
            "credit": f"₹ {l.credit}" if l.credit else "-",
        }
        for l, c in rows
    ]


@router.get("/inventory", response_model=list)
def list_inventory(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """Read-only inventory."""
    business = _get_business(db, current_user)
    items = db.query(Inventory).filter(Inventory.business_id == business.id).all()
    return [
        {
            "id": i.id,
            "item_name": i.item_name,
            "quantity": float(i.quantity),
            "unit": "pcs",
        }
        for i in items
    ]
