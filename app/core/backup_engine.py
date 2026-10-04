import os
import json
import datetime
import re
from typing import Dict, Any, List, Optional, Tuple
from sqlalchemy.orm import Session

from app.models import (
    User, BankAccount, CreditCard, Category,
    Trip, Transaction, Notification, SystemSetting, AuditLog
)
from app.core.date_provider import DateProvider
from app.config import settings

def get_backup_dir() -> str:
    """Returns the resolved backup directory path (persistent volume aware)."""
    return settings.resolved_backup_dir

BACKUP_DIR = get_backup_dir()
MAX_BACKUP_RETENTION = 30

def get_now_utc() -> datetime.datetime:
    return datetime.datetime.now(datetime.timezone.utc).replace(tzinfo=None)

def format_file_size(size_bytes: int) -> str:
    """Format bytes to human readable string."""
    if size_bytes < 1024:
        return f"{size_bytes} B"
    elif size_bytes < 1024 * 1024:
        return f"{size_bytes / 1024:.1f} KB"
    else:
        return f"{size_bytes / (1024 * 1024):.2f} MB"

def export_full_database_json(db: Session) -> Dict[str, Any]:
    """
    Serializes all tables and entities of all users into a comprehensive,
    structured JSON payload for audit, backup, and restore capabilities.
    """
    effective_date = DateProvider.get_current_date(db)
    is_simulated = DateProvider.is_date_simulated(db)

    # 1. Users
    users = db.query(User).all()
    user_map = {u.id: u.email for u in users}
    users_data = []
    for u in users:
        users_data.append({
            "id": u.id,
            "email": u.email,
            "full_name": u.full_name,
            "hashed_password": u.hashed_password,
            "is_admin": u.is_admin,
            "is_active": u.is_active,
            "currency_symbol": u.currency_symbol,
            "created_at": u.created_at.isoformat() if u.created_at else None,
            "updated_at": u.updated_at.isoformat() if u.updated_at else None,
        })

    # 2. Categories
    categories = db.query(Category).all()
    category_map = {c.id: c.name for c in categories}
    categories_data = []
    for c in categories:
        categories_data.append({
            "id": c.id,
            "user_id": c.user_id,
            "user_email": user_map.get(c.user_id) if c.user_id else None,
            "name": c.name,
            "type": c.type,
            "icon": c.icon,
            "color": c.color,
            "is_system": c.is_system,
            "created_at": c.created_at.isoformat() if c.created_at else None,
        })

    # 3. Bank Accounts
    bank_accounts = db.query(BankAccount).all()
    bank_map = {b.id: b.bank_name for b in bank_accounts}
    banks_data = []
    for b in bank_accounts:
        banks_data.append({
            "id": b.id,
            "user_id": b.user_id,
            "user_email": user_map.get(b.user_id),
            "bank_name": b.bank_name,
            "account_name": b.account_name,
            "account_number_last4": b.account_number_last4,
            "ifsc_code": b.ifsc_code,
            "initial_balance": b.initial_balance,
            "current_balance": b.current_balance,
            "color": b.color,
            "icon": b.icon,
            "is_active": b.is_active,
            "created_at": b.created_at.isoformat() if b.created_at else None,
            "updated_at": b.updated_at.isoformat() if b.updated_at else None,
        })

    # 4. Credit Cards
    credit_cards = db.query(CreditCard).all()
    card_map = {c.id: c.card_name for c in credit_cards}
    cards_data = []
    for c in credit_cards:
        cards_data.append({
            "id": c.id,
            "user_id": c.user_id,
            "user_email": user_map.get(c.user_id),
            "bank_name": c.bank_name,
            "card_name": c.card_name,
            "card_network": c.card_network,
            "last_4_digits": c.last_4_digits,
            "total_limit": c.total_limit,
            "opening_limit": c.opening_limit,
            "available_limit": c.available_limit,
            "billing_day": c.billing_day,
            "due_day": c.due_day,
            "card_image_url": c.card_image_url,
            "card_color_gradient": c.card_color_gradient,
            "is_active": c.is_active,
            "created_at": c.created_at.isoformat() if c.created_at else None,
            "updated_at": c.updated_at.isoformat() if c.updated_at else None,
        })

    # 5. Trips
    trips = db.query(Trip).all()
    trip_map = {t.id: t.name for t in trips}
    trips_data = []
    for t in trips:
        trips_data.append({
            "id": t.id,
            "user_id": t.user_id,
            "user_email": user_map.get(t.user_id),
            "name": t.name,
            "destination": t.destination,
            "start_date": t.start_date.isoformat() if t.start_date else None,
            "end_date": t.end_date.isoformat() if t.end_date else None,
            "budget": t.budget,
            "description": t.description,
            "status": t.status,
            "color": t.color,
            "created_at": t.created_at.isoformat() if t.created_at else None,
            "updated_at": t.updated_at.isoformat() if t.updated_at else None,
        })

    # 6. Transactions
    transactions = db.query(Transaction).all()
    transactions_data = []
    for tx in transactions:
        transactions_data.append({
            "id": tx.id,
            "user_id": tx.user_id,
            "user_email": user_map.get(tx.user_id),
            "type": tx.type,
            "amount": tx.amount,
            "date": tx.date.isoformat() if tx.date else None,
            "category_id": tx.category_id,
            "category_name": category_map.get(tx.category_id),
            "bank_account_id": tx.bank_account_id,
            "bank_name": bank_map.get(tx.bank_account_id),
            "credit_card_id": tx.credit_card_id,
            "card_name": card_map.get(tx.credit_card_id),
            "trip_id": tx.trip_id,
            "trip_name": trip_map.get(tx.trip_id),
            "tag": tx.tag,
            "remarks": tx.remarks,
            "created_at": tx.created_at.isoformat() if tx.created_at else None,
            "updated_at": tx.updated_at.isoformat() if tx.updated_at else None,
        })

    # 7. Notifications
    notifications = db.query(Notification).all()
    notifications_data = []
    for n in notifications:
        notifications_data.append({
            "id": n.id,
            "user_id": n.user_id,
            "user_email": user_map.get(n.user_id),
            "title": n.title,
            "message": n.message,
            "type": n.type,
            "is_read": n.is_read,
            "link": n.link,
            "created_at": n.created_at.isoformat() if n.created_at else None,
        })

    # 8. System Settings
    settings = db.query(SystemSetting).all()
    settings_data = []
    for s in settings:
        settings_data.append({
            "id": s.id,
            "key": s.key,
            "value": s.value,
            "description": s.description,
            "updated_at": s.updated_at.isoformat() if s.updated_at else None,
        })

    total_records = (
        len(users_data) + len(categories_data) + len(banks_data) +
        len(cards_data) + len(trips_data) + len(transactions_data) +
        len(notifications_data) + len(settings_data)
    )

    return {
        "metadata": {
            "application": "FinMinimal - Personal Finance",
            "schema_version": "1.0",
            "backup_timestamp": get_now_utc().isoformat(),
            "effective_system_date": effective_date.isoformat(),
            "is_simulated_date": is_simulated,
            "total_records": total_records,
            "counts": {
                "users": len(users_data),
                "categories": len(categories_data),
                "bank_accounts": len(banks_data),
                "credit_cards": len(cards_data),
                "trips": len(trips_data),
                "transactions": len(transactions_data),
                "notifications": len(notifications_data),
                "system_settings": len(settings_data)
            }
        },
        "users": users_data,
        "categories": categories_data,
        "bank_accounts": banks_data,
        "credit_cards": cards_data,
        "trips": trips_data,
        "transactions": transactions_data,
        "notifications": notifications_data,
        "system_settings": settings_data
    }

