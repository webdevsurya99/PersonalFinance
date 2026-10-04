import datetime
import calendar
from typing import Optional, List, Dict, Any
from fastapi import APIRouter, Request, Depends, HTTPException, Query
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.database import get_db
from app.models import User, Transaction, BankAccount, CreditCard, Category, Trip, Notification
from app.dependencies import get_current_user
from app.core.date_provider import DateProvider
from app.core.security import generate_csrf_token
from app.core.reminder_engine import sync_card_reminders

router = APIRouter(tags=["Dashboard"])
templates = Jinja2Templates(directory="app/templates")

def get_date_range_for_period(
    period: str, 
    ref_date: datetime.date,
    start_date_str: Optional[str] = None,
    end_date_str: Optional[str] = None
) -> tuple[datetime.date, datetime.date]:
    """Calculate start and end dates based on filter period."""
    if period == "this_month":
        start_date = datetime.date(ref_date.year, ref_date.month, 1)
        _, last_day = calendar.monthrange(ref_date.year, ref_date.month)
        end_date = datetime.date(ref_date.year, ref_date.month, last_day)
    elif period == "last_month":
        year = ref_date.year if ref_date.month > 1 else ref_date.year - 1
        month = ref_date.month - 1 if ref_date.month > 1 else 12
        start_date = datetime.date(year, month, 1)
        _, last_day = calendar.monthrange(year, month)
        end_date = datetime.date(year, month, last_day)
    elif period == "last_30_days":
        start_date = ref_date - datetime.timedelta(days=30)
        end_date = ref_date
    elif period == "last_90_days":
        start_date = ref_date - datetime.timedelta(days=90)
        end_date = ref_date
    elif period == "this_year":
        start_date = datetime.date(ref_date.year, 1, 1)
        end_date = datetime.date(ref_date.year, 12, 31)
    elif period == "custom":
        parsed_start = None
        parsed_end = None
        if start_date_str:
            try:
                parsed_start = datetime.datetime.strptime(start_date_str.strip(), "%Y-%m-%d").date()
            except (ValueError, TypeError):
                pass
        if end_date_str:
            try:
                parsed_end = datetime.datetime.strptime(end_date_str.strip(), "%Y-%m-%d").date()
            except (ValueError, TypeError):
                pass

        if parsed_start and parsed_end:
            if parsed_start > parsed_end:
                parsed_start, parsed_end = parsed_end, parsed_start
            start_date, end_date = parsed_start, parsed_end
        elif parsed_start:
            start_date = parsed_start
            end_date = ref_date
        elif parsed_end:
            start_date = parsed_end - datetime.timedelta(days=30)
            end_date = parsed_end
        else:
            start_date = datetime.date(ref_date.year, ref_date.month, 1)
            _, last_day = calendar.monthrange(ref_date.year, ref_date.month)
            end_date = datetime.date(ref_date.year, ref_date.month, last_day)
    else:
        start_date = datetime.date(ref_date.year, ref_date.month, 1)
        _, last_day = calendar.monthrange(ref_date.year, ref_date.month)
        end_date = datetime.date(ref_date.year, ref_date.month, last_day)
        
    return start_date, end_date

