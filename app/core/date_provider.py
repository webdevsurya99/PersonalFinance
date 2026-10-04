import datetime
from typing import Optional
from sqlalchemy.orm import Session
from app.models import SystemSetting

SIMULATED_DATE_KEY = "simulated_system_date"

def get_now_utc() -> datetime.datetime:
    return datetime.datetime.now(datetime.timezone.utc).replace(tzinfo=None)

class DateProvider:
    """
    Centralized date provider supporting live system date and admin-simulated date.
    When an admin sets a simulated date in the Admin portal, this provider returns
    that date for default expense lodging, statement calculations, and due-date alerts.
    """
    @classmethod
    def get_current_date(cls, db: Optional[Session] = None) -> datetime.date:
        """Return the effective date (simulated date if configured in DB, else today)."""
        if db is not None:
            try:
                setting = db.query(SystemSetting).filter(SystemSetting.key == SIMULATED_DATE_KEY).first()
                if setting and setting.value:
                    # Expected format: YYYY-MM-DD
                    return datetime.datetime.strptime(setting.value.strip(), "%Y-%m-%d").date()
            except Exception:
                pass
        return datetime.date.today()

    @classmethod
    def get_current_datetime(cls, db: Optional[Session] = None) -> datetime.datetime:
        """Return the effective datetime (combining simulated date with current time if simulated)."""
        current_date = cls.get_current_date(db)
        now_time = datetime.datetime.now().time()
        return datetime.datetime.combine(current_date, now_time)

    @classmethod
    def set_simulated_date(cls, db: Session, target_date: datetime.date, admin_user_id: int) -> bool:
        """Set or update the admin simulated date."""
        setting = db.query(SystemSetting).filter(SystemSetting.key == SIMULATED_DATE_KEY).first()
        date_str = target_date.strftime("%Y-%m-%d")
        now_dt = get_now_utc()
        if not setting:
            setting = SystemSetting(
                key=SIMULATED_DATE_KEY,
                value=date_str,
                description="Simulated system date override configured by administrator",
                updated_by_user_id=admin_user_id,
                updated_at=now_dt
            )
            db.add(setting)
        else:
            setting.value = date_str
            setting.updated_by_user_id = admin_user_id
            setting.updated_at = now_dt
        db.commit()
        return True

    @classmethod
    def reset_simulated_date(cls, db: Session, admin_user_id: int) -> bool:
        """Reset to real system date by removing simulated date override."""
        setting = db.query(SystemSetting).filter(SystemSetting.key == SIMULATED_DATE_KEY).first()
        if setting:
            db.delete(setting)
            db.commit()
        return True

    @classmethod
    def is_date_simulated(cls, db: Session) -> bool:
        """Check whether system date is currently overridden."""
        setting = db.query(SystemSetting).filter(SystemSetting.key == SIMULATED_DATE_KEY).first()
        return bool(setting and setting.value)
