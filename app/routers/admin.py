import datetime
from typing import Optional
from fastapi import APIRouter, Request, Depends, HTTPException, status, Form
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import User, Transaction, BankAccount, CreditCard, Trip, SystemSetting, AuditLog
from app.dependencies import get_current_admin_user, verify_csrf
from app.core.date_provider import DateProvider, SIMULATED_DATE_KEY
from app.core.security import generate_csrf_token, sanitize_text

router = APIRouter(tags=["Admin"])
templates = Jinja2Templates(directory="app/templates")

def get_now_utc() -> datetime.datetime:
    return datetime.datetime.now(datetime.timezone.utc).replace(tzinfo=None)

@router.get("/admin", response_class=HTMLResponse)
async def admin_portal(
    request: Request,
    current_admin: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
):
    current_date = DateProvider.get_current_date(db)
    is_simulated = DateProvider.is_date_simulated(db)
    real_system_date = datetime.date.today()

    users = db.query(User).order_by(User.created_at.desc()).all()
    total_users = len(users)
    total_txns = db.query(Transaction).count()
    total_bank_accounts = db.query(BankAccount).count()
    total_credit_cards = db.query(CreditCard).count()
    total_trips = db.query(Trip).count()

    recent_audits = db.query(AuditLog).order_by(AuditLog.created_at.desc()).limit(20).all()

    csrf_token = generate_csrf_token(current_admin.id)

    return templates.TemplateResponse(
        request=request,
        name="admin/index.html",
        context={
            "user": current_admin,
            "current_date": current_date,
            "is_simulated": is_simulated,
            "real_system_date": real_system_date,
            "total_users": total_users,
            "total_txns": total_txns,
            "total_bank_accounts": total_bank_accounts,
            "total_credit_cards": total_credit_cards,
            "total_trips": total_trips,
            "users": users,
            "recent_audits": recent_audits,
            "csrf_token": csrf_token
        }
    )

@router.post("/admin/date-override")
async def override_date(
    request: Request,
    target_date: str = Form(...),
    csrf_token: str = Form(...),
    current_admin: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
):
    await verify_csrf(request, current_admin)

    try:
        t_date = datetime.datetime.strptime(target_date, "%Y-%m-%d").date()
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid target date format. Expected YYYY-MM-DD.")

    DateProvider.set_simulated_date(db, t_date, current_admin.id)

    # Log audit
    audit = AuditLog(
        user_id=current_admin.id,
        action="ADMIN_DATE_OVERRIDE",
        details=f"Admin overridden system date to {t_date}",
        ip_address=request.client.host if request.client else "127.0.0.1",
        created_at=get_now_utc()
    )
    db.add(audit)
    db.commit()

    return RedirectResponse(url="/admin", status_code=status.HTTP_303_SEE_OTHER)

@router.post("/admin/reset-date")
async def reset_date(
    request: Request,
    csrf_token: str = Form(...),
    current_admin: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
):
    await verify_csrf(request, current_admin)

    DateProvider.reset_simulated_date(db, current_admin.id)

    # Log audit
    audit = AuditLog(
        user_id=current_admin.id,
        action="ADMIN_DATE_RESET",
        details="Admin reset system date override to real system time",
        ip_address=request.client.host if request.client else "127.0.0.1",
        created_at=get_now_utc()
    )
    db.add(audit)
    db.commit()

    return RedirectResponse(url="/admin", status_code=status.HTTP_303_SEE_OTHER)

@router.post("/admin/users/{user_id}/toggle-status")
async def toggle_user_status(
    request: Request,
    user_id: int,
    csrf_token: str = Form(...),
    current_admin: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
):
    await verify_csrf(request, current_admin)

    target_user = db.query(User).filter(User.id == user_id).first()
    if not target_user:
        raise HTTPException(status_code=404, detail="User not found.")

    if target_user.id == current_admin.id:
        raise HTTPException(status_code=400, detail="Cannot deactivate your own admin account.")

    target_user.is_active = not target_user.is_active
    db.commit()

    return RedirectResponse(url="/admin", status_code=status.HTTP_303_SEE_OTHER)
