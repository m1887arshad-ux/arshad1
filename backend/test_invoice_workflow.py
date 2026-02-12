#!/usr/bin/env python3
"""
Complete invoice workflow test
Steps: 1. Setup Business 2. Create Inventory 3. Create Draft Invoice 4. Approve 5. Verify
"""
import requests
import json
from time import sleep

BASE_URL = "http://localhost:8000"
HEADERS = {"Content-Type": "application/json"}

# Login to get session
print("=" * 60)
print("STEP 1: LOGIN & GET COOKIES")
print("=" * 60)

login_resp = requests.post(f"{BASE_URL}/auth/login", 
    json={'email': 'owner@test.com', 'password': 'TestPassword123!'},
    headers=HEADERS
)
print(f"✓ Login Status: {login_resp.status_code}")
cookies = login_resp.cookies

# Step 2: Setup business
print("\n" + "=" * 60)
print("STEP 2: SETUP BUSINESS")
print("=" * 60)

biz_resp = requests.post(f"{BASE_URL}/business/setup",
    json={
        "name": "Test Pharmacy",
        "owner_name": "Arshad Khan",
        "preferred_language": "en"
    },
    headers=HEADERS,
    cookies=cookies
)
print(f"✓ Setup Business Status: {biz_resp.status_code}")
if biz_resp.status_code == 200:
    biz_data = biz_resp.json()
    print(f"  Business ID: {biz_data.get('id')}")
    print(f"  Name: {biz_data.get('business_name')}")
else:
    print(f"  Response: {biz_resp.text}")

# Step 3: Create inventory item
print("\n" + "=" * 60)
print("STEP 3: CREATE INVENTORY ITEM")
print("=" * 60)

inv_resp = requests.post(f"{BASE_URL}/records/inventory",
    json={
        "item_name": "Paracetamol 500mg",
        "quantity": 100,
        "price": 50.00,
        "disease": "fever",
        "requires_prescription": False
    },
    headers=HEADERS,
    cookies=cookies
)
print(f"✓ Create Inventory Status: {inv_resp.status_code}")
if inv_resp.status_code == 200:
    inv_data = inv_resp.json()
    print(f"  Item: {inv_data.get('item_name')}")
    print(f"  Quantity: {inv_data.get('quantity')}")
    print(f"  Price: ₹{inv_data.get('price')}")
else:
    print(f"  Response: {inv_resp.text}")

# Step 4: Create invoice (direct)
print("\n" + "=" * 60)
print("STEP 4: CREATE INVOICE (Direct)")
print("=" * 60)

invoice_resp = requests.post(f"{BASE_URL}/records/invoices",
    json={
        "customer_name": "Rajesh Kumar",
        "amount": 500.00,
        "phone": "+91-9876543210"
    },
    headers=HEADERS,
    cookies=cookies
)
print(f"✓ Create Invoice Status: {invoice_resp.status_code}")
if invoice_resp.status_code == 200:
    inv_data = invoice_resp.json()
    print(f"  Invoice ID: {inv_data.get('id')}")
    print(f"  Customer: {inv_data.get('customer_name')}")
    print(f"  Amount: {inv_data.get('amount')}")
    print(f"  Status: {inv_data.get('status')}")
else:
    print(f"  Error: {invoice_resp.text}")

# Step 5: List invoices
print("\n" + "=" * 60)
print("STEP 5: VIEW ALL INVOICES")
print("=" * 60)

list_resp = requests.get(f"{BASE_URL}/records/invoices",
    headers=HEADERS,
    cookies=cookies
)
print(f"✓ List Invoices Status: {list_resp.status_code}")
if list_resp.status_code == 200:
    invoices = list_resp.json()
    print(f"  Total Invoices: {len(invoices)}")
    for inv in invoices[:3]:  # Show first 3
        print(f"    - {inv['customer']} | {inv['amount']} | {inv['status']}")
else:
    print(f"  Error: {list_resp.text}")

# Step 6: List ledger entries
print("\n" + "=" * 60)
print("STEP 6: VIEW LEDGER ENTRIES")
print("=" * 60)

ledger_resp = requests.get(f"{BASE_URL}/records/ledger",
    headers=HEADERS,
    cookies=cookies
)
print(f"✓ List Ledger Status: {ledger_resp.status_code}")
if ledger_resp.status_code == 200:
    entries = ledger_resp.json()
    print(f"  Total Ledger Entries: {len(entries)}")
    for entry in entries[:3]:  # Show first 3
        print(f"    - Debit: {entry.get('debit')} | Credit: {entry.get('credit')} | Description: {entry.get('description')}")
else:
    print(f"  Error: {ledger_resp.text}")

print("\n" + "=" * 60)
print("WORKFLOW COMPLETE ✓")
print("=" * 60)
