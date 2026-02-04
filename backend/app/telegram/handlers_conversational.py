"""
NEW CONVERSATIONAL HANDLER - Flexible, Interruptible, Natural

Architecture:
1. Parse intent (deterministic + LLM fallback)
2. Update conversation mode (idle/browsing/ordering/confirming)
3. Route response based on intent + mode
4. Allow interruptions (queries reset order flow)
5. Make customer optional

Key Changes from Old Handler:
- Queries can interrupt orders
- Customer is optional (defaults to "Walk-in Customer")
- Context preserved across mode switches
- Explicit state transitions
"""
import logging
from telegram import Update
from telegram.ext import ContextTypes

from app.db.session import SessionLocal
from app.models.business import Business
from app.models.inventory import Inventory
from app.models.conversation_state import ConversationState as DBConversationState
from app.agent.decision_engine import validate_and_create_draft
from app.services.symptom_mapper import map_symptom_to_medicines
from app.agent.conversation_state import ConversationMode, IntentType
from app.agent.intent_parser_deterministic import parse_intent_deterministic
from ai.intent_parser import parse_message_with_ai

logger = logging.getLogger(__name__)


# ============================================================================
# CONVERSATION STATE HELPERS
# ============================================================================

def get_conversation_data(db, chat_id: int) -> dict:
    """Get current conversation mode and context"""
    record = db.query(DBConversationState).filter(
        DBConversationState.chat_id == str(chat_id)
    ).first()
    
    if not record:
        return {
            "mode": ConversationMode.IDLE,
            "context": {}
        }
    
    payload = record.payload or {}
    return {
        "mode": payload.get("mode", ConversationMode.IDLE),
        "context": payload.get("context", {})
    }


def save_conversation_data(db, chat_id: int, mode: str, context: dict):
    """Save conversation mode and context"""
    record = db.query(DBConversationState).filter(
        DBConversationState.chat_id == str(chat_id)
    ).first()
    
    payload = {
        "mode": mode,
        "context": context
    }
    
    if record:
        record.state = mode
        record.payload = payload
    else:
        record = DBConversationState(
            chat_id=str(chat_id),
            state=mode,
            payload=payload
        )
        db.add(record)
    
    db.commit()
    logger.info(f"[CONV] chat_id={chat_id}, mode={mode}, context={context}")


def reset_conversation(db, chat_id: int):
    """Reset to idle state"""
    save_conversation_data(db, chat_id, ConversationMode.IDLE, {})


# ============================================================================
# STATE TRANSITION LOGIC
# ============================================================================

def update_conversation_state(
    db,
    chat_id: int,
    intent: str,
    entities: dict,
    should_reset: bool,
    current_mode: str,
    current_context: dict
) -> tuple:
    """
    Update conversation state based on intent
    Returns: (new_mode, new_context)
    """
    context = current_context.copy()
    
    # Handle reset (query interrupts order)
    if should_reset and current_mode == ConversationMode.ORDERING:
        logger.info(f"[STATE] Query '{intent}' interrupted order flow - resetting")
        context = {}  # Clear order context
        current_mode = ConversationMode.BROWSING
    
    # Meta intents
    if intent == IntentType.CANCEL:
        return (ConversationMode.IDLE, {})
    
    if intent == IntentType.HELP:
        return (current_mode, context)  # Don't change mode
    
    # Query intents → Browsing mode
    if intent in [IntentType.ASK_STOCK, IntentType.ASK_SYMPTOM, IntentType.ASK_PRICE]:
        # Save product in context if found (for quick ordering)
        if entities.get("product"):
            context["last_query_product"] = entities["product"]
        return (ConversationMode.BROWSING, context)
    
    # Transaction intents
    if intent == IntentType.START_ORDER:
        context.update(entities)
        # If we have product + quantity, skip to confirming
        if context.get("product") and context.get("quantity"):
            return (ConversationMode.CONFIRMING, context)
        return (ConversationMode.ORDERING, context)
    
    if intent == IntentType.PROVIDE_QUANTITY:
        context["quantity"] = entities["quantity"]
        # Use last query product if no product specified
        if not context.get("product") and context.get("last_query_product"):
            context["product"] = context["last_query_product"]
        # Move to confirming if we have product + quantity
        if context.get("product") and context.get("quantity"):
            return (ConversationMode.CONFIRMING, context)
        return (ConversationMode.ORDERING, context)
    
    if intent == IntentType.PROVIDE_CUSTOMER:
        context["customer"] = entities["customer"]
        return (ConversationMode.CONFIRMING, context)
    
    if intent == IntentType.CONFIRM_ORDER:
        if context.get("product") and context.get("quantity"):
            return (ConversationMode.CONFIRMING, context)
        return (current_mode, context)
    
    return (current_mode, context)


# ============================================================================
# RESPONSE HANDLERS
# ============================================================================

