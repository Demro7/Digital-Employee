"""
Digital Employee for MSMEs - Main Application
=============================================

A unified digital employee system for Micro, Small, and Medium Enterprises (MSMEs)
that supports Egypt's Vision 2030 for economic development.

Features:
    - Multi-sector AI chat agent for automated sales
    - Bilingual support (Arabic/English) with auto-detection
    - Order management and tracking
    - Financial reporting (daily/weekly summaries)
    - Inventory management with low-stock alerts
    - Role-based authentication (customers/accounting)
    - AI-powered business analysis and marketing content generation

Supported Sectors:
    Restaurant, Fashion Retail, Electronics, Pharmacy, Grocery,
    Home Services, Education, Clinic & Beauty, Travel, Repair Workshop
"""

# Standard library imports
import os
import json
import re
import uuid
import logging
from datetime import datetime, date, timedelta

# Third-party imports
from flask import Flask, render_template, request, jsonify, session, redirect, url_for
from flask_cors import CORS
from openai import OpenAI
from dotenv import load_dotenv

# Import database and auth modules
from database import (
    init_db, get_db,
    authenticate_user, create_user, get_user_by_id,
    save_order, get_orders, update_order_status,
    add_expense as db_add_expense,
    add_manual_revenue,
    get_daily_summary as db_get_daily_summary,
    get_weekly_summary as db_get_weekly_summary,
    get_revenues_by_date, get_expenses_by_date,
    save_chat_message,
    seed_inventory_data, list_inventory,
    update_inventory_item, adjust_inventory_stock, get_low_stock_items
)
from auth import (
    generate_token, decode_token, get_current_user,
    login_required, role_required, customer_only, accounting_only
)

load_dotenv()

# Configure logging
logger = logging.getLogger(__name__)
logging.basicConfig(
    level=logging.DEBUG if os.getenv("DEBUG", "").lower() == "true" else logging.INFO,
    format="[%(levelname)s] %(name)s: %(message)s"
)

app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY", os.urandom(24).hex())
CORS(app, supports_credentials=True)

# Initialize OpenAI client
client = None

def get_openai_client():
    global client
    if client is None:
        api_key = os.getenv("OPENAI_API_KEY")
        if api_key:
            client = OpenAI(api_key=api_key)
    return client

# Load sector configurations
SECTORS = {}
SECTORS_DIR = os.path.join(os.path.dirname(__file__), "config", "sectors")

def load_sectors():
    """Load all sector configurations from JSON files."""
    global SECTORS
    for filename in os.listdir(SECTORS_DIR):
        if filename.endswith(".json"):
            filepath = os.path.join(SECTORS_DIR, filename)
            with open(filepath, "r", encoding="utf-8") as f:
                sector_data = json.load(f)
                SECTORS[sector_data["sector_id"]] = sector_data

load_sectors()

# Expense categories
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


def detect_language(text: str) -> str:
    """Detect if text is Arabic or English."""
    arabic_chars = sum(1 for c in text if '\u0600' <= c <= '\u06FF')
    return "ar" if arabic_chars > len(text) * 0.3 else "en"


def get_sector_context(sector_id: str, business_name: str = "Our Store") -> str:
    """Build context string for the AI based on sector configuration."""
    sector = SECTORS.get(sector_id)
    if not sector:
        return ""
    
    catalog_str = "Available Products/Services:\n"
    for item in sector["catalog"]:
        catalog_str += f"- {item['name_en']} ({item['name_ar']}): {item['price']} EGP per {item['unit']}\n"
    
    faq_str = "FAQs:\n"
    for faq in sector["faqs"]:
        faq_str += f"- Keywords: {', '.join(faq['keywords'])}\n"
        faq_str += f"  EN: {faq['answer_en']}\n"
        faq_str += f"  AR: {faq['answer_ar']}\n"
    
    return f"""
Business Name: {business_name}
Sector: {sector['sector_name']['en']} / {sector['sector_name']['ar']}

{catalog_str}

{faq_str}

Order Flow:
1. Greet the customer
2. Help them browse/choose items
3. Answer any questions (FAQs)
4. Collect order details: items, quantity, phone, address
5. Confirm the order
6. Provide order ID
"""


def build_system_prompt(sector_id: str, business_name: str, lang: str) -> str:
    """Build the system prompt for the chat agent."""
    sector_context = get_sector_context(sector_id, business_name)
    
    return f"""You are a friendly and professional digital sales assistant for a small business.

SECTOR CONTEXT:
{sector_context}

RULES:
1. Detect the customer's language (Arabic or English) and respond in the same language.
2. Be polite, brief, and helpful.
3. Show the catalog when asked or when customer seems unsure.
4. Answer FAQs accurately based on the provided information.
5. When collecting an order:
   - Ask for items and quantities
   - Ask for phone number
   - Ask for delivery address (if applicable)
   - Summarize the order with total price
   - Ask for confirmation (YES/NO)
6. IMPORTANT: When the customer confirms the order (says yes, نعم, اه, تمام, أكد, confirm, etc.):
   - Generate a unique order ID in format: ORD-XXXXX (5 random characters)
   - Say EXACTLY: "تم تأكيد الطلب" (in Arabic) or "Order confirmed" (in English)
   - Include the order ID, items summary, and total price
7. Do NOT say "order confirmed" or "تم تأكيد الطلب" unless the customer has explicitly confirmed!
8. Do NOT make up information not in the context.
9. Do NOT handle payments, inventory, or accounting - just capture the order.
10. If asked about something outside your scope, politely say you can only help with orders and product info.

Always be warm and make the customer feel valued!
"""


