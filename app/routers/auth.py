import datetime
from fastapi import APIRouter, Request, Depends, HTTPException, status, Form, Response
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.models import User, Category, AuditLog
from app.core.security import hash_password, verify_password, create_access_token, generate_csrf_token, sanitize_text
from app.core.rate_limiter import limiter
from app.core.presets import DEFAULT_CATEGORIES
from app.dependencies import get_current_user_optional, get_current_user

router = APIRouter(tags=["Authentication"])
templates = Jinja2Templates(directory="app/templates")

def get_now_utc() -> datetime.datetime:
    return datetime.datetime.now(datetime.timezone.utc).replace(tzinfo=None)

def initialize_default_categories(db: Session, user: User):
    """Seed initial categories for newly registered user."""
    for cat in DEFAULT_CATEGORIES:
        category = Category(
            user_id=user.id,
            name=cat["name"],
            type=cat["type"],
            icon=cat["icon"],
            color=cat["color"],
            is_system=True
        )
        db.add(category)
    db.commit()

@router.get("/register", response_class=HTMLResponse)
async def register_page(
    request: Request,
    user: User = Depends(get_current_user_optional)
):
    if user:
        return RedirectResponse(url="/dashboard", status_code=status.HTTP_302_FOUND)
    return templates.TemplateResponse(
        request=request,
        name="auth/register.html",
        context={"user": None, "error": None}
    )

