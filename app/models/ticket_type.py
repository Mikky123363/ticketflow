from sqlalchemy import Column, ForeignKey, Integer, Numeric, String, UniqueConstraint
from sqlalchemy.orm import relationship

from app.core.database import Base


class TicketType(Base):
    """A kind of ticket for one event, e.g. VIP, Regular, Student."""

    __tablename__ = "ticket_types"
    __table_args__ = (UniqueConstraint("event_id", "name", name="uq_ticket_type_event_name"),)

    id = Column(Integer, primary_key=True, index=True)
    event_id = Column(Integer, ForeignKey("events.id"), nullable=False, index=True)
    name = Column(String(50), nullable=False)
    price = Column(Numeric(10, 2), nullable=False)
    quantity = Column(Integer, nullable=False)  # total tickets of this type

    event = relationship("Event", back_populates="ticket_types")
