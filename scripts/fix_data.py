"""Fix business_name in existing data"""
from pymongo import MongoClient

db = MongoClient('localhost', 27017)['digital_employee']

# Update revenues with empty or missing business_name
result1 = db.revenues.update_many(
    {"$or": [{"business_name": ""}, {"business_name": None}]},
    {"$set": {"business_name": "My Store"}}
)
print(f"Updated revenues: {result1.modified_count}")

# Update customer user
result2 = db.users.update_one(
    {"username": "customer"},
    {"$set": {"business_name": "My Store"}}
)
print(f"Updated customer user: {result2.modified_count}")

# Update orders with empty business_name
result3 = db.orders.update_many(
    {"$or": [{"business_name": ""}, {"business_name": None}]},
    {"$set": {"business_name": "My Store"}}
)
print(f"Updated orders: {result3.modified_count}")

# Check current data
print("\n--- Current Data Check ---")
print(f"Revenues count: {db.revenues.count_documents({})}")
print(f"Revenues with 'My Store': {db.revenues.count_documents({'business_name': 'My Store'})}")
revenues = list(db.revenues.find({}).limit(5))
for r in revenues:
    print(f"  Revenue: {r.get('order_id')} - {r.get('amount')} - business: '{r.get('business_name')}'")

print(f"\nOrders count: {db.orders.count_documents({})}")
orders = list(db.orders.find({}).limit(5))
for o in orders:
    print(f"  Order: {o.get('order_id')} - {o.get('total')} - business: '{o.get('business_name')}'")
