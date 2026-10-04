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

import socket

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
    local_ip = get_local_ip()
    print(f"[*] Starting {settings.APP_NAME}...")
    print(f"[*] Local Access:  http://localhost:{settings.PORT}")
    print(f"[*] Phone / Wi-Fi: http://{local_ip}:{settings.PORT}")
    print(f"[*] Security Mode: {settings.APP_ENV}")
    uvicorn.run(
        "app.main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.DEBUG
    )

