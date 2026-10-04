"""
Presets for Major Indian Banks, Credit Cards with Online Visual References, and Default Financial Categories.
"""

INDIAN_BANKS = [
    {
        "name": "HDFC Bank",
        "short_name": "HDFC",
        "color": "#004c8f",
        "logo_url": "https://assets.stickpng.com/images/627cc51b1b2e57dc5ef5e412.png",
        "icon": "building-library"
    },
    {
        "name": "State Bank of India (SBI)",
        "short_name": "SBI",
        "color": "#0083ca",
        "logo_url": "https://assets.stickpng.com/images/627cc52b1b2e57dc5ef5e413.png",
        "icon": "building-library"
    },
    {
        "name": "ICICI Bank",
        "short_name": "ICICI",
        "color": "#b82c20",
        "logo_url": "https://assets.stickpng.com/images/627cc4c81b2e57dc5ef5e40e.png",
        "icon": "building-library"
    },
    {
        "name": "Axis Bank",
        "short_name": "AXIS",
        "color": "#97144d",
        "logo_url": "https://assets.stickpng.com/images/627cc5011b2e57dc5ef5e410.png",
        "icon": "building-library"
    },
    {
        "name": "Kotak Mahindra Bank",
        "short_name": "KOTAK",
        "color": "#ed1c24",
        "logo_url": "https://upload.wikimedia.org/wikipedia/commons/thumb/3/39/Kotak_Mahindra_Group_logo.svg/320px-Kotak_Mahindra_Group_logo.svg.png",
        "icon": "building-library"
    },
    {
        "name": "Punjab National Bank (PNB)",
        "short_name": "PNB",
        "color": "#a21d22",
        "logo_url": "https://upload.wikimedia.org/wikipedia/commons/thumb/c/cb/Punjab_National_Bank_Logo.svg/320px-Punjab_National_Bank_Logo.svg.png",
        "icon": "building-library"
    },
    {
        "name": "Bank of Baroda",
        "short_name": "BOB",
        "color": "#f26522",
        "logo_url": "https://upload.wikimedia.org/wikipedia/commons/thumb/8/87/Bank_of_Baroda_logo.svg/320px-Bank_of_Baroda_logo.svg.png",
        "icon": "building-library"
    },
    {
        "name": "IndusInd Bank",
        "short_name": "INDUS",
        "color": "#7d1424",
        "logo_url": "https://upload.wikimedia.org/wikipedia/commons/thumb/3/30/IndusInd_Bank_Logo.svg/320px-IndusInd_Bank_Logo.svg.png",
        "icon": "building-library"
    },
    {
        "name": "IDFC FIRST Bank",
        "short_name": "IDFC",
        "color": "#9d1d27",
        "logo_url": "https://upload.wikimedia.org/wikipedia/commons/thumb/8/80/IDFC_FIRST_Bank_logo.svg/320px-IDFC_FIRST_Bank_logo.svg.png",
        "icon": "building-library"
    },
    {
        "name": "Canara Bank",
        "short_name": "CANARA",
        "color": "#0091df",
        "logo_url": "https://upload.wikimedia.org/wikipedia/commons/thumb/9/90/Canara_Bank_Logo.svg/320px-Canara_Bank_Logo.svg.png",
        "icon": "building-library"
    },
    {
        "name": "Yes Bank",
        "short_name": "YES",
        "color": "#003874",
        "logo_url": "https://upload.wikimedia.org/wikipedia/commons/thumb/9/93/Yes_Bank_Logo.svg/320px-Yes_Bank_Logo.svg.png",
        "icon": "building-library"
    },
    {
        "name": "Federal Bank",
        "short_name": "FEDERAL",
        "color": "#003366",
        "logo_url": "https://upload.wikimedia.org/wikipedia/commons/thumb/b/be/Federal_Bank_Logo.svg/320px-Federal_Bank_Logo.svg.png",
        "icon": "building-library"
    },
    {
        "name": "Standard Chartered Bank",
        "short_name": "SCB",
        "color": "#009944",
        "logo_url": "https://upload.wikimedia.org/wikipedia/commons/thumb/0/0c/Standard_Chartered.svg/320px-Standard_Chartered.svg.png",
        "icon": "building-library"
    },
    {
        "name": "HSBC Bank India",
        "short_name": "HSBC",
        "color": "#db0011",
        "logo_url": "https://upload.wikimedia.org/wikipedia/commons/thumb/a/aa/HSBC_logo_%282018%29.svg/320px-HSBC_logo_%282018%29.svg.png",
        "icon": "building-library"
    }
]

