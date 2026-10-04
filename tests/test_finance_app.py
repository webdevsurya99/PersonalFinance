import pytest
import datetime
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database import Base, get_db
from app.main import app
from app.core.security import hash_password, verify_password, create_access_token, generate_csrf_token
from app.models import User, BankAccount, CreditCard, Category, Transaction, Trip, SystemSetting
from app.core.reminder_engine import calculate_card_dates
from app.core.date_provider import DateProvider

SQLALCHEMY_DATABASE_URL = "sqlite:///./test_finance.db"
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()

app.dependency_overrides[get_db] = override_get_db

@pytest.fixture(autouse=True)
def setup_db():
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)

@pytest.fixture
def client():
    return TestClient(app)

def test_password_hashing():
    """Verify password is securely hashed and plaintext is never matched directly."""
    pwd = "SecurePassword123!"
    hashed = hash_password(pwd)
    assert hashed != pwd
    assert verify_password(pwd, hashed) is True
    assert verify_password("WrongPassword", hashed) is False

def test_user_registration_and_login(client):
    """Test user registration, password security, and login session."""
    reg_response = client.post("/register", data={
        "full_name": "Test User",
        "email": "testuser@example.com",
        "password": "Password123!",
        "confirm_password": "Password123!",
        "currency_symbol": "₹"
    }, follow_redirects=False)
    
    assert reg_response.status_code == 303
    assert "fin_session_token" in reg_response.cookies

    login_response = client.post("/login", data={
        "email": "testuser@example.com",
        "password": "Password123!",
        "next": "/dashboard"
    }, follow_redirects=False)
    assert login_response.status_code == 303
    assert "fin_session_token" in login_response.cookies

    bad_login = client.post("/login", data={
        "email": "testuser@example.com",
        "password": "WrongPassword123",
        "next": "/dashboard"
    })
    assert bad_login.status_code == 400

def test_credit_card_due_date_calculation():
    """Verify billing cycle and due date calculation for credit cards."""
    card = CreditCard(
        bank_name="HDFC Bank",
        card_name="Regalia Gold",
        last_4_digits="1234",
        total_limit=300000,
        available_limit=250000,
        billing_day=15,
        due_day=5
    )
    ref_date = datetime.date(2026, 10, 4)
    info = calculate_card_dates(card, ref_date)
    
    assert info["next_billing_date"] == datetime.date(2026, 10, 15)
    assert info["next_due_date"] == datetime.date(2026, 10, 5)
    assert info["days_to_due"] == 1
    assert info["urgency"] == "danger"

def test_bank_and_expense_lifecycle(client):
    """Test bank account creation and expense balance deduction."""
    db = TestingSessionLocal()
    user = User(
        email="finance@example.com",
        full_name="Finance User",
        hashed_password=hash_password("Pass1234!"),
        is_admin=True,
        currency_symbol="₹"
    )
    db.add(user)
    db.commit()
    user_id = user.id
    user_email = user.email

    bank = BankAccount(
        user_id=user_id,
        bank_name="HDFC Bank",
        account_name="Salary A/C",
        account_number_last4="8899",
        initial_balance=50000.0,
        current_balance=50000.0,
        color="#004c8f"
    )
    db.add(bank)
    db.commit()
    bank_id = bank.id
    db.close()

    token = create_access_token(data={"sub": str(user_id), "email": user_email})
    client.cookies.set("fin_session_token", token)
    csrf = generate_csrf_token(user_id)
    
    res = client.post("/transactions/new", data={
        "type": "expense",
        "amount": "2500.00",
        "date": "2026-10-04",
        "payment_source": f"bank:{bank_id}",
        "tag": "#groceries",
        "remarks": "Supermarket haul",
        "csrf_token": csrf
    }, follow_redirects=False)
    assert res.status_code == 303
    
    db2 = TestingSessionLocal()
    b1 = db2.query(BankAccount).filter(BankAccount.id == bank_id).first()
    assert b1.current_balance == 47500.0
    db2.close()

    res_inc = client.post("/transactions/new", data={
        "type": "income",
        "amount": "10000.00",
        "date": "2026-10-04",
        "payment_source": f"bank:{bank_id}",
        "tag": "#freelance",
        "remarks": "Side project client payout",
        "csrf_token": csrf
    }, follow_redirects=False)
    assert res_inc.status_code == 303

    db3 = TestingSessionLocal()
    b2 = db3.query(BankAccount).filter(BankAccount.id == bank_id).first()
    assert b2.current_balance == 57500.0
    db3.close()

