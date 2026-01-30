"""
Accounting Data Models and Schemas.

This module defines dataclasses for financial tracking in the Digital Employee system.
Part of Step 2: Accounting Clerk - Simple revenue/expense tracking for MSMEs.

Classes:
    RevenueTransaction: Revenue entry from confirmed orders.
    ExpenseTransaction: Expense entries (rent, utilities, salaries, etc.).
    DailySummary: Aggregated daily financial summary.
    WeeklySummary: Aggregated weekly financial summary.
    MonthlySummary: Aggregated monthly financial summary.

Constants:
    EXPENSE_CATEGORIES: Valid expense category definitions.
    CATEGORY_NAME_MAPPING: English-Arabic category name mappings.
"""

from dataclasses import dataclass, field
from datetime import datetime, date, timedelta
from typing import List, Optional, Dict
import uuid
import json


# ============== DATA MODELS ==============

@dataclass
class RevenueTransaction:
    """
    Represents a revenue entry from a confirmed order.
    
    Attributes:
        order_id: Associated order identifier.
        sector_id: Business sector identifier.
        business_name: Name of the business.
        amount: Revenue amount in EGP.
        items_summary: Brief description of items sold.
        customer_phone: Customer contact number.
        transaction_id: Unique transaction identifier (auto-generated).
        date: Transaction date (YYYY-MM-DD format).
        timestamp: Full timestamp of transaction.
        notes: Additional notes.
    """
    order_id: str
    sector_id: str
    business_name: str
    amount: float
    items_summary: str
    customer_phone: str = ""
    transaction_id: str = field(default_factory=lambda: f"REV-{uuid.uuid4().hex[:6].upper()}")
    date: str = field(default_factory=lambda: date.today().isoformat())
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    notes: str = ""
    
    def to_dict(self) -> dict:
        """Convert to dictionary representation."""
        return {
            "transaction_id": self.transaction_id,
            "order_id": self.order_id,
            "sector_id": self.sector_id,
            "business_name": self.business_name,
            "amount": self.amount,
            "items_summary": self.items_summary,
            "customer_phone": self.customer_phone,
            "date": self.date,
            "timestamp": self.timestamp,
            "notes": self.notes,
            "type": "revenue"
        }


@dataclass
class ExpenseTransaction:
    """
    Represents an expense entry.
    
    Categories include: Rent, Utilities, Salaries, Packaging, Supplies, Marketing, Other.
    
    Attributes:
        category: Expense category.
        amount: Expense amount in EGP.
        description: Description of the expense.
        expense_id: Unique expense identifier (auto-generated).
        date: Expense date (YYYY-MM-DD format).
        timestamp: Full timestamp of entry.
        business_name: Name of the business.
        notes: Additional notes.
    """
    category: str
    amount: float
    description: str
    expense_id: str = field(default_factory=lambda: f"EXP-{uuid.uuid4().hex[:6].upper()}")
    date: str = field(default_factory=lambda: date.today().isoformat())
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    business_name: str = ""
    notes: str = ""
    
    def to_dict(self) -> dict:
        """Convert to dictionary representation."""
        return {
            "expense_id": self.expense_id,
            "category": self.category,
            "amount": self.amount,
            "description": self.description,
            "date": self.date,
            "timestamp": self.timestamp,
            "business_name": self.business_name,
            "notes": self.notes,
            "type": "expense"
        }


@dataclass
class DailySummary:
    """
    Daily financial summary.
    
    Aggregates all revenues and expenses for a single day.
    """
    date: str
    business_name: str
    total_revenue: float
    total_expenses: float
    net_profit: float
    order_count: int
    expense_count: int
    revenue_transactions: List[dict]
    expense_transactions: List[dict]
    currency: str = "EGP"
    
    def to_dict(self) -> dict:
        """Convert to dictionary representation."""
        return {
            "date": self.date,
            "business_name": self.business_name,
            "total_revenue": self.total_revenue,
            "total_expenses": self.total_expenses,
            "net_profit": self.net_profit,
            "order_count": self.order_count,
            "expense_count": self.expense_count,
            "revenue_transactions": self.revenue_transactions,
            "expense_transactions": self.expense_transactions,
            "currency": self.currency
        }
    
    def get_summary_text(self, lang: str = "en") -> str:
        """Generate human-readable summary."""
        if lang == "ar":
            return f"""📊 ملخص يوم {self.date}
═══════════════════════════════
🏪 {self.business_name}

💰 إجمالي المبيعات: {self.total_revenue:,.2f} جنيه
   ({self.order_count} طلب)

💸 إجمالي المصروفات: {self.total_expenses:,.2f} جنيه
   ({self.expense_count} معاملة)

═══════════════════════════════
📈 صافي الربح: {self.net_profit:,.2f} جنيه
═══════════════════════════════"""
        else:
            return f"""📊 Daily Summary - {self.date}
═══════════════════════════════
🏪 {self.business_name}

💰 Total Revenue: {self.total_revenue:,.2f} EGP
   ({self.order_count} orders)

💸 Total Expenses: {self.total_expenses:,.2f} EGP
   ({self.expense_count} transactions)

═══════════════════════════════
📈 Net Profit: {self.net_profit:,.2f} EGP
═══════════════════════════════"""


