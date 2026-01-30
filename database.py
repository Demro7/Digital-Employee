"""
MongoDB Database Module for Digital Employee System
===================================================

This module handles all database connections and CRUD operations for the
Digital Employee system. It provides functions for managing:
    - Users (authentication, registration, profile management)
    - Orders (creation, status updates, retrieval)
    - Revenue/Expense tracking (financial transactions)
    - Inventory management (stock levels, movements)
    - Chat message persistence

Database: MongoDB (via pymongo)
Default Connection: mongodb://localhost:27017/digital_employee
"""

import os
import json
from datetime import datetime

from pymongo import MongoClient
from pymongo.errors import ConnectionFailure
from bson import ObjectId
import bcrypt
from dotenv import load_dotenv
import logging

load_dotenv()

# Configure logging
logger = logging.getLogger(__name__)
logging.basicConfig(
    level=logging.DEBUG if os.getenv("DEBUG", "").lower() == "true" else logging.INFO,
    format="[%(levelname)s] %(name)s: %(message)s"
)

# MongoDB Connection Configuration
MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017")
DB_NAME = os.getenv("DB_NAME", "digital_employee")

# Global database instance (singleton pattern)
_client = None
_db = None


def get_db():
    """
    Get MongoDB database instance (singleton).
    
    Returns:
        pymongo.database.Database: The MongoDB database instance.
        
    Raises:
        SystemExit: If connection to MongoDB fails.
    """
    global _client, _db
    if _db is None:
        try:
            _client = MongoClient(MONGO_URI)
            # Test connection
            _client.admin.command('ping')
            _db = _client[DB_NAME]
            logger.info(f"Connected to MongoDB database: {DB_NAME}")
            # Create indexes
            _create_indexes()
        except ConnectionFailure as e:
            logger.error(f"MongoDB connection failed: {e}")
            raise
    return _db


def _create_indexes():
    """Create necessary indexes for better query performance."""
    db = _db
    # Users indexes
    db.users.create_index("username", unique=True)
    db.users.create_index("role")
    
    # Orders indexes
    db.orders.create_index("order_id", unique=True)
    db.orders.create_index("created_at")
    db.orders.create_index("status")
    
    # Revenues indexes
    db.revenues.create_index("order_id")
    db.revenues.create_index("date")
    
    # Expenses indexes
    db.expenses.create_index("date")
    db.expenses.create_index("category")
    
    # Chat messages indexes
    db.chat_messages.create_index("session_id")
    db.chat_messages.create_index("created_at")
    
    # Login logs indexes
    db.login_logs.create_index("username")
    db.login_logs.create_index("timestamp")

    # Inventory indexes
    db.inventory.create_index([("sector_id", 1), ("item_id", 1)], unique=True)
    db.inventory.create_index("name_en")
    db.inventory.create_index("name_ar")
    db.inventory.create_index("stock_qty")
    db.inventory.create_index("updated_at")

    # Inventory movements indexes
    db.inventory_movements.create_index("item_id")
    db.inventory_movements.create_index("created_at")
    db.inventory_movements.create_index("order_id")
    db.inventory_movements.create_index([("sector_id", 1), ("item_id", 1)])


def _load_sector_catalogs(sectors_dir: str = None) -> list:
    """Load sector catalogs from config files for inventory seeding."""
    if sectors_dir is None:
        sectors_dir = os.path.join(os.path.dirname(__file__), "config", "sectors")

    catalogs = []
    if not os.path.isdir(sectors_dir):
        return catalogs

    for filename in os.listdir(sectors_dir):
        if not filename.endswith(".json"):
            continue
        filepath = os.path.join(sectors_dir, filename)
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                sector_data = json.load(f)
                catalogs.append(sector_data)
        except Exception:
            continue

    return catalogs


