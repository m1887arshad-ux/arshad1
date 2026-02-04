# Bot Architecture Redesign: From Rigid FSM to Conversational Agent

## PROBLEM DIAGNOSIS

### Current Architecture Issues

```
CURRENT FLOW (BROKEN):
User: "Paracetamol hai?"
Bot: [check_stock] → "50 units available"

User: "bukhar?"  ← NEW QUESTION
Bot: [FSM ACTIVE? NO] → [LLM: "unknown"] → "Samajh nahi aaya"
                        ↑ WRONG! Should search fever medicines

PROBLEM: Linear FSM blocks natural conversation
```

**Root Causes:**
1. **Rigid State Machine**: Once in order flow, all inputs treated as flow inputs
2. **No Intent Hierarchy**: "ask" vs "transact" treated equally
3. **Mandatory Customer**: Flow forces customer name collection
4. **No Interruption Handling**: Cannot ask questions mid-order
5. **Keyword Matching Fallback**: Fails on symptoms/variations

## SOLUTION: LAYERED INTENT ARCHITECTURE

### New Conversation States

```python
class ConversationMode:
    IDLE = "idle"           # No active context
    BROWSING = "browsing"   # Exploring products/symptoms
    ORDERING = "ordering"   # Building order (product + qty)
    CONFIRMING = "confirming" # Ready to create draft
```

### Intent Hierarchy (Priority Order)

```
LAYER 1: META INTENTS (Highest Priority)
├── CANCEL ("cancel", "stop", "nahi chahiye")
├── HELP ("help", "kya kar sakta hai")
└── GREET ("hi", "hello", "namaste")

LAYER 2: QUERY INTENTS (Override Order Flow)
├── ASK_STOCK ("hai kya", "available", "check")
├── ASK_SYMPTOM ("bukhar", "fever", "dard", "pain")
├── ASK_PRICE ("kitne ka", "price", "cost")
└── ASK_INFO ("kya hai", "batao", "?")

LAYER 3: TRANSACTION INTENTS
├── START_ORDER ("chahiye", "order", "bill")
├── PROVIDE_QUANTITY ("10", "ek", "twenty")
├── PROVIDE_CUSTOMER ("Rahul", "mujhe", "customer name")
└── CONFIRM_ORDER ("confirm", "yes", "haan", "theek hai")
```

**Key Principle**: Queries always reset to BROWSING mode, transactions stay in flow.

## REDESIGNED HANDLER LOGIC

### 1. Intent Parser (Deterministic First, LLM Fallback)

```python
def parse_intent(text: str, current_mode: str, context: dict) -> dict:
    """
    Returns: {
        "intent": str,
        "confidence": "high" | "medium" | "low",
        "entities": {},
        "should_reset_flow": bool
    }
    """
    text_lower = text.lower().strip()
    
    # LAYER 1: Meta Intents (Always Highest Priority)
    if any(kw in text_lower for kw in ["cancel", "stop", "band karo", "nahi"]):
        return {"intent": "CANCEL", "confidence": "high", "should_reset_flow": True}
    
    if any(kw in text_lower for kw in ["help", "kya kar", "batao"]):
        return {"intent": "HELP", "confidence": "high", "should_reset_flow": False}
    
    # LAYER 2: Query Intents (Reset Flow if in ORDER mode)
    # Stock check patterns
    if any(kw in text_lower for kw in ["hai kya", "available", "stock", "milega", "?"]):
        product = extract_product(text)
        should_reset = (current_mode == "ordering")  # Reset if ordering
        return {
            "intent": "ASK_STOCK",
            "confidence": "high",
            "entities": {"product": product},
            "should_reset_flow": should_reset
        }
    
    # Symptom patterns
    if any(kw in text_lower for kw in ["bukhar", "fever", "dard", "pain", "cold", "sardi"]):
        symptom = extract_symptom(text)
        return {
            "intent": "ASK_SYMPTOM",
            "confidence": "high",
            "entities": {"symptom": symptom},
            "should_reset_flow": True  # Always reset for questions
        }
    
    # LAYER 3: Transaction Intents (Only if already in flow)
    if current_mode == "ordering":
        # Check for quantity
        qty = extract_quantity(text)
        if qty:
            return {
                "intent": "PROVIDE_QUANTITY",
                "confidence": "high",
                "entities": {"quantity": qty},
                "should_reset_flow": False
            }
        
        # Check for customer name
        if context.get("product") and context.get("quantity"):
            customer = extract_customer(text)
            if customer:
                return {
                    "intent": "PROVIDE_CUSTOMER",
                    "confidence": "high",
                    "entities": {"customer": customer},
                    "should_reset_flow": False
                }
    
    # FALLBACK: Use LLM for ambiguous cases
    return parse_with_llm(text, current_mode, context)
```