INDIAN_CREDIT_CARDS = [
    {
        "bank_name": "HDFC Bank",
        "card_name": "HDFC Infinia Metal Edition",
        "card_network": "Visa",
        "image_url": "https://www.hdfcbank.com/content/api/contentstream-id/723fb80a-2dde-42a3-9793-7ae1be57c87f/c6ca0039-4eb1-4545-9856-787be0ff0977/Personal/Pay/Cards/Credit%20Cards/Infinia-Credit-Card/Infinia_Metal_Front.png",
        "gradient": "linear-gradient(135deg, #111827 0%, #1f2937 50%, #374151 100%)",
        "accent_color": "#D4AF37",
        "default_limit": 500000
    },
    {
        "bank_name": "HDFC Bank",
        "card_name": "HDFC Regalia Gold",
        "card_network": "Visa",
        "image_url": "https://www.hdfcbank.com/content/api/contentstream-id/723fb80a-2dde-42a3-9793-7ae1be57c87f/f0ef8cfa-555e-4bb5-8df6-905bbab3a228/Personal/Pay/Cards/Credit%20Cards/Regalia-Gold-Credit-Card/Regalia-Gold-card.png",
        "gradient": "linear-gradient(135deg, #1e3a8a 0%, #172554 60%, #0f172a 100%)",
        "accent_color": "#FBBF24",
        "default_limit": 300000
    },
    {
        "bank_name": "HDFC Bank",
        "card_name": "HDFC Millennia",
        "card_network": "Mastercard",
        "image_url": "https://www.hdfcbank.com/content/api/contentstream-id/723fb80a-2dde-42a3-9793-7ae1be57c87f/54fe04db-9ee9-4c28-bb86-d24ebfbe7248/Personal/Pay/Cards/Credit%20Cards/Millennia-Credit-Card/Millennia-Credit-Card.png",
        "gradient": "linear-gradient(135deg, #0284c7 0%, #0369a1 50%, #075985 100%)",
        "accent_color": "#38BDF8",
        "default_limit": 150000
    },
    {
        "bank_name": "HDFC Bank",
        "card_name": "Tata Neu Infinity HDFC",
        "card_network": "RuPay",
        "image_url": "https://www.hdfcbank.com/content/api/contentstream-id/723fb80a-2dde-42a3-9793-7ae1be57c87f/dc39c05c-59e5-4702-8699-2708b7e28b8f/Personal/Pay/Cards/Credit%20Cards/Tata-Neu-Infinity-HDFC-Bank-Credit-Card/Tata-Neu-Infinity-Card.png",
        "gradient": "linear-gradient(135deg, #4c1d95 0%, #2e1065 60%, #1e1b4b 100%)",
        "accent_color": "#C084FC",
        "default_limit": 200000
    },
    {
        "bank_name": "ICICI Bank",
        "card_name": "Amazon Pay ICICI Card",
        "card_network": "Visa",
        "image_url": "https://www.icicibank.com/content/dam/icicibank/india/managed-assets/images/personal-banking/cards/credit-cards/amazon-pay/amazon-pay-card-m.png",
        "gradient": "linear-gradient(135deg, #334155 0%, #1e293b 50%, #0f172a 100%)",
        "accent_color": "#FF9900",
        "default_limit": 250000
    },
    {
        "bank_name": "ICICI Bank",
        "card_name": "ICICI Coral Credit Card",
        "card_network": "Visa",
        "image_url": "https://www.icicibank.com/content/dam/icicibank/india/managed-assets/images/personal-banking/cards/credit-cards/coral-credit-card/coral-credit-card-m.png",
        "gradient": "linear-gradient(135deg, #e11d48 0%, #be123c 60%, #881337 100%)",
        "accent_color": "#FDA4AF",
        "default_limit": 150000
    },
    {
        "bank_name": "ICICI Bank",
        "card_name": "ICICI Emeralde Metal Card",
        "card_network": "Mastercard",
        "image_url": "https://www.icicibank.com/content/dam/icicibank/india/managed-assets/images/personal-banking/cards/credit-cards/emeralde/emeralde-card-m.png",
        "gradient": "linear-gradient(135deg, #064e3b 0%, #022c22 60%, #0f172a 100%)",
        "accent_color": "#34D399",
        "default_limit": 500000
    },
    {
        "bank_name": "State Bank of India (SBI)",
        "card_name": "SBI Cashback Card",
        "card_network": "Visa",
        "image_url": "https://www.sbicard.com/sbi-card-en/assets/media/images/personal/credit-cards/rewards/cashback-sbi-card/card-face.png",
        "gradient": "linear-gradient(135deg, #0284c7 0%, #0f766e 60%, #064e3b 100%)",
        "accent_color": "#2DD4BF",
        "default_limit": 180000
    },
    {
        "bank_name": "State Bank of India (SBI)",
        "card_name": "SBI SimplyCLICK",
        "card_network": "Visa",
        "image_url": "https://www.sbicard.com/sbi-card-en/assets/media/images/personal/credit-cards/shopping/simplyclick-sbi-card/card-face.png",
        "gradient": "linear-gradient(135deg, #2563eb 0%, #1d4ed8 50%, #1e40af 100%)",
        "accent_color": "#60A5FA",
        "default_limit": 100000
    },
    {
        "bank_name": "State Bank of India (SBI)",
        "card_name": "SBI Card ELITE",
        "card_network": "Visa",
        "image_url": "https://www.sbicard.com/sbi-card-en/assets/media/images/personal/credit-cards/lifestyle/sbi-card-elite/card-face.png",
        "gradient": "linear-gradient(135deg, #0f172a 0%, #1e1b4b 60%, #311042 100%)",
        "accent_color": "#E2E8F0",
        "default_limit": 350000
    },
    {
        "bank_name": "Axis Bank",
        "card_name": "Axis Magnus Credit Card",
        "card_network": "Mastercard",
        "image_url": "https://www.axisbank.com/images/default-source/magnus-credit-card/magnus_card.png",
        "gradient": "linear-gradient(135deg, #831843 0%, #500724 60%, #0f172a 100%)",
        "accent_color": "#F472B6",
        "default_limit": 500000
    },
    {
        "bank_name": "Axis Bank",
        "card_name": "Flipkart Axis Bank Card",
        "card_network": "Visa",
        "image_url": "https://www.axisbank.com/images/default-source/flipkart-credit-card/flipkart-card.png",
        "gradient": "linear-gradient(135deg, #0284c7 0%, #0369a1 60%, #082f49 100%)",
        "accent_color": "#FACC15",
        "default_limit": 150000
    },
    {
        "bank_name": "Axis Bank",
        "card_name": "Axis Atlas Credit Card",
        "card_network": "Visa",
        "image_url": "https://www.axisbank.com/images/default-source/atlas-credit-card/atlas-card.png",
        "gradient": "linear-gradient(135deg, #78350f 0%, #451a03 60%, #1c1917 100%)",
        "accent_color": "#FBBF24",
        "default_limit": 300000
    },
    {
        "bank_name": "Kotak Mahindra Bank",
        "card_name": "Kotak White Credit Card",
        "card_network": "Visa",
        "image_url": "https://www.kotak.com/content/dam/Kotak/product_card_images/white-credit-card.png",
        "gradient": "linear-gradient(135deg, #475569 0%, #334155 50%, #1e293b 100%)",
        "accent_color": "#FFFFFF",
        "default_limit": 250000
    },
    {
        "bank_name": "American Express",
        "card_name": "Amex Platinum Travel Card",
        "card_network": "Amex",
        "image_url": "https://icm.aexp-static.com/Internet/international/in/personal/credit-cards/platinum-travel-card/images/card-art.png",
        "gradient": "linear-gradient(135deg, #64748b 0%, #475569 50%, #334155 100%)",
        "accent_color": "#E2E8F0",
        "default_limit": 400000
    },
    {
        "bank_name": "OneCard / Federal Bank",
        "card_name": "OneCard Metal Credit Card",
        "card_network": "Visa",
        "image_url": "https://getonecard.app/images/cards/metal-card.png",
        "gradient": "linear-gradient(135deg, #09090b 0%, #18181b 50%, #27272a 100%)",
        "accent_color": "#38BDF8",
        "default_limit": 200000
    },
    {
        "bank_name": "Federal Bank",
        "card_name": "Scapia Federal Bank Travel Card",
        "card_network": "Visa",
        "image_url": "https://assets.scapia.cards/images/card-front.png",
        "gradient": "linear-gradient(135deg, #0d9488 0%, #0f766e 60%, #115e59 100%)",
        "accent_color": "#5EEAD4",
        "default_limit": 200000
    },
    {
        "bank_name": "IDFC FIRST Bank",
        "card_name": "IDFC FIRST Wealth Card",
        "card_network": "Visa",
        "image_url": "https://www.idfcfirstbank.com/content/dam/idfcfirstbank/images/wealth-credit-card.png",
        "gradient": "linear-gradient(135deg, #1e1b4b 0%, #312e81 50%, #0f172a 100%)",
        "accent_color": "#FCD34D",
        "default_limit": 300000
    }
]