@router.post("/register", response_class=HTMLResponse)
@limiter.limit(settings.RATE_LIMIT_LOGIN)
async def register_submit(
    request: Request,
    full_name: str = Form(...),
    email: str = Form(...),
    password: str = Form(...),
    confirm_password: str = Form(...),
    currency_symbol: str = Form("₹"),
    db: Session = Depends(get_db)
):
    full_name = sanitize_text(full_name)
    email = email.lower().strip()
    
    # Validation
    if not full_name or len(full_name) < 2:
        return templates.TemplateResponse(
            request=request,
            name="auth/register.html",
            context={"user": None, "error": "Full name must be at least 2 characters.", "email": email, "full_name": full_name}
        )
    
    if password != confirm_password:
        return templates.TemplateResponse(
            request=request,
            name="auth/register.html",
            context={"user": None, "error": "Passwords do not match.", "email": email, "full_name": full_name}
        )
        
    if len(password) < 8 or not any(c.isdigit() for c in password) or not any(c.isalpha() for c in password):
        return templates.TemplateResponse(
            request=request,
            name="auth/register.html",
            context={"user": None, "error": "Password must be at least 8 characters and contain both letters and numbers.", "email": email, "full_name": full_name}
        )

    existing_user = db.query(User).filter(User.email == email).first()
    if existing_user:
        return templates.TemplateResponse(
            request=request,
            name="auth/register.html",
            context={"user": None, "error": "An account with this email already exists.", "email": email, "full_name": full_name}
        )

    # Check if first user in system (make admin if first)
    user_count = db.query(User).count()
    is_admin = (user_count == 0)

    hashed = hash_password(password)
    new_user = User(
        email=email,
        full_name=full_name,
        hashed_password=hashed,
        is_admin=is_admin,
        currency_symbol=currency_symbol or "₹",
        created_at=get_now_utc()
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    # Initialize default categories
    initialize_default_categories(db, new_user)

    # Audit log
    audit = AuditLog(
        user_id=new_user.id,
        action="USER_REGISTER",
        details=f"User registered with email: {email}",
        ip_address=request.client.host if request.client else "127.0.0.1",
        created_at=get_now_utc()
    )
    db.add(audit)
    db.commit()

    # Create session token
    token = create_access_token(data={"sub": str(new_user.id), "email": new_user.email})
    response = RedirectResponse(url="/dashboard", status_code=status.HTTP_303_SEE_OTHER)
    response.set_cookie(
        key=settings.SESSION_COOKIE_NAME,
        value=token,
        httponly=True,
        secure=settings.SECURE_COOKIES,
        samesite="lax",
        max_age=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60
    )
    return response

@router.get("/login", response_class=HTMLResponse)
async def login_page(
    request: Request,
    user: User = Depends(get_current_user_optional),
    next: str = "/dashboard"
):
    if user:
        return RedirectResponse(url=next, status_code=status.HTTP_302_FOUND)
    return templates.TemplateResponse(
        request=request,
        name="auth/login.html",
        context={"user": None, "error": None, "next": next}
    )

@router.post("/login", response_class=HTMLResponse)
@limiter.limit(settings.RATE_LIMIT_LOGIN)
async def login_submit(
    request: Request,
    email: str = Form(...),
    password: str = Form(...),
    next: str = Form("/dashboard"),
    db: Session = Depends(get_db)
):
    email = email.lower().strip()
    user = db.query(User).filter(User.email == email).first()

    if not user or not verify_password(password, user.hashed_password):
        return templates.TemplateResponse(
            request=request,
            name="auth/login.html",
            context={"user": None, "error": "Invalid email or password.", "email": email, "next": next},
            status_code=status.HTTP_400_BAD_REQUEST
        )

    if not user.is_active:
        return templates.TemplateResponse(
            request=request,
            name="auth/login.html",
            context={"user": None, "error": "Your account has been deactivated. Please contact administrator.", "email": email, "next": next},
            status_code=status.HTTP_403_FORBIDDEN
        )

    # Audit log
    audit = AuditLog(
        user_id=user.id,
        action="USER_LOGIN",
        details="User logged in successfully",
        ip_address=request.client.host if request.client else "127.0.0.1",
        created_at=get_now_utc()
    )
    db.add(audit)
    db.commit()

    token = create_access_token(data={"sub": str(user.id), "email": user.email})
    target_url = next if (next and next.startswith("/") and not next.startswith("//")) else "/dashboard"
    response = RedirectResponse(url=target_url, status_code=status.HTTP_303_SEE_OTHER)
    response.set_cookie(
        key=settings.SESSION_COOKIE_NAME,
        value=token,
        httponly=True,
        secure=settings.SECURE_COOKIES,
        samesite="lax",
        max_age=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60
    )
    return response

@router.get("/logout")
@router.post("/logout")
async def logout(request: Request):
    response = RedirectResponse(url="/login", status_code=status.HTTP_303_SEE_OTHER)
    response.delete_cookie(key=settings.SESSION_COOKIE_NAME)
    return response

@router.get("/profile", response_class=HTMLResponse)
async def profile_page(
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    csrf_token = generate_csrf_token(current_user.id)
    return templates.TemplateResponse(
        request=request,
        name="auth/profile.html",
        context={"user": current_user, "csrf_token": csrf_token, "message": None, "error": None}
    )

@router.post("/profile", response_class=HTMLResponse)
async def profile_update(
    request: Request,
    full_name: str = Form(...),
    currency_symbol: str = Form("₹"),
    current_password: str = Form(None),
    new_password: str = Form(None),
    confirm_new_password: str = Form(None),
    csrf_token: str = Form(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    new_csrf = generate_csrf_token(current_user.id)
    current_user.full_name = sanitize_text(full_name)
    current_user.currency_symbol = currency_symbol or "₹"

    message = "Profile updated successfully."
    error = None

    if new_password:
        if not current_password or not verify_password(current_password, current_user.hashed_password):
            error = "Current password is incorrect."
        elif new_password != confirm_new_password:
            error = "New passwords do not match."
        elif len(new_password) < 8 or not any(c.isdigit() for c in new_password) or not any(c.isalpha() for c in new_password):
            error = "New password must be at least 8 characters and contain both letters and numbers."
        else:
            current_user.hashed_password = hash_password(new_password)
            message = "Profile and password updated successfully."

    if not error:
        current_user.updated_at = get_now_utc()
        db.commit()

    return templates.TemplateResponse(
        request=request,
        name="auth/profile.html",
        context={"user": current_user, "csrf_token": new_csrf, "message": message if not error else None, "error": error}
    )
