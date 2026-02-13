"""Create all tables. Run on app startup.

SECURITY: Auto-generates secure random default password (not hardcoded).
Owner must change this after first login.
"""
import secrets
from app.db.base import Base
from app.db.session import engine, SessionLocal
from app.models import user, business, customer, invoice, ledger, inventory, agent_action, conversation_state  # noqa: F401 - register models
from app.models.user import User
from app.core.security import get_password_hash


def init_db():
    Base.metadata.create_all(bind=engine)
    
    # Create default admin user if no users exist
    db = SessionLocal()
    try:
        user_count = db.query(User).count()
        if user_count == 0:
            # SECURITY: Generate random password (not hardcoded weak password)
            default_password = secrets.token_urlsafe(16)
            
            default_user = User(
                email="admin@bharat.com",
                hashed_password=get_password_hash(default_password)
            )
            db.add(default_user)
            db.commit()
            
            # Print to console (only on initial setup)
            print("\n" + "="*70)
            print("⚠️  DEFAULT ADMIN USER CREATED")
            print("="*70)
            print(f"Email:    admin@bharat.com")
            print(f"Password: {default_password}")
            print("\n🔐 SECURITY: Change this password immediately after first login!")
            print("="*70 + "\n")
    finally:
        db.close()

