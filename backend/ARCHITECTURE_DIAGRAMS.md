# SYSTEM ARCHITECTURE DIAGRAMS

## COMPLETE SYSTEM FLOW

```
┌─────────────────────────────────────────────────────────────────────────┐
│                         USER SENDS MESSAGE                               │
│                    "Rahul ko 10 Dolo 650"                                │
└────────────────────────────────┬────────────────────────────────────────┘
                                 │
                                 ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                    INTENT CLASSIFICATION                                 │
│  Priority: cancel > help > query > order > unknown                      │
│  Result: "order" (contains product + quantity + customer)               │
└────────────────────────────────┬────────────────────────────────────────┘
                                 │
                                 ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                  ENTITY EXTRACTION (with confidence)                     │
│  ┌──────────────────────────────────────────────────────────────────┐  │
│  │ extract_all_entities(text)                                       │  │
│  │ → {                                                              │  │
│  │     "product": {"value": "Dolo", "confidence": 0.95},           │  │
│  │     "quantity": {"value": 10, "confidence": 0.95},              │  │
│  │     "customer": {"value": "Rahul", "confidence": 0.85}          │  │
│  │   }                                                              │  │
│  └──────────────────────────────────────────────────────────────────┘  │
└────────────────────────────────┬────────────────────────────────────────┘
                                 │
                                 ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                    PRODUCT RESOLUTION                                    │
│  ┌──────────────────────────────────────────────────────────────────┐  │
│  │ resolve_product(db, business_id, "Dolo")                         │  │
│  │ 1. Normalize: "Dolo" → "dolo"                                    │  │
│  │ 2. Search inventory                                              │  │
│  │ 3. Fuzzy match: "dolo" ≈ "Dolo 650" (confidence: 0.95)          │  │
│  │ 4. Return canonical:                                             │  │
│  │    {                                                             │  │
│  │      "canonical_name": "Dolo 650",                               │  │
│  │      "product_id": 123,                                          │  │
│  │      "price_per_unit": 25.00,                                    │  │
│  │      "stock_quantity": 100,                                      │  │
│  │      "confidence": 0.95                                          │  │
│  │    }                                                             │  │
│  └──────────────────────────────────────────────────────────────────┘  │
└────────────────────────────────┬────────────────────────────────────────┘
                                 │
                                 ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                     ENTITY VALIDATION                                    │
│  ┌──────────────────────────────────────────────────────────────────┐  │
│  │ Check completeness:                                              │  │
│  │ ✅ Product: "Dolo 650" (confidence 0.95 > 0.7) → Valid          │  │
│  │ ✅ Quantity: 10 (confidence 0.95 > 0.7) → Valid                 │  │
│  │ ✅ Customer: "Rahul" (confidence 0.85 > 0.7) → Valid            │  │
│  │                                                                  │  │
│  │ All entities valid → Can proceed                                │  │
│  └──────────────────────────────────────────────────────────────────┘  │
└────────────────────────────────┬────────────────────────────────────────┘
                                 │
                                 ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                    FSM STATE DETERMINATION                               │
│  ┌──────────────────────────────────────────────────────────────────┐  │
│  │ determine_next_state(entities, confidence)                       │  │
│  │                                                                  │  │
│  │ Decision tree:                                                   │  │
│  │ • Product missing/low conf? → NEED_PRODUCT                       │  │
│  │ • Quantity missing/low conf? → NEED_QUANTITY                     │  │
│  │ • Customer missing/low conf? → NEED_CUSTOMER (optional)          │  │
│  │ • All present with high conf? → READY_TO_CONFIRM ✅             │  │
│  │                                                                  │  │
│  │ Result: READY_TO_CONFIRM (skip all questions)                   │  │
│  └──────────────────────────────────────────────────────────────────┘  │
└────────────────────────────────┬────────────────────────────────────────┘
                                 │
                                 ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                      CONFIRMATION MESSAGE                                │
│  ┌──────────────────────────────────────────────────────────────────┐  │
│  │ Calculate billing:                                               │  │
│  │   unit_price = 25.00 (from resolved product)                     │  │
│  │   quantity = 10                                                  │  │
│  │   total = unit_price × quantity = 25.00 × 10 = 250.00           │  │
│  │                                                                  │  │
│  │ Build confirmation:                                              │  │
│  │   ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━                                │  │
│  │   📋 Order Confirmation                                          │  │
│  │   ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━                                │  │
│  │   🏪 Seller: Pharmacy                                            │  │
│  │   👤 Buyer: Rahul                                                │  │
│  │   📦 Product: Dolo 650                                           │  │
│  │   🔢 Quantity: 10 units                                          │  │
│  │   💰 Price: ₹25.00 × 10 = ₹250.00                               │  │
│  │   ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━                                │  │
│  │   ✅ Type 'confirm' to proceed                                   │  │
│  └──────────────────────────────────────────────────────────────────┘  │
└────────────────────────────────┬────────────────────────────────────────┘
                                 │
                                 ▼ User types "confirm"
┌─────────────────────────────────────────────────────────────────────────┐
│                      DRAFT CREATION                                      │
│  ┌──────────────────────────────────────────────────────────────────┐  │
│  │ validate_and_create_draft(...)                                   │  │
│  │                                                                  │  │
│  │ payload = {                                                      │  │
│  │   "seller": "Pharmacy",      # ✅ WHO IS SELLING (constant)      │  │
│  │   "buyer": "Rahul",          # ✅ WHO IS BUYING (from conv)      │  │
│  │   "customer_name": "Rahul",                                      │  │
│  │   "product": "Dolo 650",     # ✅ CANONICAL (never raw input)    │  │
│  │   "product_id": 123,                                             │  │
│  │   "quantity": 10,                                                │  │
│  │   "unit_price": 25.00,       # ✅ FROM INVENTORY                 │  │
│  │   "amount": 250.00,          # ✅ CALCULATED (25 × 10)           │  │
│  │   "requires_prescription": False                                 │  │
│  │ }                                                                │  │
│  │                                                                  │  │
│  │ status = "DRAFT" (requires owner approval)                       │  │
│  └──────────────────────────────────────────────────────────────────┘  │
└────────────────────────────────┬────────────────────────────────────────┘
                                 │
                                 ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                       OWNER APPROVAL                                     │
│  Draft stored in database, owner reviews on dashboard                   │
│  ✅ Owner clicks APPROVE → Executor runs → Invoice created              │
│  ❌ Owner clicks REJECT → Draft deleted                                 │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## PRODUCT RESOLUTION DETAIL

```
┌────────────────────────────────────────────────────────────────────┐
│                  USER INPUT: "dolo hai kya?"                        │
└───────────────────────────────┬────────────────────────────────────┘
                                │
                                ▼
                    ┌──────────────────────┐
                    │   NORMALIZATION      │
                    │                      │
                    │ 1. Lowercase         │
                    │    "DOLO" → "dolo"   │
                    │                      │
                    │ 2. Remove punctuation│
                    │    "dolo?" → "dolo"  │
                    │                      │
                    │ 3. Remove fillers    │
                    │    "dolo hai kya"    │
                    │    → "dolo"          │
                    └─────────┬────────────┘
                              │
                              ▼
                    ┌──────────────────────┐
                    │  INVENTORY SEARCH    │
                    │                      │
                    │ Query all products   │
                    │ for business         │
                    │                      │
                    │ Products:            │
                    │ - Dolo 650           │
                    │ - Paracetamol 500mg  │
                    │ - Azithromycin 500mg │
                    │ - ...                │
                    └─────────┬────────────┘
                              │
                              ▼
                    ┌──────────────────────┐
                    │ CONFIDENCE SCORING   │
                    │                      │
                    │ For each product:    │
                    │                      │
                    │ "dolo" vs "Dolo 650" │
                    │ → Confidence: 0.95   │
                    │   (contains match)   │
                    │                      │
                    │ "dolo" vs "Para..."  │
                    │ → Confidence: 0.1    │
                    │   (no match)         │
                    └─────────┬────────────┘
                              │
                              ▼
                    ┌──────────────────────┐
                    │  BEST MATCH          │
                    │                      │
                    │ Best: "Dolo 650"     │
                    │ Confidence: 0.95     │
                    │                      │
                    │ Threshold: 0.7       │
                    │ 0.95 > 0.7 ✅        │
                    └─────────┬────────────┘
                              │
                              ▼
            ┌────────────────────────────────────────────┐
            │      CANONICAL PRODUCT MODEL                │
            │                                            │
            │  {                                         │
            │    "product_id": 123,                      │
            │    "canonical_name": "Dolo 650",           │
            │    "price_per_unit": 25.00,                │
            │    "stock_quantity": 100,                  │
            │    "requires_prescription": False,         │
            │    "confidence": 0.95                      │
            │  }                                         │
            │                                            │
            │  ✅ NEVER contains raw user input          │
            └────────────────────────────────────────────┘