def extract_order_details_from_conversation(conversation_history: list, assistant_message: str, sector_id: str) -> dict:
    """Extract order details from conversation history using AI."""
    # Combine all messages to analyze
    full_conversation = "\n".join([
        f"{msg.get('role', 'user')}: {msg.get('content', '')}" 
        for msg in conversation_history
    ])
    full_conversation += f"\nassistant: {assistant_message}"
    
    # Get sector data for product matching - use 'catalog' not 'products'
    sector = SECTORS.get(sector_id, {})
    catalog = sector.get("catalog", [])
    # Include product ID for inventory matching
    product_list = [
        {
            "id": p.get("id", ""), 
            "name_en": p.get("name_en", ""), 
            "name_ar": p.get("name_ar", ""), 
            "price": p.get("price", 0)
        } 
        for p in catalog
    ]
    
    logger.debug(f"Extracting order from conversation for sector: {sector_id}")
    logger.debug(f"Products available: {len(product_list)}")
    
    try:
        openai_client = get_openai_client()
        if not openai_client:
            logger.debug("OpenAI client not available")
            return {"items": [], "total": 0, "phone": "", "address": ""}
        
        extraction_prompt = f"""Analyze this conversation and extract order details.
Products available (with IDs): {json.dumps(product_list, ensure_ascii=False)}

Conversation:
{full_conversation}

Extract and return ONLY a JSON object (no markdown, no explanation) with these fields:
- items: array of {{"product_id": "ID from list", "product_name": "product name", "quantity": number, "price": number per unit}}
- total: number (total price = sum of quantity * price for each item)
- phone: string (customer phone if mentioned)
- address: string (delivery address if mentioned)

IMPORTANT: 
- Match product names to the products list and use the correct ID and price
- Calculate total correctly as sum of (quantity × price) for all items
- If a field is not found, use empty array for items, 0 for total, empty string for phone/address

Return ONLY valid JSON, nothing else."""

        response = openai_client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": extraction_prompt}],
            temperature=0,
            max_tokens=500
        )
        
        result_text = response.choices[0].message.content.strip()
        logger.debug(f"Extraction response: {result_text[:200]}...")
        
        # Clean up response if it has markdown code blocks
        if result_text.startswith("```"):
            result_text = result_text.split("```")[1]
            if result_text.startswith("json"):
                result_text = result_text[4:]
        result_text = result_text.strip()
        
        extracted = json.loads(result_text)
        logger.debug(f"Extracted order: {extracted}")
        return extracted
    except Exception as e:
        logger.error(f"Order extraction error: {str(e)}", exc_info=True)
        # Return None to indicate extraction failure - caller should handle this
        return None


def chat_with_agent(
    user_message: str,
    conversation_history: list,
    sector_id: str,
    business_name: str,
    user_id: str = None,
    session_id: str = None
) -> dict:
    """Send message to AI agent and get response."""
    
    lang = detect_language(user_message)
    system_prompt = build_system_prompt(sector_id, business_name, lang)
    
    messages = [{"role": "system", "content": system_prompt}]
    messages.extend(conversation_history)
    messages.append({"role": "user", "content": user_message})
    
    # Save user message to DB
    if session_id:
        save_chat_message({
            "session_id": session_id,
            "user_id": user_id,
            "role": "user",
            "content": user_message,
            "sector_id": sector_id,
            "business_name": business_name
        })
    
    try:
        openai_client = get_openai_client()
        if not openai_client:
            return {
                "success": False,
                "message": "OpenAI API key not configured",
                "language": lang,
                "order_id": None,
                "order_details": None
            }
        
        response = openai_client.chat.completions.create(
            model="gpt-4o-mini",
            messages=messages,
            temperature=0.7,
            max_tokens=500
        )
        
        assistant_message = response.choices[0].message.content
        
        # Save assistant message to DB
        if session_id:
            save_chat_message({
                "session_id": session_id,
                "user_id": user_id,
                "role": "assistant",
                "content": assistant_message,
                "sector_id": sector_id,
                "business_name": business_name
            })
        
        # Check if order was confirmed - look for order confirmation patterns
        order_id = None
        order_details = None
        
        logger.debug(f"Checking for order in message: {assistant_message[:100]}...")
        
        # First check for explicit ORD- format (most reliable)
        if "ORD-" in assistant_message:
            match = re.search(r'ORD-[A-Z0-9]+', assistant_message)
            if match:
                order_id = match.group()
                logger.debug(f"Found explicit order ID: {order_id}")
        
        # Check for strong order confirmation patterns (must have BOTH confirmation AND order context)
        # Only trigger if AI clearly confirmed an order with specific phrases
        if not order_id:
            message_lower = assistant_message.lower()
            
            # Strong confirmation phrases that clearly indicate order was placed
            strong_confirmations = [
                "order confirmed", "order is confirmed", "order has been confirmed",
                "تم تأكيد الطلب", "تم تسجيل طلبك", "طلبك تم بنجاح",
                "your order has been placed", "order placed successfully",
                "order has been received", "we have received your order",
                "تم استلام طلبك", "طلبك جاهز"
            ]
            
            # Check for strong confirmation
            has_strong_confirmation = any(
                phrase in message_lower or phrase in assistant_message 
                for phrase in strong_confirmations
            )
            
            # Also check if message contains total/price AND items (likely a final order summary)
            has_total = any(word in message_lower for word in ["total", "الإجمالي", "المجموع", "egp", "جنيه"])
            has_items = any(word in message_lower for word in ["item", "منتج", "burger", "pizza", "برجر", "بيتزا"])
            
            if has_strong_confirmation:
                order_id = f"ORD-{uuid.uuid4().hex[:5].upper()}"
                logger.debug(f"Generated order ID from strong confirmation: {order_id}")
        
        # Extract order details if order was confirmed
        if order_id:
            logger.debug(f"Extracting order details for: {order_id}")
            order_details = extract_order_details_from_conversation(
                conversation_history, 
                assistant_message, 
                sector_id
            )
            # If extraction failed, don't process order
            if order_details is None:
                logger.warning(f"Order extraction failed for {order_id}, skipping order creation")
                order_id = None  # Clear order_id so frontend doesn't save broken order
            else:
                logger.debug(f"Order details extracted: {order_details}")
        
        return {
            "success": True,
            "message": assistant_message,
            "language": lang,
            "order_id": order_id,
            "order_details": order_details
        }
        
    except Exception as e:
        logger.error(f"OpenAI API Error: {str(e)}", exc_info=True)
        return {
            "success": False,
            "message": f"Error: {str(e)}",
            "language": lang,
            "order_id": None,
            "order_details": None
        }


