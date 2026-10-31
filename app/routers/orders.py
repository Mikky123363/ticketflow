from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Response, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.rate_limit import purchase_limiter
from app.dependencies import get_current_user
from app.models import Event, Order, User
from app.schemas.order import OrderOut, ReserveRequest
from app.services import orders as order_service
from app.services.email import send_ticket_email
from app.services.qr import make_qr_png

router = APIRouter(prefix="/orders", tags=["Orders"])


def _get_order(db: Session, order_id: int, user: User, owner_only: bool = False) -> Order:
    """Finds an order. Customers only see their own. Admins can see any (unless owner_only)."""
    order = db.get(Order, order_id)
    is_owner = order is not None and order.user_id == user.id
    is_admin = user.role == "admin" and not owner_only
    if order is None or not (is_owner or is_admin):
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Order not found")
    return order


@router.post(
    "/reserve",
    response_model=OrderOut,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(purchase_limiter)],
)
def reserve(
    data: ReserveRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Step 1: hold the seats/tickets for a few minutes while the customer pays."""
    return order_service.reserve_tickets(db, user, data)


# "/me" must stay ABOVE "/{order_id}"
@router.get("/me", response_model=list[OrderOut])
def my_orders(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    order_service.release_expired_reservations(db)
    return db.execute(
        select(Order).where(Order.user_id == user.id).order_by(Order.id.desc())
    ).scalars().all()


@router.get("/{order_id}", response_model=OrderOut)
def read_order(
    order_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    order_service.release_expired_reservations(db)
    return _get_order(db, order_id, user)


@router.post("/{order_id}/confirm", response_model=OrderOut)
def confirm(
    order_id: int,
    background_tasks: BackgroundTasks,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Step 2: confirm the order (payment is simulated for now). Tickets are emailed in the background."""
    _get_order(db, order_id, user, owner_only=True)
    order = order_service.confirm_order(db, order_id)

    event = db.get(Event, order.event_id)
    background_tasks.add_task(
        send_ticket_email,
        to_email=user.email,
        customer_name=user.full_name or user.username,
        event_name=event.name,
        event_date=event.event_date.strftime("%A %d %B %Y, %H:%M %Z"),
        venue=event.venue,
        tickets=[
            {
                "code": ticket.code,
                "type": next(t.name for t in event.ticket_types if t.id == ticket.ticket_type_id),
                "seat": ticket.seat_label,
            }
            for ticket in order.tickets
        ],
    )
    return order


@router.post("/{order_id}/cancel", response_model=OrderOut)
def cancel(
    order_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Gives up a reservation that has not been paid yet."""
    _get_order(db, order_id, user, owner_only=True)
    return order_service.cancel_order(db, order_id)


@router.get(
    "/{order_id}/tickets/{ticket_id}/qr",
    response_class=Response,
    responses={200: {"content": {"image/png": {}}}},
)
def ticket_qr_code(
    order_id: int,
    ticket_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """The QR code image for one ticket. Only available after the order is confirmed."""
    order = _get_order(db, order_id, user)
    if order.status != "confirmed":
        raise HTTPException(status.HTTP_409_CONFLICT, "QR codes are only available for confirmed orders")

    ticket = next((t for t in order.tickets if t.id == ticket_id), None)
    if ticket is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Ticket not found in this order")

    return Response(content=make_qr_png(ticket.code), media_type="image/png")
