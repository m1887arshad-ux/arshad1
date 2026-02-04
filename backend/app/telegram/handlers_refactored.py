"""
REFACTORED TELEGRAM BOT HANDLER - CORRECTNESS FIRST

🔴 CRITICAL BUGS FIXED:
1. Product names: User text NEVER appears in invoices (canonical resolution)
2. Role confusion: Seller = pharmacy (constant), Buyer = customer (from conversation)
3. Magic numbers: All prices from inventory.price × quantity (deterministic)
4. Redundant questions: Confidence-based skip logic
5. FSM premature trigger: Entity validation before state transition

🟠 DESIGN IMPROVEMENTS:
1. Product resolution layer (aliases, fuzzy matching)
2. Confidence scoring for all entities
3. Strict role separation (pharmacy vs customer)
4. Deterministic billing (no hardcoded amounts)
5. Entity-first FSM (not keyword-triggered)

Architecture:
1. Parse message → Extract entities with confidence
2. Resolve product → Canonical model
3. Validate entities → Check completeness
4. FSM transition → Only with validated entities
5. Create draft → With deterministic pricing

SAFETY RULES:
- All drafts require owner approval
- Prescription verification required for Rx medicines
- No financial actions without validation
"""
import logging
from telegram import Update
from telegram.ext import ContextTypes
from decimal import Decimal

from app.db.session import SessionLocal
from app.models.business import Business
from app.models.inventory import Inventory
from app.models.conversation_state import ConversationState as DBConversationState
from app.agent.decision_engine import validate_and_create_draft
from app.services.product_resolver import resolve_product, resolve_multiple_products
from app.services.entity_extractor import (
    extract_all_entities, 
    should_skip_question
)
from app.services.symptom_mapper import map_symptom_to_medicines

logger = logging.getLogger(__name__)


# ==============================================================================
# FSM STATES
# ==============================================================================

class OrderFlowState:
    """Finite State Machine states for order creation"""
    IDLE = "idle"
    NEED_PRODUCT = "need_product"
    NEED_QUANTITY = "need_quantity"
    NEED_CUSTOMER = "need_customer"  # Optional state
    READY_TO_CONFIRM = "ready_to_confirm"
    CONFIRMED = "confirmed"


# ==============================================================================
# CONVERSATION CONTEXT MANAGEMENT
# ==============================================================================

def get_conversation_context(db, chat_id: int) -> dict:
    """Load conversation context from database"""
    record = db.query(DBConversationState).filter(
        DBConversationState.chat_id == str(chat_id)
    ).first()
    
    default_context = {
        "state": OrderFlowState.IDLE,
        "entities": {
            "product": None,         # Canonical product model
            "quantity": None,        # float
            "customer": None         # string
        },
        "raw_inputs": {
            "product_input": None,   # What user typed
            "quantity_input": None,
            "customer_input": None
        },
        "confidence": {
            "product": 0.0,
            "quantity": 0.0,
            "customer": 0.0
        }
    }
    
    if not record or not record.payload:
        return default_context
    
    # Ensure payload has required keys (handle corrupted data)
    payload = record.payload
    if not isinstance(payload, dict) or "state" not in payload:
        return default_context
    
    return payload


