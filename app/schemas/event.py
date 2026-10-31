from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.core.utils import as_utc, utcnow


def _must_be_future(value: datetime) -> datetime:
    value = as_utc(value)
    if value <= utcnow():
        raise ValueError("event_date must be in the future")
    return value


class EventCreate(BaseModel):
    name: str = Field(min_length=3, max_length=200)
    description: str | None = None
    venue: str = Field(min_length=2, max_length=200)
    event_date: datetime
    has_seating: bool = False

    @field_validator("event_date")
    @classmethod
    def check_date(cls, value: datetime) -> datetime:
        return _must_be_future(value)


class EventUpdate(BaseModel):
    # has_seating cannot be changed after the event is created
    name: str = Field(min_length=3, max_length=200)
    description: str | None = None
    venue: str = Field(min_length=2, max_length=200)
    event_date: datetime

    @field_validator("event_date")
    @classmethod
    def check_date(cls, value: datetime) -> datetime:
        return _must_be_future(value)


class EventOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    organizer_id: int
    name: str
    description: str | None = None
    venue: str
    event_date: datetime
    has_seating: bool
    status: str
    created_at: datetime


class EventStatusUpdate(BaseModel):
    status: Literal["active", "rejected", "suspended"]
