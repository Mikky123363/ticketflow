from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.dependencies import get_owned_event, get_visible_event
from app.models import Event, Ticket, TicketType
from app.schemas.ticket_type import TicketTypeCreate, TicketTypeOut
from app.services.inventory import count_seats, count_taken, ticket_type_out

router = APIRouter(prefix="/events/{event_id}/ticket-types", tags=["Ticket Types"])


def _get_ticket_type(db: Session, event: Event, ticket_type_id: int) -> TicketType:
    ticket_type = db.execute(
        select(TicketType).where(TicketType.id == ticket_type_id, TicketType.event_id == event.id)
    ).scalar_one_or_none()
    if ticket_type is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Ticket type not found")
    return ticket_type


@router.post("/", response_model=TicketTypeOut, status_code=status.HTTP_201_CREATED)
def create_ticket_type(
    data: TicketTypeCreate,
    event: Event = Depends(get_owned_event),
    db: Session = Depends(get_db),
):
    exists = db.execute(
        select(TicketType.id).where(TicketType.event_id == event.id, TicketType.name == data.name)
    ).first()
    if exists:
        raise HTTPException(status.HTTP_409_CONFLICT, f"This event already has a '{data.name}' ticket type")

    ticket_type = TicketType(
        event_id=event.id, name=data.name, price=data.price, quantity=data.quantity
    )
    db.add(ticket_type)
    db.commit()
    db.refresh(ticket_type)
    return ticket_type_out(db, ticket_type)


@router.get("/", response_model=list[TicketTypeOut])
def list_ticket_types(event: Event = Depends(get_visible_event), db: Session = Depends(get_db)):
    ticket_types = db.execute(
        select(TicketType).where(TicketType.event_id == event.id).order_by(TicketType.id)
    ).scalars().all()
    return [ticket_type_out(db, tt) for tt in ticket_types]


@router.put("/{ticket_type_id}", response_model=TicketTypeOut)
def update_ticket_type(
    ticket_type_id: int,
    data: TicketTypeCreate,
    event: Event = Depends(get_owned_event),
    db: Session = Depends(get_db),
):
    ticket_type = _get_ticket_type(db, event, ticket_type_id)

    duplicate = db.execute(
        select(TicketType.id).where(
            TicketType.event_id == event.id,
            TicketType.name == data.name,
            TicketType.id != ticket_type.id,
        )
    ).first()
    if duplicate:
        raise HTTPException(status.HTTP_409_CONFLICT, f"This event already has a '{data.name}' ticket type")

    # Quantity cannot drop below what is already sold/held, or below the number of seats
    minimum = max(count_taken(db, ticket_type.id), count_seats(db, ticket_type.id))
    if data.quantity < minimum:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            f"Quantity cannot be lower than {minimum} (tickets already sold/held or seats created)",
        )

    ticket_type.name = data.name
    ticket_type.price = data.price
    ticket_type.quantity = data.quantity
    db.commit()
    db.refresh(ticket_type)
    return ticket_type_out(db, ticket_type)


@router.delete("/{ticket_type_id}")
def delete_ticket_type(
    ticket_type_id: int,
    event: Event = Depends(get_owned_event),
    db: Session = Depends(get_db),
):
    ticket_type = _get_ticket_type(db, event, ticket_type_id)

    in_use = db.execute(select(Ticket.id).where(Ticket.ticket_type_id == ticket_type.id).limit(1)).first()
    if in_use or count_seats(db, ticket_type.id) > 0:
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            "This ticket type already has tickets or seats and cannot be deleted",
        )
    db.delete(ticket_type)
    db.commit()
    return {"message": f"Ticket type {ticket_type_id} deleted"}
