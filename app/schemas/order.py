from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.core.config import settings


class ReserveRequest(BaseModel):
    """Seated event: send seat_ids. Non-seated event: send ticket_type_id and quantity."""

    event_id: int
    ticket_type_id: int | None = None
    quantity: int = Field(default=1, ge=1, le=settings.max_tickets_per_order)
    seat_ids: list[int] | None = None

    @model_validator(mode="after")
    def check_mode(self):
        if self.seat_ids:
            if len(self.seat_ids) > settings.max_tickets_per_order:
                raise ValueError(f"You can reserve at most {settings.max_tickets_per_order} seats at once")
            if len(set(self.seat_ids)) != len(self.seat_ids):
                raise ValueError("seat_ids contains duplicates")
            if self.ticket_type_id is not None:
                raise ValueError("Send either seat_ids or ticket_type_id, not both")
        elif self.ticket_type_id is None:
            raise ValueError("Send seat_ids (seated event) or ticket_type_id with quantity")
        return self


class TicketOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    code: str
    ticket_type_id: int
    seat_id: int | None = None
    seat_label: str | None = None
    price: Decimal


class OrderOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    event_id: int
    status: str
    total_amount: Decimal
    created_at: datetime
    expires_at: datetime
    confirmed_at: datetime | None = None
    tickets: list[TicketOut]
