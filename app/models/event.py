from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship

from app.core.database import Base
from app.core.utils import utcnow


class Event(Base):
    __tablename__ = "events"

    id = Column(Integer, primary_key=True, index=True)
    organizer_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    name = Column(String(200), nullable=False)
    description = Column(Text, nullable=True)
    venue = Column(String(200), nullable=False)
    event_date = Column(DateTime(timezone=True), nullable=False, index=True)
    has_seating = Column(Boolean, default=False, nullable=False)
    # pending / active / rejected / suspended
    status = Column(String(20), default="active", nullable=False, index=True)
    created_at = Column(DateTime(timezone=True), default=utcnow, nullable=False)

    ticket_types = relationship("TicketType", back_populates="event", cascade="all, delete-orphan")
    seats = relationship("Seat", back_populates="event", cascade="all, delete-orphan")
