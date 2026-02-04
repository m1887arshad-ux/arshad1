"""
Symptom-to-Medicine Mapping Service

Purpose: Maps user symptoms (e.g., "bukhar hai", "fever") to relevant medicines
         by searching the Inventory.disease field.

Architecture Decision:
- This is DETERMINISTIC business logic, NOT LLM-powered
- Uses exact keyword matching against disease field
- Returns multiple matches ranked by relevance
- Flags prescription medicines with ⚠️ warnings

Usage:
    from app.services.symptom_mapper import map_symptom_to_medicines
    results = map_symptom_to_medicines(db, business_id, "bukhar")
"""

from typing import List, Dict, Any
from sqlalchemy.orm import Session
from app.models.inventory import Inventory

# Symptom keyword mappings (English + Hinglish)
SYMPTOM_KEYWORDS = {
    "fever": ["fever", "bukhar", "bukhaar", "तापमान"],
    "pain": ["pain", "dard", "दर्द", "ache"],
    "headache": ["headache", "sir dard", "सिर दर्द"],
    "cold": ["cold", "sardi", "जुकाम", "cough", "khasi"],
    "stomach": ["stomach", "pet", "पेट", "acidity", "gas"],
    "allergy": ["allergy", "खुजली", "khujli", "rash"],
    "vitamin": ["vitamin", "कमजोरी", "kamjori", "weakness"],
    "diabetes": ["sugar", "diabetes", "मधुमेह"],
    "blood_pressure": ["bp", "blood pressure", "रक्तचाप"],
    "infection": ["infection", "संक्रमण", "bacterial"],
    "anxiety": ["tension", "चिंता", "anxiety", "stress"]
}


def map_symptom_to_medicines(
    db: Session,
    business_id: int,
    symptom_text: str
) -> List[Dict[str, Any]]:
    """
    Map symptom keywords to medicines using Inventory.disease field.
    
    Args:
        db: Database session
        business_id: Business ID to filter inventory
        symptom_text: User's symptom query (e.g., "bukhar hai", "fever")
    
    Returns:
        List of matching medicines with format:
        [{
            "name": str,
            "disease": str,
            "requires_prescription": bool,
            "stock": int,
            "price": float
        }]
    """
    # Normalize symptom text
    symptom_lower = symptom_text.lower().strip()
    
    # Find matching symptom categories
    matching_keywords = set()
    for category, keywords in SYMPTOM_KEYWORDS.items():
        if any(kw in symptom_lower for kw in keywords):
            matching_keywords.update(keywords)
    
    # If no keyword match, try direct search in disease field
    if not matching_keywords:
        matching_keywords.add(symptom_lower)
    
    # Query inventory for matches
    results = []
    for keyword in matching_keywords:
        medicines = db.query(Inventory).filter(
            Inventory.business_id == business_id,
            Inventory.disease.ilike(f"%{keyword}%")
        ).all()
        
        for med in medicines:
            # Avoid duplicates
            if not any(r["name"] == med.item_name for r in results):
                results.append({
                    "name": med.item_name,
                    "disease": med.disease or "General use",
                    "requires_prescription": med.requires_prescription,
                    "stock": med.quantity,
                    "price": float(med.price)
                })
    
    # Limit to top 5 results
    return results[:5]
