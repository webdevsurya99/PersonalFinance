import datetime
from typing import Optional
from fastapi import APIRouter, Request, Depends, HTTPException, status, Form
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import User, Category, Transaction
from app.dependencies import get_current_user, verify_csrf
from app.core.security import generate_csrf_token, sanitize_text
from app.core.presets import DEFAULT_CATEGORIES, POPULAR_ICONS

router = APIRouter(tags=["Categories"])
templates = Jinja2Templates(directory="app/templates")

def get_now_utc() -> datetime.datetime:
    return datetime.datetime.now(datetime.timezone.utc).replace(tzinfo=None)

@router.get("/categories", response_class=HTMLResponse)
async def categories_page(
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    categories = db.query(Category).filter(
        (Category.user_id == current_user.id) | (Category.is_system == True)
    ).order_by(Category.type.asc(), Category.name.asc()).all()

    cat_stats = {}
    for cat in categories:
        count = db.query(Transaction).filter(
            Transaction.user_id == current_user.id,
            Transaction.category_id == cat.id
        ).count()
        cat_stats[cat.id] = count

    csrf_token = generate_csrf_token(current_user.id)

    return templates.TemplateResponse(
        request=request,
        name="categories/index.html",
        context={
            "user": current_user,
            "categories": categories,
            "cat_stats": cat_stats,
            "popular_icons": POPULAR_ICONS,
            "csrf_token": csrf_token
        }
    )

@router.post("/categories/new")
async def create_category(
    request: Request,
    name: str = Form(...),
    type: str = Form("expense"),
    icon: str = Form("🏷️"),
    color: str = Form("#6366F1"),
    csrf_token: str = Form(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    await verify_csrf(request, current_user)

    clean_name = sanitize_text(name)
    if not clean_name:
        raise HTTPException(status_code=400, detail="Category name cannot be empty.")

    category = Category(
        user_id=current_user.id,
        name=clean_name,
        type=type if type in ("expense", "income") else "expense",
        icon=icon.strip() or "🏷️",
        color=color or "#6366F1",
        is_system=False,
        created_at=get_now_utc()
    )
    db.add(category)
    db.commit()

    return RedirectResponse(url="/categories", status_code=status.HTTP_303_SEE_OTHER)

@router.post("/categories/{cat_id}/edit")
async def edit_category(
    request: Request,
    cat_id: int,
    name: str = Form(...),
    type: str = Form(...),
    icon: str = Form(...),
    color: str = Form(...),
    csrf_token: str = Form(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    await verify_csrf(request, current_user)

    category = db.query(Category).filter(
        Category.id == cat_id,
        (Category.user_id == current_user.id) | (Category.is_system == True)
    ).first()
    
    if not category:
        raise HTTPException(status_code=404, detail="Category not found.")

    category.name = sanitize_text(name)
    category.type = type if type in ("expense", "income") else "expense"
    category.icon = icon.strip() or "🏷️"
    category.color = color or "#6366F1"
    db.commit()

    return RedirectResponse(url="/categories", status_code=status.HTTP_303_SEE_OTHER)

@router.post("/categories/{cat_id}/delete")
async def delete_category(
    request: Request,
    cat_id: int,
    csrf_token: str = Form(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    await verify_csrf(request, current_user)

    category = db.query(Category).filter(
        Category.id == cat_id,
        (Category.user_id == current_user.id) | (Category.is_system == True)
    ).first()

    if not category:
        raise HTTPException(status_code=404, detail="Category not found.")

    db.query(Transaction).filter(
        Transaction.user_id == current_user.id,
        Transaction.category_id == cat_id
    ).update({"category_id": None})

    db.delete(category)
    db.commit()

    return RedirectResponse(url="/categories", status_code=status.HTTP_303_SEE_OTHER)

@router.post("/categories/reset-defaults")
async def reset_default_categories(
    request: Request,
    csrf_token: str = Form(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    await verify_csrf(request, current_user)

    for cat in DEFAULT_CATEGORIES:
        existing = db.query(Category).filter(
            Category.user_id == current_user.id,
            Category.name == cat["name"]
        ).first()
        if not existing:
            new_cat = Category(
                user_id=current_user.id,
                name=cat["name"],
                type=cat["type"],
                icon=cat["icon"],
                color=cat["color"],
                is_system=True,
                created_at=get_now_utc()
            )
            db.add(new_cat)
    db.commit()

    return RedirectResponse(url="/categories", status_code=status.HTTP_303_SEE_OTHER)
