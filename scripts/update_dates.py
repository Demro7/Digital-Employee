"""Update revenue dates to today"""
from pymongo import MongoClient
from datetime import date

db = MongoClient('localhost', 27017)['digital_employee']
today = date.today().isoformat()

# Update revenues from yesterday to today
result = db.revenues.update_many(
    {"date": "2026-01-27"},
    {"$set": {"date": today}}
)
print(f"Updated {result.modified_count} revenues to {today}")

# Verify
print("\nVerification:")
revs = list(db.revenues.find({}))
for r in revs:
    print(f"  {r.get('order_id')}: {r.get('amount')} EGP - date: {r.get('date')}")