def seed_inventory_data(force: bool = False, default_stock: int = 50, reorder_level: int = 10) -> dict:
    """Seed inventory from sector catalogs. Does nothing if already seeded unless force=True."""
    db = get_db()

    existing_count = db.inventory.count_documents({})
    if existing_count > 0 and not force:
        return {
            "seeded": 0,
            "updated": 0,
            "skipped": existing_count,
            "message": "Inventory already seeded"
        }

    catalogs = _load_sector_catalogs()
    now = datetime.utcnow()
    items = []

    for sector in catalogs:
        sector_id = sector.get("sector_id", "")
        for item in sector.get("catalog", []):
            item_id = item.get("id") or f"{sector_id}-{item.get('name_en', '')[:6]}"
            doc = {
                "sector_id": sector_id,
                "item_id": item_id,
                "name_en": item.get("name_en", ""),
                "name_ar": item.get("name_ar", ""),
                "price": float(item.get("price", 0)),
                "unit": item.get("unit", "unit"),
                "stock_qty": int(item.get("stock_qty", default_stock)),
                "reorder_level": int(item.get("reorder_level", reorder_level)),
                "is_active": True,
                "created_at": now,
                "updated_at": now,
                "source": "seed"
            }
            items.append(doc)

    seeded = 0
    updated = 0

    if force:
        for doc in items:
            result = db.inventory.update_one(
                {"sector_id": doc["sector_id"], "item_id": doc["item_id"]},
                {
                    "$set": {
                        "name_en": doc["name_en"],
                        "name_ar": doc["name_ar"],
                        "price": doc["price"],
                        "unit": doc["unit"],
                        "stock_qty": doc["stock_qty"],
                        "reorder_level": doc["reorder_level"],
                        "is_active": doc["is_active"],
                        "updated_at": now
                    },
                    "$setOnInsert": {
                        "created_at": now,
                        "source": "seed"
                    }
                },
                upsert=True
            )
            if result.upserted_id:
                seeded += 1
            elif result.modified_count > 0:
                updated += 1
    else:
        if items:
            result = db.inventory.insert_many(items)
            seeded = len(result.inserted_ids)

    return {
        "seeded": seeded,
        "updated": updated,
        "skipped": 0,
        "message": "Inventory seeded" if seeded or updated else "No items to seed"
    }


# ============== USER OPERATIONS ==============

def create_user(username: str, password: str, role: str, business_name: str = "") -> dict:
    """
    Create a new user.
    role: 'customer' or 'accounting'
    """
    db = get_db()
    
    # Check if username exists
    if db.users.find_one({"username": username}):
        return {"success": False, "error": "Username already exists"}
    
    # Hash password
    password_hash = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())
    
    user = {
        "username": username,
        "password_hash": password_hash,
        "role": role,  # 'customer' or 'accounting'
        "business_name": business_name,
        "status": "active",
        "created_at": datetime.utcnow(),
        "last_login": None
    }
    
    result = db.users.insert_one(user)
    user["_id"] = str(result.inserted_id)
    del user["password_hash"]  # Don't return password
    
    return {"success": True, "user": user}


def authenticate_user(username: str, password: str) -> dict:
    """Authenticate user and return user data if successful."""
    db = get_db()
    
    user = db.users.find_one({"username": username})
    
    # Log the attempt
    log_login_attempt(username, success=False if not user else None)
    
    if not user:
        return {"success": False, "error": "Invalid username or password"}
    
    if user["status"] != "active":
        return {"success": False, "error": "Account is inactive"}
    
    # Verify password
    if not bcrypt.checkpw(password.encode('utf-8'), user["password_hash"]):
        log_login_attempt(username, success=False)
        return {"success": False, "error": "Invalid username or password"}
    
    # Update last login
    db.users.update_one(
        {"_id": user["_id"]},
        {"$set": {"last_login": datetime.utcnow()}}
    )
    
    # Log successful login
    log_login_attempt(username, success=True)
    
    # Return user without password
    return {
        "success": True,
        "user": {
            "_id": str(user["_id"]),
            "username": user["username"],
            "role": user["role"],
            "business_name": user.get("business_name", ""),
            "status": user["status"]
        }
    }


