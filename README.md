# 💎 FinMinimal — Minimalistic Personal Finance & Credit Card Portal

A high-performance, privacy-first, minimalistic personal finance web application built in **Python (FastAPI & SQLAlchemy)** with a modern **Apple Wallet & iOS 18 glassmorphic UI**.

Designed from the ground up to be **mobile-friendly**, **PWA-enabled (installable on iPhone home screen)**, and **hardened against cyber attacks (OWASP Top 10 compliant)**.

---

## 🌟 Key Features

### 1. 🔐 Enterprise-Grade Security & Authentication
- **Password Protection**: Passwords are never stored in plain text. Hashed with **salted `bcrypt` (12 rounds)**.
- **Session & JWT Security**: HttpOnly, SameSite=Lax, and configurable Secure flags.
- **OWASP Hardening**:
  - **SQL Injection Prevention**: 100% parameterized queries via SQLAlchemy 2.0 ORM.
  - **CSRF Defense**: Cryptographic, time-limited CSRF tokens required on all mutating actions.
  - **XSS Sanitization**: Strict HTML entity stripping and Jinja2 auto-escaping.
  - **Brute-Force & DDoS Mitigation**: SlowAPI rate limiters on login, registration, and API routes.
  - **Security Headers**: HSTS, CSP (Content Security Policy), `X-Frame-Options: DENY`, `X-Content-Type-Options: nosniff`, and Permissions-Policy.
- **Zero Secrets in Code**: 100% environment-driven configuration via `.env`.

---

### 2. 💸 Expense & Income Management
- **Instant Lodging**: Log expenses or incomes with Amount, Date (defaults to today or simulated date), Category, Payment Source (Bank Account or Credit Card), Tag, and Remarks.
- **Dynamic Balance Recalculation**: Automatically adjusts bank balance or credit card limit upon transaction creation, edit, or deletion.
- **Category Manager**: Create, edit, and delete categories with intuitive emojis/icons (`🍔 Food`, `⛽ Fuel`, `🏠 Rent`, `🛒 Grocery`, `💡 Bills`, `💵 Salary`, etc.) and brand color pickers.

---

### 3. ✈️ Trips & Vacation Budget Framework
- **Seamless Integration**: Create trips with budget targets and destinations.
- **No Duplicate Logging**: When logging an everyday expense or vacation swipe, simply tag the trip. It automatically updates the account balance **and** aggregates into the trip budget burn-down!
- **Trip Detail Analytics**: Category breakdown, budget progress bar, remaining budget tracker, and full trip itinerary.

---

### 4. 💳 Indian Bank Accounts & Credit Cards (Apple Wallet Experience)
- **Major Indian Banks Preset**: HDFC, State Bank of India (SBI), ICICI, Axis Bank, Kotak Mahindra, PNB, Bank of Baroda, IndusInd, IDFC FIRST, Canara, Union, Yes Bank, Federal Bank, Standard Chartered, HSBC, RBL + Custom Bank option.
- **Major Indian Credit Cards Preset**:
  - HDFC Infinia Metal, Regalia Gold, Millennia, Tata Neu Infinity
  - SBI SimplyCLICK, SBI Elite, SBI Cashback
  - ICICI Amazon Pay, ICICI Coral, ICICI Emeralde
  - Axis Magnus, Axis Flipkart, Axis Atlas
  - Kotak White, Amex Platinum Travel, OneCard Metal, and more!
- **Card Artwork & Styling**: Online credit card artwork references, luxury CSS gradients, and EMV chip previews.
- **Limit & Utilization Meters**: Track total limit, opening balance, and live available credit.

---

### 5. 🔔 Credit Card Billing & Payment Due Notifications
- **Automated Due Date Engine**: Computes billing cycle date and payment due date for each card.
- **Urgency Alerts**: Highlights cards *Due Today*, *Due in X Days*, or *Overdue* with warning badges and in-app alerts.
- **Native Web Push & Notification Center**: Web Push support and in-app notifications hub.

---

### 6. 📊 Dashboard Analytics & Interactive Charts
- **Financial KPIs**: Total Incomes, Total Expenses, Net Savings, Savings Rate (%), Liquid Bank Balances, and Total Credit Card Outstanding.
- **Interactive Chart.js Visualizations**:
  - Expense by Category (Interactive Doughnut Chart).
  - Cashflow & Daily Spending Trend (Comparison Bar/Area Chart).
- **Time Filter Controls**: Filter by *This Month*, *Last Month*, *Last 30 Days*, *This Year*, or *Custom Date Range* with instant dynamic chart updates without page reloads.

