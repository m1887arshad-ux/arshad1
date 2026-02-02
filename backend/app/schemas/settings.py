from pydantic import BaseModel
from typing import Optional


class SettingsResponse(BaseModel):
    require_approval_invoices: bool
    whatsapp_notifications: bool
    agent_actions_enabled: bool
    preferred_language: str

    class Config:
        from_attributes = True


class SettingsUpdate(BaseModel):
    require_approval_invoices: Optional[bool] = None
    whatsapp_notifications: Optional[bool] = None
    agent_actions_enabled: Optional[bool] = None
    preferred_language: Optional[str] = None
