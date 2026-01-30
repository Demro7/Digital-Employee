"""
Investigation script for MongoDB database - Digital Employee Project
This script checks the database state to debug revenue reporting issues.
"""

from pymongo import MongoClient
from datetime import datetime, timedelta

def investigate_database():
    print("=" * 60)
    print("MongoDB Database Investigation")
    print("=" * 60)
    
    # Connect to MongoDB
    client = MongoClient("mongodb://localhost:27017/")
    db = client["digital_employee"]
    
    # 1. Find admin user's business_name
    print("\n1. ADMIN USER INFORMATION")
    print("-" * 40)
    admin_user = db.users.find_one({"username": "admin"})
    if admin_user:
        admin_business_name = admin_user.get("business_name", "NOT SET")
        admin_sector_id = admin_user.get("sector_id", "NOT SET")
        print(f"   Username: {admin_user.get('username')}")
        print(f"   Business Name: {admin_business_name}")
        print(f"   Sector ID: {admin_sector_id}")
        print(f"   Full document: {admin_user}")
    else:
        admin_business_name = None
        print("   ERROR: Admin user not found!")
    
    # 2. List ALL revenues in the revenues collection
    print("\n2. ALL REVENUES IN DATABASE")
    print("-" * 40)
    revenues = list(db.revenues.find())
    print(f"   Total revenue documents: {len(revenues)}")
    
    if revenues:
        for i, rev in enumerate(revenues, 1):
            print(f"\n   Revenue #{i}:")
            print(f"      _id: {rev.get('_id')}")
            print(f"      order_id: {rev.get('order_id')}")
            print(f"      amount: {rev.get('amount')}")
            print(f"      date: {rev.get('date')} (type: {type(rev.get('date')).__name__})")
            print(f"      business_name: {rev.get('business_name')}")
            print(f"      sector_id: {rev.get('sector_id')}")
            print(f"      Full document: {rev}")
    else:
        print("   NO REVENUES FOUND IN DATABASE!")
    
    # 3. Check business_name matching
    print("\n3. BUSINESS NAME MATCHING CHECK")
    print("-" * 40)
    if admin_business_name and revenues:
        matching = 0
        not_matching = 0
        for rev in revenues:
            rev_business = rev.get('business_name')
            if rev_business == admin_business_name:
                matching += 1
                print(f"   ✓ MATCH: Revenue '{rev.get('order_id')}' has business_name '{rev_business}'")
            else:
                not_matching += 1
                print(f"   ✗ NO MATCH: Revenue '{rev.get('order_id')}' has '{rev_business}' vs admin '{admin_business_name}'")
        print(f"\n   Summary: {matching} matching, {not_matching} not matching")
    else:
        print("   Cannot compare - missing admin or revenues")
    
    # 4. Date check for 2026-01-28
    print("\n4. DATE VERIFICATION (Expected: 2026-01-28)")
    print("-" * 40)
    today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    expected_date = datetime(2026, 1, 28)
    print(f"   System 'today': {today}")
    print(f"   Expected date: {expected_date}")
    
    if revenues:
        for rev in revenues:
            rev_date = rev.get('date')
            print(f"\n   Revenue '{rev.get('order_id')}':")
            print(f"      Date value: {rev_date}")
            print(f"      Date type: {type(rev_date).__name__}")
            if isinstance(rev_date, datetime):
                print(f"      Date (date only): {rev_date.date()}")
                if rev_date.date() == expected_date.date():
                    print(f"      ✓ Date matches 2026-01-28")
                else:
                    print(f"      ✗ Date does NOT match 2026-01-28")
    
    # 5. Additional diagnostics - check what queries would return
    print("\n5. SIMULATED QUERY DIAGNOSTICS")
    print("-" * 40)
    
    if admin_business_name:
        # Try the exact query that would be used in reports
        today_start = datetime(2026, 1, 28, 0, 0, 0)
        today_end = datetime(2026, 1, 28, 23, 59, 59)
        
        # Query with business_name filter
        query_result = list(db.revenues.find({
            "business_name": admin_business_name,
            "date": {"$gte": today_start, "$lte": today_end}
        }))
        print(f"   Query with business_name='{admin_business_name}' AND date 2026-01-28:")
        print(f"   Result count: {len(query_result)}")
        
        # Query with just business_name
        query_business = list(db.revenues.find({"business_name": admin_business_name}))
        print(f"\n   Query with ONLY business_name='{admin_business_name}':")
        print(f"   Result count: {len(query_business)}")
        
        # Query with just date
        query_date = list(db.revenues.find({
            "date": {"$gte": today_start, "$lte": today_end}
        }))
        print(f"\n   Query with ONLY date 2026-01-28:")
        print(f"   Result count: {len(query_date)}")
    
    # 6. List all users
    print("\n6. ALL USERS IN DATABASE")
    print("-" * 40)
    users = list(db.users.find())
    for user in users:
        print(f"   User: {user.get('username')}, business_name: {user.get('business_name')}, sector_id: {user.get('sector_id')}")
    
    # 7. Check orders collection too
    print("\n7. ORDERS COLLECTION CHECK")
    print("-" * 40)
    orders = list(db.orders.find())
    print(f"   Total orders: {len(orders)}")
    for order in orders[:5]:  # First 5
        print(f"   Order: {order.get('order_id')}, business_name: {order.get('business_name')}, date: {order.get('date')}")
    
    print("\n" + "=" * 60)
    print("Investigation Complete")
    print("=" * 60)
    
    client.close()

if __name__ == "__main__":
    investigate_database()