def save_backup_to_disk(
    data: Dict[str, Any], 
    directory: Optional[str] = None, 
    max_retention: int = MAX_BACKUP_RETENTION
) -> Tuple[str, str]:
    """
    Saves a JSON snapshot file to disk, enforcing retention limit.
    Returns (filename, filepath).
    """
    if directory is None:
        directory = get_backup_dir()
    os.makedirs(directory, exist_ok=True)
    timestamp_str = get_now_utc().strftime("%Y-%m-%d_%H%M%S")
    filename = f"backup_{timestamp_str}.json"
    filepath = os.path.join(directory, filename)

    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

    # Clean old backups beyond retention limit
    cleanup_old_backups(directory, max_retention)

    return filename, filepath

def cleanup_old_backups(directory: Optional[str] = None, max_retention: int = MAX_BACKUP_RETENTION) -> None:
    """Removes older backups beyond the maximum retention limit."""
    if directory is None:
        directory = get_backup_dir()
    if not os.path.exists(directory):
        return

    files = [
        f for f in os.listdir(directory) 
        if f.startswith("backup_") and f.endswith(".json")
    ]
    files.sort()  # Alphabetical matches chronological due to YYYY-MM-DD_HHMMSS format

    if len(files) > max_retention:
        to_delete = files[:-max_retention]
        for old_file in to_delete:
            try:
                os.remove(os.path.join(directory, old_file))
            except Exception:
                pass

