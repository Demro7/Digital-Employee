from pymongo import MongoClient
from datetime import date

db = MongoClient('localhost', 27017)['digital_employee']
today = date.today().isoformat()

output = []
output.append(f"Today: {today}")
output.append("")

admin = db.users.find_one({'username': 'admin'})
output.append(f"Admin business_name: '{admin.get('business_name') if admin else 'N/A'}'")
output.append("")

revs = list(db.revenues.find({}))
output.append(f"ALL REVENUES ({len(revs)}):")
for r in revs:
    output.append(f"  {r.get('order_id')}: {r.get('amount')} | date={r.get('date')} | bn='{r.get('business_name')}' | sec={r.get('sector_id')}")

output.append("")
orders = list(db.orders.find({}))
output.append(f"ALL ORDERS ({len(orders)}):")
for o in orders:
    output.append(f"  {o.get('order_id')}: {o.get('total')} | bn='{o.get('business_name')}' | sec={o.get('sector_id')}")

with open('db_output.txt', 'w', encoding='utf-8') as f:
    f.write('\n'.join(output))

print("Done! Check db_output.txt")
