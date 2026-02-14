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
from app.telegram.utils import get_business_by_telegram_id
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
    
    # CRITICAL: Validate product_id is preserved
    product_entity = clean_context.get("entities", {}).get("product")
    if product_entity and isinstance(product_entity, dict):
        if "product_id" not in product_entity or product_entity["product_id"] is None:
            logger.error(
                f"[SaveContext] CRITICAL: product_id missing from product entity! "
                f"Product: {product_entity.get('canonical_name', 'Unknown')}"
            )
        else:
            logger.info(
                f"[SaveContext] Saving product_id={product_entity['product_id']} "
                f"({product_entity.get('canonical_name', 'Unknown')})"
            )
    
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
    
    # Cancel (highest priority — allowed even mid-flow)
    if any(kw in text_lower for kw in ["cancel", "stop", "band", "mat karo", "rehne do"]):
        return "cancel"
    
    # ===================================================================
    # MID-FLOW FAST PATH: If user is in an active order step,
    # route directly to "order" handler WITHOUT keyword matching.
    # This prevents customer names like "Rahul" from being parsed
    # as stock queries, symptom searches, etc.
    # Only "cancel" is checked above as a valid escape hatch.
    # ===================================================================
    if current_state in (
        OrderFlowState.NEED_PRODUCT,
        OrderFlowState.NEED_QUANTITY,
        OrderFlowState.NEED_CUSTOMER,
    ):
        return "order"
    
    # Confirmation (only relevant in READY_TO_CONFIRM state)
    if current_state == OrderFlowState.READY_TO_CONFIRM:
        if any(kw in text_lower for kw in ["confirm", "yes", "haan", "ha", "theek", "ok", "sahi"]):
            return "confirm"
        # Allow cancel keyword "nahi" only in confirmation state
        if "nahi" in text_lower:
            return "cancel"
        # Any other input in confirm state → treat as order correction
        return "order"
    
    # === Below only runs when state == IDLE ===
    
    # Help
    if any(kw in text_lower for kw in ["help", "kya kar", "kaise"]):
        return "help"
    
    # Query: Stock check
    if any(kw in text_lower for kw in ["hai kya", "available", "stock", "milega", "check"]) or text_lower.endswith("?"):
        return "query_stock"
    
    # Query: Symptom
    if any(kw in text_lower for kw in ["bukhar", "fever", "dard", "pain", "cold", "sardi", "headache", "sir dard"]):
        return "query_symptom"
    
    # Order keywords
    if any(kw in text_lower for kw in ["chahiye", "order", "bill", "lena", "de do", "dedo", "batao"]):
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
    3. Need customer name (MANDATORY for invoice generation)
    4. Ready to confirm if product + quantity + customer are valid
    """
    # Product validation (CRITICAL - must be resolved)
    if not entities.get("product") or confidence.get("product", 0.0) < 0.7:
        return OrderFlowState.NEED_PRODUCT
    
    # Quantity validation
    if not entities.get("quantity") or confidence.get("quantity", 0.0) < 0.7:
        return OrderFlowState.NEED_QUANTITY
    
    # Customer validation (MANDATORY for proper invoice generation)
    if not entities.get("customer") or not entities.get("customer").strip():
        return OrderFlowState.NEED_CUSTOMER
    
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
    
    # Resolve to canonical product (use same threshold as order creation)
    resolved = resolve_product(db, business_id, product_extract["value"], min_confidence=0.7)
    
    if resolved:
        product = resolved
        stock_qty = int(product["stock_quantity"])
        
        msg = f"✅ {product['canonical_name']}\n"
        msg += f"   (ID: #{product['product_id']})\n"
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
    
    # STATE-AWARE ENTITY EXTRACTION
    # When FSM is waiting for specific input, treat it as such WITHOUT re-parsing
    # This prevents "Rahul" from being interpreted as a medicine name
    
    if current_state == OrderFlowState.NEED_CUSTOMER:
        # In NEED_CUSTOMER state, treat ANY input as customer name
        # Do NOT try to extract product/quantity from this input
        logger.info(f"[FSM] NEED_CUSTOMER state - accepting '{text}' as customer name")
        entities["customer"] = text.strip()
        confidence["customer"] = 1.0  # High confidence since we explicitly asked for it
        raw_inputs["customer_input"] = text
        
        # Determine next state (should be READY_TO_CONFIRM since we have all data)
        next_state = determine_next_state(entities, confidence)
        logger.info(f"[StateTransition] {current_state} → {next_state}")
        
        # Skip to confirmation preparation
        context["state"] = next_state
        context["entities"]["customer"] = entities["customer"]
        save_conversation_context(db, chat_id, context)
        
        # Jump to confirmation display (handled below in next_state routing)
        # Continue to the state-specific response section
    
    elif current_state == OrderFlowState.NEED_QUANTITY:
        # In NEED_QUANTITY state, extract ONLY quantity, ignore product/customer
        from app.services.entity_extractor import extract_quantity_with_confidence
        qty_extract = extract_quantity_with_confidence(text)
        
        if qty_extract["value"] and qty_extract["confidence"] > 0.5:
            entities["quantity"] = qty_extract["value"]
            confidence["quantity"] = qty_extract["confidence"]
            raw_inputs["quantity_input"] = text
            logger.info(f"[FSM] NEED_QUANTITY state - extracted quantity={qty_extract['value']}")
        else:
            # Quantity not understood
            await update.message.reply_text(
                "🤔 Quantity samajh nahi aayi\n"
                "Please provide a number: '10', '5', 'ek', 'do'"
            )
            return
        
        next_state = determine_next_state(entities, confidence)
        logger.info(f"[StateTransition] {current_state} → {next_state}")
    
    else:
        # For IDLE or NEED_PRODUCT states, do full entity extraction
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
                # CRITICAL: Validate product_id is present
                if "product_id" not in resolved or resolved["product_id"] is None:
                    logger.error(
                        f"[ProductResolved] CRITICAL: resolve_product returned no product_id! "
                        f"Input: '{extracted['product']['value']}', Result: {resolved}"
                    )
                    await update.message.reply_text(
                        f"❌ System error resolving '{extracted['product']['value']}'. Please try again."
                    )
                    reset_conversation(db, chat_id)
                    return
                
                entities["product"] = resolved
                confidence["product"] = resolved["confidence"]
                logger.info(
                    f"[ProductResolved] '{extracted['product']['value']}' → "
                    f"'{resolved['canonical_name']}' (product_id={resolved['product_id']})"
                )
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
    
    elif next_state == OrderFlowState.NEED_CUSTOMER:
        # Ask for customer name (MANDATORY)
        # CRITICAL: Save state BEFORE asking — so next message knows we expect customer name
        context["state"] = next_state
        save_conversation_context(db, chat_id, context)
        product_name = entities["product"]["canonical_name"]
        quantity = entities["quantity"]
        await update.message.reply_text(
            f"👤 {product_name} x {int(quantity)} - Kis customer ke liye?\n"
            "Example: 'Rahul', 'Priya', 'mujhe' (for yourself)"
        )
        return
    
    elif next_state == OrderFlowState.READY_TO_CONFIRM:
        # Show confirmation with deterministic pricing
        product = entities["product"]
        quantity = entities["quantity"]
        customer = entities.get("customer")
        
        # Validate customer is present
        if not customer or not customer.strip():
            await update.message.reply_text("❌ Customer name required. Please provide customer name.")
            context["state"] = OrderFlowState.NEED_CUSTOMER
            save_conversation_context(db, chat_id, context)
            return
        
        # VALIDATION: Ensure product_id is present before confirmation
        if not isinstance(product, dict) or "product_id" not in product or product.get("product_id") is None:
            logger.error(
                f"[Confirmation] CRITICAL: product entity invalid before confirmation! "
                f"Product: {product}"
            )
            await update.message.reply_text(
                "❌ Product information corrupted. Please start over."
            )
            reset_conversation(db, chat_id)
            return
        
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
            f"   (ID: #{product['product_id']})\n"
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
    customer = entities.get("customer")
    
    # Validate all required fields
    if not product or not quantity or not customer or not customer.strip():
        await update.message.reply_text(
            "❌ Order incomplete. Missing required information.\n"
            "Please start again with: product, quantity, and customer name."
        )
        reset_conversation(db, chat_id)
        return
    
    # CRITICAL: Validate product_id exists
    product_id = product.get("product_id") if isinstance(product, dict) else None
    canonical_name = product.get("canonical_name") if isinstance(product, dict) else str(product)
    
    if not product_id:
        logger.error(
            f"[OrderConfirm] CRITICAL: product_id is missing! "
            f"Product entity: {product}"
        )
        # Attempt recovery: re-resolve product from canonical name with SAME threshold
        from app.services.product_resolver import resolve_product
        resolved = resolve_product(db, business_id, canonical_name, min_confidence=0.7)
        if resolved:
            product_id = resolved["product_id"]
            canonical_name = resolved["canonical_name"]
            logger.info(f"[OrderConfirm] Recovered product_id={product_id} ({canonical_name})")
        else:
            await update.message.reply_text(
                f"❌ Product '{canonical_name}' not found in inventory. Please start again."
            )
            reset_conversation(db, chat_id)
            return
    
    # Get price from database to ensure it's current
    from app.models.inventory import Inventory
    item = db.query(Inventory).filter(
        Inventory.id == product_id,
        Inventory.business_id == business_id
    ).first()
    
    if not item:
        logger.error(
            f"[OrderConfirm] CRITICAL: product_id={product_id} not found in database!"
        )
        await update.message.reply_text("❌ Product no longer exists. Please start again.")
        reset_conversation(db, chat_id)
        return
    
    # Use database values (source of truth)
    unit_price = float(item.price)
    total_amount = unit_price * quantity
    final_product_name = item.item_name  # Always use DB name
    
    logger.info(
        f"[OrderConfirm] Creating draft: product_id={product_id}, "
        f"name='{final_product_name}', qty={quantity}, amount={total_amount:.2f}"
    )
    
    draft = validate_and_create_draft(
        db,
        business_id,
        raw_message=f"{customer} wants {int(quantity)} {final_product_name}",
        telegram_chat_id=str(chat_id),
        intent="create_invoice",
        product=final_product_name,         # ALWAYS use DB name
        product_id=product_id,              # CRITICAL: Pass resolved ID
        quantity=quantity,
        customer=customer,
        requires_prescription=item.requires_prescription
    )
    
    if draft:
        rx_note = ""
        if item.requires_prescription:
            rx_note = "\n⚠️ Prescription verification required before approval"
        
        await update.message.reply_text(
            f"✅ Invoice draft created!{rx_note}\n\n"
            f"👤 Customer: {customer}\n"
            f"📦 Product: {final_product_name}\n"
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
        # Resolve business using deterministic helper with fallback
        business = get_business_by_telegram_id(db, chat_id)
        
        if not business:
            await update.message.reply_text(
                "❌ No business found\n\n"
                "Please complete business setup in the Owner Dashboard first.\n\n"
                f"💡 Your Chat ID: {chat_id}\n"
                "You can add this to your dashboard to enable explicit linking."
            )
            logger.error(
                f"[Message] Rejected: No business found for chat_id={chat_id}"
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
