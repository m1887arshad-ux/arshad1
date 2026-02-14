"""Invoice creation. Used by executor after owner approval."""
import re
from sqlalchemy.orm import Session
from decimal import Decimal

from app.models.customer import Customer
from app.models.invoice import Invoice
from app.services.ledger_service import add_ledger_entry


def sanitize_customer_name(name: str) -> str:
    """Sanitize customer name to prevent injection and ensure clean data.
    
    - Remove SQL-like patterns
    - Strip excessive whitespace
    - Remove special characters except letters, numbers, spaces, hyphens, apostrophes
    - Limit length to 100 characters
    """
    if not name:
        raise ValueError("Customer name cannot be empty")
    
    # Strip and collapse whitespace
    name = " ".join(name.strip().split())
    
    # Remove potentially dangerous patterns
    dangerous_patterns = [
        r'--',  # SQL comments
        r';',   # SQL statement separator
        r'\/\*', r'\*\/',  # SQL block comments
        r'<script', r'<\/script>',  # XSS
        r'javascript:',  # XSS
    ]
    
    for pattern in dangerous_patterns:
        name = re.sub(pattern, '', name, flags=re.IGNORECASE)
    
    # Keep only safe characters: letters, numbers, spaces, hyphens, apostrophes, dots
    name = re.sub(r"[^a-zA-Z0-9\s\-'.]", '', name)
    
    # Limit length
    name = name[:100]
    
    # Final validation
    if not name or len(name.strip()) < 2:
        raise ValueError("Customer name must be at least 2 characters after sanitization")
    
    return name.strip()


def calculate_gst(base_amount: float, gst_rate: float = 0.18) -> dict:
    """Calculate GST breakdown for Indian tax compliance.
    
    Args:
        base_amount: Amount before tax
        gst_rate: GST rate (default 18% for most medicines, use 5% for generics if needed)
    
    Returns:
        dict with base_amount, gst_rate, gst_amount, total_amount
    """
    base = Decimal(str(base_amount))
    rate = Decimal(str(gst_rate))
    gst_amt = base * rate
    total = base + gst_amt
    
    return {
        "base_amount": base,
        "gst_rate": rate,
        "gst_amount": gst_amt,
        "total_amount": total
    }


def get_or_create_customer(db: Session, business_id: int, name: str, phone: str | None = None) -> Customer:
    """Find customer by name under business or create. Sanitizes input.
    
    Args:
        db: Database session
        business_id: Business ID
        name: Customer name (will be sanitized)
        phone: Customer phone (optional)
    
    Returns:
        Customer object
    
    Raises:
        ValueError: If name is invalid after sanitization
    """
    name_clean = sanitize_customer_name(name)
    c = db.query(Customer).filter(Customer.business_id == business_id, Customer.name == name_clean).first()
    if c:
        return c
    c = Customer(business_id=business_id, name=name_clean, phone=phone)
    db.add(c)
    db.commit()
    db.refresh(c)
    return c


def create_invoice_for_customer(db: Session, business_id: int, customer_name: str, amount: float, auto_commit: bool = False) -> Invoice:
    """Create invoice with GST calculation and ledger entry. Called only after owner approval.
    
    Args:
        amount: Base amount (before GST). GST will be calculated automatically at 18%
        auto_commit: If True, commits immediately. If False, caller must commit.
    """
    customer = get_or_create_customer(db, business_id, customer_name)
    
    # Calculate GST breakdown (18% GST for medicines in India)
    gst_calc = calculate_gst(amount, gst_rate=0.18)
    
    inv = Invoice(
        customer_id=customer.id,
        base_amount=gst_calc["base_amount"],
        gst_rate=gst_calc["gst_rate"],
        gst_amount=gst_calc["gst_amount"],
        amount=gst_calc["total_amount"],  # Total = base + GST
        status="draft"
    )
    db.add(inv)
    if auto_commit:
        db.commit()
        db.refresh(inv)
    else:
        db.flush()  # Get ID without committing
    
    # Ledger entry uses total amount (including GST)
    add_ledger_entry(db, customer.id, debit=gst_calc["total_amount"], description=f"Invoice #{inv.id}")
    if auto_commit:
        db.commit()
    return inv
