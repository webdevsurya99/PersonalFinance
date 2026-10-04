import datetime
import html
import re
from typing import Optional, Any, Dict
import bcrypt
import jwt
from itsdangerous import URLSafeTimedSerializer, BadSignature, SignatureExpired
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from app.config import settings

def get_now_utc() -> datetime.datetime:
    return datetime.datetime.now(datetime.timezone.utc).replace(tzinfo=None)

# CSRF Serializer
csrf_serializer = URLSafeTimedSerializer(settings.CSRF_SECRET_KEY, salt="csrf-salt-token-v1")

def hash_password(plain_password: str) -> str:
    """Hash a password using bcrypt with automatic salt generation."""
    if not plain_password:
        raise ValueError("Password cannot be empty")
    salt = bcrypt.gensalt(rounds=12)
    hashed = bcrypt.hashpw(plain_password.encode('utf-8'), salt)
    return hashed.decode('utf-8')

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a plain password against a bcrypt hashed password."""
    if not plain_password or not hashed_password:
        return False
    try:
        return bcrypt.checkpw(plain_password.encode('utf-8'), hashed_password.encode('utf-8'))
    except Exception:
        return False

def create_access_token(data: dict, expires_delta: Optional[datetime.timedelta] = None) -> str:
    """Create a signed JWT token."""
    to_encode = data.copy()
    now = get_now_utc()
    if expires_delta:
        expire = now + expires_delta
    else:
        expire = now + datetime.timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire, "iat": now})
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    return encoded_jwt

def decode_access_token(token: str) -> Optional[Dict[str, Any]]:
    """Decode and validate a signed JWT token."""
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        return payload
    except (jwt.PyJWTError, Exception):
        return None

def generate_csrf_token(user_id: int) -> str:
    """Generate a signed, timed CSRF token for the authenticated user session."""
    return csrf_serializer.dumps({"user_id": user_id, "timestamp": get_now_utc().isoformat()})

def validate_csrf_token(token: str, user_id: int, max_age: int = 86400) -> bool:
    """Validate a CSRF token matches user_id and has not expired (default 24h)."""
    if not token:
        return False
    try:
        data = csrf_serializer.loads(token, max_age=max_age)
        return data.get("user_id") == user_id
    except (BadSignature, SignatureExpired, Exception):
        return False

def sanitize_text(text: Optional[str]) -> Optional[str]:
    """Sanitize user text input by stripping HTML tags and control characters."""
    if text is None:
        return None
    cleaned = text.strip()
    # Strip HTML tags
    cleaned = re.sub(r'<[^>]*?>', '', cleaned)
    # Remove null bytes or unprintable control characters
    cleaned = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]', '', cleaned)
    return cleaned

class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """
    Middleware injecting OWASP-recommended security headers on every response:
    - X-Content-Type-Options: nosniff
    - X-Frame-Options: DENY (prevents Clickjacking)
    - X-XSS-Protection: 1; mode=block
    - Referrer-Policy: strict-origin-when-cross-origin
    - Permissions-Policy: camera=(), microphone=(), geolocation=()
    - Content-Security-Policy (CSP)
    """
    async def dispatch(self, request: Request, call_next):
        response: Response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
        
        csp = (
            "default-src 'self'; "
            "script-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net https://cdnjs.cloudflare.com; "
            "style-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net https://fonts.googleapis.com https://cdnjs.cloudflare.com; "
            "font-src 'self' https://fonts.gstatic.com https://cdnjs.cloudflare.com data:; "
            "img-src 'self' data: https: blob:; "
            "connect-src 'self' https://cdn.jsdelivr.net; "
            "manifest-src 'self'; "
            "base-uri 'self'; "
            "form-action 'self';"
        )
        response.headers["Content-Security-Policy"] = csp
        
        if settings.APP_ENV == "production":
            response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
            
        return response
