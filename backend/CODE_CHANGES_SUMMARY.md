# Numeric Input Bug — Code Changes Summary

## Files Modified: 4
## Lines Changed: ~50
## Risk: MINIMAL (additive only, no removal of logic)

---

## File 1: `app/agent/conversation_state.py`

### Change: Add 2 new FSM states

```python
class ConversationMode:
    """Bot conversation modes"""
    IDLE = "idle"
    STOCK_CONFIRMED = "stock_confirmed"      # ← NEW state
    AWAITING_CUSTOMER = "awaiting_customer"  # ← NEW state
    CONFIRMING = "confirming"
    BROWSING = "browsing"
    ORDERING = "ordering"
```

**Why:** Explicit states for product-locked workflows prevent ambiguity.

---

## File 2: `app/agent/intent_parser_deterministic.py`

### Change: Accept quantity in STOCK_CONFIRMED mode

```python
# BEFORE:
quantity = extract_quantity(text_lower)
if quantity and current_mode == ConversationMode.ORDERING:
    return {"intent": IntentType.PROVIDE_QUANTITY, ...}

# AFTER:
quantity = extract_quantity(text_lower)
if quantity and current_mode in [ConversationMode.ORDERING, ConversationMode.STOCK_CONFIRMED]:
    return {"intent": IntentType.PROVIDE_QUANTITY, ...}
```

**Impact:** Line count: +1 (array expansion)  
**What it does:** Numeric-only input now recognized as quantity when product is locked.

---

## File 3: `app/telegram/handlers_conversational.py`

### Change 3A: Product Locking FSM Update

```python
def update_conversation_state(db, chat_id, intent, entities, should_reset, 
                               current_mode, current_context) -> tuple:
    # === STOCK CONFIRMATION FLOW (NEW SECTION) ===
    if intent == IntentType.ASK_STOCK:
        # Lock product in STOCK_CONFIRMED state
        if entities.get("product"):
            context["product"] = entities["product"]  # ← LOCK
            logger.info(f"Product locked in STOCK_CONFIRMED: {entities['product']}")
            return (ConversationMode.STOCK_CONFIRMED, context)
    
    # === QUANTITY AFTER STOCK CONFIRMATION (FIXED) ===
    if intent == IntentType.PROVIDE_QUANTITY:
        context["quantity"] = entities["quantity"]
        
        # If in STOCK_CONFIRMED, product is already locked
        if current_mode == ConversationMode.STOCK_CONFIRMED:
            logger.info(f"Got quantity in STOCK_CONFIRMED → AWAITING_CUSTOMER")
            return (ConversationMode.AWAITING_CUSTOMER, context)
        
        # ... (rest unchanged for ORDERING mode)
```

**What changed:**
- Added explicit check for `STOCK_CONFIRMED` state
- Product transitioned from `last_query_product` to locked `context["product"]`
- Quantity input → state transition to `AWAITING_CUSTOMER`

---

### Change 3B: State-Specific Response Routing

```python
async def handle_transaction_response(update, db, business_id, chat_id, mode, context):
    """NEW: Handle STOCK_CONFIRMED and AWAITING_CUSTOMER states"""
    
    # === STOCK_CONFIRMED: Product verified, await quantity (NEW) ===
    if mode == ConversationMode.STOCK_CONFIRMED:
        product = context.get("product")
        await update.message.reply_text(
            f"🔢 {product} ki kitni quantity chahiye?\n"
            "Example: '10', 'ek dozen', 'twenty'"
        )
        return
    
    # === AWAITING_CUSTOMER: Have product+qty, need customer (NEW) ===
    if mode == ConversationMode.AWAITING_CUSTOMER:
        product = context.get("product")
        quantity = context.get("quantity")
        await update.message.reply_text(
            f"📋 Order: {product} × {int(quantity)}\n"
            f"💬 Customer name? (or 'confirm')"
        )
        return
    
    # ... rest of ORDERING and CONFIRMING unchanged
```

**What changed:** Added two new state handlers before existing ORDERING handler.

