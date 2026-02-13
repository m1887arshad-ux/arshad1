"""
Test script to verify all AI module fixes.

Tests:
1. Entity field validations (string length, quantity bounds)
2. Content type classifications
3. Schema flattening via to_dict()
4. Handler compatibility
5. Fallback parser integration
"""

import json
import sys
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent))

from ai.intent_schema import (
    ParsedIntent, Entities, IntentType, ContentType, ConfidenceLevel
)
from ai.prompts import build_prompt


def test_entity_validation():
    """Test entity field validation constraints."""
    print("\n" + "="*70)
    print("TEST 1: Entity Field Validation")
    print("="*70)
    
    # Test 1.1: Valid entities
    print("\n✓ Test 1.1: Valid entities")
    e1 = Entities(product="Paracetamol", quantity=10, customer="Rahul")
    assert e1.product == "Paracetamol"
    assert e1.quantity == 10
    assert e1.customer == "Rahul"
    print("  PASS: Valid entities accepted")
    
    # Test 1.2: Reject single character product names
    print("\n✓ Test 1.2: Reject single character product names")
    e2 = Entities(product="A")
    assert e2.product is None, "Expected single-char product to be rejected"
    print("  PASS: Single character product rejected")
    
    # Test 1.3: Reject too-long strings (>100 chars)
    print("\n✓ Test 1.3: Reject too-long strings")
    long_name = "A" * 101
    e3 = Entities(product=long_name)
    assert e3.product is None, "Expected >100 char product to be rejected"
    print("  PASS: Over-length product rejected")
    
    # Test 1.4: Reject negative quantities
    print("\n✓ Test 1.4: Reject negative quantities")
    e4 = Entities(quantity=-5)
    assert e4.quantity is None, "Expected negative quantity to be rejected"
    print("  PASS: Negative quantity rejected")
    
    # Test 1.5: Reject zero quantity
    print("\n✓ Test 1.5: Reject zero quantity")
    e5 = Entities(quantity=0)
    assert e5.quantity is None, "Expected zero quantity to be rejected"
    print("  PASS: Zero quantity rejected")
    
    # Test 1.6: Reject unrealistic quantities (>100000)
    print("\n✓ Test 1.6: Reject unrealistic quantities")
    e6 = Entities(quantity=100001)
    assert e6.quantity is None, "Expected >100000 quantity to be rejected"
    print("  PASS: Unrealistic quantity rejected")
    
    # Test 1.7: Reject fractional quantities
    print("\n✓ Test 1.7: Reject fractional quantities")
    e7 = Entities(quantity=3.5)
    assert e7.quantity is None, "Expected fractional quantity to be rejected"
    print("  PASS: Fractional quantity rejected")
    
    # Test 1.8: Accept boundary values
    print("\n✓ Test 1.8: Accept boundary values")
    e8 = Entities(product="HP", quantity=100000.0, customer="XX")
    assert e8.product == "HP", "2-char product should be accepted"
    assert e8.quantity == 100000, "Max quantity should be accepted"
    assert e8.customer == "XX", "2-char customer should be accepted"
    print("  PASS: Boundary values accepted")
    
    # Test 1.9: Strip whitespace
    print("\n✓ Test 1.9: Whitespace stripping")
    e9 = Entities(product="  Dolo 650  ", customer="  Rahul  ")
    assert e9.product == "Dolo 650", "Product whitespace not stripped"
    assert e9.customer == "Rahul", "Customer whitespace not stripped"
    print("  PASS: Whitespace properly stripped")
    
    print("\n✅ All entity validation tests PASSED")


