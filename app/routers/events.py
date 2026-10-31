from collections import defaultdict
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import get_db
from app.core.utils import utcnow
from app.dependencies import get_organizer, get_owned_event, get_visible_event
from app.models import Event, Order, Ticket, TicketType, User
from app.schemas.admin import SalesReport, TicketTypeSales
from app.schemas.event import EventCreate, EventOut, EventUpdate

router = APIRouter(prefix="/events", tags=["Events"])


@router.post("/", response_model=EventOut, status_code=status.HTTP_201_CREATED)
def create_event(
    data: EventCreate,
    user: User = Depends(get_organizer),
    db: Session = Depends(get_db),
):
    # Admin-created events are active straight away. Others may need approval.
    needs_approval = settings.require_event_approval and user.role != "admin"
    event = Event(
        organizer_id=user.id,
        name=data.name,
        description=data.description,
        venue=data.venue,
        event_date=data.event_date,
        has_seating=data.has_seating,
        status="pending" if needs_approval else "active",
    )
    db.add(event)
    db.commit()
    db.refresh(event)
    return event


@router.get("/", response_model=list[EventOut])
def browse_events(
    search: str | None = Query(default=None, description="Search in name or venue"),
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=20, ge=1, le=100),
    db: Session = Depends(get_db),
):
    """Public list of upcoming, active events."""
    query = select(Event).where(Event.status == "active", Event.event_date >= utcnow())
    if search:
        query = query.where(
            or_(
                Event.name.icontains(search, autoescape=True),
                Event.venue.icontains(search, autoescape=True),
            )
        )
    query = query.order_by(Event.event_date).offset(skip).limit(limit)
    return db.execute(query).scalars().all()


# This must stay ABOVE "/{event_id}", otherwise "mine" would be read as an event id.
@router.get("/mine", response_model=list[EventOut])
def my_events(user: User = Depends(get_organizer), db: Session = Depends(get_db)):
    """All events created by the logged-in organizer, whatever their status."""
    return db.execute(
        select(Event).where(Event.organizer_id == user.id).order_by(Event.event_date)
    ).scalars().all()


@router.get("/{event_id}", response_model=EventOut)
def read_event(event: Event = Depends(get_visible_event)):
    return event


@router.put("/{event_id}", response_model=EventOut)
def update_event(
    data: EventUpdate,
    event: Event = Depends(get_owned_event),
    db: Session = Depends(get_db),
):
    event.name = data.name
    event.description = data.description
    event.venue = data.venue
    event.event_date = data.event_date
    db.commit()
    db.refresh(event)
    return event


@router.delete("/{event_id}")
def delete_event(event: Event = Depends(get_owned_event), db: Session = Depends(get_db)):
    has_orders = db.execute(select(Order.id).where(Order.event_id == event.id).limit(1)).first()
    if has_orders:
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            "This event already has orders and cannot be deleted. Ask an admin to suspend it.",
        )
    db.delete(event)
    db.commit()
    return {"message": f"Event {event.id} deleted"}


@router.get("/{event_id}/sales", response_model=SalesReport)
def event_sales(event: Event = Depends(get_owned_event), db: Session = Depends(get_db)):
    """How many tickets were sold (paid) for this event, and the money made."""
    ticket_types = db.execute(
        select(TicketType).where(TicketType.event_id == event.id).order_by(TicketType.id)
    ).scalars().all()

    paid_tickets = db.execute(
        select(Ticket)
        .join(Order, Order.id == Ticket.order_id)
        .where(Ticket.event_id == event.id, Order.status == "confirmed")
    ).scalars().all()

    sold_count: dict[int, int] = defaultdict(int)
    revenue: dict[int, Decimal] = defaultdict(lambda: Decimal("0"))
    for ticket in paid_tickets:
        sold_count[ticket.ticket_type_id] += 1
        revenue[ticket.ticket_type_id] += ticket.price

    by_type = [
        TicketTypeSales(
            ticket_type_id=tt.id,
            name=tt.name,
            quantity=tt.quantity,
            sold=sold_count[tt.id],
            revenue=revenue[tt.id],
        )
        for tt in ticket_types
    ]
    return SalesReport(
        event_id=event.id,
        event_name=event.name,
        total_tickets_sold=len(paid_tickets),
        total_revenue=sum((r.revenue for r in by_type), Decimal("0")),
        by_ticket_type=by_type,
    )
