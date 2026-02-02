"""
Permission checks for Owner Website APIs.
Trust: only the owner of a business can approve actions or change settings.
"""
from app.models.user import User
from app.models.business import Business
from app.db.session import SessionLocal


def user_owns_business(user_id: int, business_id: int) -> bool:
    """Verify that the authenticated user is the owner of the given business."""
    db = SessionLocal()
    try:
        business = db.query(Business).filter(Business.id == business_id, Business.owner_id == user_id).first()
        return business is not None
    finally:
        db.close()