# ============== AUTHENTICATION ROUTES ==============

@app.route("/login")
def login_page():
    """Render login page."""
    return render_template("login.html")


@app.route("/api/auth/login", methods=["POST"])
def login():
    """Handle user login."""
    data = request.json
    username = data.get("username", "").strip()
    password = data.get("password", "")
    
    if not username or not password:
        return jsonify({"success": False, "error": "Username and password required"}), 400
    
    result = authenticate_user(username, password)
    
    if result["success"]:
        user = result["user"]
        token = generate_token(user)
        
        # Store in session
        session["user"] = {
            "user_id": user["_id"],
            "username": user["username"],
            "role": user["role"],
            "business_name": user.get("business_name", "")
        }
        session["token"] = token
        
        return jsonify({
            "success": True,
            "user": user,
            "token": token,
            "redirect": "/sales" if user["role"] == "customer" else "/accounting"
        })
    
    return jsonify(result), 401


@app.route("/api/auth/logout", methods=["POST"])
def logout():
    """Handle user logout."""
    session.clear()
    return jsonify({"success": True, "message": "Logged out successfully"})


@app.route("/api/auth/me", methods=["GET"])
def get_me():
    """Get current user info."""
    user = get_current_user()
    if user:
        return jsonify({"success": True, "user": user})
    return jsonify({"success": False, "error": "Not authenticated"}), 401


@app.route("/api/auth/register", methods=["POST"])
def register():
    """Register a new CUSTOMER user only. Accounting users must be added by admin."""
    data = request.json
    username = data.get("username", "").strip()
    password = data.get("password", "")
    
    if not username or not password:
        return jsonify({"success": False, "error": "Username and password required"}), 400
    
    if len(password) < 6:
        return jsonify({"success": False, "error": "Password must be at least 6 characters"}), 400
    
    # ONLY allow customer registration - accounting users are added manually
    result = create_user(
        username=username,
        password=password,
        role="customer"  # Always customer, never accounting
    )
    
    if result["success"]:
        return jsonify({"success": True, "message": "Customer account created! Please login."})
    
    return jsonify(result), 400


# ============== PAGE ROUTES ==============

@app.route("/")
def index():
    """Redirect to login or appropriate page based on role."""
    user = get_current_user()
    if not user:
        return redirect("/login")
    
    if user.get("role") == "customer":
        return redirect("/sales")
    else:
        return redirect("/accounting")


@app.route("/sales")
def sales_page():
    """Render sales/chat page for customers."""
    user = get_current_user()
    if not user:
        return redirect("/login")
    
    if user.get("role") != "customer":
        return redirect("/accounting")
    
    return render_template("sales.html", sectors=SECTORS, user=user)


@app.route("/accounting")
def accounting_page():
    """Render accounting page for staff."""
    user = get_current_user()
    if not user:
        return redirect("/login")
    
    if user.get("role") != "accounting":
        return redirect("/sales")
    
    # Prepare sectors data for the template
    sectors_for_template = {}
    for sid, sdata in SECTORS.items():
        sectors_for_template[sid] = {
            "name_en": sdata["sector_name"]["en"],
            "name_ar": sdata["sector_name"]["ar"],
            "icon": sdata.get("icon", "🏪")
        }
    
    return render_template("accounting.html", user=user, sectors=sectors_for_template)


# ============== SALES API ROUTES ==============

@app.route("/api/sectors", methods=["GET"])
def get_sectors():
    """Get list of available sectors."""
    sector_list = []
    for sid, sdata in SECTORS.items():
        sector_list.append({
            "id": sid,
            "name_en": sdata["sector_name"]["en"],
            "name_ar": sdata["sector_name"]["ar"]
        })
    return jsonify(sector_list)


@app.route("/api/sector/<sector_id>", methods=["GET"])
def get_sector(sector_id):
    """Get sector configuration."""
    if sector_id in SECTORS:
        return jsonify(SECTORS[sector_id])
    return jsonify({"error": "Sector not found"}), 404


@app.route("/api/chat", methods=["POST"])
@customer_only
def chat():
    """Handle chat messages - customers only."""
    user = get_current_user()
    
    data = request.json
    user_message = data.get("message", "")
    sector_id = data.get("sector_id", "fashion_retail")
    conversation_history = data.get("history", [])
    session_id = data.get("session_id", str(uuid.uuid4()))
    
    # Get business_name from user's account data (set by admin)
    business_name = user.get("business_name", "My Store") if user else "My Store"
    
    if not user_message:
        return jsonify({"error": "No message provided"}), 400
    
    result = chat_with_agent(
        user_message,
        conversation_history,
        sector_id,
        business_name,
        user_id=user.get("user_id") if user else None,
        session_id=session_id
    )
    
    result["session_id"] = session_id
    return jsonify(result)


@app.route("/api/orders", methods=["GET"])
@login_required
def get_orders_endpoint():
    """Get orders."""
    user = get_current_user()
    filters = {}
    
    # Customers see only their orders
    if user.get("role") == "customer":
        filters["customer_id"] = user.get("user_id")
    
    orders = get_orders(filters)
    return jsonify(orders)


