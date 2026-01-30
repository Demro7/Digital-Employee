"""Debug script to check reports data"""
from pymongo import MongoClient
from datetime import date, timedelta

db = MongoClient('localhost', 27017)['digital_employee']
today = date.today().isoformat()
week_start = (date.today() - timedelta(days=date.today().weekday())).isoformat()

print(f"Today: {today}")
print(f"Week Start: {week_start}")
print()

# Check admin user business_name
admin = db.users.find_one({'username': 'admin'})
print(f"Admin business_name: '{admin.get('business_name')}'")
print()

# All revenues
print("=== ALL REVENUES ===")
all_revs = list(db.revenues.find({}))
print(f"Total: {len(all_revs)}")
for r in all_revs:
    print(f"  {r.get('order_id')}: {r.get('amount')} EGP | date: {r.get('date')} | business: '{r.get('business_name')}' | sector: {r.get('sector_id')}")

print()

# Revenues for today with business_name filter
print("=== REVENUES TODAY (with business_name='My Store') ===")
revs_today = list(db.revenues.find({'date': today, 'business_name': 'My Store'}))
print(f"Found: {len(revs_today)}")
for r in revs_today:
    print(f"  {r.get('order_id')}: {r.get('amount')} EGP")

print()

# Revenues for today without filter
print("=== REVENUES TODAY (no filter) ===")
revs_today_all = list(db.revenues.find({'date': today}))
print(f"Found: {len(revs_today_all)}")
for r in revs_today_all:
    print(f"  {r.get('order_id')}: {r.get('amount')} EGP | business: '{r.get('business_name')}'")

print()

# Check orders too
print("=== ALL ORDERS ===")
orders = list(db.orders.find({}))
print(f"Total: {len(orders)}")
for o in orders:
    print(f"  {o.get('order_id')}: {o.get('total')} EGP | business: '{o.get('business_name')}' | sector: {o.get('sector_id')}")
