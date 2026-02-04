# CODE COMPARISON: KEY FIXES (LINE BY LINE)

## This file shows exact code changes for critical bugs

# ==============================================================================
# FIX #1: PRODUCT NAME CORRUPTION
# ==============================================================================

# ❌ OLD CODE (handlers.py - approximate line 520)
def handle_fsm_old(db, chat_id, text):
    product = parse_product_from_text(text)  # Returns raw user input
    # ...
    payload = {
        "product": product,  # ❌ RAW USER TEXT GOES TO INVOICE
        "customer_name": customer,
        "amount": 500  # Magic number
    }


# ✅ NEW CODE (handlers_refactored.py - line 480)
async def handle_order_flow(update, db, business_id, chat_id, text, owner_name):
    # Step 1: Extract entity from text
    extracted = extract_product_with_confidence(text)
    # → {"value": "dolo", "confidence": 0.8}
    
    # Step 2: Resolve to canonical product
    resolved = resolve_product(db, business_id, extracted["value"])
    # → {
    #     "canonical_name": "Dolo 650",
    #     "price_per_unit": 25.00,
    #     "product_id": 123
    # }
    
    if not resolved:
        await update.message.reply_text("Product not found")
        return
    
    # Step 3: Use canonical name in entities
    entities["product"] = resolved  # ✅ CANONICAL MODEL
    
    # ...later in draft creation...
    payload = {
        "product": product["canonical_name"],  # ✅ "Dolo 650" (never "dolo hai kya")
        "product_id": product["product_id"],
        # ...
    }


# ==============================================================================
# FIX #2: ROLE SEPARATION
# ==============================================================================

# ❌ OLD CODE (decision_engine.py - line 80)
def validate_and_create_draft_old(...):
    payload = {
        "customer_name": customer,  # Used for both roles
        "product": product,
        "amount": amount
    }
    # ❌ NO EXPLICIT SELLER/BUYER DISTINCTION


# ✅ NEW CODE (decision_engine.py - line 104)
def validate_and_create_draft(...):
    # EXPLICIT ROLE ASSIGNMENT
    payload = {
        "seller": "Pharmacy",              # ✅ WHO IS SELLING (constant)
        "buyer": customer,                 # ✅ WHO IS BUYING (variable)
        "customer_name": customer,         # Backward compat
        "product": item.item_name,         # Canonical
        "product_id": item.id,
        "quantity": quantity,
        "unit_price": unit_price,
        "amount": amount
    }
    
    # Ensure roles never confused
    assert payload["seller"] == "Pharmacy"
    assert payload["buyer"] == customer
    assert payload["seller"] != payload["buyer"]


# ==============================================================================
# FIX #3: DETERMINISTIC BILLING
# ==============================================================================

# ❌ OLD CODE (handlers.py - line 520)
def handle_invoice_old(...):
    # Magic number - no calculation
    amount = 500  # ❌ WHERE DID THIS COME FROM?
    
    payload = {
        "amount": amount,  # ❌ NO CALCULATION SHOWN
        "product": product,
        "customer_name": customer
    }


# ✅ NEW CODE (handlers_refactored.py - line 510)
async def handle_order_flow(...):
    # Get product with pricing
    product = entities["product"]  # Canonical model
    quantity = entities["quantity"]
    
    # DETERMINISTIC CALCULATION
    unit_price = float(product["price_per_unit"])  # From inventory.price
    total_amount = unit_price * quantity           # Always calculated
    
    # Show calculation to user
    msg = (
        f"💰 Price: ₹{unit_price:.2f} × {int(quantity)} = ₹{total_amount:.2f}"
    )
    
    # Draft with transparent billing
    payload = {
        "unit_price": unit_price,   # ✅ EXPLICIT UNIT PRICE
        "quantity": quantity,
        "amount": total_amount,     # ✅ CALCULATED (never hardcoded)
        # ...
    }


