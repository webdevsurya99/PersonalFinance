import os
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.responses import RedirectResponse
from slowapi.errors import RateLimitExceeded
from sqlalchemy.orm import Session

from app.config import settings
from app.database import engine, Base, SessionLocal
from app.models import User
from app.core.security import hash_password, SecurityHeadersMiddleware
from app.core.rate_limiter import limiter, rate_limit_exceeded_handler
from app.routers import (
    auth, dashboard, transactions, accounts, categories,
    trips, export, notifications, admin, pwa
)

from app.core.backup_engine import run_scheduled_backup_if_needed

def init_db():
    """Create database tables and default admin if missing."""
    Base.metadata.create_all(bind=engine)
    
    # Safe column migrations
    from sqlalchemy import text
    for col_sql, fallback_sql in [
        ("ALTER TABLE users ADD COLUMN IF NOT EXISTS monthly_budget FLOAT DEFAULT 25000.0", "ALTER TABLE users ADD COLUMN monthly_budget FLOAT DEFAULT 25000.0"),
        ("ALTER TABLE users ADD COLUMN IF NOT EXISTS cash_balance FLOAT DEFAULT 0.0", "ALTER TABLE users ADD COLUMN cash_balance FLOAT DEFAULT 0.0"),
        ("ALTER TABLE categories ADD COLUMN IF NOT EXISTS monthly_budget FLOAT DEFAULT 0.0", "ALTER TABLE categories ADD COLUMN monthly_budget FLOAT DEFAULT 0.0"),
    ]:
        try:
            with engine.begin() as conn:
                conn.execute(text(col_sql))
        except Exception:
            try:
                with engine.begin() as conn:
                    conn.execute(text(fallback_sql))
            except Exception:
                pass

    db: Session = SessionLocal()
    try:
        admin_user = db.query(User).filter(User.is_admin == True).first()
        if not admin_user:
            admin_user = User(
                email=settings.ADMIN_DEFAULT_EMAIL,
                full_name=settings.ADMIN_DEFAULT_NAME,
                hashed_password=hash_password(settings.ADMIN_DEFAULT_PASSWORD),
                is_admin=True,
                is_active=True,
                currency_symbol=settings.DEFAULT_CURRENCY_SYMBOL,
                cash_balance=0.0
            )
            db.add(admin_user)
            db.commit()
            db.refresh(admin_user)
            
            # Seed default categories for admin
            auth.initialize_default_categories(db, admin_user)
            print(f"[INIT] Created default admin account: {settings.ADMIN_DEFAULT_EMAIL}")

        # Automatic category repair and deduplication
        from app.models import Category, Transaction
        from app.core.presets import DEFAULT_CATEGORIES
        preset_map = {c["name"].strip().lower(): c for c in DEFAULT_CATEGORIES}

        users = db.query(User).all()
        for u in users:
            user_cats = db.query(Category).filter(Category.user_id == u.id).order_by(Category.id.asc()).all()
            seen = {}
            for cat in user_cats:
                key = (cat.name.strip().lower(), cat.type)
                if key in seen:
                    primary = seen[key]
                    db.query(Transaction).filter(
                        Transaction.user_id == u.id,
                        Transaction.category_id == cat.id
                    ).update({"category_id": primary.id}, synchronize_session=False)
                    db.delete(cat)
                else:
                    seen[key] = cat
                    if not cat.icon or cat.icon.strip() == "" or cat.icon == "tag":
                        if key[0] in preset_map:
                            cat.icon = preset_map[key[0]]["icon"]
                            if not cat.color or cat.color == "#6366F1":
                                cat.color = preset_map[key[0]]["color"]
        db.commit()

        # Check and run scheduled daily backup snapshot if needed
        snap = run_scheduled_backup_if_needed(db)
        if snap:
            print(f"[BACKUP] Automated scheduled daily backup created: {snap}")
    finally:
        db.close()

import asyncio

async def periodic_backup_worker():
    """Background task running every 6 hours to ensure automated backups."""
    while True:
        await asyncio.sleep(6 * 3600)
        try:
            db = SessionLocal()
            run_scheduled_backup_if_needed(db)
            db.close()
        except Exception:
            pass

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    init_db()
    backup_task = asyncio.create_task(periodic_backup_worker())
    yield
    # Shutdown
    backup_task.cancel()

app = FastAPI(
    title=settings.APP_NAME,
    description="Minimalistic Personal Finance & Credit Card Management System",
    version="1.0.0",
    docs_url="/docs" if settings.DEBUG else None,
    redoc_url="/redoc" if settings.DEBUG else None,
    lifespan=lifespan
)

# Rate Limiter setup
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, rate_limit_exceeded_handler)

# OWASP Security Headers Middleware
app.add_middleware(SecurityHeadersMiddleware)

# Mount Static Files
os.makedirs("app/static", exist_ok=True)
app.mount("/static", StaticFiles(directory="app/static"), name="static")

# Register Routers
app.include_router(pwa.router)
app.include_router(auth.router)
app.include_router(dashboard.router)
app.include_router(transactions.router)
app.include_router(accounts.router)
app.include_router(categories.router)
app.include_router(trips.router)
app.include_router(export.router)
app.include_router(notifications.router)
app.include_router(admin.router)
