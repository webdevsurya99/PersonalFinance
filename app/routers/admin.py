import os
import json
import datetime
from typing import Optional
from fastapi import APIRouter, Request, Depends, HTTPException, status, Form, Response
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse, FileResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import User, Transaction, BankAccount, CreditCard, Trip, SystemSetting, AuditLog, Category
from app.dependencies import get_current_admin_user, verify_csrf
from app.core.date_provider import DateProvider, SIMULATED_DATE_KEY
from app.core.security import generate_csrf_token, sanitize_text
from app.core.backup_engine import (
    export_full_database_json,
    save_backup_to_disk,
    list_stored_backups,
    delete_stored_backup,
    sanitize_backup_filename,
    BACKUP_DIR
)

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

    recent_audits = db.query(AuditLog).order_by(AuditLog.created_at.desc()).limit(25).all()
    stored_backups = list_stored_backups()

    csrf_token = generate_csrf_token(current_admin.id)

    categories = db.query(Category).filter(
        (Category.user_id == current_admin.id) | (Category.is_system == True)
    ).order_by(Category.name.asc()).all()
    user_banks = db.query(BankAccount).filter(BankAccount.user_id == current_admin.id, BankAccount.is_active == True).all()
    user_cards = db.query(CreditCard).filter(CreditCard.user_id == current_admin.id, CreditCard.is_active == True).all()
    active_trips = db.query(Trip).filter(Trip.user_id == current_admin.id, Trip.status.in_(["active", "planned"])).all()

    return templates.TemplateResponse(
        request=request,
        name="admin/index.html",
        context={
            "user": current_admin,
            "current_date": current_date,
            "is_simulated": is_simulated,
            "is_simulated_date": is_simulated,
            "real_system_date": real_system_date,
            "total_users": total_users,
            "total_txns": total_txns,
            "total_bank_accounts": total_bank_accounts,
            "total_credit_cards": total_credit_cards,
            "total_trips": total_trips,
            "users": users,
            "recent_audits": recent_audits,
            "stored_backups": stored_backups,
            "categories": categories,
            "bank_accounts": user_banks,
            "credit_cards": user_cards,
            "active_trips": active_trips,
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

# ----------------- Database Backup & Snapshots -----------------

@router.get("/admin/backup/download-now")
async def download_live_backup(
    request: Request,
    current_admin: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
):
    """
    Generates a full real-time database JSON export and downloads it directly to the browser.
    """
    data = export_full_database_json(db)
    timestamp_str = get_now_utc().strftime("%Y-%m-%d_%H%M%S")
    filename = f"finminimal_full_backup_{timestamp_str}.json"
    json_bytes = json.dumps(data, indent=2, ensure_ascii=False).encode("utf-8")

    # Log audit
    audit = AuditLog(
        user_id=current_admin.id,
        action="ADMIN_BACKUP_LIVE_DOWNLOAD",
        details=f"Admin generated and downloaded full JSON backup ({len(json_bytes)} bytes, {data['metadata']['total_records']} records)",
        ip_address=request.client.host if request.client else "127.0.0.1",
        created_at=get_now_utc()
    )
    db.add(audit)
    db.commit()

    return Response(
        content=json_bytes,
        media_type="application/json",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
            "Content-Type": "application/json; charset=utf-8"
        }
    )

@router.post("/admin/backup/create")
async def create_backup_snapshot(
    request: Request,
    csrf_token: str = Form(...),
    current_admin: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
):
    """
    Creates a new timestamped JSON backup snapshot stored locally on the server in backups/
    """
    await verify_csrf(request, current_admin)

    data = export_full_database_json(db)
    filename, _ = save_backup_to_disk(data)

    # Log audit
    audit = AuditLog(
        user_id=current_admin.id,
        action="ADMIN_BACKUP_SNAPSHOT_CREATE",
        details=f"Admin created stored server backup snapshot: {filename} ({data['metadata']['total_records']} records)",
        ip_address=request.client.host if request.client else "127.0.0.1",
        created_at=get_now_utc()
    )
    db.add(audit)
    db.commit()

    return RedirectResponse(url="/admin", status_code=status.HTTP_303_SEE_OTHER)

@router.get("/admin/backup/download/{filename}")
async def download_stored_backup(
    filename: str,
    request: Request,
    current_admin: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
):
    """
    Downloads a previously generated stored backup file from backups/
    """
    safe_name = sanitize_backup_filename(filename)
    if not safe_name:
        raise HTTPException(status_code=400, detail="Invalid backup filename.")

    filepath = os.path.join(BACKUP_DIR, safe_name)
    if not os.path.exists(filepath):
        raise HTTPException(status_code=404, detail="Backup snapshot file not found.")

    # Log audit
    audit = AuditLog(
        user_id=current_admin.id,
        action="ADMIN_BACKUP_DOWNLOAD",
        details=f"Admin downloaded stored snapshot: {safe_name}",
        ip_address=request.client.host if request.client else "127.0.0.1",
        created_at=get_now_utc()
    )
    db.add(audit)
    db.commit()

    return FileResponse(
        path=filepath,
        filename=safe_name,
        media_type="application/json"
    )

@router.post("/admin/backup/delete/{filename}")
async def delete_backup(
    filename: str,
    request: Request,
    csrf_token: str = Form(...),
    current_admin: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
):
    """
    Deletes a stored snapshot file from backups/
    """
    await verify_csrf(request, current_admin)

    safe_name = sanitize_backup_filename(filename)
    if not safe_name:
        raise HTTPException(status_code=400, detail="Invalid backup filename.")

    success = delete_stored_backup(safe_name)
    if not success:
        raise HTTPException(status_code=404, detail="Backup file could not be deleted or not found.")

    # Log audit
    audit = AuditLog(
        user_id=current_admin.id,
        action="ADMIN_BACKUP_DELETE",
        details=f"Admin deleted stored backup snapshot: {safe_name}",
        ip_address=request.client.host if request.client else "127.0.0.1",
        created_at=get_now_utc()
    )
    db.add(audit)
    db.commit()

    return RedirectResponse(url="/admin", status_code=status.HTTP_303_SEE_OTHER)
