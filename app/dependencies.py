from typing import Optional
from fastapi import Request, Depends, HTTPException, status
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.models import User
from app.core.security import decode_access_token, validate_csrf_token

def get_current_user_optional(
    request: Request,
    db: Session = Depends(get_db)
) -> Optional[User]:
    """
    Retrieve currently authenticated user from session cookie or Authorization Bearer header.
    Returns None if not logged in.
    """
    token = None
    
    # 1. Check Authorization header
    auth_header = request.headers.get("Authorization")
    if auth_header and auth_header.startswith("Bearer "):
        token = auth_header.split(" ")[1]
        
    # 2. Check HTTP-only session cookie
    if not token:
        token = request.cookies.get(settings.SESSION_COOKIE_NAME)
        
    if not token:
        return None
        
    payload = decode_access_token(token)
    if not payload or "sub" not in payload:
        return None
        
    user_id = payload.get("sub")
    try:
        user_id = int(user_id)
    except (ValueError, TypeError):
        return None
        
    user = db.query(User).filter(User.id == user_id, User.is_active == True).first()
    return user

def get_current_user(
    request: Request,
    user: Optional[User] = Depends(get_current_user_optional)
) -> User:
    """
    Enforces authentication.
    If request is an API request -> returns 401 Unauthorized.
    If request is a browser web request -> redirects to /login.
    """
    if not user:
        if request.url.path.startswith("/api/") or "application/json" in request.headers.get("accept", ""):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Authentication credentials were not provided or have expired."
            )
        # Browser navigation redirect
        raise HTTPException(
            status_code=status.HTTP_307_TEMPORARY_REDIRECT,
            headers={"Location": f"/login?next={request.url.path}"}
        )
    return user

def get_current_admin_user(
    current_user: User = Depends(get_current_user)
) -> User:
    """Enforces administrator privileges."""
    if not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Administrative privileges required to access this resource."
        )
    return current_user

async def verify_csrf(request: Request, user: User = Depends(get_current_user)):
    """
    Verify CSRF token for mutating requests (POST, PUT, DELETE, PATCH).
    Token can be passed in 'X-CSRF-Token' header or form field 'csrf_token'.
    """
    if request.method in ("POST", "PUT", "DELETE", "PATCH"):
        # Allow JSON API with Bearer auth to bypass form CSRF if Authorization header is used
        auth_header = request.headers.get("Authorization")
        if auth_header and auth_header.startswith("Bearer "):
            return True
            
        token = request.headers.get("X-CSRF-Token")
        if not token:
            # Try form data
            try:
                form = await request.form()
                token = form.get("csrf_token")
            except Exception:
                pass

        if not token or not validate_csrf_token(token, user.id):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Invalid or expired CSRF token. Please refresh the page."
            )
    return True
