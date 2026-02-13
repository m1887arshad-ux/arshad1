#!/usr/bin/env python3
"""
Seed script to load dummy medicine inventory data into the database.
Usage: python seed_medicines.py
"""

import json
import sys
from pathlib import Path

# Add backend directory to path
backend_dir = Path(__file__).parent / "backend"
sys.path.insert(0, str(backend_dir))

from app.db.session import SessionLocal
from app.db.init_db import init_db
from app.models.business import Business
from app.models.inventory import Inventory
from app.models.user import User


def seed_medicines():
    """Load medicines from JSON file into database"""
    
    # Load JSON data
    json_file = Path(__file__).parent / "medicines_inventory.json"
    
    if not json_file.exists():
        print(f"Error: {json_file} not found!")
        return False
    
    with open(json_file, "r") as f:
        data = json.load(f)
    
    # Ensure tables exist
    init_db()

    # Get database session
    db = SessionLocal()
    
    try:
        # Clear existing inventory (optional - comment out to keep existing data)
        # db.query(Inventory).delete()
        # print("Cleared existing inventory")
        
        # Ensure there is a business to attach inventory to
        business = db.query(Business).first()
        if not business:
            owner = db.query(User).first()
            if not owner:
                print("❌ No users found. Create a user first, then re-run.")
                return False
            business = Business(owner_id=owner.id, name="Demo Pharmacy")
            db.add(business)
            db.commit()
            db.refresh(business)
            print(f"✓ Created default business: {business.name} (ID: {business.id})")

        # Add medicines from JSON
        added_count = 0
        for med in data.get("medicines", []):
            # Check if medicine already exists
            existing = db.query(Inventory).filter(
                Inventory.item_name == med["item_name"],
                Inventory.business_id == business.id,
            ).first()
            
            if existing:
                print(f"⊙ {med['item_name']} already exists, skipping")
                continue
            
            # Create new inventory item
            inventory_item = Inventory(
                business_id=business.id,
                item_name=med["item_name"],
                quantity=med["quantity"],
                price=med.get("price", 50),
                disease=med.get("disease", ""),
                requires_prescription=med.get("requires_prescription", False),
                # expiry_date can be added here if the model supports it
            )
            
            db.add(inventory_item)
            added_count += 1
            print(f"✓ Added: {med['item_name']} (Qty: {med['quantity']}, Price: ₹{med['price']})")
        
        # Commit all changes
        db.commit()
        print(f"\n✅ Successfully seeded {added_count} medicines!")
        return True
        
    except Exception as e:
        db.rollback()
        print(f"\n❌ Error seeding data: {e}")
        return False
    finally:
        db.close()


if __name__ == "__main__":
    print("🏥 Bharat Biz-Agent - Medicine Inventory Seeding\n")
    seed_medicines()