@app.route("/api/order", methods=["POST"])
@customer_only
def save_order_endpoint():
    """Save a confirmed order and auto-log revenue."""
    user = get_current_user()
    data = request.json
    
    logger.debug(f"/api/order called with data: {data}")
    
    order_id = data.get("order_id") or f"ORD-{uuid.uuid4().hex[:5].upper()}"
    
    # Get business_name from user's account data - default to "My Store" to match accounting
    business_name = user.get("business_name") if user else "My Store"
    if not business_name:
        business_name = "My Store"  # Ensure business_name is never empty
    
    # Validate and recalculate total from items
    items = data.get("items", [])
    calculated_total = sum(
        float(item.get("price", 0)) * int(item.get("quantity", 1)) 
        for item in items
    )
    submitted_total = float(data.get("total", 0))
    
    # Use calculated total, log if mismatch
    if abs(calculated_total - submitted_total) > 0.01 and calculated_total > 0:
        logger.warning(f"Order total mismatch! Submitted: {submitted_total}, Calculated: {calculated_total}")
    
    final_total = calculated_total if calculated_total > 0 else submitted_total
    
    order_data = {
        "order_id": order_id,
        "sector_id": data.get("sector_id"),
        "business_name": business_name,
        "customer_id": user.get("user_id") if user else None,
        "items": items,
        "customer_phone": data.get("phone"),
        "customer_address": data.get("address"),
        "total": final_total,
        "status": "confirmed"
    }
    
    logger.debug(f"Saving order: {order_data}")
    
    order = save_order(order_data)
    
    logger.debug(f"Order saved successfully: {order}")
    
    return jsonify({
        "success": True,
        "order": order
    })


# ============== ACCOUNTING API ROUTES ==============

@app.route("/api/accounting/revenue", methods=["POST"])
@accounting_only
def add_revenue_endpoint():
    """Manually add a revenue transaction."""
    data = request.json
    user = get_current_user()
    
    revenue_data = {
        "order_id": data.get("order_id", f"MANUAL-{uuid.uuid4().hex[:5].upper()}"),
        "sector_id": data.get("sector_id", ""),
        "business_name": user.get("business_name", "") if user else "",
        "amount": data.get("amount", 0),
        "items_summary": data.get("items_summary", "Manual entry"),
        "customer_phone": data.get("customer_phone", ""),
        "date": data.get("date"),
        "notes": data.get("notes", "Manual entry")
    }
    
    revenue = add_manual_revenue(revenue_data)
    
    return jsonify({
        "success": True,
        "transaction": revenue
    })


@app.route("/api/accounting/expense", methods=["POST"])
@accounting_only
def add_expense_endpoint():
    """Add a manual expense entry."""
    data = request.json
    user = get_current_user()
    
    required = ["category", "amount", "description"]
    for field in required:
        if field not in data:
            return jsonify({"error": f"Missing required field: {field}"}), 400
    
    # Validate amount is positive number
    try:
        amount = float(data["amount"])
        if amount <= 0:
            return jsonify({"error": "Amount must be a positive number"}), 400
    except (ValueError, TypeError):
        return jsonify({"error": "Amount must be a valid number"}), 400
    
    expense_data = {
        "category": data["category"],
        "amount": amount,
        "description": data["description"],
        "business_name": user.get("business_name", "") if user else "",
        "date": data.get("date"),
        "notes": data.get("notes", "")
    }
    
    expense = db_add_expense(expense_data)
    
    return jsonify({
        "success": True,
        "expense": expense
    })


@app.route("/api/accounting/daily", methods=["GET"])
@accounting_only
def get_daily_report():
    """Get daily financial summary."""
    user = get_current_user()
    target_date = request.args.get("date", date.today().isoformat())
    business_name = user.get("business_name", "") if user else ""
    sector_id = request.args.get("sector_id", "")
    lang = request.args.get("lang", "en")
    
    summary = db_get_daily_summary(target_date, business_name, sector_id)
    
    # Get sector name for display
    sector_display = ""
    if sector_id and sector_id in SECTORS:
        sector_display = f" ({SECTORS[sector_id]['sector_name']['en']})"
    
    # Generate summary text
    if lang == "ar":
        sector_ar = ""
        if sector_id and sector_id in SECTORS:
            sector_ar = f" ({SECTORS[sector_id]['sector_name']['ar']})"
        summary_text = f"""📊 ملخص يوم {summary['date']}{sector_ar}
═══════════════════════════════
🏪 {summary['business_name'] or 'جميع المتاجر'}

💰 إجمالي المبيعات: {summary['total_revenue']:,.2f} جنيه
   ({summary['order_count']} طلب)

💸 إجمالي المصروفات: {summary['total_expenses']:,.2f} جنيه
   ({summary['expense_count']} معاملة)

═══════════════════════════════
📈 صافي الربح: {summary['net_profit']:,.2f} جنيه
═══════════════════════════════"""
    else:
        summary_text = f"""📊 Daily Summary - {summary['date']}{sector_display}
═══════════════════════════════
🏪 {summary['business_name'] or 'All Stores'}

💰 Total Revenue: {summary['total_revenue']:,.2f} EGP
   ({summary['order_count']} orders)

💸 Total Expenses: {summary['total_expenses']:,.2f} EGP
   ({summary['expense_count']} transactions)

═══════════════════════════════
📈 Net Profit: {summary['net_profit']:,.2f} EGP
═══════════════════════════════"""
    
    return jsonify({
        "success": True,
        "summary": summary,
        "summary_text": summary_text
    })


