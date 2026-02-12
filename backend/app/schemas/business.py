from pydantic import BaseModel
from typing import Optional


class BusinessSetup(BaseModel):
    name: str
    owner_name: str  # display only; owner from JWT
    preferred_language: str = "en"


class BusinessUpdate(BaseModel):
    name: Optional[str] = None
    preferred_language: Optional[str] = None
    require_approval_invoices: Optional[bool] = None
    whatsapp_notifications: Optional[bool] = None
    agent_actions_enabled: Optional[bool] = None
    owner_name: Optional[str] = None  # to update user.name


class BusinessResponse(BaseModel):
    id: int
    name: str
    preferred_language: str
    telegram_chat_id: Optional[str] = None
    require_approval_invoices: bool = True
    whatsapp_notifications: bool = True
    agent_actions_enabled: bool = False

    class Config:
        from_attributes = True
