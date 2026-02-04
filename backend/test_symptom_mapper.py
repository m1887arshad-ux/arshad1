"""Quick test of symptom mapper functionality"""
from app.services.symptom_mapper import map_symptom_to_medicines
from app.db.session import SessionLocal

db = SessionLocal()

# Test 1: Fever / Bukhar
print("=" * 60)
print("TEST 1: Symptom = 'bukhar' (fever)")
print("=" * 60)
results = map_symptom_to_medicines(db, 1, "bukhar")
print(f"Found {len(results)} medicines:\n")
for i, med in enumerate(results, 1):
    rx = "🔴 PRESCRIPTION REQUIRED" if med["requires_prescription"] else "🟢 OTC"
    print(f"{i}. {med['name']} {rx}")
    print(f"   Used for: {med['disease']}")
    print(f"   Stock: {int(med['stock'])} | Price: ₹{med['price']:.2f}\n")

# Test 2: Pain / Dard
print("\n" + "=" * 60)
print("TEST 2: Symptom = 'dard' (pain)")
print("=" * 60)
results = map_symptom_to_medicines(db, 1, "dard")
print(f"Found {len(results)} medicines:\n")
for i, med in enumerate(results, 1):
    rx = "🔴 PRESCRIPTION REQUIRED" if med["requires_prescription"] else "🟢 OTC"
    print(f"{i}. {med['name']} {rx}")
    print(f"   Used for: {med['disease']}")
    print(f"   Stock: {int(med['stock'])} | Price: ₹{med['price']:.2f}\n")

# Test 3: English - fever
print("\n" + "=" * 60)
print("TEST 3: Symptom = 'fever' (English)")
print("=" * 60)
results = map_symptom_to_medicines(db, 1, "fever")
print(f"Found {len(results)} medicines:\n")
for i, med in enumerate(results, 1):
    rx = "🔴 PRESCRIPTION REQUIRED" if med["requires_prescription"] else "🟢 OTC"
    print(f"{i}. {med['name']} {rx}")
    print(f"   Used for: {med['disease']}")
    print(f"   Stock: {int(med['stock'])} | Price: ₹{med['price']:.2f}\n")

db.close()
print("\n✅ All tests completed!")