---

### 7. 📑 Statement Exporter (Excel & PDF)
- **Excel Export (`.xlsx`)**: Custom-formatted spreadsheets with formulas, colored positive/negative values, and auto-fitted columns via `openpyxl`.
- **PDF Export (`.pdf`)**: Formatted statement with summary metrics table, category breakdown, and zebra-striped transaction log via `reportlab`.

---

### 8. 🛠️ Admin Module & Date Simulator
- **Date Simulation Override**: Administrators can set a simulated system date to test billing cycles, due date reminders, and backdated financial reports on request, with one-click reset to real server time.
- **User Management & Audit Logs**: Inspect system-wide transactions, user statuses, and security audit logs.

---

### 9. 📱 Mobile & iPhone PWA ("Add to Home Screen")
- **iOS 18 Native Aesthetic**: Apple San Francisco typography, bottom navigation bar, safe-area-inset padding for iPhone Dynamic Island and Home Indicator.
- **Progressive Web App**: Full `manifest.json`, `apple-touch-icon`, and `sw.js` (Service Worker) for offline shell caching and installability.

---

## 🚀 Quick Start Guide

### Prerequisites
- Python 3.10+
- Git

### 1. Clone & Setup Environment
```bash
git clone <your-github-repo-url>
cd "Personal Finance"

# Create and activate virtual environment (optional)
python -m venv venv
# On Windows:
venv\Scripts\activate
# On macOS/Linux:
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### 2. Configure Environment Variables
Copy `.env.example` to `.env` and set your secure keys:
```bash
cp .env.example .env
```

### 3. Run the Application
```bash
python run.py
```
Open your browser at: **[http://localhost:8000](http://localhost:8000)**

---

## 🧪 Running Automated Tests

Run the full pytest test suite (covers registration, password hashing, bank & card life cycles, trip expense framework, statement exporters, admin date override, security headers):
```bash
python -m pytest tests/test_finance_app.py -v
```

---

## 🛡️ Security Architecture

| Threat / Vulnerability | Mitigation Strategy |
|---|---|
| **SQL Injection** | SQLAlchemy ORM with parameterized queries across all database operations. |
| **XSS (Cross-Site Scripting)** | Jinja2 autoescaping + text sanitization stripping dangerous tags. |
| **CSRF (Cross-Site Request Forgery)** | Timed cryptographic CSRF tokens on all POST/PUT/DELETE forms & requests. |
| **Brute-Force & DDoS** | SlowAPI rate limiters configured on authentication and general endpoints. |
| **Clickjacking** | `X-Frame-Options: DENY` header injected on all HTTP responses. |
| **MIME Sniffing** | `X-Content-Type-Options: nosniff` header. |
| **Data Leakage** | `.gitignore` strictly ignores `.env`, `*.db`, `*.sqlite3`, and `*.log` files. |

---

## 📦 Project Structure

```
├── .env.example              # Configuration template (no sensitive data)
├── .gitignore                # Git ignore rules for secrets and DB
├── requirements.txt          # Python dependencies
├── run.py                    # Application runner
├── app/
│   ├── config.py             # Pydantic Settings & environment loader
│   ├── database.py           # SQLAlchemy database session & engine
│   ├── dependencies.py       # Auth dependencies, admin guard & CSRF verification
│   ├── main.py               # FastAPI entry point & security middleware
│   ├── models/               # SQLAlchemy ORM models (User, BankAccount, CreditCard, etc.)
│   ├── schemas/              # Pydantic validation schemas
│   ├── core/
│   │   ├── security.py       # Bcrypt, JWT, CSRF, input sanitization & security headers
│   │   ├── rate_limiter.py   # SlowAPI rate limiting configuration
│   │   ├── date_provider.py  # Centralized live & admin-simulated date provider
│   │   ├── reminder_engine.py# Credit card billing & payment due date calculator
│   │   ├── presets.py        # Indian Banks, Credit Cards & Category presets
│   │   ├── exporter_excel.py # OpenPyXL Excel statement generator
│   │   └── exporter_pdf.py   # ReportLab PDF statement generator
│   ├── routers/              # Route handlers (auth, dashboard, transactions, cards, trips, admin, pwa)
│   ├── templates/            # Jinja2 HTML templates (iOS aesthetic)
│   └── static/               # PWA Service worker, styles, icons & client JS
└── tests/
    └── test_finance_app.py   # Automated unit and integration test suite
```

---

## 📄 License
MIT License. Free for personal and commercial use.
