from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class UserCreate(BaseModel):
    username: str = Field(min_length=3, max_length=50)
    email: EmailStr
    full_name: str | None = Field(default=None, max_length=100)
    password: str = Field(min_length=8, max_length=128)
    # Admins cannot be created here. Use the create_admin script instead.
    role: Literal["customer", "organizer"] = "customer"


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    username: str
    email: str
    full_name: str | None = None
    role: str
    status: str
    created_at: datetime


class Token(BaseModel):
    access_token: str
    token_type: str


class UserStatusUpdate(BaseModel):
    status: Literal["active", "suspended", "banned"]
