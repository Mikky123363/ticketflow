"""Helpers that count how many tickets of a type are taken or still available."""
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import Order, Seat, Ticket, TicketType
from app.schemas.ticket_type import TicketTypeOut


def count_taken(db: Session, ticket_type_id: int) -> int:
    """Tickets that are reserved (being held) or confirmed (paid)."""
    return db.scalar(
        select(func.count(Ticket.id))
        .select_from(Ticket)
        .join(Order, Order.id == Ticket.order_id)
        .where(
            Ticket.ticket_type_id == ticket_type_id,
            Order.status.in_(["reserved", "confirmed"]),
        )
    ) or 0


def count_seats(db: Session, ticket_type_id: int, only_available: bool = False) -> int:
    query = select(func.count(Seat.id)).where(Seat.ticket_type_id == ticket_type_id)
    if only_available:
        query = query.where(Seat.status == "available")
    return db.scalar(query) or 0


def ticket_type_out(db: Session, ticket_type: TicketType) -> TicketTypeOut:
    """Builds the API response for a ticket type, including how many are still available."""
    if count_seats(db, ticket_type.id) > 0:
        available = count_seats(db, ticket_type.id, only_available=True)
    else:
        available = max(ticket_type.quantity - count_taken(db, ticket_type.id), 0)
    return TicketTypeOut(
        id=ticket_type.id,
        event_id=ticket_type.event_id,
        name=ticket_type.name,
        price=ticket_type.price,
        quantity=ticket_type.quantity,
        available=available,
    )