@router.get("/", response_class=HTMLResponse)
@router.get("/dashboard", response_class=HTMLResponse)
async def dashboard_page(
    request: Request,
    period: str = Query("this_month"),
    start_date: Optional[str] = Query(None),
    end_date: Optional[str] = Query(None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    current_date = DateProvider.get_current_date(db)
    is_simulated = DateProvider.is_date_simulated(db)

    # Sync card reminders
    due_card_alerts = sync_card_reminders(db, current_user.id)

    # Date range for calculations
    start_dt, end_dt = get_date_range_for_period(period, current_date, start_date, end_date)

    # Query transactions in period
    txns = db.query(Transaction).filter(
        Transaction.user_id == current_user.id,
        Transaction.date >= start_dt,
        Transaction.date <= end_dt
    ).order_by(Transaction.date.desc(), Transaction.id.desc()).all()

    total_income = sum(t.amount for t in txns if t.type == "income")
    total_expense = sum(t.amount for t in txns if t.type == "expense")
    net_savings = total_income - total_expense
    savings_rate = round((net_savings / total_income * 100) if total_income > 0 else 0, 1)

    # Bank accounts & Credit cards
    bank_accounts = db.query(BankAccount).filter(
        BankAccount.user_id == current_user.id,
        BankAccount.is_active == True
    ).all()
    total_bank_balance = sum(b.current_balance for b in bank_accounts)

    credit_cards = db.query(CreditCard).filter(
        CreditCard.user_id == current_user.id,
        CreditCard.is_active == True
    ).all()
    total_credit_limit = sum(c.total_limit for c in credit_cards)
    total_available_credit = sum(c.available_limit for c in credit_cards)
    total_credit_used = total_credit_limit - total_available_credit

    # Categories & Trips for fast lodging modal
    categories = db.query(Category).filter(
        (Category.user_id == current_user.id) | (Category.is_system == True)
    ).order_by(Category.name.asc()).all()
    
    active_trips = db.query(Trip).filter(
        Trip.user_id == current_user.id,
        Trip.status.in_(["active", "planned"])
    ).all()

    # Recent transactions within the selected period
    recent_transactions = txns[:10]

    # CSRF token
    csrf_token = generate_csrf_token(current_user.id)

    return templates.TemplateResponse(
        request=request,
        name="dashboard/index.html",
        context={
            "user": current_user,
            "current_date": current_date,
            "is_simulated_date": is_simulated,
            "period": period,
            "start_date": start_dt,
            "end_date": end_dt,
            "custom_start_str": start_dt.strftime("%Y-%m-%d"),
            "custom_end_str": end_dt.strftime("%Y-%m-%d"),
            "total_income": total_income,
            "total_expense": total_expense,
            "net_savings": net_savings,
            "savings_rate": savings_rate,
            "bank_accounts": bank_accounts,
            "total_bank_balance": total_bank_balance,
            "credit_cards": credit_cards,
            "total_credit_limit": total_credit_limit,
            "total_available_credit": total_available_credit,
            "total_credit_used": total_credit_used,
            "categories": categories,
            "active_trips": active_trips,
            "recent_transactions": recent_transactions,
            "due_card_alerts": due_card_alerts,
            "csrf_token": csrf_token
        }
    )

@router.get("/api/dashboard/stats")
async def dashboard_stats_api(
    period: str = Query("this_month"),
    start_date: Optional[str] = Query(None),
    end_date: Optional[str] = Query(None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    JSON API for dynamic chart updates without full page reloads.
    """
    ref_date = DateProvider.get_current_date(db)
    start_dt, end_dt = get_date_range_for_period(period, ref_date, start_date, end_date)

    txns = db.query(Transaction).filter(
        Transaction.user_id == current_user.id,
        Transaction.date >= start_dt,
        Transaction.date <= end_dt
    ).order_by(Transaction.date.asc()).all()

    total_income = sum(t.amount for t in txns if t.type == "income")
    total_expense = sum(t.amount for t in txns if t.type == "expense")
    net_savings = total_income - total_expense
    savings_rate = round((net_savings / total_income * 100) if total_income > 0 else 0, 1)

    # 1. Category-wise expense breakdown
    cat_expenses: Dict[str, Dict[str, Any]] = {}
    for t in txns:
        if t.type == "expense":
            cat_name = t.category.name if t.category else "Uncategorized"
            cat_icon = t.category.icon if t.category else "📦"
            cat_color = t.category.color if t.category else "#94A3B8"
            
            if cat_name not in cat_expenses:
                cat_expenses[cat_name] = {
                    "label": f"{cat_icon} {cat_name}",
                    "amount": 0.0,
                    "color": cat_color
                }
            cat_expenses[cat_name]["amount"] += t.amount

    # Sort categories descending
    sorted_cats = sorted(cat_expenses.values(), key=lambda x: x["amount"], reverse=True)

    # 2. Activity / trend breakdown based on period length
    daily_map: Dict[str, Dict[str, float]] = {}
    delta_days = (end_dt - start_dt).days

    if delta_days <= 62:
        # Daily timeline
        curr = start_dt
        while curr <= end_dt:
            d_str = curr.strftime("%d %b")
            daily_map[d_str] = {"income": 0.0, "expense": 0.0}
            curr += datetime.timedelta(days=1)

        for t in txns:
            d_str = t.date.strftime("%d %b")
            if d_str in daily_map:
                daily_map[d_str][t.type] += t.amount
    else:
        # Monthly timeline for longer intervals
        curr = datetime.date(start_dt.year, start_dt.month, 1)
        end_month = datetime.date(end_dt.year, end_dt.month, 1)
        while curr <= end_month:
            m_str = curr.strftime("%b %y")
            daily_map[m_str] = {"income": 0.0, "expense": 0.0}
            # Next month
            y = curr.year + (1 if curr.month == 12 else 0)
            m = 1 if curr.month == 12 else curr.month + 1
            curr = datetime.date(y, m, 1)

        for t in txns:
            m_str = t.date.strftime("%b %y")
            if m_str in daily_map:
                daily_map[m_str][t.type] += t.amount

    daily_labels = list(daily_map.keys())
    daily_income = [daily_map[k]["income"] for k in daily_labels]
    daily_expense = [daily_map[k]["expense"] for k in daily_labels]

    return JSONResponse({
        "period": period,
        "start_date": start_dt.isoformat(),
        "end_date": end_dt.isoformat(),
        "date_range_display": f"{start_dt.strftime('%d %b')} – {end_dt.strftime('%d %b %Y')}",
        "total_income": total_income,
        "total_expense": total_expense,
        "net_savings": net_savings,
        "savings_rate": savings_rate,
        "currency_symbol": current_user.currency_symbol,
        "category_chart": {
            "labels": [c["label"] for c in sorted_cats],
            "data": [c["amount"] for c in sorted_cats],
            "colors": [c["color"] for c in sorted_cats]
        },
        "daily_chart": {
            "labels": daily_labels,
            "income": daily_income,
            "expense": daily_expense
        }
    })

