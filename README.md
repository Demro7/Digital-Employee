
# Digital Employee - MSME Chat Agent

## 📸 Screenshots

<p align="center">
    <img src="screenshots/Screenshot%202026-01-28%20115930.png" alt="Chat UI" width="600" />
    <br>
    <img src="screenshots/Screenshot%202026-01-28%20120004.png" alt="Order Example" width="600" />
    <br>
    <img src="screenshots/Screenshot%202026-01-28%20120118.png" alt="Product Catalog" width="600" />
</p>

## 🎯 Vision

A unified digital employee for Micro, Small, and Medium Enterprises (MSMEs) that automates sales through chat, supporting Egypt's Vision 2030 for economic development.

## 📁 Project Structure

```
digital_employee/
├── app.py                    # Main Flask application
├── requirements.txt          # Python dependencies
├── .env.example             # Environment variables template
├── .gitignore               # Git ignore rules
├── config/
│   └── sectors/             # Sector configurations
│       ├── restaurant.json
│       ├── fashion_retail.json
│       ├── electronics.json
│       ├── pharmacy.json
│       ├── grocery.json
│       ├── home_services.json
│       ├── education.json
│       ├── clinic.json
│       ├── travel.json
│       └── repair_workshop.json
├── models/
│   ├── __init__.py
│   └── order.py             # Order data models
├── templates/
│   └── index.html           # Chat UI
└── docs/
    └── dialogue_flow.md     # Conversation flow documentation
```

## 🚀 Quick Start

### 1. Setup Environment

```bash
cd digital_employee
python -m venv venv
venv\Scripts\activate  # Windows
pip install -r requirements.txt
```

### 2. Configure API Key

```bash
copy .env.example .env
# Edit .env and add your OpenAI API key
```

### 3. Run the Application

```bash
python app.py
```

### 4. Open Browser

Navigate to: http://localhost:5000

## 🏭 Supported Sectors

| Sector            | Arabic       | Icon |
| ----------------- | ------------ | ---- |
| Restaurant & Cafe | مطعم وكافيه  | 🍽️   |
| Fashion Retail    | ملابس وأزياء | 👗   |
| Electronics       | إلكترونيات   | 📱   |
| Pharmacy          | صيدلية       | 💊   |
| Grocery           | بقالة        | 🛒   |
| Home Services     | خدمات منزلية | 🔧   |
| Education         | تعليم وتدريب | 📚   |
| Clinic & Beauty   | عيادة وتجميل | 💆   |
| Travel & Tourism  | سياحة وسفر   | ✈️   |
| Repair Workshop   | ورشة صيانة   | 🔧   |

## 🔄 Current Features (Step 1 - MVP)

- ✅ Multi-sector support with customizable configs
- ✅ Bilingual support (Arabic/English) with auto-detection
- ✅ Product catalog display
- ✅ FAQ handling
- ✅ Order capture (items, quantity, phone, address)
- ✅ Order confirmation flow
- ✅ Web-based chat interface

## 📋 Roadmap

- **Step 1 (Current)**: Chat-only agent for sales ✅
- **Step 2**: Link orders to simple accounting
- **Step 3**: Inventory updates + low-stock alerts
- **Step 4**: Marketing suggestions & campaigns dashboard

## 🔐 Security Notes

- NEVER commit `.env` file with API keys
- API key should only be used server-side
- Regenerate any exposed API keys immediately

## 🇪🇬 Vision 2030 Alignment

This project supports Goal 3 (Integrated & Sustainable Economic Development) by:

- Digitizing MSME operations
- Reducing operational costs
- Formalizing informal economy through digital records
- Enabling export potential through standardized systems

## 📝 License

MIT License - Feel free to use and modify for the competition!
