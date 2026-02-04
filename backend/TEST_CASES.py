"""
COMPREHENSIVE TEST CASES FOR REFACTORED BOT

These test cases MUST pass to ensure correctness
"""

# ==============================================================================
# 🔴 CRITICAL BUG TESTS - These MUST NOT fail
# ==============================================================================

CRITICAL_TESTS = {
    "product_resolution": [
        {
            "name": "User text never appears in invoice",
            "input": "dolo hai kya?",
            "expected_canonical": "Dolo 650",
            "must_not_contain": ["dolo hai kya", "hai", "kya"]
        },
        {
            "name": "Case insensitive matching",
            "input": "PARACETAMOL",
            "expected_canonical": "Paracetamol 500mg",
            "confidence_min": 0.8
        },
        {
            "name": "Alias resolution",
            "input": "crocin",
            "expected_canonical": "Paracetamol 500mg",
            "confidence_min": 0.7
        }
    ],
    
    "role_separation": [
        {
            "name": "Seller always pharmacy",
            "input": "Rahul ko 10 Dolo",
            "expected_seller": "Pharmacy",
            "expected_buyer": "Rahul",
            "must_never": "seller=customer or buyer=pharmacy"
        },
        {
            "name": "Self-reference maps to buyer",
            "input": "mujhe 5 Paracetamol",
            "expected_seller": "Pharmacy",
            "expected_buyer": "Owner"  # or walk-in
        }
    ],
    
    "deterministic_billing": [
        {
            "name": "Price must be unit_price × quantity",
            "product": "Paracetamol 500mg",
            "unit_price": 5.00,
            "quantity": 10,
            "expected_total": 50.00,
            "must_not_be": [500, 100, 5]  # No magic numbers
        },
        {
            "name": "No hardcoded amounts",
            "product": "Dolo 650",
            "unit_price": 25.00,
            "quantity": 2,
            "expected_total": 50.00,
            "calculation_must_show": "25.00 × 2 = 50.00"
        }
    ],
    
    "confidence_based_skip": [
        {
            "name": "High confidence entity skips question",
            "input": "10 Dolo Rahul ko",
            "extracted": {
                "product": {"value": "Dolo", "confidence": 0.95},
                "quantity": {"value": 10, "confidence": 0.95},
                "customer": {"value": "Rahul", "confidence": 0.85}
            },
            "expected_questions": [],  # No questions needed
            "goes_directly_to": "confirm"
        },
        {
            "name": "Low confidence asks question",
            "input": "order",
            "extracted": {
                "product": {"value": None, "confidence": 0.0}
            },
            "expected_question": "📦 Kaun sa medicine chahiye?"
        }
    ],
    
    "fsm_entity_first": [
        {
            "name": "FSM only triggers with validated entities",
            "input": "chahiye",  # Order keyword
            "entities_validated": False,
            "expected_behavior": "ask for product, NOT transition to ordering"
        },
        {
            "name": "FSM transitions after validation",
            "input": "10 Dolo",
            "entities": {"product": "Dolo 650", "quantity": 10},
            "entities_validated": True,
            "expected_state": "READY_TO_CONFIRM"
        }
    ]
}


# ==============================================================================
# 🟡 GENERALIZATION TESTS - Why bot failed before
# ==============================================================================

