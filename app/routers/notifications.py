import datetime
from typing import Optional
from fastapi import APIRouter, Request, Depends, HTTPException, status
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import User, Notification, Category, BankAccount, CreditCard, Trip
from app.dependencies import get_current_user
from app.core.reminder_engine import sync_card_reminders
from app.core.date_provider import DateProvider
from app.core.security import generate_csrf_token

router = APIRouter(tags=["Notifications"])
templates = Jinja2Templates(directory="app/templates")

@router.get("/notifications", response_class=HTMLResponse)
async def notifications_page(
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    # Trigger sync of credit card reminders
    sync_card_reminders(db, current_user.id)

    notifications = db.query(Notification).filter(
        Notification.user_id == current_user.id
    ).order_by(Notification.created_at.desc()).all()

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
        name="notifications/index.html",
        context={
            "user": current_user,
            "notifications": notifications,
            "categories": categories,
            "bank_accounts": bank_accounts,
            "credit_cards": credit_cards,
            "active_trips": active_trips,
            "current_date": current_date,
            "is_simulated_date": is_simulated,
            "csrf_token": csrf_token
        }
    )

@router.get("/api/notifications/unread-count")
async def get_unread_count(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    count = db.query(Notification).filter(
        Notification.user_id == current_user.id,
        Notification.is_read == False
    ).count()
    return JSONResponse({"unread_count": count})

@router.post("/api/notifications/mark-read/{notif_id}")
async def mark_notification_read(
    notif_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    notif = db.query(Notification).filter(
        Notification.id == notif_id,
        Notification.user_id == current_user.id
    ).first()
    if notif:
        notif.is_read = True
        db.commit()
    return JSONResponse({"status": "success"})

@router.post("/api/notifications/mark-all-read")
async def mark_all_read(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    db.query(Notification).filter(
        Notification.user_id == current_user.id,
        Notification.is_read == False
    ).update({"is_read": True})
    db.commit()
    return JSONResponse({"status": "success"})

@router.post("/api/notifications/sync-reminders")
async def trigger_sync(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    alerts = sync_card_reminders(db, current_user.id)
    return JSONResponse({"status": "success", "cards_checked": len(alerts)})
