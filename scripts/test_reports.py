# Test database functions directly (without API auth)
import sys
sys.path.insert(0, r"C:\Users\Windows 11\OneDrive\Desktop\Ai_Event\digital_employee")

from database import get_daily_summary, get_weekly_summary

print("=== DAILY REPORT (2026-01-28) ===")
daily = get_daily_summary("2026-01-28", "My Store", "")
print(f"Total Revenue: {daily['total_revenue']} EGP")
print(f"Order Count: {daily['order_count']}")
print(f"Revenues:")
for rev in daily.get('revenue_transactions', []):
    print(f"  - {rev.get('order_id')}: {rev.get('amount')} EGP | sector: {rev.get('sector_id')}")

print()

print("=== WEEKLY REPORT (2026-01-26 to 2026-02-01) ===")
weekly = get_weekly_summary("2026-01-26", "My Store", "")
print(f"Total Revenue: {weekly['total_revenue']} EGP")
print(f"Order Count: {weekly['order_count']}")
print(f"Revenues:")
for rev in weekly.get('revenue_transactions', []):
    print(f"  - {rev.get('order_id')}: {rev.get('amount')} EGP | date: {rev.get('date')}")