GENERALIZATION_TESTS = {
    "variant_handling": [
        # Query variants
        {"input": "fever ka medicine hai?", "should_map_to": "symptom_query"},
        {"input": "paracetamol hai kya?", "should_map_to": "stock_query"},
        {"input": "bukhar", "should_map_to": "symptom_query"},
        
        # Order variants
        {"input": "Rahul ko 10 dolo 650", "entities": {"customer": "Rahul", "qty": 10, "product": "Dolo 650"}},
        {"input": "10 Paracetamol Rahul ke liye", "entities": {"customer": "Rahul", "qty": 10, "product": "Paracetamol"}},
        {"input": "mujhe ek Dolo chahiye", "entities": {"customer": "Self/Owner", "qty": 1, "product": "Dolo"}},
        
        # Punctuation variants
        {"input": "dolo 650?", "should_resolve_to": "Dolo 650"},
        {"input": "Dolo-650", "should_resolve_to": "Dolo 650"},
        {"input": "DOLO 650!", "should_resolve_to": "Dolo 650"},
        
        # Quantity variants
        {"input": "ek", "quantity": 1},
        {"input": "one", "quantity": 1},
        {"input": "10", "quantity": 10},
        {"input": "das", "quantity": 10},
        {"input": "only one", "quantity": 1},
    ],
    
    "context_preservation": [
        {
            "name": "Query doesn't kill order",
            "flow": [
                {"input": "10 Dolo", "state": "ordering"},
                {"input": "Paracetamol hai?", "state": "should_still_be_ordering"},
                {"input": "Rahul", "state": "should_complete_original_order"}
            ]
        },
        {
            "name": "Context carries forward",
            "flow": [
                {"input": "Dolo", "context": {"product": "Dolo 650"}},
                {"input": "10", "context": {"product": "Dolo 650", "quantity": 10}},
                {"input": "confirm", "completes": True}
            ]
        }
    ]
}


# ==============================================================================
# 🧪 EDGE CASES - These MUST be handled
# ==============================================================================

EDGE_CASES = {
    "ambiguous_input": [
        {"input": "para", "multiple_matches": ["Paracetamol 500mg", "Paracetamol 650mg"], "behavior": "show_options"},
        {"input": "dolo", "matches": "Dolo 650", "confidence": 0.9},
        {"input": "medicine", "matches": None, "behavior": "ask_for_specific_name"}
    ],
    
    "invalid_quantities": [
        {"input": "0 Dolo", "error": "Quantity must be > 0"},
        {"input": "-5 Paracetamol", "error": "Quantity must be positive"},
        {"input": "100000 Dolo", "warning": "Quantity too high, confirm?"}
    ],
    
    "out_of_stock": [
        {"product": "Dolo 650", "stock": 0, "behavior": "show_error_and_suggest_alternatives"},
        {"product": "Paracetamol", "stock": 5, "quantity_requested": 10, "behavior": "insufficient_stock_warning"}
    ],
    
    "prescription_required": [
        {
            "product": "Azithromycin 500mg",
            "requires_prescription": True,
            "behavior": "flag_draft_with_warning",
            "owner_must": "verify_prescription_before_approval"
        }
    ],
    
    "interruptions": [
        {"flow": "ordering", "interrupt": "cancel", "behavior": "reset_to_idle"},
        {"flow": "ordering", "interrupt": "help", "behavior": "show_help_keep_context"},
        {"flow": "confirming", "interrupt": "stock check", "behavior": "answer_then_return"}
    ],
    
    "customer_variants": [
        {"input": "mujhe", "customer": "Owner"},
        {"input": "Rahul ko", "customer": "Rahul"},
        {"input": "for Priya", "customer": "Priya"},
        {"input": "", "customer": "Walk-in Customer"},  # Default
        {"input": "Ramesh bhai ko", "customer": "Ramesh"}
    ],
    
    "multiword_products": [
        {"input": "Dolo 650", "canonical": "Dolo 650"},
        {"input": "Azithromycin 500 mg", "canonical": "Azithromycin 500mg"},
        {"input": "Vitamin B Complex", "canonical": "Vitamin B Complex"}
    ]
}


# ==============================================================================
# 📊 INVOICE CORRECTNESS TESTS
# ==============================================================================

