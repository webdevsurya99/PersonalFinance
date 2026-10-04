import datetime
import calendar
from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session

from app.models import CreditCard, Notification
from app.core.date_provider import DateProvider

def get_safe_date(year: int, month: int, day: int) -> datetime.date:
    """Get valid date handling varying days in month (e.g., Feb 28/29, April 30)."""
    # Normalize month overflow
    while month > 12:
        month -= 12
        year += 1
    while month < 1:
        month += 12
        year -= 1
    max_day = calendar.monthrange(year, month)[1]
    safe_day = min(day, max_day)
    return datetime.date(year, month, safe_day)

def calculate_card_dates(card: CreditCard, current_date: datetime.date) -> Dict[str, Any]:
    """
    Calculate next billing date, next payment due date, and due urgency status for a credit card.
    """
    billing_day = card.billing_day or 15
    due_day = card.due_day or 5

    # 1. Next Billing Date
    if current_date.day <= billing_day:
        next_billing = get_safe_date(current_date.year, current_date.month, billing_day)
    else:
        next_billing = get_safe_date(current_date.year, current_date.month + 1, billing_day)

    # 2. Next Payment Due Date
    # Most Indian credit cards have due date either within same month (if due_day > billing_day)
    # or following month (if due_day < billing_day).
    if due_day > billing_day:
        if current_date.day <= due_day:
            next_due = get_safe_date(current_date.year, current_date.month, due_day)
        else:
            next_due = get_safe_date(current_date.year, current_date.month + 1, due_day)
    else:
        # due_day is smaller, meaning due date falls in next month relative to billing date
        if current_date.day <= due_day:
            next_due = get_safe_date(current_date.year, current_date.month, due_day)
        else:
            next_due = get_safe_date(current_date.year, current_date.month + 1, due_day)

    days_to_due = (next_due - current_date).days
    days_to_billing = (next_billing - current_date).days

    if days_to_due == 0:
        urgency = "danger"
        status_text = "Due Today!"
    elif days_to_due < 0:
        urgency = "danger"
        status_text = f"Overdue by {abs(days_to_due)} days!"
    elif days_to_due <= 3:
        urgency = "danger"
        status_text = f"Due in {days_to_due} day{'s' if days_to_due > 1 else ''}"
    elif days_to_due <= 7:
        urgency = "warning"
        status_text = f"Due in {days_to_due} days"
    else:
        urgency = "normal"
        status_text = f"Due on {next_due.strftime('%d %b')}"

    return {
        "card_id": card.id,
        "card_name": card.card_name,
        "bank_name": card.bank_name,
        "last_4": card.last_4_digits,
        "next_billing_date": next_billing,
        "next_due_date": next_due,
        "days_to_due": days_to_due,
        "days_to_billing": days_to_billing,
        "urgency": urgency,
        "status_text": status_text
    }

def sync_card_reminders(db: Session, user_id: int) -> List[Dict[str, Any]]:
    """
    Check all active cards for the user, create in-app notification records if due soon,
    and return list of card date summaries.
    """
    current_date = DateProvider.get_current_date(db)
    cards = db.query(CreditCard).filter(CreditCard.user_id == user_id, CreditCard.is_active == True).all()
    
    results = []
    for card in cards:
        info = calculate_card_dates(card, current_date)
        results.append(info)

        # If due in <= 3 days or today, check if notification already logged today
        if info["days_to_due"] <= 3:
            notif_title = f"⚠️ Credit Card Payment Due: {card.card_name} (••{card.last_4_digits})"
            # Check if recently notified
            recent_notif = db.query(Notification).filter(
                Notification.user_id == user_id,
                Notification.title == notif_title,
                Notification.type == "due_date"
            ).order_by(Notification.created_at.desc()).first()

            should_create = True
            if recent_notif:
                # If notified within last 24 hours, don't spam
                now_dt = DateProvider.get_current_datetime(db)
                if (now_dt - recent_notif.created_at).total_seconds() < 86400:
                    should_create = False

            if should_create:
                msg = (
                    f"Your payment for {card.card_name} ending with {card.last_4_digits} is "
                    f"{'due TODAY' if info['days_to_due'] == 0 else f'due in {info['days_to_due']} days'} "
                    f"on {info['next_due_date'].strftime('%d %B %Y')}."
                )
                notif = Notification(
                    user_id=user_id,
                    title=notif_title,
                    message=msg,
                    type="due_date",
                    link="/accounts",
                    created_at=DateProvider.get_current_datetime(db)
                )
                db.add(notif)

        # Billing cycle notification (if statement generated today or tomorrow)
        if info["days_to_billing"] in (0, 1):
            bill_title = f"📄 Bill Statement: {card.card_name} (••{card.last_4_digits})"
            recent_bill_notif = db.query(Notification).filter(
                Notification.user_id == user_id,
                Notification.title == bill_title,
                Notification.type == "billing_date"
            ).order_by(Notification.created_at.desc()).first()

            should_create_bill = True
            if recent_bill_notif:
                now_dt = DateProvider.get_current_datetime(db)
                if (now_dt - recent_bill_notif.created_at).total_seconds() < 86400:
                    should_create_bill = False

            if should_create_bill:
                b_msg = (
                    f"Your billing cycle for {card.card_name} ending with {card.last_4_digits} "
                    f"is {'TODAY' if info['days_to_billing'] == 0 else 'tomorrow'}. "
                    f"Statement will be generated on {info['next_billing_date'].strftime('%d %B %Y')}."
                )
                b_notif = Notification(
                    user_id=user_id,
                    title=bill_title,
                    message=b_msg,
                    type="billing_date",
                    link="/accounts",
                    created_at=DateProvider.get_current_datetime(db)
                )
                db.add(b_notif)

    db.commit()
    return results
