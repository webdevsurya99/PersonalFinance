import datetime
from typing import Optional, List
from fastapi import APIRouter, Request, Depends, HTTPException, status, Form, Query
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from sqlalchemy import or_

from app.database import get_db
from app.models import User, Transaction, BankAccount, CreditCard, Category, Trip, AuditLog
from app.dependencies import get_current_user, verify_csrf
from app.core.date_provider import DateProvider
from app.core.security import generate_csrf_token, sanitize_text

router = APIRouter(tags=["Transactions"])
templates = Jinja2Templates(directory="app/templates")

def get_now_utc() -> datetime.datetime:
    return datetime.datetime.now(datetime.timezone.utc).replace(tzinfo=None)

def apply_balance_delta(db: Session, txn_type: str, amount: float, bank_id: Optional[int], card_id: Optional[int], is_reversal: bool = False):
    """
    Adjust bank account balance or credit card available limit for a transaction.
    """
    factor = -1 if is_reversal else 1

    if bank_id:
        bank = db.query(BankAccount).filter(BankAccount.id == bank_id).first()
        if bank:
            if txn_type == "expense":
                bank.current_balance -= (amount * factor)
            elif txn_type == "income":
                bank.current_balance += (amount * factor)
            bank.updated_at = get_now_utc()

    elif card_id:
        card = db.query(CreditCard).filter(CreditCard.id == card_id).first()
        if card:
            if txn_type == "expense":
                card.available_limit -= (amount * factor)
            elif txn_type == "income":
                card.available_limit += (amount * factor)
            card.updated_at = get_now_utc()

