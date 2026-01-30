from pymongo import MongoClient
from datetime import date
import sys

sys.stdout.flush()
db = MongoClient('localhost', 27017)['digital_employee']
today = date.today().isoformat()

output = []
output.append(f"Today: {today}")

admin = db.users.find_one({'username': 'admin'})
output.append(f"Admin business_name: '{admin.get('business_name') if admin else 'N/A'}'")

revs = list(db.revenues.find({}))
output.append(f"ALL REVENUES ({len(revs)}):")
for r in revs:
    output.append(f"  {r.get('order_id')}: {r.get('amount')} | date={r.get('date')} | bn='{r.get('business_name')}' | sec={r.get('sector_id')}")

# Write to file
with open('check_output.txt', 'w', encoding='utf-8') as f:
    f.write('\n'.join(output))
    
print("Output written to check_output.txt")
