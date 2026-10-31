from sqlalchemy import Column, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import relationship

from app.core.database import Base


class Seat(Base):
    """One seat in a seated event, e.g. row A, number 5 -> label A5."""

    __tablename__ = "seats"
    __table_args__ = (UniqueConstraint("event_id", "label", name="uq_seat_event_label"),)

    id = Column(Integer, primary_key=True, index=True)
    event_id = Column(Integer, ForeignKey("events.id"), nullable=False, index=True)
    ticket_type_id = Column(Integer, ForeignKey("ticket_types.id"), nullable=False, index=True)
    row_label = Column(String(10), nullable=False)
    number = Column(Integer, nullable=False)
    label = Column(String(20), nullable=False)
    status = Column(String(20), default="available", nullable=False)  # available / reserved / sold

    event = relationship("Event", back_populates="seats")