@router.get("/transactions", response_class=HTMLResponse)
async def list_transactions(
    request: Request,
    type: Optional[str] = Query(None),
    category_id: Optional[int] = Query(None),
    account_id: Optional[int] = Query(None),
    card_id: Optional[int] = Query(None),
    trip_id: Optional[int] = Query(None),
    tag: Optional[str] = Query(None),
    q: Optional[str] = Query(None),
    start_date: Optional[str] = Query(None),
    end_date: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    limit: int = Query(25, ge=5, le=100),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    query = db.query(Transaction).filter(Transaction.user_id == current_user.id)

    if type in ("expense", "income"):
        query = query.filter(Transaction.type == type)
    if category_id:
        query = query.filter(Transaction.category_id == category_id)
    if account_id:
        query = query.filter(Transaction.bank_account_id == account_id)
    if card_id:
        query = query.filter(Transaction.credit_card_id == card_id)
    if trip_id:
        query = query.filter(Transaction.trip_id == trip_id)
    if tag:
        query = query.filter(Transaction.tag.ilike(f"%{tag}%"))
    if q:
        search = f"%{q}%"
        query = query.filter(or_(Transaction.remarks.ilike(search), Transaction.tag.ilike(search)))
        
    if start_date:
        try:
            s_dt = datetime.datetime.strptime(start_date, "%Y-%m-%d").date()
            query = query.filter(Transaction.date >= s_dt)
        except ValueError:
            pass
    if end_date:
        try:
            e_dt = datetime.datetime.strptime(end_date, "%Y-%m-%d").date()
            query = query.filter(Transaction.date <= e_dt)
        except ValueError:
            pass

    total_count = query.count()
    txns = query.order_by(Transaction.date.desc(), Transaction.id.desc()).offset((page - 1) * limit).limit(limit).all()

    # Dropdown lookups
    categories = db.query(Category).filter(
        (Category.user_id == current_user.id) | (Category.is_system == True)
    ).order_by(Category.name.asc()).all()

    bank_accounts = db.query(BankAccount).filter(BankAccount.user_id == current_user.id, BankAccount.is_active == True).all()
    credit_cards = db.query(CreditCard).filter(CreditCard.user_id == current_user.id, CreditCard.is_active == True).all()
    trips = db.query(Trip).filter(Trip.user_id == current_user.id).order_by(Trip.start_date.desc()).all()

    current_date = DateProvider.get_current_date(db)
    csrf_token = generate_csrf_token(current_user.id)

    total_pages = max(1, (total_count + limit - 1) // limit)

    return templates.TemplateResponse(
        request=request,
        name="transactions/index.html",
        context={
            "user": current_user,
            "transactions": txns,
            "total_count": total_count,
            "page": page,
            "limit": limit,
            "total_pages": total_pages,
            "categories": categories,
            "bank_accounts": bank_accounts,
            "credit_cards": credit_cards,
            "trips": trips,
            "current_date": current_date,
            "csrf_token": csrf_token,
            "filters": {
                "type": type or "",
                "category_id": category_id or "",
                "account_id": account_id or "",
                "card_id": card_id or "",
                "trip_id": trip_id or "",
                "tag": tag or "",
                "q": q or "",
                "start_date": start_date or "",
                "end_date": end_date or ""
            }
        }
    )

@router.post("/transactions/new")
async def create_transaction(
    request: Request,
    type: str = Form(...),
    amount: float = Form(...),
    date: Optional[str] = Form(None),
    category_id: Optional[int] = Form(None),
    payment_source: Optional[str] = Form(None),
    trip_id: Optional[int] = Form(None),
    tag: Optional[str] = Form(None),
    remarks: Optional[str] = Form(None),
    csrf_token: str = Form(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    await verify_csrf(request, current_user)

    if amount <= 0:
        raise HTTPException(status_code=400, detail="Amount must be greater than zero.")

    # Parse date (default to today / simulated date)
    if date:
        try:
            txn_date = datetime.datetime.strptime(date, "%Y-%m-%d").date()
        except ValueError:
            txn_date = DateProvider.get_current_date(db)
    else:
        txn_date = DateProvider.get_current_date(db)

    # Parse payment source
    bank_account_id = None
    credit_card_id = None
    if payment_source:
        if payment_source.startswith("bank:"):
            bank_account_id = int(payment_source.split(":")[1])
        elif payment_source.startswith("card:"):
            credit_card_id = int(payment_source.split(":")[1])

    clean_tag = sanitize_text(tag)
    clean_remarks = sanitize_text(remarks)

    txn = Transaction(
        user_id=current_user.id,
        type=type if type in ("expense", "income") else "expense",
        amount=amount,
        date=txn_date,
        category_id=category_id if category_id and category_id > 0 else None,
        bank_account_id=bank_account_id,
        credit_card_id=credit_card_id,
        trip_id=trip_id if trip_id and trip_id > 0 else None,
        tag=clean_tag,
        remarks=clean_remarks,
        created_at=DateProvider.get_current_datetime(db)
    )
    db.add(txn)
    
    # Update linked account balance
    apply_balance_delta(db, txn.type, amount, bank_account_id, credit_card_id, is_reversal=False)
    db.commit()

    # If AJAX request, return JSON
    if "application/json" in request.headers.get("accept", "") or request.headers.get("X-Requested-With") == "XMLHttpRequest":
        return JSONResponse({"status": "success", "message": "Transaction recorded successfully.", "id": txn.id})

    # Return redirect
    referer = request.headers.get("referer", "/dashboard")
    return RedirectResponse(url=referer, status_code=status.HTTP_303_SEE_OTHER)

@router.get("/transactions/{txn_id}/edit", response_class=HTMLResponse)
async def edit_transaction_page(
    request: Request,
    txn_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    txn = db.query(Transaction).filter(Transaction.id == txn_id, Transaction.user_id == current_user.id).first()
    if not txn:
        raise HTTPException(status_code=404, detail="Transaction not found.")

    categories = db.query(Category).filter(
        (Category.user_id == current_user.id) | (Category.is_system == True)
    ).order_by(Category.name.asc()).all()

    bank_accounts = db.query(BankAccount).filter(BankAccount.user_id == current_user.id, BankAccount.is_active == True).all()
    credit_cards = db.query(CreditCard).filter(CreditCard.user_id == current_user.id, CreditCard.is_active == True).all()
    trips = db.query(Trip).filter(Trip.user_id == current_user.id).order_by(Trip.start_date.desc()).all()

    csrf_token = generate_csrf_token(current_user.id)

    return templates.TemplateResponse(
        request=request,
        name="transactions/edit.html",
        context={
            "user": current_user,
            "txn": txn,
            "categories": categories,
            "bank_accounts": bank_accounts,
            "credit_cards": credit_cards,
            "trips": trips,
            "csrf_token": csrf_token
        }
    )

@router.post("/transactions/{txn_id}/edit")
async def update_transaction(
    request: Request,
    txn_id: int,
    type: str = Form(...),
    amount: float = Form(...),
    date: str = Form(...),
    category_id: Optional[int] = Form(None),
    payment_source: Optional[str] = Form(None),
    trip_id: Optional[int] = Form(None),
    tag: Optional[str] = Form(None),
    remarks: Optional[str] = Form(None),
    csrf_token: str = Form(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    await verify_csrf(request, current_user)

    txn = db.query(Transaction).filter(Transaction.id == txn_id, Transaction.user_id == current_user.id).first()
    if not txn:
        raise HTTPException(status_code=404, detail="Transaction not found.")

    # 1. Reverse previous balance impact
    apply_balance_delta(db, txn.type, txn.amount, txn.bank_account_id, txn.credit_card_id, is_reversal=True)

    # 2. Parse new payment source
    bank_account_id = None
    credit_card_id = None
    if payment_source:
        if payment_source.startswith("bank:"):
            bank_account_id = int(payment_source.split(":")[1])
        elif payment_source.startswith("card:"):
            credit_card_id = int(payment_source.split(":")[1])

    # 3. Update fields
    try:
        txn.date = datetime.datetime.strptime(date, "%Y-%m-%d").date()
    except ValueError:
        pass

    txn.type = type if type in ("expense", "income") else "expense"
    txn.amount = amount
    txn.category_id = category_id if category_id and category_id > 0 else None
    txn.bank_account_id = bank_account_id
    txn.credit_card_id = credit_card_id
    txn.trip_id = trip_id if trip_id and trip_id > 0 else None
    txn.tag = sanitize_text(tag)
    txn.remarks = sanitize_text(remarks)
    txn.updated_at = get_now_utc()

    # 4. Apply new balance impact
    apply_balance_delta(db, txn.type, txn.amount, txn.bank_account_id, txn.credit_card_id, is_reversal=False)
    db.commit()

    return RedirectResponse(url="/transactions", status_code=status.HTTP_303_SEE_OTHER)

@router.post("/transactions/{txn_id}/delete")
async def delete_transaction(
    request: Request,
    txn_id: int,
    csrf_token: str = Form(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    await verify_csrf(request, current_user)

    txn = db.query(Transaction).filter(Transaction.id == txn_id, Transaction.user_id == current_user.id).first()
    if not txn:
        raise HTTPException(status_code=404, detail="Transaction not found.")

    # Reverse balance impact
    apply_balance_delta(db, txn.type, txn.amount, txn.bank_account_id, txn.credit_card_id, is_reversal=True)

    db.delete(txn)
    db.commit()

    referer = request.headers.get("referer", "/transactions")
    return RedirectResponse(url=referer, status_code=status.HTTP_303_SEE_OTHER)