def test_credit_card_expense_and_limit_reduction(client):
    """Test credit card creation and available limit reduction upon charging an expense."""
    db = TestingSessionLocal()
    user = User(
        email="card_user@example.com",
        full_name="Card User",
        hashed_password=hash_password("Pass1234!"),
        is_admin=False,
        currency_symbol="₹"
    )
    db.add(user)
    db.commit()
    user_id = user.id
    user_email = user.email

    card = CreditCard(
        user_id=user_id,
        bank_name="ICICI Bank",
        card_name="Amazon Pay",
        card_network="Visa",
        last_4_digits="4321",
        total_limit=200000.0,
        opening_limit=200000.0,
        available_limit=200000.0,
        billing_day=20,
        due_day=10
    )
    db.add(card)
    db.commit()
    card_id = card.id
    db.close()

    token = create_access_token(data={"sub": str(user_id), "email": user_email})
    client.cookies.set("fin_session_token", token)
    csrf = generate_csrf_token(user_id)

    res = client.post("/transactions/new", data={
        "type": "expense",
        "amount": "15000.00",
        "date": "2026-10-04",
        "payment_source": f"card:{card_id}",
        "tag": "#electronics",
        "remarks": "New Monitor",
        "csrf_token": csrf
    }, follow_redirects=False)
    assert res.status_code == 303

    db2 = TestingSessionLocal()
    c = db2.query(CreditCard).filter(CreditCard.id == card_id).first()
    assert c.available_limit == 185000.0
    db2.close()

def test_trip_framework_and_budget_tracking(client):
    """Test trip creation and expense tagging without duplicate entries."""
    db = TestingSessionLocal()
    user = User(
        email="trip_user@example.com",
        full_name="Trip User",
        hashed_password=hash_password("Pass1234!"),
        is_admin=False,
        currency_symbol="₹"
    )
    db.add(user)
    db.commit()
    user_id = user.id
    user_email = user.email
    db.close()

    token = create_access_token(data={"sub": str(user_id), "email": user_email})
    client.cookies.set("fin_session_token", token)
    csrf = generate_csrf_token(user_id)

    # 1. Create Trip
    trip_res = client.post("/trips/new", data={
        "name": "Goa Trip 2026",
        "destination": "Goa",
        "start_date": "2026-11-01",
        "end_date": "2026-11-05",
        "budget": "40000.00",
        "description": "Beach vacation",
        "status": "active",
        "color": "#06B6D4",
        "csrf_token": csrf
    }, follow_redirects=False)
    assert trip_res.status_code == 303

    db2 = TestingSessionLocal()
    trip = db2.query(Trip).filter(Trip.user_id == user_id).first()
    assert trip is not None
    assert trip.budget == 40000.0
    trip_id = trip.id
    db2.close()

    # 2. Lodge Expense tagged to Trip
    txn_res = client.post("/transactions/new", data={
        "type": "expense",
        "amount": "12000.00",
        "date": "2026-11-01",
        "trip_id": str(trip_id),
        "tag": "#flight",
        "remarks": "Flight tickets",
        "csrf_token": csrf
    }, follow_redirects=False)
    assert txn_res.status_code == 303

    # Check Trip detail page renders
    detail_res = client.get(f"/trips/{trip_id}")
    assert detail_res.status_code == 200
    assert "Goa Trip 2026" in detail_res.text
    assert "Flight tickets" in detail_res.text