async def handle_query_response(
    update, db, business_id: int, intent: str, entities: dict, context: dict
):
    """Handle query intents (non-blocking)"""
    
    if intent == IntentType.ASK_STOCK:
        product = entities.get("product")
        if not product:
            await update.message.reply_text(
                "🔍 Kaun si medicine check karni hai?\n"
                "Example: 'Paracetamol hai kya?'"
            )
            return
        
        item = db.query(Inventory).filter(
            Inventory.business_id == business_id,
            Inventory.item_name.ilike(f"%{product}%")
        ).first()
        
        if item:
            qty = int(item.quantity)
            msg = (
                f"✅ {item.item_name}: {qty} units available\n"
                f"💰 Price: ₹{item.price}\n\n"
            )
            if qty > 0:
                msg += "📝 Order karna hai? Quantity batao (e.g., '10')"
            await update.message.reply_text(msg)
        else:
            # Try symptom search
            symptom_results = map_symptom_to_medicines(db, business_id, product)
            if symptom_results:
                await show_symptom_results(update, product, symptom_results)
            else:
                await update.message.reply_text(
                    f"❌ '{product}' stock mein nahi hai\n\n"
                    "💡 Try: Symptom batao (e.g., 'bukhar hai')"
                )
        return
    
    if intent == IntentType.ASK_SYMPTOM:
        symptom = entities.get("symptom", "")
        results = map_symptom_to_medicines(db, business_id, symptom)
        await show_symptom_results(update, symptom, results)
        return
    
    if intent == IntentType.HELP:
        await update.message.reply_text(
            "👋 Main kya kar sakta hoon:\n\n"
            "📦 Stock Check:\n"
            "   'Paracetamol hai?'\n"
            "   'Dolo available?'\n\n"
            "🔍 Symptom Search:\n"
            "   'bukhar ka medicine'\n"
            "   'fever'\n\n"
            "🛒 Order:\n"
            "   '10 Paracetamol'\n"
            "   'Rahul ko 5 Dolo'\n\n"
            "❌ Cancel: 'cancel' or 'stop'"
        )
        return


async def show_symptom_results(update, symptom: str, results: list):
    """Show symptom search results"""
    if not results:
        await update.message.reply_text(
            f"❌ '{symptom}' ke liye specific medicine nahi mila\n"
            "Medicine name se search karo"
        )
        return
    
    msg = f"🔍 '{symptom}' ke liye ye medicines hain:\n\n"
    for i, med in enumerate(results[:5], 1):
        rx = "🔴 Rx Required" if med["requires_prescription"] else "🟢 OTC"
        msg += f"{i}. {med['name']} {rx}\n"
        msg += f"   Used for: {med['disease']}\n"
        msg += f"   ₹{med['price']} | {int(med['stock'])} units\n\n"
    
    msg += "💬 Medicine name bolke order kar sakte ho"
    await update.message.reply_text(msg)


async def handle_transaction_response(
    update, db, business_id: int, chat_id: int, mode: str, context: dict
):
    """Handle transaction flow responses"""
    
    if mode == ConversationMode.ORDERING:
        if not context.get("product"):
            await update.message.reply_text(
                "📦 Kaun si medicine chahiye?\n"
                "Example: 'Paracetamol' or '10 Dolo'"
            )
            return
        
        if not context.get("quantity"):
            await update.message.reply_text(
                f"🔢 {context['product']} ki kitni quantity?\n"
                "Example: '10', 'ek', 'twenty'"
            )
            return
    
    if mode == ConversationMode.CONFIRMING:
        product = context.get("product")
        quantity = context.get("quantity")
        customer = context.get("customer", "Walk-in Customer")
        
        # Check if product exists
        item = db.query(Inventory).filter(
            Inventory.business_id == business_id,
            Inventory.item_name.ilike(f"%{product}%")
        ).first()
        
        if not item:
            await update.message.reply_text(
                f"❌ '{product}' stock mein nahi hai\n"
                "Koi aur medicine try karo"
            )
            reset_conversation(db, chat_id)
            return
        
        # Show confirmation
        rx_warning = ""
        if item.requires_prescription:
            rx_warning = "\n⚠️ PRESCRIPTION REQUIRED"
        
        await update.message.reply_text(
            f"📋 Order Summary{rx_warning}\n"
            f"━━━━━━━━━━━━━━━━━━\n"
            f"📦 Product: {item.item_name}\n"
            f"🔢 Quantity: {int(quantity)}\n"
            f"👤 Customer: {customer}\n"
            f"💰 Approx: ₹{float(item.price) * quantity:.2f}\n"
            f"━━━━━━━━━━━━━━━━━━\n\n"
            f"✅ 'confirm' - Order banao\n"
            f"❌ 'cancel' - Band karo\n"
            f"✏️ Customer name add/change karna hai to batao"
        )
        return


