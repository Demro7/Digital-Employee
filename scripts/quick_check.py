from pymongo import MongoClient
from datetime import date

db = MongoClient('localhost', 27017)['digital_employee']
today = date.today().isoformat()

print(f"Today: {today}")
print()

admin = db.users.find_one({'username': 'admin'})
print(f"Admin business_name: '{admin.get('business_name') if admin else 'N/A'}'")
print()

revs = list(db.revenues.find({}))
print(f"ALL REVENUES ({len(revs)}):")
for r in revs:
    print(f"  {r.get('order_id')}: {r.get('amount')} | date={r.get('date')} | bn='{r.get('business_name')}' | sec={r.get('sector_id')}")
