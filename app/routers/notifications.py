import datetime
from typing import Optional
from fastapi import APIRouter, Request, Depends, HTTPException, status
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import User, Notification
from app.dependencies import get_current_user
from app.core.reminder_engine import sync_card_reminders
from app.core.date_provider import DateProvider

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

    current_date = DateProvider.get_current_date(db)

    return templates.TemplateResponse(
        request=request,
        name="notifications/index.html",
        context={
            "user": current_user,
            "notifications": notifications,
            "current_date": current_date
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