# ==============================================================================
# FIX #4: CONFIDENCE-BASED QUESTION SKIPPING
# ==============================================================================

# ❌ OLD CODE (handlers.py - line 180)
def handle_fsm_old(...):
    # Always ask for missing data
    if not state["data"]["product"]:
        return "What product?"  # ❌ ALWAYS ASKS
    if not state["data"]["quantity"]:
        return "What quantity?"  # ❌ ALWAYS ASKS
    if not state["data"]["customer"]:
        return "What customer?"  # ❌ ALWAYS ASKS


# ✅ NEW CODE (handlers_refactored.py - line 350)
async def handle_order_flow(...):
    # Extract with confidence scores
    extracted = extract_all_entities(text)
    # → {
    #     "product": {"value": "Dolo", "confidence": 0.95},
    #     "quantity": {"value": 10, "confidence": 0.95},
    #     "customer": {"value": "Rahul", "confidence": 0.85}
    # }
    
    # Check if we should skip questions
    if should_skip_question(extracted["product"]["confidence"]):
        # ✅ HIGH CONFIDENCE - AUTO-FILL, DON'T ASK
        entities["product"] = resolve_product(...)
    else:
        # Low confidence - ask question
        await update.message.reply_text("What product?")
    
    # Only ask if confidence < threshold
    if all(conf > 0.8 for conf in [prod_conf, qty_conf, cust_conf]):
        # ✅ SKIP ALL QUESTIONS, GO TO CONFIRM
        next_state = OrderFlowState.READY_TO_CONFIRM
    else:
        # Ask only for low-confidence entities
        next_state = determine_next_state(entities, confidence)


# ==============================================================================
# FIX #5: ENTITY-FIRST FSM (No Premature Trigger)
# ==============================================================================

# ❌ OLD CODE (handlers.py - line 320)
def handle_fsm_old(db, chat_id, text):
    # Keyword-based state transition
    if "chahiye" in text or "order" in text:
        state = "ORDERING"  # ❌ ENTER STATE WITHOUT VALIDATION
    
    # Now in ORDERING state, but entities might be invalid
    # ...later...
    if state == "ORDERING":
        # Ask for product (might not exist)
        return "What product?"


# ✅ NEW CODE (handlers_refactored.py - line 380)
async def handle_order_flow(...):
    # Step 1: EXTRACT entities first
    extracted = extract_all_entities(text)
    
    # Step 2: RESOLVE product to canonical (VALIDATE)
    if extracted["product"]["value"]:
        resolved = resolve_product(db, business_id, extracted["product"]["value"])
        
        if not resolved:
            # ✅ STOP BEFORE FSM - PRODUCT INVALID
            await update.message.reply_text("Product not found")
            reset_conversation(db, chat_id)
            return  # Don't enter FSM
    
    # Step 3: VALIDATE all entities
    if not all_entities_valid(entities):
        # ✅ DON'T ENTER FSM YET
        next_state = OrderFlowState.NEED_PRODUCT
    else:
        # ✅ ONLY TRANSITION WITH VALIDATED ENTITIES
        next_state = OrderFlowState.READY_TO_CONFIRM
    
    # Step 4: THEN update state
    context["state"] = next_state


# ==============================================================================
# PRODUCT RESOLUTION (NEW MODULE)
# ==============================================================================

