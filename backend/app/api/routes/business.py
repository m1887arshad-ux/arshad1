"""Business: setup and get. Owner creates one business linked to Telegram (optional)."""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_db, get_current_user
from app.models.user import User
from app.models.business import Business
from app.schemas.business import BusinessSetup, BusinessUpdate, BusinessResponse

router = APIRouter()


@router.post("/setup", response_model=BusinessResponse)
def business_setup(data: BusinessSetup, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """Owner creates/updates their business. One business per owner for simplicity."""
    # Update owner display name
    current_user.name = data.owner_name
    existing = db.query(Business).filter(Business.owner_id == current_user.id).first()
    if existing:
        existing.name = data.name
        existing.preferred_language = data.preferred_language
        db.commit()
        db.refresh(current_user)
        db.refresh(existing)
        return existing
    business = Business(
        owner_id=current_user.id,
        name=data.name,
        preferred_language=data.preferred_language,
    )
    db.add(business)
    db.commit()
    db.refresh(current_user)
    db.refresh(business)
    return business


@router.get("", response_model=BusinessResponse)
def get_business(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """Get current owner's business. 404 if not set up yet."""
    business = db.query(Business).filter(Business.owner_id == current_user.id).first()
    if not business:
        raise HTTPException(status_code=404, detail="Business not set up. Call POST /business/setup first.")
    return business


@router.put("", response_model=BusinessResponse)
def update_business(data: BusinessUpdate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """Update business settings."""
    business = db.query(Business).filter(Business.owner_id == current_user.id).first()
    if not business:
        raise HTTPException(status_code=404, detail="Business not set up. Call POST /business/setup first.")
    
    # Update business fields
    if data.name is not None:
        business.name = data.name
    if data.preferred_language is not None:
        business.preferred_language = data.preferred_language
    if data.require_approval_invoices is not None:
        business.require_approval_invoices = data.require_approval_invoices
    if data.whatsapp_notifications is not None:
        business.whatsapp_notifications = data.whatsapp_notifications
    if data.agent_actions_enabled is not None:
        business.agent_actions_enabled = data.agent_actions_enabled
    
    # Update owner name if provided
    if data.owner_name is not None:
        current_user.name = data.owner_name
    
    db.commit()
    db.refresh(business)
    return business
