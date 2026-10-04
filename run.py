import uvicorn
from app.config import settings

if __name__ == "__main__":
    print(f"🚀 Starting {settings.APP_NAME}...")
    print(f"📍 Access URL: http://{settings.HOST}:{settings.PORT}")
    print(f"🔐 Security Mode: {settings.APP_ENV}")
    uvicorn.run(
        "app.main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.DEBUG
    )
