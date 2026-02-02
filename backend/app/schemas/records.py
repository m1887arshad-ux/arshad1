from pydantic import BaseModel
from typing import Optional
from datetime import datetime
from decimal import Decimal


class InvoiceRecord(BaseModel):
    id: int
    customer_id: int
    amount: Decimal
    status: str
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class LedgerRecord(BaseModel):
    id: int
    customer_id: int
    debit: Decimal
    credit: Decimal
    description: Optional[str] = None
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class InventoryRecord(BaseModel):
    id: int
    business_id: int
    item_name: str
    quantity: Decimal

    class Config:
        from_attributes = True
