# Numeric-Only Input Bug Fix — Detailed Explanation

## CRITICAL BUG REPORT

**Issue:** After confirming product stock ("Paracetamol hai?"), user inputs "10" (quantity) → System treats "10" as medicine name → Returns "'10' stock mein nahi mila" ❌

---

## ROOT CAUSE ANALYSIS

### What Was Happening (BEFORE)

```
User Flow → System Behavior → Wrong Result

1. User: "Paracetamol hai?"
   ├─ Intent detected: ASK_STOCK (high confidence)
   ├─ Mode set: BROWSING
   ├─ Context: {last_query_product: "Paracetamol"}
   └─ Response: ✅ "Paracetamol: 10 units available"

2. User: "10"  (meaning quantity)
   ├─ Text: "10" (numeric only)
   ├─ Mode: BROWSING (still)
   ├─ Check quantity? → SKIPPED ❌
   │   └─ Condition: if quantity AND mode == ORDERING
   │       Current mode is BROWSING, NOT ORDERING
   ├─ Extract product+qty? → NO (pattern doesn't match)
   ├─ Falls through to: UNKNOWN intent, low confidence
   ├─ LLM fallback attempts parse
   ├─ LLM hallucinates: "10" is a product name?
   ├─ Intent returned: ASK_STOCK, product="10"
   ├─ Inventory.filter("where item_name like '%10%'") → NULL
   └─ Response: ❌ "'10' stock mein nahi mila" [WRONG!]
```

### Key Problem: State Model Too Loose

**Old conversation states:**
- IDLE, BROWSING, ORDERING, CONFIRMING

**Issue:** After stock check, conversation enters BROWSING (non-blocking query state). But:
1. Product is stored in `last_query_product` (volatile)
2. Quantity parsing only works in ORDERING mode
3. No explicit "product locked, awaiting quantity" state
4. Numeric-only input not recognized as quantity in BROWSING mode → LLM fallback

---

## SOLUTION: State-Aware FSM with Product Locking

### New Conversation States

```python
STOCK_CONFIRMED    # ✨ NEW: Product verified and locked, awaiting quantity
AWAITING_CUSTOMER  # ✨ NEW: Have product+qty, need customer name (optional)
```

| State | Meaning | What's locked | Awaiting |
|-------|---------|--------------|----------|
| IDLE | No flow active | — | User intent |
| STOCK_CONFIRMED | ✅ Product exists & verified | **product** | quantity |
| AWAITING_CUSTOMER | ✅ Product + qty confirmed | product, quantity | customer (optional) |
| CONFIRMING | ✅ Ready to create invoice | product, qty, customer | confirmation |
| ORDERING | Generic order in progress | — | next entity |
| BROWSING | Non-blocking query | — | next query |

---

## CORRECTED CONTROL FLOW

### Scenario: Stock Check → Quantity → Confirm

```
User Flow → System Behavior → Correct Result

1. User: "Paracetamol hai?"
   ├─ Intent: ASK_STOCK, product="Paracetamol" (deterministic, high confidence)
   ├─ Mode transition: IDLE → STOCK_CONFIRMED
   ├─ Context: {product: "Paracetamol"}  ← LOCKED (not just last_query_product)
   └─ Response: ✅ "Paracetamol: 10 units | Price: ₹50 | Quantity?"

2. User: "10"
   ├─ Text: "10" (numeric)
   ├─ Mode: STOCK_CONFIRMED
   ├─ Check quantity? → YES ✅
   │   └─ Condition: if quantity AND mode in [ORDERING, STOCK_CONFIRMED]
   │       Mode is STOCK_CONFIRMED → MATCH
   │   └─ extract_quantity("10") → 10.0
   ├─ Intent returned: PROVIDE_QUANTITY, entities={quantity: 10}
   ├─ State transition: STOCK_CONFIRMED → AWAITING_CUSTOMER
   ├─ Context: {product: "Paracetamol", quantity: 10}
   └─ Response: ✅ "Order: Paracetamol × 10. Customer name? (or 'confirm')"

3. User: "confirm"
   ├─ Intent: CONFIRM_ORDER (or implied if no customer)
   ├─ State transition: AWAITING_CUSTOMER → CONFIRMING
   ├─ Context: {product: "Paracetamol", quantity: 10, customer: "Walk-in Customer"}
   ├─ Summary shown with exact price
   └─ Response: ✅ "Invoice summary | ✅ Confirm or ❌ Cancel"

4. User: "yes"
   ├─ Intent: CONFIRM_ORDER
   ├─ Mode: CONFIRMING
   ├─ Create DRAFT action (no execution without owner approval)
   ├─ Reset state: CONFIRMING → IDLE
   └─ Response: ✅ "Invoice draft created! Approve from Dashboard"
```

---

## CODE CHANGES

### Change 1: Enhanced FSM States
**File:** `conversation_state.py`

```python
class ConversationMode:
    IDLE = "idle"
    STOCK_CONFIRMED = "stock_confirmed"      # ✨ NEW
    AWAITING_CUSTOMER = "awaiting_customer"  # ✨ NEW
    CONFIRMING = "confirming"
    BROWSING = "browsing"
    ORDERING = "ordering"
```

### Change 2: State-Aware Quantity Parser
**File:** `intent_parser_deterministic.py`

```python
# BEFORE (BUG):
quantity = extract_quantity(text_lower)
if quantity and current_mode == ConversationMode.ORDERING:  # ← Only ORDERING!
    return {"intent": IntentType.PROVIDE_QUANTITY, ...}

# AFTER (FIX):
quantity = extract_quantity(text_lower)
if quantity and current_mode in [ConversationMode.ORDERING, ConversationMode.STOCK_CONFIRMED]:
    #                                                      ↑ ← Now also accepts STOCK_CONFIRMED
    return {"intent": IntentType.PROVIDE_QUANTITY, ...}
```

