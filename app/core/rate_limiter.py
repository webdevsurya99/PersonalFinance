from slowapi import Limiter
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from starlette.requests import Request
from starlette.responses import JSONResponse, HTMLResponse
from app.config import settings

def custom_rate_limit_key(request: Request) -> str:
    """Extract client IP address or forwarded client IP for rate limiting."""
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "127.0.0.1"

limiter = Limiter(
    key_func=custom_rate_limit_key,
    default_limits=[settings.RATE_LIMIT_GENERAL]
)

def rate_limit_exceeded_handler(request: Request, exc: RateLimitExceeded):
    """Custom response when rate limit is exceeded."""
    if "application/json" in request.headers.get("accept", "") or request.url.path.startswith("/api/"):
        return JSONResponse(
            status_code=429,
            content={"error": "Too Many Requests", "detail": f"Rate limit exceeded: {exc.detail}. Please try again later."}
        )
    return HTMLResponse(
        status_code=429,
        content=f"""
        <!DOCTYPE html>
        <html>
        <head><title>Rate Limit Exceeded</title><meta name="viewport" content="width=device-width, initial-scale=1"></head>
        <body style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; display:flex; align-items:center; justify-content:center; height:100vh; margin:0; background:#0f172a; color:#f8fafc; text-align:center;">
            <div style="background:#1e293b; padding:2rem; border-radius:1rem; max-width:400px; box-shadow:0 10px 25px rgba(0,0,0,0.5);">
                <div style="font-size:3rem; margin-bottom:1rem;">⏳</div>
                <h2 style="margin:0 0 0.5rem 0;">Slow Down</h2>
                <p style="color:#94a3b8; font-size:0.9rem;">Too many requests. For your security, please wait a moment before trying again.</p>
                <a href="/" style="display:inline-block; margin-top:1rem; padding:0.5rem 1.25rem; background:#3b82f6; color:#fff; border-radius:0.5rem; text-decoration:none;">Go to Home</a>
            </div>
        </body>
        </html>
        """
    )
