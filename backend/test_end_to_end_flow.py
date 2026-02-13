"""
END-TO-END TEST: Simulate exact Telegram flow

This test simulates the EXACT flow:
1. User types "Benadryl" 
2. Product is resolved and stored in conversation context
3. Context is saved to database
4. Context is loaded back from database
5. Order is confirmed
6. Draft is created with correct product

This catches any serialization/deserialization issues with product_id.
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__)))

from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from app.db.base import Base
from app.models.user import User
from app.models.business import Business
from app.models.inventory import Inventory
from app.models.conversation_state import ConversationState as DBConversationState
from app.models.agent_action import AgentAction
from app.services.product_resolver import resolve_product
from app.agent.decision_engine import validate_and_create_draft
import json
from decimal import Decimal

def setup_test_db():
    """Create in-memory DB with test data"""
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    db = Session(engine)
    
    # Create user
    user = User(id=1, email="test@example.com", hashed_password="dummy", name="Owner")
    db.add(user)
    
    # Create business
    business = Business(id=1, owner_id=1, name="Test Pharmacy")
    db.add(business)
    
    # Create inventory
    products = [
        (1, "Paracetamol 500mg", 2.50),
        (2, "Vitamin D3 60K", 35.00),  # Lower ID
        (3, "Benadryl Cough Syrup", 95.00),  # Higher ID
        (4, "Vitamin B Complex", 18.00),
    ]
    for id, name, price in products:
        db.add(Inventory(id=id, business_id=1, item_name=name, price=price, quantity=100, requires_prescription=False))
    
    db.commit()
    return db, business


def convert_decimals(obj):
    """Convert Decimal to float for JSON"""
    if isinstance(obj, dict):
        return {k: convert_decimals(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [convert_decimals(v) for v in obj]
    elif isinstance(obj, Decimal):
        return float(obj)
    return obj


def test_end_to_end_flow():
    """Simulate exact Telegram flow"""
    print("\n" + "="*70)
    print("END-TO-END TEST: TELEGRAM FLOW SIMULATION")
    print("="*70)
    
    db, business = setup_test_db()
    chat_id = "123456789"
    
    # ==== STEP 1: User types "Benadryl" ====
    print("\n[STEP 1] User types: 'Benadryl'")
    user_input = "Benadryl"
    
    # Resolve product (exactly like handlers_refactored does)
    resolved = resolve_product(db, business.id, user_input, min_confidence=0.7)
    
    assert resolved is not None, "Product should resolve"
    assert resolved["product_id"] == 3, f"Should be Benadryl (ID=3), got ID={resolved['product_id']}"
    assert "Benadryl" in resolved["canonical_name"], "Should be Benadryl"
    
    print(f"   Resolved: {resolved['canonical_name']} (product_id={resolved['product_id']})")
    
    # ==== STEP 2: Store in conversation context ====
    print("\n[STEP 2] Store in conversation context")
    
    context = {
        "state": "ready_to_confirm",
        "entities": {
            "product": resolved,  # Full resolved dict with product_id
            "quantity": 10,
            "customer": "Test Customer"
        },
        "raw_inputs": {"product_input": user_input},
        "confidence": {"product": resolved["confidence"], "quantity": 0.95, "customer": 0.9}
    }
    
    # Verify product_id is in context
    assert context["entities"]["product"]["product_id"] == 3, "product_id must be 3"
    print(f"   Context product_id: {context['entities']['product']['product_id']}")
    
    # ==== STEP 3: Save to database (simulating JSON serialization) ====
    print("\n[STEP 3] Save to database (JSON serialization)")
    
    # Convert Decimals
    clean_context = convert_decimals(context)
    
    # Simulate saving to DB
    record = DBConversationState(
        chat_id=chat_id,
        state=clean_context["state"],
        payload=clean_context
    )
    db.add(record)
    db.commit()
    
    # Verify product_id survived serialization
    saved_record = db.query(DBConversationState).filter_by(chat_id=chat_id).first()
    saved_product_id = saved_record.payload["entities"]["product"]["product_id"]
    assert saved_product_id == 3, f"Saved product_id should be 3, got {saved_product_id}"
    print(f"   Saved product_id: {saved_product_id}")
    
    # ==== STEP 4: Load back from database ====
    print("\n[STEP 4] Load from database")
    
    loaded_record = db.query(DBConversationState).filter_by(chat_id=chat_id).first()
    loaded_context = loaded_record.payload
    
    loaded_product = loaded_context["entities"]["product"]
    loaded_product_id = loaded_product.get("product_id")
    
    assert loaded_product_id == 3, f"Loaded product_id should be 3, got {loaded_product_id}"
    print(f"   Loaded product_id: {loaded_product_id}")
    print(f"   Loaded product: {loaded_product['canonical_name']}")
    
    # ==== STEP 5: Create draft (exactly like handle_order_confirm) ====
    print("\n[STEP 5] Create draft")
    
    product = loaded_context["entities"]["product"]
    quantity = loaded_context["entities"]["quantity"]
    customer = loaded_context["entities"]["customer"]
    
    # Get product_id from context
    product_id = product.get("product_id") if isinstance(product, dict) else None
    canonical_name = product.get("canonical_name") if isinstance(product, dict) else str(product)
    
    print(f"   product_id={product_id}, name='{canonical_name}', qty={quantity}")
    
    # Verify product exists in DB
    item = db.query(Inventory).filter(
        Inventory.id == product_id,
        Inventory.business_id == business.id
    ).first()
    
    assert item is not None, "Product must exist in database"
    assert item.item_name == "Benadryl Cough Syrup", f"Must be Benadryl, got {item.item_name}"
    print(f"   DB verification: {item.item_name} (ID={item.id})")
    
    # Create draft
    draft = validate_and_create_draft(
        db=db,
        business_id=business.id,
        raw_message=f"{customer} wants {quantity} {item.item_name}",
        telegram_chat_id=chat_id,
        intent="create_invoice",
        product=item.item_name,
        product_id=product_id,
        quantity=quantity,
        customer=customer,
        requires_prescription=False
    )
    
    assert draft is not None, "Draft must be created"
    assert draft.payload["product_id"] == 3, f"Draft product_id must be 3, got {draft.payload['product_id']}"
    assert draft.payload["product"] == "Benadryl Cough Syrup", f"Draft product must be Benadryl, got {draft.payload['product']}"
    assert "Vitamin" not in draft.payload["product"], "Must NOT have Vitamin in name"
    
    print(f"\n   ✅ DRAFT CREATED:")
    print(f"      Product: {draft.payload['product']}")
    print(f"      Product ID: {draft.payload['product_id']}")
    print(f"      Quantity: {draft.payload['quantity']}")
    print(f"      Amount: ₹{draft.payload['amount']:.2f}")
    
    # ==== STEP 6: Verify final draft in database ====
    print("\n[STEP 6] Verify draft in database")
    
    final_draft = db.query(AgentAction).filter_by(id=draft.id).first()
    
    assert final_draft.payload["product_id"] == 3, "Final DB check: product_id must be 3"
    assert final_draft.payload["product"] == "Benadryl Cough Syrup", "Final DB check: must be Benadryl"
    
    print(f"   Final verification: {final_draft.payload['product']} (ID={final_draft.payload['product_id']})")
    
    print("\n" + "="*70)
    print("END-TO-END TEST: PASSED ✅")
    print("="*70)
    print("\nFlow verified:")
    print("  1. User input 'Benadryl' → Resolved to product_id=3")
    print("  2. Stored in context with product_id=3")
    print("  3. Saved to database (JSON serialized)")
    print("  4. Loaded from database with product_id=3 intact")
    print("  5. Draft created with product_id=3")
    print("  6. Final DB verification: Benadryl (ID=3)")
    print("\n🔒 The product_id flow is BULLETPROOF!")
    
    db.close()


if __name__ == "__main__":
    test_end_to_end_flow()