def test_schema_flattening():
    """Test that ParsedIntent.to_dict() properly flattens nested entities."""
    print("\n" + "="*70)
    print("TEST 2: Schema Flattening via to_dict()")
    print("="*70)
    
    # Create a ParsedIntent with nested entities
    parsed = ParsedIntent(
        normalized_text="Create invoice for Rahul with 10 Dolo",
        content_type=ContentType.BUSINESS_ACTION,
        intent=IntentType.CREATE_INVOICE,
        entities=Entities(product="Dolo 650", quantity=10, customer="Rahul"),
        confidence=ConfidenceLevel.HIGH
    )
    
    # Convert to dict
    result = parsed.to_dict()
    
    print("\nFlattened output:")
    print(json.dumps(result, indent=2))
    
    # Verify flattening
    print("\n✓ Test 2.1: Top-level entity fields exist")
    assert "product" in result, "product should be at top level"
    assert "quantity" in result, "quantity should be at top level"
    assert "customer" in result, "customer should be at top level"
    print("  PASS: Entity fields flattened to top level")
    
    print("\n✓ Test 2.2: Entity values are correct")
    assert result["product"] == "Dolo 650", "Product value incorrect"
    assert result["quantity"] == 10, "Quantity value incorrect"
    assert result["customer"] == "Rahul", "Customer value incorrect"
    print("  PASS: Entity values preserved correctly")
    
    print("\n✓ Test 2.3: Metadata fields present")
    assert result["normalized_text"] == "Create invoice for Rahul with 10 Dolo"
    assert result["content_type"] == "business_action"
    assert result["intent"] == "create_invoice"
    assert result["confidence"] == "high"
    print("  PASS: Metadata fields preserved")
    
    print("\n✅ All schema flattening tests PASSED")


def test_content_type_enforcement():
    """Test model_validator for content_type and intent alignment."""
    print("\n" + "="*70)
    print("TEST 3: Content Type and Intent Alignment")
    print("="*70)
    
    # Test 3.1: Business action with valid intent
    print("\n✓ Test 3.1: Business action with valid intent")
    p1 = ParsedIntent(
        content_type=ContentType.BUSINESS_ACTION,
        intent=IntentType.CHECK_STOCK
    )
    assert p1.intent == IntentType.CHECK_STOCK, "Intent should be preserved"
    print("  PASS: Valid business_action intent preserved")
    
    # Test 3.2: Non-business content forces intent to UNKNOWN
    print("\n✓ Test 3.2: Non-business content forces intent to UNKNOWN")
    p2 = ParsedIntent(
        content_type=ContentType.MEDICAL_QUERY,
        intent=IntentType.CHECK_STOCK  # Try to set intent for non-business
    )
    # Model validator should force intent to None
    assert p2.intent is None, "Intent should be None for non-business content"
    result = p2.to_dict()
    assert result["intent"] == "unknown", "to_dict() should return UNKNOWN"
    print("  PASS: Intent forced to None for non-business content")
    
    # Test 3.3: All content types supported
    print("\n✓ Test 3.3: All content types supported")
    for content_type in ContentType:
        p = ParsedIntent(content_type=content_type)
        if content_type != ContentType.BUSINESS_ACTION:
            assert p.intent is None, f"Intent should be None for {content_type}"
        print(f"  ✓ {content_type.value}")
    print("  PASS: All content types handled correctly")
    
    print("\n✅ All content type tests PASSED")


def test_confidence_levels():
    """Test confidence level enum and is_high_confidence() method."""
    print("\n" + "="*70)
    print("TEST 4: Confidence Levels and Methods")
    print("="*70)
    
    print("\n✓ Test 4.1: Confidence levels enum")
    p_low = ParsedIntent(confidence=ConfidenceLevel.LOW)
    p_med = ParsedIntent(confidence=ConfidenceLevel.MEDIUM)
    p_high = ParsedIntent(confidence=ConfidenceLevel.HIGH)
    
    assert not p_low.is_high_confidence(), "LOW confidence should return False"
    assert not p_med.is_high_confidence(), "MEDIUM confidence should return False"
    assert p_high.is_high_confidence(), "HIGH confidence should return True"
    print("  PASS: is_high_confidence() works correctly")
    
    print("\n✓ Test 4.2: Actionable check")
    p1 = ParsedIntent(
        intent=IntentType.CHECK_STOCK,
        entities=Entities(product="Dolo")
    )
    assert p1.is_actionable(), "Stock check with product is actionable"
    
    p2 = ParsedIntent(
        intent=IntentType.CHECK_STOCK,
        entities=Entities()  # No product
    )
    assert not p2.is_actionable(), "Stock check without product is not actionable"
    
    p3 = ParsedIntent(
        intent=IntentType.CREATE_INVOICE,
        entities=Entities(customer="Rahul")
    )
    assert p3.is_actionable(), "Invoice with customer is actionable"
    print("  PASS: is_actionable() works correctly")
    
    print("\n✅ All confidence tests PASSED")


