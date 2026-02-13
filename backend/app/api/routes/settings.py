"""Owner control panel settings: toggles and language."""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.deps import get_db, get_current_user
from app.models.user import User
from app.models.business import Business
from app.schemas.settings import SettingsResponse, SettingsUpdate

router = APIRouter()


def _get_business(db: Session, user: User) -> Business:
    b = db.query(Business).filter(Business.owner_id == user.id).first()
    if not b:
        raise HTTPException(status_code=404, detail="Business not set up")
    return b


@router.get("", response_model=SettingsResponse)
def get_settings(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    business = _get_business(db, current_user)
    return SettingsResponse(
        require_approval_invoices=business.require_approval_invoices,
        whatsapp_notifications=business.whatsapp_notifications,
        agent_actions_enabled=business.agent_actions_enabled,
        preferred_language=business.preferred_language or "en",
    )


@router.patch("", response_model=SettingsResponse)
def update_settings(
    data: SettingsUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    import logging
    logger = logging.getLogger(__name__)
    logger.info(f"[SETTINGS] Update request from user {current_user.id}: {data.dict()}")
    
    business = _get_business(db, current_user)
    if data.require_approval_invoices is not None:
        business.require_approval_invoices = data.require_approval_invoices
    if data.whatsapp_notifications is not None:
        business.whatsapp_notifications = data.whatsapp_notifications
    if data.agent_actions_enabled is not None:
        business.agent_actions_enabled = data.agent_actions_enabled
    if data.preferred_language is not None:
        business.preferred_language = data.preferred_language
    db.commit()
    db.refresh(business)
    
    logger.info(f"[SETTINGS] Updated business {business.id}: approval={business.require_approval_invoices}, notifications={business.whatsapp_notifications}, agent={business.agent_actions_enabled}")
    
    return get_settings(db=db, current_user=current_user)
