from fastapi.templating import Jinja2Templates
from app.core.currency import format_inr

templates = Jinja2Templates(directory="app/templates")
templates.env.filters["format_inr"] = format_inr
