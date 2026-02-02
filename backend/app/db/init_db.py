"""Create all tables. Run on app startup."""
from app.db.base import Base
from app.db.session import engine
from app.models import user, business, customer, invoice, ledger, inventory, agent_action  # noqa: F401 - register models


def init_db():
    Base.metadata.create_all(bind=engine)