def test_categories_management(client):
    """Test category creation, editing, and deletion."""
    db = TestingSessionLocal()
    user = User(
        email="cat_user@example.com",
        full_name="Category User",
        hashed_password=hash_password("Pass1234!"),
        is_admin=False,
        currency_symbol="₹"
    )
    db.add(user)
    db.commit()
    user_id = user.id
    user_email = user.email
    db.close()

    token = create_access_token(data={"sub": str(user_id), "email": user_email})
    client.cookies.set("fin_session_token", token)
    csrf = generate_csrf_token(user_id)

    # Create category
    res = client.post("/categories/new", data={
        "name": "Gym & Fitness",
        "type": "expense",
        "icon": "🏋️",
        "color": "#F59E0B",
        "csrf_token": csrf
    }, follow_redirects=False)
    assert res.status_code == 303

    db2 = TestingSessionLocal()
    cat = db2.query(Category).filter(Category.name == "Gym & Fitness").first()
    assert cat is not None
    assert cat.icon == "🏋️"
    cat_id = cat.id
    db2.close()

    # Edit category
    edit_res = client.post(f"/categories/{cat_id}/edit", data={
        "name": "Gym & Sports",
        "type": "expense",
        "icon": "⚽",
        "color": "#10B981",
        "csrf_token": csrf
    }, follow_redirects=False)
    assert edit_res.status_code == 303

    db3 = TestingSessionLocal()
    edited_cat = db3.query(Category).filter(Category.id == cat_id).first()
    assert edited_cat.name == "Gym & Sports"
    assert edited_cat.icon == "⚽"
    db3.close()

    # Delete category
    del_res = client.post(f"/categories/{cat_id}/delete", data={
        "csrf_token": csrf
    }, follow_redirects=False)
    assert del_res.status_code == 303

    db4 = TestingSessionLocal()
    assert db4.query(Category).filter(Category.id == cat_id).first() is None
    db4.close()

def test_admin_simulated_date_override(client):
    """Test admin system date override and reset capability."""
    db = TestingSessionLocal()
    admin = User(
        email="admin_test@example.com",
        full_name="Admin Test",
        hashed_password=hash_password("AdminPass123!"),
        is_admin=True,
        currency_symbol="₹"
    )
    db.add(admin)
    db.commit()
    admin_id = admin.id
    admin_email = admin.email
    db.close()

    token = create_access_token(data={"sub": str(admin_id), "email": admin_email})
    client.cookies.set("fin_session_token", token)
    csrf = generate_csrf_token(admin_id)

    override_res = client.post("/admin/date-override", data={
        "target_date": "2026-12-25",
        "csrf_token": csrf
    }, follow_redirects=False)
    assert override_res.status_code == 303

    db2 = TestingSessionLocal()
    eff_date = DateProvider.get_current_date(db2)
    assert eff_date == datetime.date(2026, 12, 25)
    assert DateProvider.is_date_simulated(db2) is True
    db2.close()

    reset_res = client.post("/admin/reset-date", data={
        "csrf_token": csrf
    }, follow_redirects=False)
    assert reset_res.status_code == 303

    db3 = TestingSessionLocal()
    eff_date_reset = DateProvider.get_current_date(db3)
    assert eff_date_reset == datetime.date.today()
    assert DateProvider.is_date_simulated(db3) is False
    db3.close()

def test_export_statements(client):
    """Test Excel and PDF generation endpoints."""
    db = TestingSessionLocal()
    user = User(
        email="export_user@example.com",
        full_name="Export User",
        hashed_password=hash_password("UserPass123!"),
        is_admin=False,
        currency_symbol="₹"
    )
    db.add(user)
    db.commit()
    user_id = user.id
    user_email = user.email
    db.close()

    token = create_access_token(data={"sub": str(user_id), "email": user_email})
    client.cookies.set("fin_session_token", token)

    excel_res = client.get("/export/excel?period=this_month")
    assert excel_res.status_code == 200
    assert "spreadsheetml" in excel_res.headers["content-type"]
    assert len(excel_res.content) > 100

    pdf_res = client.get("/export/pdf?period=this_month")
    assert pdf_res.status_code == 200
    assert "application/pdf" in pdf_res.headers["content-type"]
    assert pdf_res.content.startswith(b"%PDF")

def test_security_headers_and_pwa(client):
    """Verify OWASP security headers and PWA manifest delivery."""
    res = client.get("/manifest.json")
    assert res.status_code == 200
    manifest = res.json()
    assert manifest["short_name"] == "FinMinimal"
    assert manifest["display"] == "standalone"

    assert res.headers.get("x-frame-options") == "DENY"
    assert res.headers.get("x-content-type-options") == "nosniff"
    assert "default-src 'self'" in res.headers.get("content-security-policy", "")
