"""Business: setup and get. Owner creates one business linked to Telegram (optional)."""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_db, get_current_user
from app.models.user import User
from app.models.business import Business
from app.schemas.business import BusinessSetup, BusinessResponse

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
