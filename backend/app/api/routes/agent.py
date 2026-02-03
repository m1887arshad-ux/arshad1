"""
Agent actions: list pending/drafts and approve/reject.
Trust: execution ONLY after owner approval. No autonomy.
"""
import logging
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_db, get_current_user
from app.models.user import User
from app.models.business import Business
from app.models.agent_action import AgentAction
from app.schemas.agent_action import AgentActionResponse
from app.agent.executor import execute_action

logger = logging.getLogger(__name__)
router = APIRouter()


def _get_owner_business(db: Session, user: User) -> Business:
    business = db.query(Business).filter(Business.owner_id == user.id).first()
    if not business:
        raise HTTPException(status_code=404, detail="Business not set up")
    return business


@router.get("/pending", response_model=list[AgentActionResponse])
def list_pending(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """List agent actions for owner: DRAFT and APPROVED (not yet executed). Owner Website uses this for dashboard."""
    business = _get_owner_business(db, current_user)
    actions = (
        db.query(AgentAction)
        .filter(AgentAction.business_id == business.id)
        .filter(AgentAction.status.in_(["DRAFT", "APPROVED"]))
        .order_by(AgentAction.created_at.desc())
        .limit(50)
        .all()
    )
    return actions


@router.get("/actions", response_model=list[AgentActionResponse])
def list_actions(limit: int = 20, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """List recent agent actions (all statuses). For Owner Dashboard 'Recent Agent Actions'."""
    business = _get_owner_business(db, current_user)
    actions = (
        db.query(AgentAction)
        .filter(AgentAction.business_id == business.id)
        .order_by(AgentAction.created_at.desc())
        .limit(limit)
        .all()
    )
    return actions


@router.get("/actions/{action_id}", response_model=AgentActionResponse)
def get_action(action_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """Get single action by id. For Owner Website approve page."""
    business = _get_owner_business(db, current_user)
    action = db.query(AgentAction).filter(AgentAction.id == action_id, AgentAction.business_id == business.id).first()
    if not action:
        raise HTTPException(status_code=404, detail="Action not found")
    return action


@router.post("/actions/{action_id}/approve")
def approve_action(action_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """Owner approves action. Backend then executes it (e.g. create invoice, send reminder). Trust: no silent execution."""
    business = _get_owner_business(db, current_user)
    action = db.query(AgentAction).filter(AgentAction.id == action_id, AgentAction.business_id == business.id).first()
    if not action:
        raise HTTPException(status_code=404, detail="Action not found")
    if action.status != "DRAFT":
        raise HTTPException(status_code=400, detail=f"Action already {action.status}")
    
    # Atomic state transition with error handling
    try:
        action.status = "APPROVED"
        db.flush()  # Don't commit yet - keep transaction open
        logger.info(f"Action {action_id} approved by owner {current_user.id} for business {business.id}")
        
        # Execute: update DB (invoice/ledger/etc.) - all in same transaction
        execute_action(db, action, auto_commit=False)
        action.status = "EXECUTED"
        
        # Single atomic commit for all changes
        db.commit()
        db.refresh(action)
        logger.info(f"Action {action_id} executed successfully (atomic transaction)")
        return {"ok": True, "status": "EXECUTED"}
    except Exception as e:
        db.rollback()  # Reverts everything: approval + invoice + ledger
        logger.error(f"Action {action_id} execution failed: {str(e)}")
        # Reload action state after rollback
        db.refresh(action)
        raise HTTPException(status_code=500, detail=f"Execution failed: {str(e)}")


@router.post("/actions/{action_id}/reject")
def reject_action(action_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """Owner rejects action. No execution. Logged for visibility."""
    business = _get_owner_business(db, current_user)
    action = db.query(AgentAction).filter(AgentAction.id == action_id, AgentAction.business_id == business.id).first()
    if not action:
        raise HTTPException(status_code=404, detail="Action not found")
    if action.status != "DRAFT":
        raise HTTPException(status_code=400, detail=f"Action already {action.status}")
    action.status = "REJECTED"
    db.commit()
    logger.info(f"Action {action_id} rejected by owner {current_user.id} for business {business.id}")
    return {"ok": True, "status": "REJECTED"}
