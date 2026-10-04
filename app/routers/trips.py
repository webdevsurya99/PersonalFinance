import datetime
from typing import Optional
from fastapi import APIRouter, Request, Depends, HTTPException, status, Form
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import User, Trip, Transaction, Category, BankAccount, CreditCard
from app.dependencies import get_current_user, verify_csrf
from app.core.date_provider import DateProvider
from app.core.security import generate_csrf_token, sanitize_text

router = APIRouter(tags=["Trips"])
templates = Jinja2Templates(directory="app/templates")

def get_now_utc() -> datetime.datetime:
    return datetime.datetime.now(datetime.timezone.utc).replace(tzinfo=None)

@router.get("/trips", response_class=HTMLResponse)
async def trips_list_page(
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    trips = db.query(Trip).filter(Trip.user_id == current_user.id).order_by(Trip.start_date.desc()).all()

    trips_data = []
    for trip in trips:
        spent = sum(t.amount for t in trip.transactions if t.type == "expense")
        spent_pct = round((spent / trip.budget * 100) if trip.budget > 0 else 0, 1)
        remaining = max(0.0, trip.budget - spent)
        trips_data.append({
            "trip": trip,
            "spent": spent,
            "spent_pct": min(spent_pct, 100.0),
            "raw_spent_pct": spent_pct,
            "remaining": remaining,
            "is_overbudget": spent > trip.budget if trip.budget > 0 else False
        })

    categories = db.query(Category).filter(
        (Category.user_id == current_user.id) | (Category.is_system == True)
    ).order_by(Category.name.asc()).all()
    bank_accounts = db.query(BankAccount).filter(BankAccount.user_id == current_user.id, BankAccount.is_active == True).all()
    credit_cards = db.query(CreditCard).filter(CreditCard.user_id == current_user.id, CreditCard.is_active == True).all()
    active_trips = db.query(Trip).filter(Trip.user_id == current_user.id, Trip.status.in_(["active", "planned"])).all()

    current_date = DateProvider.get_current_date(db)
    is_simulated = DateProvider.is_date_simulated(db)
    csrf_token = generate_csrf_token(current_user.id)

    return templates.TemplateResponse(
        request=request,
        name="trips/index.html",
        context={
            "user": current_user,
            "trips_data": trips_data,
            "categories": categories,
            "bank_accounts": bank_accounts,
            "credit_cards": credit_cards,
            "active_trips": active_trips,
            "current_date": current_date,
            "is_simulated_date": is_simulated,
            "csrf_token": csrf_token
        }
    )

@router.post("/trips/new")
async def create_trip(
    request: Request,
    name: str = Form(...),
    destination: str = Form(...),
    start_date: str = Form(...),
    end_date: str = Form(...),
    budget: float = Form(0.0),
    description: Optional[str] = Form(None),
    status: str = Form("active"),
    color: Optional[str] = Form("#06B6D4"),
    csrf_token: str = Form(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    await verify_csrf(request, current_user)

    try:
        s_dt = datetime.datetime.strptime(start_date, "%Y-%m-%d").date()
        e_dt = datetime.datetime.strptime(end_date, "%Y-%m-%d").date()
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid date format.")

    trip = Trip(
        user_id=current_user.id,
        name=sanitize_text(name),
        destination=sanitize_text(destination),
        start_date=s_dt,
        end_date=e_dt,
        budget=budget,
        description=sanitize_text(description),
        status=status if status in ("planned", "active", "completed") else "active",
        color=color or "#06B6D4",
        created_at=get_now_utc()
    )
    db.add(trip)
    db.commit()

    return RedirectResponse(url=f"/trips/{trip.id}", status_code=303)

@router.get("/trips/{trip_id}", response_class=HTMLResponse)
async def trip_detail_page(
    request: Request,
    trip_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    trip = db.query(Trip).filter(Trip.id == trip_id, Trip.user_id == current_user.id).first()
    if not trip:
        raise HTTPException(status_code=404, detail="Trip not found.")

    txns = db.query(Transaction).filter(
        Transaction.user_id == current_user.id,
        Transaction.trip_id == trip_id
    ).order_by(Transaction.date.desc(), Transaction.id.desc()).all()

    total_spent = sum(t.amount for t in txns if t.type == "expense")
    total_refund = sum(t.amount for t in txns if t.type == "income")
    net_spent = total_spent - total_refund
    spent_pct = round((net_spent / trip.budget * 100) if trip.budget > 0 else 0, 1)

    cat_breakdown = {}
    for t in txns:
        if t.type == "expense":
            c_name = t.category.name if t.category else "Other"
            c_icon = t.category.icon if t.category else "📦"
            c_color = t.category.color if t.category else "#94A3B8"
            if c_name not in cat_breakdown:
                cat_breakdown[c_name] = {"name": c_name, "icon": c_icon, "color": c_color, "amount": 0.0}
            cat_breakdown[c_name]["amount"] += t.amount

    categories = db.query(Category).filter(
        (Category.user_id == current_user.id) | (Category.is_system == True)
    ).order_by(Category.name.asc()).all()

    bank_accounts = db.query(BankAccount).filter(BankAccount.user_id == current_user.id, BankAccount.is_active == True).all()
    credit_cards = db.query(CreditCard).filter(CreditCard.user_id == current_user.id, CreditCard.is_active == True).all()
    active_trips = db.query(Trip).filter(Trip.user_id == current_user.id, Trip.status.in_(["active", "planned"])).all()

    current_date = DateProvider.get_current_date(db)
    is_simulated = DateProvider.is_date_simulated(db)
    csrf_token = generate_csrf_token(current_user.id)

    return templates.TemplateResponse(
        request=request,
        name="trips/detail.html",
        context={
            "user": current_user,
            "trip": trip,
            "transactions": txns,
            "total_spent": total_spent,
            "net_spent": net_spent,
            "spent_pct": spent_pct,
            "cat_breakdown": list(cat_breakdown.values()),
            "categories": categories,
            "bank_accounts": bank_accounts,
            "credit_cards": credit_cards,
            "active_trips": active_trips,
            "current_date": current_date,
            "is_simulated_date": is_simulated,
            "csrf_token": csrf_token
        }
    )

@router.post("/trips/{trip_id}/edit")
async def edit_trip(
    request: Request,
    trip_id: int,
    name: str = Form(...),
    destination: str = Form(...),
    start_date: str = Form(...),
    end_date: str = Form(...),
    budget: float = Form(0.0),
    description: Optional[str] = Form(None),
    status: str = Form("active"),
    color: Optional[str] = Form("#06B6D4"),
    csrf_token: str = Form(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    await verify_csrf(request, current_user)

    trip = db.query(Trip).filter(Trip.id == trip_id, Trip.user_id == current_user.id).first()
    if not trip:
        raise HTTPException(status_code=404, detail="Trip not found.")

    try:
        s_dt = datetime.datetime.strptime(start_date, "%Y-%m-%d").date()
        e_dt = datetime.datetime.strptime(end_date, "%Y-%m-%d").date()
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid date format.")

    trip.name = sanitize_text(name)
    trip.destination = sanitize_text(destination)
    trip.start_date = s_dt
    trip.end_date = e_dt
    trip.budget = budget
    trip.description = sanitize_text(description)
    trip.status = status if status in ("planned", "active", "completed") else "active"
    trip.color = color or "#06B6D4"
    trip.updated_at = get_now_utc()

    db.commit()
    return RedirectResponse(url=f"/trips/{trip.id}", status_code=303)

@router.post("/trips/{trip_id}/delete")
async def delete_trip(
    request: Request,
    trip_id: int,
    csrf_token: str = Form(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    await verify_csrf(request, current_user)

    trip = db.query(Trip).filter(Trip.id == trip_id, Trip.user_id == current_user.id).first()
    if not trip:
        raise HTTPException(status_code=404, detail="Trip not found.")

    db.query(Transaction).filter(Transaction.trip_id == trip_id).update({"trip_id": None})

    db.delete(trip)
    db.commit()

    return RedirectResponse(url="/trips", status_code=303)
