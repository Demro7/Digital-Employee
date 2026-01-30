# Dialogue Flow - Chat Agent (Step 1)

## State Machine

```
┌─────────────┐
│   START     │
└──────┬──────┘
       │ User sends first message
       ▼
┌─────────────┐
│  GREETING   │──────────────────────────────┐
└──────┬──────┘                              │
       │ Detect language                     │
       ▼                                     │
┌─────────────┐      FAQ question?           │
│  BROWSING   │◄─────────────────────────────┤
└──────┬──────┘                              │
       │ User wants to order                 │
       ▼                                     │
┌─────────────┐                              │
│  ORDERING   │ ◄── Add more items ──┐       │
└──────┬──────┘                      │       │
       │ Items selected              │       │
       ▼                             │       │
┌─────────────┐                      │       │
│ COLLECT_QTY │──────────────────────┘       │
└──────┬──────┘                              │
       │ Quantity provided                   │
       ▼                                     │
┌─────────────┐                              │
│COLLECT_PHONE│                              │
└──────┬──────┘                              │
       │ Phone provided                      │
       ▼                                     │
┌─────────────┐                              │
│COLLECT_ADDR │                              │
└──────┬──────┘                              │
       │ Address provided                    │
       ▼                                     │
┌─────────────┐      User says NO            │
│ CONFIRMING  │──────────────────────────────┘
└──────┬──────┘
       │ User says YES
       ▼
┌─────────────┐
│  CONFIRMED  │
└─────────────┘
```

## States Description

### 1. GREETING

- **Trigger**: First message from user
- **Actions**:
  - Detect language (Arabic/English)
  - Send welcome message in detected language
  - Offer help
- **Transitions**: → BROWSING

### 2. BROWSING

- **Trigger**: User exploring products/asking questions
- **Actions**:
  - Show catalog on request
  - Answer FAQs
  - Suggest products
- **Transitions**:
  - FAQ → Stay in BROWSING
  - "I want to order" → ORDERING

### 3. ORDERING

- **Trigger**: User expresses intent to order
- **Actions**:
  - Ask which items
  - Show options if unclear
- **Transitions**: → COLLECT_QTY

### 4. COLLECT_QTY

- **Trigger**: Item selected
- **Actions**:
  - Ask for quantity
  - Ask for size (if applicable)
- **Transitions**:
  - More items → ORDERING
  - Done → COLLECT_PHONE

### 5. COLLECT_PHONE

- **Trigger**: All items collected
- **Actions**:
  - Ask for phone number
  - Validate Egyptian format (01XXXXXXXXX)
- **Transitions**: → COLLECT_ADDR

### 6. COLLECT_ADDR

- **Trigger**: Phone collected
- **Actions**:
  - Ask for delivery address
- **Transitions**: → CONFIRMING

### 7. CONFIRMING

- **Trigger**: All info collected
- **Actions**:
  - Display order summary
  - Show total price
  - Ask for YES/NO confirmation
- **Transitions**:
  - YES → CONFIRMED
  - NO → BROWSING (reset order)

### 8. CONFIRMED

- **Trigger**: User confirms order
- **Actions**:
  - Generate order ID (ORD-XXXXX)
  - Save order
  - Send confirmation message
  - Provide estimated time
- **End State**

---

## Example Conversations

### Example 1: Fashion Retail (English)

```
User: Hi
Bot: Welcome to Fashion Store! 👗 How can I help you today?

User: Show me what you have
Bot: Here's our catalog:
     • T-Shirt - 200 EGP
     • Hoodie - 450 EGP
     • Cap - 120 EGP
     • Jeans - 550 EGP
     • Sneakers - 800 EGP

     What would you like to order?

User: I want 2 hoodies and a cap
Bot: Great choice!
     • 2x Hoodie = 900 EGP
     • 1x Cap = 120 EGP

     What size for the Hoodies? (S, M, L, XL)

User: Large
Bot: Got it! Anything else?

User: No that's all
Bot: Please share your phone number:

User: 01012345678
Bot: What's your delivery address?

User: 15 Ahmed St, Maadi, Cairo
Bot: Please confirm your order:
     ─────────────────
     • Hoodie (L) x2 = 900 EGP
     • Cap x1 = 120 EGP
     ─────────────────
     Total: 1020 EGP
     📞 01012345678
     📍 15 Ahmed St, Maadi, Cairo

     Reply YES to confirm or NO to cancel.

User: YES
Bot: ✅ Order confirmed! Order #ORD-A3B2C will be shipped within 2-3 days. Thank you!
```

### Example 2: Restaurant (Arabic)

```
User: السلام عليكم
Bot: وعليكم السلام! أهلاً بك في مطعم الشيف! 🍽️ كيف أقدر أساعدك؟

User: عندكم إيه؟
Bot: القائمة:
     • فراخ مشوية - 120 جنيه
     • برجر لحمة - 85 جنيه
     • سلطة سيزر - 65 جنيه
     • عصير طازج - 35 جنيه
     • قهوة - 25 جنيه

     تحب تطلب إيه؟

User: فراخ مشوية وعصير
Bot: تمام! كام طلب فراخ مشوية؟

User: 2
Bot: ممتاز!
     • 2x فراخ مشوية = 240 جنيه
     • 1x عصير طازج = 35 جنيه

     حاجة تانية؟

User: لا خلاص
Bot: ممكن رقم تليفونك؟

User: 01098765432
Bot: عنوان التوصيل إيه؟

User: 20 شارع التحرير، الدقي
Bot: تأكيد الطلب:
     ─────────────────
     • فراخ مشوية x2 = 240 جنيه
     • عصير طازج x1 = 35 جنيه
     ─────────────────
     الإجمالي: 275 جنيه
     📞 01098765432
     📍 20 شارع التحرير، الدقي

     رد بـ نعم للتأكيد أو لا للإلغاء.

User: نعم
Bot: ✅ تم تأكيد الطلب! طلبك رقم #ORD-X7Y8Z هيوصل خلال 30-45 دقيقة. شكراً!
```

---

## Order Data Schema (JSON)

```json
{
  "order_id": "ORD-A3B2C",
  "sector_id": "fashion_retail",
  "business_name": "Fashion Store",
  "items": [
    {
      "product_id": "F002",
      "product_name": "Hoodie",
      "quantity": 2,
      "unit_price": 450,
      "size": "L",
      "subtotal": 900
    },
    {
      "product_id": "F003",
      "product_name": "Cap",
      "quantity": 1,
      "unit_price": 120,
      "size": "Free",
      "subtotal": 120
    }
  ],
  "customer_phone": "01012345678",
  "customer_address": "15 Ahmed St, Maadi, Cairo",
  "total": 1020,
  "status": "confirmed",
  "created_at": "2026-01-27T14:30:00Z"
}
```

---

## FAQ Handling

The agent matches user questions against keywords in the sector config:

| Keywords         | Response Type   |
| ---------------- | --------------- |
| delivery, توصيل  | Delivery info   |
| price, سعر       | Pricing info    |
| payment, دفع     | Payment methods |
| time, وقت, hours | Working hours   |
| return, استرجاع  | Return policy   |
| warranty, ضمان   | Warranty info   |

---

## Error Handling

- Invalid phone → Ask again with format hint
- Unknown product → Suggest from catalog
- Unclear intent → Ask clarifying question
- API error → Apologize and ask to retry