### 2. State Transition Logic

```python
def update_conversation_state(
    db, 
    chat_id: int, 
    intent: str, 
    entities: dict, 
    should_reset: bool
) -> str:
    """
    Returns new mode: idle | browsing | ordering | confirming
    """
    current = get_conversation_mode(db, chat_id)
    context = get_conversation_context(db, chat_id)
    
    # Reset if query intent interrupts order
    if should_reset and current == "ordering":
        logger.info(f"[STATE] User asked question during order - resetting to browsing")
        set_conversation_mode(db, chat_id, "browsing")
        return "browsing"
    
    # State transitions
    if intent == "CANCEL":
        clear_context(db, chat_id)
        return "idle"
    
    if intent in ["ASK_STOCK", "ASK_SYMPTOM", "ASK_PRICE"]:
        return "browsing"
    
    if intent == "START_ORDER":
        context.update(entities)
        save_context(db, chat_id, context)
        return "ordering"
    
    if intent == "PROVIDE_QUANTITY":
        context["quantity"] = entities["quantity"]
        save_context(db, chat_id, context)
        # Move to confirming if we have product + quantity
        if context.get("product") and context.get("quantity"):
            return "confirming"
        return "ordering"
    
    if intent == "PROVIDE_CUSTOMER":
        context["customer"] = entities["customer"]
        save_context(db, chat_id, context)
        return "confirming"
    
    if intent == "CONFIRM_ORDER":
        return "confirming"
    
    return current
```

### 3. Response Router

```python
async def route_response(
    update, 
    db, 
    chat_id: int, 
    intent: str, 
    entities: dict, 
    mode: str,
    context: dict
):
    """Generate appropriate response based on intent and mode"""
    
    # === QUERY HANDLERS (Non-blocking) ===
    if intent == "ASK_STOCK":
        product = entities.get("product")
        if not product:
            await update.message.reply_text(
                "🔍 Kaun si medicine check karni hai?\n"
                "Example: 'Paracetamol hai kya?'"
            )
            return
        
        item = find_inventory(db, product)
        if item:
            await update.message.reply_text(
                f"✅ {item.item_name}: {int(item.quantity)} units available\n"
                f"💰 Price: ₹{item.price}\n\n"
                f"Order karna hai? Quantity batao (e.g., '10' or 'ek packet')"
            )
            # Save product in context for quick order
            context["product"] = item.item_name
            save_context(db, chat_id, context)
        else:
            # Try symptom search
            symptom_results = search_by_symptom(db, product)
            if symptom_results:
                await show_symptom_results(update, symptom_results)
            else:
                await update.message.reply_text(f"❌ '{product}' stock mein nahi hai")
        return
    
    if intent == "ASK_SYMPTOM":
        symptom = entities.get("symptom", "")
        results = search_by_symptom(db, symptom)
        if results:
            msg = f"🔍 '{symptom}' ke liye ye medicines hain:\n\n"
            for i, med in enumerate(results[:5], 1):
                rx = "🔴 Rx Required" if med["requires_prescription"] else "🟢 OTC"
                msg += f"{i}. {med['name']} {rx}\n"
                msg += f"   Used for: {med['disease']}\n"
                msg += f"   ₹{med['price']} | {int(med['stock'])} units\n\n"
            msg += "💬 Medicine name bolke order kar sakte ho"
            await update.message.reply_text(msg)
        else:
            await update.message.reply_text(
                f"❌ '{symptom}' ke liye specific medicine nahi mila\n"
                "Medicine name se search karo"
            )
        return
    
    # === TRANSACTION HANDLERS (Flow-based) ===
    if mode == "ordering":
        if not context.get("product"):
            await update.message.reply_text("📦 Kaun si medicine chahiye?")
            return
        
        if not context.get("quantity"):
            await update.message.reply_text(
                f"🔢 {context['product']} ki kitni quantity?\n"
                "Example: '10', 'ek', 'twenty'"
            )
            return
    
    if mode == "confirming":
        # Show confirmation (customer is optional now!)
        product = context.get("product")
        quantity = context.get("quantity")
        customer = context.get("customer", "Walk-in Customer")
        
        await update.message.reply_text(
            f"📋 Order Summary\n"
            f"━━━━━━━━━━━━━━━━━━\n"
            f"📦 Product: {product}\n"
            f"🔢 Quantity: {int(quantity)}\n"
            f"👤 Customer: {customer}\n"
            f"━━━━━━━━━━━━━━━━━━\n\n"
            f"✅ 'confirm' - Order banao\n"
            f"❌ 'cancel' - Band karo\n"
            f"✏️ Ya kuch change karna hai to batao"
        )
        return
```

