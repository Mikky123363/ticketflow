from decimal import Decimal

from pydantic import BaseModel, Field


class TicketTypeCreate(BaseModel):
    name: str = Field(min_length=2, max_length=50)
    price: Decimal = Field(gt=0, max_digits=10, decimal_places=2)
    quantity: int = Field(gt=0, le=100000)


class TicketTypeOut(BaseModel):
    id: int
    event_id: int
    name: str
    price: Decimal
    quantity: int
    available: int