# ✅ NEW MODULE: product_resolver.py
def resolve_product(db, business_id, user_input, min_confidence=0.7):
    """
    Map user input to canonical product model
    
    Example:
        resolve_product(db, 1, "dolo hai kya?")
        → {
            "product_id": 123,
            "canonical_name": "Dolo 650",
            "price_per_unit": Decimal("25.00"),
            "stock_quantity": Decimal("100"),
            "requires_prescription": False,
            "confidence": 0.95
        }
    """
    # Step 1: Normalize input
    normalized = normalize_product_input(user_input)
    # "dolo hai kya?" → "dolo"
    
    # Step 2: Search inventory
    items = db.query(Inventory).filter(
        Inventory.business_id == business_id
    ).all()
    
    # Step 3: Calculate confidence for each item
    best_match = None
    best_confidence = 0.0
    
    for item in items:
        confidence = calculate_match_confidence(user_input, item.item_name)
        if confidence > best_confidence:
            best_confidence = confidence
            best_match = item
    
    # Step 4: Check threshold
    if best_confidence < min_confidence:
        return None  # No good match
    
    # Step 5: Return canonical model
    return {
        "product_id": best_match.id,
        "canonical_name": best_match.item_name,  # ✅ NEVER raw user input
        "price_per_unit": Decimal(str(best_match.price)),
        "stock_quantity": Decimal(str(best_match.quantity)),
        "requires_prescription": best_match.requires_prescription,
        "confidence": best_confidence
    }


# ==============================================================================
# ENTITY EXTRACTION (NEW MODULE)
# ==============================================================================

# ✅ NEW MODULE: entity_extractor.py
def extract_quantity_with_confidence(text, context=None):
    """
    Extract quantity with confidence score
    
    Example:
        extract_quantity_with_confidence("10")
        → {"value": 10.0, "confidence": 0.95, "source": "numeric"}
        
        extract_quantity_with_confidence("ek")
        → {"value": 1.0, "confidence": 0.85, "source": "word"}
    """
    # Try numeric extraction (highest confidence)
    numeric_match = re.search(r'\b(\d+(?:\.\d+)?)\b', text)
    if numeric_match:
        value = float(numeric_match.group(1))
        return {
            "value": value,
            "confidence": 0.95,  # High confidence for numbers
            "source": "numeric"
        }
    
    # Try word-based extraction (medium confidence)
    for word, num in NUMBER_WORDS.items():
        if word in text.lower():
            return {
                "value": float(num),
                "confidence": 0.85,  # Medium-high for words
                "source": "word"
            }
    
    # Try context (low confidence)
    if context and context.get("last_quantity"):
        return {
            "value": float(context["last_quantity"]),
            "confidence": 0.4,  # Low confidence from context
            "source": "context"
        }
    
    return {"value": None, "confidence": 0.0, "source": None}


def should_skip_question(entity_confidence, threshold=0.8):
    """
    Decide if we should skip asking for this entity
    
    Example:
        should_skip_question(0.95)  → True (high confidence, skip question)
        should_skip_question(0.5)   → False (low confidence, ask question)
    """
    return entity_confidence >= threshold


# ==============================================================================
# USAGE COMPARISON: Complete Flow
# ==============================================================================

# ❌ OLD FLOW
"""
1. User: "Rahul ko 10 Dolo"
2. Parse with regex (fragile)
3. Extract: product="Dolo", quantity=10, customer="Rahul"
4. Enter FSM without validation
5. Ask redundant questions:
   - "Product?" (already said Dolo)
   - "Quantity?" (already said 10)
   - "Customer?" (already said Rahul)
6. Create draft with:
   - product="Dolo" (not canonical)
   - amount=500 (magic number)
   - No roles specified
"""

# ✅ NEW FLOW
"""
1. User: "Rahul ko 10 Dolo"
2. Extract entities with confidence:
   - product: {"value": "Dolo", "confidence": 0.95}
   - quantity: {"value": 10, "confidence": 0.95}
   - customer: {"value": "Rahul", "confidence": 0.85}
3. Resolve product to canonical:
   - "Dolo" → {"canonical_name": "Dolo 650", "price": 25.00}
4. Validate all entities (all high confidence)
5. Skip redundant questions (confidence > 0.8)
6. Show confirmation:
   - Seller: Pharmacy
   - Buyer: Rahul
   - Product: Dolo 650 (canonical)
   - Calculation: ₹25 × 10 = ₹250
7. Create draft with validated, canonical data
"""

# Result: 
# OLD: 8 messages (frustrating)
# NEW: 2 messages (efficient) ✅