INVOICE_TESTS = [
    {
        "name": "Simple order",
        "input": "Rahul ko 10 Dolo 650",
        "inventory": {"Dolo 650": {"price": 25.00, "stock": 100}},
        "expected_invoice": {
            "seller": "Pharmacy",
            "buyer": "Rahul",
            "product": "Dolo 650",  # Canonical
            "quantity": 10,
            "unit_price": 25.00,
            "total": 250.00,  # 25 × 10
            "calculation_shown": True
        }
    },
    {
        "name": "Self-reference order",
        "input": "mujhe 5 Paracetamol",
        "inventory": {"Paracetamol 500mg": {"price": 5.00, "stock": 50}},
        "expected_invoice": {
            "seller": "Pharmacy",
            "buyer": "Owner",
            "product": "Paracetamol 500mg",
            "quantity": 5,
            "unit_price": 5.00,
            "total": 25.00
        }
    },
    {
        "name": "Walk-in customer",
        "input": "10 Dolo",
        "inventory": {"Dolo 650": {"price": 25.00, "stock": 100}},
        "expected_invoice": {
            "seller": "Pharmacy",
            "buyer": "Walk-in Customer",
            "product": "Dolo 650",
            "quantity": 10,
            "unit_price": 25.00,
            "total": 250.00
        }
    }
]


# ==============================================================================
# 🔄 STATE MACHINE TESTS
# ==============================================================================

FSM_TESTS = [
    {
        "name": "Complete flow: all entities in one message",
        "input": "Rahul ko 10 Dolo 650",
        "expected_flow": [
            "IDLE → extract entities",
            "All entities high confidence",
            "Skip all questions",
            "Go directly to READY_TO_CONFIRM"
        ]
    },
    {
        "name": "Partial flow: missing quantity",
        "messages": [
            {"input": "Dolo", "state": "NEED_QUANTITY"},
            {"input": "10", "state": "READY_TO_CONFIRM"}
        ]
    },
    {
        "name": "Interruption handling",
        "messages": [
            {"input": "10 Dolo", "state": "NEED_CUSTOMER"},
            {"input": "Paracetamol hai?", "answer_query": True, "state": "still_NEED_CUSTOMER"},
            {"input": "Rahul", "state": "READY_TO_CONFIRM"}
        ]
    }
]


# ==============================================================================
# 🎯 SUCCESS CRITERIA
# ==============================================================================

SUCCESS_CRITERIA = """
ALL of the following MUST be true:

✅ Product Resolution:
   - User text NEVER appears in invoice
   - All products resolved to canonical names
   - Confidence scores accurate (tested against known cases)

✅ Role Separation:
   - Seller is ALWAYS "Pharmacy" 
   - Buyer is ALWAYS customer name (from conversation)
   - NEVER confused or swapped

✅ Deterministic Billing:
   - Total = unit_price × quantity (ALWAYS)
   - No magic numbers (500, 100, etc.)
   - Calculation visible and verifiable

✅ Confidence-Based Flow:
   - High confidence (>0.8) → auto-fill, skip question
   - Low confidence (<0.5) → ask question
   - Reduces redundant questions by ~60%

✅ Entity-First FSM:
   - FSM transitions only after entity validation
   - No keyword-based premature transitions
   - Context preserved across queries

✅ Generalization:
   - Handles: "fever hai", "paracetamol", "Rahul ko 10 dolo"
   - Case insensitive
   - Punctuation agnostic
   - Supports Hindi, English, Hinglish
"""


# ==============================================================================
# 🚨 FAILURE SCENARIOS (Old system)
# ==============================================================================

OLD_SYSTEM_FAILURES = """
These scenarios FAILED in old system, MUST PASS now:

1. "fever ka medicine hai?"
   OLD: Didn't understand
   NEW: Maps to symptom query, shows relevant medicines

2. "paracetamol hai kya?"
   OLD: Sometimes worked, sometimes didn't
   NEW: Consistently resolves to canonical product

3. "Rahul ko 10 dolo 650"
   OLD: Invoice showed "Rahul" as seller sometimes
   NEW: Seller=Pharmacy, Buyer=Rahul (correct)

4. "dolo?" (with punctuation)
   OLD: Broke regex matching
   NEW: Normalized, resolves correctly

5. Query during order
   OLD: Lost order context
   NEW: Answers query, preserves order state

6. "mujhe Dolo"
   OLD: Customer = "mujhe" (raw text in invoice)
   NEW: Customer = "Owner" (resolved)

7. Invoice shows "₹500" without calculation
   OLD: Magic number
   NEW: Shows "₹25 × 10 = ₹250" (deterministic)
"""