def get_user_by_id(user_id: str) -> dict:
    """Get user by ID."""
    db = get_db()
    user = db.users.find_one({"_id": ObjectId(user_id)})
    if user:
        user["_id"] = str(user["_id"])
        del user["password_hash"]
    return user


def update_user_business_name(user_id: str, business_name: str) -> dict:
    """Update user's business name (admin only operation)."""
    db = get_db()
    try:
        result = db.users.update_one(
            {"_id": ObjectId(user_id)},
            {"$set": {"business_name": business_name}}
        )
        if result.modified_count > 0:
            return {"success": True, "message": "Business name updated"}
        return {"success": False, "error": "User not found or no change"}
    except Exception as e:
        return {"success": False, "error": str(e)}


def log_login_attempt(username: str, success: bool):
    """Log login attempt."""
    db = get_db()
    db.login_logs.insert_one({
        "username": username,
        "success": success,
        "timestamp": datetime.utcnow(),
        "ip_address": None  # Can be set from request
    })


# ============== ORDER OPERATIONS ==============

def save_order(order_data: dict) -> dict:
    """
    Save order to database and auto-create revenue if confirmed.
    
    Args:
        order_data: Dictionary containing order details:
            - order_id: Unique order identifier
            - sector_id: Business sector (e.g., 'restaurant', 'grocery')
            - business_name: Name of the business
            - customer_id: ID of the customer placing the order
            - items: List of order items
            - customer_phone: Customer's phone number
            - customer_address: Delivery address
            - total: Order total amount
            - status: Order status ('pending', 'confirmed', etc.)
    
    Returns:
        dict: The saved order with MongoDB _id.
    """
    db = get_db()
    
    logger.debug(f"save_order called with: {order_data}")
    
    order = {
        "order_id": order_data.get("order_id"),
        "sector_id": order_data.get("sector_id"),
        "business_name": order_data.get("business_name"),
        "customer_id": order_data.get("customer_id"),
        "items": order_data.get("items", []),
        "customer_phone": order_data.get("customer_phone", ""),
        "customer_address": order_data.get("customer_address", ""),
        "total": float(order_data.get("total", 0)),
        "status": order_data.get("status", "pending"),
        "created_at": datetime.utcnow(),
        "updated_at": datetime.utcnow()
    }
    
    result = db.orders.insert_one(order)
    order["_id"] = str(result.inserted_id)
    
    logger.debug(f"Order inserted with _id: {order['_id']}")
    
    # Auto-create revenue if order is confirmed
    if order["status"] == "confirmed":
        logger.debug("Creating revenue for confirmed order")
        create_revenue_from_order(order)
    
    return order


def get_orders(filters: dict = None, limit: int = 100) -> list:
    """Get orders with optional filters."""
    db = get_db()
    query = filters or {}
    orders = list(db.orders.find(query).sort("created_at", -1).limit(limit))
    for order in orders:
        order["_id"] = str(order["_id"])
    return orders


def update_order_status(order_id: str, status: str) -> bool:
    """Update order status."""
    db = get_db()
    result = db.orders.update_one(
        {"order_id": order_id},
        {"$set": {"status": status, "updated_at": datetime.utcnow()}}
    )
    
    # If confirming, create revenue
    if status == "confirmed":
        order = db.orders.find_one({"order_id": order_id})
        if order:
            create_revenue_from_order(order)
    
    return result.modified_count > 0


# ============== REVENUE OPERATIONS ==============