def test_build_prompt():
    """Test prompt building with context injection."""
    print("\n" + "="*70)
    print("TEST 5: Prompt Building with Context")
    print("="*70)
    
    print("\n✓ Test 5.1: Basic prompt building")
    prompt = build_prompt("Paracetamol ki stock batao")
    assert "Paracetamol ki stock batao" in prompt, "User message should be in prompt"
    assert "SYSTEM_PROMPT" not in prompt, "Should include SYSTEM_PROMPT but not the literal string"
    assert "semantic normalization" in prompt.lower(), "Should include system instructions"
    print("  PASS: Basic prompt built correctly")
    
    print("\n✓ Test 5.2: Prompt with context")
    context = {
        "last_product": "Dolo 650",
        "last_customer": "Rahul",
        "last_quantity": 10
    }
    prompt = build_prompt("same one", context=context)
    assert json.dumps(context) in prompt, "Context should be JSON-serialized in prompt"
    assert "last_product" in prompt, "Context fields should be present"
    print("  PASS: Context properly injected into prompt")
    
    print("\n✓ Test 5.3: Empty context handling")
    prompt = build_prompt("Dolo hai?", context=None)
    assert "Dolo hai?" in prompt, "Message should be present"
    print("  PASS: Empty context handled gracefully")
    
    print("\n✅ All prompt building tests PASSED")


def test_schema_output_compatibility():
    """Test that output format works with handler expectations."""
    print("\n" + "="*70)
    print("TEST 6: Handler Compatibility Check")
    print("="*70)
    
    # Simulate what handlers.py line 591-594 does
    parsed = ParsedIntent(
        content_type=ContentType.BUSINESS_ACTION,
        intent=IntentType.CREATE_INVOICE,
        entities=Entities(product="Dolo 650", quantity=10, customer="Rahul"),
        confidence=ConfidenceLevel.HIGH
    )
    
    groq_result = parsed.to_dict()
    groq_result["source"] = "llm"  # This is added after to_dict()
    
    # Handler code that expects these fields
    print("\n✓ Test 6.1: Handler field extraction")
    intent = groq_result.get("intent", "unknown")
    product = groq_result.get("product")
    customer = groq_result.get("customer")
    quantity = groq_result.get("quantity")
    confidence = groq_result.get("confidence", "low")
    content_type = groq_result.get("content_type", "unknown")
    
    assert intent == "create_invoice", "Intent extraction failed"
    assert product == "Dolo 650", "Product extraction failed"
    assert customer == "Rahul", "Customer extraction failed"
    assert quantity == 10, "Quantity extraction failed"
    assert confidence == "high", "Confidence extraction failed"
    assert content_type == "business_action", "Content type extraction failed"
    print("  PASS: All handler field extractions work")
    
    print("\n✓ Test 6.2: Validate output has source field")
    assert groq_result.get("source") == "llm", "Source field missing"
    print("  PASS: Source field present for audit trail")
    
    print("\n✅ All handler compatibility tests PASSED")


def main():
    """Run all tests."""
    print("\n" + "🧪 "*35)
    print("COMPREHENSIVE AI MODULE FIX VALIDATION")
    print("🧪 "*35)
    
    try:
        test_entity_validation()
        test_schema_flattening()
        test_content_type_enforcement()
        test_confidence_levels()
        test_build_prompt()
        test_schema_output_compatibility()
        
        print("\n" + "="*70)
        print("✅ ALL TESTS PASSED!")
        print("="*70)
        print("\n✓ Entity validations working (string length, quantity bounds)")
        print("✓ Schema flattening via to_dict() working")
        print("✓ Content type enforcement with model_validator working")
        print("✓ Confidence levels and actionability checks working")
        print("✓ Prompt building with context injection working")
        print("✓ Handler compatibility verified")
        print("\n🎉 AI module fixes verified successfully!\n")
        
        return 0
        
    except AssertionError as e:
        print(f"\n❌ TEST FAILED: {e}")
        import traceback
        traceback.print_exc()
        return 1
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