```

---

## CONFIDENCE-BASED FLOW CONTROL

```
┌─────────────────────────────────────────────────────────────────────┐
│           EXTRACTED ENTITIES WITH CONFIDENCE                         │
│                                                                     │
│  Product:  "Dolo"      Confidence: 0.95  [████████████████████░]   │
│  Quantity: 10          Confidence: 0.95  [████████████████████░]   │
│  Customer: "Rahul"     Confidence: 0.85  [█████████████████░░░]    │
└────────────────────────────────┬────────────────────────────────────┘
                                 │
                                 ▼
                    ┌─────────────────────────┐
                    │  CONFIDENCE CHECK        │
                    │  Threshold: 0.8          │
                    └─────────────────────────┘
                                 │
                    ┌────────────┴────────────┐
                    │                         │
                    ▼                         ▼
        ┌────────────────────┐    ┌────────────────────┐
        │  HIGH CONFIDENCE   │    │  LOW CONFIDENCE    │
        │     (≥ 0.8)        │    │     (< 0.8)        │
        │                    │    │                    │
        │  ✅ Auto-fill      │    │  ❌ Ask question   │
        │  ✅ Skip question  │    │                    │
        └────────────────────┘    └────────────────────┘

Example Flow:

┌──────────────────────────────────────────────────────────────────┐
│  Input: "Rahul ko 10 Dolo 650"                                   │
├──────────────────────────────────────────────────────────────────┤
│  Product: 0.95 > 0.8  ✅ SKIP "What product?" question          │
│  Quantity: 0.95 > 0.8 ✅ SKIP "What quantity?" question         │
│  Customer: 0.85 > 0.8 ✅ SKIP "What customer?" question         │
├──────────────────────────────────────────────────────────────────┤
│  Result: Go directly to CONFIRMATION                             │
│  Messages: 1 (confirm) instead of 4 (product + qty + cust + cfm)│
│  Reduction: 75% fewer messages ✅                                │
└──────────────────────────────────────────────────────────────────┘