def deduct_inventory_for_order(order: dict) -> list:
    """
    Deduct inventory stock for confirmed order items.
    
    Args:
        order: Order dictionary containing items to deduct.
        
    Returns:
        list: Items that were successfully deducted from inventory.
    """
    db = get_db()
    sector_id = order.get("sector_id", "")
    items = order.get("items", [])
    deducted = []
    
    logger.debug(f"Deducting inventory for order {order.get('order_id')}, sector: {sector_id}")
    logger.debug(f"Items to deduct: {items}")
    
    for item in items:
        # Try to get item_id from multiple possible keys
        item_id = item.get("product_id") or item.get("item_id") or item.get("id")
        quantity = int(item.get("quantity", 1))
        item_name = item.get("product_name") or item.get("name_en") or item.get("name", "")
        
        logger.debug(f"Processing item: {item_name}, ID: {item_id}, Qty: {quantity}")
        
        # If no item_id, try to find by name
        if not item_id and item_name:
            inv_item = db.inventory.find_one({
                "sector_id": sector_id,
                "$or": [
                    {"name_en": {"$regex": f"^{item_name}$", "$options": "i"}},
                    {"name_ar": {"$regex": f"^{item_name}$", "$options": "i"}},
                    {"name_en": {"$regex": item_name, "$options": "i"}},
                    {"name_ar": {"$regex": item_name, "$options": "i"}}
                ]
            })
            if inv_item:
                item_id = inv_item.get("item_id")
                logger.debug(f"Found item by name: {item_id}")
        
        if item_id:
            # Check current stock before deducting
            current_item = db.inventory.find_one({"sector_id": sector_id, "item_id": item_id})
            if current_item:
                current_stock = current_item.get("stock_qty", 0)
                if current_stock < quantity:
                    logger.warning(f"Insufficient stock for {item_id}: have {current_stock}, need {quantity}")
                    # Still deduct but log warning - business decision may allow overselling
            
            # Deduct stock
            result = db.inventory.update_one(
                {"sector_id": sector_id, "item_id": item_id},
                {
                    "$inc": {"stock_qty": -quantity},
                    "$set": {"updated_at": datetime.utcnow()}
                }
            )
            
            if result.modified_count > 0:
                # Log movement
                db.inventory_movements.insert_one({
                    "sector_id": sector_id,
                    "item_id": item_id,
                    "delta": -quantity,
                    "reason": f"Sale - Order {order.get('order_id')}",
                    "order_id": order.get("order_id"),
                    "product_name": item_name,
                    "created_at": datetime.utcnow()
                })
                deducted.append({"item_id": item_id, "name": item_name, "quantity": quantity})
                logger.debug(f"Deducted {quantity} from {item_id} ({item_name})")
            else:
                logger.debug(f"Failed to deduct - item not found in inventory: {item_id}")
        else:
            logger.debug(f"No item_id found for: {item_name}")
    
    logger.debug(f"Total deducted items: {len(deducted)}")
    return deducted


def create_revenue_from_order(order: dict) -> dict:
    """
    Create revenue record from a confirmed order.
    
    Also triggers inventory deduction for order items.
    Uses upsert to prevent duplicate revenue entries.
    
    Args:
        order: Order dictionary with order_id, items, total, etc.
        
    Returns:
        dict: Revenue record with _id as string.
    """
    db = get_db()
    
    logger.debug(f"Creating revenue for order: {order.get('order_id')}")
    
    # First deduct inventory
    deduct_inventory_for_order(order)
    
    # Build items summary
    items = order.get("items", [])
    if items:
        items_summary = ", ".join([
            f"{item.get('product_name', 'Item')} x{item.get('quantity', 1)}"
            for item in items[:3]
        ])
        if len(items) > 3:
            items_summary += f" (+{len(items) - 3} more)"
    else:
        items_summary = "Order items"
    
    revenue = {
        "transaction_id": f"REV-{order['order_id'].replace('ORD-', '')}",
        "order_id": order["order_id"],
        "sector_id": order.get("sector_id", ""),
        "business_name": order.get("business_name", ""),
        "amount": float(order.get("total", 0)),
        "items_summary": items_summary,
        "customer_phone": order.get("customer_phone", ""),
        "date": datetime.now().strftime("%Y-%m-%d"),  # Use local date for consistency
        "timestamp": datetime.utcnow(),
        "notes": f"Auto-logged from order {order['order_id']}"
    }
    
    # Use upsert to prevent race condition duplicates
    result = db.revenues.update_one(
        {"order_id": order["order_id"]},
        {"$setOnInsert": revenue},
        upsert=True
    )
    
    if not result.upserted_id:
        # Revenue already existed
        existing = db.revenues.find_one({"order_id": order["order_id"]})
        logger.debug(f"Revenue already exists for order {order['order_id']}")
        if existing:
            existing["_id"] = str(existing["_id"])
        return existing
    
    revenue["_id"] = str(result.upserted_id)
    logger.debug(f"Revenue created: {revenue['transaction_id']} - Amount: {revenue['amount']}")
    return revenue