@app.route("/api/accounting/weekly", methods=["GET"])
@accounting_only
def get_weekly_report():
    """Get weekly financial summary."""
    user = get_current_user()
    today = date.today()
    default_start = today - timedelta(days=today.weekday())
    
    week_start = request.args.get("weekStart", default_start.isoformat())
    business_name = user.get("business_name", "") if user else ""
    sector_id = request.args.get("sector_id", "")
    lang = request.args.get("lang", "en")
    
    summary = db_get_weekly_summary(week_start, business_name, sector_id)
    
    # Get sector name for display
    sector_display = ""
    sector_ar = ""
    if sector_id and sector_id in SECTORS:
        sector_display = f" ({SECTORS[sector_id]['sector_name']['en']})"
        sector_ar = f" ({SECTORS[sector_id]['sector_name']['ar']})"
    
    # Generate summary text
    expense_breakdown = "\n".join([f"   • {cat}: {amt:,.2f} {'جنيه' if lang == 'ar' else 'EGP'}" 
                                   for cat, amt in summary.get('top_expense_categories', {}).items()])
    
    if lang == "ar":
        summary_text = f"""📊 ملخص الأسبوع{sector_ar}
{summary['week_start']} إلى {summary['week_end']}
═══════════════════════════════
🏪 {summary['business_name'] or 'جميع المتاجر'}

💰 إجمالي المبيعات: {summary['total_revenue']:,.2f} جنيه
   ({summary['order_count']} طلب)
   📊 متوسط يومي: {summary['average_daily_revenue']:,.2f} جنيه

💸 إجمالي المصروفات: {summary['total_expenses']:,.2f} جنيه
{expense_breakdown}

═══════════════════════════════
📈 صافي الربح الأسبوعي: {summary['net_profit']:,.2f} جنيه
═══════════════════════════════"""
    else:
        summary_text = f"""📊 Weekly Summary{sector_display}
{summary['week_start']} to {summary['week_end']}
═══════════════════════════════
🏪 {summary['business_name'] or 'All Stores'}

💰 Total Revenue: {summary['total_revenue']:,.2f} EGP
   ({summary['order_count']} orders)
   📊 Daily Average: {summary['average_daily_revenue']:,.2f} EGP

💸 Total Expenses: {summary['total_expenses']:,.2f} EGP
{expense_breakdown}

═══════════════════════════════
📈 Weekly Net Profit: {summary['net_profit']:,.2f} EGP
═══════════════════════════════"""
    
    return jsonify({
        "success": True,
        "summary": summary,
        "summary_text": summary_text
    })


@app.route("/api/accounting/categories", methods=["GET"])
def get_expense_categories():
    """Get list of expense categories."""
    return jsonify(EXPENSE_CATEGORIES)


# ============== INVENTORY API ROUTES (STAFF ONLY) ==============

@app.route("/api/inventory", methods=["GET"])
@accounting_only
def list_inventory_endpoint():
    """List inventory items with optional filters."""
    sector_id = request.args.get("sector_id", "").strip()
    query_text = request.args.get("q", "").strip()

    filters = {}
    if sector_id:
        filters["sector_id"] = sector_id

    if query_text:
        filters["$or"] = [
            {"name_en": {"$regex": query_text, "$options": "i"}},
            {"name_ar": {"$regex": query_text, "$options": "i"}},
            {"item_id": {"$regex": query_text, "$options": "i"}}
        ]

    items = list_inventory(filters)
    return jsonify({"success": True, "inventory": items})


@app.route("/api/inventory/seed", methods=["POST"])
@accounting_only
def seed_inventory_endpoint():
    """Seed inventory data from sector catalogs."""
    data = request.json or {}
    force = bool(data.get("force", False))
    default_stock = int(data.get("default_stock", 50))
    reorder_level = int(data.get("reorder_level", 10))

    result = seed_inventory_data(
        force=force,
        default_stock=default_stock,
        reorder_level=reorder_level
    )

    return jsonify({"success": True, **result})


@app.route("/api/inventory/update", methods=["POST"])
@accounting_only
def update_inventory_endpoint():
    """Update inventory item fields."""
    data = request.json or {}
    user = get_current_user()
    sector_id = data.get("sector_id", "").strip()
    item_id = data.get("item_id", "").strip()
    updates = data.get("updates", {})

    if not sector_id or not item_id:
        return jsonify({"error": "sector_id and item_id are required"}), 400

    allowed = {"name_en", "name_ar", "price", "unit", "stock_qty", "reorder_level", "is_active"}
    cleaned = {k: v for k, v in updates.items() if k in allowed}

    if "price" in cleaned:
        cleaned["price"] = float(cleaned["price"])
    
    # If stock_qty is being updated directly, use adjust_inventory_stock for proper logging
    if "stock_qty" in cleaned:
        from database import get_inventory_item as db_get_inventory_item
        current_item = db_get_inventory_item(sector_id, item_id)
        if current_item:
            old_qty = current_item.get("stock_qty", 0)
            new_qty = int(cleaned["stock_qty"])
            delta = new_qty - old_qty
            if delta != 0:
                adjust_inventory_stock(
                    sector_id=sector_id,
                    item_id=item_id,
                    delta=delta,
                    reason=f"Manual update via inventory/update endpoint",
                    user_id=user.get("user_id") if user else "",
                    username=user.get("username") if user else ""
                )
        del cleaned["stock_qty"]  # Remove from updates since we handled it
    
    if "reorder_level" in cleaned:
        cleaned["reorder_level"] = int(cleaned["reorder_level"])

    if not cleaned:
        # All updates were stock_qty changes, already handled
        item = db_get_inventory_item(sector_id, item_id) if 'db_get_inventory_item' in dir() else update_inventory_item(sector_id, item_id, {})
        if not item:
            return jsonify({"error": "Item not found"}), 404
        return jsonify({"success": True, "item": item})

    item = update_inventory_item(sector_id, item_id, cleaned)
    if not item:
        return jsonify({"error": "Item not found"}), 404

    return jsonify({"success": True, "item": item})


