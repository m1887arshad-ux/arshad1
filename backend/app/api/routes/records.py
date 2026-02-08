"""Records: invoices, ledger, inventory for Owner Website with CRUD support."""
from fastapi import APIRouter, Depends, Query, HTTPException, Body
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from sqlalchemy import func
from pydantic import BaseModel
from typing import Optional
from decimal import Decimal
from datetime import datetime, timedelta, date
import csv
import io

from app.api.deps import get_db, get_current_user
from app.models.user import User
from app.models.business import Business
from app.models.invoice import Invoice
from app.models.ledger import Ledger
from app.models.inventory import Inventory
from app.models.customer import Customer
from app.models.agent_action import AgentAction

router = APIRouter()


# ==============================================================================
# PYDANTIC SCHEMAS FOR INVENTORY CRUD
# ==============================================================================

class InventoryCreate(BaseModel):
    item_name: str
    quantity: float = 0
    price: float = 50.0
    disease: Optional[str] = None
    requires_prescription: bool = False
    expiry_date: Optional[date] = None


class InventoryUpdate(BaseModel):
    item_name: Optional[str] = None
    quantity: Optional[float] = None
    price: Optional[float] = None
    disease: Optional[str] = None
    requires_prescription: Optional[bool] = None
    expiry_date: Optional[date] = None


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
def list_inventory(
    search: str | None = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Inventory list with search."""
    business = _get_business(db, current_user)
    q = db.query(Inventory).filter(Inventory.business_id == business.id)
    
    if search:
        q = q.filter(Inventory.item_name.ilike(f"%{search}%"))
    
    items = q.order_by(Inventory.item_name).all()
    return [
        {
            "id": i.id,
            "item_name": i.item_name,
            "quantity": float(i.quantity),
            "price": float(i.price) if i.price else 50.0,
            "disease": i.disease or "",
            "requires_prescription": i.requires_prescription or False,
            "expiry_date": i.expiry_date.isoformat() if i.expiry_date else None,
            "unit": "strips" if "strip" not in i.item_name.lower() else "units",
            "status": "Low Stock" if float(i.quantity) < 20 else "In Stock"
        }
        for i in items
    ]


# ==============================================================================
# LOW STOCK ALERT ENDPOINT
# ==============================================================================

@router.get("/inventory/low-stock", response_model=list)
def get_low_stock_items(
    threshold: int = Query(20, description="Stock threshold for low stock alert"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get items with low stock for dashboard alert banner."""
    business = _get_business(db, current_user)
    items = db.query(Inventory).filter(
        Inventory.business_id == business.id,
        Inventory.quantity < threshold
    ).order_by(Inventory.quantity.asc()).limit(10).all()
    
    return [
        {
            "id": i.id,
            "item_name": i.item_name,
            "quantity": float(i.quantity),
            "status": "Out of Stock" if float(i.quantity) == 0 else "Low Stock"
        }
        for i in items
    ]


# ==============================================================================
# EXPIRY DATE ALERTS ENDPOINT
# ==============================================================================

def get_expiring_items(
    days: int = Query(30, description="Alert for items expiring within N days"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get medicines expiring soon for dashboard alert."""
    business = _get_business(db, current_user)
    today = date.today()
    alert_date = today + timedelta(days=days)
    
    items = db.query(Inventory).filter(
        Inventory.business_id == business.id,
        Inventory.expiry_date.isnot(None),
        Inventory.expiry_date <= alert_date,
        Inventory.expiry_date >= today
    ).order_by(Inventory.expiry_date.asc()).limit(10).all()
    
    return [
        {
            "id": i.id,
            "item_name": i.item_name,
            "expiry_date": i.expiry_date.isoformat() if i.expiry_date else None,
            "days_until_expiry": (i.expiry_date - today).days if i.expiry_date else None,
            "quantity": float(i.quantity)
        }
        for i in items
    ]


# ==============================================================================
# INVENTORY CRUD ENDPOINTS
# ==============================================================================

@router.post("/inventory", response_model=dict)
def create_inventory_item(
    item: InventoryCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Add a new medicine/item to inventory."""
    business = _get_business(db, current_user)
    
    # Validate input values
    if item.quantity < 0:
        raise HTTPException(status_code=400, detail="Quantity cannot be negative")
    if item.price < 0:
        raise HTTPException(status_code=400, detail="Price cannot be negative")
    if not item.item_name.strip():
        raise HTTPException(status_code=400, detail="Item name cannot be empty")
    
    # Check if item already exists
    existing = db.query(Inventory).filter(
        Inventory.business_id == business.id,
        Inventory.item_name.ilike(item.item_name)
    ).first()
    
    if existing:
        raise HTTPException(status_code=400, detail=f"Item '{item.item_name}' already exists")
    
    new_item = Inventory(
        business_id=business.id,
        item_name=item.item_name.strip(),
        quantity=Decimal(str(item.quantity)),
        price=Decimal(str(item.price)),
        disease=item.disease,
        requires_prescription=item.requires_prescription,
        expiry_date=item.expiry_date
    )
    db.add(new_item)
    db.commit()
    db.refresh(new_item)
    
    return {
        "id": new_item.id,
        "item_name": new_item.item_name,
        "quantity": float(new_item.quantity),
        "price": float(new_item.price),
        "message": f"Added {new_item.item_name} to inventory"
    }


@router.patch("/inventory/{item_id}", response_model=dict)
def update_inventory_item(
    item_id: int,
    updates: InventoryUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Update an existing inventory item."""
    business = _get_business(db, current_user)
    
    item = db.query(Inventory).filter(
        Inventory.id == item_id,
        Inventory.business_id == business.id
    ).first()
    
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")
    
    # Validate input values
    if updates.quantity is not None and updates.quantity < 0:
        raise HTTPException(status_code=400, detail="Quantity cannot be negative")
    if updates.price is not None and updates.price < 0:
        raise HTTPException(status_code=400, detail="Price cannot be negative")
    if updates.item_name is not None and not updates.item_name.strip():
        raise HTTPException(status_code=400, detail="Item name cannot be empty")
    
    if updates.item_name is not None:
        item.item_name = updates.item_name.strip()
    if updates.quantity is not None:
        item.quantity = Decimal(str(updates.quantity))
    if updates.price is not None:
        item.price = Decimal(str(updates.price))
    if updates.disease is not None:
        item.disease = updates.disease
    if updates.requires_prescription is not None:
        item.requires_prescription = updates.requires_prescription
    if updates.expiry_date is not None:
        item.expiry_date = updates.expiry_date
    
    db.commit()
    db.refresh(item)
    
    return {
        "id": item.id,
        "item_name": item.item_name,
        "quantity": float(item.quantity),
        "price": float(item.price),
        "message": f"Updated {item.item_name}"
    }


@router.delete("/inventory/{item_id}", response_model=dict)
def delete_inventory_item(
    item_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Delete an inventory item."""
    business = _get_business(db, current_user)
    
    item = db.query(Inventory).filter(
        Inventory.id == item_id,
        Inventory.business_id == business.id
    ).first()
    
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")
    
    item_name = item.item_name
    db.delete(item)
    db.commit()
    
    return {"message": f"Deleted {item_name}", "id": item_id}


# ==============================================================================
# EXPORT ENDPOINTS (CSV Download)
# ==============================================================================

def export_invoices_csv(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Export all invoices as CSV file."""
    business = _get_business(db, current_user)
    
    rows = (
        db.query(Invoice, Customer)
        .join(Customer, Invoice.customer_id == Customer.id)
        .filter(Customer.business_id == business.id)
        .order_by(Invoice.created_at.desc())
        .all()
    )
    
    # Create CSV in memory
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["Date", "Customer", "Amount (₹)", "Status"])
    
    for inv, c in rows:
        writer.writerow([
            inv.created_at.strftime("%Y-%m-%d %H:%M") if inv.created_at else "",
            c.name,
            float(inv.amount) if inv.amount else 0,
            inv.status
        ])
    
    output.seek(0)
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename=invoices_{date.today()}.csv"}
    )


def export_inventory_csv(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Export inventory as CSV file."""
    business = _get_business(db, current_user)
    
    items = db.query(Inventory).filter(
        Inventory.business_id == business.id
    ).order_by(Inventory.item_name).all()
    
    # Create CSV in memory
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["Medicine Name", "Quantity", "Price (₹)", "Disease", "Expiry Date", "Requires Rx"])
    
    for i in items:
        writer.writerow([
            i.item_name,
            float(i.quantity),
            float(i.price) if i.price else 50.0,
            i.disease or "",
            i.expiry_date.isoformat() if i.expiry_date else "",
            "Yes" if i.requires_prescription else "No"
        ])
    
    output.seek(0)
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename=inventory_{date.today()}.csv"}
    )
