"""
Analytics API — Dashboard charts data for Owner Website.

Provides aggregated data for:
- Daily sales (last 7 days)
- Top-selling products
- Revenue trends
- Action stats (pending/approved/executed)
"""
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import func, case
from datetime import datetime, timedelta
from decimal import Decimal

from app.api.deps import get_db, get_current_user
from app.models.user import User
from app.models.business import Business
from app.models.invoice import Invoice
from app.models.inventory import Inventory
from app.models.customer import Customer
from app.models.agent_action import AgentAction

router = APIRouter()


def _get_business(db: Session, user: User) -> Business:
    from fastapi import HTTPException
    b = db.query(Business).filter(Business.owner_id == user.id).first()
    if not b:
        raise HTTPException(status_code=404, detail="Business not set up")
    return b


@router.get("/summary")
def get_analytics_summary(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get overall analytics summary for dashboard cards.
    Returns: total revenue, total invoices, pending actions, low stock count
    """
    business = _get_business(db, current_user)
    
    # Total revenue from all invoices
    total_revenue = db.query(func.sum(Invoice.amount)).join(
        Customer, Invoice.customer_id == Customer.id
    ).filter(Customer.business_id == business.id).scalar() or Decimal("0")
    
    # Total invoice count
    total_invoices = db.query(func.count(Invoice.id)).join(
        Customer, Invoice.customer_id == Customer.id
    ).filter(Customer.business_id == business.id).scalar() or 0
    
    # Pending actions count
    pending_actions = db.query(func.count(AgentAction.id)).filter(
        AgentAction.business_id == business.id,
        AgentAction.status == "DRAFT"
    ).scalar() or 0
    
    # Low stock items count
    low_stock_count = db.query(func.count(Inventory.id)).filter(
        Inventory.business_id == business.id,
        Inventory.quantity < 20
    ).scalar() or 0
    
    # Total customers
    total_customers = db.query(func.count(Customer.id)).filter(
        Customer.business_id == business.id
    ).scalar() or 0
    
    # Today's revenue
    today = datetime.utcnow().date()
    today_revenue = db.query(func.sum(Invoice.amount)).join(
        Customer, Invoice.customer_id == Customer.id
    ).filter(
        Customer.business_id == business.id,
        func.date(Invoice.created_at) == today
    ).scalar() or Decimal("0")
    
    return {
        "total_revenue": float(total_revenue),
        "total_invoices": total_invoices,
        "pending_actions": pending_actions,
        "low_stock_count": low_stock_count,
        "total_customers": total_customers,
        "today_revenue": float(today_revenue)
    }


@router.get("/daily-sales")
def get_daily_sales(
    days: int = Query(7, description="Number of days to fetch"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get daily sales data for bar chart.
    Returns: [{date: "Mon", revenue: 1500, invoices: 5}, ...]
    """
    business = _get_business(db, current_user)
    
    # Get data for last N days
    end_date = datetime.utcnow().date()
    start_date = end_date - timedelta(days=days - 1)
    
    # Query invoices grouped by date
    results = db.query(
        func.date(Invoice.created_at).label("date"),
        func.sum(Invoice.amount).label("revenue"),
        func.count(Invoice.id).label("invoices")
    ).join(
        Customer, Invoice.customer_id == Customer.id
    ).filter(
        Customer.business_id == business.id,
        func.date(Invoice.created_at) >= start_date
    ).group_by(
        func.date(Invoice.created_at)
    ).order_by(
        func.date(Invoice.created_at)
    ).all()
    
    # Create a dict for quick lookup
    data_dict = {str(r.date): {"revenue": float(r.revenue), "invoices": r.invoices} for r in results}
    
    # Fill in all days (including zeros)
    daily_data = []
    day_names = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]  # Python weekday(): 0=Mon, 6=Sun
    
    for i in range(days):
        d = start_date + timedelta(days=i)
        date_str = str(d)
        day_name = day_names[d.weekday()]  # 0=Mon, 1=Tue, ..., 6=Sun
        
        if date_str in data_dict:
            daily_data.append({
                "date": d.strftime("%d %b"),
                "day": day_name,
                "revenue": data_dict[date_str]["revenue"],
                "invoices": data_dict[date_str]["invoices"]
            })
        else:
            daily_data.append({
                "date": d.strftime("%d %b"),
                "day": day_name,
                "revenue": 0,
                "invoices": 0
            })
    
    return daily_data


@router.get("/top-products")
def get_top_products(
    limit: int = Query(5, description="Number of top products to return"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get top-selling products for pie chart.
    Returns: [{name: "Paracetamol", sold: 150, revenue: 7500}, ...]
    
    Note: Since we don't track per-product sales in invoices yet,
    we'll return inventory data as a placeholder.
    """
    business = _get_business(db, current_user)
    
    # For now, return top items by estimated sales (original qty - current qty)
    # In production, you'd track this in a sales/line_items table
    items = db.query(Inventory).filter(
        Inventory.business_id == business.id
    ).order_by(Inventory.quantity.desc()).limit(limit).all()
    
    colors = ["#6366f1", "#8b5cf6", "#a855f7", "#d946ef", "#ec4899"]
    
    return [
        {
            "name": item.item_name.split(" ")[0] if item.item_name else "Unknown",  # Short name
            "fullName": item.item_name,
            "quantity": float(item.quantity),
            "price": float(item.price) if item.price else 50,
            "color": colors[i % len(colors)]
        }
        for i, item in enumerate(items)
    ]


@router.get("/action-stats")
def get_action_stats(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get action status distribution for pie/donut chart.
    Returns: {pending: 5, approved: 10, executed: 25, rejected: 2}
    """
    business = _get_business(db, current_user)
    
    stats = db.query(
        AgentAction.status,
        func.count(AgentAction.id).label("count")
    ).filter(
        AgentAction.business_id == business.id
    ).group_by(AgentAction.status).all()
    
    result = {
        "pending": 0,
        "approved": 0,
        "executed": 0,
        "rejected": 0
    }
    
    for status, count in stats:
        if status == "DRAFT":
            result["pending"] = count
        elif status == "APPROVED":
            result["approved"] = count
        elif status == "EXECUTED":
            result["executed"] = count
        elif status == "REJECTED":
            result["rejected"] = count
    
    return result


@router.get("/recent-activity")
def get_recent_activity(
    limit: int = Query(10, description="Number of recent activities"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get recent activity feed for dashboard.
    Combines actions, invoices, and inventory changes.
    """
    business = _get_business(db, current_user)
    
    # Get recent actions
    actions = db.query(AgentAction).filter(
        AgentAction.business_id == business.id
    ).order_by(AgentAction.created_at.desc()).limit(limit).all()
    
    activities = []
    for a in actions:
        payload = a.payload or {}
        customer = payload.get("customer_name", "Unknown")
        amount = payload.get("amount", 0)
        
        activities.append({
            "id": a.id,
            "type": "action",
            "intent": a.intent,
            "status": a.status,
            "description": f"{a.intent.replace('_', ' ').title()} for {customer}",
            "amount": float(amount) if amount else None,
            "time": a.created_at.isoformat() if a.created_at else None
        })
    
    return activities