---

### Change 3C: Clarified Stock Response

```python
async def handle_query_response(update, db, business_id, intent, entities, context, current_mode=None):
    if intent == IntentType.ASK_STOCK:
        # ... product lookup ...
        if item:
            qty = int(item.quantity)
            msg = (
                f"✅ {item.item_name}: {qty} units available\n"
                f"💰 Price: ₹{item.price}\n\n"
            )
            if qty > 0:
                # ✨ BETTER PROMPT: Now explicitly asks for quantity
                msg += "🔢 Kitni quantity chahiye? (e.g., '10', 'ek', 'twenty')"
            await update.message.reply_text(msg)
```

**What changed:** Message prompt explicitly guides user to provide quantity next.

---

### Change 3D: Main Handler Routing

```python
# BEFORE:
elif new_mode in [ConversationMode.ORDERING, ConversationMode.CONFIRMING]:
    await handle_transaction_response(...)

# AFTER:
elif new_mode in [ConversationMode.STOCK_CONFIRMED, ConversationMode.AWAITING_CUSTOMER, 
                  ConversationMode.ORDERING, ConversationMode.CONFIRMING]:
    await handle_transaction_response(...)
```

**Impact:** Now routes new states to transaction handler.

---

## Summary of Changes

| File | Type | Lines | Change |
|------|------|-------|--------|
| conversation_state.py | Addition | +2 | New FSM states |
| intent_parser_deterministic.py | Modification | ~1 | Include STOCK_CONFIRMED in condition |
| handlers_conversational.py | Addition | ~50 | FSM logic + new handlers + routing |
| **Total** | — | **~53** | Minimal, additive changes |

---

## Safety Analysis

✅ **No destructive changes** — All code is additive  
✅ **No business logic removed** — Old ORDERING path still works  
✅ **Backward compatible** — Non-stock-check flows unchanged  
✅ **Deterministic** — No new LLM calls added  
✅ **Maintainable** — Clear state transitions logged  

---

## Before/After: Execution Trace

### BEFORE (BUG)
```
User: "Paracetamol hai?"
├─ Intent: ASK_STOCK ✓
├─ Mode: idle → browsing
└─ Response: "Stock available"

User: "10"
├─ Mode: browsing (NOT ordering)
├─ Check quantity? → NO (only checks in ORDERING mode)
├─ Falls to: UNKNOWN, low confidence
├─ LLM tries to parse: "10" as product name
└─ Response: "'10' stock mein nahi mila" ❌ WRONG
```

### AFTER (FIXED)
```
User: "Paracetamol hai?"
├─ Intent: ASK_STOCK ✓
├─ Mode: idle → stock_confirmed
├─ Product: locked as "Paracetamol"
└─ Response: "Stock available, quantity?"

User: "10"
├─ Mode: stock_confirmed
├─ Check quantity? → YES (checks in STOCK_CONFIRMED mode now)
├─ extract_quantity("10") → 10.0 ✓
├─ Intent: PROVIDE_QUANTITY ✓
├─ Mode: stock_confirmed → awaiting_customer
└─ Response: "Paracetamol × 10, customer name?" ✅ CORRECT
```

---

## Deployment Notes

1. **No migration needed** — FSM states are string constants
2. **No DB schema changes** — States stored in existing `payload` JSON
3. **Backward compatible** — Old conversations in IDLE/BROWSING/ORDERING unaffected
4. **Can rollback** — New states simply won't be set on rollback

---

## Testing Commands

```bash
# Test stock → quantity flow
User: "Paracetamol hai?"
Expected mode: stock_confirmed
Expected product: Paracetamol

User: "10"
Expected intent: PROVIDE_QUANTITY
Expected mode: awaiting_customer
Expected response: "Paracetamol × 10, customer?"

User: "Rahul"
Expected intent: PROVIDE_CUSTOMER
Expected mode: confirming
Expected response: Invoice summary

User: "confirm"
Expected: DRAFT created, mode → idle
```

