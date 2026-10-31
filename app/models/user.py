from sqlalchemy import Column, DateTime, Integer, String

from app.core.database import Base
from app.core.utils import utcnow


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), unique=True, nullable=False, index=True)
    email = Column(String(255), unique=True, nullable=False, index=True)
    full_name = Column(String(100), nullable=True)
    hashed_password = Column(String, nullable=False)  # never the plain password
    role = Column(String(20), default="customer", nullable=False)  # customer / organizer / admin
    status = Column(String(20), default="active", nullable=False)  # active / suspended / banned
    created_at = Column(DateTime(timezone=True), default=utcnow, nullable=False)