@app.route("/api/inventory/adjust", methods=["POST"])
@accounting_only
def adjust_inventory_endpoint():
    """Adjust inventory stock quantity."""
    data = request.json or {}
    sector_id = data.get("sector_id", "").strip()
    item_id = data.get("item_id", "").strip()
    delta = data.get("delta", None)
    new_qty = data.get("new_qty", None)
    reason = data.get("reason", "")

    if not sector_id or not item_id:
        return jsonify({"error": "sector_id and item_id are required"}), 400

    # If new_qty is provided, calculate delta
    if new_qty is not None:
        try:
            new_qty = int(new_qty)
        except (TypeError, ValueError):
            return jsonify({"error": "new_qty must be an integer"}), 400
        
        # Get current stock to calculate delta
        from database import get_inventory_item
        current_item = get_inventory_item(sector_id, item_id)
        if not current_item:
            return jsonify({"error": "Item not found"}), 404
        delta = new_qty - current_item.get("stock_qty", 0)
    elif delta is not None:
        try:
            delta = int(delta)
        except (TypeError, ValueError):
            return jsonify({"error": "delta must be an integer"}), 400
    else:
        return jsonify({"error": "Either delta or new_qty is required"}), 400

    user = get_current_user()
    item = adjust_inventory_stock(
        sector_id=sector_id,
        item_id=item_id,
        delta=delta,
        reason=reason,
        user_id=user.get("user_id") if user else "",
        username=user.get("username") if user else ""
    )

    if not item:
        return jsonify({"error": "Item not found"}), 404

    return jsonify({"success": True, "item": item})


@app.route("/api/inventory/low-stock", methods=["GET"])
@accounting_only
def low_stock_endpoint():
    """Get low-stock items."""
    sector_id = request.args.get("sector_id", "").strip()
    items = get_low_stock_items(sector_id=sector_id)
    return jsonify({"success": True, "items": items})


# ============== DASHBOARD API ROUTES ==============

@app.route("/api/accounting/dashboard-data", methods=["GET"])
@accounting_only
def get_dashboard_data():
    """Get data for dashboard charts."""
    user = get_current_user()
    business_name = user.get("business_name", "") if user else ""
    sector_id = request.args.get("sector_id", "")
    
    # Get last 7 days data
    labels = []
    revenues = []
    expenses = []
    
    for i in range(6, -1, -1):
        day = date.today() - timedelta(days=i)
        labels.append(day.strftime("%a"))
        summary = db_get_daily_summary(day.isoformat(), business_name, sector_id)
        revenues.append(summary.get("total_revenue", 0))
        expenses.append(summary.get("total_expenses", 0))
    
    # Get expense categories breakdown
    expense_categories = {"categories": [], "amounts": []}
    try:
        db = get_db()
        match_stage = {"date": {"$gte": (date.today() - timedelta(days=30)).isoformat()}}
        if business_name:
            match_stage["business_name"] = business_name
        pipeline = [
            {"$match": match_stage},
            {"$group": {"_id": "$category", "total": {"$sum": "$amount"}}},
            {"$sort": {"total": -1}},
            {"$limit": 6}
        ]
        results = list(db.expenses.aggregate(pipeline))
        for r in results:
            cat_name = r["_id"] or "Other"
            expense_categories["categories"].append(cat_name.capitalize())
            expense_categories["amounts"].append(r["total"])
    except Exception as e:
        logger.error(f"Error getting expense categories: {e}")
    
    # Get top products (from orders) - filter by sector if specified
    top_products = {"products": [], "sales": []}
    try:
        db = get_db()
        match_stage = {}
        if sector_id:
            match_stage["sector_id"] = sector_id
        if business_name:
            match_stage["business_name"] = business_name
        
        pipeline = []
        if match_stage:
            pipeline.append({"$match": match_stage})
        pipeline.extend([
            {"$unwind": "$items"},
            {"$group": {"_id": {"$ifNull": ["$items.product_name", {"$ifNull": ["$items.name_en", "$items.name"]}]}, "total": {"$sum": "$items.quantity"}}},
            {"$sort": {"total": -1}},
            {"$limit": 5}
        ])
        results = list(db.orders.aggregate(pipeline))
        for r in results:
            top_products["products"].append(r["_id"] or "Unknown")
            top_products["sales"].append(r["total"])
    except Exception as e:
        logger.error(f"Error getting top products: {e}")
    
    return jsonify({
        "success": True,
        "daily_data": {
            "labels": labels,
            "revenues": revenues,
            "expenses": expenses
        },
        "expense_categories": expense_categories,
        "top_products": top_products
    })


# ============== ADMIN/USER MANAGEMENT API ROUTES ==============

@app.route("/api/admin/users", methods=["GET"])
@accounting_only
def list_users():
    """List all users (accounting only)."""
    try:
        db = get_db()
        users = list(db.users.find({}, {"password": 0}))
        for u in users:
            u["_id"] = str(u["_id"])
        return jsonify({"success": True, "users": users})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/admin/users", methods=["POST"])
@accounting_only
def create_user_admin():
    """Create a new user (admin only)."""
    data = request.json
    username = data.get("username", "").strip()
    password = data.get("password", "")
    role = data.get("role", "customer")
    business_name = data.get("business_name", "")
    
    if not username or not password:
        return jsonify({"success": False, "error": "Username and password required"}), 400
    
    if len(password) < 6:
        return jsonify({"success": False, "error": "Password must be at least 6 characters"}), 400
    
    if role not in ["customer", "accounting"]:
        return jsonify({"success": False, "error": "Invalid role"}), 400
    
    result = create_user(
        username=username,
        password=password,
        role=role,
        business_name=business_name
    )
    
    if result["success"]:
        return jsonify({"success": True, "message": "User created successfully"})
    
    return jsonify(result), 400


