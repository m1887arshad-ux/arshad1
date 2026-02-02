from pydantic import BaseModel
from typing import Optional


class BusinessSetup(BaseModel):
    name: str
    owner_name: str  # display only; owner from JWT
    preferred_language: str = "en"


class BusinessResponse(BaseModel):
    id: int
    name: str
    preferred_language: str
    telegram_chat_id: Optional[str] = None

    class Config:
        from_attributes = True