DEFAULT_CATEGORIES = [
    # Expense Categories
    {"name": "Food & Dining", "type": "expense", "icon": "🍔", "color": "#EF4444"},
    {"name": "Groceries & Supermarket", "type": "expense", "icon": "🛒", "color": "#10B981"},
    {"name": "Fuel & Transport", "type": "expense", "icon": "⛽", "color": "#F59E0B"},
    {"name": "Rent & Housing", "type": "expense", "icon": "🏠", "color": "#8B5CF6"},
    {"name": "Electricity & Bills", "type": "expense", "icon": "💡", "color": "#3B82F6"},
    {"name": "Shopping & Lifestyle", "type": "expense", "icon": "🛍️", "color": "#EC4899"},
    {"name": "Travel & Holidays", "type": "expense", "icon": "✈️", "color": "#06B6D4"},
    {"name": "Health & Medical", "type": "expense", "icon": "🏥", "color": "#14B8A6"},
    {"name": "Movies & Entertainment", "type": "expense", "icon": "🎬", "color": "#F97316"},
    {"name": "Mobile & Subscriptions", "type": "expense", "icon": "📱", "color": "#6366F1"},
    {"name": "Education & Courses", "type": "expense", "icon": "📚", "color": "#84CC16"},
    {"name": "Personal Care & Grooming", "type": "expense", "icon": "💇", "color": "#D946EF"},
    {"name": "Vehicle Maintenance", "type": "expense", "icon": "🚗", "color": "#64748B"},
    {"name": "Gifts & Donations", "type": "expense", "icon": "🎁", "color": "#F43F5E"},
    {"name": "General Expenses", "type": "expense", "icon": "📦", "color": "#94A3B8"},
    
    # Income Categories
    {"name": "Monthly Salary", "type": "income", "icon": "💵", "color": "#10B981"},
    {"name": "Freelance & Consulting", "type": "income", "icon": "💻", "color": "#3B82F6"},
    {"name": "Investments & Dividends", "type": "income", "icon": "📈", "color": "#8B5CF6"},
    {"name": "Rental Income", "type": "income", "icon": "🏢", "color": "#06B6D4"},
    {"name": "Cashback & Rewards", "type": "income", "icon": "🎁", "color": "#F59E0B"},
    {"name": "Bonus & Incentives", "type": "income", "icon": "⭐", "color": "#EAB308"},
    {"name": "Other Income", "type": "income", "icon": "💰", "color": "#6366F1"},
]

POPULAR_ICONS = [
    "🍔", "🛒", "⛽", "🏠", "💡", "🛍️", "✈️", "🏥", "🎬", "📱",
    "📚", "💇", "🚗", "🎁", "📦", "💵", "💻", "📈", "🏢", "💰",
    "☕", "🍕", "🚴", "🏋️", "🎟️", "👶", "🐶", "✈️", "🏖️", "🏨",
    "💳", "🔧", "🎨", "🎮", "🛡️", "👔", "💍", "🍼", "💊", "🧾"
]
