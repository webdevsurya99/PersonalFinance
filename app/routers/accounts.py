import datetime
from typing import Optional, List
from fastapi import APIRouter, Request, Depends, HTTPException, status, Form
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import User, BankAccount, CreditCard, Category, Trip, Transaction, AuditLog
from app.dependencies import get_current_user, verify_csrf
from app.core.date_provider import DateProvider
from app.core.security import generate_csrf_token, sanitize_text
from app.core.presets import INDIAN_BANKS, INDIAN_CREDIT_CARDS
from app.core.reminder_engine import calculate_card_dates

router = APIRouter(tags=["Accounts & Cards"])
templates = Jinja2Templates(directory="app/templates")

def get_now_utc() -> datetime.datetime:
    return datetime.datetime.now(datetime.timezone.utc).replace(tzinfo=None)

def get_common_context(db: Session, user: User) -> dict:
    categories = db.query(Category).filter(
        (Category.user_id == user.id) | (Category.is_system == True)
    ).order_by(Category.name.asc()).all()
    bank_accounts = db.query(BankAccount).filter(BankAccount.user_id == user.id, BankAccount.is_active == True).all()
    credit_cards = db.query(CreditCard).filter(CreditCard.user_id == user.id, CreditCard.is_active == True).all()
    active_trips = db.query(Trip).filter(Trip.user_id == user.id, Trip.status.in_(["active", "planned"])).all()
    current_date = DateProvider.get_current_date(db)
    is_simulated = DateProvider.is_date_simulated(db)
    csrf_token = generate_csrf_token(user.id)
    return {
        "user": user,
        "categories": categories,
        "bank_accounts": bank_accounts,
        "credit_cards": credit_cards,
        "active_trips": active_trips,
        "current_date": current_date,
        "is_simulated_date": is_simulated,
        "csrf_token": csrf_token
    }

