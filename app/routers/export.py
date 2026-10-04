import datetime
import calendar
from typing import Optional, Any
from fastapi import APIRouter, Request, Depends, HTTPException, Query
from fastapi.responses import HTMLResponse, StreamingResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import User, Transaction, Category, BankAccount, CreditCard, Trip, AuditLog
from app.dependencies import get_current_user
from app.core.date_provider import DateProvider
from app.core.exporter_excel import generate_excel_statement
from app.core.exporter_pdf import generate_pdf_statement
from app.routers.dashboard import get_date_range_for_period

router = APIRouter(tags=["Statement Export"])
templates = Jinja2Templates(directory="app/templates")

def get_now_utc() -> datetime.datetime:
    return datetime.datetime.now(datetime.timezone.utc).replace(tzinfo=None)

def parse_optional_int(val: Optional[Any]) -> Optional[int]:
    if val is None:
        return None
    if isinstance(val, int):
        return val
    val_str = str(val).strip()
    if not val_str:
        return None
    try:
        return int(val_str)
    except (ValueError, TypeError):
        return None

def query_export_transactions(
    db: Session,
    user_id: int,
    period: str,
    start_date_str: Optional[str],
    end_date_str: Optional[str],
    type_filter: Optional[str] = None,
    category_id: Optional[int] = None,
    account_id: Optional[int] = None,
    card_id: Optional[int] = None,
    trip_id: Optional[int] = None
) -> tuple[list[Transaction], datetime.date, datetime.date]:
    """Helper to query transactions for statement generation."""
    ref_date = DateProvider.get_current_date(db)
    start_dt, end_dt = get_date_range_for_period(period, ref_date, start_date_str, end_date_str)

    query = db.query(Transaction).filter(
        Transaction.user_id == user_id,
        Transaction.date >= start_dt,
        Transaction.date <= end_dt
    )

    if type_filter in ("expense", "income"):
        query = query.filter(Transaction.type == type_filter)
    if category_id:
        query = query.filter(Transaction.category_id == category_id)
    if account_id:
        query = query.filter(Transaction.bank_account_id == account_id)
    if card_id:
        query = query.filter(Transaction.credit_card_id == card_id)
    if trip_id:
        query = query.filter(Transaction.trip_id == trip_id)

    txns = query.order_by(Transaction.date.desc(), Transaction.id.desc()).all()
    return txns, start_dt, end_dt

@router.get("/export", response_class=HTMLResponse)
async def export_hub_page(
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    categories = db.query(Category).filter(
        (Category.user_id == current_user.id) | (Category.is_system == True)
    ).order_by(Category.name.asc()).all()

    bank_accounts = db.query(BankAccount).filter(BankAccount.user_id == current_user.id, BankAccount.is_active == True).all()
    credit_cards = db.query(CreditCard).filter(CreditCard.user_id == current_user.id, CreditCard.is_active == True).all()
    trips = db.query(Trip).filter(Trip.user_id == current_user.id).order_by(Trip.start_date.desc()).all()

    active_trips = [t for t in trips if t.status in ("active", "planned")]
    current_date = DateProvider.get_current_date(db)
    is_simulated = DateProvider.is_date_simulated(db)
    from app.core.security import generate_csrf_token
    csrf_token = generate_csrf_token(current_user.id)

    return templates.TemplateResponse(
        request=request,
        name="export/index.html",
        context={
            "user": current_user,
            "categories": categories,
            "bank_accounts": bank_accounts,
            "credit_cards": credit_cards,
            "trips": trips,
            "active_trips": active_trips,
            "current_date": current_date,
            "is_simulated_date": is_simulated,
            "csrf_token": csrf_token
        }
    )

@router.get("/export/excel")
async def export_excel_download(
    period: str = Query("this_month"),
    start_date: Optional[str] = Query(None),
    end_date: Optional[str] = Query(None),
    type: Optional[str] = Query(None),
    category_id: Optional[str] = Query(None),
    account_id: Optional[str] = Query(None),
    card_id: Optional[str] = Query(None),
    trip_id: Optional[str] = Query(None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    cat_id = parse_optional_int(category_id)
    acc_id = parse_optional_int(account_id)
    c_id = parse_optional_int(card_id)
    tr_id = parse_optional_int(trip_id)
    t_filter = type.strip() if type and type.strip() in ("expense", "income") else None

    txns, start_dt, end_dt = query_export_transactions(
        db, current_user.id, period, start_date, end_date,
        type_filter=t_filter, category_id=cat_id,
        account_id=acc_id, card_id=c_id, trip_id=tr_id
    )

    excel_stream = generate_excel_statement(txns, current_user, start_dt, end_dt)
    filename = f"Statement_{start_dt.strftime('%Y%m%d')}_{end_dt.strftime('%Y%m%d')}.xlsx"

    # Audit log
    audit = AuditLog(
        user_id=current_user.id,
        action="EXPORT_EXCEL",
        details=f"Exported Excel statement ({len(txns)} records, {start_dt} to {end_dt})",
        created_at=get_now_utc()
    )
    db.add(audit)
    db.commit()

    return StreamingResponse(
        excel_stream,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'}
    )

@router.get("/export/pdf")
async def export_pdf_download(
    period: str = Query("this_month"),
    start_date: Optional[str] = Query(None),
    end_date: Optional[str] = Query(None),
    type: Optional[str] = Query(None),
    category_id: Optional[str] = Query(None),
    account_id: Optional[str] = Query(None),
    card_id: Optional[str] = Query(None),
    trip_id: Optional[str] = Query(None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    cat_id = parse_optional_int(category_id)
    acc_id = parse_optional_int(account_id)
    c_id = parse_optional_int(card_id)
    tr_id = parse_optional_int(trip_id)
    t_filter = type.strip() if type and type.strip() in ("expense", "income") else None

    txns, start_dt, end_dt = query_export_transactions(
        db, current_user.id, period, start_date, end_date,
        type_filter=t_filter, category_id=cat_id,
        account_id=acc_id, card_id=c_id, trip_id=tr_id
    )

    pdf_stream = generate_pdf_statement(txns, current_user, start_dt, end_dt)
    filename = f"Statement_{start_dt.strftime('%Y%m%d')}_{end_dt.strftime('%Y%m%d')}.pdf"

    # Audit log
    audit = AuditLog(
        user_id=current_user.id,
        action="EXPORT_PDF",
        details=f"Exported PDF statement ({len(txns)} records, {start_dt} to {end_dt})",
        created_at=get_now_utc()
    )
    db.add(audit)
    db.commit()

    return StreamingResponse(
        pdf_stream,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'}
    )

