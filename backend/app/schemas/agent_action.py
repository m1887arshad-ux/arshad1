from pydantic import BaseModel
from typing import Optional, Any
from datetime import datetime


class AgentActionPayload(BaseModel):
    """Structured payload from rule-based intent parser."""
    customer_name: Optional[str] = None
    amount: Optional[float] = None
    channel: Optional[str] = None
    action_type: Optional[str] = None


class AgentActionResponse(BaseModel):
    id: int
    business_id: int
    intent: str
    payload: Optional[dict] = None
    status: str
    created_at: datetime
    explanation: Optional[str] = None

    class Config:
        from_attributes = True


class AgentActionApproveReject(BaseModel):
    """No body required; approval/rejection is the action."""
    pass
