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

def init_db():
    """Create database tables and default admin if missing."""
    Base.metadata.create_all(bind=engine)
    
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
                currency_symbol=settings.DEFAULT_CURRENCY_SYMBOL
            )
            db.add(admin_user)
            db.commit()
            db.refresh(admin_user)
            
            # Seed default categories for admin
            auth.initialize_default_categories(db, admin_user)
            print(f"[INIT] Created default admin account: {settings.ADMIN_DEFAULT_EMAIL}")
    finally:
        db.close()

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    init_db()
    yield
    # Shutdown

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
