from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.dependencies import get_owned_event, get_visible_event
from app.models import Event, Seat, TicketType
from app.schemas.seat import SeatGenerate, SeatOut
from app.services.inventory import count_seats
from app.services.orders import release_expired_reservations

router = APIRouter(prefix="/events/{event_id}/seats", tags=["Seats"])


@router.post("/", response_model=list[SeatOut], status_code=status.HTTP_201_CREATED)
def generate_seats(
    data: SeatGenerate,
    event: Event = Depends(get_owned_event),
    db: Session = Depends(get_db),
):
    """Creates a block of seats for one ticket type (only for events with has_seating = true)."""
    if not event.has_seating:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "This event does not use seating")

    ticket_type = db.execute(
        select(TicketType).where(TicketType.id == data.ticket_type_id, TicketType.event_id == event.id)
    ).scalar_one_or_none()
    if ticket_type is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Ticket type not found for this event")

    new_count = len(data.rows) * data.seats_per_row
    if count_seats(db, ticket_type.id) + new_count > ticket_type.quantity:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            f"Not enough quantity. '{ticket_type.name}' allows {ticket_type.quantity} seats in total.",
        )

    labels = [f"{row}{number}" for row in data.rows for number in range(1, data.seats_per_row + 1)]
    already = db.execute(
        select(Seat.label).where(Seat.event_id == event.id, Seat.label.in_(labels))
    ).scalars().all()
    if already:
        raise HTTPException(
            status.HTTP_409_CONFLICT, f"These seats already exist: {', '.join(sorted(already)[:10])}"
        )

    seats = [
        Seat(
            event_id=event.id,
            ticket_type_id=ticket_type.id,
            row_label=row,
            number=number,
            label=f"{row}{number}",
        )
        for row in data.rows
        for number in range(1, data.seats_per_row + 1)
    ]
    db.add_all(seats)
    db.flush()  # gives every seat its id
    result = [_seat_out(seat, ticket_type) for seat in seats]
    db.commit()
    return result


@router.get("/", response_model=list[SeatOut])
def seat_map(
    seat_status: Literal["available", "reserved", "sold"] | None = Query(default=None, alias="status"),
    event: Event = Depends(get_visible_event),
    db: Session = Depends(get_db),
):
    """All seats of an event (the seat map). Filter with ?status=available."""
    release_expired_reservations(db)  # so held-but-unpaid seats show as available again

    query = (
        select(Seat, TicketType)
        .join(TicketType, TicketType.id == Seat.ticket_type_id)
        .where(Seat.event_id == event.id)
        .order_by(Seat.row_label, Seat.number)
    )
    if seat_status:
        query = query.where(Seat.status == seat_status)

    return [_seat_out(seat, ticket_type) for seat, ticket_type in db.execute(query).all()]


def _seat_out(seat: Seat, ticket_type: TicketType) -> SeatOut:
    return SeatOut(
        id=seat.id,
        label=seat.label,
        row_label=seat.row_label,
        number=seat.number,
        status=seat.status,
        ticket_type_id=ticket_type.id,
        ticket_type_name=ticket_type.name,
        price=ticket_type.price,
    )