def sanitize_backup_filename(filename: str) -> Optional[str]:
    """Validates filename to prevent directory traversal attacks."""
    if not filename:
        return None
    basename = os.path.basename(filename.strip())
    if re.match(r"^backup_\d{4}-\d{2}-\d{2}_\d{6}\.json$", basename):
        return basename
    return None

def list_stored_backups(directory: Optional[str] = None) -> List[Dict[str, Any]]:
    """
    Lists all saved snapshot files with metadata (size, date, total records).
    """
    if directory is None:
        directory = get_backup_dir()
    if not os.path.exists(directory):
        return []

    backups = []
    for fname in os.listdir(directory):
        if not (fname.startswith("backup_") and fname.endswith(".json")):
            continue
        
        fpath = os.path.join(directory, fname)
        try:
            stat = os.stat(fpath)
            size_bytes = stat.st_size
            created_at = datetime.datetime.fromtimestamp(stat.st_mtime)

            # Try to read quick metadata from header
            records_count = None
            try:
                with open(fpath, "r", encoding="utf-8") as f:
                    # Read first 1024 bytes to inspect metadata without loading whole file
                    content_chunk = f.read(2048)
                    match = re.search(r'"total_records"\s*:\s*(\d+)', content_chunk)
                    if match:
                        records_count = int(match.group(1))
            except Exception:
                pass

            backups.append({
                "filename": fname,
                "filepath": fpath,
                "size_bytes": size_bytes,
                "size_formatted": format_file_size(size_bytes),
                "created_at": created_at,
                "total_records": records_count or 0
            })
        except Exception:
            continue

    # Sort newest first
    backups.sort(key=lambda x: x["created_at"], reverse=True)
    return backups

def delete_stored_backup(filename: str, directory: Optional[str] = None) -> bool:
    """Deletes a stored snapshot file safely."""
    if directory is None:
        directory = get_backup_dir()
    safe_name = sanitize_backup_filename(filename)
    if not safe_name:
        return False

    fpath = os.path.join(directory, safe_name)
    if os.path.exists(fpath):
        try:
            os.remove(fpath)
            return True
        except Exception:
            return False
    return False

def run_scheduled_backup_if_needed(db: Session, directory: Optional[str] = None) -> Optional[str]:
    """
    Executes a daily automated snapshot if no backup was created in the last 24 hours.
    """
    if directory is None:
        directory = get_backup_dir()
    backups = list_stored_backups(directory)
    now = datetime.datetime.now()

    if backups:
        latest = backups[0]["created_at"]
        if (now - latest).total_seconds() < 86400: # Less than 24 hours old
            return None

    # Generate new snapshot
    data = export_full_database_json(db)
    filename, _ = save_backup_to_disk(data, directory)

    # Log audit entry
    try:
        audit = AuditLog(
            user_id=None,
            action="AUTOMATED_SCHEDULED_BACKUP",
            details=f"System automated backup created snapshot: {filename}",
            ip_address="127.0.0.1",
            created_at=get_now_utc()
        )
        db.add(audit)
        db.commit()
    except Exception:
        pass

    return filename
