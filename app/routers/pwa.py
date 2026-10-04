import os
from fastapi import APIRouter, Request, Response
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse

router = APIRouter(tags=["PWA"])

@router.get("/manifest.json")
async def get_manifest():
    manifest_data = {
        "name": "FinMinimal - Personal Finance",
        "short_name": "FinMinimal",
        "description": "Minimalistic Personal Finance, Expense, Bank & Credit Card Manager",
        "start_url": "/dashboard",
        "scope": "/",
        "display": "standalone",
        "orientation": "portrait-primary",
        "background_color": "#0B0F19",
        "theme_color": "#0B0F19",
        "icons": [
            {
                "src": "/static/img/icon-192.png",
                "sizes": "192x192",
                "type": "image/png",
                "purpose": "any maskable"
            },
            {
                "src": "/static/img/icon-512.png",
                "sizes": "512x512",
                "type": "image/png",
                "purpose": "any maskable"
            },
            {
                "src": "/static/img/apple-touch-icon.png",
                "sizes": "180x180",
                "type": "image/png"
            }
        ],
        "categories": ["finance", "productivity", "utilities"]
    }
    return JSONResponse(manifest_data, media_type="application/manifest+json")

@router.get("/sw.js")
async def get_service_worker():
    file_path = "app/static/js/sw.js"
    if os.path.exists(file_path):
        return FileResponse(file_path, media_type="application/javascript")
    return Response(content="// Service worker fallback", media_type="application/javascript")

@router.get("/offline.html", response_class=HTMLResponse)
async def get_offline_page():
    return HTMLResponse("""
    <!DOCTYPE html>
    <html lang="en" class="dark">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>FinMinimal - Offline</title>
        <style>
            body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; background: #0B0F19; color: #F8FAFC; display: flex; align-items: center; justify-content: center; height: 100vh; margin: 0; text-align: center; }
            .card { background: #161F30; padding: 2.5rem; border-radius: 1.5rem; max-width: 400px; border: 1px solid #283548; box-shadow: 0 20px 40px rgba(0,0,0,0.5); }
            .icon { font-size: 3.5rem; margin-bottom: 1rem; }
            h2 { margin: 0 0 0.5rem 0; font-weight: 700; }
            p { color: #94A3B8; font-size: 0.95rem; line-height: 1.5; }
            button { margin-top: 1.5rem; padding: 0.75rem 1.5rem; background: #3B82F6; color: #fff; border: none; border-radius: 0.75rem; font-weight: 600; cursor: pointer; }
        </style>
    </head>
    <body>
        <div class="card">
            <div class="icon">📶</div>
            <h2>You're Offline</h2>
            <p>FinMinimal needs an internet connection to sync your latest transactions and bank balances.</p>
            <button onclick="window.location.reload()">Retry Connection</button>
        </div>
    </body>
    </html>
    """)