def add_manual_revenue(revenue_data: dict) -> dict:
    """Add manual revenue entry."""
    db = get_db()
    
    revenue = {
        "transaction_id": revenue_data.get("transaction_id", f"REV-MANUAL-{datetime.utcnow().strftime('%Y%m%d%H%M%S')}"),
        "order_id": revenue_data.get("order_id", "MANUAL"),
        "sector_id": revenue_data.get("sector_id", ""),
        "business_name": revenue_data.get("business_name", ""),
        "amount": float(revenue_data.get("amount", 0)),
        "items_summary": revenue_data.get("items_summary", "Manual entry"),
        "customer_phone": revenue_data.get("customer_phone", ""),
        "date": revenue_data.get("date", datetime.now().strftime("%Y-%m-%d")),
        "timestamp": datetime.utcnow(),
        "notes": revenue_data.get("notes", "Manual entry")
    }
    
    result = db.revenues.insert_one(revenue)
    revenue["_id"] = str(result.inserted_id)
    return revenue


def get_revenues_by_date(date: str, business_name: str = "", sector_id: str = "") -> list:
    """Get revenues for a specific date."""
    db = get_db()
    query = {"date": date}
    if business_name:
        query["business_name"] = business_name
    if sector_id:
        query["sector_id"] = sector_id
    
    revenues = list(db.revenues.find(query).sort("timestamp", -1))
    for rev in revenues:
        rev["_id"] = str(rev["_id"])
    return revenues


def get_revenues_by_date_range(start_date: str, end_date: str, business_name: str = "", sector_id: str = "") -> list:
    """Get revenues for a date range."""
    db = get_db()
    query = {
        "date": {"$gte": start_date, "$lte": end_date}
    }
    if business_name:
        query["business_name"] = business_name
    if sector_id:
        query["sector_id"] = sector_id
    
    revenues = list(db.revenues.find(query).sort("timestamp", -1))
    for rev in revenues:
        rev["_id"] = str(rev["_id"])
    return revenues


# ============== EXPENSE OPERATIONS ==============

def add_expense(expense_data: dict) -> dict:
    """Add expense record."""
    db = get_db()
    
    expense = {
        "expense_id": expense_data.get("expense_id", f"EXP-{datetime.utcnow().strftime('%Y%m%d%H%M%S')}"),
        "category": expense_data.get("category"),
        "amount": float(expense_data.get("amount", 0)),
        "description": expense_data.get("description", ""),
        "business_name": expense_data.get("business_name", ""),
        "date": expense_data.get("date", datetime.now().strftime("%Y-%m-%d")),
        "timestamp": datetime.utcnow(),
        "notes": expense_data.get("notes", "")
    }
    
    result = db.expenses.insert_one(expense)
    expense["_id"] = str(result.inserted_id)
    return expense


def get_expenses_by_date(date: str, business_name: str = "") -> list:
    """Get expenses for a specific date."""
    db = get_db()
    query = {"date": date}
    if business_name:
        query["business_name"] = business_name
    
    expenses = list(db.expenses.find(query).sort("timestamp", -1))
    for exp in expenses:
        exp["_id"] = str(exp["_id"])
    return expenses


def get_expenses_by_date_range(start_date: str, end_date: str, business_name: str = "") -> list:
    """Get expenses for a date range."""
    db = get_db()
    query = {
        "date": {"$gte": start_date, "$lte": end_date}
    }
    if business_name:
        query["business_name"] = business_name
    
    expenses = list(db.expenses.find(query).sort("timestamp", -1))
    for exp in expenses:
        exp["_id"] = str(exp["_id"])
    return expenses


