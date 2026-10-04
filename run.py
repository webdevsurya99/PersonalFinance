import sys
import uvicorn
from app.config import settings

# Ensure UTF-8 output encoding on Windows console
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

if __name__ == "__main__":
    print(f"[*] Starting {settings.APP_NAME}...")
    print(f"[*] Access URL: http://{settings.HOST}:{settings.PORT}")
    print(f"[*] Security Mode: {settings.APP_ENV}")
    uvicorn.run(
        "app.main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.DEBUG
    )
