"""Ledger entries. Used by invoice service and executor."""
from sqlalchemy.orm import Session
from decimal import Decimal

from app.models.ledger import Ledger


def add_ledger_entry(
    db: Session,
    customer_id: int,
    debit: Decimal | float = Decimal("0"),
    credit: Decimal | float = Decimal("0"),
    description: str | None = None,
) -> Ledger:
    entry = Ledger(
        customer_id=customer_id,
        debit=Decimal(str(debit)),
        credit=Decimal(str(credit)),
        description=description,
    )
    db.add(entry)
    db.commit()
    db.refresh(entry)
    return entry