# ============== CHAT MESSAGE OPERATIONS ==============

def save_chat_message(message_data: dict) -> dict:
    """Save chat message."""
    db = get_db()
    
    message = {
        "session_id": message_data.get("session_id"),
        "user_id": message_data.get("user_id"),
        "role": message_data.get("role"),  # 'user' or 'assistant'
        "content": message_data.get("content"),
        "sector_id": message_data.get("sector_id"),
        "business_name": message_data.get("business_name"),
        "created_at": datetime.utcnow()
    }
    
    result = db.chat_messages.insert_one(message)
    message["_id"] = str(result.inserted_id)
    return message


def get_chat_history(session_id: str, limit: int = 50) -> list:
    """Get chat history for a session."""
    db = get_db()
    messages = list(
        db.chat_messages.find({"session_id": session_id})
        .sort("created_at", 1)
        .limit(limit)
    )
    for msg in messages:
        msg["_id"] = str(msg["_id"])
    return messages


# ============== INVENTORY OPERATIONS ==============

def list_inventory(filters: dict = None, limit: int = 500) -> list:
    """List inventory items with optional filters."""
    db = get_db()
    query = filters or {}
    items = list(db.inventory.find(query).sort("updated_at", -1).limit(limit))
    for item in items:
        item["_id"] = str(item["_id"])
    return items


def get_inventory_item(sector_id: str, item_id: str) -> dict:
    """Get a single inventory item by sector and item ID."""
    db = get_db()
    item = db.inventory.find_one({"sector_id": sector_id, "item_id": item_id})
    if item:
        item["_id"] = str(item["_id"])
    return item


def update_inventory_item(sector_id: str, item_id: str, updates: dict) -> dict:
    """Update inventory item fields."""
    db = get_db()
    updates = updates or {}
    updates["updated_at"] = datetime.utcnow()

    result = db.inventory.update_one(
        {"sector_id": sector_id, "item_id": item_id},
        {"$set": updates}
    )

    if result.matched_count == 0:
        return None

    return get_inventory_item(sector_id, item_id)


def adjust_inventory_stock(
    sector_id: str,
    item_id: str,
    delta: int,
    reason: str = "",
    user_id: str = "",
    username: str = ""
) -> dict:
    """Adjust inventory stock quantity and log movement."""
    db = get_db()
    now = datetime.utcnow()

    result = db.inventory.update_one(
        {"sector_id": sector_id, "item_id": item_id},
        {
            "$inc": {"stock_qty": int(delta)},
            "$set": {"updated_at": now}
        }
    )

    if result.matched_count == 0:
        return None

    db.inventory_movements.insert_one({
        "sector_id": sector_id,
        "item_id": item_id,
        "delta": int(delta),
        "reason": reason,
        "user_id": user_id,
        "username": username,
        "created_at": now
    })

    return get_inventory_item(sector_id, item_id)


def get_low_stock_items(sector_id: str = "", limit: int = 200) -> list:
    """Get items with stock at or below reorder level."""
    db = get_db()
    query = {
        "$expr": {"$lte": ["$stock_qty", "$reorder_level"]}
    }
    if sector_id:
        query["sector_id"] = sector_id

    items = list(db.inventory.find(query).sort("stock_qty", 1).limit(limit))
    for item in items:
        item["_id"] = str(item["_id"])
    return items


# ============== REPORTING ==============

def get_daily_summary(date: str, business_name: str = "", sector_id: str = "") -> dict:
    """Generate daily financial summary from MongoDB."""
    revenues = get_revenues_by_date(date, business_name, sector_id)
    expenses = get_expenses_by_date(date, business_name)
    
    total_revenue = sum(r.get("amount", 0) for r in revenues)
    total_expenses = sum(e.get("amount", 0) for e in expenses)
    net_profit = total_revenue - total_expenses
    
    return {
        "date": date,
        "business_name": business_name or "All Businesses",
        "sector_id": sector_id,
        "total_revenue": total_revenue,
        "total_expenses": total_expenses,
        "net_profit": net_profit,
        "order_count": len(revenues),
        "expense_count": len(expenses),
        "revenue_transactions": revenues,
        "expense_transactions": expenses,
        "currency": "EGP"
    }