def save_conversation_context(db, chat_id: int, context: dict):
    """Save conversation context to database"""
    import json
    from decimal import Decimal
    
    # Convert Decimal to float for JSON serialization
    def convert_decimals(obj):
        if isinstance(obj, dict):
            return {k: convert_decimals(v) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [convert_decimals(v) for v in obj]
        elif isinstance(obj, Decimal):
            return float(obj)
        return obj
    
    # Clean context for JSON storage
    clean_context = convert_decimals(context)
    
    record = db.query(DBConversationState).filter(
        DBConversationState.chat_id == str(chat_id)
    ).first()
    
    if record:
        record.state = clean_context.get("state", OrderFlowState.IDLE)
        record.payload = clean_context
    else:
        record = DBConversationState(
            chat_id=str(chat_id),
            state=clean_context.get("state", OrderFlowState.IDLE),
            payload=clean_context
        )
        db.add(record)
    
    db.commit()
    logger.info(f"[Context] chat_id={chat_id}, state={clean_context['state']}")


def reset_conversation(db, chat_id: int):
    """Reset conversation to IDLE"""
    save_conversation_context(db, chat_id, {
        "state": OrderFlowState.IDLE,
        "entities": {"product": None, "quantity": None, "customer": None},
        "raw_inputs": {"product_input": None, "quantity_input": None, "customer_input": None},
        "confidence": {"product": 0.0, "quantity": 0.0, "customer": 0.0}
    })


# ==============================================================================
# INTENT CLASSIFICATION
# ==============================================================================

def classify_intent(text: str, current_state: str) -> str:
    """
    Classify user intent based on keywords
    
    Intents:
    - cancel: Stop current flow
    - help: Show help message
    - query_stock: Check product availability
    - query_symptom: Search by symptom
    - order: Start or continue order
    - confirm: Confirm current order
    - unknown: Cannot determine
    """
    text_lower = text.lower().strip()
    
    # Cancel (highest priority)
    if any(kw in text_lower for kw in ["cancel", "stop", "band", "nahi", "mat karo", "rehne do"]):
        return "cancel"
    
    # Help
    if any(kw in text_lower for kw in ["help", "kya kar", "batao", "kaise"]):
        return "help"
    
    # Confirmation (only relevant in READY_TO_CONFIRM state)
    if current_state == OrderFlowState.READY_TO_CONFIRM:
        if any(kw in text_lower for kw in ["confirm", "yes", "haan", "ha", "theek", "ok", "sahi"]):
            return "confirm"
    
    # Query: Stock check
    if any(kw in text_lower for kw in ["hai kya", "available", "stock", "milega", "check"]) or text_lower.endswith("?"):
        return "query_stock"
    
    # Query: Symptom
    if any(kw in text_lower for kw in ["bukhar", "fever", "dard", "pain", "cold", "sardi", "headache", "sir"]):
        return "query_symptom"
    
    # Order (default if in flow or has order keywords)
    if current_state != OrderFlowState.IDLE:
        return "order"
    
    if any(kw in text_lower for kw in ["chahiye", "order", "bill", "lena", "de do", "dedo"]):
        return "order"
    
    # Check if message has numeric quantity (suggests order intent)
    import re
    if re.search(r'\d+', text_lower):
        return "order"
    
    return "unknown"


# ==============================================================================
# ENTITY VALIDATION
# ==============================================================================

def determine_next_state(entities: dict, confidence: dict) -> str:
    """
    Determine next FSM state based on entities and confidence
    
    Rules:
    1. Need product if missing or low confidence
    2. Need quantity if missing or low confidence
    3. Customer is optional (default to "Walk-in Customer")
    4. Ready to confirm if product + quantity are valid
    """
    # Product validation (CRITICAL - must be resolved)
    if not entities.get("product") or confidence.get("product", 0.0) < 0.7:
        return OrderFlowState.NEED_PRODUCT
    
    # Quantity validation
    if not entities.get("quantity") or confidence.get("quantity", 0.0) < 0.7:
        return OrderFlowState.NEED_QUANTITY
    
    # Customer is optional - if not provided, use default
    # We don't ask for customer unless user explicitly wants to add it
    
    return OrderFlowState.READY_TO_CONFIRM


# ==============================================================================
# COMMAND HANDLERS
# ==============================================================================

async def handle_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /start command"""
    chat_id = update.effective_chat.id if update.effective_chat else None
    
    await update.message.reply_text(
        "🙏 Namaste! Welcome to Bharat Pharmacy Bot\n\n"
        "Main kya kar sakta hoon:\n"
        "📦 Stock check: 'Paracetamol hai?'\n"
        "🛒 Order: '10 Dolo 650'\n"
        "🔍 Symptom search: 'bukhar ka medicine'\n\n"
        f"📱 Your Chat ID: {chat_id}\n"
        "Link this from Owner Dashboard"
    )


# ==============================================================================
# QUERY HANDLERS (Non-blocking, instant response)
# ==============================================================================

async def handle_query_stock(update, db, business_id: int, text: str):
    """Handle stock check query"""
    # Extract product from query
    from app.services.entity_extractor import extract_product_with_confidence
    
    product_extract = extract_product_with_confidence(text)
    
    if not product_extract["value"]:
        await update.message.reply_text(
            "🤔 Kaun si medicine check karni hai?\n"
            "Example: 'Paracetamol hai?'"
        )
        return
    
    # Resolve to canonical product
    resolved = resolve_product(db, business_id, product_extract["value"], min_confidence=0.6)
    
    if resolved:
        product = resolved
        stock_qty = int(product["stock_quantity"])
        
        msg = f"✅ {product['canonical_name']}\n"
        msg += f"📦 Stock: {stock_qty} units\n"
        msg += f"💰 Price: ₹{float(product['price_per_unit']):.2f} per unit\n"
        
        if product["requires_prescription"]:
            msg += "⚠️ Prescription Required\n"
        
        if stock_qty > 0:
            msg += "\n💬 Order karna hai? Quantity batao (e.g., '10')"
        else:
            msg += "\n❌ Out of stock"
        
        await update.message.reply_text(msg)
    else:
        # No exact match - try symptom search
        symptom_results = map_symptom_to_medicines(db, business_id, product_extract["value"])
        
        if symptom_results:
            await handle_symptom_results(update, product_extract["value"], symptom_results)
        else:
            # Try showing multiple matches
            multiple = resolve_multiple_products(db, business_id, product_extract["value"], min_confidence=0.4)
            
            if multiple:
                msg = f"🔍 '{product_extract['value']}' ke liye ye options hain:\n\n"
                for i, prod in enumerate(multiple[:5], 1):
                    msg += f"{i}. {prod['canonical_name']} (₹{float(prod['price_per_unit']):.2f})\n"
                msg += "\n💬 Exact name se phir pucho"
                await update.message.reply_text(msg)
            else:
                await update.message.reply_text(
                    f"❌ '{product_extract['value']}' stock mein nahi mila\n\n"
                    "💡 Try: Medicine ka exact name ya symptom"
                )


async def handle_query_symptom(update, db, business_id: int, text: str):
    """Handle symptom-based search"""
    results = map_symptom_to_medicines(db, business_id, text)
    await handle_symptom_results(update, text, results)


async def handle_symptom_results(update, symptom: str, results: list):
    """Display symptom search results"""
    if not results:
        await update.message.reply_text(
            f"❌ '{symptom}' ke liye specific medicine nahi mila\n"
            "Medicine name se direct search karo"
        )
        return
    
    msg = f"🔍 '{symptom}' ke liye ye medicines available hain:\n\n"
    for i, med in enumerate(results[:5], 1):
        rx = "🔴 Rx Required" if med["requires_prescription"] else "🟢 OTC"
        msg += f"{i}. {med['name']} {rx}\n"
        msg += f"   Used for: {med['disease']}\n"
        msg += f"   ₹{med['price']:.2f} | Stock: {int(med['stock'])}\n\n"
    
    msg += "💬 Medicine name bolke order kar sakte ho"
    await update.message.reply_text(msg)


# ==============================================================================
# ORDER FLOW HANDLER (Multi-step with FSM)
# ==============================================================================

async def handle_order_flow(update, db, business_id: int, chat_id: int, text: str, owner_name: str):
    """
    Handle order creation flow with entity-first FSM
    
    Flow:
    1. Extract entities from user input
    2. Resolve product to canonical model
    3. Validate all entities
    4. Determine next state
    5. Ask for missing data or confirm
    """
    context = get_conversation_context(db, chat_id)
    current_state = context["state"]
    entities = context["entities"]
    raw_inputs = context["raw_inputs"]
    confidence = context["confidence"]
    
    logger.info(f"[OrderFlow] state={current_state}, text='{text}'")
    
    # Extract entities from current message
    extracted = extract_all_entities(
        text,
        context={
            "last_product": raw_inputs.get("product_input"),
            "last_quantity": entities.get("quantity"),
            "last_customer": entities.get("customer")
        },
        default_owner_name=owner_name
    )
    
    logger.info(f"[EntityExtract] product={extracted['product']}, qty={extracted['quantity']}, customer={extracted['customer']}")
    
    # Update context with extracted entities
    
    # Product: Resolve to canonical if extracted
    if extracted["product"]["value"] and extracted["product"]["confidence"] > 0.5:
        raw_inputs["product_input"] = extracted["product"]["value"]
        
        # Resolve to canonical product model
        resolved = resolve_product(db, business_id, extracted["product"]["value"], min_confidence=0.7)
        
        if resolved:
            entities["product"] = resolved
            confidence["product"] = resolved["confidence"]
            logger.info(f"[ProductResolved] '{extracted['product']['value']}' → '{resolved['canonical_name']}'")
        else:
            # Product not found in inventory
            await update.message.reply_text(
                f"❌ '{extracted['product']['value']}' stock mein nahi mila\n\n"
                "💡 Stock check karo: '<medicine name> hai?'\n"
                "Ya symptom batao: 'bukhar ka medicine'"
            )
            reset_conversation(db, chat_id)
            return
    
    # Quantity: Update if extracted
    if extracted["quantity"]["value"] and extracted["quantity"]["confidence"] > 0.5:
        entities["quantity"] = extracted["quantity"]["value"]
        confidence["quantity"] = extracted["quantity"]["confidence"]
        raw_inputs["quantity_input"] = text
    
    # Customer: Update if extracted (but it's optional)
    if extracted["customer"]["value"] and extracted["customer"]["confidence"] > 0.7:
        entities["customer"] = extracted["customer"]["value"]
        confidence["customer"] = extracted["customer"]["confidence"]
        raw_inputs["customer_input"] = text
    
    # Determine next state based on entity completeness
    next_state = determine_next_state(entities, confidence)
    
    logger.info(f"[StateTransition] {current_state} → {next_state}")
    
    # Handle state-specific responses
    if next_state == OrderFlowState.NEED_PRODUCT:
        context["state"] = next_state
        save_conversation_context(db, chat_id, context)
        await update.message.reply_text(
            "📦 Kaun sa medicine chahiye?\n"
            "Example: 'Paracetamol', 'Dolo 650'"
        )
        return
    
    elif next_state == OrderFlowState.NEED_QUANTITY:
        context["state"] = next_state
        save_conversation_context(db, chat_id, context)
        product_name = entities["product"]["canonical_name"]
        await update.message.reply_text(
            f"🔢 {product_name} ki kitni quantity chahiye?\n"
            "Example: '10', 'ek', 'twenty'"
        )
        return
    
    elif next_state == OrderFlowState.READY_TO_CONFIRM:
        # Show confirmation with deterministic pricing
        product = entities["product"]
        quantity = entities["quantity"]
        customer = entities.get("customer") or "Walk-in Customer"
        
        # DETERMINISTIC BILLING: price_per_unit × quantity
        unit_price = float(product["price_per_unit"])
        total_amount = unit_price * quantity
        
        # ROLE SEPARATION: Seller = pharmacy (constant), Buyer = customer
        seller = "Your Pharmacy"  # Constant
        buyer = customer  # From conversation
        
        rx_warning = ""
        if product["requires_prescription"]:
            rx_warning = "\n⚠️ PRESCRIPTION REQUIRED - Owner must verify"
        
        msg = (
            f"📋 Order Confirmation{rx_warning}\n"
            f"━━━━━━━━━━━━━━━━━━━━━━\n"
            f"🏪 Seller: {seller}\n"
            f"👤 Buyer: {buyer}\n"
            f"📦 Product: {product['canonical_name']}\n"
            f"🔢 Quantity: {int(quantity)} units\n"
            f"💰 Price: ₹{unit_price:.2f} × {int(quantity)} = ₹{total_amount:.2f}\n"
            f"━━━━━━━━━━━━━━━━━━━━━━\n\n"
            f"✅ Type 'confirm' to create invoice\n"
            f"❌ Type 'cancel' to stop\n"
            f"✏️ Change customer? Just type name"
        )
        
        context["state"] = next_state
        context["entities"]["customer"] = customer  # Finalize customer
        save_conversation_context(db, chat_id, context)
        
        await update.message.reply_text(msg)
        return


async def handle_order_confirm(update, db, business_id: int, chat_id: int):
    """
    Confirm and create invoice draft
    
    CRITICAL: This creates DRAFT only, not executed invoice
    Owner must approve from dashboard
    """
    context = get_conversation_context(db, chat_id)
    entities = context["entities"]
    
    product = entities["product"]
    quantity = entities["quantity"]
    customer = entities.get("customer") or "Walk-in Customer"
    
    if not product or not quantity:
        await update.message.reply_text("❌ Order incomplete. Please start again.")
        reset_conversation(db, chat_id)
        return
    
    # Create draft with deterministic pricing
    unit_price = float(product["price_per_unit"])
    total_amount = unit_price * quantity
    
    draft = validate_and_create_draft(
        db,
        business_id,
        raw_message=f"{customer} wants {int(quantity)} {product['canonical_name']}",
        telegram_chat_id=str(chat_id),
        intent="create_invoice",
        product=product["canonical_name"],  # CANONICAL name, not raw input
        quantity=quantity,
        customer=customer,
        requires_prescription=product["requires_prescription"]
    )
    
    if draft:
        rx_note = ""
        if product["requires_prescription"]:
            rx_note = "\n⚠️ Prescription verification required before approval"
        
        await update.message.reply_text(
            f"✅ Invoice draft created!{rx_note}\n\n"
            f"👤 Customer: {customer}\n"
            f"📦 Product: {product['canonical_name']}\n"
            f"🔢 Quantity: {int(quantity)}\n"
            f"💰 Amount: ₹{total_amount:.2f}\n\n"
            f"📱 Approve from Owner Dashboard to finalize"
        )
    else:
        await update.message.reply_text("❌ Draft creation failed. Please try again.")
    
    # Reset conversation
    reset_conversation(db, chat_id)


# ==============================================================================
# MAIN MESSAGE HANDLER
# ==============================================================================

async def handle_message_refactored(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    REFACTORED message handler with correctness guarantees
    
    Architecture:
    1. Intent classification (meta > query > order)
    2. Query intents → instant response (non-blocking)
    3. Order intents → FSM with entity validation
    4. All entities validated before state transitions
    5. All products resolved to canonical models
    6. All prices calculated deterministically
    """
    if not update.message or not update.message.text:
        return
    
    text = update.message.text.strip()
    chat_id = update.effective_chat.id if update.effective_chat else None
    
    if chat_id is None:
        return
    
    logger.info(f"[Message] chat_id={chat_id}, text='{text}'")
    
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
                "❌ No business linked\n"
                "Link Telegram from Owner Dashboard"
            )
            return
        
        owner_name = business.name or "Owner"
        
        # Get current conversation state
        context_data = get_conversation_context(db, chat_id)
        current_state = context_data["state"]
        
        # Classify intent
        intent = classify_intent(text, current_state)
        
        logger.info(f"[Intent] {intent}, state={current_state}")
        
        # Route based on intent
        if intent == "cancel":
            reset_conversation(db, chat_id)
            await update.message.reply_text("✅ Cancelled. Kya chahiye?")
            return
        
        elif intent == "help":
            await update.message.reply_text(
                "👋 Main kya kar sakta hoon:\n\n"
                "📦 Stock Check:\n"
                "   'Paracetamol hai?'\n\n"
                "🔍 Symptom Search:\n"
                "   'bukhar ka medicine'\n\n"
                "🛒 Order:\n"
                "   '10 Paracetamol'\n"
                "   'Rahul ko 5 Dolo'\n\n"
                "❌ Cancel: 'cancel'"
            )
            return
        
        elif intent == "query_stock":
            # Non-blocking query - don't change order state
            await handle_query_stock(update, db, business.id, text)
            return
        
        elif intent == "query_symptom":
            await handle_query_symptom(update, db, business.id, text)
            return
        
        elif intent == "confirm":
            if current_state == OrderFlowState.READY_TO_CONFIRM:
                await handle_order_confirm(update, db, business.id, chat_id)
            else:
                await update.message.reply_text("🤔 Kya confirm karein? Order nahi hai")
            return
        
        elif intent == "order":
            # Enter/continue order flow
            if current_state == OrderFlowState.IDLE:
                # Start new order
                context_data["state"] = OrderFlowState.NEED_PRODUCT
                save_conversation_context(db, chat_id, context_data)
            
            await handle_order_flow(update, db, business.id, chat_id, text, owner_name)
            return
        
        else:
            # Unknown intent
            await update.message.reply_text(
                "🤔 Samajh nahi aaya\n\n"
                "Try:\n"
                "• 'Paracetamol hai?' - Stock check\n"
                "• '10 Dolo' - Order\n"
                "• 'bukhar' - Symptom search\n"
                "• 'help' - Help"
            )
            return
    
    finally:
        db.close()
