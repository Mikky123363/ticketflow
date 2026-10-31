"""The purchase flow: reserve -> confirm (or cancel / expire).

The important rule is that the same seat or ticket can never be sold twice.
We do that by LOCKING the database rows (SELECT ... FOR UPDATE) before checking
them. If two customers try to buy the same seat at the same moment, the
second one waits until the first finishes, then sees the seat is taken.
"""
from datetime import timedelta
from decimal import Decimal
from uuid import uuid4

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.utils import utcnow
from app.models import Event, Order, Seat, Ticket, TicketType, User
from app.schemas.order import ReserveRequest
from app.services.inventory import count_taken


def _release_order(db: Session, order: Order, new_status: str) -> None:
    """Gives the seats of an order back and marks the order cancelled/expired."""
    for ticket in order.tickets:
        if ticket.seat_id:
            seat = db.get(Seat, ticket.seat_id)
            if seat is not None and seat.status == "reserved":
                seat.status = "available"
    order.status = new_status


def release_expired_reservations(db: Session) -> None:
    """Finds reservations that were not paid in time and frees them."""
    expired_orders = db.execute(
        select(Order)
        .where(Order.status == "reserved", Order.expires_at < utcnow())
        .with_for_update(skip_locked=True)
    ).scalars().all()

    for order in expired_orders:
        _release_order(db, order, "expired")
    db.commit()


def reserve_tickets(db: Session, user: User, data: ReserveRequest) -> Order:
    release_expired_reservations(db)

    event = db.get(Event, data.event_id)
    if event is None or event.status != "active":
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Event not found or not on sale")
    if event.event_date <= utcnow():
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "This event has already happened")

    lines: list[tuple[TicketType, Seat | None]] = []

    if event.has_seating:
        if not data.seat_ids:
            raise HTTPException(
                status.HTTP_400_BAD_REQUEST, "This event has seating. Choose seats with seat_ids."
            )

        # Lock the seats (always in the same order, so two buyers can't block each other forever)
        seats = db.execute(
            select(Seat)
            .where(Seat.id.in_(data.seat_ids), Seat.event_id == event.id)
            .order_by(Seat.id)
            .with_for_update()
        ).scalars().all()

        if len(seats) != len(data.seat_ids):
            raise HTTPException(status.HTTP_404_NOT_FOUND, "One or more seats were not found for this event")

        taken = [seat.label for seat in seats if seat.status != "available"]
        if taken:
            raise HTTPException(
                status.HTTP_409_CONFLICT, f"These seats are not available: {', '.join(taken)}"
            )

        type_ids = {seat.ticket_type_id for seat in seats}
        ticket_types = {
            tt.id: tt
            for tt in db.execute(select(TicketType).where(TicketType.id.in_(type_ids))).scalars()
        }
        for seat in seats:
            seat.status = "reserved"
            lines.append((ticket_types[seat.ticket_type_id], seat))

    else:
        if data.ticket_type_id is None:
            raise HTTPException(
                status.HTTP_400_BAD_REQUEST, "Choose a ticket_type_id and quantity for this event"
            )

        # Lock the ticket type row so nobody else can buy from it while we count
        ticket_type = db.execute(
            select(TicketType)
            .where(TicketType.id == data.ticket_type_id, TicketType.event_id == event.id)
            .with_for_update()
        ).scalar_one_or_none()
        if ticket_type is None:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Ticket type not found for this event")

        available = ticket_type.quantity - count_taken(db, ticket_type.id)
        if data.quantity > available:
            raise HTTPException(
                status.HTTP_409_CONFLICT,
                f"Only {max(available, 0)} '{ticket_type.name}' ticket(s) left",
            )
        lines = [(ticket_type, None)] * data.quantity

    total = sum((tt.price for tt, _ in lines), Decimal("0"))
    order = Order(
        user_id=user.id,
        event_id=event.id,
        status="reserved",
        total_amount=total,
        expires_at=utcnow() + timedelta(minutes=settings.reservation_minutes),
    )
    db.add(order)
    db.flush()  # gives the order an id

    for ticket_type, seat in lines:
        db.add(
            Ticket(
                order_id=order.id,
                event_id=event.id,
                ticket_type_id=ticket_type.id,
                seat_id=seat.id if seat else None,
                code=uuid4().hex,
                price=ticket_type.price,
            )
        )

    db.commit()
    db.refresh(order)
    return order


def confirm_order(db: Session, order_id: int) -> Order:
    """Marks a reserved order as paid. (The payment itself is simulated for now.)"""
    release_expired_reservations(db)

    order = db.execute(
        select(Order)
        .where(Order.id == order_id)
        .with_for_update()
        .execution_options(populate_existing=True)
    ).scalar_one()

    if order.status == "confirmed":
        raise HTTPException(status.HTTP_409_CONFLICT, "This order is already confirmed")
    if order.status != "reserved":
        raise HTTPException(
            status.HTTP_410_GONE, f"This order is {order.status}. Please reserve again."
        )
    if order.expires_at < utcnow():
        _release_order(db, order, "expired")
        db.commit()
        raise HTTPException(status.HTTP_410_GONE, "Your reservation expired. Please reserve again.")

    order.status = "confirmed"
    order.confirmed_at = utcnow()
    for ticket in order.tickets:
        if ticket.seat_id:
            seat = db.get(Seat, ticket.seat_id)
            if seat is not None:
                seat.status = "sold"
    db.commit()
    db.refresh(order)
    return order


def cancel_order(db: Session, order_id: int) -> Order:
    order = db.execute(
        select(Order)
        .where(Order.id == order_id)
        .with_for_update()
        .execution_options(populate_existing=True)
    ).scalar_one()

    if order.status == "confirmed":
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            "Paid orders cannot be cancelled here. Refunds are not available yet.",
        )
    if order.status != "reserved":
        raise HTTPException(status.HTTP_409_CONFLICT, f"This order is already {order.status}")

    _release_order(db, order, "cancelled")
    db.commit()
    db.refresh(order)
    return order