@app.route("/api/admin/users/<user_id>", methods=["DELETE"])
@accounting_only
def delete_user(user_id):
    """Delete a user (admin only)."""
    try:
        from bson import ObjectId
        db = get_db()
        result = db.users.delete_one({"_id": ObjectId(user_id)})
        if result.deleted_count > 0:
            return jsonify({"success": True, "message": "User deleted"})
        return jsonify({"success": False, "error": "User not found"}), 404
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/admin/users/<user_id>/business", methods=["PUT"])
@accounting_only
def update_user_business(user_id):
    """Update user's business name (admin only)."""
    from database import update_user_business_name
    data = request.json
    business_name = data.get("business_name", "").strip()
    
    result = update_user_business_name(user_id, business_name)
    
    if result["success"]:
        return jsonify(result)
    return jsonify(result), 400


# ============== AI ANALYSIS API ROUTES ==============

@app.route("/api/ai/analyze", methods=["POST"])
@accounting_only
def ai_analyze():
    """Generate AI-powered business analysis."""
    data = request.json
    analysis_type = data.get("analysis_type", "daily")
    target_date = data.get("date", date.today().isoformat())
    
    user = get_current_user()
    business_name = user.get("business_name", "") if user else ""
    
    # Get financial data
    if analysis_type == "weekly":
        summary = db_get_weekly_summary(target_date, business_name)
    else:
        summary = db_get_daily_summary(target_date, business_name)
    
    # Get low stock items
    low_stock = get_low_stock_items()
    
    # Build context for AI
    context = f"""
Business Financial Data:
- Total Revenue: {summary.get('total_revenue', 0):.2f} EGP
- Total Expenses: {summary.get('total_expenses', 0):.2f} EGP
- Net Profit: {summary.get('net_profit', 0):.2f} EGP
- Order Count: {summary.get('order_count', 0)}
- Date/Period: {target_date}

Low Stock Items: {len(low_stock)} items below reorder level
"""
    
    try:
        openai_client = get_openai_client()
        if not openai_client:
            return jsonify({"success": False, "error": "OpenAI API not configured"}), 500
        
        if analysis_type == "suggestions":
            prompt = f"""Based on this business data, provide 5 actionable business suggestions to improve profitability:

{context}

Provide suggestions in both English and Arabic. Format nicely with emojis."""
        else:
            prompt = f"""Analyze this business financial data and provide insights:

{context}

Provide:
1. Performance summary
2. Key observations
3. Areas of concern
4. Recommendations

Respond in both English and Arabic. Use emojis for visual appeal."""
        
        response = openai_client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "You are a business analyst expert helping MSMEs understand their financial performance."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.7,
            max_tokens=1000
        )
        
        analysis = response.choices[0].message.content
        
        return jsonify({
            "success": True,
            "analysis": analysis
        })
        
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


# ============== EXPORT API ROUTES ==============

@app.route("/api/export/daily/csv", methods=["GET"])
@accounting_only
def export_daily_csv():
    """Export daily report as CSV."""
    from flask import Response
    import csv
    import io
    
    target_date = request.args.get("date", date.today().isoformat())
    user = get_current_user()
    business_name = user.get("business_name", "") if user else ""
    
    summary = db_get_daily_summary(target_date, business_name)
    
    # Get revenues and expenses for the day
    revenues = get_revenues_by_date(target_date, business_name)
    expenses = get_expenses_by_date(target_date, business_name)
    
    output = io.StringIO()
    writer = csv.writer(output)
    
    # Write header
    writer.writerow([f"Daily Financial Report - {target_date}"])
    writer.writerow([])
    writer.writerow(["Summary"])
    writer.writerow(["Total Revenue", summary.get("total_revenue", 0)])
    writer.writerow(["Total Expenses", summary.get("total_expenses", 0)])
    writer.writerow(["Net Profit", summary.get("net_profit", 0)])
    writer.writerow(["Order Count", summary.get("order_count", 0)])
    writer.writerow([])
    
    # Revenue details
    writer.writerow(["Revenue Details"])
    writer.writerow(["Order ID", "Amount", "Description"])
    for r in revenues:
        writer.writerow([r.get("order_id", ""), r.get("amount", 0), r.get("items_summary", "")])
    
    writer.writerow([])
    
    # Expense details
    writer.writerow(["Expense Details"])
    writer.writerow(["Category", "Amount", "Description"])
    for e in expenses:
        writer.writerow([e.get("category", ""), e.get("amount", 0), e.get("description", "")])
    
    output.seek(0)
    
    return Response(
        output.getvalue(),
        mimetype="text/csv",
        headers={"Content-Disposition": f"attachment;filename=daily_report_{target_date}.csv"}
    )


@app.route("/api/export/weekly/csv", methods=["GET"])
@accounting_only
def export_weekly_csv():
    """Export weekly report as CSV."""
    from flask import Response
    import csv
    import io
    
    week_start = request.args.get("weekStart", (date.today() - timedelta(days=date.today().weekday())).isoformat())
    user = get_current_user()
    business_name = user.get("business_name", "") if user else ""
    
    summary = db_get_weekly_summary(week_start, business_name)
    
    output = io.StringIO()
    writer = csv.writer(output)
    
    # Write header
    writer.writerow([f"Weekly Financial Report - {week_start}"])
    writer.writerow([])
    writer.writerow(["Summary"])
    writer.writerow(["Period", f"{summary.get('week_start', '')} to {summary.get('week_end', '')}"])
    writer.writerow(["Total Revenue", summary.get("total_revenue", 0)])
    writer.writerow(["Total Expenses", summary.get("total_expenses", 0)])
    writer.writerow(["Net Profit", summary.get("net_profit", 0)])
    writer.writerow(["Order Count", summary.get("order_count", 0)])
    writer.writerow(["Daily Average Revenue", summary.get("average_daily_revenue", 0)])
    writer.writerow([])
    
    # Top expense categories
    writer.writerow(["Top Expense Categories"])
    for cat, amt in summary.get("top_expense_categories", {}).items():
        writer.writerow([cat, amt])
    
    output.seek(0)
    
    return Response(
        output.getvalue(),
        mimetype="text/csv",
        headers={"Content-Disposition": f"attachment;filename=weekly_report_{week_start}.csv"}
    )


