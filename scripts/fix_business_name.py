"""
Script to fix and check data
"""
from pymongo import MongoClient
from datetime import datetime

db = MongoClient('localhost', 27017)['digital_employee']
today = datetime.now().strftime("%Y-%m-%d")

# Get admin user
admin = db.users.find_one({'username': 'admin'})
admin_bn = admin.get('business_name', '') if admin else ''
print(f"Admin business_name: '{admin_bn}'")
print(f"Today's date: {today}")
print()

# Get all revenues
all_revs = list(db.revenues.find({}))
print(f"=== ALL REVENUES ({len(all_revs)}) ===")
for r in all_revs:
    print(f"Order: {r.get('order_id')} | Amount: {r.get('amount')} | Date: {r.get('date')} | BN: '{r.get('business_name')}' | Sector: {r.get('sector_id')}")

print()

# Revenues that WILL appear in reports (matching business_name and today's date)
print(f"=== REVENUES FOR TODAY WITH ADMIN BN ===")
matching = list(db.revenues.find({'date': today, 'business_name': admin_bn}))
print(f"Found: {len(matching)}")
for r in matching:
    print(f"  {r.get('order_id')}: {r.get('amount')}")

# Check if business_name matches
print()
print("=== FIX NEEDED? ===")
needs_fix = []
for r in all_revs:
    if r.get('business_name') != admin_bn:
        needs_fix.append(r)
        print(f"Revenue {r.get('order_id')} has BN '{r.get('business_name')}' but admin has '{admin_bn}'")

if needs_fix:
    print()
    print(f"Fixing {len(needs_fix)} revenues to have business_name='{admin_bn}'...")
    result = db.revenues.update_many(
        {},
        {'$set': {'business_name': admin_bn}}
    )
    print(f"Updated {result.modified_count} revenues")
else:
    print("No fix needed - all revenues have correct business_name")
