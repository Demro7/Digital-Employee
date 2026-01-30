"""Check revenue dates"""
from pymongo import MongoClient
from datetime import date

db = MongoClient('localhost', 27017)['digital_employee']
today = date.today().isoformat()

print(f"Today: {today}")
print()

# Check revenues for today
revs_today = list(db.revenues.find({'date': today, 'business_name': 'My Store'}))
print(f"Revenues today with 'My Store': {len(revs_today)}")
for r in revs_today:
    print(f"  {r.get('order_id')}: {r.get('amount')} EGP")

print()

# All revenues
all_revs = list(db.revenues.find({}))
print(f"All revenues ({len(all_revs)} total):")
for r in all_revs:
    print(f"  {r.get('order_id')}: {r.get('amount')} EGP - date: {r.get('date')} - business: '{r.get('business_name')}'")
