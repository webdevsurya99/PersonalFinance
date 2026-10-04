import os
import sys
import socket
import uvicorn
from app.config import settings

# Ensure UTF-8 output encoding on Windows console
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

def get_local_ip():
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "127.0.0.1"

if __name__ == "__main__":
    port = int(os.environ.get("PORT", settings.PORT or 8000))
    host = os.environ.get("HOST", "0.0.0.0")
    debug = settings.DEBUG and os.environ.get("RAILWAY_ENVIRONMENT") is None

    local_ip = get_local_ip()
    print(f"[*] Starting {settings.APP_NAME} on port {port}...")
    print(f"[*] Local Access:  http://localhost:{port}")
    print(f"[*] Phone / Wi-Fi: http://{local_ip}:{port}")
    print(f"[*] Environment:   {settings.APP_ENV}")

    uvicorn.run(
        "app.main:app",
        host=host,
        port=port,
        reload=debug
    )