@router.get("/accounts", response_class=HTMLResponse)
async def accounts_overview_page(
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    ctx = get_common_context(db, current_user)
    current_date = ctx["current_date"]
    credit_cards = ctx["credit_cards"]

    cards_with_meta = []
    for card in credit_cards:
        dates_info = calculate_card_dates(card, current_date)
        used_limit = max(0.0, card.total_limit - card.available_limit)
        utilization_pct = round((used_limit / card.total_limit * 100) if card.total_limit > 0 else 0, 1)
        cards_with_meta.append({
            "card": card,
            "dates": dates_info,
            "used_limit": used_limit,
            "utilization_pct": utilization_pct
        })

    ctx.update({
        "cards_with_meta": cards_with_meta,
        "bank_presets": INDIAN_BANKS,
        "card_presets": INDIAN_CREDIT_CARDS
    })

    return templates.TemplateResponse(
        request=request,
        name="accounts/index.html",
        context=ctx
    )

# ----------------- Bank Accounts -----------------

@router.get("/accounts/bank/new", response_class=HTMLResponse)
async def add_bank_page(
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    ctx = get_common_context(db, current_user)
    ctx.update({"bank_presets": INDIAN_BANKS})
    return templates.TemplateResponse(
        request=request,
        name="accounts/add_bank.html",
        context=ctx
    )

@router.post("/accounts/bank/new")
async def add_bank_submit(
    request: Request,
    bank_name: str = Form(...),
    account_name: str = Form(...),
    account_number_last4: str = Form(...),
    ifsc_code: Optional[str] = Form(None),
    initial_balance: float = Form(0.0),
    color: Optional[str] = Form("#2563EB"),
    csrf_token: str = Form(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    await verify_csrf(request, current_user)

    clean_bank_name = sanitize_text(bank_name)
    clean_account_name = sanitize_text(account_name)
    clean_last4 = sanitize_text(account_number_last4)[-4:]

    bank = BankAccount(
        user_id=current_user.id,
        bank_name=clean_bank_name,
        account_name=clean_account_name,
        account_number_last4=clean_last4,
        ifsc_code=sanitize_text(ifsc_code),
        initial_balance=initial_balance,
        current_balance=initial_balance,
        color=color or "#2563EB",
        created_at=get_now_utc()
    )
    db.add(bank)
    db.commit()

    return RedirectResponse(url="/accounts", status_code=status.HTTP_303_SEE_OTHER)

@router.get("/accounts/bank/{bank_id}/edit", response_class=HTMLResponse)
async def edit_bank_page(
    request: Request,
    bank_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    bank = db.query(BankAccount).filter(BankAccount.id == bank_id, BankAccount.user_id == current_user.id).first()
    if not bank:
        raise HTTPException(status_code=404, detail="Bank account not found.")

    ctx = get_common_context(db, current_user)
    ctx.update({
        "bank": bank,
        "bank_presets": INDIAN_BANKS
    })

    return templates.TemplateResponse(
        request=request,
        name="accounts/edit_bank.html",
        context=ctx
    )

@router.post("/accounts/bank/{bank_id}/edit")
async def edit_bank_submit(
    request: Request,
    bank_id: int,
    bank_name: str = Form(...),
    account_name: str = Form(...),
    account_number_last4: str = Form(...),
    ifsc_code: Optional[str] = Form(None),
    current_balance: float = Form(...),
    color: Optional[str] = Form("#2563EB"),
    csrf_token: str = Form(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    await verify_csrf(request, current_user)

    bank = db.query(BankAccount).filter(BankAccount.id == bank_id, BankAccount.user_id == current_user.id).first()
    if not bank:
        raise HTTPException(status_code=404, detail="Bank account not found.")

    bank.bank_name = sanitize_text(bank_name)
    bank.account_name = sanitize_text(account_name)
    bank.account_number_last4 = sanitize_text(account_number_last4)[-4:]
    bank.ifsc_code = sanitize_text(ifsc_code)
    bank.current_balance = current_balance
    bank.color = color or "#2563EB"
    bank.updated_at = get_now_utc()

    db.commit()
    return RedirectResponse(url="/accounts", status_code=status.HTTP_303_SEE_OTHER)

@router.post("/accounts/bank/{bank_id}/delete")
async def delete_bank(
    request: Request,
    bank_id: int,
    csrf_token: str = Form(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    await verify_csrf(request, current_user)

    bank = db.query(BankAccount).filter(BankAccount.id == bank_id, BankAccount.user_id == current_user.id).first()
    if not bank:
        raise HTTPException(status_code=404, detail="Bank account not found.")

    bank.is_active = False
    db.commit()

    return RedirectResponse(url="/accounts", status_code=status.HTTP_303_SEE_OTHER)

# ----------------- Credit Cards -----------------

@router.get("/accounts/card/new", response_class=HTMLResponse)
async def add_card_page(
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    ctx = get_common_context(db, current_user)
    ctx.update({"card_presets": INDIAN_CREDIT_CARDS})
    return templates.TemplateResponse(
        request=request,
        name="accounts/add_card.html",
        context=ctx
    )

@router.post("/accounts/card/new")
async def add_card_submit(
    request: Request,
    bank_name: str = Form(...),
    card_name: str = Form(...),
    card_network: str = Form("Visa"),
    last_4_digits: str = Form(...),
    total_limit: float = Form(...),
    opening_limit: float = Form(...),
    billing_day: int = Form(...),
    due_day: int = Form(...),
    card_image_url: Optional[str] = Form(None),
    card_color_gradient: Optional[str] = Form(None),
    csrf_token: str = Form(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    await verify_csrf(request, current_user)

    if billing_day < 1 or billing_day > 31 or due_day < 1 or due_day > 31:
        raise HTTPException(status_code=400, detail="Billing day and Due day must be between 1 and 31.")

    card = CreditCard(
        user_id=current_user.id,
        bank_name=sanitize_text(bank_name),
        card_name=sanitize_text(card_name),
        card_network=sanitize_text(card_network) or "Visa",
        last_4_digits=sanitize_text(last_4_digits)[-4:],
        total_limit=total_limit,
        opening_limit=opening_limit,
        available_limit=opening_limit,
        billing_day=billing_day,
        due_day=due_day,
        card_image_url=card_image_url or None,
        card_color_gradient=card_color_gradient or "linear-gradient(135deg, #1e293b 0%, #0f172a 100%)",
        created_at=get_now_utc()
    )
    db.add(card)
    db.commit()

    return RedirectResponse(url="/accounts", status_code=status.HTTP_303_SEE_OTHER)

@router.get("/accounts/card/{card_id}/edit", response_class=HTMLResponse)
async def edit_card_page(
    request: Request,
    card_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    card = db.query(CreditCard).filter(CreditCard.id == card_id, CreditCard.user_id == current_user.id).first()
    if not card:
        raise HTTPException(status_code=404, detail="Credit card not found.")

    ctx = get_common_context(db, current_user)
    ctx.update({
        "card": card,
        "card_presets": INDIAN_CREDIT_CARDS
    })

    return templates.TemplateResponse(
        request=request,
        name="accounts/edit_card.html",
        context=ctx
    )

@router.post("/accounts/card/{card_id}/edit")
async def edit_card_submit(
    request: Request,
    card_id: int,
    bank_name: str = Form(...),
    card_name: str = Form(...),
    card_network: str = Form("Visa"),
    last_4_digits: str = Form(...),
    total_limit: float = Form(...),
    available_limit: float = Form(...),
    billing_day: int = Form(...),
    due_day: int = Form(...),
    card_image_url: Optional[str] = Form(None),
    card_color_gradient: Optional[str] = Form(None),
    csrf_token: str = Form(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    await verify_csrf(request, current_user)

    card = db.query(CreditCard).filter(CreditCard.id == card_id, CreditCard.user_id == current_user.id).first()
    if not card:
        raise HTTPException(status_code=404, detail="Credit card not found.")

    card.bank_name = sanitize_text(bank_name)
    card.card_name = sanitize_text(card_name)
    card.card_network = sanitize_text(card_network) or "Visa"
    card.last_4_digits = sanitize_text(last_4_digits)[-4:]
    card.total_limit = total_limit
    card.available_limit = available_limit
    card.billing_day = billing_day
    card.due_day = due_day
    if card_image_url:
        card.card_image_url = card_image_url
    if card_color_gradient:
        card.card_color_gradient = card_color_gradient
    card.updated_at = get_now_utc()

    db.commit()
    return RedirectResponse(url="/accounts", status_code=status.HTTP_303_SEE_OTHER)

@router.post("/accounts/card/{card_id}/delete")
async def delete_card(
    request: Request,
    card_id: int,
    csrf_token: str = Form(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    await verify_csrf(request, current_user)

    card = db.query(CreditCard).filter(CreditCard.id == card_id, CreditCard.user_id == current_user.id).first()
    if not card:
        raise HTTPException(status_code=404, detail="Credit card not found.")

    card.is_active = False
    db.commit()

    return RedirectResponse(url="/accounts", status_code=status.HTTP_303_SEE_OTHER)

@router.get("/api/banks/presets")
@router.get("/api/presets/banks")
async def get_bank_presets_api():
    return JSONResponse({"banks": INDIAN_BANKS})

@router.get("/api/cards/presets")
@router.get("/api/presets/cards")
async def get_card_presets_api():
    return JSONResponse({"cards": INDIAN_CREDIT_CARDS})

