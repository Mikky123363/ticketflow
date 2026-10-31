from decimal import Decimal

from pydantic import BaseModel, Field, field_validator


class SeatGenerate(BaseModel):
    """Creates a block of seats, e.g. rows A and B with 10 seats each -> A1..A10, B1..B10."""

    ticket_type_id: int
    rows: list[str] = Field(min_length=1, max_length=26)
    seats_per_row: int = Field(ge=1, le=100)

    @field_validator("rows")
    @classmethod
    def clean_rows(cls, rows: list[str]) -> list[str]:
        cleaned = [r.strip().upper() for r in rows]
        for r in cleaned:
            if not r.isalnum() or len(r) > 3:
                raise ValueError("Each row must be 1-3 letters or numbers, e.g. 'A'")
        if len(set(cleaned)) != len(cleaned):
            raise ValueError("rows contains duplicates")
        return cleaned


class SeatOut(BaseModel):
    id: int
    label: str
    row_label: str
    number: int
    status: str
    ticket_type_id: int
    ticket_type_name: str
    price: Decimal
