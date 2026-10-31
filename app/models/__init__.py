# Importing every model here makes sure SQLAlchemy knows about all the tables.
from app.models.event import Event  # noqa: F401
from app.models.order import Order, Ticket  # noqa: F401
from app.models.seat import Seat  # noqa: F401
from app.models.ticket_type import TicketType  # noqa: F401
from app.models.user import User  # noqa: F401