@dataclass
class WeeklySummary:
    """Weekly financial summary."""
    week_start: str
    week_end: str
    business_name: str
    total_revenue: float
    total_expenses: float
    net_profit: float
    order_count: int
    expense_count: int
    daily_breakdown: List[dict]
    top_expense_categories: Dict[str, float]
    average_daily_revenue: float
    currency: str = "EGP"
    
    def to_dict(self) -> dict:
        return {
            "week_start": self.week_start,
            "week_end": self.week_end,
            "business_name": self.business_name,
            "total_revenue": self.total_revenue,
            "total_expenses": self.total_expenses,
            "net_profit": self.net_profit,
            "order_count": self.order_count,
            "expense_count": self.expense_count,
            "daily_breakdown": self.daily_breakdown,
            "top_expense_categories": self.top_expense_categories,
            "average_daily_revenue": self.average_daily_revenue,
            "currency": self.currency
        }
    
    def get_summary_text(self, lang: str = "en") -> str:
        """Generate human-readable weekly summary."""
        if lang == "ar":
            expense_breakdown = "\n".join([f"   • {cat}: {amt:,.2f} جنيه" for cat, amt in self.top_expense_categories.items()])
            return f"""📊 ملخص الأسبوع
{self.week_start} إلى {self.week_end}
═══════════════════════════════
🏪 {self.business_name}

💰 إجمالي المبيعات: {self.total_revenue:,.2f} جنيه
   ({self.order_count} طلب)
   📊 متوسط يومي: {self.average_daily_revenue:,.2f} جنيه

💸 إجمالي المصروفات: {self.total_expenses:,.2f} جنيه
{expense_breakdown}

═══════════════════════════════
📈 صافي الربح الأسبوعي: {self.net_profit:,.2f} جنيه
═══════════════════════════════"""
        else:
            expense_breakdown = "\n".join([f"   • {cat}: {amt:,.2f} EGP" for cat, amt in self.top_expense_categories.items()])
            return f"""📊 Weekly Summary
{self.week_start} to {self.week_end}
═══════════════════════════════
🏪 {self.business_name}

💰 Total Revenue: {self.total_revenue:,.2f} EGP
   ({self.order_count} orders)
   📊 Daily Average: {self.average_daily_revenue:,.2f} EGP

💸 Total Expenses: {self.total_expenses:,.2f} EGP
{expense_breakdown}

═══════════════════════════════
📈 Weekly Net Profit: {self.net_profit:,.2f} EGP
═══════════════════════════════"""


# ============== IN-MEMORY STORAGE ==============

# Storage for accounting data (in production, use a database)
accounting_db = {
    "revenue": {},      # transaction_id -> RevenueTransaction
    "expenses": {},     # expense_id -> ExpenseTransaction
}


# ============== ACCOUNTING FUNCTIONS ==============

def log_revenue_from_order(order_data: dict) -> RevenueTransaction:
    """
    Create a revenue transaction from a confirmed order.
    Called automatically when an order is confirmed in Step 1.
    """
    # Build items summary
    items = order_data.get("items", [])
    if items:
        items_summary = ", ".join([
            f"{item.get('product_name', 'Item')} x{item.get('quantity', 1)}"
            for item in items[:3]  # Show first 3 items
        ])
        if len(items) > 3:
            items_summary += f" (+{len(items) - 3} more)"
    else:
        items_summary = "Order items"
    
    revenue = RevenueTransaction(
        order_id=order_data.get("order_id", ""),
        sector_id=order_data.get("sector_id", ""),
        business_name=order_data.get("business_name", ""),
        amount=float(order_data.get("total", 0)),
        items_summary=items_summary,
        customer_phone=order_data.get("customer_phone", ""),
        notes=f"Auto-logged from order {order_data.get('order_id', '')}"
    )
    
    # Store in database
    accounting_db["revenue"][revenue.transaction_id] = revenue
    
    return revenue


def add_expense(
    category: str,
    amount: float,
    description: str,
    business_name: str = "",
    expense_date: str = None,
    notes: str = ""
) -> ExpenseTransaction:
    """Add a manual expense entry."""
    expense = ExpenseTransaction(
        category=category,
        amount=amount,
        description=description,
        business_name=business_name,
        notes=notes
    )
    
    # Override date if provided
    if expense_date:
        expense.date = expense_date
    
    # Store in database
    accounting_db["expenses"][expense.expense_id] = expense
    
    return expense


