from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.dependencies import get_admin
from app.models import Event, Order, Ticket, User
from app.schemas.admin import AdminStats
from app.schemas.event import EventOut, EventStatusUpdate
from app.schemas.user import UserOut, UserStatusUpdate

# Every endpoint in this file is admin-only
router = APIRouter(prefix="/admin", tags=["Admin"], dependencies=[Depends(get_admin)])


@router.get("/events", response_model=list[EventOut])
def all_events(
    event_status: str | None = Query(default=None, alias="status", description="e.g. pending"),
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=200),
    db: Session = Depends(get_db),
):
    """Every event on the platform, whatever its status."""
    query = select(Event).order_by(Event.id.desc())
    if event_status:
        query = query.where(Event.status == event_status)
    return db.execute(query.offset(skip).limit(limit)).scalars().all()


@router.patch("/events/{event_id}/status", response_model=EventOut)
def moderate_event(event_id: int, data: EventStatusUpdate, db: Session = Depends(get_db)):
    """Approve (active), reject, or suspend an event."""
    event = db.get(Event, event_id)
    if event is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Event not found")
    event.status = data.status
    db.commit()
    db.refresh(event)
    return event


@router.get("/users", response_model=list[UserOut])
def all_users(
    role: str | None = None,
    user_status: str | None = Query(default=None, alias="status"),
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=200),
    db: Session = Depends(get_db),
):
    query = select(User).order_by(User.id)
    if role:
        query = query.where(User.role == role)
    if user_status:
        query = query.where(User.status == user_status)
    return db.execute(query.offset(skip).limit(limit)).scalars().all()


@router.patch("/users/{user_id}/status", response_model=UserOut)
def change_user_status(
    user_id: int,
    data: UserStatusUpdate,
    admin: User = Depends(get_admin),
    db: Session = Depends(get_db),
):
    """Suspend or ban a user (or set them back to active)."""
    if user_id == admin.id:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "You cannot change your own status")
    user = db.get(User, user_id)
    if user is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "User not found")
    user.status = data.status
    db.commit()
    db.refresh(user)
    return user


@router.get("/stats", response_model=AdminStats)
def platform_stats(db: Session = Depends(get_db)):
    """Dashboard numbers for the whole platform."""

    def count_by(column, model):
        return {key: total for key, total in db.execute(select(column, func.count(model.id)).group_by(column)).all()}

    tickets_sold = db.scalar(
        select(func.count(Ticket.id))
        .select_from(Ticket)
        .join(Order, Order.id == Ticket.order_id)
        .where(Order.status == "confirmed")
    )
    revenue = db.scalar(
        select(func.coalesce(func.sum(Order.total_amount), 0)).where(Order.status == "confirmed")
    )

    return AdminStats(
        total_users=db.scalar(select(func.count(User.id))) or 0,
        users_by_role=count_by(User.role, User),
        users_by_status=count_by(User.status, User),
        events_by_status=count_by(Event.status, Event),
        orders_by_status=count_by(Order.status, Order),
        tickets_sold=tickets_sold or 0,
        total_revenue=Decimal(revenue or 0),
    )