def get_weekly_summary(week_start: str, business_name: str = "", sector_id: str = "") -> dict:
    """Generate weekly financial summary from MongoDB."""
    from datetime import timedelta
    start = datetime.fromisoformat(week_start)
    end = start + timedelta(days=6)
    end_str = end.strftime("%Y-%m-%d")
    
    revenues = get_revenues_by_date_range(week_start, end_str, business_name, sector_id)
    expenses = get_expenses_by_date_range(week_start, end_str, business_name)
    
    total_revenue = sum(r.get("amount", 0) for r in revenues)
    total_expenses = sum(e.get("amount", 0) for e in expenses)
    
    # Group expenses by category
    expense_categories = {}
    for exp in expenses:
        cat = exp.get("category", "Other")
        expense_categories[cat] = expense_categories.get(cat, 0) + exp.get("amount", 0)
    
    # Daily breakdown
    daily_breakdown = []
    current = start
    while current <= end:
        date_str = current.strftime("%Y-%m-%d")
        day_revs = [r for r in revenues if r.get("date") == date_str]
        day_exps = [e for e in expenses if e.get("date") == date_str]
        day_rev = sum(r.get("amount", 0) for r in day_revs)
        day_exp = sum(e.get("amount", 0) for e in day_exps)
        daily_breakdown.append({
            "date": date_str,
            "revenue": day_rev,
            "expenses": day_exp,
            "profit": day_rev - day_exp,
            "orders": len(day_revs)
        })
        current += timedelta(days=1)
    
    return {
        "week_start": week_start,
        "week_end": end_str,
        "business_name": business_name or "All Businesses",
        "total_revenue": total_revenue,
        "total_expenses": total_expenses,
        "net_profit": total_revenue - total_expenses,
        "order_count": len(revenues),
        "expense_count": len(expenses),
        "daily_breakdown": daily_breakdown,
        "top_expense_categories": dict(sorted(expense_categories.items(), key=lambda x: x[1], reverse=True)),
        "average_daily_revenue": total_revenue / 7 if total_revenue > 0 else 0,
        "currency": "EGP"
    }


# ============== INITIALIZATION ==============

def init_db():
    """
    Initialize database and create default users if needed.
    
    Creates default admin (accounting) and customer users if they don't exist.
    Seeds inventory data for all supported sectors.
    
    Returns:
        Database: MongoDB database instance.
        
    Raises:
        SystemExit: If MongoDB connection fails.
    """
    try:
        db = get_db()
    except Exception as e:
        logger.critical(f"Failed to connect to MongoDB: {e}")
        logger.critical("Make sure MongoDB is running on localhost:27017")
        raise SystemExit(1)
    
    # Create default accounting user if not exists
    if not db.users.find_one({"username": "admin"}):
        create_user(
            username="admin",
            password="admin123",
            role="accounting",
            business_name="My Store"
        )
        logger.info("Created default accounting user: admin/admin123")
    
    # Create default customer if not exists
    if not db.users.find_one({"username": "customer"}):
        create_user(
            username="customer",
            password="customer123",
            role="customer",
            business_name="My Store"  # Must match accounting user's business_name
        )
        logger.info("Created default customer user: customer/customer123")
    else:
        # Update existing customer to have business_name if missing
        db.users.update_one(
            {"username": "customer", "business_name": {"$in": ["", None]}},
            {"$set": {"business_name": "My Store"}}
        )

    # Seed inventory data if not already present
    seed_result = seed_inventory_data(force=False)
    if seed_result.get("seeded") or seed_result.get("updated"):
        logger.info(f"Inventory seeded: {seed_result}")
    
    return db