### Change 3: Product Locking State Machine
**File:** `handlers_conversational.py`

```python
def update_conversation_state(...) -> tuple:
    """
    FSM STATES:
    - IDLE: No active flow
    - STOCK_CONFIRMED: Product locked after stock check ← PRODUCT LOCKED HERE
    - AWAITING_CUSTOMER: Have product+qty, need customer
    - CONFIRMING: Ready to execute
    """
    
    # === STOCK CONFIRMATION FLOW (NEW) ===
    if intent == IntentType.ASK_STOCK:
        if entities.get("product"):
            context["product"] = entities["product"]  # ← LOCK PRODUCT IN CONTEXT
            logger.info(f"Product locked in STOCK_CONFIRMED: {entities['product']}")
            return (ConversationMode.STOCK_CONFIRMED, context)
    
    # === QUANTITY AFTER STOCK CONFIRMATION (FIXED) ===
    if intent == IntentType.PROVIDE_QUANTITY:
        context["quantity"] = entities["quantity"]
        
        if current_mode == ConversationMode.STOCK_CONFIRMED:  # ← NEW CHECK
            logger.info(f"Got quantity in STOCK_CONFIRMED → AWAITING_CUSTOMER")
            return (ConversationMode.AWAITING_CUSTOMER, context)
        
        # ... rest of logic for ORDERING mode
```

### Change 4: State-Specific Response Handlers
**File:** `handlers_conversational.py`

```python
async def handle_transaction_response(update, db, business_id, chat_id, mode, context):
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
    
    # ... rest of handlers
```

---

## EXECUTION GUARANTEE

### What This Achieves

✅ **Deterministic**: Numeric input in STOCK_CONFIRMED → quantity, NOT product name  
✅ **Product Locking**: Once stock confirmed, product persists until order complete  
✅ **No LLM Hallucination**: Numeric parsing happens before LLM fallback  
✅ **State Safety**: Can't accidentally reuse quantity for other products  
✅ **FSM Explainable**: Clear state transitions visible in logs  

### Before/After Comparison

| Metric | BEFORE | AFTER |
|--------|--------|-------|
| Max states | 4 | 6 (with STOCK_CONFIRMED, AWAITING_CUSTOMER) |
| Product storage | `last_query_product` (volatile) | `context["product"]` (locked) |
| Quantity recognition | ORDERING mode only | ORDERING + STOCK_CONFIRMED |
| LLM fallback for "10" | YES (hallucination risk) | NO (deterministic match) |
| Bug scenario | "'10' stock nahi mila" ❌ | "Paracetamol × 10 confirm?" ✅ |

---

## SAFETY & COMPLIANCE (PS-2)

✅ **No business logic in LLM**: Intent extraction only  
✅ **All execution requires owner approval**: DRAFT → APPROVE → EXECUTE  
✅ **No autonomous financial action**: User can cancel anytime  
✅ **Audit trail**: FSM state logged for compliance  
✅ **Deterministic**: No random LLM behavior in numeric parsing  

---

## Testing Checklist

- [ ] User: "Paracetamol hai?" → Mode: STOCK_CONFIRMED, product locked
- [ ] User: "10" → Intent: PROVIDE_QUANTITY, mode: AWAITING_CUSTOMER
- [ ] User: "Rahul" → Intent: PROVIDE_CUSTOMER, mode: CONFIRMING
- [ ] User: "confirm" → DRAFT invoice created
- [ ] User: "Paracetamol hai?" → "10" → "cancel" → Reset to IDLE
- [ ] Numeric only in BROWSING mode → Should NOT be interpreted as quantity
- [ ] Non-numeric in STOCK_CONFIRMED → Should ask for valid quantity

---

## Files Modified

1. **conversation_state.py** — Added STOCK_CONFIRMED, AWAITING_CUSTOMER states
2. **intent_parser_deterministic.py** — Quantity check now includes STOCK_CONFIRMED mode
3. **handlers_conversational.py** — FSM transitions, state-aware response routing

---

## Debug Output Example

```
[MSG] chat_id=123456, text='Paracetamol hai?'
[STATE] mode=idle, context={}
[INTENT] ASK_STOCK, product=Paracetamol, reset=False
[FSM] Product locked in STOCK_CONFIRMED: Paracetamol
[STATE] Saved: mode=stock_confirmed, context={product: Paracetamol}

[MSG] chat_id=123456, text='10'
[STATE] mode=stock_confirmed, context={product: Paracetamol}
[INTENT] PROVIDE_QUANTITY, quantity=10, reset=False ✅ (quantity check MATCHED)
[FSM] Got quantity in STOCK_CONFIRMED → AWAITING_CUSTOMER
[STATE] Saved: mode=awaiting_customer, context={product: Paracetamol, quantity: 10}
```

Compare this to OLD behavior:
```
[MSG] chat_id=123456, text='10'
[STATE] mode=browsing, context={last_query_product: Paracetamol}
[INTENT] UNKNOWN, low confidence (quantity check SKIPPED, not in ORDERING mode) ❌
[LLM] Fallback parse: ASK_STOCK, product=10 (HALLUCINATION)
```

---

## End Result

**Before:** ❌ "'10' stock mein nahi mila" (wrong product name, user confused)  
**After:** ✅ "Paracetamol × 10 confirm?" (correct product, user continues naturally)