async def execute_order(update, db, business_id: int, chat_id: int, context: dict):
    """Execute confirmed order"""
    product = context.get("product")
    quantity = context.get("quantity")
    customer = context.get("customer", "Walk-in Customer")
    
    # Find exact item
    item = db.query(Inventory).filter(
        Inventory.business_id == business_id,
        Inventory.item_name.ilike(f"%{product}%")
    ).first()
    
    if not item:
        await update.message.reply_text("❌ Order create nahi ho paya - product not found")
        reset_conversation(db, chat_id)
        return
    
    # Create draft
    draft = validate_and_create_draft(
        db,
        business_id,
        raw_message=f"{customer} wants {int(quantity)} {item.item_name}",
        telegram_chat_id=str(chat_id),
        intent="create_invoice",
        product=item.item_name,
        quantity=quantity,
        customer=customer,
        requires_prescription=item.requires_prescription
    )
    
    if draft:
        payload = draft.payload or {}
        amount = payload.get("amount", 0)
        
        rx_note = ""
        if item.requires_prescription:
            rx_note = "\n⚠️ Owner must verify prescription before approval"
        
        await update.message.reply_text(
            f"✅ Invoice draft created!{rx_note}\n\n"
            f"👤 Customer: {customer}\n"
            f"📦 Product: {item.item_name}\n"
            f"🔢 Quantity: {int(quantity)}\n"
            f"💰 Amount: ₹{amount:.2f}\n\n"
            f"📱 Approve from Owner Dashboard"
        )
    else:
        await update.message.reply_text("❌ Order create nahi ho paya - try again")
    
    # Reset to idle
    reset_conversation(db, chat_id)


# ============================================================================
# MAIN MESSAGE HANDLER
# ============================================================================

async def handle_message_conversational(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    New conversational handler with flexible state management
    """
    if not update.message or not update.message.text:
        return
    
    text = update.message.text.strip()
    chat_id = update.effective_chat.id if update.effective_chat else None
    if chat_id is None:
        return
    
    logger.info(f"[MSG] chat_id={chat_id}, text='{text}'")
    
    db = SessionLocal()
    try:
        # Find business
        business = db.query(Business).filter(
            Business.telegram_chat_id == str(chat_id)
        ).first()
        if not business:
            business = db.query(Business).first()
        if not business:
            await update.message.reply_text(
                "No business linked. Please link Telegram from Owner Dashboard."
            )
            return
        
        # Get current conversation state
        conv_data = get_conversation_data(db, chat_id)
        current_mode = conv_data["mode"]
        current_context = conv_data["context"]
        
        logger.info(f"[STATE] mode={current_mode}, context={current_context}")
        
        # Parse intent (deterministic first)
        intent_result = parse_intent_deterministic(text, current_mode, current_context)
        
        # If low confidence, try LLM
        if intent_result["confidence"] == "low":
            llm_result = parse_message_with_ai(text, context=current_context)
            if llm_result.get("confidence") in ["high", "medium"]:
                intent_result = {
                    "intent": llm_result.get("intent", IntentType.UNKNOWN),
                    "confidence": llm_result["confidence"],
                    "entities": {
                        "product": llm_result.get("product"),
                        "quantity": llm_result.get("quantity"),
                        "customer": llm_result.get("customer")
                    },
                    "should_reset_flow": False
                }
        
        intent = intent_result["intent"]
        entities = intent_result["entities"]
        should_reset = intent_result["should_reset_flow"]
        
        logger.info(f"[INTENT] {intent}, entities={entities}, reset={should_reset}")
        
        # Update conversation state
        new_mode, new_context = update_conversation_state(
            db, chat_id, intent, entities, should_reset,
            current_mode, current_context
        )
        
        # Save new state
        save_conversation_data(db, chat_id, new_mode, new_context)
        
        # Route response
        if intent in [IntentType.ASK_STOCK, IntentType.ASK_SYMPTOM, IntentType.ASK_PRICE, IntentType.HELP]:
            await handle_query_response(update, db, business.id, intent, entities, new_context)
        elif intent == IntentType.CANCEL:
            await update.message.reply_text("✅ Order cancelled. Kya chahiye?")
        elif intent == IntentType.CONFIRM_ORDER and new_mode == ConversationMode.CONFIRMING:
            await execute_order(update, db, business.id, chat_id, new_context)
        elif new_mode in [ConversationMode.ORDERING, ConversationMode.CONFIRMING]:
            await handle_transaction_response(update, db, business.id, chat_id, new_mode, new_context)
        else:
            await update.message.reply_text(
                "🤔 Samajh nahi aaya\n\n"
                "Try:\n"
                "• 'Paracetamol hai?'\n"
                "• 'bukhar ka medicine'\n"
                "• '10 Dolo'\n"
                "• 'help'"
            )
    
    finally:
        db.close()