vs.

┌──────────────────────────────────────────────────────────────────┐
│  Input: "order"                                                   │
├──────────────────────────────────────────────────────────────────┤
│  Product: 0.0 < 0.8   ❌ ASK "What product?"                    │
│  Quantity: 0.0 < 0.8  ❌ ASK "What quantity?"                   │
│  Customer: 0.3 < 0.8  ❌ ASK "What customer?"                   │
├──────────────────────────────────────────────────────────────────┤
│  Result: Ask all 3 questions                                     │
│  Messages: 4 (product + qty + customer + confirm)                │
└──────────────────────────────────────────────────────────────────┘
```

---

## ROLE SEPARATION MODEL

```
┌─────────────────────────────────────────────────────────────────────┐
│                          TRANSACTION MODEL                           │
│                                                                     │
│  ┌──────────────────┐              ┌──────────────────┐            │
│  │                  │              │                  │            │
│  │    PHARMACY      │   ──────→    │    CUSTOMER      │            │
│  │   (Seller)       │   Goods      │    (Buyer)       │            │
│  │                  │   ←──────    │                  │            │
│  │   CONSTANT       │   Payment    │    VARIABLE      │            │
│  │   (always same)  │              │  (from message)  │            │
│  │                  │              │                  │            │
│  └──────────────────┘              └──────────────────┘            │
│                                                                     │
│  Rules:                                                             │
│  1. Seller is ALWAYS "Pharmacy" (who owns the business)            │
│  2. Buyer is ALWAYS customer name (from conversation)              │
│  3. These roles are NEVER confused or swapped                      │
│  4. Every transaction explicitly states both roles                 │
└─────────────────────────────────────────────────────────────────────┘

Example Invoice:

┌─────────────────────────────────────────────────────────────────────┐
│                          INVOICE #123                                │
├─────────────────────────────────────────────────────────────────────┤
│  FROM (Seller):  Pharmacy ✅                                        │
│  TO (Buyer):     Rahul ✅                                           │
│                                                                     │
│  Product:        Dolo 650                                           │
│  Quantity:       10 units                                           │
│  Unit Price:     ₹25.00                                             │
│  Total:          ₹250.00                                            │
├─────────────────────────────────────────────────────────────────────┤
│  Ledger Entry:                                                      │
│    DEBIT  → Rahul (buyer owes)                                     │
│    CREDIT → Pharmacy (seller receives)                             │
└─────────────────────────────────────────────────────────────────────┘

❌ NEVER:
  - Seller: Rahul, Buyer: Pharmacy
  - Seller: Customer, Buyer: Customer
  - Undefined roles
```

---

## DETERMINISTIC BILLING

```
┌─────────────────────────────────────────────────────────────────────┐
│                    BILLING CALCULATION FLOW                          │
└─────────────────────────────────┬───────────────────────────────────┘
                                  │
                                  ▼
                    ┌──────────────────────────┐
                    │  Get Product from DB     │
                    │                          │
                    │  product = Inventory     │
                    │    .filter(name="Dolo")  │
                    │    .first()              │
                    │                          │
                    │  product.price = 25.00   │
                    └─────────┬────────────────┘
                              │
                              ▼
                    ┌──────────────────────────┐
                    │  Extract Unit Price      │
                    │                          │
                    │  unit_price =            │
                    │    float(product.price)  │
                    │                          │
                    │  unit_price = 25.00      │
                    └─────────┬────────────────┘
                              │
                              ▼
                    ┌──────────────────────────┐
                    │  Get Quantity            │
                    │                          │
                    │  quantity = 10           │
                    └─────────┬────────────────┘
                              │
                              ▼
                    ┌──────────────────────────┐
                    │  Calculate Total         │
                    │                          │
                    │  amount =                │
                    │    unit_price × quantity │
                    │                          │
                    │  amount = 25.00 × 10     │
                    │         = 250.00         │
                    └─────────┬────────────────┘
                              │
                              ▼
                    ┌──────────────────────────┐
                    │  Show Calculation        │
                    │                          │
                    │  "₹25.00 × 10 = ₹250.00" │
                    │                          │
                    │  ✅ Transparent          │
                    │  ✅ Auditable            │
                    │  ✅ Verifiable           │
                    └──────────────────────────┘

❌ NEVER:
  - amount = 500  (magic number)
  - amount = some_calculation_without_showing
  - Use hardcoded values
```

This is the complete refactoring with all documentation! 🎉