def get_daily_summary(target_date: str, business_name: str = "") -> DailySummary:
    """Generate daily financial summary for a specific date."""
    
    # Filter revenue transactions for the date
    revenue_transactions = []
    total_revenue = 0.0
    for rev in accounting_db["revenue"].values():
        if rev.date == target_date:
            if not business_name or rev.business_name == business_name:
                revenue_transactions.append(rev.to_dict())
                total_revenue += rev.amount
    
    # Filter expense transactions for the date
    expense_transactions = []
    total_expenses = 0.0
    for exp in accounting_db["expenses"].values():
        if exp.date == target_date:
            if not business_name or exp.business_name == business_name:
                expense_transactions.append(exp.to_dict())
                total_expenses += exp.amount
    
    # Calculate net profit
    net_profit = total_revenue - total_expenses
    
    return DailySummary(
        date=target_date,
        business_name=business_name or "All Businesses",
        total_revenue=total_revenue,
        total_expenses=total_expenses,
        net_profit=net_profit,
        order_count=len(revenue_transactions),
        expense_count=len(expense_transactions),
        revenue_transactions=revenue_transactions,
        expense_transactions=expense_transactions
    )


def get_weekly_summary(week_start: str, business_name: str = "") -> WeeklySummary:
    """Generate weekly financial summary starting from week_start date."""
    
    # Parse start date
    start_date = date.fromisoformat(week_start)
    end_date = start_date + timedelta(days=6)
    
    # Initialize aggregates
    total_revenue = 0.0
    total_expenses = 0.0
    order_count = 0
    expense_count = 0
    expense_categories: Dict[str, float] = {}
    daily_breakdown = []
    
    # Loop through each day of the week
    current_date = start_date
    while current_date <= end_date:
        date_str = current_date.isoformat()
        daily = get_daily_summary(date_str, business_name)
        
        total_revenue += daily.total_revenue
        total_expenses += daily.total_expenses
        order_count += daily.order_count
        expense_count += daily.expense_count
        
        # Track expense categories
        for exp in daily.expense_transactions:
            cat = exp.get("category", "Other")
            expense_categories[cat] = expense_categories.get(cat, 0) + exp.get("amount", 0)
        
        # Add to daily breakdown
        daily_breakdown.append({
            "date": date_str,
            "revenue": daily.total_revenue,
            "expenses": daily.total_expenses,
            "profit": daily.net_profit,
            "orders": daily.order_count
        })
        
        current_date += timedelta(days=1)
    
    # Calculate averages
    average_daily_revenue = total_revenue / 7 if total_revenue > 0 else 0
    
    # Sort expense categories by amount
    sorted_categories = dict(sorted(
        expense_categories.items(),
        key=lambda x: x[1],
        reverse=True
    ))
    
    return WeeklySummary(
        week_start=week_start,
        week_end=end_date.isoformat(),
        business_name=business_name or "All Businesses",
        total_revenue=total_revenue,
        total_expenses=total_expenses,
        net_profit=total_revenue - total_expenses,
        order_count=order_count,
        expense_count=expense_count,
        daily_breakdown=daily_breakdown,
        top_expense_categories=sorted_categories,
        average_daily_revenue=average_daily_revenue
    )


def get_all_revenue(business_name: str = "") -> List[dict]:
    """Get all revenue transactions, optionally filtered by business."""
    transactions = []
    for rev in accounting_db["revenue"].values():
        if not business_name or rev.business_name == business_name:
            transactions.append(rev.to_dict())
    return sorted(transactions, key=lambda x: x["timestamp"], reverse=True)


def get_all_expenses(business_name: str = "") -> List[dict]:
    """Get all expense transactions, optionally filtered by business."""
    transactions = []
    for exp in accounting_db["expenses"].values():
        if not business_name or exp.business_name == business_name:
            transactions.append(exp.to_dict())
    return sorted(transactions, key=lambda x: x["timestamp"], reverse=True)


# Expense category options for UI
EXPENSE_CATEGORIES = [
    {"id": "rent", "name_en": "Rent", "name_ar": "الإيجار", "icon": "🏠"},
    {"id": "utilities", "name_en": "Utilities", "name_ar": "المرافق", "icon": "💡"},
    {"id": "salaries", "name_en": "Salaries", "name_ar": "الرواتب", "icon": "👥"},
    {"id": "packaging", "name_en": "Packaging", "name_ar": "التغليف", "icon": "📦"},
    {"id": "supplies", "name_en": "Supplies", "name_ar": "المستلزمات", "icon": "🛒"},
    {"id": "marketing", "name_en": "Marketing", "name_ar": "التسويق", "icon": "📢"},
    {"id": "transport", "name_en": "Transport", "name_ar": "النقل", "icon": "🚚"},
    {"id": "maintenance", "name_en": "Maintenance", "name_ar": "الصيانة", "icon": "🔧"},
    {"id": "other", "name_en": "Other", "name_ar": "أخرى", "icon": "📋"},
]
