from sqlalchemy import Column, DateTime, ForeignKey, Integer, Numeric, String
from sqlalchemy.orm import relationship

from app.core.database import Base
from app.core.utils import utcnow


class Order(Base):
    """A purchase. Starts as 'reserved', becomes 'confirmed' after payment.

    Status values: reserved / confirmed / cancelled / expired
    """

    __tablename__ = "orders"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    event_id = Column(Integer, ForeignKey("events.id"), nullable=False, index=True)
    status = Column(String(20), default="reserved", nullable=False, index=True)
    total_amount = Column(Numeric(10, 2), nullable=False)
    created_at = Column(DateTime(timezone=True), default=utcnow, nullable=False)
    expires_at = Column(DateTime(timezone=True), nullable=False)
    confirmed_at = Column(DateTime(timezone=True), nullable=True)

    tickets = relationship("Ticket", back_populates="order", order_by="Ticket.id")


class Ticket(Base):
    """One ticket inside an order. Has a unique code that goes into the QR code."""

    __tablename__ = "tickets"

    id = Column(Integer, primary_key=True, index=True)
    order_id = Column(Integer, ForeignKey("orders.id"), nullable=False, index=True)
    event_id = Column(Integer, ForeignKey("events.id"), nullable=False, index=True)
    ticket_type_id = Column(Integer, ForeignKey("ticket_types.id"), nullable=False, index=True)
    seat_id = Column(Integer, ForeignKey("seats.id"), nullable=True)
    code = Column(String(32), unique=True, nullable=False, index=True)
    price = Column(Numeric(10, 2), nullable=False)  # price at the time of purchase

    order = relationship("Order", back_populates="tickets")
    seat = relationship("Seat")

    @property
    def seat_label(self) -> str | None:
        return self.seat.label if self.seat else None