## EXAMPLE CONVERSATIONS

### Scenario 1: Browse → Order → Interrupt → Resume

```
User: "Paracetamol hai?"
Bot: ✅ Paracetamol 500mg: 200 units available
     💰 Price: ₹2.50
     Order karna hai? Quantity batao

[MODE: browsing, CONTEXT: {product: "Paracetamol 500mg"}]

User: "bukhar ke liye aur kya hai?"  ← INTERRUPT
Bot: 🔍 'bukhar' ke liye ye medicines hain:
     1. Paracetamol 500mg 🟢 OTC
        Used for: Fever, Headache
     2. Dolo 650 🟢 OTC
        Used for: High Fever
     💬 Medicine name bolke order kar sakte ho

[MODE: browsing, CONTEXT: cleared]

User: "Dolo 10 chahiye"
Bot: 🔢 Dolo 650 ki kitni quantity?
     Example: '10', 'ek', 'twenty'

[MODE: ordering, CONTEXT: {product: "Dolo 650", quantity: 10}]

User: "Rahul"
Bot: 📋 Order Summary
     ━━━━━━━━━━━━━━━━━━
     📦 Product: Dolo 650
     🔢 Quantity: 10
     👤 Customer: Rahul
     ━━━━━━━━━━━━━━━━━━
     ✅ 'confirm' - Order banao

[MODE: confirming]

User: "confirm"
Bot: ✅ Invoice draft created!
     📱 Approve from Owner Dashboard.

[MODE: idle]
```

### Scenario 2: Direct Order (No Customer)

```
User: "10 Crocin"
Bot: 📋 Order Summary
     ━━━━━━━━━━━━━━━━━━
     📦 Product: Crocin Advance
     🔢 Quantity: 10
     👤 Customer: Walk-in Customer
     ━━━━━━━━━━━━━━━━━━
     ✅ 'confirm' - Order banao
     👤 Customer name add karna hai to batao

[MODE: confirming, CONTEXT: {product: "Crocin", quantity: 10}]

User: "confirm"
Bot: ✅ Invoice draft created!
```

### Scenario 3: Natural Flow Changes

```
User: "Dolo chahiye"
Bot: 🔢 Dolo 650 ki kitni quantity?

[MODE: ordering]

User: "wait, Combiflam hai?"  ← QUERY INTERRUPTS
Bot: ✅ Combiflam: 180 units available
     💰 Price: ₹5.00
     Order karna hai? Quantity batao

[MODE: browsing, order cleared]

User: "haan, 5 packets"
Bot: 📋 Order Summary
     ━━━━━━━━━━━━━━━━━━
     📦 Product: Combiflam
     🔢 Quantity: 5
     👤 Customer: Walk-in Customer
```

## IMPLEMENTATION CHANGES

### File: handlers.py

Changes needed:
1. Replace `InvoiceFlowStep` enum with `ConversationMode`
2. Add `parse_intent()` function with keyword patterns
3. Add `update_conversation_state()` function
4. Refactor `handle_message()` to use intent hierarchy
5. Make customer optional in order flow
6. Add query interrupt handling

### File: prompts.py

Add examples for interruption handling:
```python
User: "Dolo chahiye"
Context: mode = "ordering"
Output: {"intent": "START_ORDER", "product": "Dolo"}

User: "wait, fever medicine hai?"
Context: mode = "ordering", product = "Dolo"
Output: {"intent": "ASK_SYMPTOM", "should_reset_flow": true}
```

## KEY ARCHITECTURAL PRINCIPLES

1. **Intent > State**: Intent determines response, not current state
2. **Query = Non-destructive**: Asking questions never breaks flow
3. **Transaction = Additive**: Building order accumulates data
4. **Reset = Explicit**: Only queries or "cancel" reset context
5. **Customer = Optional**: Walk-in customer is default
6. **Confirmation = Flexible**: Can edit any field before confirm

## DEMO SCRIPT FOR HACKATHON

```
"I'll show you how our bot handles natural conversation..."

[DEMO 1: Simple Order]
"10 Paracetamol" → Confirms → Done

[DEMO 2: Symptom Search]
"bukhar hai" → Shows fever medicines → Pick one → Order

[DEMO 3: Interruption Handling]
Start ordering Dolo → Ask about Crocin → Switch to Crocin → Complete

[DEMO 4: Context Memory]
"Paracetamol hai?" → Bot remembers → Just say "10" → Order created

"This is conversational AI, not a form-filling chatbot."
```

---

**Status**: Ready for implementation
**Risk**: Low - adds flexibility without breaking existing flows
**Effort**: 2-3 hours refactoring
**Impact**: Transforms UX from rigid to natural