# ============== MARKETING HELPER API ==============

@app.route("/api/marketing/generate", methods=["POST"])
@accounting_only
def generate_marketing_content():
    """Generate AI-powered marketing content for MSMEs."""
    data = request.json
    content_type = data.get("content_type", "promotion")
    sector = data.get("sector", "general")
    season = data.get("season", "none")
    platform = data.get("platform", "facebook")
    language = data.get("language", "bilingual")
    additional_details = data.get("additional_details", "")
    
    # Get business name from current user's data
    user = get_current_user()
    business_name = user.get("business_name", "My Business") if user else "My Business"
    
    # Content type descriptions
    content_types = {
        "promotion": "promotional offer or discount announcement",
        "social_post": "engaging social media post",
        "product_launch": "new product announcement",
        "seasonal": "seasonal or holiday-themed marketing content",
        "engagement": "customer engagement post (review request, poll, or interaction)"
    }
    
    # Season descriptions
    seasons = {
        "general": "",
        "none": "",
        "ramadan": "Ramadan season - include Ramadan greetings and spirit",
        "eid": "Eid celebration - include Eid Mubarak wishes",
        "summer": "Summer season - energetic, refreshing vibes",
        "back_to_school": "Back to school season",
        "black_friday": "Black Friday sales event",
        "new_year": "New Year celebration and offers",
        "valentines": "Valentine's Day",
        "mothers_day": "Mother's Day celebration"
    }
    
    # Platform guidelines
    platforms = {
        "general": "General social media post",
        "facebook": "Facebook post format - can be longer, include call-to-action",
        "instagram": "Instagram post - visual focus, use emojis, include hashtags",
        "whatsapp": "WhatsApp broadcast message - personal, direct, concise",
        "twitter": "Twitter/X post - concise (under 280 chars if possible), impactful"
    }
    
    # Language preference
    lang_instructions = {
        "bilingual": "Provide the content in BOTH Arabic AND English (Arabic first, then English translation)",
        "arabic": "Provide the content in Arabic only",
        "english": "Provide the content in English only"
    }
    
    # Build the marketing prompt
    season_context = f"\nSeasonal Context: {seasons.get(season, '')}" if season and season not in ["none", "general"] else ""
    
    marketing_prompt = f"""You are an expert marketing content creator for small and medium businesses (MSMEs) in the Middle East and Arab region.

Create a {content_types.get(content_type, 'promotional')} for the following business:

📌 **Business Name:** {business_name}
📌 **Business Sector:** {sector}
📌 **Target Platform:** {platforms.get(platform, 'social media')}
📌 **Content Type:** {content_type.replace('-', ' ').title()}{season_context}

{f'📌 **Additional Details:** {additional_details}' if additional_details else ''}

**Language Requirement:** {lang_instructions.get(language, lang_instructions['bilingual'])}

**Guidelines:**
1. Make it attention-grabbing and engaging
2. Include relevant emojis for visual appeal
3. Add a clear call-to-action (CTA)
4. Keep it authentic and relatable to the local market
5. If promotional, suggest discount percentage or offer type
6. Include relevant hashtags if platform supports them
7. Make it shareable and memorable

**Output Format:**
📢 **Main Content:**
[The actual marketing content ready to post]

💡 **Suggested Visuals:**
[Brief description of what image/video would work best]

🎯 **Best Posting Tips:**
[When to post, how to boost engagement]

📣 **Alternative Version:**
[A shorter/different version of the same message]"""

    try:
        openai_client = get_openai_client()
        if not openai_client:
            return jsonify({"success": False, "error": "OpenAI API not configured"}), 500
        
        response = openai_client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {
                    "role": "system", 
                    "content": """You are a creative marketing expert specializing in helping Middle Eastern and Arab MSMEs 
create compelling, culturally-appropriate marketing content. You understand local business culture, seasonal events 
(Ramadan, Eid, etc.), and what resonates with Arab consumers. Your content is always professional, engaging, and 
designed to drive real business results."""
                },
                {"role": "user", "content": marketing_prompt}
            ],
            temperature=0.8,
            max_tokens=1500
        )
        
        content = response.choices[0].message.content
        
        return jsonify({
            "success": True,
            "content": content
        })
        
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


# ============== MAIN ==============

if __name__ == "__main__":
    # Initialize database
    init_db()
    
    # Startup banner (intentional user-facing output)
    print("\n" + "=" * 55)
    print("  DIGITAL EMPLOYEE - MSME Assistant")
    print("  ✓ Step 1: Sales Chat Bot")
    print("  ✓ Step 2: Accounting Clerk")
    print("  ✓ MongoDB Database")
    print("  ✓ Role-Based Authentication")
    print("=" * 55)
    print(f"\n  Loaded {len(SECTORS)} sectors")
    print("\n  Default Users:")
    print("    📦 Customer: customer / customer123")
    print("    📊 Accounting: admin / admin123")
    print("\n  Starting server at http://localhost:5000")
    print("=" * 55 + "\n")
    
    app.run(debug=True, port=5000, use_reloader=False)
