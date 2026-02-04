"""Seed pharmacy inventory with comprehensive Indian medicines."""
from app.db.session import SessionLocal
from app.models.business import Business
from app.models.inventory import Inventory
from decimal import Decimal
import json

def seed_inventory():
    db = SessionLocal()
    
    # Get first business (or create one if needed)
    business = db.query(Business).first()
    if not business:
        # Create default business
        from app.models.user import User
        user = db.query(User).first()
        if not user:
            print("❌ No user found. Database not initialized properly.")
            return
        
        business = Business(
            owner_id=user.id,
            name="Bharat Pharmacy",
            preferred_language="hinglish",
            telegram_chat_id=None,
            require_approval_invoices=True,
            whatsapp_notifications=True,
            agent_actions_enabled=True
        )
        db.add(business)
        db.commit()
        db.refresh(business)
        print(f"✅ Created default business: {business.name}")
    
    business_id = business.id
    
    # Clear existing inventory for clean seed
    db.query(Inventory).filter(Inventory.business_id == business_id).delete()
    
    # Comprehensive medicine list with disease information
    medicines = [
        {
            "name": "Paracetamol 500mg",
            "used_for": "Fever, Headache, Body Pain",
            "price": 2.50,
            "units": 200
        },
        {
            "name": "Dolo 650",
            "used_for": "High Fever, Severe Headache, Post-vaccination Pain",
            "price": 3.00,
            "units": 180
        },
        {
            "name": "Crocin Advance",
            "used_for": "Fast Relief from Fever and Pain",
            "price": 4.50,
            "units": 150
        },
        {
            "name": "Azithromycin 500mg",
            "used_for": "Bacterial Infections, Respiratory Infections",
            "price": 15.00,
            "units": 80
        },
        {
            "name": "Amoxicillin 500mg",
            "used_for": "Bacterial Infections, Throat Infection, Ear Infection",
            "price": 8.00,
            "units": 100
        },
        {
            "name": "Cetirizine 10mg",
            "used_for": "Allergic Rhinitis, Skin Allergies, Itching",
            "price": 1.50,
            "units": 250
        },
        {
            "name": "Pan 40 (Pantoprazole)",
            "used_for": "Acidity, GERD, Stomach Ulcers",
            "price": 6.00,
            "units": 120
        },
        {
            "name": "Omez (Omeprazole)",
            "used_for": "Acid Reflux, Gastritis, Heartburn",
            "price": 4.50,
            "units": 140
        },
        {
            "name": "Ranitidine 150mg",
            "used_for": "Acidity, Indigestion, Stomach Pain",
            "price": 2.00,
            "units": 160
        },
        {
            "name": "Metformin 500mg",
            "used_for": "Type 2 Diabetes, Blood Sugar Control",
            "price": 1.00,
            "units": 200
        },
        {
            "name": "Glimepiride 1mg",
            "used_for": "Type 2 Diabetes Management",
            "price": 3.50,
            "units": 100
        },
        {
            "name": "Atorvastatin 10mg",
            "used_for": "High Cholesterol, Heart Disease Prevention",
            "price": 4.00,
            "units": 120
        },
        {
            "name": "Amlodipine 5mg",
            "used_for": "High Blood Pressure, Hypertension",
            "price": 2.50,
            "units": 150
        },
        {
            "name": "Combiflam",
            "used_for": "Severe Pain, Fever with Body Ache",
            "price": 5.00,
            "units": 180
        },
        {
            "name": "Voveran (Diclofenac)",
            "used_for": "Joint Pain, Arthritis, Muscle Pain",
            "price": 6.50,
            "units": 100
        },
        {
            "name": "Brufen (Ibuprofen) 400mg",
            "used_for": "Pain Relief, Inflammation, Fever",
            "price": 3.50,
            "units": 140
        },
        {
            "name": "Disprin (Aspirin)",
            "used_for": "Headache, Fever, Blood Thinning",
            "price": 1.50,
            "units": 200
        },
        {
            "name": "Ciprofloxacin 500mg",
            "used_for": "UTI, Diarrhea, Bacterial Infections",
            "price": 7.00,
            "units": 90
        },
        {
            "name": "Norflox TZ",
            "used_for": "Diarrhea, Dysentery, Intestinal Infections",
            "price": 12.00,
            "units": 80
        },
        {
            "name": "Montelukast 10mg",
            "used_for": "Asthma, Allergic Rhinitis, Breathing Problems",
            "price": 8.50,
            "units": 100
        },
        {
            "name": "Levocetrizine 5mg",
            "used_for": "Seasonal Allergies, Sneezing, Runny Nose",
            "price": 3.00,
            "units": 150
        },
        {
            "name": "Allegra 120mg (Fexofenadine)",
            "used_for": "Chronic Allergic Rhinitis, Hives",
            "price": 9.00,
            "units": 110
        },
        {
            "name": "Digene Gel",
            "used_for": "Instant Acidity Relief, Gas, Bloating",
            "price": 25.00,
            "units": 60
        },
        {
            "name": "Gelusil Syrup",
            "used_for": "Acidity, Heartburn, Stomach Upset",
            "price": 45.00,
            "units": 50
        },
        {
            "name": "ORS (Electral)",
            "used_for": "Dehydration, Diarrhea, Vomiting",
            "price": 8.00,
            "units": 100
        },
        {
            "name": "Calpol 250mg Syrup",
            "used_for": "Child Fever, Pain Relief for Kids",
            "price": 55.00,
            "units": 70
        },
        {
            "name": "Ascoril LS Syrup",
            "used_for": "Cough with Mucus, Bronchitis",
            "price": 85.00,
            "units": 50
        },
        {
            "name": "Benadryl Cough Syrup",
            "used_for": "Dry Cough, Allergic Cough",
            "price": 95.00,
            "units": 45
        },
        {
            "name": "Vitamin D3 60K",
            "used_for": "Vitamin D Deficiency, Bone Health",
            "price": 35.00,
            "units": 80
        },
        {
            "name": "Vitamin B Complex",
            "used_for": "Energy, Nerve Health, General Weakness",
            "price": 18.00,
            "units": 120
        },
        {
            "name": "Calcium + Vitamin D3",
            "used_for": "Bone Strength, Osteoporosis Prevention",
            "price": 75.00,
            "units": 90
        },
        {
            "name": "Codeine Phosphate 30mg",
            "used_for": "Severe Pain, Persistent Cough",
            "price": 120.00,
            "units": 15,
            "requires_prescription": True
        },
        {
            "name": "Alprazolam 0.5mg",
            "used_for": "Anxiety Disorder, Panic Attacks",
            "price": 85.00,
            "units": 20,
            "requires_prescription": True
        },
        {
            "name": "Tramadol 50mg",
            "used_for": "Moderate to Severe Pain",
            "price": 95.00,
            "units": 18,
            "requires_prescription": True
        }
    ]
    
    # Save medicine data as JSON for reference
    with open('medicines_data.json', 'w', encoding='utf-8') as f:
        json.dump(medicines, f, indent=2, ensure_ascii=False)
    print(f"📄 Medicine data saved to medicines_data.json")
    
    # Add medicines to database
    for med in medicines:
        inventory = Inventory(
            business_id=business_id,
            item_name=med["name"],
            quantity=Decimal(str(med["units"])),
            price=Decimal(str(med["price"])),
            disease=med.get("used_for"),
            requires_prescription=med.get("requires_prescription", False)
        )
        db.add(inventory)
    
    db.commit()
    print(f"\n✅ Successfully added {len(medicines)} medicines to inventory for business '{business.name}'")
    
    # Print summary with disease info
    print(f"\n📦 MEDICINE INVENTORY ({len(medicines)} items):")
    print("=" * 80)
    for med in medicines:
        print(f"  📌 {med['name']}")
        print(f"     💊 Used For: {med['used_for']}")
        print(f"     💰 Price: ₹{med['price']:.2f} | 📦 Stock: {med['units']} units")
        print()
    
    db.close()

if __name__ == "__main__":
    seed_inventory()
