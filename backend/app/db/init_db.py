"""Create all tables. Run on app startup."""
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
            default_user = User(
                email="admin@bharat.com",
                hashed_password=get_password_hash("admin123")
            )
            db.add(default_user)
            db.commit()
            print("✅ Default user created: admin@bharat.com / admin123")
    finally:
        db.close()
