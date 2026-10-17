import datetime
import calendar
import math
from typing import Optional, List, Dict, Any
from fastapi import APIRouter, Request, Depends, HTTPException, Query, Form, status
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.database import get_db
from app.models import User, Transaction, BankAccount, CreditCard, Category, Trip, Notification
from app.dependencies import get_current_user
from app.core.date_provider import DateProvider
from app.core.security import generate_csrf_token
from app.core.reminder_engine import sync_card_reminders

from app.core.templates import templates
from app.core.currency import format_inr

router = APIRouter(tags=["Dashboard"])

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
    total_credit_used = max(0.0, total_credit_limit - total_available_credit)
    cash_balance = getattr(current_user, "cash_balance", 0.0) or 0.0
    live_balance = total_bank_balance + cash_balance - total_credit_used

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

    # Dynamic Greeting (Image 1: "Good evening, Sahil 👋")
    now_hour = datetime.datetime.now().hour
    if now_hour < 12:
        greeting = "Good morning,"
    elif now_hour < 17:
        greeting = "Good afternoon,"
    else:
        greeting = "Good evening,"

    # Unread notifications count
    unread_notifications_count = db.query(Notification).filter(
        Notification.user_id == current_user.id,
        Notification.is_read == False
    ).count()

    # Budget info for current month
    user_budget = getattr(current_user, "monthly_budget", 25000.0) or 25000.0
    cur_month_start = datetime.date(current_date.year, current_date.month, 1)
    _, last_day_cur = calendar.monthrange(current_date.year, current_date.month)
    cur_month_end = datetime.date(current_date.year, current_date.month, last_day_cur)
    cur_month_expense = db.query(func.coalesce(func.sum(Transaction.amount), 0.0)).filter(
        Transaction.user_id == current_user.id,
        Transaction.date >= cur_month_start,
        Transaction.date <= cur_month_end,
        Transaction.type == "expense"
    ).scalar() or 0.0

    budget_spent_percent = round((cur_month_expense / user_budget * 100), 1) if user_budget > 0 else 0
    budget_remaining = max(0.0, user_budget - cur_month_expense)

    # CSRF token
    csrf_token = generate_csrf_token(current_user.id)

    return templates.TemplateResponse(
        request=request,
        name="dashboard/index.html",
        context={
            "user": current_user,
            "greeting": greeting,
            "unread_notifications_count": unread_notifications_count,
            "user_budget": user_budget,
            "cur_month_expense": cur_month_expense,
            "budget_spent_percent": budget_spent_percent,
            "budget_remaining": budget_remaining,
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
            "cash_balance": cash_balance,
            "credit_cards": credit_cards,
            "total_credit_limit": total_credit_limit,
            "total_available_credit": total_available_credit,
            "total_credit_used": total_credit_used,
            "live_balance": live_balance,
            "live_balance_formatted": format_inr(live_balance),
            "total_bank_balance_formatted": format_inr(total_bank_balance),
            "cash_balance_formatted": format_inr(cash_balance),
            "total_income_formatted": format_inr(total_income),
            "total_expense_formatted": format_inr(total_expense),
            "net_savings_formatted": format_inr(net_savings),
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

    # Live balance calculations
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
    total_credit_used = max(0.0, total_credit_limit - total_available_credit)
    cash_balance = getattr(current_user, "cash_balance", 0.0) or 0.0
    live_balance = total_bank_balance + cash_balance - total_credit_used

    return JSONResponse({
        "period": period,
        "start_date": start_dt.isoformat(),
        "end_date": end_dt.isoformat(),
        "date_range_display": f"{start_dt.strftime('%d %b')} – {end_dt.strftime('%d %b %Y')}",
        "total_income": total_income,
        "total_expense": total_expense,
        "net_savings": net_savings,
        "savings_rate": savings_rate,
        "total_bank_balance": total_bank_balance,
        "cash_balance": cash_balance,
        "total_credit_used": total_credit_used,
        "live_balance": live_balance,
        "live_balance_formatted": format_inr(live_balance),
        "total_bank_balance_formatted": format_inr(total_bank_balance),
        "cash_balance_formatted": format_inr(cash_balance),
        "total_income_formatted": format_inr(total_income),
        "total_expense_formatted": format_inr(total_expense),
        "net_savings_formatted": format_inr(net_savings),
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

@router.get("/budgets", response_class=HTMLResponse)
async def budgets_page(
    request: Request,
    month: Optional[str] = Query(None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Budgets & Insights Page matching iOS FinTech circular breakdown design.
    """
    current_date = DateProvider.get_current_date(db)
    is_simulated = DateProvider.is_date_simulated(db)

    # Determine Year and Month
    target_year = current_date.year
    target_month = current_date.month
    if month:
        try:
            parts = month.strip().split("-")
            target_year = int(parts[0])
            target_month = int(parts[1])
        except Exception:
            pass

    start_dt = datetime.date(target_year, target_month, 1)
    _, last_day = calendar.monthrange(target_year, target_month)
    end_dt = datetime.date(target_year, target_month, last_day)

    # Prev and Next month navigation strings
    prev_y = target_year if target_month > 1 else target_year - 1
    prev_m = target_month - 1 if target_month > 1 else 12
    prev_month_str = f"{prev_y:04d}-{prev_m:02d}"

    next_y = target_year if target_month < 12 else target_year + 1
    next_m = target_month + 1 if target_month < 12 else 1
    next_month_str = f"{next_y:04d}-{next_m:02d}"

    month_label = f"{calendar.month_name[target_month]} {target_year}"

    # Budget Limits
    user_budget = getattr(current_user, "monthly_budget", 25000.0) or 25000.0

    # Query expenses for the month
    txns = db.query(Transaction).filter(
        Transaction.user_id == current_user.id,
        Transaction.date >= start_dt,
        Transaction.date <= end_dt,
        Transaction.type == "expense"
    ).all()

    total_spent = sum(t.amount for t in txns)
    percentage_spent = round((total_spent / user_budget * 100), 1) if user_budget > 0 else 0
    remaining_budget = max(0.0, user_budget - total_spent)

    # Group by category with vibrant modern palette matching screenshot
    palette = [
        {"color": "#F97316", "icon": "fa-solid fa-mug-hot"},     # Orange (Food & Drinks)
        {"color": "#06B6D4", "icon": "fa-solid fa-car"},         # Blue/Cyan (Transport)
        {"color": "#10B981", "icon": "fa-solid fa-basket-shopping"}, # Green (Groceries)
        {"color": "#F59E0B", "icon": "fa-solid fa-bag-shopping"},   # Yellow (Shopping)
        {"color": "#EF4444", "icon": "fa-solid fa-heart-pulse"},    # Coral Red (Health/Bills)
        {"color": "#8B5CF6", "icon": "fa-solid fa-film"},           # Purple (Entertainment)
        {"color": "#EC4899", "icon": "fa-solid fa-receipt"},        # Pink (Utilities)
        {"color": "#3B82F6", "icon": "fa-solid fa-plane"}           # Royal Blue (Travel)
    ]

    cat_map: Dict[int, Dict[str, Any]] = {}
    uncat_spent = 0.0

    for t in txns:
        if t.category:
            cid = t.category.id
            if cid not in cat_map:
                idx = len(cat_map) % len(palette)
                chosen_color = t.category.color if t.category.color and t.category.color != "#6366F1" else palette[idx]["color"]
                chosen_icon = t.category.icon or palette[idx]["icon"]
                if chosen_icon and not chosen_icon.startswith("fa-") and not any(ord(c) > 127 for c in chosen_icon):
                    chosen_icon = f"fa-solid fa-{chosen_icon}"
                cat_map[cid] = {
                    "id": cid,
                    "name": t.category.name,
                    "icon": chosen_icon,
                    "color": chosen_color,
                    "amount": 0.0
                }
            cat_map[cid]["amount"] += t.amount
        else:
            uncat_spent += t.amount

    if uncat_spent > 0:
        cat_map[0] = {
            "id": 0,
            "name": "General / Others",
            "icon": "fa-solid fa-shapes",
            "color": "#94A3B8",
            "amount": uncat_spent
        }

    category_list = sorted(cat_map.values(), key=lambda x: x["amount"], reverse=True)

    # Angular placement of category badges along the donut ring
    current_angle = -90.0  # Top start (-90 degrees)
    for cat in category_list:
        cat_share = (cat["amount"] / total_spent) if total_spent > 0 else (1.0 / max(1, len(category_list)))
        cat_degrees = cat_share * 360.0
        mid_angle_deg = current_angle + (cat_degrees / 2.0)
        current_angle += cat_degrees

        rad = math.radians(mid_angle_deg)
        # 50% center, 40% radius
        cat["pin_x"] = round(50 + 40 * math.cos(rad), 2)
        cat["pin_y"] = round(50 + 40 * math.sin(rad), 2)
        cat["percentage"] = round(cat_share * 100, 1)

    # If no expenses yet, provide friendly fallback preview pins
    if not category_list:
        sample_cats = [
            {"id": 1, "name": "Food & Dining", "icon": "🍔", "color": "#F97316", "amount": 0.0, "percentage": 35.0, "pin_x": 88.0, "pin_y": 62.0},
            {"id": 2, "name": "Transport", "icon": "🚗", "color": "#06B6D4", "amount": 0.0, "percentage": 25.0, "pin_x": 22.0, "pin_y": 78.0},
            {"id": 3, "name": "Groceries", "icon": "🛒", "color": "#10B981", "amount": 0.0, "percentage": 20.0, "pin_x": 15.0, "pin_y": 38.0},
            {"id": 4, "name": "Shopping", "icon": "🛍️", "color": "#F59E0B", "amount": 0.0, "percentage": 10.0, "pin_x": 48.0, "pin_y": 10.0},
            {"id": 5, "name": "Health", "icon": "💊", "color": "#EF4444", "amount": 0.0, "percentage": 10.0, "pin_x": 80.0, "pin_y": 25.0},
        ]
        category_list = sample_cats

    # Category Budget vs Actual Comparison
    user_categories = db.query(Category).filter(
        Category.user_id == current_user.id,
        Category.type == "expense"
    ).order_by(Category.name.asc()).all()

    budget_comparisons = []
    total_allocated_budget = 0.0
    for cat in user_categories:
        allocated = getattr(cat, "monthly_budget", 0.0) or 0.0
        spent = cat_map.get(cat.id, {}).get("amount", 0.0)
        variance = allocated - spent
        pct = round((spent / allocated * 100), 1) if allocated > 0 else (0.0 if spent == 0 else 100.0)
        total_allocated_budget += allocated

        status_class = "neutral"
        if allocated > 0:
            if spent > allocated:
                status_class = "danger"
            elif pct >= 80:
                status_class = "warning"
            else:
                status_class = "success"
        elif spent > 0:
            status_class = "unbudgeted"

        budget_comparisons.append({
            "id": cat.id,
            "name": cat.name,
            "icon": cat.icon,
            "color": cat.color,
            "allocated": allocated,
            "spent": spent,
            "variance": variance,
            "percentage": pct,
            "status": status_class
        })

    csrf_token = generate_csrf_token(current_user.id)

    return templates.TemplateResponse(
        request=request,
        name="dashboard/budgets.html",
        context={
            "user": current_user,
            "current_date": current_date,
            "is_simulated_date": is_simulated,
            "month_label": month_label,
            "current_month_str": f"{target_year:04d}-{target_month:02d}",
            "prev_month_str": prev_month_str,
            "next_month_str": next_month_str,
            "user_budget": user_budget,
            "total_spent": total_spent,
            "percentage_spent": percentage_spent,
            "remaining_budget": remaining_budget,
            "category_list": category_list,
            "user_categories": user_categories,
            "budget_comparisons": budget_comparisons,
            "total_allocated_budget": total_allocated_budget,
            "csrf_token": csrf_token
        }
    )

@router.post("/budgets/update-limit")
async def update_budget_limit(
    request: Request,
    budget_limit: float = Form(...),
    csrf_token: str = Form(...),
    month: Optional[str] = Form(None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    from app.dependencies import verify_csrf
    await verify_csrf(request, current_user)

    current_user.monthly_budget = max(100.0, float(budget_limit))
    db.commit()

    redirect_url = f"/budgets?month={month}" if month else "/budgets"
    return RedirectResponse(url=redirect_url, status_code=status.HTTP_303_SEE_OTHER)

@router.post("/budgets/category-limit")
async def update_single_category_budget(
    request: Request,
    category_id: int = Form(...),
    monthly_budget: float = Form(...),
    csrf_token: str = Form(...),
    month: Optional[str] = Form(None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    from app.dependencies import verify_csrf
    await verify_csrf(request, current_user)
    cat = db.query(Category).filter(Category.id == category_id, Category.user_id == current_user.id).first()
    if cat:
        cat.monthly_budget = max(0.0, float(monthly_budget))
        db.commit()
    redirect_url = f"/budgets?month={month}" if month else "/budgets"
    return RedirectResponse(url=redirect_url, status_code=status.HTTP_303_SEE_OTHER)

@router.post("/budgets/category-limits/bulk")
async def bulk_update_category_budgets(
    request: Request,
    csrf_token: str = Form(...),
    month: Optional[str] = Form(None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    from app.dependencies import verify_csrf
    await verify_csrf(request, current_user)
    form_data = await request.form()
    for key, value in form_data.items():
        if key.startswith("budget_cat_"):
            try:
                cid = int(key.replace("budget_cat_", ""))
                val = max(0.0, float(value))
                cat = db.query(Category).filter(Category.id == cid, Category.user_id == current_user.id).first()
                if cat:
                    cat.monthly_budget = val
            except (ValueError, TypeError):
                pass
    db.commit()
    redirect_url = f"/budgets?month={month}" if month else "/budgets"
    return RedirectResponse(url=redirect_url, status_code=status.HTTP_303_SEE_OTHER)


