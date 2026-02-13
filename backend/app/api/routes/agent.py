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


@router.post("/chat")
def chat_with_agent(
    request: dict,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Web-based chat endpoint for conversational ordering.
    Enables web users to place orders just like Telegram users.
    
    Request: {"message": "I need 2 Benadryl"}
    Response: {
        "response": str,
        "draft_created": bool,
        "draft_id": int | None,
        "state": str
    }
    """
    from app.services.entity_extractor import extract_all_entities, should_skip_question
    from app.services.product_resolver import resolve_product
    from app.agent.decision_engine import validate_and_create_draft
    from app.models.conversation_state import ConversationState as DBConversationState
    
    business = _get_owner_business(db, current_user)
    message = request.get("message", "").strip()
    
    if not message:
        raise HTTPException(400, "Message cannot be empty")
    
    # Use business ID as chat_id for web users
    web_chat_id = f"web_{business.id}"
    
    logger.info(f"[Web Chat] User {current_user.id}, Business {business.id}: '{message}'")
    
    # Get conversation context
    conv_record = db.query(DBConversationState).filter(
        DBConversationState.chat_id == web_chat_id
    ).first()
    
    if not conv_record:
        context = {
            "state": "idle",
            "entities": {"product": None, "quantity": None, "customer": None},
            "product_id": None,
            "product_name": None,
            "last_message": ""
        }
    else:
        import json
        context = json.loads(conv_record.context_data) if conv_record.context_data else {
            "state": "idle",
            "entities": {"product": None, "quantity": None, "customer": None},
            "product_id": None,
            "product_name": None,
            "last_message": ""
        }
    
    # Extract entities from the message - pass context as dict, NOT db
    extracted = extract_all_entities(
        message,
        context={
            "last_product": context.get("product_name"),
            "last_quantity": context["entities"].get("quantity"),
            "last_customer": context["entities"].get("customer")
        },
        default_owner_name="Owner"
    )
    
    logger.info(f"[Web Chat] Extracted entities: {extracted}")
    
    # Update context with extracted entities - resolve product if found
    if extracted["product"]["value"] and extracted["product"]["confidence"] > 0.5:
        from app.services.product_resolver import resolve_product
        
        resolved = resolve_product(db, business.id, extracted["product"]["value"], min_confidence=0.7)
        
        if resolved:
            # Store only JSON-serializable data in context (not Decimal objects)
            context["entities"]["product"] = {
                "product_id": resolved["product_id"],
                "name": resolved["canonical_name"],
                "confidence": resolved["confidence"]
            }
            context["product_id"] = resolved["product_id"]
            context["product_name"] = resolved["canonical_name"]
            logger.info(f"[Web Chat] Resolved product: {resolved['canonical_name']} (id={resolved['product_id']})")
        else:
            response_text = f"❌ Medicine '{extracted['product']['value']}' not found in inventory. Please try another name."
            return {
                "response": response_text,
                "draft_created": False,
                "draft_id": None,
                "state": context["state"]
            }
    
    if extracted["quantity"]["value"] and extracted["quantity"]["confidence"] > 0.5:
        context["entities"]["quantity"] = extracted["quantity"]["value"]
    
    if extracted["customer"]["value"] and extracted["customer"]["confidence"] > 0.5:
        context["entities"]["customer"] = extracted["customer"]["value"]
    
    context["last_message"] = message
    
    # Determine what we still need
    need_product = context["entities"]["product"] is None
    need_quantity = context["entities"]["quantity"] is None
    need_customer = context["entities"]["customer"] is None
    
    response_text = ""
    draft_created = False
    draft_id = None
    
    # State machine logic
    if need_product:
        context["state"] = "need_product"
        response_text = "What medicine do you need? (e.g., 'Paracetamol', 'Benadryl')"
    
    elif need_quantity:
        context["state"] = "need_quantity"
        response_text = f"How many {context['product_name']} do you need?"
    
    elif need_customer and not should_skip_question(message, "customer"):
        context["state"] = "need_customer"
        response_text = f"Who is this order for? (optional: press skip or just confirm)"
    
    else:
        # All entities collected, create draft
        context["state"] = "ready_to_confirm"
        
        try:
            action = validate_and_create_draft(
                db=db,
                business_id=business.id,
                raw_message=message,
                telegram_chat_id=web_chat_id,
                intent="create_invoice",
                product=context["product_name"],
                product_id=context["product_id"],
                quantity=context["entities"]["quantity"],
                customer=context["entities"]["customer"]
            )
            
            if action:
                draft_id = action.id
                draft_created = True
                response_text = (
                    f"✅ Draft order created!\n\n"
                    f"Product: {context['product_name']}\n"
                    f"Quantity: {context['entities']['quantity']}\n"
                    f"Customer: {context['entities']['customer'] or 'Not specified'}\n\n"
                    f"Draft ID: {draft_id}\n\n"
                    f"Go to Dashboard → Approve to approve this order."
                )
                
                # Reset context after successful order
                context = {
                    "state": "idle",
                    "entities": {"product": None, "quantity": None, "customer": None},
                    "product_id": None,
                    "product_name": None,
                    "last_message": ""
                }
            else:
                response_text = "⚠️ Could not create draft order. Please try again."
        
        except Exception as e:
            logger.error(f"[Web Chat] Error creating draft: {e}", exc_info=True)
            response_text = f"⚠️ Error: {str(e)}"
    
    # Save updated context
    import json
    if conv_record:
        conv_record.context_data = json.dumps(context)
        conv_record.state = context["state"]
    else:
        conv_record = DBConversationState(
            chat_id=web_chat_id,
            state=context["state"],
            context_data=json.dumps(context)
        )
        db.add(conv_record)
    
    db.commit()
    
    return {
        "response": response_text,
        "draft_created": draft_created,
        "draft_id": draft_id,
        "state": context["state"]
    }
