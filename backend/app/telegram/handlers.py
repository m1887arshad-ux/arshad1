"""
Telegram message handler with Finite State Machine (FSM) for multi-step flows.
FSM runs BEFORE AI/Groq - AI only helps extract intent, never manages state.
NO EXECUTION FROM TELEGRAM. NO AUTONOMY.
"""
import logging
import re
from typing import Dict, Optional, Tuple
from telegram import Update
from telegram.ext import ContextTypes

from app.db.session import SessionLocal
from app.models.business import Business
from app.models.inventory import Inventory
from app.agent.decision_engine import validate_and_create_draft
from app.agent.intent_parser import parse_message
from ai.intent_parser import parse_message_with_ai

logger = logging.getLogger(__name__)


# ==============================================================================
# COMMAND HANDLERS
# ==============================================================================

async def handle_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /start command - Link Telegram to business."""
    chat_id = update.effective_chat.id if update.effective_chat else None
    
    await update.message.reply_text(
        "🙏 Namaste! Welcome to Bharat Biz-Agent\n\n"
        "I help you manage your pharmacy business.\n\n"
        "Try:\n"
        "• 'Paracetamol hai?' - Check stock\n"
        "• 'Rahul ko 10 Dolo 650' - Create invoice\n\n"
        f"📱 Your Chat ID: {chat_id}\n"
        "Add this to Owner Dashboard to link Telegram."
    )

# ==============================================================================
# FINITE STATE MACHINE (FSM) FOR MULTI-STEP FLOWS
# ==============================================================================

# FSM States for invoice creation
class InvoiceFlowStep:
    IDLE = "idle"
    AWAIT_PRODUCT = "await_product"
    AWAIT_QUANTITY = "await_quantity"
    AWAIT_CUSTOMER = "await_customer"
    AWAIT_CONFIRMATION = "await_confirmation"
    LOCKED = "locked"  # Terminal state after confirmation

# Per-chat FSM state storage
# Structure: {chat_id: {flow, step, data, locked}}
FSM_STATE: Dict[int, dict] = {}


def get_fsm_state(chat_id: int) -> dict:
    """Get or initialize FSM state for a chat."""
    if chat_id not in FSM_STATE:
        FSM_STATE[chat_id] = {
            "flow": None,  # Current flow: "create_invoice" or None
            "step": InvoiceFlowStep.IDLE,
            "data": {
                "product": None,
                "quantity": None,
                "customer": None,
            },
            "locked": False,
        }
    return FSM_STATE[chat_id]


def reset_fsm_state(chat_id: int) -> None:
    """Clear FSM state after flow completion or cancellation."""
    FSM_STATE[chat_id] = {
        "flow": None,
        "step": InvoiceFlowStep.IDLE,
        "data": {"product": None, "quantity": None, "customer": None},
        "locked": False,
    }
    logger.info(f"[FSM] Reset state for chat_id={chat_id}")


def start_invoice_flow(chat_id: int, product: str = None, quantity: float = None, customer: str = None) -> None:
    """Start invoice creation flow with any known data."""
    state = get_fsm_state(chat_id)
    state["flow"] = "create_invoice"
    state["locked"] = False
    
    # Set known data
    if product:
        state["data"]["product"] = product
    if quantity:
        state["data"]["quantity"] = quantity
    if customer:
        state["data"]["customer"] = customer
    
    # Determine next step based on what's missing
    state["step"] = determine_next_step(state["data"])
    logger.info(f"[FSM] Started invoice flow for chat_id={chat_id}, step={state['step']}, data={state['data']}")


def determine_next_step(data: dict) -> str:
    """Determine next step based on what data is missing."""
    if not data.get("product"):
        return InvoiceFlowStep.AWAIT_PRODUCT
    if not data.get("quantity"):
        return InvoiceFlowStep.AWAIT_QUANTITY
    if not data.get("customer"):
        return InvoiceFlowStep.AWAIT_CUSTOMER
    return InvoiceFlowStep.AWAIT_CONFIRMATION


# ==============================================================================
# NATURAL LANGUAGE PARSERS FOR FSM INPUTS
# ==============================================================================

def parse_quantity_from_text(text: str) -> Optional[float]:
    """Parse quantity from natural language.
    
    Handles:
    - "10" → 10
    - "only one" → 1
    - "ek" → 1
    - "do" → 2
    - "teen" → 3
    - "100 units" → 100
    """
    text = text.lower().strip()
    
    # Hindi number words
    hindi_numbers = {
        "ek": 1, "one": 1, "only one": 1, "sirf ek": 1,
        "do": 2, "two": 2,
        "teen": 3, "three": 3,
        "char": 4, "four": 4,
        "paanch": 5, "panch": 5, "five": 5,
        "chhe": 6, "six": 6,
        "saat": 7, "seven": 7,
        "aath": 8, "eight": 8,
        "nau": 9, "nine": 9,
        "das": 10, "ten": 10,
        "bees": 20, "twenty": 20,
        "pachas": 50, "fifty": 50,
        "sau": 100, "hundred": 100,
    }
    
    # Check exact matches first
    if text in hindi_numbers:
        return float(hindi_numbers[text])
    
    # Check partial matches
    for word, num in hindi_numbers.items():
        if word in text:
            return float(num)
    
    # Extract numeric value
    match = re.search(r'(\d+(?:\.\d+)?)', text)
    if match:
        return float(match.group(1))
    
    return None


def parse_customer_from_text(text: str, owner_name: str = "Owner") -> Optional[str]:
    """Parse customer name from natural language.
    
    Handles:
    - "mujhe" → owner_name
    - "mere liye" → owner_name
    - "Rahul" → "Rahul"
    - "ramesh ko" → "Ramesh"
    """
    text = text.lower().strip()
    
    # Self-references
    self_words = ["mujhe", "mere liye", "mera", "apne liye", "khud", "myself", "me"]
    for word in self_words:
        if word in text:
            return owner_name
    
    # Extract capitalized name or name before "ko"
    ko_match = re.search(r'(\w+)\s*ko', text, re.IGNORECASE)
    if ko_match:
        return ko_match.group(1).capitalize()
    
    # If it's just a name (single word, no special chars)
    if re.match(r'^[a-zA-Z]+$', text):
        return text.capitalize()
    
    return None


def parse_product_from_text(text: str) -> Optional[str]:
    """Extract product name from text."""
    text = text.strip()
    
    # Remove common filler words
    fillers = ["ka", "ki", "ke", "hai", "chahiye", "dedo", "dena", "do", "lo", "order"]
    words = text.split()
    filtered = [w for w in words if w.lower() not in fillers]
    
    if filtered:
        return " ".join(filtered).strip()
    
    return text if len(text) > 1 else None


def is_confirmation(text: str) -> bool:
    """Check if text is a confirmation."""
    confirmations = [
        "confirm", "yes", "haan", "han", "ha", "theek", "thik", 
        "ok", "okay", "done", "kar do", "kardo", "bana do", "banado",
        "proceed", "approved", "approve"
    ]
    return text.lower().strip() in confirmations


def is_cancellation(text: str) -> bool:
    """Check if text is a cancellation."""
    cancellations = [
        "cancel", "nahi", "no", "na", "mat", "stop", "ruk", 
        "band", "abort", "exit", "quit", "chhod", "rehne do"
    ]
    return text.lower().strip() in cancellations


# ==============================================================================
# FSM HANDLER - RUNS BEFORE AI
# ==============================================================================

def handle_fsm(chat_id: int, text: str, owner_name: str = "Owner") -> Tuple[bool, Optional[str], Optional[dict]]:
    """
    Handle FSM state transitions BEFORE AI processing.
    
    Returns:
        (handled, action, data)
        - handled: True if FSM consumed this message
        - action: "reply" | "create_invoice" | None
        - data: Response message or invoice data
    """
    state = get_fsm_state(chat_id)
    
    # If not in a flow, don't handle
    if state["flow"] is None or state["step"] == InvoiceFlowStep.IDLE:
        return (False, None, None)
    
    # If locked (just completed), reset and don't handle
    if state["locked"]:
        reset_fsm_state(chat_id)
        return (False, None, None)
    
    logger.info(f"[FSM] Processing: chat_id={chat_id}, step={state['step']}, text='{text}'")
    
    # Handle cancellation at any step
    if is_cancellation(text):
        reset_fsm_state(chat_id)
        return (True, "reply", {"message": "❌ Invoice cancelled."})
    
    # Handle based on current step
    step = state["step"]
    
    if step == InvoiceFlowStep.AWAIT_PRODUCT:
        product = parse_product_from_text(text)
        if product:
            state["data"]["product"] = product
            state["step"] = determine_next_step(state["data"])
            
            if state["step"] == InvoiceFlowStep.AWAIT_QUANTITY:
                return (True, "reply", {"message": f"✅ Product: {product}\n\n🔢 Kitni quantity chahiye?"})
            elif state["step"] == InvoiceFlowStep.AWAIT_CUSTOMER:
                return (True, "reply", {"message": f"✅ Product: {product}\n\n👤 Kis customer ke liye?"})
            else:
                return show_confirmation(chat_id, state)
        else:
            return (True, "reply", {"message": "🤔 Product ka naam batao (e.g., Paracetamol, Dolo 650)"})
    
    elif step == InvoiceFlowStep.AWAIT_QUANTITY:
        quantity = parse_quantity_from_text(text)
        if quantity:
            # Validate
            if quantity <= 0:
                return (True, "reply", {"message": "❌ Quantity 0 se zyada honi chahiye"})
            if quantity > 10000:
                return (True, "reply", {"message": "❌ Quantity bahut zyada hai (max 10000)"})
            
            state["data"]["quantity"] = quantity
            state["step"] = determine_next_step(state["data"])
            
            if state["step"] == InvoiceFlowStep.AWAIT_CUSTOMER:
                return (True, "reply", {"message": f"✅ Quantity: {int(quantity)}\n\n👤 Kis customer ke liye?"})
            else:
                return show_confirmation(chat_id, state)
        else:
            return (True, "reply", {"message": "🤔 Quantity samajh nahi aayi. Number batao (e.g., 10, ek, do)"})
    
    elif step == InvoiceFlowStep.AWAIT_CUSTOMER:
        customer = parse_customer_from_text(text, owner_name)
        if customer:
            state["data"]["customer"] = customer
            state["step"] = InvoiceFlowStep.AWAIT_CONFIRMATION
            return show_confirmation(chat_id, state)
        else:
            return (True, "reply", {"message": "🤔 Customer ka naam batao (e.g., Rahul, mujhe)"})
    
    elif step == InvoiceFlowStep.AWAIT_CONFIRMATION:
        if is_confirmation(text):
            # LOCK the flow and return create_invoice action
            state["locked"] = True
            data = state["data"].copy()
            logger.info(f"[FSM] Invoice confirmed: {data}")
            return (True, "create_invoice", data)
        else:
            # Maybe they're providing more info - try to parse
            quantity = parse_quantity_from_text(text)
            if quantity and quantity != state["data"]["quantity"]:
                state["data"]["quantity"] = quantity
                return show_confirmation(chat_id, state)
            
            customer = parse_customer_from_text(text, owner_name)
            if customer and customer != state["data"]["customer"]:
                state["data"]["customer"] = customer
                return show_confirmation(chat_id, state)
            
            # Unknown input during confirmation
            return (True, "reply", {
                "message": "🤔 'confirm' bolke invoice banao ya 'cancel' bolke band karo."
            })
    
    return (False, None, None)


def show_confirmation(chat_id: int, state: dict) -> Tuple[bool, str, dict]:
    """Show confirmation summary."""
    data = state["data"]
    state["step"] = InvoiceFlowStep.AWAIT_CONFIRMATION
    
    message = (
        f"📋 Invoice Summary\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"👤 Customer: {data['customer']}\n"
        f"📦 Product: {data['product']}\n"
        f"🔢 Quantity: {int(data['quantity'])}\n"
        f"━━━━━━━━━━━━━━━━━━\n\n"
        f"✅ 'confirm' - Invoice banao\n"
        f"❌ 'cancel' - Band karo"
    )
    return (True, "reply", {"message": message})


# ==============================================================================
# MAIN MESSAGE HANDLER
# ==============================================================================

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Main message handler with FSM-first architecture.
    
    Flow:
    1. FSM check (handles multi-step flows)
    2. If not in flow: AI parsing for intent
    3. Route based on intent
    """
    if not update.message or not update.message.text:
        return
    
    text = update.message.text.strip()
    chat_id = update.effective_chat.id if update.effective_chat else None
    if chat_id is None:
        return

    logger.info(f"[Incoming] chat_id={chat_id}, text='{text}'")
    
    db = SessionLocal()
    try:
        # Find business linked to this Telegram chat
        business = db.query(Business).filter(Business.telegram_chat_id == str(chat_id)).first()
        if not business:
            business = db.query(Business).first()
        if not business:
            await update.message.reply_text(
                "No business linked. Please link Telegram from Owner Dashboard."
            )
            return
        
        owner_name = business.name or "Owner"
        
        # ==================================================================
        # STEP 1: FSM FIRST - Handle multi-step flows
        # ==================================================================
        handled, action, data = handle_fsm(chat_id, text, owner_name)
        
        if handled:
            if action == "reply":
                await update.message.reply_text(data["message"])
                return
            elif action == "create_invoice":
                # Create the actual invoice draft
                product = data["product"]
                customer = data["customer"]
                quantity = data["quantity"]
                
                # FIXED: Pass explicit parameters instead of building a text string
                draft = validate_and_create_draft(
                    db, 
                    business.id, 
                    raw_message=f"{customer} wants {int(quantity)} {product}",
                    telegram_chat_id=str(chat_id),
                    intent="create_invoice",
                    product=product,
                    quantity=quantity,
                    customer=customer
                )
                
                if draft:
                    payload = draft.payload or {}
                    amount = payload.get("amount", 0)
                    await update.message.reply_text(
                        f"✅ Invoice draft created!\n\n"
                        f"👤 Customer: {customer}\n"
                        f"📦 Product: {product}\n"
                        f"🔢 Quantity: {int(quantity)}\n"
                        f"💰 Amount: ₹{amount:.2f}\n\n"
                        f"📱 Approve from Owner Dashboard."
                    )
                else:
                    await update.message.reply_text("❌ Invoice create nahi ho paya. Dobara try karo.")
                
                # Reset FSM after completion
                reset_fsm_state(chat_id)
                return
        
        # ==================================================================
        # STEP 2: AI PARSING - Only if not in FSM flow
        # ==================================================================
        fsm_state = get_fsm_state(chat_id)
        fsm_data = fsm_state.get("data", {})
        
        # FIXED: Map FSM data keys to prompt context keys
        ai_context = {}
        if fsm_data.get("product"):
            ai_context["last_product"] = fsm_data["product"]
        if fsm_data.get("customer"):
            ai_context["last_customer"] = fsm_data["customer"]
        if fsm_data.get("quantity"):
            ai_context["last_quantity"] = fsm_data["quantity"]
            
        groq_result = parse_message_with_ai(text, context=ai_context)
        logger.info(f"[Groq] result={groq_result}")
        
        intent = groq_result.get("intent", "unknown")
        product = groq_result.get("product")
        customer = groq_result.get("customer")
        quantity = groq_result.get("quantity")
        confidence = groq_result.get("confidence", "low")
        
        # ==================================================================
        # STEP 3: ROUTE BASED ON INTENT
        # ==================================================================
        
        # Stock check - instant response
        if intent == "check_stock":
            if product:
                item = db.query(Inventory).filter(
                    Inventory.business_id == business.id,
                    Inventory.item_name.ilike(f"%{product}%")
                ).first()
                
                if not item:
                    await update.message.reply_text(f"❌ {product} stock mein nahi hai")
                else:
                    qty = float(item.quantity)
                    if qty == 0:
                        await update.message.reply_text(f"❌ {item.item_name} stock khatam!")
                    elif qty < 20:
                        await update.message.reply_text(f"⚠️ {item.item_name} kam hai: {int(qty)} units")
                    else:
                        await update.message.reply_text(f"✅ {item.item_name}: {int(qty)} units available")
            else:
                await update.message.reply_text("🤔 Kaun si medicine check karni hai?")
            return
        
        # Invoice creation - start FSM flow
        if intent == "create_invoice":
            # Start FSM with whatever data we have
            start_invoice_flow(chat_id, product=product, quantity=quantity, customer=customer)
            
            fsm_state = get_fsm_state(chat_id)
            step = fsm_state["step"]
            
            if step == InvoiceFlowStep.AWAIT_PRODUCT:
                await update.message.reply_text("📦 Kaun sa product?")
            elif step == InvoiceFlowStep.AWAIT_QUANTITY:
                await update.message.reply_text(f"🔢 {product} ki kitni quantity?")
            elif step == InvoiceFlowStep.AWAIT_CUSTOMER:
                await update.message.reply_text(f"👤 {product} x {int(quantity)} - kis customer ke liye?")
            elif step == InvoiceFlowStep.AWAIT_CONFIRMATION:
                _, _, resp = show_confirmation(chat_id, fsm_state)
                await update.message.reply_text(resp["message"])
            return
        
        # Unknown intent - try keyword fallback
        parsed = parse_message(text)
        if parsed and parsed.intent == "check_stock":
            item_name = parsed.payload.get("item_name", "")
            item = db.query(Inventory).filter(
                Inventory.business_id == business.id,
                Inventory.item_name.ilike(f"%{item_name}%")
            ).first()
            
            if item:
                qty = float(item.quantity)
                await update.message.reply_text(f"✅ {item.item_name}: {int(qty)} units")
            else:
                await update.message.reply_text(f"❌ {item_name} nahi mila")
            return
        
        # Fallback - helpful message
        await update.message.reply_text(
            "🤔 Samajh nahi aaya.\n\n"
            "Try:\n"
            "• 'Paracetamol hai?'\n"
            "• 'Rahul ko 10 Dolo 650'"
        )
        
    finally:
        db.close()
