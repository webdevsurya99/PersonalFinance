import os
import uvicorn
from app.main import app
from app.config import settings

if __name__ == "__main__":
    port = int(os.environ.get("PORT", getattr(settings, "PORT", 8000)))
    host = os.environ.get("HOST", "0.0.0.0")
    uvicorn.run("app.main:app", host=host, port=port)
